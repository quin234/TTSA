from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.db.models import Q, Count, Sum, Avg, F, Max
from django.utils import timezone
from django.views.decorators.cache import cache_page
from django.core.cache import cache
from functools import wraps
import logging

logger = logging.getLogger(__name__)
from .forms import (
    YouTubeChannelForm, VideoLessonForm, TournamentForm, 
    TournamentPlayerForm, TournamentGameForm, TournamentSearchForm
)
from .models import YouTubeChannel, SyncNotification, Tournament, TournamentPlayer, TournamentGame, TournamentRound, TournamentStanding, TournamentResult
from .youtube_utils import validate_and_fetch_channel_metadata, YouTubeChannelError, fetch_channel_videos
from ttsa_app.models import VideoLesson, User, PlayerProfile, ChessGame, MultiplayerGame
from .youtube_utils import validate_and_fetch_video_metadata, YouTubeVideoError
from django.db import transaction
from django.core.exceptions import ValidationError


def ttsa_admin_required(view_func):
    """Decorator for views that require TTSA Admin role."""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'success': False, 'error': 'Authentication required'}, status=401)
        if not request.user.is_ttsa_admin:
            return JsonResponse({'success': False, 'error': 'TTSA Admin access required'}, status=403)
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def tournament_manager_required(view_func):
    """Decorator for views that require tournament management permissions (PLAYER_PLUS or TTSA Admin)."""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'success': False, 'error': 'Authentication required'}, status=401)
        if not request.user.can_manage_tournaments:
            return JsonResponse({'success': False, 'error': 'You do not have permission to manage tournaments. Upgrade to PLAYER_PLUS to create and manage tournaments.'}, status=403)
        return view_func(request, *args, **kwargs)
    return _wrapped_view


@login_required
def admin_dashboard(request):
    """Main dashboard view for TTSA admin portal"""
    if not request.user.is_ttsa_admin:
        messages.error(request, 'You do not have permission to access the admin dashboard.')
        return redirect('dashboard')
    
    from django.db.models import Count, Q
    from datetime import datetime, timedelta
    from .models import Tournament, TournamentPlayer
    from ttsa_app.models import PlayerProfile, ChessGame, MultiplayerGame
    
    # Get statistics
    total_users = User.objects.count()
    active_players = PlayerProfile.objects.filter(
        last_played__gte=timezone.now() - timedelta(days=30)
    ).count()
    
    # Games today (both single player and multiplayer)
    today = timezone.now().date()
    games_today = ChessGame.objects.filter(created_at__date=today).count() + \
                  MultiplayerGame.objects.filter(created_at__date=today).count()
    
    # Get upcoming tournaments (ongoing, upcoming, and completed tournaments)
    upcoming_tournaments = Tournament.objects.select_related('created_by').filter(
        status__in=['ongoing', 'upcoming', 'completed']
    ).order_by('start_date')[:10]
    
    # Add empty tournament form for creation
    from .forms import TournamentForm
    form = TournamentForm()
    
    context = {
        'user': request.user,
        'form': form,
        'total_users': total_users,
        'active_players': active_players,
        'games_today': games_today,
        'upcoming_tournaments': upcoming_tournaments,
        'show_tournament_form': False,  # Don't show form by default
    }
    return render(request, 'ttsaadmin/dashboard.html', context)


@login_required
def add_youtube_channel(request):
    """View for adding a YouTube channel"""
    if not request.user.is_ttsa_admin:
        messages.error(request, 'You do not have permission to add YouTube channels.')
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = YouTubeChannelForm(request.POST)
        if form.is_valid():
            try:
                channel = form.save()
                
                # Return JSON if requested via AJAX
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': True, 'message': f'Successfully added YouTube channel: {channel.channel_name}'})
                
                messages.success(
                    request,
                    f'Successfully added YouTube channel: {channel.channel_name}'
                )
                return redirect('youtube_channels_list')
            except Exception as e:
                # Return JSON if requested via AJAX
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'error': str(e)})
                
                messages.error(
                    request,
                    f'Error saving channel: {str(e)}'
                )
        else:
            # Return JSON if requested via AJAX
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                errors = {field: errors[0] for field, errors in form.errors.items()}
                return JsonResponse({'success': False, 'error': 'Please correct the errors in the form.', 'errors': errors})
            
            messages.error(
                request,
                'Please correct the errors in the form.'
            )
    else:
        form = YouTubeChannelForm()
    
    context = {
        'form': form,
        'user': request.user,
    }
    return render(request, 'ttsaadmin/add_youtube_channel.html', context)


@login_required
def youtube_channels_list(request):
    """View for listing all YouTube channels"""
    channels = YouTubeChannel.objects.filter(is_active=True).order_by('-created_at')
    
    # Return JSON if requested via AJAX
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        channels_data = [{
            'id': channel.id,
            'channel_id': channel.channel_id,
            'channel_url': channel.channel_url,
            'channel_name': channel.channel_name,
            'channel_description': channel.channel_description,
            'channel_thumbnail_url': channel.channel_thumbnail_url,
            'video_count': channel.video_count,
            'view_count': channel.view_count,
            'created_at': channel.created_at.isoformat(),
        } for channel in channels]
        return JsonResponse({'channels': channels_data})
    
    # For non-AJAX requests, redirect to dashboard since channels are now integrated there
    from django.shortcuts import redirect
    return redirect('admin_dashboard')


