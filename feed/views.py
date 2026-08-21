import base64
import json
import ipaddress
import logging
import os
from functools import lru_cache
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse, urlunparse
from django.utils import timezone
from django.db.models import Q, F
from django.db import transaction, IntegrityError
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Post, PostStatus, EngagementEvent, EngagementType, AnalyticsEvent, SourceProvider

logger = logging.getLogger(__name__)


SUPPORTED_LANGUAGE_PAIRS = {
    ('es', 'en'),
    ('fr', 'en'),
    ('ja', 'en'),
    ('ko', 'en'),
    ('ja', 'zh-hant'),
    ('ko', 'zh-hant'),
    ('es', 'zh-hant'),
}

SUPPORTED_SOURCE_LANGUAGES = {'es', 'fr', 'ja', 'ko'}
SUPPORTED_TARGET_LANGUAGES = {'en', 'zh-hant'}
DEFAULT_GEOIP_DB_PATH = (
    Path(__file__).resolve().parent.parent / 'vendor' / 'geoip' / 'dbip-country-lite.mmdb'
)


def build_feed_path(source_language_code, target_language_code):
    """Build a feed path for a supported language pair."""
    return f'/{source_language_code}/{target_language_code}/'


def detect_source_provider(url):
    """Detect the source provider from a URL."""
    parsed = urlparse(url)
    hostname = (parsed.hostname or '').lower()

    if hostname.startswith('www.'):
        hostname = hostname[4:]
    if hostname.startswith('m.'):
        hostname = hostname[2:]

    provider_domains = {
        SourceProvider.REDDIT: ('reddit.com', 'redd.it'),
        SourceProvider.INSTAGRAM: ('instagram.com',),
        SourceProvider.TWITTER: ('twitter.com', 'x.com'),
        SourceProvider.IMGUR: ('imgur.com',),
        SourceProvider.FACEBOOK: ('facebook.com', 'fb.watch'),
    }

    for provider, domains in provider_domains.items():
        for domain in domains:
            if hostname == domain or hostname.endswith(f'.{domain}'):
                return provider

    return None


def canonicalize_source_url(raw_url):
    """Normalize a source URL for storage, embeds, and duplicate detection."""
    parsed = urlparse(raw_url.strip())
    if parsed.scheme not in ('http', 'https') or not parsed.netloc:
        return None

    hostname = (parsed.hostname or '').lower()
    if hostname.startswith('www.'):
        hostname = hostname[4:]
    if hostname.startswith('m.'):
        hostname = hostname[2:]

    netloc = hostname
    if parsed.port:
        netloc = f'{netloc}:{parsed.port}'

    path = parsed.path or '/'
    if path != '/':
        path = path.rstrip('/')

    normalized = parsed._replace(
        scheme='https',
        netloc=netloc,
        path=path,
        params='',
        fragment='',
    )
    return urlunparse(normalized)


def get_user_engagement_map(user, post_ids):
    """
    Batch fetch engagement events for a user and list of post IDs.
    
    Returns a dictionary mapping post_id (UUID) to engagement_type string.
    If no engagement event exists for a post, it won't be in the dict.
    
    Args:
        user: User instance
        post_ids: List of Post UUIDs
        
    Returns:
        dict: {post_id: engagement_type} where engagement_type is "helpful", "confusing", or "none"
    """
    if not user or not user.is_authenticated or not post_ids:
        return {}
    
    engagement_events = EngagementEvent.objects.filter(
        user=user,
        post_id__in=post_ids
    ).select_related('post')
    
    # Build map: post_id -> engagement_type
    engagement_map = {}
    for event in engagement_events:
        engagement_map[event.post_id] = event.engagement_type
    
    return engagement_map


def post_to_dict(post, my_engagement_type=None):
    """
    Convert a Post model instance to the API response format.
    
    Args:
        post: Post model instance
        my_engagement_type: Optional engagement type for the current user ("helpful", "confusing", or "none")
    """
    result = {
        "id": str(post.id),
        "short_code": post.short_code,
        "permalink": f"/post/{post.short_code}/",
        "created_at": post.created_at.isoformat(),
        "languages": {
            "source_language_code": post.source_language_code,
            "target_language_code": post.target_language_code
        },
        "source": {
            "raw_url": post.source_raw_url,
            "canonical_url": post.source_canonical_url,
            "provider": post.source_provider
        },
        "contribution": {
            "translation": {
                "text": post.translation_text
            },
            "explanation": {
                "text": post.explanation_text
            }
        },
        "engagement": {
            "helpful": post.helpful_count_cache,
            "confusing": post.confusing_count_cache
        },
        "author": {
            "id": str(post.author_user.id),
            "display_name": post.author_user.display_name or "Anonymous"
        }
    }
    
    # Only include my_engagement_type if user is authenticated
    if my_engagement_type is not None:
        result["my_engagement_type"] = my_engagement_type
    
    return result


