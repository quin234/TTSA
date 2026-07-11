from django.core.management.base import BaseCommand
from ttsa_app.models import Lesson


class Command(BaseCommand):
    help = 'Populate the database with chess lessons'

    def handle(self, *args, **kwargs):
        lessons_data = [
            {
                'title': 'Chess Pieces and How They Move',
                'description': 'Learn about each chess piece and how it moves across the board.',
                'content': '''Welcome to your first chess lesson! Let's learn about each piece and how it moves.

**The Chess Board:**
The chess board has 64 squares arranged in an 8×8 grid. Each player starts with 16 pieces.

**The Pieces:**

**♔ King (♚)**
- Moves one square in any direction (horizontally, vertically, or diagonally)
- The most important piece - if your king is checkmated, you lose
- Can castle with a rook (special move)

**♕ Queen (♛)**
- The most powerful piece
- Moves any number of squares in any direction (like a rook + bishop combined)
- Can move horizontally, vertically, or diagonally

**♖ Rook (♜)**
- Moves any number of squares horizontally or vertically
- Cannot move diagonally
- Powerful in open files and on the 7th rank

**♗ Bishop (♝)**
- Moves any number of squares diagonally
- Each player has one light-squared bishop and one dark-squared bishop
- Bishops work well together (the "bishop pair")

**♘ Knight (♞)**
- Moves in an L-shape: 2 squares in one direction, then 1 square perpendicular
- The only piece that can jump over other pieces
- Unique movement makes it excellent for forking

**♙ Pawn (♟)**
- Moves forward one square (or two squares from its starting position)
- Captures diagonally (one square forward-diagonal)
- Can promote to any piece when reaching the opposite end
- Can capture en passant (special pawn capture)

**Special Moves:**
- **Castling**: King moves two squares toward a rook, rook jumps over the king
- **En Passant**: Special pawn capture when opponent moves pawn two squares
- **Promotion**: Pawn reaching the 8th rank can become queen, rook, bishop, or knight

**Getting Started:**
Watch the interactive demonstration below to see each piece in action!''',
                'difficulty': 'beginner',
                'category': 'basics',
                'order': 1,
                'is_interactive': True,
                'points_reward': 10
            },
            {
                'title': 'Piece Values and Trading',
                'description': 'Understand the relative value of chess pieces and when to trade them.',
                'content': '''Knowing the value of each piece is essential for making good trading decisions.

**Piece Values (approximate):**
- Pawn: 1 point
- Knight: 3 points
- Bishop: 3 points
- Rook: 5 points
- Queen: 9 points
- King: Invaluable (losing it means losing the game)

**Trading Rules:**
1. Trade when you get equal or better material
2. Trade to simplify when you have an advantage
3. Avoid trading when you have better piece activity
4. Consider piece activity and position, not just material

**Example:**
Trading a knight (3 points) for a bishop (3 points) is usually equal, but if your bishop is blocked by your own pawns while their knight is active, you might be losing value.

**Interactive Example:**
Watch the board below to see a typical piece trade scenario!''',
                'difficulty': 'beginner',
                'category': 'basics',
                'order': 2,
                'is_interactive': True,
                'points_reward': 10
            },
            {
                'title': 'The Scholar\'s Mate',
                'description': 'Learn this common four-move checkmate pattern and how to defend against it.',
                'content': '''The Scholar\'s Mate is a four-move checkmate pattern that beginners often fall for.

**The Pattern:**
1. e4 (White opens with e-pawn)
2. ... e5 (Black responds with e-pawn)
3. Bc4 (White develops bishop to c4, attacking f7)
4. ... Nc6 (Black develops knight)
5. Qh5 (White brings queen to h5, attacking f7)
6. ... Nf6 (Black develops knight, attacking queen)
7. Qxf7# (White delivers checkmate)

**How to Defend:**
- After 3. Bc4, play 3... Nc6 to defend f7
- Or play 3... Qf6 to defend f7 with the queen
- After 5. Qh5, play 5... Nf6 to attack the queen

**Key Lesson:**
Always defend your weakest point (f7 for Black, f2 for White) and don't bring your queen out too early!''',
                'difficulty': 'beginner',
                'category': 'tactics',
                'order': 3,
                'is_interactive': True,
                'points_reward': 15
            },
            {
                'title': 'Fork Tactics',
                'description': 'Master the fork - one piece attacking two or more enemy pieces simultaneously.',
                'content': '''A fork is a tactic where one piece attacks two or more enemy pieces simultaneously.

**Knight Forks:**
Knights are excellent at forking due to their unique L-shaped movement.

Example: Knight on e5 forking king on g6 and queen on c7

**Pawn Forks:**
Pawns can also fork pieces, especially in the center of the board.

Example: Pawn on d4 forking knight on c5 and bishop on e5

**Queen Forks:**
The queen\'s power allows it to fork multiple pieces across the board.

**How to Create Forks:**
1. Look for pieces on the same color squares (for bishops/queens)
2. Identify pieces that can be reached by a knight\'s L-shape
3. Use discovered attacks to set up forks
4. Create weaknesses in opponent\'s position

**Defending Against Forks:**
- Keep your pieces protected
- Avoid placing pieces on vulnerable squares
- Look for tactical opportunities before moving''',
                'difficulty': 'easy',
                'category': 'tactics',
                'order': 4,
                'is_interactive': True,
                'points_reward': 15
            },
            {
                'title': 'Pin and Skewer',
                'description': 'Learn about pins and skewers - powerful tactical motifs.',
                'content': '''Pins and skewers are tactical motifs that restrict piece movement.

**Pin:**
A pin occurs when a piece cannot move because it would expose a more valuable piece behind it.

**Types of Pins:**
1. **Absolute Pin**: Pinned piece cannot move because it would expose the king to check
2. **Relative Pin**: Pinned piece can move but would expose a more valuable piece

Example: Bishop on g5 pining knight on f6 to king on e8

**Skewer:**
A skewer is similar to a pin but attacks a more valuable piece, forcing it to move and exposing a less valuable piece behind it.

Example: Rook on e1 skewering king on e8 and queen on e2

**Using Pins and Skewers:**
1. Identify pieces lined up on ranks, files, or diagonals
2. Use long-range pieces (queen, rook, bishop)
3. Create pins to restrict opponent\'s options
4. Use skewers to win material

**Defending:**
- Break the line with piece interposition
- Move the attacked piece to safety
- Attack the pinning piece
- Counter-attack elsewhere''',
                'difficulty': 'easy',
                'category': 'tactics',
                'order': 5,
                'is_interactive': True,
                'points_reward': 15
            },
            {
                'title': 'Italian Game Opening',
                'description': 'Learn the Italian Game, one of the oldest and most popular chess openings.',
                'content': '''The Italian Game is a classical chess opening that begins with the moves:

1. e4 e5
2. Nf3 Nc6
3. Bc4

**Key Ideas:**
- White develops the bishop to c4, attacking the f7 square
- Controls the center with e4
- Prepares for castling and king safety

**Main Variations:**

**Giuoco Piano (Quiet Game):**
3... Bc4
4. c3 Nf6
5. d4 exd4
6. cxd4

**Two Knights Defense:**
3... Nf6
4. Ng5 (attacking f7)
4... d5 (counter-attacking)

**Evans Gambit:**
3... Bc4
4. b4 (sacrificing a pawn for rapid development)

**Strategic Goals:**
- Control the center
- Develop pieces quickly
- Create attacking chances
- Maintain king safety

**Common Mistakes to Avoid:**
- Don't bring your queen out too early
- Don't ignore center control
- Don't neglect development

**Interactive Example:**
Watch the board below to see the main line of the Italian Game!''',
                'difficulty': 'intermediate',
                'category': 'openings',
                'order': 6,
                'is_interactive': True,
                'points_reward': 20
            },
            {
                'title': 'Sicilian Defense',
                'description': 'Master the Sicilian Defense - Black\'s most aggressive response to 1.e4.',
                'content': '''The Sicilian Defense is Black\'s most popular and aggressive response to 1.e4.

**Starting Position:**
1. e4 c5

**Key Characteristics:**
- Asymmetric position leads to complex games
- Black controls the d4 square
- Often leads to sharp, tactical battles

**Main Variations:**

**Open Sicilian:**
2. Nf3 d6
3. d4 cxd4
4. Nxd4

**Closed Sicilian:**
2. Nc6
3. g3 (preparing Bg2)

**Najdorf Variation:**
2... d6
3. d4 cxd4
4. Nxd4 Nf6
5. Nc3 a6

**Dragon Variation:**
2... d6
3. d4 cxd4
4. Nxd4 Nf6
5. Nc3 g6

**Strategic Themes:**
- Counter-attacking in the center
- Piece activity over material
- Queenside attacks for Black
- Central and kingside attacks for White

**When to Play:**
- When you want complex, tactical positions
- When you're comfortable with sharp play
- When you want to play for a win

**Interactive Example:**
Watch the board below to see the Open Sicilian main line!''',
                'difficulty': 'intermediate',
                'category': 'openings',
                'order': 7,
                'is_interactive': True,
                'points_reward': 20
            },
            {
                'title': 'King and Pawn Endgame',
                'description': 'Learn fundamental king and pawn endgame techniques.',
                'content': '''King and pawn endgames are the foundation of endgame knowledge.

**Key Concepts:**

**Opposition:**
When kings face each other with one square between them, the side not to move has the opposition.

**Key Squares:**
Squares that allow your king to promote a pawn or stop opponent's pawn.

**Passed Pawn:**
A pawn with no opposing pawns to stop it from reaching promotion.

**Rule of the Square:**
If your king can enter the square of an opponent's passed pawn, you can catch it.

**Basic Techniques:**

**Promoting a Pawn:**
1. Advance your king to support the pawn
2. Use opposition to gain space
3. Create a passed pawn
4. Advance the pawn to promotion

**Defending Against a Passed Pawn:**
1. Use your king to block the pawn
2. Use opposition to hold the position
3. Create counterplay with your own pawns

**Common Patterns:**
- Lucena Position (winning technique)
- Philidor Position (drawing technique)
- Pawn Breakthrough
- Outside passed pawn

**Practice Tips:**
- Calculate king moves carefully
- Use opposition strategically
- Look for pawn breakthroughs
- Know when to trade pawns

**Interactive Example:**
Watch the board below to see a basic pawn promotion technique!''',
                'difficulty': 'intermediate',
                'category': 'endgames',
                'order': 8,
                'is_interactive': True,
                'points_reward': 20
            },
            {
                'title': 'Rook Endgames',
                'description': 'Master essential rook endgame principles and patterns.',
                'content': '''Rook endgames are the most common type of endgame.

**Key Principles:**

**Rook Behind Passed Pawn:**
Always place your rook behind a passed pawn - either yours or your opponent's.

**Activity Over Material:**
Active rooks are worth more than material. A rook on the 7th rank is often worth a pawn.

**Cutting Off the King:**
Use your rook to restrict the opponent's king movement.

**Lucena Position:**
A winning technique where you have a rook and pawn against a rook.

**Philidor Position:**
A drawing technique where you defend against a rook and pawn with a rook.

**Important Patterns:**

**Rook + Pawn vs Rook:**
- With the rook in front of the pawn, it's usually a draw
- With the rook behind the pawn, the side with the pawn usually wins

**Rook Activity:**
- Place rooks on open files
- Put rooks on the 7th rank when possible
- Keep rooks active and mobile

**Practical Tips:**
1. Activate your rook before considering pawn moves
2. Look for rook sacrifices to promote pawns
3. Use the rook to cut off the enemy king
4. Create passed pawns to distract the opponent

**Interactive Example:**
Watch the board below to see rook activity principles!''',
                'difficulty': 'advanced',
                'category': 'endgames',
                'order': 9,
                'is_interactive': True,
                'points_reward': 25
            },
            {
                'title': 'Positional Play - Outposts',
                'description': 'Learn about piece outposts and how to create and use them.',
                'content': '''An outpost is a square where a piece, especially a knight, can settle without being attacked by enemy pawns.

**Creating Outposts:**

**Knight Outposts:**
Knights are excellent on outposts due to their unique movement.

Example: A knight on d5 supported by a pawn on c4 or e4

**Bishop Outposts:**
Bishops can also use outposts, particularly on diagonals.

**Key Outpost Squares:**
- Central squares (d4, d5, e4, e5)
- Squares in enemy territory
- Squares that cannot be attacked by pawns

**How to Create Outposts:**
1. Fix enemy pawns on the color of your bishop
2. Advance pawns to support your pieces
3. Trade pieces that could attack the outpost
4. Control key squares with your pawns

**Using Outposts:**
- Place knights on supported central squares
- Use outposts to launch attacks
- Control key lines and diagonals
- Restrict opponent's piece mobility

**Defending Against Outposts:**
- Avoid creating pawn weaknesses
- Keep pieces flexible to challenge outposts
- Trade off well-placed enemy pieces
- Use pawn breaks to disrupt outpost squares

**Interactive Example:**
Watch the board below to see how to create a knight outpost!''',
                'difficulty': 'advanced',
                'category': 'strategy',
                'order': 10,
                'is_interactive': True,
                'points_reward': 25
            }
        ]

        created_count = 0
        updated_count = 0

        for lesson_data in lessons_data:
            lesson, created = Lesson.objects.update_or_create(
                title=lesson_data['title'],
                defaults=lesson_data
            )
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created lesson: {lesson.title}')
                )
            else:
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(f'Updated lesson: {lesson.title}')
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'\nSummary: {created_count} lessons created, {updated_count} lessons updated'
            )
        )