@csrf_exempt
@login_required
def validate_channel_api(request):
    """API endpoint for validating YouTube channel before submission"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Only POST method allowed'})
    
    try:
        import json
        data = json.loads(request.body)
        channel_url = data.get('channel_url')
        
        if not channel_url:
            return JsonResponse({'success': False, 'error': 'Channel URL is required'})
        
        # Validate and fetch metadata
        channel_metadata = validate_and_fetch_channel_metadata(channel_url)
        
        # Check if channel already exists
        if YouTubeChannel.objects.filter(channel_id=channel_metadata['channel_id']).exists():
            return JsonResponse({'success': False, 'error': 'This YouTube channel has already been added'})
        
        return JsonResponse({
            'success': True,
            'channel_id': channel_metadata['channel_id'],
            'channel_url': channel_metadata['channel_url'],
            'channel_name': channel_metadata['channel_name'],
            'channel_description': channel_metadata['channel_description'],
            'channel_thumbnail_url': channel_metadata['channel_thumbnail_url'],
            'video_count': channel_metadata['video_count'],
        })
        
    except YouTubeChannelError as e:
        return JsonResponse({'success': False, 'error': str(e)})
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'An error occurred: {str(e)}'})


@login_required
def add_video_lesson(request):
    """View for adding a YouTube video lesson"""
    if not request.user.is_ttsa_admin:
        messages.error(request, 'You do not have permission to add video lessons.')
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = VideoLessonForm(request.POST)
        if form.is_valid():
            try:
                video = form.save()
                
                # Return JSON if requested via AJAX
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': True, 'message': f'Successfully added video lesson: {video.title}'})
                
                messages.success(
                    request,
                    f'Successfully added video lesson: {video.title}'
                )
                return redirect('video_library')
            except Exception as e:
                # Return JSON if requested via AJAX
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'error': str(e)})
                
                messages.error(
                    request,
                    f'Error saving video: {str(e)}'
                )
        else:
            # Return JSON if requested via AJAX
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                errors = {field: errors[0] for field, errors in form.errors.items()}
                return JsonResponse({'success': False, 'error': 'Please correct the errors in the form.', 'errors': errors})
            
            messages.error(
                request,
                'Please correct the errors in the form.'
            )
    else:
        form = VideoLessonForm()
    
    context = {
        'form': form,
        'user': request.user,
    }
    return render(request, 'ttsaadmin/add_video_lesson.html', context)


@login_required
def video_library(request):
    """View for listing all video lessons with pagination"""
    videos = VideoLesson.objects.all().order_by('order', '-created_at')
    
    # Return JSON if requested via AJAX
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        # Get pagination parameters
        page = int(request.GET.get('page', 1))
        per_page = int(request.GET.get('per_page', 10))
        
        # Apply pagination
        paginator = Paginator(videos, per_page)
        videos_page = paginator.get_page(page)
        
        videos_data = [{
            'id': video.id,
            'title': video.title,
            'description': video.description,
            'youtube_id': video.youtube_id,
            'thumbnail_url': video.thumbnail_url,
            'channel_name': video.channel_name,
            'duration': video.duration,
            'category': video.category,
            'difficulty': video.difficulty,
            'views': video.views,
            'created_at': video.created_at.isoformat(),
        } for video in videos_page]
        
        return JsonResponse({
            'videos': videos_data,
            'has_next': videos_page.has_next(),
            'has_previous': videos_page.has_previous(),
            'current_page': page,
            'total_pages': paginator.num_pages,
            'total_count': paginator.count
        })
    
    # For non-AJAX requests, redirect to dashboard since videos are now integrated there
    from django.shortcuts import redirect
    return redirect('admin_dashboard')


@csrf_exempt
@login_required
def validate_video_api(request):
    """API endpoint for validating YouTube video before submission"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Only POST method allowed'})
    
    try:
        import json
        data = json.loads(request.body)
        video_url = data.get('video_url')
        
        if not video_url:
            return JsonResponse({'success': False, 'error': 'Video URL is required'})
        
        # Check if video already exists
        from .youtube_utils import extract_video_id
        video_id = extract_video_id(video_url)
        if video_id and VideoLesson.objects.filter(youtube_id=video_id).exists():
            return JsonResponse({'success': False, 'error': 'This YouTube video has already been added'})
        
        # Validate and fetch metadata
        video_metadata = validate_and_fetch_video_metadata(video_url)
        
        return JsonResponse({
            'success': True,
            'video_id': video_metadata['video_id'],
            'video_url': video_metadata['video_url'],
            'title': video_metadata['title'],
            'description': video_metadata.get('description', ''),
            'channel_name': video_metadata.get('channel_name', video_metadata.get('author_name', '')),
            'thumbnail_url': video_metadata['thumbnail_url'],
            'duration': video_metadata.get('duration', ''),
        })
        
    except YouTubeVideoError as e:
        return JsonResponse({'success': False, 'error': str(e)})
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'An error occurred: {str(e)}'})


@csrf_exempt
@login_required
def delete_video_lesson(request, video_id):
    """API endpoint for deleting a video lesson"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Only POST method allowed'})
    
    try:
        video = VideoLesson.objects.get(id=video_id)
        video.delete()
        
        # Return JSON if requested via AJAX
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'message': 'Video deleted successfully'})
        
        messages.success(request, 'Video deleted successfully')
        return redirect('video_library')
        
    except VideoLesson.DoesNotExist:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': 'Video not found'})
        
        messages.error(request, 'Video not found')
        return redirect('video_library')
    except Exception as e:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': str(e)})
        
        messages.error(request, f'Error deleting video: {str(e)}')
        return redirect('video_library')


@csrf_exempt
@login_required
def delete_youtube_channel(request, channel_id):
    """API endpoint for deleting a YouTube channel"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Only POST method allowed'})
    
    try:
        channel = YouTubeChannel.objects.get(id=channel_id)
        channel.delete()
        
        # Return JSON if requested via AJAX
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'message': 'Channel deleted successfully'})
        
        messages.success(request, 'Channel deleted successfully')
        return redirect('youtube_channels_list')
        
    except YouTubeChannel.DoesNotExist:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': 'Channel not found'})
        
        messages.error(request, 'Channel not found')
        return redirect('youtube_channels_list')
    except Exception as e:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': str(e)})
        
        messages.error(request, f'Error deleting channel: {str(e)}')
        return redirect('youtube_channels_list')


