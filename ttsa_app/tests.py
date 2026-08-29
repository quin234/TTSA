from datetime import timedelta
from django.test import TestCase, Client
from django.core.cache import cache
from django.utils import timezone
from unittest.mock import patch

from ttsa_app.stockfish_config import get_difficulty_config, DIFFICULTY_CONFIG
from ttsa_app.stockfish_service import DifficultyLevel, stockfish_service
from ttsa_app.models import GuestSession, MultiplayerGame


class GuestMultiplayerTests(TestCase):
    def setUp(self):
        cache.delete('ratelimit:ttsa_app.views.multiplayer_create_api:127.0.0.1')

    def test_guest_can_create_private_multiplayer_game(self):
        response = self.client.get('/multiplayer/create/')

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Playing as a guest')
        self.assertIn('multiplayer_guest_token', self.client.session)

        guest_session = GuestSession.objects.get()
        self.assertFalse(guest_session.user.is_active)
        self.assertFalse(guest_session.user.has_usable_password())

        response = self.client.post(
            '/api/multiplayer/create/',
            data='{"time_control":"5+0","color_preference":"random","guest_name":"Guest Player"}',
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['success'])
        game = MultiplayerGame.objects.get(game_code=response.json()['game_code'])
        self.assertEqual(game.white_player, guest_session.user)
        guest_session.refresh_from_db()
        self.assertEqual(guest_session.display_name, 'Guest Player')

    def test_guest_game_creation_requires_valid_csrf_token(self):
        client = Client(enforce_csrf_checks=True)
        page_response = client.get('/multiplayer/create/')
        csrf_token = page_response.cookies['csrftoken'].value

        rejected_response = client.post(
            '/api/multiplayer/create/',
            data='{"time_control":"5+0","color_preference":"random"}',
            content_type='application/json',
        )
        accepted_response = client.post(
            '/api/multiplayer/create/',
            data='{"time_control":"5+0","color_preference":"random"}',
            content_type='application/json',
            HTTP_X_CSRFTOKEN=csrf_token,
        )

        self.assertEqual(rejected_response.status_code, 403)
        self.assertEqual(accepted_response.status_code, 200)

    def test_lobby_matches_two_anonymous_players(self):
        self.client.get('/multiplayer/create/')
        first_response = self.client.post(
            '/api/multiplayer/create/',
            data='{"time_control":"5+0","color_preference":"random","creation_mode":"lobby"}',
            content_type='application/json',
        )
        game_code = first_response.json()['game_code']
        game = MultiplayerGame.objects.get(game_code=game_code)
        self.assertTrue(game.is_lobby_game)
        self.assertEqual(game.visibility, 'public')
        self.assertEqual(game.status, 'waiting')

        joining_client = Client()
        joining_client.get('/multiplayer/create/')
        second_response = joining_client.post(
            '/api/multiplayer/create/',
            data='{"time_control":"5+0","color_preference":"random","creation_mode":"lobby"}',
            content_type='application/json',
        )

        self.assertTrue(second_response.json()['matched'])
        self.assertEqual(second_response.json()['game_code'], game_code)
        game.refresh_from_db()
        self.assertEqual(game.status, 'playing')
        self.assertIsNotNone(game.black_player)

    def test_lobby_starts_stockfish_after_timeout(self):
        self.client.get('/multiplayer/create/')
        response = self.client.post(
            '/api/multiplayer/create/',
            data='{"time_control":"5+0","color_preference":"random","creation_mode":"lobby"}',
            content_type='application/json',
        )
        game = MultiplayerGame.objects.get(game_code=response.json()['game_code'])
        self.assertGreaterEqual(game.lobby_fallback_at - game.created_at, timedelta(seconds=10))
        self.assertLessEqual(game.lobby_fallback_at - game.created_at, timedelta(seconds=20, microseconds=1))
        game.lobby_fallback_at = timezone.now() - timedelta(seconds=1)
        game.save(update_fields=['lobby_fallback_at'])

        status_response = self.client.get(f'/api/multiplayer/status/{game.game_code}/')

        self.assertEqual(status_response.status_code, 200)
        self.assertTrue(status_response.json()['stockfish_opponent'])
        game.refresh_from_db()
        self.assertTrue(game.has_stockfish_opponent)
        self.assertEqual(game.status, 'playing')
        self.assertEqual(game.black_player.username, 'ttsa-stockfish-bot')

    def test_second_guest_can_join_shared_game_link(self):
        self.client.get('/multiplayer/create/')
        response = self.client.post(
            '/api/multiplayer/create/',
            data='{"time_control":"5+0","color_preference":"random"}',
            content_type='application/json',
        )
        game_code = response.json()['game_code']

        joining_client = Client()
        response = joining_client.get(f'/multiplayer/game/{game_code}/')

        self.assertEqual(response.status_code, 200)
        game = MultiplayerGame.objects.get(game_code=game_code)
        self.assertEqual(game.status, 'playing')
        self.assertIsNotNone(game.black_player)
        self.assertNotEqual(game.white_player_id, game.black_player_id)
        self.assertTrue(GuestSession.objects.filter(user=game.black_player).exists())


