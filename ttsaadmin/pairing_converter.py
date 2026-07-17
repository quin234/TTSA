"""
Data conversion utilities for tournament pairing services.

This module provides utilities to convert between Django models and the
pairing service data structures, ensuring clean separation between the
database layer and the pairing logic.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import Tournament, TournamentPlayer, TournamentGame, TournamentRound, TournamentStanding
from .pairing_interface import Player, Pairing, RoundPairings, GameResult

logger = logging.getLogger(__name__)


class PairingDataConverter:
    """
    Utility class for converting between Django models and pairing service data.
    """
    
    @staticmethod
    def tournament_to_players(tournament: Tournament) -> List[Player]:
        """
        Convert tournament players to Player objects for pairing service.
        
        Args:
            tournament: Tournament instance
            
        Returns:
            List of Player objects
        """
        players = []
        
        tournament_players = TournamentPlayer.objects.filter(
            tournament=tournament
        )
        
        for tp in tournament_players:
            # Calculate current score from completed games
            score = PairingDataConverter._calculate_player_score(tp, tournament)
            
            # Get color history
            color_history = PairingDataConverter._get_color_history(tp, tournament)
            
            player = Player(
                id=tp.id,
                name=tp.player_name,
                rating=tp.rating or 1200,
                score=score,
                color_history=color_history
            )
            players.append(player)
        
        return players
    
    @staticmethod
    def _calculate_player_score(tournament_player: TournamentPlayer, tournament: Tournament) -> float:
        """Calculate player's current score from completed games."""
        score = 0.0
        
        # Get all completed games for this player
        games = TournamentGame.objects.filter(
            tournament=tournament,
            result__in=['1-0', '0-1', '½-½']
        ).filter(
            models.Q(white_player=tournament_player) | 
            models.Q(black_player=tournament_player)
        )
        
        for game in games:
            if game.result == '1-0' and game.white_player == tournament_player:
                score += 1.0
            elif game.result == '0-1' and game.black_player == tournament_player:
                score += 1.0
            elif game.result == '½-½':
                score += 0.5
        
        # Add bye points
        bye_rounds = TournamentRound.objects.filter(
            tournament=tournament,
            bye_players=tournament_player
        )
        score += len(bye_rounds) * 1.0
        
        return score
    
    @staticmethod
    def _get_color_history(tournament_player: TournamentPlayer, tournament: Tournament) -> List[str]:
        """Get player's color history from completed rounds."""
        color_history = []
        
        completed_rounds = TournamentRound.objects.filter(
            tournament=tournament,
            status='completed'
        ).order_by('round_number')
        
        for round_obj in completed_rounds:
            games = TournamentGame.objects.filter(
                tournament=tournament,
                round_number=round_obj.round_number
            )
            
            for game in games:
                if game.white_player == tournament_player:
                    color_history.append('white')
                elif game.black_player == tournament_player:
                    color_history.append('black')
        
        return color_history
    
    @staticmethod
    def pairings_to_database(
        round_pairings: RoundPairings, 
        tournament: Tournament
    ) -> Tuple[TournamentRound, List[TournamentGame]]:
        """
        Convert RoundPairings to database objects.
        
        Args:
            round_pairings: RoundPairings from pairing service
            tournament: Tournament instance
            
        Returns:
            Tuple of (TournamentRound, List[TournamentGame])
        """
        # Create or get the round
        round_obj, created = TournamentRound.objects.get_or_create(
            tournament=tournament,
            round_number=round_pairings.round_number,
            defaults={
                'status': 'active',
                'pairings_generated_at': timezone.now()
            }
        )
        
        if not created:
            # Update existing round
            round_obj.pairings_generated_at = timezone.now()
            round_obj.save()
        
        # Create games
        games = []
        tournament_players = {
            tp.id: tp for tp in TournamentPlayer.objects.filter(
                tournament=tournament
            )
        }
        
        for pairing in round_pairings.pairings:
            # Get TournamentPlayer objects
            white_tp = tournament_players.get(pairing.white_player.id)
            black_tp = tournament_players.get(pairing.black_player.id)
            
            if not white_tp or not black_tp:
                logger.error(f"Could not find tournament players for pairing: {pairing}")
                continue
            
            # Create game
            game = TournamentGame.objects.create(
                tournament=tournament,
                round_number=round_pairings.round_number,
                board_number=pairing.board_number,
                white_player=white_tp,
                black_player=black_tp,
                result='*',  # Not started
                status='scheduled',
                scheduled_time=tournament.start_date
            )
            games.append(game)
        
        # Handle bye if present
        if round_pairings.bye_player:
            bye_tp = tournament_players.get(round_pairings.bye_player.id)
            if bye_tp:
                round_obj.bye_players.add(bye_tp)
        
        return round_obj, games
    
    @staticmethod
    def database_to_pairings(tournament: Tournament, round_number: int) -> RoundPairings:
        """
        Convert database objects to RoundPairings.
        
        Args:
            tournament: Tournament instance
            round_number: Round number to convert
            
        Returns:
            RoundPairings object
        """
        # Get round
        try:
            round_obj = TournamentRound.objects.get(
                tournament=tournament,
                round_number=round_number
            )
        except TournamentRound.DoesNotExist:
            raise ValueError(f"Round {round_number} not found for tournament {tournament.id}")
        
        # Get games
        games = TournamentGame.objects.filter(
            tournament=tournament,
            round_number=round_number
        ).order_by('board_number')
        
        # Convert to Player objects
        tournament_players = {
            tp.id: tp for tp in TournamentPlayer.objects.filter(
                tournament=tournament
            )
        }
        
        pairings = []
        for game in games:
            white_player = Player(
                id=game.white_player.id,
                name=game.white_player.player_name,
                rating=game.white_player.rating or 1200
            )
            black_player = Player(
                id=game.black_player.id,
                name=game.black_player.player_name,
                rating=game.black_player.rating or 1200
            )
            
            # Convert result
            result_map = {
                '*': GameResult.NOT_STARTED,
                '1-0': GameResult.WHITE_WIN,
                '0-1': GameResult.BLACK_WIN,
                '½-½': GameResult.DRAW
            }
            result = result_map.get(game.result, GameResult.NOT_STARTED)
            
            pairing = Pairing(
                board_number=game.board_number,
                white_player=white_player,
                black_player=black_player,
                result=result
            )
            pairings.append(pairing)
        
        # Handle bye
        bye_player = None
        if round_obj.bye_players.exists():
            bye_tp = round_obj.bye_players.first()
            bye_player = Player(
                id=bye_tp.id,
                name=bye_tp.player_name,
                rating=bye_tp.rating or 1200
            )
        
        return RoundPairings(
            round_number=round_number,
            pairings=pairings,
            bye_player=bye_player
        )
    
    @staticmethod
    def get_previous_pairings(tournament: Tournament, up_to_round: int) -> List[RoundPairings]:
        """
        Get all completed pairings up to a specific round.
        
        Args:
            tournament: Tournament instance
            up_to_round: Maximum round number to include
            
        Returns:
            List of RoundPairings
        """
        pairings_list = []
        
        completed_rounds = TournamentRound.objects.filter(
            tournament=tournament,
            round_number__lt=up_to_round,
            status='completed'
        ).order_by('round_number')
        
        for round_obj in completed_rounds:
            try:
                round_pairings = PairingDataConverter.database_to_pairings(
                    tournament, round_obj.round_number
                )
                pairings_list.append(round_pairings)
            except ValueError as e:
                logger.warning(f"Could not load round {round_obj.round_number}: {e}")
        
        return pairings_list
    
    @staticmethod
    def validate_round_completion(tournament: Tournament, round_number: int) -> bool:
        """
        Check if all games in a round are completed.
        
        Args:
            tournament: Tournament instance
            round_number: Round number to check
            
        Returns:
            True if all games are completed, False otherwise
        """
        games = TournamentGame.objects.filter(
            tournament=tournament,
            round_number=round_number
        )
        
        if not games.exists():
            return False
        
        # A round is complete only when every game is explicitly marked completed.
        # This allows results to be auto-saved as drafts before the round is submitted.
        incomplete_games = games.exclude(
            status='completed'
        ).count()
        
        return incomplete_games == 0
    
    @staticmethod
    def update_game_result(game_id: int, result: str) -> bool:
        """
        Update a game result as a draft. The round is not marked complete
        until submit_round_results is called, allowing results to be edited.
        
        Args:
            game_id: TournamentGame ID
            result: New result ('1-0', '0-1', '½-½', '*')
            
        Returns:
            True if update successful, False otherwise
        """
        try:
            game = TournamentGame.objects.get(id=game_id)
            game.result = result
            
            # Results are auto-saved as drafts (in_progress) until the round is submitted
            if result == '*':
                game.status = 'scheduled'
                game.completed_at = None
            else:
                game.status = 'in_progress'
                game.completed_at = None
            
            game.save()
            return True
            
        except TournamentGame.DoesNotExist:
            logger.error(f"Game {game_id} not found")
            return False
        except Exception as e:
            logger.error(f"Error updating game result: {e}")
            return False
    
    @staticmethod
    def submit_round_results(tournament: Tournament, round_number: int) -> Dict[str, Any]:
        """
        Confirm all auto-saved results for a round, mark games/round completed,
        and recalculate the standings.
        
        Args:
            tournament: Tournament instance
            round_number: Round number to submit
            
        Returns:
            Dict with success status, message, and round data
        """
        from decimal import Decimal

        try:
            round_obj = TournamentRound.objects.get(
                tournament=tournament,
                round_number=round_number
            )
        except TournamentRound.DoesNotExist:
            return {
                'success': False,
                'error': f'Round {round_number} does not exist'
            }
        
        games = TournamentGame.objects.filter(
            tournament=tournament,
            round_number=round_number
        )
        
        if not games.exists():
            return {
                'success': False,
                'error': f'No games found for round {round_number}'
            }
        
        # All games must have a result selected
        unplayed_games = games.filter(result='*')
        if unplayed_games.exists():
            missing = [f"Board {g.board_number}" for g in unplayed_games]
            return {
                'success': False,
                'error': f"Cannot submit round: results missing for {', '.join(missing)}"
            }
        
        # Mark all games as completed and lock results
        now = timezone.now()
        games.update(status='completed', completed_at=now)
        
        # Mark round as completed
        round_obj.status = 'completed'
        round_obj.end_time = now
        round_obj.save()
        
        # Recalculate standings for this round
        PairingDataConverter.recalculate_standings(tournament, round_number)
        
        return {
            'success': True,
            'message': f'Round {round_number} submitted and standings updated',
            'round_number': round_number,
            'games_count': games.count()
        }
    
    @staticmethod
    def recalculate_standings(tournament: Tournament, round_number: int = None) -> List[Dict[str, Any]]:
        """
        Recalculate tournament standings from completed games.
        
        Args:
            tournament: Tournament instance
            round_number: Round number to compute standings for (defaults to latest completed round)
            
        Returns:
            List of standing dictionaries sorted by rank
        """
        from decimal import Decimal

        # Determine which round to compute
        if round_number is None:
            max_round = TournamentRound.objects.filter(
                tournament=tournament,
                status='completed'
            ).order_by('-round_number').first()
            if not max_round:
                return []
            round_number = max_round.round_number

        # Delete existing standings for this round
        TournamentStanding.objects.filter(
            tournament=tournament,
            round_number=round_number
        ).delete()

        # Gather completed games up to this round (only confirmed results)
        games = list(TournamentGame.objects.filter(
            tournament=tournament,
            round_number__lte=round_number,
            status='completed'
        ))

        # Compute basic stats per player
        player_stats = {}
        for tp in TournamentPlayer.objects.filter(tournament=tournament):
            player_stats[tp.id] = {
                'player': tp,
                'points': Decimal('0'),
                'wins': 0,
                'draws': 0,
                'losses': 0,
                'white_games': 0,
                'black_games': 0,
                'cumulative_scores': [],
                'opponent_points': [],
                'sonneborn_points': [],
            }

        for game in games:
            white = player_stats.get(game.white_player_id)
            black = player_stats.get(game.black_player_id)
            if not white or not black:
                continue

            white['white_games'] += 1
            black['black_games'] += 1

            white_result = game.result
            white_score = Decimal('0')
            black_score = Decimal('0')

            if white_result == '1-0':
                white_score = Decimal('1')
                white['wins'] += 1
                black['losses'] += 1
            elif white_result == '0-1':
                black_score = Decimal('1')
                black['wins'] += 1
                white['losses'] += 1
            elif white_result == '½-½':
                white_score = Decimal('0.5')
                black_score = Decimal('0.5')
                white['draws'] += 1
                black['draws'] += 1
            else:
                continue

            white['points'] += white_score
            black['points'] += black_score

            white['opponent_points'].append((black['player'], black['points']))
            black['opponent_points'].append((white['player'], white['points']))

            # Sonneborn-Berger contributions use opponent's current total points
            if white_result == '1-0':
                white['sonneborn_points'].append(black['points'])
            elif white_result == '½-½':
                white['sonneborn_points'].append(black['points'] / Decimal('2'))
                black['sonneborn_points'].append(white['points'] / Decimal('2'))
            elif white_result == '0-1':
                black['sonneborn_points'].append(white['points'])

        # Build standings list with tie-breaks and rank
        standings_list = []
        for sid, stats in player_stats.items():
            # Cumulative score = sum of progressive scores after each round
            progressive = Decimal('0')
            cumulative_scores = []
            for game in games:
                if game.white_player_id == sid or game.black_player_id == sid:
                    if game.result == '1-0' and game.white_player_id == sid:
                        progressive += Decimal('1')
                    elif game.result == '0-1' and game.black_player_id == sid:
                        progressive += Decimal('1')
                    elif game.result == '½-½':
                        progressive += Decimal('0.5')
                    cumulative_scores.append(progressive)

            cumulative_score = sum(cumulative_scores) if cumulative_scores else Decimal('0')

            # Buchholz = sum of opponents' total points
            buchholz = sum(op_score for _, op_score in stats['opponent_points'])

            # Sonneborn-Berger = sum over wins/draws of opponent scores
            sonneborn_berger = sum(stats['sonneborn_points'])

            standings_list.append({
                'player': stats['player'],
                'points': stats['points'],
                'wins': stats['wins'],
                'draws': stats['draws'],
                'losses': stats['losses'],
                'white_games': stats['white_games'],
                'black_games': stats['black_games'],
                'games_played': stats['wins'] + stats['draws'] + stats['losses'],
                'buchholz': buchholz,
                'sonneborn_berger': sonneborn_berger,
                'cumulative_score': cumulative_score,
                'progressive_score': progressive,
            })

        # Sort by points, Buchholz, Sonneborn-Berger, then name
        standings_list.sort(key=lambda s: (
            -s['points'],
            -s['buchholz'],
            -s['sonneborn_berger'],
            s['player'].player_name
        ))

        # Assign ranks and persist TournamentStanding records
        for rank, standing in enumerate(standings_list, 1):
            player = standing['player']
            player.points = standing['points']
            player.wins = standing['wins']
            player.draws = standing['draws']
            player.losses = standing['losses']
            player.buchholz = standing['buchholz']
            player.sonneborn_berger = standing['sonneborn_berger']
            player.rank = rank
            player.save()

            TournamentStanding.objects.create(
                tournament=tournament,
                player=player,
                round_number=round_number,
                points=standing['points'],
                games_played=standing['games_played'],
                wins=standing['wins'],
                draws=standing['draws'],
                losses=standing['losses'],
                white_games=standing['white_games'],
                black_games=standing['black_games'],
                buchholz=standing['buchholz'],
                sonneborn_berger=standing['sonneborn_berger'],
                cumulative_score=standing['cumulative_score'],
                progressive_score=standing['progressive_score'],
                rank=rank,
            )

        return standings_list