@csrf_exempt
@login_required
def sync_channel_videos(request):
    """API endpoint to sync videos from YouTube channels (limited to 100 videos)"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Only POST method allowed'})
    
    try:
        import json
        data = json.loads(request.body)
        channel_id = data.get('channel_id')
        category = data.get('category', 'strategy')
        difficulty = data.get('difficulty', 'intermediate')
        
        # Validate category and difficulty
        valid_categories = ['openings', 'middlegame', 'endgames', 'tactics', 'strategy']
        valid_difficulties = ['beginner', 'intermediate', 'advanced']
        
        if category not in valid_categories:
            return JsonResponse({'success': False, 'error': f'Invalid category. Valid options: {valid_categories}'})
        
        if difficulty not in valid_difficulties:
            return JsonResponse({'success': False, 'error': f'Invalid difficulty. Valid options: {valid_difficulties}'})
        
        # Get channel
        try:
            channel = YouTubeChannel.objects.get(channel_id=channel_id, is_active=True)
        except YouTubeChannel.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Channel not found or not active'})
        
        # Sync videos synchronously with 100 video limit
        from .youtube_utils import fetch_channel_videos, YouTubeChannelError
        
        try:
            # Fetch up to 100 videos from YouTube API
            videos = fetch_channel_videos(channel.channel_id, max_results=100)
            
            added_count = 0
            skipped_count = 0
            
            for video_data in videos:
                try:
                    # Check if video already exists
                    if VideoLesson.objects.filter(youtube_id=video_data['video_id']).exists():
                        skipped_count += 1
                        continue
                    
                    # Create VideoLesson
                    with transaction.atomic():
                        video_lesson = VideoLesson.objects.create(
                            title=video_data['title'],
                            description=video_data['description'][:500],
                            youtube_id=video_data['video_id'],
                            thumbnail_url=video_data['thumbnail_url'],
                            channel_name=video_data['channel_name'],
                            duration='',
                            category=category,
                            difficulty=difficulty,
                            views=0,
                            order=0,
                        )
                        added_count += 1
                        
                except Exception as e:
                    continue
            
            return JsonResponse({
                'success': True,
                'message': f'Sync completed. Added {added_count} videos, skipped {skipped_count} existing videos.',
                'videos_added': added_count,
                'videos_skipped': skipped_count
            })
            
        except YouTubeChannelError as e:
            return JsonResponse({'success': False, 'error': f'Error fetching videos: {str(e)}'})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'An error occurred: {str(e)}'})


@csrf_exempt
@login_required
def get_notifications(request):
    """API endpoint to get user notifications"""
    if request.method != 'GET':
        return JsonResponse({'success': False, 'error': 'Only GET method allowed'})
    
    try:
        notifications = SyncNotification.objects.filter(
            user=request.user,
            is_read=False
        ).order_by('-created_at')[:10]
        
        notifications_data = [{
            'id': notification.id,
            'type': notification.notification_type,
            'title': notification.title,
            'message': notification.message,
            'channel_name': notification.channel_name,
            'video_title': notification.video_title,
            'videos_added': notification.videos_added,
            'videos_skipped': notification.videos_skipped,
            'created_at': notification.created_at.isoformat(),
        } for notification in notifications]
        
        unread_count = SyncNotification.objects.filter(user=request.user, is_read=False).count()
        
        return JsonResponse({
            'success': True,
            'notifications': notifications_data,
            'unread_count': unread_count
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'An error occurred: {str(e)}'})


@csrf_exempt
@login_required
def mark_notification_read(request, notification_id):
    """API endpoint to mark notification as read"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Only POST method allowed'})
    
    try:
        notification = SyncNotification.objects.get(id=notification_id, user=request.user)
        notification.is_read = True
        notification.save()
        
        return JsonResponse({'success': True})
        
    except SyncNotification.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Notification not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'An error occurred: {str(e)}'})


# Tournament Management Views

@login_required
def tournament_list(request):
    """View for listing tournaments with search, filtering, and pagination"""
    search_form = TournamentSearchForm(request.GET)
    tournaments = Tournament.objects.select_related('created_by').prefetch_related('players')
    
    # Apply filters
    if search_form.is_valid():
        cleaned_data = search_form.cleaned_data
        
        # Search
        search = cleaned_data.get('search')
        if search:
            tournaments = tournaments.filter(
                Q(name__icontains=search) |
                Q(venue__icontains=search) |
                Q(description__icontains=search)
            )
        
        # Category filter
        category = cleaned_data.get('category')
        if category:
            tournaments = tournaments.filter(category=category)
        
        # Status filter
        status = cleaned_data.get('status')
        if status:
            tournaments = tournaments.filter(status=status)
        
        # Date range filter
        date_from = cleaned_data.get('date_from')
        if date_from:
            tournaments = tournaments.filter(start_date__date__gte=date_from)
        
        date_to = cleaned_data.get('date_to')
        if date_to:
            tournaments = tournaments.filter(start_date__date__lte=date_to)
        
        # Sorting
        sort_by = cleaned_data.get('sort_by', '-created_at')
        tournaments = tournaments.order_by(sort_by)
    
    # Pagination
    paginator = Paginator(tournaments, 12)  # 12 tournaments per page
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_form': search_form,
        'total_tournaments': tournaments.count(),
    }
    
    # Return JSON if requested via AJAX
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        tournaments_data = []
        for tournament in page_obj:
            tournaments_data.append({
                'id': tournament.id,
                'name': tournament.name,
                'venue': tournament.venue,
                'category': tournament.category,
                'format': tournament.format,
                'rounds': tournament.rounds,
                'time_control': tournament.time_control,
                'start_date': tournament.start_date.isoformat(),
                'end_date': tournament.end_date.isoformat(),
                'registration_deadline': tournament.registration_deadline.isoformat(),
                'entry_fee': float(tournament.entry_fee),
                'max_players': tournament.max_players,
                'current_players': tournament.registered_players_count,
                'available_slots': tournament.available_slots,
                'status': tournament.status,
                'is_active': tournament.is_active,
                'is_featured': tournament.is_featured,
                'created_by': tournament.created_by.username,
                'created_at': tournament.created_at.isoformat(),
                'updated_at': tournament.updated_at.isoformat(),
            })
        
        return JsonResponse({
            'success': True,
            'tournaments': tournaments_data,
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous(),
            'num_pages': page_obj.paginator.num_pages,
            'current_page': page_obj.number,
            'total_count': tournaments.count(),
        })
    
    return render(request, 'ttsaadmin/tournament_list.html', context)


