from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, update_session_auth_hash
from django.contrib.auth.forms import UserCreationForm, PasswordChangeForm
from .forms import CustomUserCreationForm, PlayerPlusApplicationForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponseForbidden
from django.utils import timezone
from datetime import timedelta
from functools import wraps
from django.db import models, transaction, IntegrityError
from django.db.models import Q, Max
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.core.exceptions import ValidationError
import logging
from .models import (
    User, PlayerProfile, OrganizerProfile, PlayerPlusApplication, Achievement, PlayerAchievement, ChessGame,
    Lesson, PlayerLesson, Puzzle,	PlayerPuzzle, Leaderboard,
    Friend, Message, AcademyNews, MultiplayerGame, GameMove, VideoLesson
)
from ttsaadmin.models import Tournament, TournamentPlayer, TournamentGame, TournamentRound, TournamentStanding
from ttsaadmin.forms import TournamentForm, TournamentPlayerForm
from ttsaadmin.pairing_manager import get_pairing_manager
from ttsaadmin.pairing_converter import PairingDataConverter
from .stockfish_service import stockfish_service, DifficultyLevel
import random
import json
import secrets
import string

logger = logging.getLogger(__name__)


# Custom decorator for social features that require authentication
def login_required_with_message(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.info(request, 'This feature requires an account. Sign up to connect with friends, join tournaments, and access all social features!')
            return redirect('signup')
        return view_func(request, *args, **kwargs)
    return _wrapped_view


# Decorator for views that require tournament management permissions
def tournament_manager_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'success': False, 'error': 'Authentication required'}, status=401)
        if not request.user.can_manage_tournaments:
            return JsonResponse({'success': False, 'error': 'You do not have permission to manage tournaments. Upgrade to PLAYER_PLUS to create and manage tournaments.'}, status=403)
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def can_manage_tournament_object(user, tournament):
    """Check if a user can manage a specific tournament. Admins can manage all;
    Player Plus users can only manage tournaments they created."""
    if not user.is_authenticated:
        return False
    if user.is_ttsa_admin:
        return True
    return user.is_player_plus and tournament.created_by == user


def player_plus_tournament_access(view_func):
    """Decorator ensuring the user can manage the tournament in the URL."""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if not request.user.can_manage_tournaments:
            messages.error(request, 'You do not have permission to manage tournaments.')
            return redirect('tournaments')
        tournament_id = kwargs.get('tournament_id')
        if tournament_id:
            tournament = get_object_or_404(Tournament, id=tournament_id)
            if not can_manage_tournament_object(request.user, tournament):
                messages.error(request, 'You do not have permission to manage this tournament.')
                return redirect('player_tournament_list')
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def home(request):
    # Always redirect to chess game page for instant access
    return redirect('chess_game')




def chess_game(request):
    difficulty = request.GET.get('difficulty', 'intermediate')
    
    # Handle both authenticated and guest users
    if request.user.is_authenticated:
        profile = request.user.playerprofile
        is_guest = False
    else:
        profile = None
        is_guest = True
    
    # Get current difficulty info - three learner-focused levels
    difficulty_info = {
        'beginner': {'name': 'Beginner'},
        'intermediate': {'name': 'Intermediate'},
        'master': {'name': 'Master'}
    }

    current_difficulty = difficulty_info.get(difficulty, difficulty_info['intermediate'])

    context = {
        'profile': profile,
        'is_guest': is_guest,
        'difficulty': difficulty,
        'current_difficulty_name': current_difficulty['name'],
        'difficulty_levels': difficulty_info
    }
    return render(request, 'ttsa_app/chess_game.html', context)


def lessons(request):
    lessons = Lesson.objects.all().order_by('category', 'order')
    total_lessons = lessons.count()
    
    # Handle both authenticated and guest users
    if request.user.is_authenticated:
        profile = request.user.playerprofile
        completed_lessons = PlayerLesson.objects.filter(player=profile, completed=True).values_list('lesson_id', flat=True)
        is_guest = False
    else:
        profile = None
        completed_lessons = []
        is_guest = True
    
    # Calculate progress percentage
    if total_lessons > 0:
        progress_percentage = int((len(completed_lessons) / total_lessons) * 100)
    else:
        progress_percentage = 0
    
    context = {
        'profile': profile,
        'is_guest': is_guest,
        'lessons': lessons,
        'completed_lessons': completed_lessons,
        'total_lessons': total_lessons,
        'progress_percentage': progress_percentage,
    }
    return render(request, 'ttsa_app/lessons.html', context)


def lesson_detail(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id)
    
    # Handle both authenticated and guest users
    if request.user.is_authenticated:
        profile = request.user.playerprofile
        player_lesson, created = PlayerLesson.objects.get_or_create(player=profile, lesson=lesson)
        is_guest = False
    else:
        profile = None
        player_lesson = None
        is_guest = True
    
    context = {
        'profile': profile,
        'lesson': lesson,
        'player_lesson': player_lesson,
        'is_guest': is_guest,
    }
    return render(request, 'ttsa_app/lesson_detail.html', context)


def puzzles(request):
    # Get daily puzzle
    daily_puzzle = Puzzle.objects.filter(daily=True).first()
    if not daily_puzzle:
        # Create a random daily puzzle if none exists
        all_puzzles = Puzzle.objects.all()
        if all_puzzles:
            daily_puzzle = random.choice(all_puzzles)
            daily_puzzle.daily = True
            daily_puzzle.save()
    
    # Get other puzzles
    other_puzzles = Puzzle.objects.filter(daily=False).order_by('difficulty')[:10]
    
    # Handle both authenticated and guest users
    if request.user.is_authenticated:
        profile = request.user.playerprofile
        solved_puzzles = PlayerPuzzle.objects.filter(player=profile, solved=True).values_list('puzzle_id', flat=True)
        is_guest = False
    else:
        profile = None
        solved_puzzles = []
        is_guest = True
    
    context = {
        'profile': profile,
        'is_guest': is_guest,
        'daily_puzzle': daily_puzzle,
        'other_puzzles': other_puzzles,
        'solved_puzzles': solved_puzzles,
    }
    return render(request, 'ttsa_app/puzzles.html', context)


@login_required_with_message
def achievements(request):
    profile = request.user.playerprofile
    player_achievements = PlayerAchievement.objects.filter(player=profile).select_related('achievement')
    all_achievements = Achievement.objects.all()
    
    # Create a list of achievement data with progress info
    achievements_with_progress = []
    for achievement in all_achievements:
        player_ach = player_achievements.filter(achievement=achievement).first()
        if player_ach:
            achievements_with_progress.append({
                'achievement': achievement,
                'player_achievement': player_ach,
                'progress': player_ach.progress,
                'completed': True
            })
        else:
            achievements_with_progress.append({
                'achievement': achievement,
                'player_achievement': None,
                'progress': 0,
                'completed': False
            })
    
    context = {
        'profile': profile,
        'player_achievements': player_achievements,
        'all_achievements': all_achievements,
        'achievements_with_progress': achievements_with_progress,
    }
    return render(request, 'ttsa_app/achievements.html', context)


