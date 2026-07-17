"""
Tournament Pairing Manager

This module provides the main interface for tournament pairings,
acting as a facade that coordinates between Django models,
the pairing service, and the data conversion utilities.
"""

import logging
from typing import List, Dict, Any, Optional
from django.core.exceptions import ValidationError
from django.db import transaction

from .pairing_interface import PairingServiceFactory, Player, RoundPairings
from .pairing_converter import PairingDataConverter

# Import BBP service to ensure registration
from .bbp_pairings_service import BBPPairingsService
from .models import Tournament, TournamentPlayer, TournamentGame, TournamentRound

logger = logging.getLogger(__name__)


class PairingManager:
    """
    Main interface for tournament pairing operations.
    
    This class provides a high-level API for tournament management while
    keeping the pairing logic modular and replaceable.
    """
    
    def __init__(self, service_name: str = 'bbp'):
        """
        Initialize the pairing manager.
        
        Args:
            service_name: Name of the pairing service to use
        """
        self.service_name = service_name
        self.service = None
        self._initialize_service()
    
    def _initialize_service(self):
        """Initialize the pairing service."""
        try:
            self.service = PairingServiceFactory.create_service(self.service_name)
            logger.info(f"Initialized pairing service: {self.service.get_service_name()}")
        except Exception as e:
            logger.error(f"Failed to initialize pairing service: {e}")
            raise
    
    def generate_next_round(self, tournament: Tournament) -> Dict[str, Any]:
        """
        Generate pairings for the next round in a tournament.
        
        Args:
            tournament: Tournament instance
            
        Returns:
            Dict with success status, round data, and message
            
        Raises:
            ValidationError: If pairings cannot be generated
        """
        try:
            with transaction.atomic():
                # Validate tournament state
                self._validate_tournament_state(tournament)
                
                # Get next round number
                next_round = self._get_next_round_number(tournament)
                
                # Get tournament players
                players = PairingDataConverter.tournament_to_players(tournament)
                
                # Get previous pairings
                previous_pairings = PairingDataConverter.get_previous_pairings(
                    tournament, next_round
                )
                
                # Generate pairings using the service
                round_pairings = self.service.generate_pairings(
                    players=players,
                    round_number=next_round,
                    previous_pairings=previous_pairings,
                    tournament_name=tournament.name
                )
                
                # Save pairings to database
                round_obj, games = PairingDataConverter.pairings_to_database(
                    round_pairings, tournament
                )
                
                # Update tournament status
                if tournament.status == 'registration':
                    tournament.status = 'in_progress'
                    tournament.save()
                
                return {
                    'success': True,
                    'round_number': next_round,
                    'round_id': round_obj.id,
                    'games_count': len(games),
                    'pairings': self._serialize_pairings(round_pairings),
                    'message': f'Successfully generated pairings for Round {next_round}'
                }
                
        except ValidationError as e:
            logger.error(f"Validation error generating round: {e}")
            return {
                'success': False,
                'error': str(e)
            }
        except Exception as e:
            logger.error(f"Error generating next round: {e}")
            return {
                'success': False,
                'error': 'Failed to generate pairings'
            }
    
    def update_game_result(self, game_id: int, result: str) -> Dict[str, Any]:
        """
        Update a game result as an auto-saved draft. Does not complete the round.
        
        Args:
            game_id: TournamentGame ID
            result: New result ('1-0', '0-1', '½-½', '*')
            
        Returns:
            Dict with success status and message
        """
        try:
            success = PairingDataConverter.update_game_result(game_id, result)
            
            if success:
                return {
                    'success': True,
                    'message': 'Result saved (draft)',
                    'round_completed': False
                }
            else:
                return {
                    'success': False,
                    'error': 'Failed to update game result'
                }
                
        except TournamentGame.DoesNotExist:
            return {
                'success': False,
                'error': 'Game not found'
            }
        except Exception as e:
            logger.error(f"Error updating game result: {e}")
            return {
                'success': False,
                'error': 'Failed to update game result'
            }
    
    def submit_round_results(self, tournament: Tournament, round_number: int) -> Dict[str, Any]:
        """
        Finalize all auto-saved results for a round and update standings.
        
        Args:
            tournament: Tournament instance
            round_number: Round number to submit
            
        Returns:
            Dict with success status and message
        """
        try:
            return PairingDataConverter.submit_round_results(tournament, round_number)
        except Exception as e:
            logger.error(f"Error submitting round {round_number}: {e}")
            return {
                'success': False,
                'error': 'Failed to submit round results'
            }
    
    def get_current_standings(self, tournament: Tournament) -> List[Dict[str, Any]]:
        """
        Get current tournament standings.
        
        Args:
            tournament: Tournament instance
            
        Returns:
            List of player standings data
        """
        try:
            # Recalculate standings
            standings_list = PairingDataConverter.recalculate_standings(tournament)
            
            # Serialize standings
            standings = []
            for i, standing in enumerate(standings_list, 1):
                player = standing['player']
                standings.append({
                    'rank': i,
                    'player_id': player.id,
                    'player_name': player.player_name,
                    'rating': player.rating or 1200,
                    'score': float(standing['points']),
                    'tie_break': float(standing['buchholz']),
                    'games_played': standing['games_played']
                })
            
            return standings
            
        except Exception as e:
            logger.error(f"Error getting standings: {e}")
            return []
    
    def get_round_pairings(self, tournament: Tournament, round_number: int) -> Dict[str, Any]:
        """
        Get pairings for a specific round.
        
        Args:
            tournament: Tournament instance
            round_number: Round number
            
        Returns:
            Dict with pairings data
        """
        try:
            round_pairings = PairingDataConverter.database_to_pairings(
                tournament, round_number
            )
            
            return {
                'success': True,
                'round_number': round_number,
                'pairings': self._serialize_pairings(round_pairings),
                'bye_player': self._serialize_player(round_pairings.bye_player) if round_pairings.bye_player else None
            }
            
        except ValueError as e:
            return {
                'success': False,
                'error': str(e)
            }
        except Exception as e:
            logger.error(f"Error getting round pairings: {e}")
            return {
                'success': False,
                'error': 'Failed to get round pairings'
            }
    
    def validate_pairing_request(self, tournament: Tournament) -> Dict[str, Any]:
        """
        Validate if the tournament is ready for next round pairings.
        
        Args:
            tournament: Tournament instance
            
        Returns:
            Dict with validation results
        """
        try:
            # Get current round from TournamentRound objects
            current_round = self._get_current_round_number(tournament)
            
            # Check if current round is complete
            if current_round:
                if not PairingDataConverter.validate_round_completion(
                    tournament, current_round
                ):
                    return {
                        'valid': False,
                        'error': f'Round {current_round} is not complete',
                        'incomplete_games': self._get_incomplete_games(tournament, current_round)
                    }
            
            # Check if tournament has enough players
            player_count = TournamentPlayer.objects.filter(tournament=tournament).count()
            if player_count < 2:
                return {
                    'valid': False,
                    'error': 'Need at least 2 players to generate pairings'
                }
            
            # Check if tournament is at max rounds
            if current_round and current_round >= tournament.rounds:
                return {
                    'valid': False,
                    'error': 'Tournament has reached maximum number of rounds'
                }
            
            return {
                'valid': True,
                'message': 'Tournament is ready for next round pairings'
            }
            
        except Exception as e:
            logger.error(f"Error validating pairing request: {e}")
            return {
                'valid': False,
                'error': 'Failed to validate tournament state'
            }
    
    def _validate_tournament_state(self, tournament: Tournament):
        """Validate tournament state before generating pairings."""
        validation = self.validate_pairing_request(tournament)
        if not validation['valid']:
            raise ValidationError(validation['error'])
    
    def _get_current_round_number(self, tournament: Tournament) -> Optional[int]:
        """Get the current round number for the tournament."""
        try:
            # Get the highest round number that exists
            latest_round = TournamentRound.objects.filter(
                tournament=tournament
            ).order_by('-round_number').first()
            
            if latest_round:
                return latest_round.round_number
            else:
                return None
        except Exception:
            return None
    
    def _get_next_round_number(self, tournament: Tournament) -> int:
        """Get the next round number for the tournament."""
        current_round = self._get_current_round_number(tournament)
        if current_round:
            return current_round + 1
        else:
            return 1
    
    def _serialize_pairings(self, round_pairings: RoundPairings) -> List[Dict[str, Any]]:
        """Serialize pairings to JSON-serializable format."""
        pairings_data = []
        
        for pairing in round_pairings.pairings:
            pairings_data.append({
                'board_number': pairing.board_number,
                'white_player': self._serialize_player(pairing.white_player),
                'black_player': self._serialize_player(pairing.black_player),
                'result': pairing.result.value
            })
        
        return pairings_data
    
    def calculate_standings(self, players: List[Player], completed_rounds: List[RoundPairings]) -> List[Player]:
        """
        Calculate tournament standings based on completed rounds.
        
        Args:
            players: List of Player objects
            completed_rounds: List of completed round pairings
            
        Returns:
            List of Player objects sorted by standings
        """
        try:
            # Use the pairing service to calculate standings
            return self.service.calculate_standings(players, completed_rounds)
        except Exception as e:
            logger.error(f"Error calculating standings: {e}")
            # Fallback: sort by existing scores
            return sorted(players, key=lambda p: (-p.score, -p.rating))

    def _serialize_player(self, player: Player) -> Dict[str, Any]:
        """Serialize player to JSON-serializable format."""
        return {
            'id': player.id,
            'name': player.name,
            'rating': player.rating,
            'score': player.score
        }
    
    def _get_games_played(self, tournament_player: TournamentPlayer, tournament: Tournament) -> int:
        """Get number of games played by a player."""
        return TournamentGame.objects.filter(
            tournament=tournament
        ).filter(
            models.Q(white_player=tournament_player) | 
            models.Q(black_player=tournament_player)
        ).exclude(result='*').count()
    
    def _get_incomplete_games(self, tournament: Tournament, round_number: int) -> List[Dict[str, Any]]:
        """Get list of incomplete games for a round."""
        games = TournamentGame.objects.filter(
            tournament=tournament,
            round_number=round_number,
            result='*'
        ).order_by('board_number')
        
        incomplete_games = []
        for game in games:
            incomplete_games.append({
                'board_number': game.board_number,
                'white_player': game.white_player.player_name,
                'black_player': game.black_player.player_name
            })
        
        return incomplete_games
    
    def get_service_info(self) -> Dict[str, str]:
        """Get information about the current pairing service."""
        return {
            'name': self.service.get_service_name(),
            'version': self.service.get_service_version()
        }
    
    def switch_service(self, service_name: str):
        """
        Switch to a different pairing service.
        
        Args:
            service_name: Name of the new service to use
        """
        self.service_name = service_name
        self._initialize_service()
        logger.info(f"Switched to pairing service: {service_name}")


# Global pairing manager instance
_pairing_manager = None

def get_pairing_manager(service_name: str = 'bbp') -> PairingManager:
    """
    Get the global pairing manager instance.
    
    Args:
        service_name: Name of the pairing service to use
        
    Returns:
        PairingManager instance
    """
    global _pairing_manager
    if _pairing_manager is None or _pairing_manager.service_name != service_name:
        _pairing_manager = PairingManager(service_name)
    return _pairing_manager
