from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.utils import timezone


class User(AbstractUser):
    """Custom User model with Role-Based Access Control."""
    ROLE_CHOICES = [
        ('player', 'Player'),
        ('player_plus', 'Player Plus'),
        ('ttsa_admin', 'TTSA Admin'),
    ]

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='player',
        db_index=True,
    )

    class Meta:
        db_table = 'ttsa_user'
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self):
        return self.username

    @property
    def is_player(self):
        return self.role == 'player'

    @property
    def is_player_plus(self):
        return self.role == 'player_plus'

    @property
    def is_ttsa_admin(self):
        return self.role == 'ttsa_admin'

    @property
    def can_manage_tournaments(self):
        """Only PLAYER_PLUS and TTSA Admin users can create/manage tournaments."""
        return self.role in ('player_plus', 'ttsa_admin')

    def upgrade_to_player_plus(self):
        """Upgrade a player to PLAYER_PLUS role, preserving all history."""
        if self.role == 'player':
            self.role = 'player_plus'
            self.save(update_fields=['role'])
            return True
        return False

    @property
    def has_pending_player_plus_application(self):
        if not hasattr(self, 'player_plus_applications'):
            return False
        return self.player_plus_applications.filter(status='pending').exists()


class PlayerProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    avatar = models.ImageField(upload_to='avatars/', default='avatars/default.png')
    rating = models.IntegerField(default=800)
    coins = models.IntegerField(default=100)
    level = models.IntegerField(default=1)
    experience_points = models.IntegerField(default=0)
    learning_streak = models.IntegerField(default=0)
    last_played = models.DateField(default=timezone.now)
    bio = models.TextField(max_length=500, blank=True)

    def __str__(self):
        return f"{self.user.username}'s Profile"


class OrganizerProfile(models.Model):
    """Profile for PLAYER_PLUS users who can organize tournaments."""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='organizer_profile')
    organization_name = models.CharField(max_length=255, blank=True, db_index=True)
    contact_phone = models.CharField(max_length=20, blank=True)
    contact_email = models.EmailField(blank=True)
    bio = models.TextField(max_length=500, blank=True)
    is_verified = models.BooleanField(default=False, db_index=True)
    tournaments_created = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ttsa_organizer_profile'
        verbose_name = 'Organizer Profile'
        verbose_name_plural = 'Organizer Profiles'

    def __str__(self):
        return f"{self.user.username} - Organizer"


