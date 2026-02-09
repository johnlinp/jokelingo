import base64
import json
from datetime import datetime
from django.utils import timezone
from django.db.models import Q
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Post, PostStatus


def post_to_dict(post):
    """
    Convert a Post model instance to the API response format.
    """
    return {
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
        
        # Convert Post objects to response format
        posts = [post_to_dict(post) for post in posts_list]
        
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