@login_required_with_message
def tournaments(request):
    profile = request.user.playerprofile
    context = {
        'profile': profile,
    }
    return render(request, 'ttsa_app/tournaments.html', context)


def video_lessons(request):
    videos = VideoLesson.objects.all()
    
    # Get filter parameters
    category_filter = request.GET.get('category', '')
    difficulty_filter = request.GET.get('difficulty', '')
    search_query = request.GET.get('search', '')
    
    # Apply filters
    if category_filter:
        videos = videos.filter(category=category_filter)
    if difficulty_filter:
        videos = videos.filter(difficulty=difficulty_filter)
    if search_query:
        videos = videos.filter(title__icontains=search_query)
    
    # Get first video for player (if any)
    first_video = videos.first()
    
    # Get selected video from URL parameter
    selected_video_id = request.GET.get('video_id')
    if selected_video_id:
        try:
            selected_video = videos.get(id=selected_video_id)
        except VideoLesson.DoesNotExist:
            selected_video = first_video
    else:
        selected_video = first_video
    
    # Increment view count for selected video
    if selected_video and request.user.is_authenticated:
        selected_video.views += 1
        selected_video.save()
    
    context = {
        'videos': videos,
        'selected_video': selected_video,
        'category_filter': category_filter,
        'difficulty_filter': difficulty_filter,
        'search_query': search_query,
    }
    return render(request, 'ttsa_app/video_lessons.html', context)


@login_required_with_message
def leaderboard(request):
    profile = request.user.playerprofile
    
    # Get top players
    top_players = Leaderboard.objects.all().order_by('weekly_rank')[:20]
    
    # Get user's rank
    user_rank = Leaderboard.objects.filter(player=profile).first()
    
    context = {
        'profile': profile,
        'top_players': top_players,
        'user_rank': user_rank,
    }
    return render(request, 'ttsa_app/leaderboard.html', context)


@login_required_with_message
def friends(request):
    profile = request.user.playerprofile
    
    # Get friends
    friends = Friend.objects.filter(
        models.Q(from_user=profile) | models.Q(to_user=profile),
        accepted=True
    ).select_related('from_user', 'to_user')
    
    # Get friend requests
    friend_requests = Friend.objects.filter(to_user=profile, accepted=False)
    
    context = {
        'profile': profile,
        'friends': friends,
        'friend_requests': friend_requests,
    }
    return render(request, 'ttsa_app/friends.html', context)


@login_required_with_message
def messages_view(request):
    profile = request.user.playerprofile
    
    # Get messages
    received_messages = Message.objects.filter(receiver=profile).order_by('-created_at')
    sent_messages = Message.objects.filter(sender=profile).order_by('-created_at')
    
    context = {
        'profile': profile,
        'received_messages': received_messages,
        'sent_messages': sent_messages,
    }
    return render(request, 'ttsa_app/messages.html', context)


@login_required
def news(request):
    profile = request.user.playerprofile
    news = AcademyNews.objects.all().order_by('-published_at')
    
    context = {
        'profile': profile,
        'news': news,
    }
    return render(request, 'ttsa_app/news.html', context)


@login_required
def settings_view(request):
    profile = request.user.playerprofile
    
    if request.method == 'POST':
        # Handle settings update
        profile.bio = request.POST.get('bio', '')
        if 'avatar' in request.FILES:
            profile.avatar = request.FILES['avatar']
        profile.save()
        messages.success(request, 'Settings updated successfully!')
        return redirect('settings')
    
    context = {
        'profile': profile,
    }
    return render(request, 'ttsa_app/settings.html', context)


@login_required
def change_username(request):
    if request.method == 'POST':
        new_username = request.POST.get('new_username')
        password = request.POST.get('password')
        
        # Verify current password
        user = authenticate(request, username=request.user.username, password=password)
        if user is None:
            messages.error(request, 'Current password is incorrect.')
            return redirect('settings')
        
        # Check if username is already taken
        if User.objects.filter(username=new_username).exists():
            messages.error(request, 'Username is already taken.')
            return redirect('settings')
        
        # Change username
        user.username = new_username
        user.save()
        messages.success(request, 'Username changed successfully!')
        return redirect('settings')
    
    return redirect('settings')


@login_required
def change_password(request):
    if request.method == 'POST':
        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        
        # Verify current password
        user = authenticate(request, username=request.user.username, password=current_password)
        if user is None:
            messages.error(request, 'Current password is incorrect.')
            return redirect('settings')
        
        # Check if new passwords match
        if new_password != confirm_password:
            messages.error(request, 'New passwords do not match.')
            return redirect('settings')
        
        # Change password
        user.set_password(new_password)
        user.save()
        update_session_auth_hash(request, user)
        messages.success(request, 'Password changed successfully!')
        return redirect('settings')
    
    return redirect('settings')


@login_required
def apply_player_plus(request):
    """View for a player to apply to become PLAYER_PLUS. Application is reviewed by an admin."""
    if request.method == 'POST':
        user = request.user
        
        if user.role != 'player':
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': 'Only regular players can apply for Player Plus.'}, status=403)
            messages.error(request, 'Only regular players can apply for Player Plus.')
            return redirect('settings')
        
        # Only one pending application at a time
        if PlayerPlusApplication.objects.filter(user=user, status='pending').exists():
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': 'You already have a pending application.'}, status=400)
            messages.warning(request, 'You already have a pending Player Plus application.')
            return redirect('settings')
        
        form = PlayerPlusApplicationForm(request.POST)
        if form.is_valid():
            application = form.save(commit=False)
            application.user = user
            application.status = 'pending'
            application.save()
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': 'Your Player Plus application has been submitted for review.',
                })
            messages.success(request, 'Your Player Plus application has been submitted for review.')
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': 'Please provide full name and phone number.', 'errors': form.errors}, status=400)
            messages.error(request, 'Please provide full name and phone number.')
        
        return redirect('settings')
    
    return redirect('settings')


@login_required
def user_role_api(request):
    """API endpoint to get current user's role and permissions."""
    user = request.user
    return JsonResponse({
        'success': True,
        'role': user.role,
        'is_player': user.is_player,
        'is_player_plus': user.is_player_plus,
        'is_ttsa_admin': user.is_ttsa_admin,
        'can_manage_tournaments': user.can_manage_tournaments,
    })


def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            messages.success(request, f'Welcome back, {username}!')
            
            # Redirect TTSA admins to admin dashboard
            if user.is_ttsa_admin:
                return redirect('admin_dashboard')
            
            return redirect('chess_game')
        else:
            messages.error(request, 'Invalid username or password.')
    
    return render(request, 'ttsa_app/login.html')


