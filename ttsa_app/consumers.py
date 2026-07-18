import json
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from asgiref.sync import sync_to_async
from django.utils import timezone
from django.db import transaction
from datetime import timedelta
from .models import MultiplayerGame, GameMove
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

# Import chess only for multiplayer game functionality
try:
    import chess
    CHESS_AVAILABLE = True
except ImportError:
    CHESS_AVAILABLE = False


class MultiplayerGameConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.game_code = self.scope['url_route']['kwargs']['game_code']
        self.game_group_name = f'game_{self.game_code}'
        
        # Get user in async-safe way
        self.user = await sync_to_async(lambda: self.scope['user'])()

        # Verify user is part of the game
        game = await self.get_game()
        if not game:
            await self.close()
            return

        if game.white_player != self.user and game.black_player != self.user:
            await self.close()
            return

        # Join game group
        await self.channel_layer.group_add(self.game_group_name, self.channel_name)
        await self.accept()

        # Send current clock state to connecting player
        await self.send_clock_state(game)

        # Start periodic clock sync if game is playing (run in background)
        if game.status == 'playing':
            asyncio.create_task(self.start_clock_sync())

        # Notify others that user joined
        await self.channel_layer.group_send(
            self.game_group_name,
            {
                'type': 'player_joined',
                'username': self.user.username,
                'user_id': self.user.id
            }
        )

    async def disconnect(self, close_code):
        # Leave game group
        await self.channel_layer.group_discard(self.game_group_name, self.channel_name)

        # Notify others that user left
        await self.channel_layer.group_send(
            self.game_group_name,
            {
                'type': 'player_left',
                'username': self.user.username,
                'user_id': self.user.id
            }
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        message_type = data.get('type')
        print(f"Received message type: {message_type}, data: {data}")

        if message_type == 'move':
            await self.handle_move(data)
        elif message_type == 'game_end':
            await self.handle_game_end(data)
        elif message_type == 'draw_offer':
            await self.handle_draw_offer()
        elif message_type == 'draw_response':
            await self.handle_draw_response(data)
        elif message_type == 'resign':
            await self.handle_resign()
        elif message_type == 'rematch':
            await self.handle_rematch()
        elif message_type == 'chat':
            await self.handle_chat(data)
        elif message_type == 'reconnect':
            await self.handle_reconnect(data)
        elif message_type == 'clock_sync':
            await self.handle_clock_sync(data)
        elif message_type == 'timeout':
            await self.handle_timeout(data)

    async def handle_move(self, data):
        print(f"handle_move called by user: {self.user.username}")
        game = await self.get_game()
        if not game or game.status != 'playing':
            print(f"Game not found or not playing: {game}")
            return

        if not CHESS_AVAILABLE:
            print("Chess module not available")
            return

        # Verify it's the user's turn
        chess_game = chess.Board(game.current_fen)
        current_turn = 'white' if chess_game.turn == chess.WHITE else 'black'
        
        user_color = 'white' if game.white_player == self.user else 'black'
        print(f"Current turn: {current_turn}, User color: {user_color}")
        if current_turn != user_color:
            print("Not user's turn, returning")
            return

        # Validate move using chess-python
        move_data = data.get('move')
        print(f"Move data received: {move_data}")
        move_from = move_data.get('from')
        move_to = move_data.get('to')
        promotion = move_data.get('promotion')
        
        try:
            # Create the move object - only add promotion if it's actually a promotion move
            uci_move = f"{move_from}{move_to}"
            if promotion:
                uci_move += promotion
            move = chess.Move.from_uci(uci_move)
            
            # Validate the move is legal
            if move not in chess_game.legal_moves:
                print(f"Move not legal: {move}")
                return
            
            # Apply the move
            chess_game.push(move)
            print(f"Move applied successfully: {move}")
            
        except ValueError as e:
            print(f"ValueError creating move: {e}")
            return

        # Initialize clock on first move if not already started
        if game.last_move_timestamp is None:
            await self.initialize_clock(game)

        # Update clock before saving - calculate elapsed time for current player
        await self.update_clock_on_move(game, current_turn)

        # Update game state
        game.current_fen = chess_game.fen()
        await self.update_game(game)
        print(f"Game FEN updated: {game.current_fen}")

        # Save move to database
        try:
            await self.save_move(game, move_data, chess_game.fen())
            print(f"Move saved successfully: {move_data}")
        except Exception as e:
            print(f"Error saving move: {e}")

        # Broadcast move and clock state to both players
        await self.channel_layer.group_send(
            self.game_group_name,
            {
                'type': 'broadcast_move',
                'move': move_data,
                'fen': chess_game.fen(),
                'player': self.user.username,
                'white_time': game.white_time,
                'black_time': game.black_time,
                'active_clock': game.active_clock
            }
        )

        # Check for game end
        if chess_game.is_game_over():
            await self.handle_game_over(chess_game)
        else:
            # Check for timeout after move
            await self.check_timeout(game)

    async def handle_game_end(self, data):
        game = await self.get_game()
        if not game:
            return

        result = data.get('result')
        game.status = 'completed'
        game.result = result
        game.completed_at = timezone.now()
        await self.update_game(game)
        
        # Ensure PGN is updated on game end
        await self.update_pgn(game)

        await self.channel_layer.group_send(
            self.game_group_name,
            {
                'type': 'game_completed',
                'result': result
            }
        )

    async def handle_draw_offer(self):
        game = await self.get_game()
        if not game:
            return

        # Send draw offer to opponent
        opponent = game.black_player if game.white_player == self.user else game.white_player
        await self.channel_layer.group_send(
            self.game_group_name,
            {
                'type': 'draw_offered',
                'from_user': self.user.username,
                'to_user_id': opponent.id
            }
        )

    async def handle_draw_response(self, data):
        game = await self.get_game()
        if not game:
            return

        accepted = data.get('accepted', False)
        if accepted:
            game.status = 'completed'
            game.result = 'draw'
            game.completed_at = timezone.now()
            await self.update_game(game)
            
            # Ensure PGN is updated on draw
            await self.update_pgn(game)

        await self.channel_layer.group_send(
            self.game_group_name,
            {
                'type': 'draw_response',
                'accepted': accepted
            }
        )

    async def handle_resign(self):
        game = await self.get_game()
        if not game:
            return

        # Determine winner
        winner = 'black' if game.white_player == self.user else 'white'
        game.status = 'completed'
        game.result = 'resignation'
        game.completed_at = timezone.now()
        await self.update_game(game)
        
        # Ensure PGN is updated on resignation
        await self.update_pgn(game)

        await self.channel_layer.group_send(
            self.game_group_name,
            {
                'type': 'player_resigned',
                'winner': winner,
                'resigned_player': self.user.username
            }
        )

    async def handle_rematch(self):
        game = await self.get_game()
        if not game:
            return

        # Only allow rematch if game is completed
        if game.status != 'completed':
            return

        # Reset game state for rematch
        game.status = 'playing'
        game.result = None
        game.completed_at = None
        game.current_fen = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'
        game.pgn = ''
        
        # Swap colors
        old_white = game.white_player
        game.white_player = game.black_player
        game.black_player = old_white
        
        # Reset clocks based on game type
        time_limits = {
            'standard': 600,
            'blitz': 300,
            'rapid': 600,
            'classical': 1800
        }
        game.white_time = time_limits.get(game.game_type, 600)
        game.black_time = time_limits.get(game.game_type, 600)
        
        await self.update_game(game)

        # Clear old moves
        await database_sync_to_async(GameMove.objects.filter(game=game).delete)()

        await self.channel_layer.group_send(
            self.game_group_name,
            {
                'type': 'rematch_started',
                'white_player': game.white_player.username,
                'black_player': game.black_player.username
            }
        )

    async def handle_chat(self, data):
        message = data.get('message', '')
        if not message:
            return

        await self.channel_layer.group_send(
            self.game_group_name,
            {
                'type': 'chat_message',
                'username': self.user.username,
                'message': message
            }
        )

    async def handle_reconnect(self, data):
        """Handle player reconnection by sending current game state"""
        game = await self.get_game()
        if not game:
            return
        
        # Calculate current clock times based on elapsed time
        current_times = await self.calculate_current_times(game)
        
        # Send current game state to the reconnecting player
        await self.send(text_data=json.dumps({
            'type': 'game_state',
            'fen': game.current_fen,
            'status': game.status,
            'result': game.result,
            'white_time': current_times['white_time'],
            'black_time': current_times['black_time'],
            'active_clock': current_times['active_clock']
        }))

    async def handle_game_over(self, chess_game):
        game = await self.get_game()
        if not game:
            return

        if not CHESS_AVAILABLE:
            return

        result = None
        if chess_game.is_checkmate():
            result = 'black' if chess_game.turn == chess.WHITE else 'white'
        elif chess_game.is_stalemate():
            result = 'draw'
        elif chess_game.is_insufficient_material():
            result = 'draw'
        elif chess_game.is_repetition():
            result = 'draw'

        if result:
            game.status = 'completed'
            game.result = result
            game.completed_at = timezone.now()
            await self.update_game(game)
            
            # Ensure PGN is updated on game completion
            await self.update_pgn(game)

            await self.channel_layer.group_send(
                self.game_group_name,
                {
                    'type': 'game_completed',
                    'result': result
                }
            )

    # Channel message handlers
    async def broadcast_move(self, event):
        await self.send(text_data=json.dumps({
            'type': 'move',
            'move': event['move'],
            'fen': event['fen'],
            'player': event['player'],
            'white_time': event.get('white_time'),
            'black_time': event.get('black_time'),
            'active_clock': event.get('active_clock')
        }))

    async def player_joined(self, event):
        await self.send(text_data=json.dumps({
            'type': 'opponent_joined',
            'username': event['username'],
            'user_id': event['user_id']
        }))

    async def player_left(self, event):
        await self.send(text_data=json.dumps({
            'type': 'opponent_left',
            'username': event['username'],
            'user_id': event['user_id']
        }))

    async def draw_offered(self, event):
        if event['to_user_id'] == self.user.id:
            await self.send(text_data=json.dumps({
                'type': 'draw_offer',
                'from_user': event['from_user']
            }))

    async def draw_response(self, event):
        await self.send(text_data=json.dumps({
            'type': 'draw_response',
            'accepted': event['accepted']
        }))

    async def player_resigned(self, event):
        await self.send(text_data=json.dumps({
            'type': 'game_end',
            'result': 'resignation',
            'winner': event['winner'],
            'resigned_player': event['resigned_player']
        }))

    async def rematch_started(self, event):
        await self.send(text_data=json.dumps({
            'type': 'rematch_started',
            'white_player': event['white_player'],
            'black_player': event['black_player']
        }))

    async def game_completed(self, event):
        await self.send(text_data=json.dumps({
            'type': 'game_end',
            'result': event['result']
        }))

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'chat',
            'username': event['username'],
            'message': event['message']
        }))

    async def handle_clock_sync(self, data):
        # Broadcast clock sync to other player
        await self.channel_layer.group_send(
            self.game_group_name,
            {
                'type': 'clock_sync_broadcast',
                'white_time': data.get('white_time'),
                'black_time': data.get('black_time'),
                'active_clock': data.get('active_clock'),
                'sender_id': self.user.id
            }
        )

    async def clock_sync_broadcast(self, event):
        # Only send to the other player, not the sender
        if event['sender_id'] != self.user.id:
            await self.send(text_data=json.dumps({
                'type': 'clock_sync',
                'white_time': event['white_time'],
                'black_time': event['black_time'],
                'active_clock': event['active_clock']
            }))

    async def clock_state_broadcast(self, event):
        # Send clock state to all connected clients
        await self.send(text_data=json.dumps({
            'type': 'clock_state',
            'white_time': event['white_time'],
            'black_time': event['black_time'],
            'active_clock': event['active_clock']
        }))

    async def handle_timeout(self, data):
        game = await self.get_game()
        if not game:
            return

        winner = data.get('winner')
        game.status = 'completed'
        game.result = winner
        game.completed_at = timezone.now()
        await self.update_game(game)
        
        # Ensure PGN is updated on timeout
        await self.update_pgn(game)

        await self.channel_layer.group_send(
            self.game_group_name,
            {
                'type': 'game_completed',
                'result': winner
            }
        )

    # Database helper methods
    @database_sync_to_async
    def get_game(self):
        try:
            return MultiplayerGame.objects.select_related('white_player', 'black_player').get(game_code=self.game_code)
        except MultiplayerGame.DoesNotExist:
            return None

    @database_sync_to_async
    def update_game(self, game):
        game.save()

    @database_sync_to_async
    def update_pgn(self, game):
        """Build and update PGN from all moves in the game"""
        moves = game.moves.all().order_by('move_number')
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

    @database_sync_to_async
    def save_move(self, game, move_data, fen_after):
        move_number = game.moves.count() + 1
        GameMove.objects.create(
            game=game,
            player=self.user,
            move_from=move_data.get('from', ''),
            move_to=move_data.get('to', ''),
            piece=move_data.get('piece', ''),
            captured_piece=move_data.get('captured'),
            promotion=move_data.get('promotion'),
            castling=move_data.get('san'),
            en_passant=move_data.get('flags', '') == 'e',
            is_check=move_data.get('san', '').endswith('+'),
            is_checkmate=move_data.get('san', '').endswith('#'),
            fen_after=fen_after,
            move_number=move_number
        )
        
        # Update PGN after saving the move
        self.update_pgn(game)

    def save_move_sync(self, game, move_data, fen_after):
        """Synchronous version of save_move for use in transactions"""
        move_number = game.moves.count() + 1
        GameMove.objects.create(
            game=game,
            player=self.user,
            move_from=move_data.get('from', ''),
            move_to=move_data.get('to', ''),
            piece=move_data.get('piece', ''),
            captured_piece=move_data.get('captured'),
            promotion=move_data.get('promotion'),
            castling=move_data.get('san'),
            en_passant=move_data.get('flags', '') == 'e',
            is_check=move_data.get('san', '').endswith('+'),
            is_checkmate=move_data.get('san', '').endswith('#'),
            fen_after=fen_after,
            move_number=move_number
        )

    # Clock management methods
    @database_sync_to_async
    def initialize_clock(self, game):
        """Initialize clock on first move"""
        game.white_time = game.initial_time
        game.black_time = game.initial_time
        
        game.active_clock = 'white'
        game.last_move_timestamp = timezone.now()
        game.save()

    @database_sync_to_async
    def update_clock_on_move(self, game, current_turn):
        """Update clock times when a move is made"""
        now = timezone.now()
        
        if game.last_move_timestamp:
            # Calculate elapsed time since last move
            elapsed = (now - game.last_move_timestamp).total_seconds()
            
            # Deduct elapsed time from the active player's clock
            if game.active_clock == 'white':
                game.white_time = max(0, game.white_time - int(elapsed))
            else:
                game.black_time = max(0, game.black_time - int(elapsed))
        
        if current_turn == 'white':
            game.white_time += game.increment_seconds
        else:
            game.black_time += game.increment_seconds
        game.active_clock = 'black' if current_turn == 'white' else 'white'
        game.last_move_timestamp = now
        game.save()

    @database_sync_to_async
    def calculate_current_times(self, game):
        """Calculate current clock times based on elapsed time since last move"""
        if game.status != 'playing' or not game.last_move_timestamp:
            return {
                'white_time': game.white_time,
                'black_time': game.black_time,
                'active_clock': game.active_clock
            }
        
        now = timezone.now()
        elapsed = (now - game.last_move_timestamp).total_seconds()
        
        # Calculate current times
        white_time = game.white_time
        black_time = game.black_time
        
        if game.active_clock == 'white':
            white_time = max(0, game.white_time - int(elapsed))
        else:
            black_time = max(0, game.black_time - int(elapsed))
        
        return {
            'white_time': white_time,
            'black_time': black_time,
            'active_clock': game.active_clock
        }

    async def send_clock_state(self, game):
        """Send current clock state to client"""
        current_times = await self.calculate_current_times(game)
        await self.send(text_data=json.dumps({
            'type': 'clock_state',
            'white_time': current_times['white_time'],
            'black_time': current_times['black_time'],
            'active_clock': current_times['active_clock']
        }))

    async def check_timeout(self, game):
        """Check if either player has run out of time"""
        current_times = await self.calculate_current_times(game)
        
        if current_times['white_time'] <= 0:
            await self.handle_timeout_loss('black')
        elif current_times['black_time'] <= 0:
            await self.handle_timeout_loss('white')

    async def handle_timeout_loss(self, winner):
        """Handle game loss due to timeout"""
        game = await self.get_game()
        if not game:
            return
        
        game.status = 'completed'
        game.result = 'timeout'
        game.completed_at = timezone.now()
        
        # Update clock times to reflect timeout
        if winner == 'white':
            game.white_time = max(0, game.white_time)
            game.black_time = 0
        else:
            game.white_time = 0
            game.black_time = max(0, game.black_time)
        
        await self.update_game(game)
        
        await self.channel_layer.group_send(
            self.game_group_name,
            {
                'type': 'game_completed',
                'result': winner,
                'reason': 'timeout'
            }
        )

    async def start_clock_sync(self):
        """Start periodic clock synchronization"""
        while True:
            await asyncio.sleep(1)  # Sync every second
            game = await self.get_game()
            if not game or game.status != 'playing':
                break
            
            # Broadcast clock state to all connected clients
            current_times = await self.calculate_current_times(game)
            await self.channel_layer.group_send(
                self.game_group_name,
                {
                    'type': 'clock_state_broadcast',
                    'white_time': current_times['white_time'],
                    'black_time': current_times['black_time'],
                    'active_clock': current_times['active_clock']
                }
            )


class TournamentStandingsConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.tournament_id = self.scope['url_route']['kwargs']['tournament_id']
        self.tournament_group_name = f'tournament_standings_{self.tournament_id}'
        
        # Get user in async-safe way
        self.user = await sync_to_async(lambda: self.scope['user'])()

        # Check if user is authenticated
        if not self.user.is_authenticated:
            await self.close()
            return

        # Join tournament group
        await self.channel_layer.group_add(self.tournament_group_name, self.channel_name)
        await self.accept()

        # Send current standings on connect
        await self.send_current_standings()

    async def disconnect(self, close_code):
        # Leave tournament group
        await self.channel_layer.group_discard(self.tournament_group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        message_type = data.get('type')
        
        if message_type == 'request_standings':
            await self.send_current_standings()
        elif message_type == 'ping':
            await self.send(text_data=json.dumps({'type': 'pong'}))

    async def send_current_standings(self):
        """Send current tournament standings to the client"""
        try:
            standings = await self.get_tournament_standings()
            await self.send(text_data=json.dumps({
                'type': 'standings_update',
                'standings': standings,
                'timestamp': timezone.now().isoformat()
            }))
        except Exception as e:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': f'Failed to load standings: {str(e)}'
            }))

    async def standings_updated(self, event):
        """Handle standings update broadcast"""
        await self.send(text_data=json.dumps({
            'type': 'standings_update',
            'standings': event['standings'],
            'timestamp': event.get('timestamp', timezone.now().isoformat()),
            'update_type': event.get('update_type', 'game_result')
        }))

    @database_sync_to_async
    def get_tournament_standings(self):
        """Get tournament standings from database"""
        from ttsaadmin.models import Tournament, TournamentPlayer
        
        try:
            tournament = Tournament.objects.get(id=self.tournament_id)
            players = tournament.players.filter(status='confirmed').order_by('-points', '-buchholz', '-sonneborn_berger', '-rating')
            
            standings_data = []
            rank = 1
            for player in players:
                standings_data.append({
                    'rank': rank,
                    'id': player.id,
                    'name': player.player_name,
                    'rating': player.rating,
                    'points': float(player.points),
                    'wins': player.wins,
                    'losses': player.losses,
                    'draws': player.draws,
                    'buchholz': float(player.buchholz),
                    'sonneborn_berger': float(player.sonneborn_berger),
                    'status': player.status
                })
                rank += 1
            
            return {
                'tournament_id': self.tournament_id,
                'tournament_name': tournament.name,
                'players': standings_data,
                'total_players': len(standings_data)
            }
            
        except Tournament.DoesNotExist:
            return None


