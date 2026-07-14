"""Celery tasks for background video sync"""
from celery import shared_task
from django.db import transaction
from ttsaadmin.models import YouTubeChannel, SyncNotification
from ttsaadmin.youtube_utils import fetch_channel_videos, YouTubeChannelError
from ttsa_app.models import VideoLesson
from django.contrib.auth.models import User
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def sync_channel_videos_task(self, channel_id=None, category='strategy', difficulty='intermediate', user_id=None):
    """
    Celery task to sync videos from YouTube channels to VideoLesson model
    Runs in background with no limit on number of videos
    """
    # Get user for notifications
    user = None
    if user_id:
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            logger.error(f'User with ID {user_id} not found')
    
    # Create sync started notification
    task_id = self.request.id
    if user:
        SyncNotification.objects.create(
            user=user,
            notification_type='sync_started',
            title='Video Sync Started',
            message='Background video sync has started. Videos will be added as they are processed.',
            task_id=task_id
        )
    
    # Get channels to sync
    if channel_id:
        channels = YouTubeChannel.objects.filter(channel_id=channel_id, is_active=True)
        if not channels.exists():
            logger.error(f'Channel with ID {channel_id} not found or not active')
            if user:
                SyncNotification.objects.create(
                    user=user,
                    notification_type='sync_failed',
                    title='Sync Failed',
                    message=f'Channel with ID {channel_id} not found or not active',
                    task_id=task_id
                )
            return {'success': False, 'error': f'Channel with ID {channel_id} not found or not active'}
    else:
        channels = YouTubeChannel.objects.filter(is_active=True)

    logger.info(f'Starting video sync for {channels.count()} channel(s)')
    
    total_videos_added = 0
    total_videos_skipped = 0
    channel_results = []
    
    for channel in channels:
        logger.info(f'Syncing videos from channel: {channel.channel_name} ({channel.channel_id})')
        
        try:
            # Fetch all videos from YouTube API (no limit)
            videos = fetch_channel_videos(channel.channel_id, max_results=50)
            
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
                        logger.info(f'Added video: {video_data["title"]} ({video_data["video_id"]})')
                        
                        # Create notification for each video added
                        if user:
                            SyncNotification.objects.create(
                                user=user,
                                notification_type='video_added',
                                title=f'Video Added: {video_data["title"][:50]}...',
                                message=f'Added from {channel.channel_name}',
                                channel_name=channel.channel_name,
                                video_title=video_data['title'],
                                task_id=task_id
                            )
                        
                except Exception as e:
                    logger.error(f'Error processing video {video_data["video_id"]}: {str(e)}')
                    continue
            
            total_videos_added += added_count
            total_videos_skipped += skipped_count
            
            channel_results.append({
                'channel_name': channel.channel_name,
                'channel_id': channel.channel_id,
                'added': added_count,
                'skipped': skipped_count
            })
            
            logger.info(f'Channel {channel.channel_name}: Added {added_count} videos, Skipped {skipped_count} existing videos')
            
        except YouTubeChannelError as e:
            logger.error(f'Error fetching videos for channel {channel.channel_name}: {str(e)}')
            channel_results.append({
                'channel_name': channel.channel_name,
                'channel_id': channel.channel_id,
                'error': str(e)
            })
        except Exception as e:
            logger.error(f'Unexpected error for channel {channel.channel_name}: {str(e)}')
            channel_results.append({
                'channel_name': channel.channel_name,
                'channel_id': channel.channel_id,
                'error': str(e)
            })

    result = {
        'success': True,
        'total_videos_added': total_videos_added,
        'total_videos_skipped': total_videos_skipped,
        'channel_results': channel_results
    }
    
    logger.info(f'Video sync completed: Added {total_videos_added} videos, Skipped {total_videos_skipped} existing videos')
    
    # Create sync completed notification
    if user:
        SyncNotification.objects.create(
            user=user,
            notification_type='sync_completed',
            title='Video Sync Completed',
            message=f'Sync completed successfully. Added {total_videos_added} videos, skipped {total_videos_skipped} existing videos.',
            task_id=task_id,
            videos_added=total_videos_added,
            videos_skipped=total_videos_skipped
        )
    
    return result
