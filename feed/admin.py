"""
Django admin configuration for Jokelingo models.
"""

import json
from django.contrib import admin
from .models import Post, User, EngagementEvent, AnalyticsEvent


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    """Admin interface for Post model."""
    
    list_display = [
        'id',
        'source_provider',
        'source_language_code',
        'target_language_code',
        'status',
        'helpful_count_cache',
        'confusing_count_cache',
        'created_at',
    ]
    
    list_filter = [
        'status',
        'source_provider',
        'source_language_code',
        'target_language_code',
        'created_at',
    ]
    
    search_fields = [
        'id',
        'translation_text',
        'explanation_text',
        'source_raw_url',
        'source_canonical_url',
    ]
    
    readonly_fields = [
        'id',
        'created_at',
        'updated_at',
    ]
    
    fieldsets = (
        ('Identity', {
            'fields': ('id', 'status', 'created_at', 'updated_at')
        }),
        ('Languages', {
            'fields': ('source_language_code', 'target_language_code')
        }),
        ('Source', {
            'fields': ('source_provider', 'source_raw_url', 'source_canonical_url')
        }),
        ('Content', {
            'fields': ('translation_text', 'explanation_text')
        }),
        ('Author', {
            'fields': ('author_user',)
        }),
        ('Engagement (Cached)', {
            'fields': ('helpful_count_cache', 'confusing_count_cache'),
        }),
    )
    
    raw_id_fields = ['author_user']
    
    date_hierarchy = 'created_at'


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    """Admin interface for User model."""
    
    list_display = ['id', 'email', 'display_name', 'created_at']
    search_fields = ['email', 'display_name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    date_hierarchy = 'created_at'


@admin.register(EngagementEvent)
class EngagementEventAdmin(admin.ModelAdmin):
    """Admin interface for EngagementEvent model."""
    
    list_display = ['id', 'post', 'user', 'engagement_type', 'created_at']
    list_filter = ['engagement_type', 'created_at']
    search_fields = ['post__id', 'user__email']
    readonly_fields = ['id', 'created_at', 'updated_at']
    raw_id_fields = ['post', 'user']


@admin.register(AnalyticsEvent)
class AnalyticsEventAdmin(admin.ModelAdmin):
    """Admin interface for AnalyticsEvent model."""
    
    list_display = ['id', 'event_type', 'user', 'metadata_display', 'created_at']
    list_filter = ['event_type', 'created_at']
    search_fields = ['id', 'user__id', 'user__email']
    readonly_fields = ['id', 'created_at', 'event_type', 'user', 'metadata_display', 'user_agent']
    
    def metadata_display(self, obj):
        """Display metadata in a readable format."""
        if obj.metadata:
            return json.dumps(obj.metadata, indent=2)
        return '-'
    metadata_display.short_description = 'Metadata'
    
    def has_add_permission(self, request):
        """Disable adding analytics events through admin."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Disable editing analytics events through admin."""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Allow deletion for debugging purposes."""
        return True
    
    date_hierarchy = 'created_at'