def generate_cursor(created_at_str):
    cursor_data = {
        "created_at": created_at_str
    }
    cursor_json = json.dumps(cursor_data, sort_keys=True)
    cursor_bytes = cursor_json.encode('utf-8')
    return base64.b64encode(cursor_bytes).decode('utf-8')


def generate_cursor_from_updated_at(updated_at_str):
    """Generate cursor from updated_at timestamp for collection pagination."""
    cursor_data = {
        "updated_at": updated_at_str
    }
    cursor_json = json.dumps(cursor_data, sort_keys=True)
    cursor_bytes = cursor_json.encode('utf-8')
    return base64.b64encode(cursor_bytes).decode('utf-8')


def parse_cursor(cursor_str):
    try:
        cursor_bytes = base64.b64decode(cursor_str.encode('utf-8'))
        cursor_json = cursor_bytes.decode('utf-8')
        return json.loads(cursor_json)
    except (ValueError, json.JSONDecodeError):
        return None


def get_client_country_code(request):
    """
    Return a normalized client country code.

    Derive the country code transiently from the client IP via a configured
    GeoIP service, without storing the raw IP address.
    """
    client_ip = get_client_ip_address(request)
    if not client_ip:
        return None

    return lookup_country_code_for_ip(client_ip)


def get_client_ip_address(request):
    """Extract the first valid public client IP address from request headers."""
    raw_value = request.META.get('HTTP_X_FORWARDED_FOR')
    if not raw_value:
        return None

    for candidate in raw_value.split(','):
        normalized_ip = normalize_public_ip(candidate)
        if normalized_ip:
            return normalized_ip

    return None


def normalize_public_ip(raw_value):
    """Normalize a candidate IP address and reject non-public addresses."""
    if not raw_value:
        return None

    candidate = raw_value.strip()
    if candidate.startswith('[') and ']' in candidate:
        candidate = candidate[1:candidate.index(']')]
    elif candidate.count(':') == 1 and '.' in candidate:
        host, _, port = candidate.partition(':')
        if port.isdigit():
            candidate = host

    try:
        ip_obj = ipaddress.ip_address(candidate)
    except ValueError:
        return None

    if not ip_obj.is_global:
        return None

    return ip_obj.compressed


def lookup_country_code_for_ip(ip_address_value):
    """Look up a country code for a public IP using a local MMDB database."""
    reader = get_geoip_country_reader()
    if reader is None:
        return None

    try:
        response = reader.get(ip_address_value)
    except ValueError:
        return None

    if not response:
        return None

    country_code = (
        response.get('country', {}).get('iso_code')
        or response.get('registered_country', {}).get('iso_code')
        or response.get('represented_country', {}).get('iso_code')
    )
    if country_code:
        country_code = country_code.strip().upper()
        return country_code

    return None


@lru_cache(maxsize=1)
def get_geoip_country_reader():
    """
    Lazily open the local country MMDB database.
    """
    db_path = str(DEFAULT_GEOIP_DB_PATH)
    if not db_path:
        logger.error("GeoIP database path is empty")
        return None

    try:
        import maxminddb
    except ImportError as exc:
        logger.error("Failed to import maxminddb for GeoIP lookup: %s", exc)
        return None

    try:
        return maxminddb.open_database(db_path)
    except OSError as exc:
        logger.error("Failed to open GeoIP database at %s: %s", db_path, exc)
        return None


