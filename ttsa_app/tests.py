from django.test import TestCase, Client
from unittest.mock import patch

from ttsa_app.stockfish_config import get_difficulty_config, DIFFICULTY_CONFIG
from ttsa_app.stockfish_service import DifficultyLevel, stockfish_service


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
