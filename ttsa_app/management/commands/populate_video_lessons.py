from django.core.management.base import BaseCommand
from ttsa_app.models import VideoLesson


class Command(BaseCommand):
    help = 'Populate the database with chess video lessons from YouTube'

    def handle(self, *args, **kwargs):
        video_data = [
            {
                'title': 'Chess Openings: The Italian Game',
                'description': 'Learn the Italian Game, one of the oldest and most classical chess openings. This video covers the main lines, key ideas, and typical plans for both white and black.',
                'youtube_id': 'fKxG8K1HxO0',
                'thumbnail_url': 'https://img.youtube.com/vi/fKxG8K1HxO0/maxresdefault.jpg',
                'channel_name': 'Chess.com',
                'duration': '12:34',
                'category': 'openings',
                'difficulty': 'beginner',
                'order': 1
            },
            {
                'title': 'Tactics: The Fork',
                'description': 'Master the fork tactic, one of the most powerful tactical motifs in chess. Learn how to identify fork opportunities and execute them effectively.',
                'youtube_id': '5XSB1dbCz-g',
                'thumbnail_url': 'https://img.youtube.com/vi/5XSB1dbCz-g/maxresdefault.jpg',
                'channel_name': 'Hanging Pawns',
                'duration': '8:45',
                'category': 'tactics',
                'difficulty': 'beginner',
                'order': 2
            },
            {
                'title': 'Endgame Fundamentals: King and Pawn vs King',
                'description': 'Essential endgame knowledge for every chess player. Learn the key positions and techniques to win or draw king and pawn endgames.',
                'youtube_id': '5Go2eQ3x4xQ',
                'thumbnail_url': 'https://img.youtube.com/vi/5Go2eQ3x4xQ/maxresdefault.jpg',
                'channel_name': 'ChessNetwork',
                'duration': '15:20',
                'category': 'endgames',
                'difficulty': 'beginner',
                'order': 3
            },
            {
                'title': 'Middlegame Strategy: Piece Activity',
                'description': 'Understanding piece activity is crucial for middlegame success. Learn how to improve your pieces and coordinate them effectively.',
                'youtube_id': '7U4q6mFQkT0',
                'thumbnail_url': 'https://img.youtube.com/vi/7U4q6mFQkT0/maxresdefault.jpg',
                'channel_name': 'St. Louis Chess Club',
                'duration': '18:15',
                'category': 'middlegame',
                'difficulty': 'intermediate',
                'order': 4
            },
            {
                'title': 'Advanced Tactics: The Pin',
                'description': 'Deep dive into the pin tactic. Learn about absolute pins, relative pins, and how to use pins to win material or deliver checkmate.',
                'youtube_id': '3KxP8mQk8xM',
                'thumbnail_url': 'https://img.youtube.com/vi/3KxP8mQk8xM/maxresdefault.jpg',
                'channel_name': 'GothamChess',
                'duration': '10:50',
                'category': 'tactics',
                'difficulty': 'intermediate',
                'order': 5
            },
            {
                'title': 'Sicilian Defense: Open Sicilian',
                'description': 'Complete guide to the Open Sicilian. Learn the main lines, typical pawn structures, and strategic ideas for both sides.',
                'youtube_id': '9LmT9jC5Y0k',
                'thumbnail_url': 'https://img.youtube.com/vi/9LmT9jC5Y0k/maxresdefault.jpg',
                'channel_name': 'Agadmator',
                'duration': '22:30',
                'category': 'openings',
                'difficulty': 'advanced',
                'order': 6
            },
            {
                'title': 'Rook Endgames: Lucena and Philidor',
                'description': 'Master the two most important rook endgame positions. Learn the Lucena position (how to win) and Philidor position (how to draw).',
                'youtube_id': '4KdP7Q0x8xQ',
                'thumbnail_url': 'https://img.youtube.com/vi/4KdP7Q0x8xQ/maxresdefault.jpg',
                'channel_name': 'Chess.com',
                'duration': '14:45',
                'category': 'endgames',
                'difficulty': 'intermediate',
                'order': 7
            },
            {
                'title': 'Strategic Planning: Prophylaxis',
                'description': 'Learn the concept of prophylaxis - preventing your opponent\'s plans before they can execute them. Essential for advanced strategic thinking.',
                'youtube_id': '6KxQ8mQk9xM',
                'thumbnail_url': 'https://img.youtube.com/vi/6KxQ8mQk9xM/maxresdefault.jpg',
                'channel_name': 'St. Louis Chess Club',
                'duration': '20:10',
                'category': 'strategy',
                'difficulty': 'advanced',
                'order': 8
            },
            {
                'title': 'Beginner Tactics: Discovered Attack',
                'description': 'Introduction to discovered attacks. Learn how to uncover a powerful piece to create threats and win material.',
                'youtube_id': '1KxP7mQk7xM',
                'thumbnail_url': 'https://img.youtube.com/vi/1KxP7mQk7xM/maxresdefault.jpg',
                'channel_name': 'Hanging Pawns',
                'duration': '7:30',
                'category': 'tactics',
                'difficulty': 'beginner',
                'order': 9
            },
            {
                'title': 'Caro-Kann Defense: Classical Variation',
                'description': 'Complete guide to the Classical Caro-Kann. Learn the key ideas, typical plans, and important tactical motifs.',
                'youtube_id': '2KxQ9mQk8xM',
                'thumbnail_url': 'https://img.youtube.com/vi/2KxQ9mQk8xM/maxresdefault.jpg',
                'channel_name': 'GothamChess',
                'duration': '16:40',
                'category': 'openings',
                'difficulty': 'intermediate',
                'order': 10
            },
            {
                'title': 'Chess Tutorial',
                'description': 'Learn chess fundamentals and improve your game with this comprehensive tutorial.',
                'youtube_id': '7S-1qAy-nnY',
                'thumbnail_url': 'https://img.youtube.com/vi/7S-1qAy-nnY/maxresdefault.jpg',
                'channel_name': 'Chess Creator',
                'duration': '10:00',
                'category': 'basics',
                'difficulty': 'beginner',
                'order': 11
            },
            {
                'title': 'Chess Fundamentals',
                'description': 'Master the essential fundamentals of chess including piece movement, basic tactics, and strategic concepts.',
                'youtube_id': 'TYbXzmAAftQ',
                'thumbnail_url': 'https://img.youtube.com/vi/TYbXzmAAftQ/maxresdefault.jpg',
                'channel_name': 'Chess Academy',
                'duration': '15:30',
                'category': 'basics',
                'difficulty': 'beginner',
                'order': 12
            },
        ]
        
        created_count = 0
        updated_count = 0
        
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
        
        self.stdout.write(self.style.SUCCESS(f'\nSummary: {created_count} videos created, {updated_count} videos updated'))
