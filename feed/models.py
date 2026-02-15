"""
Django models for Jokelingo application.

This module defines the database schema:
- User: Custom user model
- Post: Source + translation + explanation posts
- EngagementEvent: Source of truth for user engagement (helpful/confusing)
- AnalyticsEvent: Privacy-friendly analytics events (no IP, no sessions)
"""

import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """
    Custom user model for Jokelingo.
    
    Social login only - no password support.
    Table name: user
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Username and email fields are provided by AbstractUser by default
    display_name = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'user'
    
    def __str__(self):
        return f"{self.display_name or self.username or 'Anonymous'}"


class PostStatus(models.TextChoices):
    """Status enum for posts."""
    ACTIVE = 'active', 'Active'
    DELETED = 'deleted', 'Deleted'


class SourceProvider(models.TextChoices):
    """Source provider enum for posts."""
    REDDIT = 'reddit', 'Reddit'
    INSTAGRAM = 'instagram', 'Instagram'
    TWITTER = 'twitter', 'Twitter'
    IMGUR = 'imgur', 'Imgur'


class Post(models.Model):
    """
    Post model representing source + translation + explanation.
    
    A post is a complete unit that includes:
    - the source of a joke or meme
    - a user-provided translation
    - an optional explanation
    
    Table name: post
    """
    
    # Identity
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.CharField(
        max_length=20,
        choices=PostStatus.choices,
        default=PostStatus.ACTIVE
    )
    
    # Languages
    source_language_code = models.CharField(max_length=10)  # e.g., 'es'
    target_language_code = models.CharField(max_length=10)  # e.g., 'en'
    
    # Source
    source_provider = models.CharField(
        max_length=20,
        choices=SourceProvider.choices
    )
    source_raw_url = models.TextField()
    source_canonical_url = models.TextField()
    
    # Content
    translation_text = models.TextField(null=True, blank=True)
    explanation_text = models.TextField(null=True, blank=True)
    
    # Author
    author_user = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='posts',
        null=False
    )
    
    # Engagement caches (read-optimized, NOT source of truth)
    helpful_count_cache = models.IntegerField(default=0)
    confusing_count_cache = models.IntegerField(default=0)
    
    class Meta:
        db_table = 'post'
    
    def __str__(self):
        return f"Post {self.id} ({self.source_language_code} -> {self.target_language_code})"


class EngagementType(models.TextChoices):
    """Engagement type enum."""
    HELPFUL = 'helpful', 'Helpful'
    CONFUSING = 'confusing', 'Confusing'
    NONE = 'none', 'None'


class EngagementEvent(models.Model):
    """
    Engagement event model - source of truth for user engagement.
    
    Stores helpful/confusing votes from users.
    The engagement counts in Post are caches only.
    
    Table name: engagement_event
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    post = models.ForeignKey(
        Post,
        on_delete=models.PROTECT,
        related_name='engagement_events'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='engagement_events'
    )
    engagement_type = models.CharField(
        max_length=20,
        choices=EngagementType.choices,
        default=EngagementType.NONE
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'engagement_event'
        constraints = [
            models.UniqueConstraint(
                fields=['post', 'user'],
                name='unique_post_user_engagement'
            )
        ]
        indexes = [
            models.Index(fields=['post', 'user']),
        ]
    
    def __str__(self):
        return f"{self.user} -> {self.post}: {self.engagement_type}"


class AnalyticsEventType(models.TextChoices):
    """Analytics event type enum."""
    ENGAGEMENT_CLICK_ANON = 'engagement_click_anon', 'Engagement Click (Anonymous)'
    LOGIN_CLICK_TOPRIGHT_ANON = 'login_click_topright_anon', 'Login Click Top-Right (Anonymous)'
    LOAD_MORE_CLICK = 'load_more_click', 'Load More Click'
    PAGE_LANDING = 'page_landing', 'Page Landing'
    LANGUAGE_MENU_EXPAND = 'language_menu_expand', 'Language Menu Expand'
    LOGIN_MODAL_CLOSE = 'login_modal_close', 'Login Modal Close'


class AnalyticsEvent(models.Model):
    """
    Analytics event model for tracking user interactions.
    
    Privacy-friendly analytics - no IP addresses or session IDs stored.
    Table name: analytics_event
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event_type = models.CharField(
        max_length=50,
        choices=AnalyticsEventType.choices,
        db_index=True
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name='analytics_events',
        null=True,
        blank=True,
        db_index=True
    )
    metadata = models.JSONField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    
    class Meta:
        db_table = 'analytics_event'
        indexes = [
            models.Index(fields=['event_type', '-created_at']),
            models.Index(fields=['user', '-created_at']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        user_str = str(self.user) if self.user else 'Anonymous'
        return f"{self.event_type} by {user_str} at {self.created_at}"
