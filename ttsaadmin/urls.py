from django.urls import path
from . import views

urlpatterns = [
    path('', views.admin_dashboard, name='admin_dashboard'),
    path('youtube-channels/add/', views.add_youtube_channel, name='add_youtube_channel'),
    path('youtube-channels/', views.youtube_channels_list, name='youtube_channels_list'),
    path('youtube-channels/<int:channel_id>/delete/', views.delete_youtube_channel, name='delete_youtube_channel'),
    path('api/validate-channel/', views.validate_channel_api, name='validate_channel_api'),
    path('video-lessons/add/', views.add_video_lesson, name='add_video_lesson'),
    path('video-lessons/', views.video_library, name='video_library'),
    path('video-lessons/<int:video_id>/delete/', views.delete_video_lesson, name='delete_video_lesson'),
    path('api/validate-video/', views.validate_video_api, name='validate_video_api'),
]
