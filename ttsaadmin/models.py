from django.db import models
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from django.utils import timezone
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


class SyncNotification(models.Model):
    """Model for tracking video sync notifications"""
    
    NOTIFICATION_TYPES = [
        ('sync_started', 'Sync Started'),
        ('sync_completed', 'Sync Completed'),
        ('sync_failed', 'Sync Failed'),
        ('video_added', 'Video Added'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, db_index=True)
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES, db_index=True)
    title = models.CharField(max_length=200)
    message = models.TextField()
    channel_name = models.CharField(max_length=255, blank=True)
    video_title = models.CharField(max_length=255, blank=True)
    task_id = models.CharField(max_length=255, blank=True, db_index=True)
    videos_added = models.IntegerField(default=0)
    videos_skipped = models.IntegerField(default=0)
    is_read = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['user', 'is_read', '-created_at']),
            models.Index(fields=['notification_type', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.title}"


class Tournament(models.Model):
    """Model for chess tournaments"""
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('registration', 'Registration Open'),
        ('ongoing', 'Ongoing'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    CATEGORY_CHOICES = [
        ('open', 'Open'),
        ('junior', 'Junior'),
        ('senior', 'Senior'),
        ('rapid', 'Rapid'),
        ('blitz', 'Blitz'),
    ]
    
    FORMAT_CHOICES = [
        ('swiss', 'Swiss System'),
        ('round_robin', 'Round Robin'),
        ('elimination', 'Knockout'),
        ('double_elimination', 'Double Elimination'),
    ]
    
    # Basic Information
    name = models.CharField(max_length=255, db_index=True)
    description = models.TextField(blank=True)
    venue = models.CharField(max_length=255, db_index=True)
    
    # Tournament Details
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, db_index=True)
    format = models.CharField(max_length=20, choices=FORMAT_CHOICES, default='swiss')
    rounds = models.PositiveIntegerField(default=7)
    time_control = models.CharField(max_length=20, help_text="e.g., '90+30', '15+10'")
    
    # Dates and Times
    start_date = models.DateTimeField(db_index=True)
    end_date = models.DateTimeField()
    registration_deadline = models.DateTimeField()
    
    # Registration
    entry_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    max_players = models.PositiveIntegerField(default=32)
    current_players = models.PositiveIntegerField(default=0, editable=False)
    
    # Status and Management
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft', db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)
    is_featured = models.BooleanField(default=False, db_index=True)
    
    # Metadata
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['category', 'status']),
            models.Index(fields=['start_date', 'status']),
            models.Index(fields=['created_by', '-created_at']),
            models.Index(fields=['is_active', 'status', '-start_date']),
        ]
    
    def __str__(self):
        return self.name
    
    def clean(self):
        """Validate tournament data"""
        if self.end_date <= self.start_date:
            raise ValidationError('End date must be after start date')
        
        if self.registration_deadline >= self.start_date:
            raise ValidationError('Registration deadline must be before tournament start date')
        
        if self.max_players < 2:
            raise ValidationError('Maximum players must be at least 2')
        
        if self.rounds < 1:
            raise ValidationError('Number of rounds must be at least 1')
    
    @property
    def available_slots(self):
        """Calculate available slots"""
        return max(0, self.max_players - self.current_players)
    
    @property
    def is_registration_open(self):
        """Check if registration is still open"""
        return (
            self.status in ['published', 'registration'] and
            self.registration_deadline > timezone.now() and
            self.available_slots > 0
        )
    
    @property
    def is_full(self):
        """Check if tournament is full"""
        return self.current_players >= self.max_players


class TournamentPlayer(models.Model):
    """Model for tournament participants"""
    
    STATUS_CHOICES = [
        ('registered', 'Registered'),
        ('confirmed', 'Confirmed'),
        ('withdrawn', 'Withdrawn'),
        ('disqualified', 'Disqualified'),
    ]
    
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE, related_name='players', db_index=True)
    player_name = models.CharField(max_length=255, db_index=True)
    rating = models.PositiveIntegerField(db_index=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    category = models.CharField(max_length=20, choices=Tournament.CATEGORY_CHOICES)
    
    # Tournament Statistics
    points = models.DecimalField(max_digits=5, decimal_places=2, default=0, db_index=True)
    wins = models.PositiveIntegerField(default=0)
    losses = models.PositiveIntegerField(default=0)
    draws = models.PositiveIntegerField(default=0)
    
    # Tie-break scores
    buchholz = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    sonneborn_berger = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    
    # Status and Metadata
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='registered', db_index=True)
    rank = models.PositiveIntegerField(null=True, blank=True, db_index=True)
    registered_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-points', '-buchholz', '-sonneborn_berger', 'player_name']
        indexes = [
            models.Index(fields=['tournament', '-points']),
            models.Index(fields=['tournament', 'status']),
            models.Index(fields=['tournament', 'rank']),
            models.Index(fields=['rating']),
            models.Index(fields=['player_name']),
        ]
        unique_together = ['tournament', 'player_name']
    
    def __str__(self):
        return f"{self.player_name} - {self.tournament.name}"
    
    @property
    def games_played(self):
        """Calculate total games played"""
        return self.wins + self.losses + self.draws


class TournamentGame(models.Model):
    """Model for individual tournament games"""
    
    RESULT_CHOICES = [
        ('1-0', 'White Wins'),
        ('0-1', 'Black Wins'),
        ('½-½', 'Draw'),
        ('*', 'Not Started/In Progress'),
    ]
    
    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('adjourned', 'Adjourned'),
        ('forfeit', 'Forfeit'),
    ]
    
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE, related_name='games', db_index=True)
    round_number = models.PositiveIntegerField(db_index=True)
    board_number = models.PositiveIntegerField(db_index=True)
    
    # Players
    white_player = models.ForeignKey(TournamentPlayer, on_delete=models.CASCADE, related_name='white_games', db_index=True)
    black_player = models.ForeignKey(TournamentPlayer, on_delete=models.CASCADE, related_name='black_games', db_index=True)
    
    # Game Details
    result = models.CharField(max_length=5, choices=RESULT_CHOICES, default='*', db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled', db_index=True)
    
    # Timing
    scheduled_time = models.DateTimeField()
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Game Data
    pgn = models.TextField(blank=True, help_text="PGN notation of the game")
    moves_count = models.PositiveIntegerField(default=0)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['round_number', 'board_number']
        indexes = [
            models.Index(fields=['tournament', 'round_number', 'board_number']),
            models.Index(fields=['white_player', 'tournament']),
            models.Index(fields=['black_player', 'tournament']),
            models.Index(fields=['tournament', 'status']),
            models.Index(fields=['tournament', 'result']),
            models.Index(fields=['scheduled_time']),
        ]
        unique_together = ['tournament', 'round_number', 'board_number']
    
    def __str__(self):
        return f"Round {self.round_number}, Board {self.board_number}: {self.white_player.player_name} vs {self.black_player.player_name}"
    
    def clean(self):
        """Validate game data"""
        if self.white_player == self.black_player:
            raise ValidationError('White and black players must be different')
        
        if self.white_player.tournament != self.black_player.tournament:
            raise ValidationError('Both players must be from the same tournament')
        
        if self.white_player.tournament != self.tournament:
            raise ValidationError('Players must be from the specified tournament')
    
    @property
    def is_completed(self):
        """Check if game is completed"""
        return self.status == 'completed' and self.result != '*'
    
    @property
    def winner(self):
        """Determine the winner of the game"""
        if self.result == '1-0':
            return self.white_player
        elif self.result == '0-1':
            return self.black_player
        elif self.result == '½-½':
            return None
        return None