def signup(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            
            # Create player profile (use get_or_create to handle existing profiles)
            profile, created = PlayerProfile.objects.get_or_create(user=user)
            
            # Handle guest progress transfer
            guest_data = request.POST.get('guest_transfer_data')
            if guest_data:
                try:
                    guest_progress = json.loads(guest_data)
                    
                    # Transfer guest progress to new account
                    if 'guest_data' in guest_progress:
                        data = guest_progress['guest_data']
                        profile.rating = data.get('current_rating', 800)
                        profile.coins = data.get('coins', 100)
                        profile.experience_points = data.get('experience_points', 0)
                        profile.level = data.get('level', 1)
                        profile.learning_streak = data.get('learning_streak', 0)
                        profile.save()
                        
                        # Transfer completed lessons
                        for lesson_id in data.get('completed_lessons', []):
                            try:
                                lesson = Lesson.objects.get(id=lesson_id)
                                PlayerLesson.objects.create(
                                    player=profile,
                                    lesson=lesson,
                                    completed=True,
                                    score=100,
                                    completed_at=timezone.now()
                                )
                            except Lesson.DoesNotExist:
                                pass
                        
                        # Transfer solved puzzles
                        for puzzle_id in data.get('solved_puzzles', []):
                            try:
                                puzzle = Puzzle.objects.get(id=puzzle_id)
                                PlayerPuzzle.objects.create(
                                    player=profile,
                                    puzzle=puzzle,
                                    solved=True,
                                    solved_at=timezone.now()
                                )
                            except Puzzle.DoesNotExist:
                                pass
                        
                        messages.success(request, f'Account created for {user.username}! Your guest progress has been transferred.')
                except (json.JSONDecodeError, KeyError) as e:
                    messages.warning(request, f'Account created for {user.username}, but we could not transfer your guest progress.')
            else:
                messages.success(request, f'Account created for {user.username}!')
            
            login(request, user)
            return redirect('chess_game')
    else:
        form = CustomUserCreationForm()
    return render(request, 'ttsa_app/signup.html', {'form': form})


# API Views
def save_game(request):
    if request.method == 'POST':
        # Handle both authenticated and guest users
        if request.user.is_authenticated:
            profile = request.user.playerprofile
            is_guest = False
        else:
            profile = None
            is_guest = True
        
        data = request.POST
        
        if is_guest:
            # For guests, just return success without saving to database
            # Progress will be saved in localStorage
            return JsonResponse({'success': True, 'guest': True, 'message': 'Game saved locally'})
        
        game = ChessGame.objects.create(
            player=profile,
            player_color=data.get('player_color', 'white'),
            difficulty_level=data.get('difficulty', 'beginner'),
            pgn=data.get('pgn', ''),
            result=data.get('result', 'ongoing'),
            moves_count=int(data.get('moves_count', 0)),
            time_elapsed=timedelta(seconds=int(data.get('time_elapsed', 0)))
        )
        
        # Update player stats
        if data.get('result') == 'win':
            profile.rating += 25
            profile.coins += 10
            profile.experience_points += 50
        elif data.get('result') == 'draw':
            profile.rating += 10
            profile.coins += 5
            profile.experience_points += 25
        elif data.get('result') == 'loss':
            profile.rating -= 15
            profile.experience_points += 10
        
        profile.last_played = timezone.now().date()
        profile.save()
        
        return JsonResponse({'success': True, 'game_id': game.id, 'guest': False})
    
    return JsonResponse({'success': False}, status=400)


@csrf_exempt
def complete_lesson(request, lesson_id):
    if request.method == 'POST':
        # Handle both authenticated and guest users
        if request.user.is_authenticated:
            profile = request.user.playerprofile
            is_guest = False
        else:
            profile = None
            is_guest = True
        
        lesson = get_object_or_404(Lesson, id=lesson_id)
        
        if is_guest:
            # For guests, just return success without saving to database
            # Progress will be saved in localStorage
            return JsonResponse({'success': True, 'guest': True, 'coins': lesson.points_reward, 'message': 'Lesson completed locally'})
        
        player_lesson, created = PlayerLesson.objects.get_or_create(player=profile, lesson=lesson)
        
        if not player_lesson.completed:
            player_lesson.completed = True
            player_lesson.score = int(request.POST.get('score', 100))
            player_lesson.completed_at = timezone.now()
            player_lesson.save()
            
            # Award coins and experience
            profile.coins += lesson.points_reward
            profile.experience_points += lesson.points_reward * 2
            profile.last_played = timezone.now().date()
            profile.save()
            
            # Check for lesson-related achievements
            check_lesson_achievements(profile)
            
            return JsonResponse({'success': True, 'guest': False, 'coins': lesson.points_reward})
        
        return JsonResponse({'success': False, 'message': 'Lesson already completed'})
    
    return JsonResponse({'success': False}, status=400)


def check_lesson_achievements(profile):
    """Check and award lesson-related achievements"""
    completed_lessons_count = PlayerLesson.objects.filter(player=profile, completed=True).count()
    
    # Check for lesson completion achievements
    achievement_milestones = {
        5: 'Chess Student',
        10: 'Dedicated Learner',
        25: 'Chess Scholar',
        50: 'Chess Master'
    }
    
    for milestone, achievement_name in achievement_milestones.items():
        if completed_lessons_count >= milestone:
            try:
                achievement = Achievement.objects.get(name=achievement_name, category='lessons')
                PlayerAchievement.objects.get_or_create(
                    player=profile,
                    achievement=achievement,
                    defaults={'progress': 100}
                )
            except Achievement.DoesNotExist:
                # Create achievement if it doesn't exist
                Achievement.objects.create(
                    name=achievement_name,
                    description=f'Complete {milestone} lessons',
                    icon='📚',
                    points=milestone * 2,
                    category='lessons'
                )


@csrf_exempt
def lesson_progress(request):
    """API endpoint to get lesson progress for a user"""
    if request.method == 'GET':
        if not request.user.is_authenticated:
            return JsonResponse({'success': False, 'error': 'Authentication required'}, status=401)
        
        profile = request.user.playerprofile
        completed_lessons = PlayerLesson.objects.filter(
            player=profile, 
            completed=True
        ).select_related('lesson')
        
        total_lessons = Lesson.objects.count()
        
        lessons_data = []
        for player_lesson in completed_lessons:
            lessons_data.append({
                'id': player_lesson.lesson.id,
                'title': player_lesson.lesson.title,
                'category': player_lesson.lesson.category,
                'difficulty': player_lesson.lesson.difficulty,
                'score': player_lesson.score,
                'completed_at': player_lesson.completed_at.isoformat() if player_lesson.completed_at else None,
                'points_reward': player_lesson.lesson.points_reward
            })
        
        return JsonResponse({
            'success': True,
            'completed_lessons': lessons_data,
            'total_completed': len(lessons_data),
            'total_lessons': total_lessons,
            'progress_percentage': round((len(lessons_data) / total_lessons * 100) if total_lessons > 0 else 0, 2)
        })
    
    return JsonResponse({'success': False}, status=400)


@csrf_exempt
def lesson_recommendations(request):
    """API endpoint to get recommended lessons based on user progress"""
    if request.method == 'GET':
        if not request.user.is_authenticated:
            return JsonResponse({'success': False, 'error': 'Authentication required'}, status=401)
        
        profile = request.user.playerprofile
        
        # Get completed lesson IDs
        completed_lesson_ids = PlayerLesson.objects.filter(
            player=profile, 
            completed=True
        ).values_list('lesson_id', flat=True)
        
        # Get incomplete lessons, ordered by difficulty and category
        recommended_lessons = Lesson.objects.exclude(
            id__in=completed_lesson_ids
        ).order_by('difficulty', 'order', 'category')[:5]
        
        lessons_data = []
        for lesson in recommended_lessons:
            lessons_data.append({
                'id': lesson.id,
                'title': lesson.title,
                'description': lesson.description,
                'category': lesson.category,
                'difficulty': lesson.difficulty,
                'points_reward': lesson.points_reward
            })
        
        return JsonResponse({
            'success': True,
            'recommended_lessons': lessons_data
        })
    
    return JsonResponse({'success': False}, status=400)


def solve_puzzle(request, puzzle_id):
    if request.method == 'POST':
        # Handle both authenticated and guest users
        if request.user.is_authenticated:
            profile = request.user.playerprofile
            is_guest = False
        else:
            profile = None
            is_guest = True
        
        puzzle = get_object_or_404(Puzzle, id=puzzle_id)
        
        if is_guest:
            # For guests, just return success without saving to database
            # Progress will be saved in localStorage
            coins = 5 if puzzle.difficulty == 'beginner' else 10
            return JsonResponse({'success': True, 'guest': True, 'coins': coins, 'message': 'Puzzle solved locally'})
        
        player_puzzle, created = PlayerPuzzle.objects.get_or_create(player=profile, puzzle=puzzle)
        
        solution = request.POST.get('solution', '')
        if solution == puzzle.solution and not player_puzzle.solved:
            player_puzzle.solved = True
            player_puzzle.solved_at = timezone.now()
            player_puzzle.save()
            
            # Award coins and experience
            coins = 5 if puzzle.difficulty == 'beginner' else 10
            profile.coins += coins
            profile.experience_points += coins * 2
            profile.save()
            
            return JsonResponse({'success': True, 'guest': False, 'coins': coins})
        
        player_puzzle.attempts += 1
        player_puzzle.save()
        
        return JsonResponse({'success': False, 'attempts': player_puzzle.attempts})
    
    return JsonResponse({'success': False}, status=400)


@csrf_exempt
def stockfish_move(request):
    """API endpoint to get best move from Stockfish engine"""
    if request.method == 'POST':
        try:
            # Get parameters from request
            fen = request.POST.get('fen', '')
            difficulty_str = request.POST.get('difficulty', 'intermediate')
            
            if not fen:
                return JsonResponse({'success': False, 'error': 'No FEN provided'}, status=400)
            
            # Map difficulty string to enum (only the three Play vs Computer levels)
            difficulty_map = {
                'beginner': DifficultyLevel.BEGINNER,
                'intermediate': DifficultyLevel.INTERMEDIATE,
                'master': DifficultyLevel.MASTER
            }
            
            difficulty = difficulty_map.get(difficulty_str.lower(), DifficultyLevel.INTERMEDIATE)
            
            # Check if Stockfish is available
            if not stockfish_service.is_engine_available():
                return JsonResponse({
                    'success': False,
                    'error': 'Stockfish engine not available',
                    'fallback': True
                }, status=503)
            
            # Start engine if not running
            if not stockfish_service.is_engine_ready():
                if not stockfish_service.start_engine():
                    return JsonResponse({
                        'success': False,
                        'error': 'Failed to start Stockfish engine',
                        'fallback': True
                    }, status=503)
            
            # Get best move from Stockfish
            best_move = stockfish_service.get_best_move(fen, difficulty)
            
            if best_move:
                return JsonResponse({
                    'success': True,
                    'move': best_move,
                    'engine': 'stockfish',
                    'difficulty': difficulty.value
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': 'No best move found',
                    'fallback': True
                }, status=500)
                
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e),
                'fallback': True
            }, status=500)
    
    return JsonResponse({'success': False}, status=400)


