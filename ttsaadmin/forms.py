"""Forms for YouTube channel management and tournament management"""
from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import YouTubeChannel, Tournament, TournamentPlayer, TournamentGame
from .youtube_utils import validate_and_fetch_channel_metadata, YouTubeChannelError
from ttsa_app.models import VideoLesson
from .youtube_utils import validate_and_fetch_video_metadata, YouTubeVideoError


class YouTubeChannelForm(forms.ModelForm):
    """Form for adding a YouTube channel"""
    
    channel_url_input = forms.CharField(
        max_length=255,
        label='Channel ID or Handle',
        help_text='Enter YouTube channel handle (e.g., @chess-kenya), channel ID (UC...), or full URL',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '@chess-kenya or UC... or full URL',
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


class TournamentForm(forms.ModelForm):
    """Professional form for creating and editing tournaments"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes and placeholders
        for field_name, field in self.fields.items():
            if field.widget.__class__.__name__ in ['TextInput', 'NumberInput', 'EmailInput']:
                field.widget.attrs.update({'class': 'form-control'})
            elif field.widget.__class__.__name__ == 'Textarea':
                field.widget.attrs.update({'class': 'form-control', 'rows': 4})
            elif field.widget.__class__.__name__ == 'Select':
                field.widget.attrs.update({'class': 'form-select'})
            elif field.widget.__class__.__name__ == 'CheckboxInput':
                field.widget.attrs.update({'class': 'form-check-input'})
        
        # Set initial values and placeholders
        self.fields['name'].widget.attrs.update({
            'placeholder': 'Tournament name'
        })
        self.fields['description'].widget.attrs.update({
            'placeholder': 'Tournament description...'
        })
        self.fields['venue'].widget.attrs.update({
            'placeholder': 'Venue location'
        })
        self.fields['time_control'].widget.attrs.update({
            'placeholder': '90+30'
        })
        self.fields['entry_fee'].widget.attrs.update({
            'placeholder': '0.00',
            'step': '0.01'
        })
        
        # Set help texts
        self.fields['rounds'].help_text = '1-15 rounds'
        self.fields['time_control'].help_text = 'Minutes+increment (e.g., 90+30)'
        self.fields['max_players'].help_text = '2-1000 players'
        self.fields['entry_fee'].help_text = 'USD (0 for free)'
        
        # Make fields required
        self.fields['name'].required = True
        self.fields['venue'].required = True
        self.fields['category'].required = True
        self.fields['format'].required = True
        self.fields['rounds'].required = True
        self.fields['time_control'].required = True
        self.fields['start_date'].required = True
        self.fields['end_date'].required = True
        self.fields['registration_deadline'].required = True
        self.fields['max_players'].required = True
        self.fields['entry_fee'].required = False

    class Meta:
        model = Tournament
        fields = [
            'name', 'description', 'venue', 'category', 'format', 'rounds',
            'time_control', 'start_date', 'end_date', 'registration_deadline',
            'entry_fee', 'max_players', 'status', 'is_active', 'is_featured'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'required': True
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4
            }),
            'venue': forms.TextInput(attrs={
                'class': 'form-control',
                'required': True
            }),
            'category': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
            'format': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
            'rounds': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'max': 15,
                'required': True
            }),
            'time_control': forms.TextInput(attrs={
                'class': 'form-control',
                'required': True
            }),
            'start_date': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local',
                'required': True
            }),
            'end_date': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local',
                'required': True
            }),
            'registration_deadline': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local',
                'required': True
            }),
            'entry_fee': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'step': '0.01'
            }),
            'max_players': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 2,
                'max': 1000,
                'required': True
            }),
            'status': forms.Select(attrs={
                'class': 'form-select'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'is_featured': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }
    
    def clean(self):
        """Validate tournament data"""
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        registration_deadline = cleaned_data.get('registration_deadline')
        max_players = cleaned_data.get('max_players')
        rounds = cleaned_data.get('rounds')
        
        # Validate date logic only if dates are provided
        if start_date and end_date and start_date >= end_date:
            raise ValidationError('End date must be after start date')
        
        if start_date and registration_deadline and registration_deadline >= start_date:
            raise ValidationError('Registration deadline must be before tournament start date')
        
        # Validate numeric values only if provided
        if max_players is not None and max_players < 2:
            raise ValidationError('Maximum players must be at least 2')
        
        if rounds is not None and rounds < 1:
            raise ValidationError('Number of rounds must be at least 1')
        
        return cleaned_data


class TournamentPlayerForm(forms.ModelForm):
    """Form for adding players to tournaments"""
    
    class Meta:
        model = TournamentPlayer
        fields = ['player_name', 'rating', 'email', 'phone', 'category']
        widgets = {
            'player_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter player name',
                'required': True
            }),
            'rating': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1000,
                'max': 3000,
                'placeholder': 'Enter rating',
                'required': True
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter email (optional)'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter phone (optional)'
            }),
            'category': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            })
        }
    
    def clean_rating(self):
        """Validate rating"""
        rating = self.cleaned_data.get('rating')
        if rating and (rating < 1000 or rating > 3000):
            raise ValidationError('Rating must be between 1000 and 3000')
        return rating


class TournamentGameForm(forms.ModelForm):
    """Form for updating game results"""
    
    class Meta:
        model = TournamentGame
        fields = ['result', 'status', 'pgn']
        widgets = {
            'result': forms.Select(attrs={
                'class': 'form-select'
            }),
            'status': forms.Select(attrs={
                'class': 'form-select'
            }),
            'pgn': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Enter PGN notation (optional)',
                'rows': 5
            })
        }


class TournamentSearchForm(forms.Form):
    """Form for searching tournaments"""
    
    search = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search tournaments...'
        })
    )
    
    category = forms.ChoiceField(
        choices=[('', 'All Categories')] + Tournament.CATEGORY_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    status = forms.ChoiceField(
        choices=[('', 'All Status')] + Tournament.STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    sort_by = forms.ChoiceField(
        choices=[
            ('-created_at', 'Newest First'),
            ('created_at', 'Oldest First'),
            ('start_date', 'Start Date (Earliest)'),
            ('-start_date', 'Start Date (Latest)'),
            ('name', 'Name (A-Z)'),
            ('-name', 'Name (Z-A)'),
        ],
        initial='-created_at',
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