@login_required
def tournament_create(request):
    """View for creating new tournaments"""
    if not request.user.can_manage_tournaments:
        messages.error(request, 'You do not have permission to create tournaments. Upgrade to PLAYER_PLUS to create and manage tournaments.')
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = TournamentForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    tournament = form.save(commit=False)
                    tournament.created_by = request.user
                    tournament.current_players = 0
                    tournament.save()
                    
                    # Return JSON if requested via AJAX
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse({
                            'success': True,
                            'message': f'Tournament "{tournament.name}" has been created successfully!'
                        })
                    
                    messages.success(
                        request, 
                        f'Tournament "{tournament.name}" has been created successfully!'
                    )
                    return redirect('admin_dashboard')
                    
            except Exception as e:
                # Return JSON if requested via AJAX
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False,
                        'error': f'An error occurred while creating the tournament: {str(e)}'
                    })
                
                messages.error(
                    request,
                    f'An error occurred while creating the tournament: {str(e)}'
                )
        else:
            # Return JSON if requested via AJAX
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'error': 'Please correct the errors below and try again.',
                    'errors': form.errors
                })
            
            messages.error(
                request,
                'Please correct the errors below and try again.'
            )
    else:
        form = TournamentForm()
    
    # Get dashboard context
    from django.db.models import Count, Q
    from datetime import datetime, timedelta
    from .models import Tournament, TournamentPlayer
    from ttsa_app.models import PlayerProfile, ChessGame, MultiplayerGame
    
    # Get statistics
    total_users = User.objects.count()
    active_players = PlayerProfile.objects.filter(
        last_played__gte=timezone.now() - timedelta(days=30)
    ).count()
    
    # Games today (both single player and multiplayer)
    today = timezone.now().date()
    games_today = ChessGame.objects.filter(created_at__date=today).count() + \
                  MultiplayerGame.objects.filter(created_at__date=today).count()
    
    # Get upcoming tournaments
    upcoming_tournaments = Tournament.objects.select_related('created_by').filter(
        status__in=['ongoing', 'upcoming', 'completed']
    ).order_by('start_date')[:10]
    
    context = {
        'form': form,
        'total_users': total_users,
        'active_players': active_players,
        'games_today': games_today,
        'upcoming_tournaments': upcoming_tournaments,
        'show_tournament_form': True  # Flag to show the tournament form on load
    }
    
    return render(request, 'ttsaadmin/dashboard.html', context)


@login_required
def tournament_detail(request, tournament_id):
    """View for tournament details"""
    tournament = get_object_or_404(
        Tournament.objects.select_related('created_by').prefetch_related('players', 'games'),
        id=tournament_id
    )
    
    # Get tournament statistics
    players = tournament.players.filter(status='confirmed').order_by('-points', '-buchholz', '-sonneborn_berger')
    games = tournament.games.select_related('white_player', 'black_player').order_by('round_number', 'board_number')
    
    # Calculate statistics
    total_games = games.count()
    completed_games = games.filter(status='completed').count()
    current_round = games.aggregate(max_round=Max('round_number'))['max_round'] or 0
    
    context = {
        'tournament': tournament,
        'players': players,
        'games': games,
        'total_games': total_games,
        'completed_games': completed_games,
        'current_round': current_round,
    }
    
    return render(request, 'ttsaadmin/tournament_detail.html', context)


@login_required
def tournament_edit(request, tournament_id):
    """View for editing a tournament"""
    
    if not request.user.can_manage_tournaments:
        messages.error(request, 'You do not have permission to edit tournaments.')
        return redirect('dashboard')
    
    from .models import Tournament, TournamentPlayer
    from ttsa_app.models import PlayerProfile, ChessGame, MultiplayerGame
    
    tournament = get_object_or_404(Tournament, id=tournament_id)
    
    if request.method == 'POST':
        form = TournamentForm(request.POST, instance=tournament)
        if form.is_valid():
            try:
                tournament = form.save()
                
                # Return JSON if requested via AJAX
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': True, 
                        'message': f'Tournament "{tournament.name}" updated successfully!'
                    })
                
                messages.success(request, f'Tournament "{tournament.name}" updated successfully!')
                return redirect('admin_dashboard')
                
            except Exception as e:
                # Return JSON if requested via AJAX
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'error': str(e)})
                
                messages.error(request, f'Error updating tournament: {str(e)}')
        else:
            # Return JSON if requested via AJAX
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False, 
                    'error': 'Form validation failed',
                    'errors': form.errors
                })
            
            messages.error(request, 'Please correct the errors below and try again.')
    else:
        form = TournamentForm(instance=tournament)
    
    # Get dashboard context
    from django.db.models import Count, Q
    from datetime import datetime, timedelta
    
    # Get statistics
    total_users = User.objects.count()
    active_players = PlayerProfile.objects.filter(
        last_played__gte=timezone.now() - timedelta(days=30)
    ).count()
    
    # Games today (both single player and multiplayer)
    today = timezone.now().date()
    games_today = ChessGame.objects.filter(created_at__date=today).count() + \
                  MultiplayerGame.objects.filter(created_at__date=today).count()
    
    # Get upcoming tournaments
    upcoming_tournaments = Tournament.objects.select_related('created_by').filter(
        status__in=['ongoing', 'upcoming', 'completed']
    ).order_by('start_date')[:10]
    
    context = {
        'form': form,
        'total_users': total_users,
        'active_players': active_players,
        'games_today': games_today,
        'upcoming_tournaments': upcoming_tournaments,
        'show_tournament_form': True,  # Flag to show the tournament form on load
        'edit_tournament': tournament  # Pass tournament data for edit mode
    }
    
    return render(request, 'ttsaadmin/dashboard.html', context)


@require_POST
def tournament_delete(request, tournament_id):
    """View for deleting a tournament"""
    
    # Check if user is authenticated for API requests
    if not request.user.is_authenticated:
        return JsonResponse({
            'success': False, 
            'error': 'Authentication required'
        }, status=401)
    
    if not request.user.can_manage_tournaments:
        return JsonResponse({
            'success': False,
            'error': 'You do not have permission to delete tournaments.'
        }, status=403)
    
    tournament = get_object_or_404(Tournament, id=tournament_id)
    
    try:
        tournament_name = tournament.name
        tournament.delete()
        
        # Return JSON if requested via AJAX
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True, 
                'message': f'Tournament "{tournament_name}" deleted successfully!'
            })
        
        messages.success(request, f'Tournament "{tournament_name}" deleted successfully!')
        return redirect('tournament_list')
        
    except Exception as e:
        # Return JSON if requested via AJAX
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': str(e)})
        
        messages.error(request, f'Error deleting tournament: {str(e)}')
        return redirect('tournament_detail', tournament_id=tournament_id)