# Multiplayer Game Views
MULTIPLAYER_TIME_CONTROLS = {
    '1+0': ('bullet', 60, 0),
    '2+1': ('bullet', 120, 1),
    '3+2': ('blitz', 180, 2),
    '5+0': ('blitz', 300, 0),
    '5+3': ('blitz', 300, 3),
    '10+0': ('rapid', 600, 0),
    '15+10': ('rapid', 900, 10),
    '30+0': ('rapid', 1800, 0),
}

MULTIPLAYER_COLOR_PREFERENCES = {'white', 'black', 'random'}


def multiplayer_game_type(initial_time):
    if initial_time <= 120:
        return 'bullet'
    if initial_time <= 600:
        return 'blitz'
    return 'rapid'


@login_required
def multiplayer_create(request):
    """Render the game creation page"""
    return render(request, 'ttsa_app/multiplayer_create.html')


@login_required
@require_POST
def multiplayer_create_api(request):
    """Create a private multiplayer game for an allowed time control."""
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({'success': False, 'error': 'Invalid request data'}, status=400)

    time_control = data.get('time_control')
    color_preference = data.get('color_preference', 'random')
    if color_preference not in MULTIPLAYER_COLOR_PREFERENCES:
        return JsonResponse({'success': False, 'error': 'Invalid color preference'}, status=400)

    settings = MULTIPLAYER_TIME_CONTROLS.get(time_control)
    if settings:
        game_type, initial_time, increment_seconds = settings
    elif data.get('is_custom') is True:
        initial_minutes = data.get('initial_minutes')
        increment_seconds = data.get('increment_seconds')
        if (
            isinstance(initial_minutes, bool) or isinstance(increment_seconds, bool)
            or not isinstance(initial_minutes, int) or not isinstance(increment_seconds, int)
            or not 1 <= initial_minutes <= 180 or not 0 <= increment_seconds <= 60
        ):
            return JsonResponse({'success': False, 'error': 'Choose 1–180 minutes and a 0–60 second increment'}, status=400)
        initial_time = initial_minutes * 60
        time_control = f'{initial_minutes}+{increment_seconds}'
        game_type = multiplayer_game_type(initial_time)
    else:
        return JsonResponse({'success': False, 'error': 'Invalid time control'}, status=400)
    for _ in range(10):
        game_code = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))
        try:
            game = MultiplayerGame.objects.create(
                game_code=game_code,
                white_player=request.user,
                game_type=game_type,
                time_control=time_control,
                initial_time=initial_time,
                increment_seconds=increment_seconds,
                white_time=initial_time,
                black_time=initial_time,
                visibility='private',
                rated=False,
                color_preference=color_preference,
            )
            return JsonResponse({
                'success': True,
                'game_id': game.id,
                'game_code': game_code,
            })
        except IntegrityError:
            continue

    return JsonResponse({'success': False, 'error': 'Could not create a unique game link'}, status=503)


