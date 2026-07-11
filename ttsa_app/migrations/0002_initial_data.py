# Generated manually for initial data

from django.db import migrations


def create_initial_achievements(apps, schema_editor):
    Achievement = apps.get_model('ttsa_app', 'Achievement')
    
    achievements = [
        # Game achievements
        {
            'name': 'First Victory',
            'description': 'Win your first game against the AI',
            'icon': '🏆',
            'points': 10,
            'category': 'games'
        },
        {
            'name': 'Winning Streak',
            'description': 'Win 3 games in a row',
            'icon': '🔥',
            'points': 25,
            'category': 'games'
        },
        {
            'name': 'Chess Master',
            'description': 'Win 50 games total',
            'icon': '👑',
            'points': 100,
            'category': 'games'
        },
        
        # Lesson achievements
        {
            'name': 'Eager Student',
            'description': 'Complete your first lesson',
            'icon': '📚',
            'points': 10,
            'category': 'lessons'
        },
        {
            'name': 'Dedicated Learner',
            'description': 'Complete 10 lessons',
            'icon': '🎓',
            'points': 50,
            'category': 'lessons'
        },
        {
            'name': 'Chess Scholar',
            'description': 'Complete all beginner lessons',
            'icon': '🧠',
            'points': 75,
            'category': 'lessons'
        },
        
        # Puzzle achievements
        {
            'name': 'Puzzle Solver',
            'description': 'Solve your first daily puzzle',
            'icon': '🧩',
            'points': 10,
            'category': 'puzzles'
        },
        {
            'name': 'Tactical Genius',
            'description': 'Solve 25 puzzles',
            'icon': '⚡',
            'points': 50,
            'category': 'puzzles'
        },
        {
            'name': 'Puzzle Master',
            'description': 'Solve 100 puzzles',
            'icon': '💎',
            'points': 150,
            'category': 'puzzles'
        },
        
        # Learning streak achievements
        {
            'name': 'Consistent Player',
            'description': 'Maintain a 7-day learning streak',
            'icon': '📅',
            'points': 25,
            'category': 'streak'
        },
        {
            'name': 'Dedicated Student',
            'description': 'Maintain a 30-day learning streak',
            'icon': '🌟',
            'points': 100,
            'category': 'streak'
        },
        {
            'name': 'Chess Legend',
            'description': 'Maintain a 100-day learning streak',
            'icon': '🏅',
            'points': 500,
            'category': 'streak'
        },
        
        # Special achievements
        {
            'name': 'Quick Learner',
            'description': 'Reach level 5',
            'icon': '🚀',
            'points': 50,
            'category': 'special'
        },
        {
            'name': 'Chess Expert',
            'description': 'Reach rating 1500',
            'icon': '🎯',
            'points': 75,
            'category': 'special'
        },
        {
            'name': 'Academy Champion',
            'description': 'Reach the top of the leaderboard',
            'icon': '🏆',
            'points': 200,
            'category': 'special'
        }
    ]
    
    for achievement_data in achievements:
        Achievement.objects.create(**achievement_data)