def tournament_players(request, tournament_id):
    """View for managing tournament players"""
    
    # Check if user is authenticated for API requests
    if not request.user.is_authenticated:
        return JsonResponse({
            'success': False, 
            'error': 'Authentication required'
        }, status=401)
    
    if not request.user.can_manage_tournaments:
        return JsonResponse({
            'success': False,
            'error': 'You do not have permission to manage tournament players.'
        }, status=403)
    
    tournament = get_object_or_404(Tournament, id=tournament_id)
    players = tournament.players.select_related('tournament').order_by('-points', '-buchholz', '-sonneborn_berger')
    
    if request.method == 'POST':
        form = TournamentPlayerForm(request.POST)
        if form.is_valid():
            try:
                player = form.save(commit=False)
                player.tournament = tournament
                player.save()
                
                # Update tournament player count
                tournament.current_players = tournament.players.filter(status='registered').count()
                tournament.save()
                
                # Return JSON if requested via AJAX
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': True, 
                        'message': f'Player "{player.player_name}" added successfully!',
                        'player': {
                            'id': player.id,
                            'player_name': player.player_name,
                            'rating': player.rating,
                            'points': float(player.points),
                            'wins': player.wins,
                            'losses': player.losses,
                            'draws': player.draws,
                            'status': player.status,
                        }
                    })
                
                messages.success(request, f'Player "{player.player_name}" added successfully!')
                return redirect('tournament_players', tournament_id=tournament_id)
                
            except Exception as e:
                # Return JSON if requested via AJAX
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'error': str(e)})
                
                messages.error(request, f'Error adding player: {str(e)}')
        else:
            # Return JSON if requested via AJAX
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False, 
                    'error': 'Form validation failed',
                    'errors': form.errors
                })
    else:
        form = TournamentPlayerForm()
    
    context = {
        'tournament': tournament,
        'players': players,
        'form': form,
    }
    
    return render(request, 'ttsaadmin/tournament_players.html', context)


@require_POST
def tournament_remove_player(request, tournament_id, player_id):
    """View for removing a player from tournament"""
    
    # Check if user is authenticated for API requests
    if not request.user.is_authenticated:
        return JsonResponse({
            'success': False, 
            'error': 'Authentication required'
        }, status=401)
    
    if not request.user.can_manage_tournaments:
        return JsonResponse({
            'success': False,
            'error': 'You do not have permission to remove tournament players.'
        }, status=403)
    
    tournament = get_object_or_404(Tournament, id=tournament_id)
    player = get_object_or_404(TournamentPlayer, id=player_id, tournament=tournament)
    
    try:
        player_name = player.player_name
        player.delete()
        
        # Update tournament player count
        tournament.current_players = tournament.players.count()
        tournament.save()
        
        # Return JSON if requested via AJAX
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True, 
                'message': f'Player "{player_name}" removed successfully!'
            })
        
        messages.success(request, f'Player "{player_name}" removed successfully!')
        return redirect('tournament_players', tournament_id=tournament_id)
        
    except Exception as e:
        # Return JSON if requested via AJAX
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': str(e)})
        
        messages.error(request, f'Error removing player: {str(e)}')
        return redirect('tournament_players', tournament_id=tournament_id)


@login_required
def tournament_games(request, tournament_id):
    """View for managing tournament games"""
    if not request.user.can_manage_tournaments:
        messages.error(request, 'You do not have permission to manage tournament games.')
        return redirect('dashboard')
    
    tournament = get_object_or_404(Tournament, id=tournament_id)
    games = tournament.games.select_related('white_player', 'black_player').order_by('round_number', 'board_number')
    
    # Group games by round
    rounds = {}
    for game in games:
        round_num = game.round_number
        if round_num not in rounds:
            rounds[round_num] = []
        rounds[round_num].append(game)
    
    context = {
        'tournament': tournament,
        'rounds': rounds,
        'current_round': max(rounds.keys()) if rounds else 0,
    }
    
    return render(request, 'ttsaadmin/tournament_games.html', context)


@login_required
@require_POST
def tournament_update_game_result(request, tournament_id, game_id):
    """View for updating game result"""
    if not request.user.can_manage_tournaments:
        return JsonResponse({'success': False, 'error': 'You do not have permission to update game results.'}, status=403)
    
    tournament = get_object_or_404(Tournament, id=tournament_id)
    game = get_object_or_404(TournamentGame, id=game_id, tournament=tournament)
    
    try:
        result = request.POST.get('result')
        if result in dict(TournamentGame.RESULT_CHOICES):
            game.result = result
            if result != '*':
                game.status = 'completed'
                game.completed_at = timezone.now()
            game.save()
            
            # Update player statistics
            update_player_statistics(tournament)
            
            # Return JSON if requested via AJAX
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True, 
                    'message': 'Game result updated successfully!'
                })
            
            messages.success(request, 'Game result updated successfully!')
        else:
            raise ValidationError('Invalid result')
            
    except Exception as e:
        # Return JSON if requested via AJAX
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': str(e)})
        
        messages.error(request, f'Error updating game result: {str(e)}')
    
    return redirect('tournament_games', tournament_id=tournament_id)


def update_player_statistics(tournament):
    """Update player statistics based on game results"""
    from django.db.models import Max
    
    players = tournament.players.all()
    
    for player in players:
        # Reset statistics
        player.wins = 0
        player.losses = 0
        player.draws = 0
        player.points = 0
        
        # Calculate from games
        white_games = tournament.games.filter(white_player=player, status='completed')
        black_games = tournament.games.filter(black_player=player, status='completed')
        
        for game in white_games:
            if game.result == '1-0':
                player.wins += 1
                player.points += 1
            elif game.result == '0-1':
                player.losses += 1
            elif game.result == '½-½':
                player.draws += 1
                player.points += 0.5
        
        for game in black_games:
            if game.result == '1-0':
                player.losses += 1
            elif game.result == '0-1':
                player.wins += 1
                player.points += 1
            elif game.result == '½-½':
                player.draws += 1
                player.points += 0.5
        
        player.save()
    
    # Update rankings and tie-breaks (simplified version)
    ranked_players = players.filter(status='confirmed').order_by('-points', '-buchholz', '-sonneborn_berger', 'player_name')
    for rank, player in enumerate(ranked_players, 1):
        player.rank = rank
        player.save()


