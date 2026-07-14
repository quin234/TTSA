from django.contrib import admin
from .models import YouTubeChannel, Tournament, TournamentPlayer, TournamentGame


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


@admin.register(Tournament)
class TournamentAdmin(admin.ModelAdmin):
    """Admin interface for Tournament model"""
    list_display = ['name', 'venue', 'category', 'format', 'start_date', 'status', 'current_players', 'max_players', 'created_by']
    list_filter = ['category', 'format', 'status', 'is_active', 'is_featured', 'start_date', 'created_at']
    search_fields = ['name', 'venue', 'description']
    readonly_fields = ['created_at', 'updated_at', 'current_players']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'venue')
        }),
        ('Tournament Details', {
            'fields': ('category', 'format', 'rounds', 'time_control')
        }),
        ('Schedule', {
            'fields': ('start_date', 'end_date', 'registration_deadline')
        }),
        ('Registration', {
            'fields': ('entry_fee', 'max_players', 'current_players')
        }),
        ('Status', {
            'fields': ('status', 'is_active', 'is_featured')
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not change:  # Only set created_by on creation
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(TournamentPlayer)
class TournamentPlayerAdmin(admin.ModelAdmin):
    """Admin interface for TournamentPlayer model"""
    list_display = ['player_name', 'tournament', 'rating', 'category', 'points', 'wins', 'losses', 'draws', 'status', 'rank']
    list_filter = ['category', 'status', 'tournament', 'registered_at']
    search_fields = ['player_name', 'email']
    readonly_fields = ['registered_at', 'updated_at']
    ordering = ['-tournament', '-points']
    
    fieldsets = (
        ('Player Information', {
            'fields': ('tournament', 'player_name', 'rating', 'email', 'phone', 'category')
        }),
        ('Tournament Statistics', {
            'fields': ('points', 'wins', 'losses', 'draws', 'rank')
        }),
        ('Tie-break Scores', {
            'fields': ('buchholz', 'sonneborn_berger')
        }),
        ('Status', {
            'fields': ('status',)
        }),
        ('Timestamps', {
            'fields': ('registered_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(TournamentGame)
class TournamentGameAdmin(admin.ModelAdmin):
    """Admin interface for TournamentGame model"""
    list_display = ['tournament', 'round_number', 'board_number', 'white_player', 'black_player', 'result', 'status', 'scheduled_time']
    list_filter = ['tournament', 'round_number', 'status', 'result', 'scheduled_time']
    search_fields = ['white_player__player_name', 'black_player__player_name']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['tournament', 'round_number', 'board_number']
    
    fieldsets = (
        ('Game Information', {
            'fields': ('tournament', 'round_number', 'board_number')
        }),
        ('Players', {
            'fields': ('white_player', 'black_player')
        }),
        ('Result', {
            'fields': ('result', 'status')
        }),
        ('Timing', {
            'fields': ('scheduled_time', 'started_at', 'completed_at')
        }),
        ('Game Data', {
            'fields': ('pgn', 'moves_count')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
