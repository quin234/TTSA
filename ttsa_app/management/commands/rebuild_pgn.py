from django.core.management.base import BaseCommand
from ttsa_app.models import MultiplayerGame, GameMove


class Command(BaseCommand):
    help = 'Rebuild PGN for all multiplayer games from their move history'

    def add_arguments(self, parser):
        parser.add_argument(
            '--game-id',
            type=int,
            help='Rebuild PGN for a specific game ID only',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force rebuild even if PGN already exists',
        )

    def handle(self, *args, **options):
        game_id = options.get('game_id')
        force = options.get('force', False)

        if game_id:
            # Rebuild PGN for specific game
            try:
                game = MultiplayerGame.objects.get(id=game_id)
                self.rebuild_game_pgn(game, force)
                self.stdout.write(self.style.SUCCESS(f'Successfully rebuilt PGN for game {game_id}'))
            except MultiplayerGame.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'Game {game_id} does not exist'))
        else:
            # Rebuild PGN for all games
            games = MultiplayerGame.objects.all()
            count = 0
            for game in games:
                if self.rebuild_game_pgn(game, force):
                    count += 1
            
            self.stdout.write(self.style.SUCCESS(f'Successfully rebuilt PGN for {count} games'))

    def rebuild_game_pgn(self, game, force=False):
        """Rebuild PGN for a single game"""
        # Skip if PGN already exists and force is False
        if game.pgn and not force:
            self.stdout.write(f'Skipping game {game.id} - PGN already exists (use --force to rebuild)')
            return False
        
        moves = game.moves.all().order_by('move_number')
        if not moves.exists():
            self.stdout.write(f'Skipping game {game.id} - no moves found')
            return False
        
        pgn_moves = []
        
        for move in moves:
            # Use SAN (Standard Algebraic Notation) if available, otherwise build from move data
            if move.castling and move.castling in ['O-O', 'O-O-O']:
                pgn_moves.append(move.castling)
            else:
                # Build simple notation from move data
                notation = move.piece.upper() if move.piece else ''
                if move.captured_piece:
                    notation += 'x'
                notation += move.move_to
                if move.promotion:
                    notation += f'={move.promotion.upper()}'
                if move.is_checkmate:
                    notation += '#'
                elif move.is_check:
                    notation += '+'
                pgn_moves.append(notation)
        
        # Format PGN with move numbers
        formatted_pgn = ''
        for i, move in enumerate(pgn_moves):
            move_num = (i // 2) + 1
            if i % 2 == 0:  # White's move
                formatted_pgn += f'{move_num}. {move} '
            else:  # Black's move
                formatted_pgn += f'{move} '
        
        game.pgn = formatted_pgn.strip()
        game.save()
        
        self.stdout.write(f'Rebuilt PGN for game {game.id} ({len(pgn_moves)} moves)')
        return True