def tournament_api_data(request, tournament_id=None):
    """API endpoint for tournament data"""
    
    # Check if user is authenticated for API requests
    if not request.user.is_authenticated:
        return JsonResponse({
            'success': False, 
            'error': 'Authentication required'
        }, status=401)
    
    if not request.user.can_manage_tournaments:
        return JsonResponse({
            'success': False,
            'error': 'You do not have permission to access tournament management data.'
        }, status=403)
    
    if tournament_id:
        # Single tournament data
        tournament = get_object_or_404(
            Tournament.objects.select_related('created_by').prefetch_related('players', 'games'),
            id=tournament_id
        )
        
        players_data = []
        for player in tournament.players.filter(status='registered'):
            players_data.append({
                'id': player.id,
                'player_name': player.player_name,
                'rating': player.rating,
                'email': player.email,
                'phone': player.phone,
                'category': player.category,
                'points': float(player.points),
                'wins': player.wins,
                'losses': player.losses,
                'draws': player.draws,
                'buchholz': float(player.buchholz),
                'sonneborn_berger': float(player.sonneborn_berger),
                'status': player.status,
                'rank': player.rank,
                'registered_at': player.registered_at.isoformat(),
            })
        
        games_data = []
        for game in tournament.games.all():
            games_data.append({
                'id': game.id,
                'round_number': game.round_number,
                'board_number': game.board_number,
                'white_player': {
                    'id': game.white_player.id,
                    'name': game.white_player.player_name,
                    'rating': game.white_player.rating,
                },
                'black_player': {
                    'id': game.black_player.id,
                    'name': game.black_player.player_name,
                    'rating': game.black_player.rating,
                },
                'result': game.result,
                'status': game.status,
                'scheduled_time': game.scheduled_time.isoformat(),
                'started_at': game.started_at.isoformat() if game.started_at else None,
                'completed_at': game.completed_at.isoformat() if game.completed_at else None,
                'pgn': game.pgn,
                'moves_count': game.moves_count,
            })
        
        data = {
            'success': True,
            'tournament': {
                'id': tournament.id,
                'name': tournament.name,
                'description': tournament.description,
                'venue': tournament.venue,
                'category': tournament.category,
                'format': tournament.format,
                'rounds': tournament.rounds,
                'time_control': tournament.time_control,
                'start_date': tournament.start_date.isoformat(),
                'end_date': tournament.end_date.isoformat(),
                'registration_deadline': tournament.registration_deadline.isoformat(),
                'entry_fee': float(tournament.entry_fee),
                'max_players': tournament.max_players,
                'current_players': tournament.registered_players_count,
                'available_slots': tournament.available_slots,
                'status': tournament.status,
                'is_active': tournament.is_active,
                'is_featured': tournament.is_featured,
                'created_by': tournament.created_by.username,
                'created_at': tournament.created_at.isoformat(),
                'updated_at': tournament.updated_at.isoformat(),
            },
            'players': players_data,
            'games': games_data,
        }
        
    else:
        # All tournaments data (with pagination)
        tournaments = Tournament.objects.select_related('created_by').prefetch_related('players')
        
        # Apply filters from GET params
        search = request.GET.get('search')
        if search:
            tournaments = tournaments.filter(
                Q(name__icontains=search) |
                Q(venue__icontains=search) |
                Q(description__icontains=search)
            )
        
        category = request.GET.get('category')
        if category:
            tournaments = tournaments.filter(category=category)
        
        status = request.GET.get('status')
        if status:
            tournaments = tournaments.filter(status=status)
        
        # Pagination
        page = int(request.GET.get('page', 1))
        per_page = int(request.GET.get('per_page', 12))
        paginator = Paginator(tournaments, per_page)
        page_obj = paginator.get_page(page)
        
        tournaments_list = []
        for tournament in page_obj:
            tournaments_list.append({
                'id': tournament.id,
                'name': tournament.name,
                'venue': tournament.venue,
                'category': tournament.category,
                'format': tournament.format,
                'rounds': tournament.rounds,
                'time_control': tournament.time_control,
                'start_date': tournament.start_date.isoformat(),
                'end_date': tournament.end_date.isoformat(),
                'registration_deadline': tournament.registration_deadline.isoformat(),
                'entry_fee': float(tournament.entry_fee),
                'max_players': tournament.max_players,
                'current_players': tournament.registered_players_count,
                'available_slots': tournament.available_slots,
                'status': tournament.status,
                'is_active': tournament.is_active,
                'is_featured': tournament.is_featured,
                'created_by': tournament.created_by.username,
                'created_at': tournament.created_at.isoformat(),
                'updated_at': tournament.updated_at.isoformat(),
            })
        
        response_data = {
            'success': True,
            'tournaments': tournaments_list,
            'pagination': {
                'current_page': page_obj.number,
                'total_pages': page_obj.paginator.num_pages,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous(),
                'total_count': tournaments.count(),
            }
        }
    
    if tournament_id:
        return JsonResponse(data)
    else:
        return JsonResponse(response_data)


# Round Management Views
@login_required
def tournament_rounds_api(request, tournament_id):
    """API endpoint for tournament rounds management"""
    
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Authentication required'}, status=401)
    
    tournament = get_object_or_404(Tournament, id=tournament_id)
    
    if request.method == 'GET':
        # Get all rounds for tournament
        rounds = TournamentRound.objects.filter(tournament=tournament).order_by('round_number')
        
        rounds_data = []
        for round_obj in rounds:
            rounds_data.append({
                'id': round_obj.id,
                'round_number': round_obj.round_number,
                'status': round_obj.status,
                'start_time': round_obj.start_time.isoformat() if round_obj.start_time else None,
                'end_time': round_obj.end_time.isoformat() if round_obj.end_time else None,
                'pairings_generated_at': round_obj.pairings_generated_at.isoformat() if round_obj.pairings_generated_at else None,
                'time_control': round_obj.time_control,
                'games_count': round_obj.games_count,
                'completed_games_count': round_obj.completed_games_count,
                'bye_players': [{'id': p.id, 'name': p.player_name} for p in round_obj.bye_players.all()]
            })
        
        return JsonResponse({
            'success': True,
            'rounds': rounds_data,
            'current_round': rounds.filter(status='active').first().round_number if rounds.filter(status='active').exists() else None
        })
    
    return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)


