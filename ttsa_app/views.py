from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, update_session_auth_hash
from django.contrib.auth.forms import UserCreationForm, PasswordChangeForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta
from functools import wraps
from django.db import models
from django.views.decorators.csrf import csrf_exempt
from .models import (
    PlayerProfile, Achievement, PlayerAchievement, ChessGame,
    Lesson, PlayerLesson, Puzzle,	PlayerPuzzle, Leaderboard,
    Friend, Message, AcademyNews, MultiplayerGame, GameMove, VideoLesson, TournamentRegistration
)
from .stockfish_service import stockfish_service, DifficultyLevel
import random
import json
import secrets
import string


# Custom decorator for social features that require authentication
def login_required_with_message(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.info(request, 'This feature requires an account. Sign up to connect with friends, join tournaments, and access all social features!')
            return redirect('signup')
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def home(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    # Redirect guests to the chess game page for instant access
    return redirect('chess_game')


@login_required
def dashboard(request):
    profile, created = PlayerProfile.objects.get_or_create(user=request.user)
    
    # Get recent games
    recent_games = ChessGame.objects.filter(player=profile).order_by('-created_at')[:5]
    
    # Get achievements
    achievements = PlayerAchievement.objects.filter(player=profile).select_related('achievement')
    
    # Get learning streak
    if profile.last_played == timezone.now().date():
        profile.learning_streak += 1
    elif profile.last_played < timezone.now().date() - timedelta(days=1):
        profile.learning_streak = 1
    profile.save()
    
    # Get lessons progress
    completed_lessons = PlayerLesson.objects.filter(player=profile, completed=True).count()
    total_lessons = Lesson.objects.count()
    
    # Get news
    news = AcademyNews.objects.all().order_by('-published_at')[:3]
    
    context = {
        'profile': profile,
        'recent_games': recent_games,
        'achievements': achievements,
        'completed_lessons': completed_lessons,
        'total_lessons': total_lessons,
        'news': news,
    }
    return render(request, 'ttsa_app/dashboard.html', context)


def chess_game(request):
    difficulty = request.GET.get('difficulty', 'intermediate')
    
    # Handle both authenticated and guest users
    if request.user.is_authenticated:
        profile = request.user.playerprofile
        is_guest = False
    else:
        profile = None
        is_guest = True
    
    # Get current difficulty info - 3 main levels
    difficulty_info = {
        'beginner': {'name': 'Beginner', 'description': 'Perfect for learning the basics - Stockfish skill level 0'},
        'intermediate': {'name': 'Intermediate', 'description': 'Challenging gameplay - Stockfish skill level 10'},
        'master': {'name': 'Master', 'description': 'Test your skills against the best - Stockfish maximum strength with multi-threaded analysis'}
    }
    
    current_difficulty = difficulty_info.get(difficulty, difficulty_info['intermediate'])
    
    context = {
        'profile': profile,
        'is_guest': is_guest,
        'difficulty': difficulty,
        'current_difficulty_name': current_difficulty['name'],
        'current_difficulty_description': current_difficulty['description'],
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


def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            messages.success(request, f'Welcome back, {username}!')
            
            # Check if user is a TTSA admin and redirect accordingly
            try:
                profile = user.playerprofile
                if profile.ttsa_admin:
                    return redirect('admin_dashboard')
            except PlayerProfile.DoesNotExist:
                pass
            
            return redirect('dashboard')
        else:
            messages.error(request, 'Invalid username or password.')
    
    return render(request, 'ttsa_app/login.html')


def signup(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
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
            return redirect('dashboard')
    else:
        form = UserCreationForm()
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
            
            # Map difficulty string to enum - 3 main levels
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
@login_required
def multiplayer_create(request):
    """Render the game creation page"""
    return render(request, 'ttsa_app/multiplayer_create.html')


@login_required
@csrf_exempt
def multiplayer_create_api(request):
    """API endpoint to create a new multiplayer game"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=400)
    
    try:
        data = json.loads(request.body)
        
        # Generate unique game code
        while True:
            game_code = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))
            if not MultiplayerGame.objects.filter(game_code=game_code).exists():
                break
        
        # Handle color assignment
        color_preference = data.get('color_preference', 'random')
        if color_preference == 'random':
            color_preference = random.choice(['white', 'black'])
        
        # Create game
        game = MultiplayerGame.objects.create(
            game_code=game_code,
            white_player=request.user,
            game_type=data.get('game_type', 'standard'),
            visibility=data.get('visibility', 'private'),
            rated=data.get('rated', False),
            color_preference=color_preference
        )
        
        return JsonResponse({
            'success': True,
            'game_id': game.id,
            'game_code': game_code
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
def multiplayer_game(request, game_code):
    """Render the multiplayer game page"""
    game = get_object_or_404(MultiplayerGame, game_code=game_code)
    
    # Check if user is part of this game
    if game.white_player != request.user and game.black_player != request.user:
        # If game is waiting for opponent, let user join as black
        if game.status == 'waiting' and game.black_player is None:
            game.black_player = request.user
            game.status = 'playing'
            game.started_at = timezone.now()
            # Clock will start on first move, not here
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
    
    # Only allow creator to cancel
    if game.white_player != request.user:
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
    return render(request, 'ttsa_app/tournaments.html')


@csrf_exempt
def tournaments_api(request):
    """API endpoint for tournaments data - public access for viewing tournaments"""
    
    if request.method == 'GET':
        from ttsaadmin.models import Tournament
        from django.db.models import Q
        
        # Get only published/registration tournaments for public view
        tournaments = Tournament.objects.filter(
            status__in=['published', 'registration'],
            is_active=True
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
        
        # Order by start date (upcoming first)
        tournaments = tournaments.order_by('start_date')
        
        tournaments_list = []
        for tournament in tournaments:
            # Check if current user is registered
            is_registered = False
            if request.user.is_authenticated:
                try:
                    profile = request.user.playerprofile
                    is_registered = TournamentRegistration.objects.filter(
                        player=profile, 
                        tournament=tournament
                    ).exists()
                except PlayerProfile.DoesNotExist:
                    pass
            
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
                'is_registration_open': tournament.is_registration_open,
                'is_full': tournament.is_full,
                'is_registered': is_registered,
            })
        
        return JsonResponse({
            'success': True,
            'tournaments': tournaments_list,
        })
    
    return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)


@csrf_exempt
@login_required
def tournament_register_api(request, tournament_id):
    """API endpoint for tournament registration"""
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    try:
        from ttsaadmin.models import Tournament
        
        # Get tournament
        tournament = get_object_or_404(Tournament, id=tournament_id)
        
        # Get player profile
        profile = get_object_or_404(PlayerProfile, user=request.user)
        
        # Check if registration is still open
        if not tournament.is_registration_open:
            return JsonResponse({
                'success': False, 
                'error': 'Registration is closed for this tournament'
            }, status=400)
        
        # Check if tournament is full
        if tournament.is_full:
            return JsonResponse({
                'success': False, 
                'error': 'Tournament is full'
            }, status=400)
        
        # Check if already registered
        existing_registration = TournamentRegistration.objects.filter(
            player=profile, 
            tournament=tournament
        ).first()
        
        if existing_registration:
            return JsonResponse({
                'success': False, 
                'error': 'You are already registered for this tournament'
            }, status=400)
        
        # Create registration
        registration = TournamentRegistration.objects.create(
            player=profile,
            tournament=tournament,
            status='registered'
        )
        
        # Update tournament current players count
        tournament.current_players += 1
        tournament.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Successfully registered for {tournament.name}',
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
        from ttsaadmin.models import Tournament
        
        # Get tournament
        tournament = get_object_or_404(Tournament, id=tournament_id)
        
        # Get player profile
        profile = get_object_or_404(PlayerProfile, user=request.user)
        
        # Find registration
        registration = TournamentRegistration.objects.filter(
            player=profile, 
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
        
        registrations = TournamentRegistration.objects.filter(
            player=profile
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
