from django.db import models
from django.core.exceptions import ValidationError
import re


class YouTubeChannel(models.Model):
    """Model for storing YouTube channel information"""
    
    channel_id = models.CharField(max_length=100, unique=True, db_index=True)
    channel_url = models.URLField(max_length=255, unique=True)
    channel_name = models.CharField(max_length=255)
    channel_description = models.TextField(blank=True)
    channel_thumbnail_url = models.URLField(max_length=255, blank=True)
    video_count = models.PositiveIntegerField(default=0)
    view_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['channel_id']),
            models.Index(fields=['channel_name']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return self.channel_name
    
    def clean(self):
        """Validate channel URL format"""
        if not self.is_valid_youtube_channel_url(self.channel_url):
            raise ValidationError({'channel_url': 'Invalid YouTube channel URL format'})
    
    @staticmethod
    def is_valid_youtube_channel_url(url):
        """Validate if the URL is a valid YouTube channel URL"""
        patterns = [
            r'^https?://(www\.)?youtube\.com/channel/[A-Za-z0-9_-]{24}$',
            r'^https?://(www\.)?youtube\.com/c/[A-Za-z0-9_-]+$',
            r'^https?://(www\.)?youtube\.com/@[A-Za-z0-9_.-]+$',
            r'^https?://(www\.)?youtube\.com/user/[A-Za-z0-9_-]+$',
        ]
        return any(re.match(pattern, url) for pattern in patterns)