@login_required
def generate_next_round(request, tournament_id):
    """API endpoint to generate pairings for next round"""
    
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Authentication required'}, status=401)
    
    if not request.user.can_manage_tournaments:
        return JsonResponse({'success': False, 'error': 'You do not have permission to generate rounds.'}, status=403)
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    tournament = get_object_or_404(Tournament, id=tournament_id)
    
    try:
        from .swiss_pairing import SwissPairingService
        
        pairing_service = SwissPairingService(tournament)
        pairings = pairing_service.generate_pairings()
        
        # Get the created round
        round_number = tournament.tournament_rounds.count()
        current_round = tournament.tournament_rounds.get(round_number=round_number)
        
        # Get games for this round
        games = TournamentGame.objects.filter(tournament=tournament, round_number=round_number)
        
        games_data = []
        for game in games:
            games_data.append({
                'id': game.id,
                'board_number': game.board_number,
                'white_player': {
                    'id': game.white_player.id,
                    'name': game.white_player.player_name,
                    'rating': game.white_player.rating
                },
                'black_player': {
                    'id': game.black_player.id,
                    'name': game.black_player.player_name,
                    'rating': game.black_player.rating
                },
                'result': game.result,
                'status': game.status,
                'scheduled_time': game.scheduled_time.isoformat()
            })
        
        return JsonResponse({
            'success': True,
            'round': {
                'id': current_round.id,
                'round_number': current_round.round_number,
                'status': current_round.status,
                'games_count': len(games_data)
            },
            'games': games_data,
            'message': f'Successfully generated pairings for Round {round_number}'
        })
        
    except ValidationError as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
    except Exception as e:
        logger.error(f"Error generating pairings: {e}")
        return JsonResponse({'success': False, 'error': 'Failed to generate pairings'}, status=500)


@login_required
def tournament_games_api(request, tournament_id, round_number=None):
    """API endpoint for tournament games"""
    
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Authentication required'}, status=401)
    
    tournament = get_object_or_404(Tournament, id=tournament_id)
    
    if request.method == 'GET':
        # Filter by round if specified
        games = TournamentGame.objects.filter(tournament=tournament)
        if round_number:
            games = games.filter(round_number=round_number)
        
        games = games.order_by('round_number', 'board_number')
        
        games_data = []
        for game in games:
            games_data.append({
                'id': game.id,
                'round_number': game.round_number,
                'board_number': game.board_number,
                'white_player': {
                    'id': game.white_player.id,
                    'name': game.white_player.player_name,
                    'rating': game.white_player.rating
                },
                'black_player': {
                    'id': game.black_player.id,
                    'name': game.black_player.player_name,
                    'rating': game.black_player.rating
                },
                'result': game.result,
                'status': game.status,
                'scheduled_time': game.scheduled_time.isoformat(),
                'started_at': game.started_at.isoformat() if game.started_at else None,
                'completed_at': game.completed_at.isoformat() if game.completed_at else None,
                'pgn': game.pgn,
                'moves_count': game.moves_count
            })
        
        return JsonResponse({
            'success': True,
            'games': games_data
        })
    
    elif request.method == 'POST':
        # Update game result - requires tournament management permissions
        if not request.user.can_manage_tournaments:
            return JsonResponse({'success': False, 'error': 'You do not have permission to update game results.'}, status=403)
        
        game_id = request.POST.get('game_id')
        result = request.POST.get('result')
        
        if not game_id or not result:
            return JsonResponse({'success': False, 'error': 'Missing game_id or result'}, status=400)
        
        game = get_object_or_404(TournamentGame, id=game_id, tournament=tournament)
        
        if result not in ['1-0', '0-1', '½-½', '*']:
            return JsonResponse({'success': False, 'error': 'Invalid result'}, status=400)
        
        try:
            with transaction.atomic():
                # Update game result
                game.result = result
                if result != '*':
                    game.status = 'completed'
                    game.completed_at = timezone.now()
                game.save()
                
                # Create detailed result record
                TournamentResult.objects.update_or_create(
                    game=game,
                    defaults={
                        'result': result,
                        'entered_by': request.user,
                        'points_awarded': True
                    }
                )
                
                # Update player statistics
                if result != '*':
                    _update_player_stats(game, result)
                
                # Check if round is complete
                round_obj = game.round_number
                total_games = TournamentGame.objects.filter(tournament=tournament, round_number=round_obj).count()
                completed_games = TournamentGame.objects.filter(tournament=tournament, round_number=round_obj, status='completed').count()
                
                if completed_games == total_games:
                    # Mark round as complete
                    tournament_round = TournamentRound.objects.get(tournament=tournament, round_number=round_obj)
                    tournament_round.status = 'completed'
                    tournament_round.end_time = timezone.now()
                    tournament_round.save()
                    
                    # Update standings
                    from .swiss_pairing import StandingsService
                    standings_service = StandingsService(tournament)
                    standings_service.update_standings(round_obj)
                
                return JsonResponse({
                    'success': True,
                    'message': 'Game result updated successfully'
                })
                
        except Exception as e:
            logger.error(f"Error updating game result: {e}")
            return JsonResponse({'success': False, 'error': 'Failed to update result'}, status=500)
    
    return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)


