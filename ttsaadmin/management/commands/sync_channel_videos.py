"""Django management command to sync videos from YouTube channels to VideoLesson model"""
from django.core.management.base import BaseCommand
from django.db import transaction
from ttsaadmin.models import YouTubeChannel
from ttsaadmin.youtube_utils import fetch_channel_videos, YouTubeChannelError
from ttsa_app.models import VideoLesson
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Sync videos from all active YouTube channels to VideoLesson model'

    def add_arguments(self, parser):
        parser.add_argument(
            '--channel-id',
            type=str,
            help='Specific channel ID to sync (syncs all if not provided)',
        )
        parser.add_argument(
            '--max-videos',
            type=int,
            default=50,
            help='Maximum number of videos to fetch per channel (default: 50)',
        )
        parser.add_argument(
            '--category',
            type=str,
            default='strategy',
            help='Default category for synced videos (default: strategy)',
        )
        parser.add_argument(
            '--difficulty',
            type=str,
            default='intermediate',
            help='Default difficulty for synced videos (default: intermediate)',
        )

    def handle(self, *args, **options):
        channel_id = options.get('channel_id')
        max_videos = options.get('max_videos')
        category = options.get('category')
        difficulty = options.get('difficulty')

        # Validate category and difficulty
        valid_categories = ['openings', 'middlegame', 'endgames', 'tactics', 'strategy']
        valid_difficulties = ['beginner', 'intermediate', 'advanced']

        if category not in valid_categories:
            self.stdout.write(
                self.style.ERROR(f'Invalid category. Valid options: {valid_categories}')
            )
            return

        if difficulty not in valid_difficulties:
            self.stdout.write(
                self.style.ERROR(f'Invalid difficulty. Valid options: {valid_difficulties}')
            )
            return

        # Get channels to sync
        if channel_id:
            channels = YouTubeChannel.objects.filter(channel_id=channel_id, is_active=True)
            if not channels.exists():
                self.stdout.write(
                    self.style.ERROR(f'Channel with ID {channel_id} not found or not active')
                )
                return
        else:
            channels = YouTubeChannel.objects.filter(is_active=True)

        self.stdout.write(f'Found {channels.count()} channel(s) to sync')

        total_videos_added = 0
        total_videos_skipped = 0
        total_errors = 0

        for channel in channels:
            self.stdout.write(f'\nSyncing videos from channel: {channel.channel_name} ({channel.channel_id})')
            
            try:
                # Fetch videos from YouTube API
                videos = fetch_channel_videos(channel.channel_id, max_results=max_videos)
                self.stdout.write(f'Fetched {len(videos)} videos from YouTube API')
                
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
                                description=video_data['description'][:500],  # Truncate if too long
                                youtube_id=video_data['video_id'],
                                thumbnail_url=video_data['thumbnail_url'],
                                channel_name=video_data['channel_name'],
                                duration='',  # Duration would need additional API call
                                category=category,
                                difficulty=difficulty,
                                views=0,
                                order=0,
                            )
                            added_count += 1
                            
                    except Exception as e:
                        logger.error(f'Error processing video {video_data["video_id"]}: {str(e)}')
                        total_errors += 1
                
                total_videos_added += added_count
                total_videos_skipped += skipped_count
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Channel {channel.channel_name}: Added {added_count} videos, '
                        f'Skipped {skipped_count} existing videos'
                    )
                )
                
            except YouTubeChannelError as e:
                self.stdout.write(
                    self.style.ERROR(f'Error fetching videos for channel {channel.channel_name}: {str(e)}')
                )
                total_errors += 1
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Unexpected error for channel {channel.channel_name}: {str(e)}')
                )
                total_errors += 1

        # Summary
        self.stdout.write('\n' + '='*50)
        self.stdout.write('Sync Summary:')
        self.stdout.write(f'Total videos added: {total_videos_added}')
        self.stdout.write(f'Total videos skipped (already exist): {total_videos_skipped}')
        self.stdout.write(f'Total errors: {total_errors}')
        self.stdout.write('='*50)
        
        if total_videos_added > 0:
            self.stdout.write(self.style.SUCCESS('Video sync completed successfully!'))
        else:
            self.stdout.write(self.style.WARNING('No new videos were added'))
