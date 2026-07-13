"""Forms for YouTube channel management"""
from django import forms
from django.core.exceptions import ValidationError
from .models import YouTubeChannel
from .youtube_utils import validate_and_fetch_channel_metadata, YouTubeChannelError
from ttsa_app.models import VideoLesson
from .youtube_utils import validate_and_fetch_video_metadata, YouTubeVideoError


class YouTubeChannelForm(forms.ModelForm):
    """Form for adding a YouTube channel"""
    
    channel_url_input = forms.URLField(
        max_length=255,
        label='Channel URL',
        help_text='Paste YouTube channel URL (e.g., https://www.youtube.com/channel/... or https://www.youtube.com/@handle)',
        widget=forms.URLInput(attrs={
            'class': 'form-control',
            'placeholder': 'https://www.youtube.com/channel/...',
            'required': True,
            'id': 'channel_url_input'
        })
    )
    
    class Meta:
        model = YouTubeChannel
        fields = ['channel_url', 'channel_name', 'channel_description', 'video_count']
        widgets = {
            'channel_url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://www.youtube.com/channel/...',
                'required': True,
                'id': 'channel_url',
                'readonly': True
            }),
            'channel_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Channel name',
                'required': True,
                'id': 'channel_name',
                'readonly': True
            }),
            'channel_description': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Channel description',
                'rows': 4,
                'id': 'channel_description',
                'readonly': True
            }),
            'video_count': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Video count',
                'required': True,
                'id': 'video_count',
                'readonly': True
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['channel_url'].label = 'Channel URL (auto-filled)'
        self.fields['channel_url'].required = False
        self.fields['channel_url'].help_text = 'This will be auto-filled based on the input URL'
        self.fields['channel_name'].label = 'Channel Name (auto-filled)'
        self.fields['channel_name'].required = False
        self.fields['channel_name'].help_text = 'This will be auto-filled from YouTube API'
        self.fields['channel_description'].label = 'Channel Description (auto-filled)'
        self.fields['channel_description'].required = False
        self.fields['channel_description'].help_text = 'This will be auto-filled from YouTube API'
        self.fields['video_count'].label = 'Video Count (auto-filled)'
        self.fields['video_count'].required = False
        self.fields['video_count'].help_text = 'This will be auto-filled from YouTube API'
    
    def clean_channel_url_input(self):
        """Validate channel URL and fetch metadata"""
        channel_url = self.cleaned_data.get('channel_url_input')
        
        if not channel_url:
            raise ValidationError('Channel URL is required')
        
        # Validate channel URL and fetch metadata
        try:
            channel_metadata = validate_and_fetch_channel_metadata(channel_url)
            
            # Check if channel already exists by channel_id
            if YouTubeChannel.objects.filter(channel_id=channel_metadata['channel_id']).exists():
                raise ValidationError('This YouTube channel has already been added')
            
            # Store metadata for use in save method
            self.channel_metadata = channel_metadata
            
            return channel_url
            
        except YouTubeChannelError as e:
            raise ValidationError(str(e))
    
    def save(self, commit=True):
        """Save the channel with fetched metadata"""
        channel = super().save(commit=False)
        
        # Populate fields from fetched metadata
        if hasattr(self, 'channel_metadata'):
            metadata = self.channel_metadata
            channel.channel_id = metadata['channel_id']
            channel.channel_url = metadata.get('channel_url', self.cleaned_data.get('channel_url_input'))
            channel.channel_name = metadata['channel_name']
            channel.channel_description = metadata['channel_description']
            channel.channel_thumbnail_url = metadata['channel_thumbnail_url']
            channel.video_count = metadata['video_count']
            channel.view_count = metadata['view_count']
        
        if commit:
            channel.save()
        
        return channel


class VideoLessonForm(forms.ModelForm):
    """Form for adding a YouTube video lesson"""
    
    video_url = forms.URLField(
        max_length=500,
        label='YouTube Video URL',
        help_text='Paste the YouTube video URL (e.g., https://www.youtube.com/watch?v=...)',
        widget=forms.URLInput(attrs={
            'class': 'form-control',
            'placeholder': 'https://www.youtube.com/watch?v=...',
            'required': True,
            'id': 'video_url'
        })
    )
    
    class Meta:
        model = VideoLesson
        fields = ['category', 'difficulty']
        widgets = {
            'category': forms.Select(attrs={
                'class': 'form-control',
                'required': True,
                'id': 'category'
            }),
            'difficulty': forms.Select(attrs={
                'class': 'form-control',
                'required': True,
                'id': 'difficulty'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].label = 'Category'
        self.fields['difficulty'].label = 'Difficulty'
    
    def clean_video_url(self):
        """Validate video URL and fetch metadata"""
        video_url = self.cleaned_data.get('video_url')
        
        if not video_url:
            raise ValidationError('Video URL is required')
        
        # Check if video already exists by youtube_id
        video_id = None
        try:
            from .youtube_utils import extract_video_id
            video_id = extract_video_id(video_url)
            if video_id and VideoLesson.objects.filter(youtube_id=video_id).exists():
                raise ValidationError('This YouTube video has already been added')
        except:
            pass
        
        # Validate video URL and fetch metadata
        try:
            video_metadata = validate_and_fetch_video_metadata(video_url)
            
            # Store metadata for use in save method
            self.video_metadata = video_metadata
            
            return video_url
            
        except YouTubeVideoError as e:
            raise ValidationError(str(e))
    
    def save(self, commit=True):
        """Save the video lesson with fetched metadata"""
        video = super().save(commit=False)
        
        # Populate fields from fetched metadata
        if hasattr(self, 'video_metadata'):
            metadata = self.video_metadata
            video.youtube_id = metadata['video_id']
            video.title = metadata['title']
            video.description = metadata.get('description', '')
            video.thumbnail_url = metadata['thumbnail_url']
            video.channel_name = metadata.get('channel_name', metadata.get('author_name', ''))
            video.duration = metadata.get('duration', '')
        
        if commit:
            video.save()
        
        return video