class PlayerPlusApplication(models.Model):
    """Application submitted by a player to become Player Plus."""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='player_plus_applications', db_index=True)
    full_name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=20)
    additional_info = models.TextField(max_length=1000, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', db_index=True)
    submitted_at = models.DateTimeField(auto_now_add=True, db_index=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_player_plus_applications')
    admin_notes = models.TextField(max_length=1000, blank=True)

    class Meta:
        db_table = 'ttsa_player_plus_application'
        ordering = ['-submitted_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['status', '-submitted_at']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.status}"

    def approve(self, admin_user):
        if self.status != 'pending':
            return False
        self.status = 'approved'
        self.reviewed_at = timezone.now()
        self.reviewed_by = admin_user
        self.save()
        user = self.user
        if user.role == 'player':
            user.role = 'player_plus'
            user.save(update_fields=['role'])
        # Populate organizer profile
        profile, _ = OrganizerProfile.objects.get_or_create(user=user)
        profile.contact_phone = self.phone_number
        profile.contact_email = user.email
        profile.organization_name = self.full_name
        profile.bio = self.additional_info
        profile.is_verified = True
        profile.save()
        return True

    def reject(self, admin_user, notes=''):
        if self.status != 'pending':
            return False
        self.status = 'rejected'
        self.reviewed_at = timezone.now()
        self.reviewed_by = admin_user
        self.admin_notes = notes
        self.save()
        return True


class Achievement(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    icon = models.CharField(max_length=50)  # emoji or icon name
    points = models.IntegerField(default=10)
    category = models.CharField(max_length=50, choices=[
        ('games', 'Games'),
        ('lessons', 'Lessons'),
        ('puzzles', 'Puzzles'),
        ('streak', 'Learning Streak'),
        ('special', 'Special')
    ])
    
    def __str__(self):
        return self.name


class PlayerAchievement(models.Model):
    player = models.ForeignKey(PlayerProfile, on_delete=models.CASCADE)
    achievement = models.ForeignKey(Achievement, on_delete=models.CASCADE)
    earned_at = models.DateTimeField(auto_now_add=True)
    progress = models.IntegerField(default=0)  # For achievements with progress
    
    class Meta:
        unique_together = ['player', 'achievement']


class ChessGame(models.Model):
    WHITE = 'white'
    BLACK = 'black'
    COLORS = [(WHITE, 'White'), (BLACK, 'Black')]
    
    player = models.ForeignKey(PlayerProfile, on_delete=models.CASCADE, db_index=True)
    player_color = models.CharField(max_length=5, choices=COLORS, db_index=True)
    difficulty_level = models.CharField(max_length=20, choices=[
        ('beginner', 'Beginner'),
        ('easy', 'Easy'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
        ('expert', 'Expert'),
        ('master', 'Master')
    ], db_index=True)
    pgn = models.TextField(blank=True)  # Portable Game Notation
    result = models.CharField(max_length=20, choices=[
        ('win', 'Win'),
        ('loss', 'Loss'),
        ('draw', 'Draw'),
        ('ongoing', 'Ongoing')
    ], default='ongoing', db_index=True)
    moves_count = models.IntegerField(default=0)
    time_elapsed = models.DurationField(default=timezone.timedelta)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['player', '-created_at']),
            models.Index(fields=['result', 'created_at']),
        ]
    
    def __str__(self):
        return f"Game {self.id} - {self.player.user.username} vs AI ({self.difficulty_level})"


class Lesson(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    content = models.TextField()
    difficulty = models.CharField(max_length=20, choices=[
        ('beginner', 'Beginner'),
        ('easy', 'Easy'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced')
    ], db_index=True)
    category = models.CharField(max_length=50, choices=[
        ('basics', 'Chess Basics'),
        ('openings', 'Openings'),
        ('tactics', 'Tactics'),
        ('endgames', 'Endgames'),
        ('strategy', 'Strategy')
    ], db_index=True)
    order = models.IntegerField(default=0)
    is_interactive = models.BooleanField(default=True)
    points_reward = models.IntegerField(default=10)
    
    class Meta:
        indexes = [
            models.Index(fields=['category', 'order']),
            models.Index(fields=['difficulty', 'order']),
        ]
    
    def __str__(self):
        return self.title


class PlayerLesson(models.Model):
    player = models.ForeignKey(PlayerProfile, on_delete=models.CASCADE)
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE)
    completed = models.BooleanField(default=False)
    score = models.IntegerField(default=0)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ['player', 'lesson']


class Puzzle(models.Model):
    fen = models.CharField(max_length=100)  # Forsyth-Edwards Notation
    solution = models.CharField(max_length=200)
    difficulty = models.CharField(max_length=20, choices=[
        ('beginner', 'Beginner'),
        ('easy', 'Easy'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
        ('expert', 'Expert')
    ], db_index=True)
    category = models.CharField(max_length=50, choices=[
        ('tactics', 'Tactics'),
        ('checkmate', 'Checkmate'),
        ('endgame', 'Endgame')
    ], db_index=True)
    rating = models.IntegerField(default=1200)
    daily = models.BooleanField(default=False, db_index=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['daily', 'difficulty']),
            models.Index(fields=['category', 'difficulty']),
        ]
    
    def __str__(self):
        return f"Puzzle {self.id} - {self.category}"


class PlayerPuzzle(models.Model):
    player = models.ForeignKey(PlayerProfile, on_delete=models.CASCADE)
    puzzle = models.ForeignKey(Puzzle, on_delete=models.CASCADE)
    solved = models.BooleanField(default=False)
    attempts = models.IntegerField(default=0)
    solved_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ['player', 'puzzle']


class Leaderboard(models.Model):
    player = models.ForeignKey(PlayerProfile, on_delete=models.CASCADE)
    weekly_rank = models.IntegerField(default=0)
    monthly_rank = models.IntegerField(default=0)
    all_time_rank = models.IntegerField(default=0)
    weekly_points = models.IntegerField(default=0)
    monthly_points = models.IntegerField(default=0)
    all_time_points = models.IntegerField(default=0)
    
    def __str__(self):
        return f"{self.player.user.username} - Rank: {self.weekly_rank}"


class Friend(models.Model):
    from_user = models.ForeignKey(PlayerProfile, related_name='friends', on_delete=models.CASCADE)
    to_user = models.ForeignKey(PlayerProfile, related_name='friend_requests', on_delete=models.CASCADE)
    accepted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['from_user', 'to_user']


class Message(models.Model):
    sender = models.ForeignKey(PlayerProfile, related_name='sent_messages', on_delete=models.CASCADE, db_index=True)
    receiver = models.ForeignKey(PlayerProfile, related_name='received_messages', on_delete=models.CASCADE, db_index=True)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    read = models.BooleanField(default=False, db_index=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['receiver', '-created_at']),
            models.Index(fields=['sender', '-created_at']),
            models.Index(fields=['receiver', 'read', '-created_at']),
        ]
    
    def __str__(self):
        return f"Message from {self.sender.user.username} to {self.receiver.user.username}"


class AcademyNews(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    image = models.ImageField(upload_to='news/', blank=True, null=True)
    published_at = models.DateTimeField(auto_now_add=True, db_index=True)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    
    class Meta:
        ordering = ['-published_at']
        indexes = [
            models.Index(fields=['-published_at']),
        ]
    
    def __str__(self):
        return self.title


class MultiplayerGame(models.Model):
    GAME_TYPE_CHOICES = [
        ('standard', 'Standard Chess'),
        ('blitz', 'Blitz (5+0)'),
        ('rapid', 'Rapid (10+0)'),
        ('classical', 'Classical (30+0)'),
    ]
    
    STATUS_CHOICES = [
        ('waiting', 'Waiting for opponent'),
        ('playing', 'Game in progress'),
        ('completed', 'Game completed'),
        ('abandoned', 'Game abandoned'),
    ]
    
    RESULT_CHOICES = [
        ('white', 'White wins'),
        ('black', 'Black wins'),
        ('draw', 'Draw'),
        ('resignation', 'Resignation'),
        ('timeout', 'Timeout'),
        ('abandoned', 'Abandoned'),
    ]
    
    VISIBILITY_CHOICES = [
        ('private', 'Private'),
        ('public', 'Public'),
    ]
    
    game_code = models.CharField(max_length=8, unique=True, db_index=True)
    white_player = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='white_games', on_delete=models.CASCADE, db_index=True)
    black_player = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='black_games', on_delete=models.CASCADE, null=True, blank=True, db_index=True)
    game_type = models.CharField(max_length=20, choices=GAME_TYPE_CHOICES, default='standard')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='waiting', db_index=True)
    result = models.CharField(max_length=20, choices=RESULT_CHOICES, null=True, blank=True)
    current_fen = models.TextField(default='rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1')
    pgn = models.TextField(blank=True)
    visibility = models.CharField(max_length=20, choices=VISIBILITY_CHOICES, default='private')
    rated = models.BooleanField(default=False)
    color_preference = models.CharField(max_length=10, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Chess clock fields
    white_time = models.IntegerField(default=600)  # Remaining time in seconds for white (default 10 minutes)
    black_time = models.IntegerField(default=600)  # Remaining time in seconds for black (default 10 minutes)
    last_move_timestamp = models.DateTimeField(null=True, blank=True)  # Timestamp of last move
    active_clock = models.CharField(max_length=10, default='white', choices=[('white', 'White'), ('black', 'Black')])  # Whose clock is running
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['white_player', 'status']),
            models.Index(fields=['black_player', 'status']),
        ]
    
    def __str__(self):
        return f"Game {self.game_code} - {self.white_player.username} vs {self.black_player.username if self.black_player else 'Waiting'}"
    
    def get_game_type_display(self):
        return dict(self.GAME_TYPE_CHOICES).get(self.game_type, self.game_type)


