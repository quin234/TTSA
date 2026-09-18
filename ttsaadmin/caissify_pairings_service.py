"""
Caissify Pairings service implementation.

This module implements the PairingService interface using the caissify-pairings library
for FIDE-compliant Dutch Swiss tournament pairings.
"""

import logging
from typing import List, Dict, Any, Optional, Set, Tuple
import warnings

from caissify_pairings import generate_pairings, MissingFloatHistoryWarning

from .pairing_interface import (
    PairingService, Player, Pairing, RoundPairings, GameResult
)

logger = logging.getLogger(__name__)


class CaissifyPairingsService(PairingService):
    """
    Caissify Pairings implementation for FIDE-compliant Dutch Swiss tournaments.
    
    This service wraps the caissify-pairings library to provide tournament pairings
    that follow FIDE Dutch Swiss pairing rules (C.04.3) with full A.7 conformance.
    """
    
    def __init__(self):
        """Initialize the Caissify Pairings service."""
        self.name = "Caissify Pairings"
        self.version = "0.5.0"
        
        # Promote float history warnings to errors for strict compliance
        warnings.simplefilter("error", MissingFloatHistoryWarning)
        
        logger.info("Caissify Pairings service initialized")
    
    def generate_pairings(
        self, 
        players: List[Player], 
        round_number: int,
        previous_pairings: List[RoundPairings] = None,
        **kwargs
    ) -> RoundPairings:
        """
        Generate pairings using FIDE-compliant Dutch Swiss algorithm.
        
        Args:
            players: List of players to be paired
            round_number: Current round number (1-based)
            previous_pairings: List of previous round pairings
            **kwargs: Additional parameters (tournament_name, total_rounds, etc.)
            
        Returns:
            RoundPairings object with generated pairings
        """
        if not self.validate_pairing_request(players, round_number, previous_pairings):
            raise ValueError("Cannot generate pairings with given parameters")
        
        # Extract tournament parameters
        total_rounds = kwargs.get('total_rounds', 9)
        tournament_name = kwargs.get('tournament_name', 'Tournament')
        
        # Convert players to caissify-pairings format
        caissify_players = self._players_to_caissify_format(players, previous_pairings)
        
        # Extract previous pairings as set of tuples
        previous_pairings_set = self._extract_previous_pairings_set(previous_pairings)
        
        try:
            # Generate pairings using caissify-pairings
            caissify_pairings = generate_pairings(
                system="dutch",
                players=caissify_players,
                previous_pairings=previous_pairings_set,
                round_number=round_number,
                total_rounds=total_rounds,
                bye_value=1.0,
                max_byes_per_player=1
            )
            
            # Convert back to our format
            return self._caissify_to_round_pairings(caissify_pairings, round_number, players)
            
        except MissingFloatHistoryWarning as e:
            logger.error(f"Float history missing for round {round_number}: {e}")
            raise ValueError(
                f"Cannot generate pairings for round {round_number}: "
                f"Player float history is required from round 2 onward. "
                f"Ensure all previous rounds have been completed and results submitted."
            ) from e
        except Exception as e:
            logger.error(f"Error generating caissify pairings: {e}")
            raise
    
    def validate_pairing_request(
        self, 
        players: List[Player], 
        round_number: int,
        previous_pairings: List[RoundPairings] = None
    ) -> bool:
        """
        Validate that pairings can be generated for the given parameters.
        
        Args:
            players: List of players to be paired
            round_number: Current round number
            previous_pairings: List of previous round pairings
            
        Returns:
            True if pairings can be generated, False otherwise
        """
        # Need at least 2 players
        if len(players) < 2:
            logger.warning("Need at least 2 players to generate pairings")
            return False
        
        # Round number must be positive
        if round_number < 1:
            logger.warning(f"Invalid round number: {round_number}")
            return False
        
        # For round 2+, we need previous pairings with proper history
        if round_number >= 2:
            if not previous_pairings or len(previous_pairings) < round_number - 1:
                logger.warning(
                    f"Round {round_number} requires {round_number - 1} previous pairings, "
                    f"but only {len(previous_pairings) if previous_pairings else 0} provided"
                )
                return False
        
        return True
    
    def calculate_standings(
        self, 
        players: List[Player], 
        completed_rounds: List[RoundPairings]
    ) -> List[Player]:
        """
        Calculate tournament standings based on completed rounds.
        
        Args:
            players: List of all tournament players
            completed_rounds: List of completed round pairings with results
            
        Returns:
            List of players sorted by standing (best to worst)
        """
        # Calculate scores from completed rounds
        player_scores = {p.id: 0.0 for p in players}
        player_games = {p.id: 0 for p in players}
        
        for round_pairings in completed_rounds:
            for pairing in round_pairings.pairings:
                if pairing.result == GameResult.WHITE_WIN:
                    player_scores[pairing.white_player.id] += 1.0
                elif pairing.result == GameResult.BLACK_WIN:
                    player_scores[pairing.black_player.id] += 1.0
                elif pairing.result == GameResult.DRAW:
                    player_scores[pairing.white_player.id] += 0.5
                    player_scores[pairing.black_player.id] += 0.5
                
                player_games[pairing.white_player.id] += 1
                player_games[pairing.black_player.id] += 1
            
            # Handle bye
            if round_pairings.bye_player:
                player_scores[round_pairings.bye_player.id] += 1.0
        
        # Update player scores
        for player in players:
            player.score = player_scores.get(player.id, 0.0)
        
        # Sort by score (descending), then by rating (descending)
        sorted_players = sorted(
            players, 
            key=lambda p: (p.score, p.rating), 
            reverse=True
        )
        
        return sorted_players
    
    def get_service_name(self) -> str:
        """Return the name of this pairing service."""
        return self.name
    
    def get_service_version(self) -> str:
        """Return the version of this pairing service."""
        return self.version
    
    def _players_to_caissify_format(
        self, 
        players: List[Player], 
        previous_pairings: List[RoundPairings] = None
    ) -> List[Dict]:
        """
        Convert our Player objects to caissify-pairings format.
        
        Args:
            players: List of Player objects (with float_history and bye_count attributes)
            previous_pairings: List of previous round pairings (for validation)
            
        Returns:
            List of player dictionaries in caissify-pairings format
        """
        caissify_players = []
        
        for player in players:
            # Use the pre-calculated history from the Player object
            # (calculated by PairingDataConverter)
            caissify_player = {
                'id': player.id,
                'name': player.name,
                'rating': player.rating,
                'score': player.score,
                'starting_number': player.id,  # Use player ID as starting number
                'color_hist': player.color_history,
                'float_history': getattr(player, 'float_history', []),
                'bye_count': getattr(player, 'bye_count', 0)
            }
            caissify_players.append(caissify_player)
        
        return caissify_players
    
    def _extract_previous_pairings_set(
        self, 
        previous_pairings: List[RoundPairings] = None
    ) -> Set[Tuple[int, int]]:
        """
        Extract previous pairings as a set of tuples for caissify-pairings.
        
        Args:
            previous_pairings: List of previous round pairings
            
        Returns:
            Set of unordered (player_id_a, player_id_b) tuples
        """
        pairings_set = set()
        
        if not previous_pairings:
            return pairings_set
        
        for round_pairings in previous_pairings:
            for pairing in round_pairings.pairings:
                # Create unordered tuple (smaller ID first)
                player_ids = (pairing.white_player.id, pairing.black_player.id)
                unordered_pair = tuple(sorted(player_ids))
                pairings_set.add(unordered_pair)
        
        return pairings_set
    
    def _caissify_to_round_pairings(
        self, 
        caissify_pairings: List[Dict], 
        round_number: int,
        original_players: List[Player]
    ) -> RoundPairings:
        """
        Convert caissify-pairings output to our RoundPairings format.
        
        Args:
            caissify_pairings: List of pairing dictionaries from caissify-pairings
            round_number: Round number
            original_players: Original list of Player objects
            
        Returns:
            RoundPairings object
        """
        # Create player lookup
        player_map = {p.id: p for p in original_players}
        
        pairings = []
        bye_player = None
        
        for pairing_data in caissify_pairings:
            white_id = pairing_data['white_id']
            black_id = pairing_data.get('black_id')
            table_number = pairing_data['table']
            
            # Check if this is a bye
            if black_id is None or pairing_data.get('bye', False):
                # This is a bye
                bye_player = player_map.get(white_id)
                logger.info(f"Bye assigned to player {white_id} in round {round_number}")
            else:
                # Regular pairing
                white_player = player_map.get(white_id)
                black_player = player_map.get(black_id)
                
                if white_player and black_player:
                    pairing = Pairing(
                        board_number=table_number,
                        white_player=white_player,
                        black_player=black_player,
                        result=GameResult.NOT_STARTED
                    )
                    pairings.append(pairing)
                else:
                    logger.error(
                        f"Could not find players for pairing: white={white_id}, black={black_id}"
                    )
        
        return RoundPairings(
            round_number=round_number,
            pairings=pairings,
            bye_player=bye_player
        )


# Register the Caissify Pairings service
from .pairing_interface import PairingServiceFactory
PairingServiceFactory.register_service('caissify', CaissifyPairingsService)