class DifficultyConfigTests(TestCase):
    """Verify the three Play vs Computer difficulty levels are tuned as expected."""

    def test_beginner_settings(self):
        config = get_difficulty_config('beginner')
        self.assertEqual(config['skill_level'], 0)
        self.assertEqual(config['depth'], 1)
        self.assertEqual(config['movetime'], 80)
        self.assertEqual(config['nodes'], 100)
        self.assertEqual(config['elo_target'], 750)
        self.assertEqual(config['multipv'], 5)
        self.assertGreater(config['blunder_chance'], 0)

    def test_intermediate_settings(self):
        config = get_difficulty_config('intermediate')
        self.assertEqual(config['skill_level'], 8)
        self.assertEqual(config['depth'], 8)
        self.assertEqual(config['movetime'], 1000)
        self.assertEqual(config['nodes'], 8000)
        self.assertEqual(config['elo_target'], 1400)
        self.assertEqual(config['multipv'], 2)
        self.assertGreater(config['blunder_chance'], 0)

    def test_master_settings(self):
        config = get_difficulty_config('master')
        self.assertEqual(config['skill_level'], 20)
        self.assertEqual(config['depth'], 30)
        self.assertEqual(config['movetime'], 5000)
        self.assertNotIn('nodes', config)
        self.assertEqual(config['elo_target'], 3000)
        self.assertEqual(config['multipv'], 1)
        self.assertEqual(config['blunder_chance'], 0.0)

    def test_only_three_levels_exposed(self):
        self.assertEqual(set(DIFFICULTY_CONFIG.keys()), {'beginner', 'intermediate', 'master'})


class StockfishDifficultyAPITests(TestCase):
    """Verify the selected difficulty is forwarded from the frontend to the engine."""

    def setUp(self):
        self.client = Client()

    def _make_move(self, difficulty, expected_enum):
        fen = 'rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1'
        with patch.object(stockfish_service, 'is_engine_available', return_value=True), \
             patch.object(stockfish_service, 'is_engine_ready', return_value=True), \
             patch.object(stockfish_service, 'get_best_move', return_value='e7e5') as mock_get_move:
            response = self.client.post('/api/stockfish-move/', {
                'fen': fen,
                'difficulty': difficulty
            })

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['move'], 'e7e5')
        self.assertEqual(data['engine'], 'stockfish')
        self.assertEqual(data['difficulty'], difficulty)
        mock_get_move.assert_called_once()
        called_fen, called_difficulty = mock_get_move.call_args.args
        self.assertEqual(called_fen, fen)
        self.assertEqual(called_difficulty, expected_enum)

    def test_beginner_difficulty_passed_to_engine(self):
        self._make_move('beginner', DifficultyLevel.BEGINNER)

    def test_intermediate_difficulty_passed_to_engine(self):
        self._make_move('intermediate', DifficultyLevel.INTERMEDIATE)

    def test_master_difficulty_passed_to_engine(self):
        self._make_move('master', DifficultyLevel.MASTER)

    def test_game_page_csrf_cookie_allows_stockfish_request(self):
        client = Client(enforce_csrf_checks=True)
        game_response = client.get('/game/')

        self.assertEqual(game_response.status_code, 200)
        self.assertIn('csrftoken', game_response.cookies)

        csrf_token = game_response.cookies['csrftoken'].value
        fen = 'rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1'
        with patch.object(stockfish_service, 'is_engine_available', return_value=True), \
             patch.object(stockfish_service, 'is_engine_ready', return_value=True), \
             patch.object(stockfish_service, 'get_best_move', return_value='e7e5'):
            response = client.post(
                '/api/stockfish-move/',
                {'fen': fen, 'difficulty': 'intermediate'},
                HTTP_X_CSRFTOKEN=csrf_token,
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['move'], 'e7e5')