class GameMove(models.Model):
    game = models.ForeignKey(MultiplayerGame, related_name='moves', on_delete=models.CASCADE, db_index=True)
    player = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, db_index=True)
    move_from = models.CharField(max_length=2)
    move_to = models.CharField(max_length=2)
    piece = models.CharField(max_length=1)
    captured_piece = models.CharField(max_length=1, null=True, blank=True)
    promotion = models.CharField(max_length=1, null=True, blank=True)
    castling = models.CharField(max_length=10, null=True, blank=True)
    en_passant = models.BooleanField(default=False)
    is_check = models.BooleanField(default=False)
    is_checkmate = models.BooleanField(default=False)
    fen_after = models.TextField()
    move_number = models.IntegerField()
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['move_number']
        indexes = [
            models.Index(fields=['game', 'move_number']),
        ]
    
    def __str__(self):
        return f"Move {self.move_number}: {self.move_from} -> {self.move_to}"


class VideoLesson(models.Model):
    title = models.CharField(max_length=200, db_index=True)
    description = models.TextField()
    youtube_id = models.CharField(max_length=20, unique=True)  # YouTube video ID
    thumbnail_url = models.URLField(max_length=500, blank=True, default='')
    channel_name = models.CharField(max_length=100)
    duration = models.CharField(max_length=20, blank=True, default='')  # e.g., "10:30"
    category = models.CharField(max_length=50, choices=[
        ('openings', 'Openings'),
        ('middlegame', 'Middlegame'),
        ('endgames', 'Endgames'),
        ('tactics', 'Tactics'),
        ('strategy', 'Strategy'),
    ], db_index=True)
    difficulty = models.CharField(max_length=20, choices=[
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
    ], db_index=True)
    views = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    order = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['order', '-created_at']
        indexes = [
            models.Index(fields=['category', 'difficulty', 'order']),
            models.Index(fields=['title']),
        ]
    
    def __str__(self):
        return self.title