@login_required
def tournament_standings_api(request, tournament_id, round_number=None):
    """API endpoint for tournament standings"""
    
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Authentication required'}, status=401)
    
    tournament = get_object_or_404(Tournament, id=tournament_id)
    
    if request.method == 'GET':
        # Get standings for specific round or latest
        if round_number:
            standings = TournamentStanding.objects.filter(tournament=tournament, round_number=round_number)
        else:
            # Get latest round standings
            latest_round = TournamentStanding.objects.filter(tournament=tournament).order_by('-round_number').first()
            if latest_round:
                standings = TournamentStanding.objects.filter(tournament=tournament, round_number=latest_round.round_number)
            else:
                standings = TournamentStanding.objects.none()
        
        standings = standings.order_by('rank')
        
        standings_data = []
        for standing in standings:
            standings_data.append({
                'rank': standing.rank,
                'player': {
                    'id': standing.player.id,
                    'name': standing.player.player_name,
                    'rating': standing.player.rating
                },
                'points': float(standing.points),
                'games_played': standing.games_played,
                'wins': standing.wins,
                'draws': standing.draws,
                'losses': standing.losses,
                'white_games': standing.white_games,
                'black_games': standing.black_games,
                'buchholz': float(standing.buchholz),
                'sonneborn_berger': float(standing.sonneborn_berger),
                'cumulative_score': float(standing.cumulative_score)
            })
        
        return JsonResponse({
            'success': True,
            'standings': standings_data,
            'round_number': round_number or (standings.first().round_number if standings.exists() else None)
        })
    
    return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)


def _update_player_stats(game: TournamentGame, result: str):
    """Update player statistics after game result"""
    from decimal import Decimal
    
    # Update white player stats
    white_player = game.white_player
    if result == '1-0':
        white_player.points += Decimal('1')
        white_player.wins += 1
    elif result == '½-½':
        white_player.points += Decimal('0.5')
        white_player.draws += 1
    elif result == '0-1':
        white_player.losses += 1
    
    white_player.save()
    
    # Update black player stats
    black_player = game.black_player
    if result == '0-1':
        black_player.points += Decimal('1')
        black_player.wins += 1
    elif result == '½-½':
        black_player.points += Decimal('0.5')
        black_player.draws += 1
    elif result == '1-0':
        black_player.losses += 1
    
    black_player.save()


@login_required
def print_pairings(request, tournament_id, round_number):
    """API endpoint to generate printable pairings"""
    
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Authentication required'}, status=401)
    
    tournament = get_object_or_404(Tournament, id=tournament_id)
    
    # Get games for this round
    games = TournamentGame.objects.filter(tournament=tournament, round_number=round_number).order_by('board_number')
    
    pairings_html = f"""
    <html>
    <head>
        <title>{tournament.name} - Round {round_number} Pairings</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            h1 {{ text-align: center; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background-color: #f2f2f2; }}
            .board {{ text-align: center; font-weight: bold; }}
            .player {{ font-weight: bold; }}
            .rating {{ color: #666; }}
        </style>
    </head>
    <body>
        <h1>{tournament.name}</h1>
        <h2>Round {round_number} Pairings</h2>
        <p>Date: {timezone.now().strftime('%B %d, %Y')}</p>
        <p>Time Control: {tournament.time_control}</p>
        
        <table>
            <thead>
                <tr>
                    <th>Board</th>
                    <th>White Player</th>
                    <th>Rating</th>
                    <th>Black Player</th>
                    <th>Rating</th>
                </tr>
            </thead>
            <tbody>
    """
    
    for game in games:
        pairings_html += f"""
                <tr>
                    <td class="board">{game.board_number}</td>
                    <td class="player">{game.white_player.player_name}</td>
                    <td class="rating">{game.white_player.rating}</td>
                    <td class="player">{game.black_player.player_name}</td>
                    <td class="rating">{game.black_player.rating}</td>
                </tr>
        """
    
    pairings_html += """
            </tbody>
        </table>
    </body>
    </html>
    """
    
    return JsonResponse({
        'success': True,
        'html': pairings_html,
        'filename': f"{tournament.name.replace(' ', '_')}_Round_{round_number}_Pairings.html"
    })


@login_required
def print_standings(request, tournament_id, round_number=None):
    """API endpoint to generate printable standings"""
    
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Authentication required'}, status=401)
    
    tournament = get_object_or_404(Tournament, id=tournament_id)
    
    # Get standings
    if round_number:
        standings = TournamentStanding.objects.filter(tournament=tournament, round_number=round_number)
    else:
        latest_round = TournamentStanding.objects.filter(tournament=tournament).order_by('-round_number').first()
        if latest_round:
            standings = TournamentStanding.objects.filter(tournament=tournament, round_number=latest_round.round_number)
        else:
            standings = TournamentStanding.objects.none()
    
    standings = standings.order_by('rank')
    
    standings_html = f"""
    <html>
    <head>
        <title>{tournament.name} - Standings</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            h1 {{ text-align: center; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: center; }}
            th {{ background-color: #f2f2f2; }}
            .rank {{ font-weight: bold; }}
            .player {{ text-align: left; font-weight: bold; }}
            .points {{ font-weight: bold; color: #2c5aa0; }}
            .tie-break {{ font-size: 0.9em; color: #666; }}
        </style>
    </head>
    <body>
        <h1>{tournament.name}</h1>
        <h2>Standings - Round {round_number or 'Latest'}</h2>
        <p>Date: {timezone.now().strftime('%B %d, %Y')}</p>
        
        <table>
            <thead>
                <tr>
                    <th>Rank</th>
                    <th>Player</th>
                    <th>Rating</th>
                    <th>Points</th>
                    <th>Played</th>
                    <th>Wins</th>
                    <th>Draws</th>
                    <th>Losses</th>
                    <th>Buchholz</th>
                    <th>S-B</th>
                </tr>
            </thead>
            <tbody>
    """
    
    for standing in standings:
        standings_html += f"""
                <tr>
                    <td class="rank">{standing.rank}</td>
                    <td class="player">{standing.player.player_name}</td>
                    <td>{standing.player.rating}</td>
                    <td class="points">{standing.points}</td>
                    <td>{standing.games_played}</td>
                    <td>{standing.wins}</td>
                    <td>{standing.draws}</td>
                    <td>{standing.losses}</td>
                    <td class="tie-break">{standing.buchholz}</td>
                    <td class="tie-break">{standing.sonneborn_berger}</td>
                </tr>
        """
    
    standings_html += """
            </tbody>
        </table>
    </body>
    </html>
    """
    
    return JsonResponse({
        'success': True,
        'html': standings_html,
        'filename': f"{tournament.name.replace(' ', '_')}_Standings_Round_{round_number or 'Latest'}.html"
    })
