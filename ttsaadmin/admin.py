from django.contrib import admin
from .models import YouTubeChannel


@admin.register(YouTubeChannel)
class YouTubeChannelAdmin(admin.ModelAdmin):
    """Admin interface for YouTubeChannel model"""
    list_display = ['channel_name', 'channel_id', 'video_count', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['channel_name', 'channel_id', 'channel_url']
    readonly_fields = ['channel_id', 'channel_name', 'channel_description', 'channel_thumbnail_url', 
                      'video_count', 'view_count', 'created_at', 'updated_at']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Channel Information', {
            'fields': ('channel_url', 'channel_id', 'channel_name', 'channel_description')
        }),
        ('Statistics', {
            'fields': ('video_count', 'view_count')
        }),
        ('Media', {
            'fields': ('channel_thumbnail_url',)
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