@login_required
def multiplayer_game(request, game_code):
    """Render the multiplayer game page"""
    game = get_object_or_404(MultiplayerGame, game_code=game_code)
    
    # Join waiting games atomically and randomly assign the two players' colors.
    if game.white_player != request.user and game.black_player != request.user:
        if game.status == 'waiting' and game.black_player is None:
            with transaction.atomic():
                game = MultiplayerGame.objects.select_for_update().get(pk=game.pk)
                if game.status != 'waiting' or game.black_player is not None:
                    return render(request, 'ttsa_app/error.html', {
                        'error': 'This game is no longer available to join'
                    })
                creator = game.white_player
                if game.color_preference == 'white':
                    game.white_player = creator
                    game.black_player = request.user
                elif game.color_preference == 'black':
                    game.white_player = request.user
                    game.black_player = creator
                elif random.choice([True, False]):
                    game.white_player = creator
                    game.black_player = request.user
                else:
                    game.white_player = request.user
                    game.black_player = creator
                game.status = 'playing'
                game.started_at = timezone.now()
                game.white_time = game.initial_time
                game.black_time = game.initial_time
                game.active_clock = 'white'
                game.last_move_timestamp = None
                game.save()
        else:
            return render(request, 'ttsa_app/error.html', {
                'error': 'You are not authorized to view this game'
            })
    
    # Determine user's color
    my_color = None
    if game.white_player == request.user:
        my_color = 'white'
    elif game.black_player == request.user:
        my_color = 'black'
    
    # Get player profiles for ratings
    from .models import PlayerProfile
    try:
        white_profile = game.white_player.playerprofile
    except PlayerProfile.DoesNotExist:
        white_profile = PlayerProfile.objects.create(user=game.white_player)
    
    # Handle case where black_player is None (game waiting for opponent)
    if game.black_player:
        try:
            black_profile = game.black_player.playerprofile
        except PlayerProfile.DoesNotExist:
            black_profile = PlayerProfile.objects.create(user=game.black_player)
    else:
        # Create a placeholder profile for display
        black_profile = type('obj', (object,), {'rating': 0, 'avatar': type('obj', (object,), {'url': ''})()})
    
    return render(request, 'ttsa_app/multiplayer_game.html', {
        'game': game,
        'my_color': my_color,
        'white_profile': white_profile,
        'black_profile': black_profile
    })


@login_required
@csrf_exempt
def multiplayer_status_api(request, game_code):
    """API endpoint to check game status"""
    game = get_object_or_404(MultiplayerGame, game_code=game_code)
    
    return JsonResponse({
        'opponent_joined': game.black_player is not None,
        'status': game.status
    })


@login_required
@csrf_exempt
def multiplayer_cancel_api(request, game_code):
    """API endpoint to cancel a waiting game"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=400)
    
    game = get_object_or_404(MultiplayerGame, game_code=game_code)
    
    # Only allow the creator to cancel
    if game.white_player != request.user and game.black_player != request.user:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
    
    # Only allow cancellation if game is still waiting
    if game.status != 'waiting':
        return JsonResponse({'success': False, 'error': 'Game already started'}, status=400)
    
    game.status = 'abandoned'
    game.save()
    
    return JsonResponse({'success': True})


# Tournament Views for TTSA App

def tournaments_view(request):
    """View for tournaments page"""
    profile = request.user.playerprofile if request.user.is_authenticated else None
    return render(request, 'ttsa_app/tournaments.html', {'profile': profile})


@csrf_exempt
def tournaments_api(request):
    """API endpoint for tournaments data - public access for viewing tournaments"""
    
    if request.method == 'GET':
        from ttsaadmin.models import Tournament
        from django.db.models import Q
        from django.utils import timezone
        
        # Get all active tournaments, excluding closed ones
        tournaments = Tournament.objects.filter(
            is_active=True
        ).exclude(
            status='closed'
        ).select_related('created_by').prefetch_related('players')
        
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
        
        # Order by start date
        tournaments = tournaments.order_by('start_date')
        
        # Categorize tournaments
        upcoming = []
        ongoing = []
        completed = []
        
        for tournament in tournaments:
            # Check if current user is registered
            is_registered = False
            if hasattr(request, 'user') and request.user.is_authenticated:
                try:
                    profile = request.user.playerprofile
                    is_registered = TournamentPlayer.objects.filter(
                        player_name=profile.user.username, 
                        tournament=tournament
                    ).exists()
                except (PlayerProfile.DoesNotExist, AttributeError):
                    pass
            
            tournament_data = {
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
                'is_registration_open': tournament.is_registration_open,
                'is_full': tournament.is_full,
                'is_registered': is_registered,
            }
            
            # Categorize based on status and dates
            now = timezone.now()
            
            # Upcoming: tournaments that haven't started yet
            if tournament.status in ['published', 'registration', 'upcoming'] and tournament.start_date > now:
                upcoming.append(tournament_data)
            # Ongoing: tournaments currently in progress
            elif tournament.status in ['in_progress', 'ongoing'] or (tournament.start_date <= now <= tournament.end_date):
                ongoing.append(tournament_data)
            # Completed: tournaments that have finished
            elif tournament.status in ['completed', 'finished'] or tournament.end_date < now:
                completed.append(tournament_data)
            # Handle edge case: tournaments with 'upcoming' status but past start date should be ongoing
            elif tournament.status == 'upcoming' and tournament.start_date <= now:
                ongoing.append(tournament_data)
        
        return JsonResponse({
            'success': True,
            'upcoming': upcoming,
            'ongoing': ongoing,
            'completed': completed,
        })
    
    return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)


@csrf_exempt
@login_required
def tournament_register_api(request, tournament_id):
    """API endpoint for tournament registration"""
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    try:
        from ttsaadmin.models import Tournament, TournamentPlayer
        from django.utils import timezone
        
        # Get tournament
        tournament = get_object_or_404(Tournament, id=tournament_id)
        
        # Validate tournament status and eligibility
        if tournament.status not in ['upcoming', 'published', 'registration']:
            return JsonResponse({
                'success': False, 
                'error': 'Registration is not available for this tournament'
            }, status=400)
        
        # Check if registration is still open
        if not tournament.is_registration_open:
            return JsonResponse({
                'success': False, 
                'error': 'Registration deadline has passed'
            }, status=400)
        
        # Check if tournament is full
        if tournament.is_full:
            return JsonResponse({
                'success': False, 
                'error': 'Tournament is full'
            }, status=400)
        
        # Get player profile
        try:
            profile = request.user.playerprofile
        except PlayerProfile.DoesNotExist:
            return JsonResponse({
                'success': False, 
                'error': 'Player profile not found. Please complete your profile first.'
            }, status=400)
        
        # Check if already registered
        existing_registration = TournamentPlayer.objects.filter(
            player_name=profile.user.username, 
            tournament=tournament
        ).first()
        
        if existing_registration:
            if existing_registration.status == 'registered':
                return JsonResponse({
                    'success': False, 
                    'error': 'You are already registered for this tournament'
                }, status=400)
            else:
                # Re-activate cancelled registration if exists
                existing_registration.status = 'registered'
                existing_registration.registered_at = timezone.now()
                existing_registration.save(update_fields=['status', 'registered_at'])
                
                # Update tournament current players count
                tournament.current_players += 1
                tournament.save(update_fields=['current_players'])
                
                return JsonResponse({
                    'success': True,
                    'message': 'Registration reactivated successfully!',
                    'registration_id': existing_registration.id
                })
        
        # Note: PlayerProfile doesn't have category field, using 'open' as default
        # All players can register for 'open' tournaments, category restrictions handled at tournament level
        
        # Create registration
        registration = TournamentPlayer.objects.create(
            player_name=profile.user.username,
            rating=profile.rating or 1200,
            email=profile.user.email,
            phone=getattr(profile, 'phone', '') or '',
            category='open',  # Default category since PlayerProfile doesn't have category field
            tournament=tournament,
            status='registered',
            registered_at=timezone.now()
        )
        
        # Update tournament current players count
        tournament.current_players += 1
        tournament.save(update_fields=['current_players'])
        
        return JsonResponse({
            'success': True,
            'message': f'Successfully registered for {tournament.name}!',
            'registration_id': registration.id
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False, 
            'error': str(e)
        }, status=500)


@csrf_exempt
@login_required
def tournament_unregister_api(request, tournament_id):
    """API endpoint for tournament withdrawal"""
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    try:
        from ttsaadmin.models import Tournament, TournamentPlayer
        
        # Get tournament
        tournament = get_object_or_404(Tournament, id=tournament_id)
        
        # Get player profile
        profile = get_object_or_404(PlayerProfile, user=request.user)
        
        # Find registration
        registration = TournamentPlayer.objects.filter(
            player_name=profile.user.username, 
            tournament=tournament
        ).first()
        
        if not registration:
            return JsonResponse({
                'success': False, 
                'error': 'You are not registered for this tournament'
            }, status=400)
        
        # Check if tournament has already started
        if tournament.start_date <= timezone.now():
            return JsonResponse({
                'success': False, 
                'error': 'Cannot withdraw after tournament has started'
            }, status=400)
        
        # Update registration status
        registration.status = 'withdrawn'
        registration.withdrawn_at = timezone.now()
        registration.save()
        
        # Update tournament current players count
        tournament.current_players = max(0, tournament.current_players - 1)
        tournament.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Successfully withdrawn from {tournament.name}'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False, 
            'error': str(e)
        }, status=500)


@login_required
def my_tournaments_api(request):
    """API endpoint for user's tournament registrations"""
    
    if request.method != 'GET':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    try:
        profile = get_object_or_404(PlayerProfile, user=request.user)
        
        registrations = TournamentPlayer.objects.filter(
            player_name=profile.user.username
        ).select_related('tournament').order_by('-registered_at')
        
        registrations_list = []
        for registration in registrations:
            tournament = registration.tournament
            registrations_list.append({
                'id': registration.id,
                'tournament_id': tournament.id,
                'tournament_name': tournament.name,
                'venue': tournament.venue,
                'category': tournament.category,
                'format': tournament.format,
                'start_date': tournament.start_date.isoformat(),
                'end_date': tournament.end_date.isoformat(),
                'registration_deadline': tournament.registration_deadline.isoformat(),
                'entry_fee': float(tournament.entry_fee),
                'status': registration.status,
                'registered_at': registration.registered_at.isoformat(),
                'confirmed_at': registration.confirmed_at.isoformat() if registration.confirmed_at else None,
                'withdrawn_at': registration.withdrawn_at.isoformat() if registration.withdrawn_at else None,
                'points': float(registration.points),
                'wins': registration.wins,
                'losses': registration.losses,
                'draws': registration.draws,
                'rank': registration.rank,
                'tournament_status': tournament.status,
                'is_registration_open': tournament.is_registration_open,
                'is_full': tournament.is_full,
            })
        
        return JsonResponse({
            'success': True,
            'registrations': registrations_list,
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False, 
            'error': str(e)
        }, status=500)


