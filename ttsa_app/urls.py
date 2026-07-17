from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('signup/', views.signup, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='chess_game'), name='logout'),
    
        path('game/', views.chess_game, name='chess_game'),
    
    path('lessons/', views.lessons, name='lessons'),
    path('lessons/<int:lesson_id>/', views.lesson_detail, name='lesson_detail'),
    
    path('video-lessons/', views.video_lessons, name='video_lessons'),
    
    path('puzzles/', views.puzzles, name='puzzles'),
    path('achievements/', views.achievements, name='achievements'),
    path('tournaments/', views.tournaments_view, name='tournaments'),
    path('tournaments/<int:tournament_id>/results/', views.tournament_results, name='tournament_results'),
    path('leaderboard/', views.leaderboard, name='leaderboard'),
    path('friends/', views.friends, name='friends'),
    path('messages/', views.messages_view, name='messages'),
    path('news/', views.news, name='news'),
    path('settings/', views.settings_view, name='settings'),
    path('settings/change-username/', views.change_username, name='change_username'),
    path('settings/change-password/', views.change_password, name='change_password'),
    path('settings/apply-player-plus/', views.apply_player_plus, name='apply_player_plus'),
    
    # Role API endpoint
    path('api/user-role/', views.user_role_api, name='user_role_api'),
    
    # Multiplayer game URLs
    path('multiplayer/create/', views.multiplayer_create, name='multiplayer_create'),
    path('multiplayer/game/<str:game_code>/', views.multiplayer_game, name='multiplayer_game'),
    
    # Multiplayer API endpoints
    path('api/multiplayer/create/', views.multiplayer_create_api, name='multiplayer_create_api'),
    path('api/multiplayer/status/<str:game_code>/', views.multiplayer_status_api, name='multiplayer_status_api'),
    path('api/multiplayer/cancel/<str:game_code>/', views.multiplayer_cancel_api, name='multiplayer_cancel_api'),
    
    # Tournament API endpoints
    path('api/tournaments/', views.tournaments_api, name='tournaments_api'),
    path('api/tournaments/<int:tournament_id>/register/', views.tournament_register_api, name='tournament_register_api'),
    path('api/tournaments/<int:tournament_id>/unregister/', views.tournament_unregister_api, name='tournament_unregister_api'),
    path('api/my-tournaments/', views.my_tournaments_api, name='my_tournaments_api'),

    # Player Plus tournament management (stays inside ttsa_app)
    path('my-tournaments/', views.player_tournament_list, name='player_tournament_list'),
    path('my-tournaments/create/', views.player_tournament_create, name='player_tournament_create'),
    path('my-tournaments/<int:tournament_id>/', views.player_tournament_manage, name='player_tournament_manage'),
    path('my-tournaments/<int:tournament_id>/edit/', views.player_tournament_edit, name='player_tournament_edit'),
    path('my-tournaments/<int:tournament_id>/delete/', views.player_tournament_delete, name='player_tournament_delete'),
    path('my-tournaments/<int:tournament_id>/print/pairings/', views.player_tournament_print_pairings, name='player_tournament_print_pairings'),
    path('my-tournaments/<int:tournament_id>/print/standings/', views.player_tournament_print_standings, name='player_tournament_print_standings'),
    path('api/my-tournaments/<int:tournament_id>/', views.player_tournament_api_data, name='player_tournament_api_data'),
    
    # API endpoints
    path('api/save-game/', views.save_game, name='save_game'),
    path('api/complete-lesson/<int:lesson_id>/', views.complete_lesson, name='complete_lesson'),
    path('api/lesson-progress/', views.lesson_progress, name='lesson_progress'),
    path('api/lesson-recommendations/', views.lesson_recommendations, name='lesson_recommendations'),
    path('api/solve-puzzle/<int:puzzle_id>/', views.solve_puzzle, name='solve_puzzle'),
    path('api/stockfish-move/', views.stockfish_move, name='stockfish_move'),
]