@transaction.atomic
def set_engagement(user, post_id, new_type):
    """
    Transaction-safe function to set user engagement on a post.
    
    This function:
    - Ensures exactly one engagement_event row per (post_id, user_id)
    - Updates cached counters correctly using delta logic
    - Uses F() expressions for atomic counter updates
    - Ensures counters never go below 0
    
    Args:
        user: User instance (must be authenticated)
        post_id: UUID of the post
        new_type: New engagement type ("helpful", "confusing", or "none")
        
    Returns:
        tuple: (success: bool, error_message: str or None)
    """
    # Validate engagement type
    valid_types = ['helpful', 'confusing', 'none']
    if new_type not in valid_types:
        return False, f"Invalid engagement_type: {new_type}"
    
    # Get or create engagement event with select_for_update to prevent race conditions
    try:
        engagement_event = EngagementEvent.objects.select_for_update().get(
            post_id=post_id,
            user=user
        )
        old_type = engagement_event.engagement_type
    except EngagementEvent.DoesNotExist:
        # Create new engagement event
        try:
            engagement_event = EngagementEvent.objects.create(
                post_id=post_id,
                user=user,
                engagement_type=new_type
            )
            old_type = 'none'
        except IntegrityError:
            # Race condition: another request created it, retry by getting it
            engagement_event = EngagementEvent.objects.select_for_update().get(
                post_id=post_id,
                user=user
            )
            old_type = engagement_event.engagement_type
    
    # Calculate counter deltas
    helpful_delta = 0
    confusing_delta = 0
    
    # Remove old engagement
    if old_type == 'helpful':
        helpful_delta -= 1
    elif old_type == 'confusing':
        confusing_delta -= 1
    
    # Add new engagement
    if new_type == 'helpful':
        helpful_delta += 1
    elif new_type == 'confusing':
        confusing_delta += 1
    
    # Update engagement event
    engagement_event.engagement_type = new_type
    engagement_event.save()
    
    # Update cached counters atomically using F() expressions
    post = Post.objects.select_for_update().get(id=post_id)
    
    if helpful_delta != 0:
        # Use update() with F() to update atomically
        Post.objects.filter(id=post_id).update(
            helpful_count_cache=F('helpful_count_cache') + helpful_delta
        )
        # Refresh to get actual value and clamp to ensure >= 0
        post.refresh_from_db()
        if post.helpful_count_cache < 0:
            Post.objects.filter(id=post_id).update(helpful_count_cache=0)
    
    if confusing_delta != 0:
        # Use update() with F() to update atomically
        Post.objects.filter(id=post_id).update(
            confusing_count_cache=F('confusing_count_cache') + confusing_delta
        )
        # Refresh to get actual value and clamp to ensure >= 0
        post.refresh_from_db()
        if post.confusing_count_cache < 0:
            Post.objects.filter(id=post_id).update(confusing_count_cache=0)
    
    return True, None


class FeedView(APIView):
    """
    API endpoint for fetching feed posts.
    
    Query parameters:
    - limit: Number of posts to return (default: 10)
    - source_language_code: Filter by source language (e.g., "es")
    - target_language_code: Filter by target language (e.g., "en")
    - cursor: Pagination cursor (optional)
    """
    
    def get(self, request):
        limit = request.query_params.get('limit', '10')
        try:
            limit = int(limit)
            if limit < 1:
                limit = 10
        except ValueError:
            limit = 10
        
        source_language_code = request.query_params.get('source_language_code')
        target_language_code = request.query_params.get('target_language_code')
        cursor = request.query_params.get('cursor')
        
        # Start with base queryset - only active posts, ordered by created_at descending
        queryset = Post.objects.filter(status=PostStatus.ACTIVE).order_by('-created_at')
        
        # Filter by language codes
        if source_language_code:
            queryset = queryset.filter(source_language_code=source_language_code)
        
        if target_language_code:
            queryset = queryset.filter(target_language_code=target_language_code)
        
        # Handle pagination with cursor
        if cursor:
            cursor_data = parse_cursor(cursor)
            if cursor_data:
                cursor_created_at = cursor_data.get('created_at')
                if cursor_created_at:
                    try:
                        # Parse ISO format string to datetime
                        cursor_dt = datetime.fromisoformat(cursor_created_at)
                        queryset = queryset.filter(created_at__lt=cursor_dt)
                    except (ValueError, AttributeError):
                        pass
        
        # Get one extra to check if there are more posts
        posts_queryset = queryset[:limit + 1]
        posts_list = list(posts_queryset)
        
        # Determine if there are more posts
        has_more = len(posts_list) > limit
        
        # Get only the requested number of posts
        posts_list = posts_list[:limit]
        
        # Fetch user engagement map if user is authenticated
        engagement_map = {}
        if request.user.is_authenticated:
            post_ids = [post.id for post in posts_list]
            engagement_map = get_user_engagement_map(request.user, post_ids)
        
        # Convert Post objects to response format
        posts = []
        for post in posts_list:
            # Get engagement type for this post, default to "none" if not found
            my_engagement_type = engagement_map.get(post.id, "none") if request.user.is_authenticated else None
            posts.append(post_to_dict(post, my_engagement_type=my_engagement_type))
        
        # Generate next cursor if there are more posts
        next_cursor = None
        if has_more and posts:
            last_post = posts_list[-1]
            next_cursor = generate_cursor(last_post.created_at.isoformat())
        
        # Build applied_filters
        applied_filters = {}
        if source_language_code or target_language_code:
            applied_filters['languages'] = {}
            if source_language_code:
                applied_filters['languages']['source_language_code'] = source_language_code
            if target_language_code:
                applied_filters['languages']['target_language_code'] = target_language_code
        
        # Build response
        response_data = {
            "meta": {
                "limit": limit,
                "has_more": has_more,
                "applied_filters": applied_filters
            },
            "posts": posts
        }
        
        if next_cursor:
            response_data["meta"]["next_cursor"] = next_cursor
        
        return Response(response_data, status=status.HTTP_200_OK)


