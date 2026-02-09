import base64
import json
from datetime import datetime
from django.utils import timezone
from django.db.models import Q, F
from django.db import transaction, IntegrityError
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Post, PostStatus, EngagementEvent, EngagementType


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


def parse_cursor(cursor_str):
    try:
        cursor_bytes = base64.b64decode(cursor_str.encode('utf-8'))
        cursor_json = cursor_bytes.decode('utf-8')
        return json.loads(cursor_json)
    except (ValueError, json.JSONDecodeError):
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
    - source_language_code: Filter by source language (e.g., "es_ES")
    - target_language_code: Filter by target language (e.g., "en_US")
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
