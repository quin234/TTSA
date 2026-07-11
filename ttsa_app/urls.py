from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('signup/', views.signup, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='chess_game'), name='logout'),
    
    path('dashboard/', views.dashboard, name='dashboard'),
    path('game/', views.chess_game, name='chess_game'),
    
    path('lessons/', views.lessons, name='lessons'),
    path('lessons/<int:lesson_id>/', views.lesson_detail, name='lesson_detail'),
    
    path('video-lessons/', views.video_lessons, name='video_lessons'),
    
    path('puzzles/', views.puzzles, name='puzzles'),
    path('achievements/', views.achievements, name='achievements'),
    path('leaderboard/', views.leaderboard, name='leaderboard'),
    path('friends/', views.friends, name='friends'),
    path('messages/', views.messages_view, name='messages'),
    path('news/', views.news, name='news'),
    path('settings/', views.settings_view, name='settings'),
    path('settings/change-username/', views.change_username, name='change_username'),
    path('settings/change-password/', views.change_password, name='change_password'),
    
    # Multiplayer game URLs
    path('multiplayer/create/', views.multiplayer_create, name='multiplayer_create'),
    path('multiplayer/game/<int:game_id>/', views.multiplayer_game, name='multiplayer_game'),
    
    # Multiplayer API endpoints
    path('api/multiplayer/create/', views.multiplayer_create_api, name='multiplayer_create_api'),
    path('api/multiplayer/status/<int:game_id>/', views.multiplayer_status_api, name='multiplayer_status_api'),
    path('api/multiplayer/cancel/<int:game_id>/', views.multiplayer_cancel_api, name='multiplayer_cancel_api'),
    
    # API endpoints
    path('api/save-game/', views.save_game, name='save_game'),
    path('api/complete-lesson/<int:lesson_id>/', views.complete_lesson, name='complete_lesson'),
    path('api/lesson-progress/', views.lesson_progress, name='lesson_progress'),
    path('api/lesson-recommendations/', views.lesson_recommendations, name='lesson_recommendations'),
    path('api/solve-puzzle/<int:puzzle_id>/', views.solve_puzzle, name='solve_puzzle'),
    path('api/stockfish-move/', views.stockfish_move, name='stockfish_move'),
]
