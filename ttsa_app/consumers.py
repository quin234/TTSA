import json
import chess
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from asgiref.sync import sync_to_async
from django.utils import timezone
from .models import MultiplayerGame, GameMove


class MultiplayerGameConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.game_id = self.scope['url_route']['kwargs']['game_id']
        self.game_group_name = f'game_{self.game_id}'
        
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
        elif message_type == 'chat':
            await self.handle_chat(data)
        elif message_type == 'reconnect':
            await self.handle_reconnect(data)
        elif message_type == 'clock_sync':
            await self.handle_clock_sync(data)
        elif message_type == 'timeout':
            await self.handle_timeout(data)

    async def handle_move(self, data):
        game = await self.get_game()
        if not game or game.status != 'playing':
            return

        # Verify it's the user's turn
        chess_game = chess.Board(game.current_fen)
        current_turn = 'white' if chess_game.turn == chess.WHITE else 'black'
        
        user_color = 'white' if game.white_player == self.user else 'black'
        if current_turn != user_color:
            return

        # Validate move using chess-python
        move_data = data.get('move')
        move_from = move_data.get('from')
        move_to = move_data.get('to')
        promotion = move_data.get('promotion', 'q')
        
        try:
            # Create the move object
            move = chess.Move.from_uci(f"{move_from}{move_to}{promotion if promotion else ''}")
            
            # Validate the move is legal
            if move not in chess_game.legal_moves:
                return
            
            # Apply the move
            chess_game.push(move)
            
        except ValueError:
            return

        # Save move to database
        await self.save_move(game, move_data, chess_game.fen())

        # Update game state
        game.current_fen = chess_game.fen()
        await self.update_game(game)

        # Broadcast move to other player
        await self.channel_layer.group_send(
            self.game_group_name,
            {
                'type': 'broadcast_move',
                'move': move_data,
                'fen': chess_game.fen(),
                'player': self.user.username
            }
        )

        # Check for game end
        if chess_game.is_game_over():
            await self.handle_game_over(chess_game)

    async def handle_game_end(self, data):
        game = await self.get_game()
        if not game:
            return

        result = data.get('result')
        game.status = 'completed'
        game.result = result
        game.completed_at = timezone.now()
        await self.update_game(game)

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

        await self.channel_layer.group_send(
            self.game_group_name,
            {
                'type': 'player_resigned',
                'winner': winner,
                'resigned_player': self.user.username
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
        
        # Send current game state to the reconnecting player
        await self.send(text_data=json.dumps({
            'type': 'game_state',
            'fen': game.current_fen,
            'status': game.status,
            'result': game.result
        }))

    async def handle_game_over(self, chess_game):
        game = await self.get_game()
        if not game:
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
            'player': event['player']
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

    async def handle_timeout(self, data):
        game = await self.get_game()
        if not game:
            return

        winner = data.get('winner')
        game.status = 'completed'
        game.result = winner
        game.completed_at = timezone.now()
        await self.update_game(game)

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
            return MultiplayerGame.objects.select_related('white_player', 'black_player').get(id=self.game_id)
        except MultiplayerGame.DoesNotExist:
            return None

    @database_sync_to_async
    def update_game(self, game):
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