def tournament_results(request, tournament_id):
    """Display tournament results and standings"""
    
    try:
        from ttsaadmin.models import Tournament, TournamentPlayer, TournamentGame, TournamentStanding
        
        # Get tournament
        tournament = get_object_or_404(Tournament, id=tournament_id, is_active=True)
        
        # Get all registered players with their stats
        players = TournamentPlayer.objects.filter(
            tournament=tournament,
            status='registered'
        ).order_by('-points', '-wins', '-draws', 'rank')
        
        # Calculate standings if not already calculated
        standings = TournamentStanding.objects.filter(
            tournament=tournament
        ).order_by('rank')
        
        # If no standings exist, create basic standings from player data
        if not standings.exists():
            standings_list = []
            for i, player in enumerate(players, 1):
                standings_list.append({
                    'rank': i,
                    'player_name': player.player_name,
                    'rating': player.rating,
                    'points': player.points,
                    'wins': player.wins,
                    'losses': player.losses,
                    'draws': player.draws,
                    'games_played': player.wins + player.losses + player.draws,
                    'score_percentage': (player.points / (player.wins + player.losses + player.draws) * 100) if (player.wins + player.losses + player.draws) > 0 else 0
                })
        else:
            standings_list = []
            for standing in standings:
                standings_list.append({
                    'rank': standing.rank,
                    'player_name': standing.player.player_name,
                    'rating': standing.player.rating,
                    'points': standing.points,
                    'wins': standing.wins,
                    'losses': standing.losses,
                    'draws': standing.draws,
                    'games_played': standing.games_played,
                    'score_percentage': standing.score_percentage,
                    'tie_breaks': standing.tie_breaks
                })
        
        # Get recent games for this tournament
        recent_games = TournamentGame.objects.filter(
            tournament=tournament
        ).order_by('-scheduled_time')[:10]
        
        context = {
            'tournament': tournament,
            'standings': standings_list,
            'players_count': players.count(),
            'recent_games': recent_games,
            'is_completed': tournament.status in ['completed', 'finished']
        }
        
        return render(request, 'ttsa_app/tournament_results.html', context)
        
    except Exception as e:
        logger.error(f"Error in tournament_results: {str(e)}")
        messages.error(request, 'Unable to load tournament results. Please try again.')
        return redirect('tournaments')


# Player Plus Tournament Management Views

@login_required
def player_tournament_list(request):
    """List tournaments owned by the current Player Plus user (admins see all)."""
    if not request.user.can_manage_tournaments:
        messages.error(request, 'You do not have permission to manage tournaments.')
        return redirect('tournaments')

    if request.user.is_ttsa_admin:
        tournaments = Tournament.objects.all()
    else:
        tournaments = Tournament.objects.filter(created_by=request.user)

    tournaments = tournaments.prefetch_related('tournament_rounds', 'players').order_by('-created_at')
    paginator = Paginator(tournaments, 12)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    for tournament in page_obj:
        rounds = list(tournament.tournament_rounds.order_by('round_number'))
        registered = tournament.players.filter(status='registered').count()
        if rounds:
            latest = rounds[-1]
            tournament.round_label = f"Round {latest.round_number} of {tournament.rounds}"
            tournament.round_status = latest.get_status_display() or latest.status
            tournament.can_generate_round = (
                tournament.status not in ['completed', 'cancelled'] and
                latest.status == 'completed' and
                latest.round_number < tournament.rounds and
                registered >= 2
            )
        else:
            tournament.round_label = "No rounds"
            tournament.round_status = "Not started"
            tournament.can_generate_round = (
                tournament.status not in ['completed', 'cancelled'] and
                registered >= 2
            )

    return render(request, 'ttsa_app/tournament_management.html', {
        'profile': request.user.playerprofile,
        'page_obj': page_obj,
    })


