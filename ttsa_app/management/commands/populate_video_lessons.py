from django.core.management.base import BaseCommand
from ttsa_app.models import VideoLesson


class Command(BaseCommand):
    help = 'Populate the database with chess video lessons from YouTube'

    def handle(self, *args, **kwargs):
        video_data = [
            {
                'title': 'How To Play Chess: The Ultimate Beginner Guide',
                'description': 'Complete beginner guide to chess. Learn all the rules, piece movements, and basic strategies to start playing chess. Covers board setup, piece movements, check & checkmate, openings, tactics basics, endgames, and study plan.',
                'youtube_id': 'OCSbzArwB10',
                'thumbnail_url': 'https://img.youtube.com/vi/OCSbzArwB10/hqdefault.jpg',
                'channel_name': 'GothamChess',
                'duration': '31:26',
                'category': 'basics',
                'difficulty': 'beginner',
                'order': 1
            },
            {
                'title': 'Chess Tactics Explained: CRUSH Your Opponents Using FORKS!',
                'description': 'Master the fork tactic, one of the most powerful tactical motifs in chess. Learn how to identify fork opportunities and execute them effectively to win material and games.',
                'youtube_id': 'diRaiqF06eY',
                'thumbnail_url': 'https://img.youtube.com/vi/diRaiqF06eY/hqdefault.jpg',
                'channel_name': 'Chess.com',
                'duration': '12:30',
                'category': 'tactics',
                'difficulty': 'beginner',
                'order': 2
            },
            {
                'title': 'Chess Endgames- King and Pawn',
                'description': 'Essential endgame knowledge for every chess player. Learn the key positions and techniques to win or draw king and pawn endgames, including opposition and key concepts.',
                'youtube_id': 'V-UcVihtK9M',
                'thumbnail_url': 'https://img.youtube.com/vi/V-UcVihtK9M/hqdefault.jpg',
                'channel_name': 'ChessNetwork',
                'duration': '18:45',
                'category': 'endgames',
                'difficulty': 'beginner',
                'order': 3
            },
            {
                'title': 'Italian Game Every Single Line Explained',
                'description': 'Learn the Italian Game, one of the oldest and most classical chess openings. This video covers the main lines, key ideas, and typical plans for both white and black, including Fried Liver Attack and common variations.',
                'youtube_id': 'ALwL52J8IV4',
                'thumbnail_url': 'https://img.youtube.com/vi/ALwL52J8IV4/hqdefault.jpg',
                'channel_name': 'Remote Chess Academy',
                'duration': '20:49',
                'category': 'openings',
                'difficulty': 'beginner',
                'order': 4
            },
            {
                'title': 'Give Me 19 Minutes and I\'ll Teach You How to Beat Everyone at Chess',
                'description': 'Comprehensive chess tutorial covering essential strategies, tactics, and techniques to improve your game and beat opponents of all skill levels.',
                'youtube_id': 'V_94QGEzVc4',
                'thumbnail_url': 'https://img.youtube.com/vi/V_94QGEzVc4/hqdefault.jpg',
                'channel_name': 'Chess Creator',
                'duration': '19:00',
                'category': 'strategy',
                'difficulty': 'beginner',
                'order': 5
            },
        ]
        
        created_count = 0
        updated_count = 0
        deleted_count = 0
        
        # Get the YouTube IDs from the current video data
        current_youtube_ids = {video['youtube_id'] for video in video_data}
        
        # Delete any videos not in the current list
        existing_videos = VideoLesson.objects.exclude(youtube_id__in=current_youtube_ids)
        deleted_count = existing_videos.count()
        if deleted_count > 0:
            existing_videos.delete()
            self.stdout.write(self.style.WARNING(f'Deleted {deleted_count} videos not in current list'))
        
        # Create or update the current videos
        for video in video_data:
            obj, created = VideoLesson.objects.update_or_create(
                youtube_id=video['youtube_id'],
                defaults=video
            )
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'Created video: {video["title"]}'))
            else:
                updated_count += 1
                self.stdout.write(self.style.WARNING(f'Updated video: {video["title"]}'))
        
        self.stdout.write(self.style.SUCCESS(f'\nSummary: {created_count} videos created, {updated_count} videos updated, {deleted_count} videos deleted'))
