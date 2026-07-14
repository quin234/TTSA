from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.db.models import Q, Count, Sum, Avg, F
from django.utils import timezone
from django.views.decorators.cache import cache_page
from django.core.cache import cache
from .forms import (
    YouTubeChannelForm, VideoLessonForm, TournamentForm, 
    TournamentPlayerForm, TournamentGameForm, TournamentSearchForm
)
from .models import YouTubeChannel, SyncNotification, Tournament, TournamentPlayer, TournamentGame
from .youtube_utils import validate_and_fetch_channel_metadata, YouTubeChannelError, fetch_channel_videos
from ttsa_app.models import VideoLesson
from .youtube_utils import validate_and_fetch_video_metadata, YouTubeVideoError
from django.db import transaction


@login_required
def admin_dashboard(request):
    """Main dashboard view for TTSA admin portal"""
    context = {
        'user': request.user,
    }
    return render(request, 'ttsaadmin/dashboard.html', context)


@login_required
def add_youtube_channel(request):
    """View for adding a YouTube channel"""
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
    """View for listing all video lessons"""
    videos = VideoLesson.objects.all().order_by('order', '-created_at')
    
    # Return JSON if requested via AJAX
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
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
        } for video in videos]
        return JsonResponse({'videos': videos_data})
    
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
                'current_players': tournament.current_players,
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


@csrf_exempt
def tournament_create(request):
    """View for creating a new tournament"""
    
    # Check if user is authenticated for API requests
    if not request.user.is_authenticated:
        return JsonResponse({
            'success': False, 
            'error': 'Authentication required'
        }, status=401)
    
    if request.method == 'POST':
        form = TournamentForm(request.POST)
        if form.is_valid():
            try:
                tournament = form.save(commit=False)
                tournament.created_by = request.user
                tournament.save()
                
                # Return JSON if requested via AJAX
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': True, 
                        'message': f'Tournament "{tournament.name}" created successfully!',
                        'tournament_id': tournament.id
                    })
                
                messages.success(request, f'Tournament "{tournament.name}" created successfully!')
                return redirect('tournament_detail', tournament_id=tournament.id)
                
            except Exception as e:
                # Return JSON if requested via AJAX
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'error': str(e)})
                
                messages.error(request, f'Error creating tournament: {str(e)}')
        else:
            # Return JSON if requested via AJAX
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False, 
                    'error': 'Form validation failed',
                    'errors': form.errors
                })
    else:
        form = TournamentForm()
    
    return render(request, 'ttsaadmin/tournament_form.html', {'form': form, 'title': 'Create Tournament'})


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


@csrf_exempt
def tournament_edit(request, tournament_id):
    """View for editing a tournament"""
    
    # Check if user is authenticated for API requests
    if not request.user.is_authenticated:
        return JsonResponse({
            'success': False, 
            'error': 'Authentication required'
        }, status=401)
    
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
                return redirect('tournament_detail', tournament_id=tournament.id)
                
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
    else:
        form = TournamentForm(instance=tournament)
    
    return render(request, 'ttsaadmin/tournament_form.html', {'form': form, 'tournament': tournament, 'title': 'Edit Tournament'})


@require_POST
def tournament_delete(request, tournament_id):
    """View for deleting a tournament"""
    
    # Check if user is authenticated for API requests
    if not request.user.is_authenticated:
        return JsonResponse({
            'success': False, 
            'error': 'Authentication required'
        }, status=401)
    
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
                tournament.current_players = tournament.players.count()
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
    
    if tournament_id:
        # Single tournament data
        tournament = get_object_or_404(
            Tournament.objects.select_related('created_by').prefetch_related('players', 'games'),
            id=tournament_id
        )
        
        players_data = []
        for player in tournament.players.all():
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
            'current_players': tournament.current_players,
            'available_slots': tournament.available_slots,
            'status': tournament.status,
            'is_active': tournament.is_active,
            'is_featured': tournament.is_featured,
            'created_by': tournament.created_by.username,
            'created_at': tournament.created_at.isoformat(),
            'updated_at': tournament.updated_at.isoformat(),
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
                'current_players': tournament.current_players,
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
    
    return JsonResponse(response_data)