@login_required
def player_tournament_create(request):
    """Create a new tournament from the TTSA app (Player Plus / Admin)."""
    if not request.user.can_manage_tournaments:
        messages.error(request, 'You do not have permission to create tournaments.')
        return redirect('tournaments')

    if request.method == 'POST':
        form = TournamentForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    tournament = form.save(commit=False)
                    tournament.created_by = request.user
                    tournament.current_players = 0
                    tournament.save()
                messages.success(request, f'Tournament "{tournament.name}" created successfully.')
                return redirect('player_tournament_manage', tournament_id=tournament.id)
            except Exception as e:
                messages.error(request, f'Error creating tournament: {str(e)}')
    else:
        form = TournamentForm(initial={'status': 'upcoming'})

    return render(request, 'ttsa_app/tournament_form.html', {
        'profile': request.user.playerprofile,
        'form': form,
        'title': 'Create Tournament',
    })


@login_required
@player_plus_tournament_access
def player_tournament_edit(request, tournament_id):
    """Edit an existing tournament (owner or admin)."""
    tournament = get_object_or_404(Tournament, id=tournament_id)

    if request.method == 'POST':
        form = TournamentForm(request.POST, instance=tournament)
        if form.is_valid():
            try:
                tournament = form.save()
                messages.success(request, f'Tournament "{tournament.name}" updated successfully.')
                return redirect('player_tournament_manage', tournament_id=tournament.id)
            except Exception as e:
                messages.error(request, f'Error updating tournament: {str(e)}')
    else:
        form = TournamentForm(instance=tournament)

    return render(request, 'ttsa_app/tournament_form.html', {
        'profile': request.user.playerprofile,
        'form': form,
        'title': 'Edit Tournament',
        'tournament': tournament,
    })


@login_required
@player_plus_tournament_access
@require_POST
def player_tournament_delete(request, tournament_id):
    """Delete a tournament (owner or admin)."""
    tournament = get_object_or_404(Tournament, id=tournament_id)
    tournament_name = tournament.name
    tournament.delete()
    messages.success(request, f'Tournament "{tournament_name}" deleted successfully.')
    return redirect('player_tournament_list')


@login_required
@player_plus_tournament_access
def player_tournament_manage(request, tournament_id):
    """Central management page for a tournament: players, rounds, results, standings."""
    tournament = get_object_or_404(
        Tournament.objects.prefetch_related('players', 'tournament_rounds'),
        id=tournament_id
    )
    tab = request.POST.get('tab') or request.GET.get('tab', 'overview')

    # Pre-load rounds and games so POST actions can enforce round locking.
    games = tournament.games.select_related('white_player', 'black_player').order_by('round_number', 'board_number')
    rounds = {r.round_number: r for r in tournament.tournament_rounds.all()}

    if request.method == 'POST':
        action = request.POST.get('action')
        extra_round = None  # used to keep the rounds tab on the active round after POST

        if action == 'add_player':
            form = TournamentPlayerForm(request.POST)
            if form.is_valid():
                player_name = form.cleaned_data['player_name']
                if tournament.players.filter(player_name__iexact=player_name).exists():
                    messages.error(request, f'A player named "{player_name}" already exists in this tournament.')
                else:
                    try:
                        with transaction.atomic():
                            player = form.save(commit=False)
                            player.tournament = tournament
                            player.save()
                            tournament.current_players = tournament.players.filter(status='registered').count()
                            tournament.save()
                        messages.success(request, f'Player "{player.player_name}" added successfully.')
                    except IntegrityError:
                        messages.error(request, f'A player named "{player_name}" already exists in this tournament.')
                    except Exception as e:
                        logger.error(f"Error adding player: {e}")
                        messages.error(request, 'An error occurred while adding the player. Please try again.')
            else:
                messages.error(request, 'Please correct the player form and try again.')

        elif action == 'remove_player':
            player_id = request.POST.get('player_id')
            player = get_object_or_404(TournamentPlayer, id=player_id, tournament=tournament)
            player_name = player.player_name
            player.delete()
            tournament.current_players = tournament.players.filter(status='registered').count()
            tournament.save()
            messages.success(request, f'Player "{player_name}" removed successfully.')

        elif action == 'generate_next_round':
            try:
                pairing_manager = get_pairing_manager()
                result = pairing_manager.generate_next_round(tournament)
                if result['success']:
                    if tournament.status != 'ongoing':
                        tournament.status = 'ongoing'
                        tournament.save(update_fields=['status'])
                    messages.success(request, result['message'])
                else:
                    messages.error(request, result.get('error', 'Failed to generate pairings.'))
            except Exception as e:
                logger.error(f"Error generating next round: {e}")
                messages.error(request, 'An error occurred while generating pairings.')

        elif action == 'update_game_result':
            game_id = request.POST.get('game_id')
            result = request.POST.get('result')
            try:
                game = TournamentGame.objects.select_related('white_player', 'black_player').get(id=int(game_id), tournament=tournament)
            except (ValueError, TournamentGame.DoesNotExist):
                messages.error(request, 'Game not found.')
            else:
                extra_round = game.round_number
                round_obj = rounds.get(game.round_number)
                # A round is locked once it has been submitted (completed) or any of its games are completed.
                round_locked = round_obj and round_obj.status == 'completed'
                if round_locked:
                    messages.error(request, f'Round {game.round_number} has already been submitted and cannot be edited.')
                elif result in dict(TournamentGame.RESULT_CHOICES):
                    success = PairingDataConverter.update_game_result(int(game_id), result)
                    if success:
                        messages.success(request, 'Game result updated.')
                    else:
                        messages.error(request, 'Failed to update game result.')
                else:
                    messages.error(request, 'Invalid game result.')

        elif action == 'submit_round':
            round_number = request.POST.get('round_number')
            try:
                rn = int(round_number)
                extra_round = rn
                pairing_manager = get_pairing_manager()
                result = pairing_manager.submit_round_results(tournament, rn)
                if result['success']:
                    if rn >= tournament.rounds:
                        tournament.status = 'completed'
                        tournament.save(update_fields=['status'])
                    messages.success(request, result['message'])
                else:
                    messages.error(request, result.get('error', 'Failed to submit round.'))
            except Exception as e:
                logger.error(f"Error submitting round: {e}")
                messages.error(request, 'An error occurred while submitting round results.')

        elif action == 'reset_round':
            round_number = request.POST.get('round_number')
            try:
                rn = int(round_number)
            except (ValueError, TypeError):
                messages.error(request, 'Invalid round number.')
            else:
                extra_round = rn
                if not request.user.is_ttsa_admin:
                    messages.error(request, 'Only TTSA administrators can reset a submitted round.')
                else:
                    round_obj = rounds.get(rn)
                    if not round_obj:
                        messages.error(request, f'Round {rn} does not exist.')
                    elif round_obj.status != 'completed':
                        messages.error(request, f'Round {rn} is not submitted, so it does not need to be reset.')
                    elif rn != max(rounds.keys(), default=0):
                        messages.error(request, 'Only the latest submitted round can be reset.')
                    else:
                        with transaction.atomic():
                            # Reset all games in this round to unplayed
                            TournamentGame.objects.filter(
                                tournament=tournament, round_number=rn
                            ).update(result='*', status='scheduled', completed_at=None)
                            # Unlock the round
                            round_obj.status = 'active'
                            round_obj.end_time = None
                            round_obj.save()
                            # Remove standings for this and later rounds
                            TournamentStanding.objects.filter(
                                tournament=tournament, round_number__gte=rn
                            ).delete()
                            # Re-open tournament if it was completed
                            if tournament.status == 'completed':
                                tournament.status = 'ongoing'
                                tournament.save(update_fields=['status'])
                        messages.success(request, f'Round {rn} has been reset and can now be edited.')

        elif action == 'delete_tournament':
            tournament_name = tournament.name
            tournament.delete()
            messages.success(request, f'Tournament "{tournament_name}" deleted successfully.')
            return redirect('player_tournament_list')

        redirect_url = f'/my-tournaments/{tournament_id}/?tab={tab}'
        if extra_round:
            redirect_url += f'&round={extra_round}'
        return redirect(redirect_url)

    # Build context per tab
    players = tournament.players.order_by('-points', '-buchholz', '-sonneborn_berger', 'player_name')

    grouped_games = {}
    for game in games:
        grouped_games.setdefault(game.round_number, []).append(game)

    round_numbers = sorted(grouped_games.keys())
    current_round = max(round_numbers) if round_numbers else 0

    # Build round data with locking info. A round is locked once it has been
    # submitted (status=completed). Rounds with no submitted results remain editable.
    round_data = []
    for rn in round_numbers:
        round_obj = rounds.get(rn, TournamentRound(round_number=rn, tournament=tournament))
        round_games = grouped_games[rn]
        is_locked = round_obj.status == 'completed' or any(g.status == 'completed' for g in round_games)
        has_results = any(g.result != '*' for g in round_games)
        all_results_set = all(g.result != '*' for g in round_games) and round_games
        round_data.append({
            'round_number': rn,
            'round': round_obj,
            'games': round_games,
            'is_locked': is_locked,
            'is_editable': not is_locked,
            'has_results': has_results,
            'all_results_set': all_results_set,
        })

    completed_games = games.filter(status='completed').count()

    # Determine if next round can be generated
    registered_players = tournament.players.filter(status='registered').count()
    can_generate = (
        tournament.status not in ['completed', 'cancelled'] and
        current_round < tournament.rounds and
        registered_players >= 2 and
        (current_round == 0 or rounds.get(current_round, TournamentRound()).status == 'completed')
    )
    can_submit = any(r.status == 'active' for r in rounds.values())

    player_form = TournamentPlayerForm()

    # Recalculate latest standings if any completed rounds exist
    standings = []
    latest_completed = tournament.tournament_rounds.filter(status='completed').order_by('-round_number').first()
    if latest_completed:
        standings_list = PairingDataConverter.recalculate_standings(tournament, latest_completed.round_number)
        for rank, standing in enumerate(standings_list, 1):
            standings.append({
                'rank': rank,
                'player': standing['player'],
                'points': float(standing['points']),
                'wins': standing['wins'],
                'draws': standing['draws'],
                'losses': standing['losses'],
                'games_played': standing['games_played'],
                'buchholz': float(standing['buchholz']),
                'sonneborn_berger': float(standing['sonneborn_berger']),
            })

    # Selected round for the rounds tab (default to the latest round)
    try:
        selected_round = int(request.GET.get('round'))
        if selected_round not in round_numbers:
            selected_round = current_round
    except (ValueError, TypeError):
        selected_round = current_round

    context = {
        'profile': request.user.playerprofile,
        'tournament': tournament,
        'tab': tab,
        'players': players,
        'games': games,
        'round_data': round_data,
        'round_numbers': round_numbers,
        'current_round': current_round,
        'selected_round': selected_round,
        'completed_games': completed_games,
        'player_form': player_form,
        'standings': standings,
        'result_choices': TournamentGame.RESULT_CHOICES,
        'can_generate': can_generate,
        'can_submit': can_submit,
        'is_admin': request.user.is_ttsa_admin,
    }

    return render(request, 'ttsa_app/tournament_manage.html', context)