def create_initial_lessons(apps, schema_editor):
    Lesson = apps.get_model('ttsa_app', 'Lesson')
    
    lessons = [
        # Chess Basics
        {
            'title': 'Introduction to Chess',
            'description': 'Learn the basic rules and objectives of chess',
            'content': 'Chess is a strategic board game played between two players...',
            'difficulty': 'beginner',
            'category': 'basics',
            'order': 1,
            'is_interactive': True,
            'points_reward': 10
        },
        {
            'title': 'The Chess Board and Pieces',
            'description': 'Understanding the chessboard and how each piece moves',
            'content': 'The chess board consists of 64 squares arranged in an 8x8 grid...',
            'difficulty': 'beginner',
            'category': 'basics',
            'order': 2,
            'is_interactive': True,
            'points_reward': 10
        },
        {
            'title': 'Special Rules',
            'description': 'Learn about castling, en passant, and pawn promotion',
            'content': 'Chess has special rules that make the game more interesting...',
            'difficulty': 'beginner',
            'category': 'basics',
            'order': 3,
            'is_interactive': True,
            'points_reward': 15
        },
        
        # Openings
        {
            'title': 'Opening Principles',
            'description': 'Fundamental principles for starting your game',
            'content': 'A good opening sets the foundation for the rest of your game...',
            'difficulty': 'beginner',
            'category': 'openings',
            'order': 1,
            'is_interactive': True,
            'points_reward': 15
        },
        {
            'title': 'The Italian Game',
            'description': 'Learn one of the oldest and most popular openings',
            'content': 'The Italian Game begins with 1.e4 e5 2.Nf3 Nc6 3.Bc4...',
            'difficulty': 'easy',
            'category': 'openings',
            'order': 2,
            'is_interactive': True,
            'points_reward': 20
        },
        {
            'title': 'The Sicilian Defense',
            'description': 'Master this aggressive and popular defense',
            'content': 'The Sicilian Defense is Black\'s most popular response to 1.e4...',
            'difficulty': 'intermediate',
            'category': 'openings',
            'order': 3,
            'is_interactive': True,
            'points_reward': 25
        },
        
        # Tactics
        {
            'title': 'Basic Tactics: Forks',
            'description': 'Learn how to attack two pieces at once',
            'content': 'A fork is a tactic where one piece attacks two enemy pieces simultaneously...',
            'difficulty': 'beginner',
            'category': 'tactics',
            'order': 1,
            'is_interactive': True,
            'points_reward': 15
        },
        {
            'title': 'Basic Tactics: Pins',
            'description': 'Understanding pinning tactics and how to use them',
            'content': 'A pin occurs when a piece is unable to move because it would expose a more valuable piece...',
            'difficulty': 'easy',
            'category': 'tactics',
            'order': 2,
            'is_interactive': True,
            'points_reward': 20
        },
        {
            'title': 'Basic Tactics: Skewers',
            'description': 'Learn the skewer tactic and its applications',
            'content': 'A skewer is similar to a pin but attacks a more valuable piece first...',
            'difficulty': 'intermediate',
            'category': 'tactics',
            'order': 3,
            'is_interactive': True,
            'points_reward': 25
        },
        
        # Endgames
        {
            'title': 'Basic Checkmates',
            'description': 'Learn fundamental checkmating patterns',
            'content': 'Understanding basic checkmates is essential for every chess player...',
            'difficulty': 'beginner',
            'category': 'endgames',
            'order': 1,
            'is_interactive': True,
            'points_reward': 15
        },
        {
            'title': 'King and Queen vs King',
            'description': 'Master the most basic endgame',
            'content': 'This endgame teaches you how to deliver checkmate with minimal material...',
            'difficulty': 'beginner',
            'category': 'endgames',
            'order': 2,
            'is_interactive': True,
            'points_reward': 20
        },
        {
            'title': 'King and Rook vs King',
            'description': 'Learn to checkmate with a rook',
            'content': 'The rook and king endgame is fundamental to chess mastery...',
            'difficulty': 'easy',
            'category': 'endgames',
            'order': 3,
            'is_interactive': True,
            'points_reward': 25
        },
        
        # Strategy
        {
            'title': 'Piece Value',
            'description': 'Understanding the relative value of chess pieces',
            'content': 'Each piece has a point value that helps evaluate positions...',
            'difficulty': 'beginner',
            'category': 'strategy',
            'order': 1,
            'is_interactive': True,
            'points_reward': 15
        },
        {
            'title': 'Controlling the Center',
            'description': 'Why the center squares are important',
            'content': 'The center of the board is the most important area in chess...',
            'difficulty': 'easy',
            'category': 'strategy',
            'order': 2,
            'is_interactive': True,
            'points_reward': 20
        },
        {
            'title': 'Pawn Structure',
            'description': 'Understanding pawn formations and their importance',
            'content': 'Pawn structure is the skeleton of your chess position...',
            'difficulty': 'intermediate',
            'category': 'strategy',
            'order': 3,
            'is_interactive': True,
            'points_reward': 25
        }
    ]
    
    for lesson_data in lessons:
        Lesson.objects.create(**lesson_data)


def create_initial_puzzles(apps, schema_editor):
    Puzzle = apps.get_model('ttsa_app', 'Puzzle')
    
    puzzles = [
        # Beginner puzzles
        {
            'fen': 'rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2',
            'solution': 'fxe5',
            'difficulty': 'beginner',
            'category': 'tactics',
            'rating': 800
        },
        {
            'fen': 'rnbqkbnr/ppp2ppp/3p4/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R b KQkq - 1 3',
            'solution': 'd5',
            'difficulty': 'beginner',
            'category': 'tactics',
            'rating': 900
        },
        
        # Easy puzzles
        {
            'fen': 'r1bqkb1r/pppp1ppp/2n2n2/4p2Q/2B1P3/3P4/PPP2PPP/RN2KB1R b KQkq - 2 6',
            'solution': 'Nf6',
            'difficulty': 'easy',
            'category': 'tactics',
            'rating': 1100
        },
        {
            'fen': 'rnbqk2r/pppp1ppp/5n2/2b1p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 3 5',
            'solution': 'Bxf7+',
            'difficulty': 'easy',
            'category': 'checkmate',
            'rating': 1200
        },
        
        # Intermediate puzzles
        {
            'fen': 'r1bq1rk1/ppp2ppp/2np1n2/2b1p3/2B1P3/3P1N2/PPP2PPP/RN1QKB1R w KQ - 0 8',
            'solution': 'Nxe5',
            'difficulty': 'intermediate',
            'category': 'tactics',
            'rating': 1400
        },
        {
            'fen': '3r2k1/p2r1ppp/4pn2/2p5/2P5/1P3NP1/P2RPPKP/3R4 b - - 0 20',
            'solution': 'Rxc3',
            'difficulty': 'intermediate',
            'category': 'tactics',
            'rating': 1500
        }
    ]
    
    for puzzle_data in puzzles:
        Puzzle.objects.create(**puzzle_data)


class Migration(migrations.Migration):
    dependencies = [
        ('ttsa_app', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_initial_achievements),
        migrations.RunPython(create_initial_lessons),
        migrations.RunPython(create_initial_puzzles),
    ]
