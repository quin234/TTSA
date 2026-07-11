-- Direct SQL script to populate chess lessons into the database
-- This script can be run directly against the SQLite database
-- Usage: sqlite3 db.sqlite3 < populate_lessons.sql

-- Clear existing lessons (optional - comment out if you want to keep existing data)
DELETE FROM ttsa_app_lesson;

-- Insert all chess lessons
INSERT INTO ttsa_app_lesson (id, title, description, content, difficulty, category, "order", is_interactive, points_reward, created_at, updated_at) VALUES
(1, 'Introduction to Chess', 'Learn the basics of chess including piece movements and the objective of the game.', 'Chess is a two-player strategy board game played on a checkered board with 64 squares arranged in an 8×8 grid. The game is played by millions of people worldwide.

**Objective:**
The objective of chess is to checkmate your opponent''s king. This happens when the king is under attack (in check) and has no legal move to escape capture.

**Piece Movements:**
- **King**: Moves one square in any direction
- **Queen**: Moves any number of squares in any direction
- **Rook**: Moves any number of squares horizontally or vertically
- **Bishop**: Moves any number of squares diagonally
- **Knight**: Moves in an L-shape (2 squares in one direction, then 1 square perpendicular)
- **Pawn**: Moves forward one square (or two squares on its first move), captures diagonally

**Special Moves:**
- Castling: King and rook special move
- En passant: Special pawn capture
- Pawn promotion: Pawn reaches the opposite end of the board

**Getting Started:**
Use the interactive board below to practice piece movements. Click Play to see demonstrations of basic moves!', 'beginner', 'basics', 1, 1, 10, datetime('now'), datetime('now')),

(2, 'Piece Values and Trading', 'Understand the relative value of chess pieces and when to trade them.', 'Knowing the value of each piece is essential for making good trading decisions.

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
Watch the board below to see a typical piece trade scenario!', 'beginner', 'basics', 2, 1, 10, datetime('now'), datetime('now')),

(3, 'The Scholar''s Mate', 'Learn this common four-move checkmate pattern and how to defend against it.', 'The Scholar''s Mate is a four-move checkmate pattern that beginners often fall for.

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
Always defend your weakest point (f7 for Black, f2 for White) and don''t bring your queen out too early!', 'beginner', 'tactics', 3, 1, 15, datetime('now'), datetime('now')),

(4, 'Fork Tactics', 'Master the fork - one piece attacking two or more enemy pieces simultaneously.', 'A fork is a tactic where one piece attacks two or more enemy pieces simultaneously.

**Knight Forks:**
Knights are excellent at forking due to their unique L-shaped movement.

Example: Knight on e5 forking king on g6 and queen on c7

**Pawn Forks:**
Pawns can also fork pieces, especially in the center of the board.

Example: Pawn on d4 forking knight on c5 and bishop on e5

**Queen Forks:**
The queen''s power allows it to fork multiple pieces across the board.

**How to Create Forks:**
1. Look for pieces on the same color squares (for bishops/queens)
2. Identify pieces that can be reached by a knight''s L-shape
3. Use discovered attacks to set up forks
4. Create weaknesses in opponent''s position

**Defending Against Forks:**
- Keep your pieces protected
- Avoid placing pieces on vulnerable squares
- Look for tactical opportunities before moving', 'easy', 'tactics', 4, 1, 15, datetime('now'), datetime('now')),

(5, 'Pin and Skewer', 'Learn about pins and skewers - powerful tactical motifs.', 'Pins and skewers are tactical motifs that restrict piece movement.

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
3. Create pins to restrict opponent''s options
4. Use skewers to win material

**Defending:**
- Break the line with piece interposition
- Move the attacked piece to safety
- Attack the pinning piece
- Counter-attack elsewhere', 'easy', 'tactics', 5, 1, 15, datetime('now'), datetime('now')),

(6, 'Italian Game Opening', 'Learn the Italian Game, one of the oldest and most popular chess openings.', 'The Italian Game is a classical chess opening that begins with the moves:

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
- Don''t bring your queen out too early
- Don''t ignore center control
- Don''t neglect development

**Interactive Example:**
Watch the board below to see the main line of the Italian Game!', 'intermediate', 'openings', 6, 1, 20, datetime('now'), datetime('now')),

(7, 'Sicilian Defense', 'Master the Sicilian Defense - Black''s most aggressive response to 1.e4.', 'The Sicilian Defense is Black''s most popular and aggressive response to 1.e4.

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
- When you''re comfortable with sharp play
- When you want to play for a win

**Interactive Example:**
Watch the board below to see the Open Sicilian main line!', 'intermediate', 'openings', 7, 1, 20, datetime('now'), datetime('now')),

(8, 'King and Pawn Endgame', 'Learn fundamental king and pawn endgame techniques.', 'King and pawn endgames are the foundation of endgame knowledge.

**Key Concepts:**

**Opposition:**
When kings face each other with one square between them, the side not to move has the opposition.

**Key Squares:**
Squares that allow your king to promote a pawn or stop opponent''s pawn.

**Passed Pawn:**
A pawn with no opposing pawns to stop it from reaching promotion.

**Rule of the Square:**
If your king can enter the square of an opponent''s passed pawn, you can catch it.

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
Watch the board below to see a basic pawn promotion technique!', 'intermediate', 'endgames', 8, 1, 20, datetime('now'), datetime('now')),

(9, 'Rook Endgames', 'Master essential rook endgame principles and patterns.', 'Rook endgames are the most common type of endgame.

**Key Principles:**

**Rook Behind Passed Pawn:**
Always place your rook behind a passed pawn - either yours or your opponent''s.

**Activity Over Material:**
Active rooks are worth more than material. A rook on the 7th rank is often worth a pawn.

**Cutting Off the King:**
Use your rook to restrict the opponent''s king movement.

**Lucena Position:**
A winning technique where you have a rook and pawn against a rook.

**Philidor Position:**
A drawing technique where you defend against a rook and pawn with a rook.

**Important Patterns:**

**Rook + Pawn vs Rook:**
- With the rook in front of the pawn, it''s usually a draw
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
Watch the board below to see rook activity principles!', 'advanced', 'endgames', 9, 1, 25, datetime('now'), datetime('now')),

(10, 'Positional Play - Outposts', 'Learn about piece outposts and how to create and use them.', 'An outpost is a square where a piece, especially a knight, can settle without being attacked by enemy pawns.

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
- Restrict opponent''s piece mobility

**Defending Against Outposts:**
- Avoid creating pawn weaknesses
- Keep pieces flexible to challenge outposts
- Trade off well-placed enemy pieces
- Use pawn breaks to disrupt outpost squares

**Interactive Example:**
Watch the board below to see how to create a knight outpost!', 'advanced', 'strategy', 10, 1, 25, datetime('now'), datetime('now'));

-- Reset the auto-increment sequence
DELETE FROM sqlite_sequence WHERE name='ttsa_app_lesson';
INSERT INTO sqlite_sequence (name, seq) VALUES ('ttsa_app_lesson', 10);

-- Verify the lessons were inserted
SELECT COUNT(*) as total_lessons FROM ttsa_app_lesson;
SELECT id, title, is_interactive, points_reward FROM ttsa_app_lesson ORDER BY "order";
