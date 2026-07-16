from django.urls import path
from . import views

urlpatterns = [
    path('', views.admin_dashboard, name='admin_dashboard'),
    path('youtube-channels/add/', views.add_youtube_channel, name='add_youtube_channel'),
    path('youtube-channels/', views.youtube_channels_list, name='youtube_channels_list'),
    path('youtube-channels/<int:channel_id>/delete/', views.delete_youtube_channel, name='delete_youtube_channel'),
    path('api/validate-channel/', views.validate_channel_api, name='validate_channel_api'),
    path('api/sync-channel-videos/', views.sync_channel_videos, name='sync_channel_videos'),
    path('api/notifications/', views.get_notifications, name='get_notifications'),
    path('api/notifications/<int:notification_id>/read/', views.mark_notification_read, name='mark_notification_read'),
    path('video-lessons/add/', views.add_video_lesson, name='add_video_lesson'),
    path('video-lessons/', views.video_library, name='video_library'),
    path('video-lessons/<int:video_id>/delete/', views.delete_video_lesson, name='delete_video_lesson'),
    path('api/validate-video/', views.validate_video_api, name='validate_video_api'),
    
    # Tournament URLs
    path('tournaments/', views.tournament_list, name='tournament_list'),
    path('tournaments/create/', views.tournament_create, name='tournament_create'),
    path('tournaments/<int:tournament_id>/', views.tournament_detail, name='tournament_detail'),
    path('tournaments/<int:tournament_id>/edit/', views.tournament_edit, name='tournament_edit'),
    path('tournaments/<int:tournament_id>/delete/', views.tournament_delete, name='tournament_delete'),
    path('tournaments/<int:tournament_id>/players/', views.tournament_players, name='tournament_players'),
    path('tournaments/<int:tournament_id>/players/<int:player_id>/remove/', views.tournament_remove_player, name='tournament_remove_player'),
    path('tournaments/<int:tournament_id>/games/', views.tournament_games, name='tournament_games'),
    path('tournaments/<int:tournament_id>/games/<int:game_id>/result/', views.tournament_update_game_result, name='tournament_update_game_result'),
    path('api/tournaments/', views.tournament_api_data, name='tournament_api_data'),
    path('api/tournaments/<int:tournament_id>/', views.tournament_api_data, name='tournament_api_detail'),
    
    # Round Management URLs
    path('api/tournaments/<int:tournament_id>/rounds/', views.tournament_rounds_api, name='tournament_rounds_api'),
    path('api/tournaments/<int:tournament_id>/generate-next-round/', views.generate_next_round, name='generate_next_round'),
    path('api/tournaments/<int:tournament_id>/games/', views.tournament_games_api, name='tournament_games_api'),
    path('api/tournaments/<int:tournament_id>/games/<int:round_number>/', views.tournament_games_api, name='tournament_games_round'),
    path('api/tournaments/<int:tournament_id>/standings/', views.tournament_standings_api, name='tournament_standings_api'),
    path('api/tournaments/<int:tournament_id>/standings/<int:round_number>/', views.tournament_standings_api, name='tournament_standings_round'),
    path('api/tournaments/<int:tournament_id>/print-pairings/<int:round_number>/', views.print_pairings, name='print_pairings'),
    path('api/tournaments/<int:tournament_id>/print-standings/', views.print_standings, name='print_standings'),
    path('api/tournaments/<int:tournament_id>/print-standings/<int:round_number>/', views.print_standings, name='print_standings_round'),
]
