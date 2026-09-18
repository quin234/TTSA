"""
BBP Pairings service implementation.

This module implements the PairingService interface using the caissify-pairings library
for FIDE-compliant Dutch Swiss tournament pairings.

Note: This service now delegates to CaissifyPairingsService for better FIDE compliance.
The 'bbp' name is maintained for backward compatibility.
"""

import logging
from typing import List, Dict, Any, Optional

from .pairing_interface import (
    PairingService, Player, Pairing, RoundPairings, GameResult,
    PairingServiceFactory
)

logger = logging.getLogger(__name__)


class BBPPairingsService(PairingService):
    """
    BBP Pairings implementation for FIDE-compliant Swiss tournaments.
    
    This service now delegates to CaissifyPairingsService for proper FIDE Dutch 
    Swiss pairings with full A.7 conformance. The 'bbp' name is maintained for 
    backward compatibility.
    """
    
    def __init__(self):
        """Initialize the BBP Pairings service."""
        self.name = "BBP Pairings (delegated to Caissify)"
        self.version = "2.0.0"
        
        # Import and use the caissify service internally
        from .caissify_pairings_service import CaissifyPairingsService
        self._caissify_service = CaissifyPairingsService()
        
        logger.info("BBP Pairings service initialized (delegating to Caissify)")
    
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
            **kwargs: Additional parameters (tournament_name, etc.)
            
        Returns:
            RoundPairings object with generated pairings
        """
        logger.info("BBP service delegating to Caissify for FIDE-compliant pairings")
        return self._caissify_service.generate_pairings(
            players=players,
            round_number=round_number,
            previous_pairings=previous_pairings,
            **kwargs
        )
    
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
        return self._caissify_service.validate_pairing_request(
            players, round_number, previous_pairings
        )
    
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
        return self._caissify_service.calculate_standings(players, completed_rounds)
    
    def get_service_name(self) -> str:
        """Return the name of this pairing service."""
        return self.name
    
    def get_service_version(self) -> str:
        """Return the version of this pairing service."""
        return self.version


# Register the BBP Pairings service (now delegates to Caissify)
PairingServiceFactory.register_service('bbp', BBPPairingsService)