class PostByCodeView(APIView):
    """Return one active post addressed by its public short code."""

    def get(self, request, short_code):
        try:
            post = Post.objects.select_related('author_user').get(
                short_code=short_code,
                status=PostStatus.ACTIVE,
            )
        except Post.DoesNotExist:
            return Response(
                {"error": "Post not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        my_engagement_type = None
        if request.user.is_authenticated:
            my_engagement_type = get_user_engagement_map(request.user, [post.id]).get(post.id, 'none')

        return Response(post_to_dict(post, my_engagement_type=my_engagement_type))


class MyCollectionView(APIView):
    """
    API endpoint for fetching the user's collection (posts marked as helpful).
    
    GET /api/v1/me/collection/
    
    Query parameters:
    - limit: Number of posts to return (default: 10)
    - cursor: Pagination cursor (optional)
    
    Returns:
        200 OK with list of posts
        401 Unauthorized if not authenticated
    """
    
    def get(self, request):
        # Check authentication
        if not request.user.is_authenticated:
            return Response(
                {"error": "Authentication required"},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        limit = request.query_params.get('limit', '10')
        try:
            limit = int(limit)
            if limit < 1:
                limit = 10
        except ValueError:
            limit = 10
        
        cursor = request.query_params.get('cursor')
        
        # Query engagement_event table for helpful posts
        # Filter by: user, engagement_type="helpful", post.status="active"
        queryset = EngagementEvent.objects.filter(
            user=request.user,
            engagement_type='helpful',
            post__status=PostStatus.ACTIVE
        ).select_related('post', 'post__author_user').order_by('-updated_at')
        
        # Handle pagination with cursor (based on updated_at)
        if cursor:
            cursor_data = parse_cursor(cursor)
            if cursor_data:
                cursor_updated_at = cursor_data.get('updated_at')
                if cursor_updated_at:
                    try:
                        # Parse ISO format string to datetime
                        cursor_dt = datetime.fromisoformat(cursor_updated_at)
                        queryset = queryset.filter(updated_at__lt=cursor_dt)
                    except (ValueError, AttributeError):
                        pass
        
        # Get one extra to check if there are more posts
        engagement_events_queryset = queryset[:limit + 1]
        engagement_events_list = list(engagement_events_queryset)
        
        # Determine if there are more posts
        has_more = len(engagement_events_list) > limit
        
        # Get only the requested number of engagement events
        engagement_events_list = engagement_events_list[:limit]
        
        # Extract posts from engagement events
        posts_list = [event.post for event in engagement_events_list]
        
        # Since all posts are marked as helpful by this user, we know the engagement type
        # Convert Post objects to response format
        posts = []
        for post in posts_list:
            # All posts in this list are marked as helpful by the current user
            posts.append(post_to_dict(post, my_engagement_type="helpful"))
        
        # Generate next cursor if there are more posts
        next_cursor = None
        if has_more and engagement_events_list:
            last_event = engagement_events_list[-1]
            next_cursor = generate_cursor_from_updated_at(last_event.updated_at.isoformat())
        
        # Build response
        response_data = {
            "meta": {
                "limit": limit,
                "has_more": has_more
            },
            "posts": posts
        }
        
        if next_cursor:
            response_data["meta"]["next_cursor"] = next_cursor
        
        return Response(response_data, status=status.HTTP_200_OK)


class EngagementView(APIView):
    """
    API endpoint for setting user engagement on a post.
    
    POST /api/v1/posts/<post_id>/engagement
    
    Request body:
    {
        "engagement_type": "helpful" | "confusing" | "none"
    }
    
    Returns:
        204 No Content on success
        401 Unauthorized if not authenticated
        400 Bad Request if invalid input
        404 Not Found if post doesn't exist
    """
    
    def post(self, request, post_id):
        # Check authentication
        if not request.user.is_authenticated:
            return Response(
                {"error": "Authentication required"},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # Parse request body
        try:
            engagement_type = request.data.get('engagement_type')
            if not engagement_type:
                return Response(
                    {"error": "engagement_type is required"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except Exception:
            return Response(
                {"error": "Invalid request body"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate post exists
        try:
            post = Post.objects.get(id=post_id, status=PostStatus.ACTIVE)
        except Post.DoesNotExist:
            return Response(
                {"error": "Post not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Set engagement
        success, error_message = set_engagement(request.user, post_id, engagement_type)
        
        if not success:
            return Response(
                {"error": error_message},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Return 204 No Content (no JSON body)
        return Response(status=status.HTTP_204_NO_CONTENT)


class CreatePostView(APIView):
    """
    API endpoint for creating a new post.

    POST /api/v1/posts
    """

    def post(self, request):
        if not request.user.is_authenticated:
            return Response(
                {"error": "Authentication required"},
                status=status.HTTP_401_UNAUTHORIZED
            )

        source_language_code = (request.data.get('source_language_code') or '').strip().lower()
        target_language_code = (request.data.get('target_language_code') or '').strip().lower()
        source_raw_url = (request.data.get('source_raw_url') or '').strip()
        translation_text = (request.data.get('translation_text') or '').strip()
        explanation_text = (request.data.get('explanation_text') or '').strip()

        if source_language_code not in SUPPORTED_SOURCE_LANGUAGES:
            return Response(
                {"error": "Unsupported source language"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if target_language_code not in SUPPORTED_TARGET_LANGUAGES:
            return Response(
                {"error": "Unsupported target language"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if (source_language_code, target_language_code) not in SUPPORTED_LANGUAGE_PAIRS:
            return Response(
                {"error": "Unsupported language pair"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not source_raw_url:
            return Response(
                {"error": "source_raw_url is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        has_translation = bool(translation_text)
        has_explanation = bool(explanation_text)

        if not has_translation and not has_explanation:
            return Response(
                {"error": "Either translation or explanation is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        source_canonical_url = canonicalize_source_url(source_raw_url)
        if not source_canonical_url:
            return Response(
                {"error": "Enter a valid source URL"},
                status=status.HTTP_400_BAD_REQUEST
            )

        source_provider = detect_source_provider(source_canonical_url)
        if not source_provider:
            return Response(
                {"error": "Only Reddit, Instagram, X/Twitter, Imgur, and Facebook URLs are supported right now"},
                status=status.HTTP_400_BAD_REQUEST
            )

        post = Post.objects.create(
            source_language_code=source_language_code,
            target_language_code=target_language_code,
            source_provider=source_provider,
            source_raw_url=source_raw_url,
            source_canonical_url=source_canonical_url,
            translation_text=translation_text,
            explanation_text=explanation_text or None,
            author_user=request.user,
        )

        return Response(
            {"post_id": str(post.id)},
            status=status.HTTP_201_CREATED
        )


@method_decorator(csrf_exempt, name='dispatch')
class AnalyticsView(APIView):
    """
    API endpoint for recording analytics events.
    
    POST /api/v1/analytics/events
    
    Request body:
    {
        "event_type": string,
        "metadata": { ... }  // optional
    }
    
    Returns:
        204 No Content on success
    """
    
    def post(self, request):
        event_type = request.data.get('event_type', '')
        metadata = request.data.get('metadata')
        user_agent = request.META.get('HTTP_USER_AGENT', None)
        
        AnalyticsEvent.objects.create(
            event_type=event_type,
            user=request.user if request.user.is_authenticated else None,
            client_country_code=get_client_country_code(request),
            metadata=metadata,
            user_agent=user_agent
        )
        
        return Response(status=status.HTTP_204_NO_CONTENT)