def broadcast_tournament_standings(tournament_id, update_type='game_result'):
    """
    Helper function to broadcast tournament standings updates
    Can be called from views or signals
    """
    channel_layer = get_channel_layer()
    group_name = f'tournament_standings_{tournament_id}'
    
    # Get current standings
    from ttsaadmin.models import Tournament, TournamentPlayer
    
    try:
        tournament = Tournament.objects.get(id=tournament_id)
        players = tournament.players.filter(status='confirmed').order_by('-points', '-buchholz', '-sonneborn_berger', '-rating')
        
        standings_data = []
        rank = 1
        for player in players:
            standings_data.append({
                'rank': rank,
                'id': player.id,
                'name': player.player_name,
                'rating': player.rating,
                'points': float(player.points),
                'wins': player.wins,
                'losses': player.losses,
                'draws': player.draws,
                'buchholz': float(player.buchholz),
                'sonneborn_berger': float(player.sonneborn_berger),
                'status': player.status
            })
            rank += 1
        
        standings = {
            'tournament_id': tournament_id,
            'tournament_name': tournament.name,
            'players': standings_data,
            'total_players': len(standings_data)
        }
        
        # Broadcast to all clients in the tournament group
        async_to_sync(channel_layer.group_send)(
            group_name,
            {
                'type': 'standings_updated',
                'standings': standings,
                'timestamp': timezone.now().isoformat(),
                'update_type': update_type
            }
        )
        
    except Tournament.DoesNotExist:
        pass