@login_required
@player_plus_tournament_access
@csrf_exempt
def player_tournament_api_data(request, tournament_id):
    """API endpoint for tournament data (owner or admin)."""
    tournament = get_object_or_404(Tournament, id=tournament_id)

    players_data = []
    for player in tournament.players.all():
        players_data.append({
            'id': player.id,
            'player_name': player.player_name,
            'rating': player.rating,
            'points': float(player.points),
            'wins': player.wins,
            'losses': player.losses,
            'draws': player.draws,
            'status': player.status,
        })

    games_data = []
    for game in tournament.games.all():
        games_data.append({
            'id': game.id,
            'round_number': game.round_number,
            'board_number': game.board_number,
            'white_player': game.white_player.player_name,
            'black_player': game.black_player.player_name,
            'result': game.result,
            'status': game.status,
        })

    return JsonResponse({
        'success': True,
        'tournament': {
            'id': tournament.id,
            'name': tournament.name,
            'status': tournament.status,
            'current_players': tournament.current_players,
            'max_players': tournament.max_players,
            'rounds': tournament.rounds,
        },
        'players': players_data,
        'games': games_data,
    })


@login_required
@player_plus_tournament_access
def player_tournament_print_pairings(request, tournament_id):
    """Printable pairings for a tournament or a single round."""
    tournament = get_object_or_404(Tournament, id=tournament_id)
    games = tournament.games.select_related('white_player', 'black_player').order_by('round_number', 'board_number')

    round_param = request.GET.get('round')
    round_data = []
    if round_param:
        try:
            rn = int(round_param)
            filtered_games = [g for g in games if g.round_number == rn]
            if filtered_games:
                round_data = [{'round_number': rn, 'games': filtered_games}]
        except (ValueError, TypeError):
            pass

    if not round_data:
        grouped = {}
        for g in games:
            grouped.setdefault(g.round_number, []).append(g)
        round_data = [{'round_number': rn, 'games': grouped[rn]} for rn in sorted(grouped.keys())]

    context = {
        'tournament': tournament,
        'round_data': round_data,
    }
    return render(request, 'ttsa_app/tournament_print_pairings.html', context)


@login_required
@player_plus_tournament_access
def player_tournament_print_standings(request, tournament_id):
    """Printable tournament standings."""
    tournament = get_object_or_404(Tournament, id=tournament_id)

    standings = []
    latest_completed = tournament.tournament_rounds.filter(status='completed').order_by('-round_number').first()
    if latest_completed:
        standings_list = PairingDataConverter.recalculate_standings(tournament, latest_completed.round_number)
        for rank, standing in enumerate(standings_list, 1):
            standings.append({
                'rank': rank,
                'player': standing['player'],
                'points': float(standing['points']),
                'wins': standing['wins'],
                'draws': standing['draws'],
                'losses': standing['losses'],
                'games_played': standing['games_played'],
                'buchholz': float(standing['buchholz']),
                'sonneborn_berger': float(standing['sonneborn_berger']),
            })

    context = {
        'tournament': tournament,
        'standings': standings,
        'round_number': latest_completed.round_number if latest_completed else None,
    }
    return render(request, 'ttsa_app/tournament_print_standings.html', context)
