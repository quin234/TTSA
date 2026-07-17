"""
Abstract interface for tournament pairing services.

This module defines the contract that all pairing services must implement,
making it easy to swap between different pairing algorithms while maintaining
consistent behavior across the application.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum


class GameResult(Enum):
    """Standard chess game results."""
    WHITE_WIN = "1-0"
    BLACK_WIN = "0-1"
    DRAW = "½-½"
    NOT_STARTED = "*"


@dataclass
class Player:
    """Represents a tournament player."""
    id: int
    name: str
    rating: int
    score: float = 0.0
    tie_break_score: float = 0.0
    color_history: List[str] = None
    
    def __post_init__(self):
        if self.color_history is None:
            self.color_history = []


@dataclass
class Pairing:
    """Represents a single game pairing."""
    board_number: int
    white_player: Player
    black_player: Player
    result: GameResult = GameResult.NOT_STARTED
    
    def get_player_ids(self) -> tuple:
        """Return tuple of (white_player_id, black_player_id)."""
        return (self.white_player.id, self.black_player.id)


@dataclass
class RoundPairings:
    """Contains all pairings for a tournament round."""
    round_number: int
    pairings: List[Pairing]
    bye_player: Optional[Player] = None
    
    def get_all_players(self) -> List[int]:
        """Get all player IDs involved in this round."""
        player_ids = []
        for pairing in self.pairings:
            player_ids.extend(pairing.get_player_ids())
        if self.bye_player:
            player_ids.append(self.bye_player.id)
        return player_ids


class PairingService(ABC):
    """
    Abstract base class for tournament pairing services.
    
    All pairing implementations must inherit from this class and implement
    the required methods to ensure consistent behavior.
    """
    
    @abstractmethod
    def generate_pairings(
        self, 
        players: List[Player], 
        round_number: int,
        previous_pairings: List[RoundPairings] = None,
        **kwargs
    ) -> RoundPairings:
        """
        Generate pairings for a tournament round.
        
        Args:
            players: List of players to be paired
            round_number: Current round number (1-based)
            previous_pairings: List of previous round pairings for conflict checking
            **kwargs: Additional parameters specific to the pairing algorithm
            
        Returns:
            RoundPairings object containing the generated pairings
            
        Raises:
            ValidationError: If pairings cannot be generated
        """
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
    def get_service_name(self) -> str:
        """Return the name of this pairing service."""
        pass
    
    @abstractmethod
    def get_service_version(self) -> str:
        """Return the version of this pairing service."""
        pass


class PairingServiceFactory:
    """Factory for creating pairing service instances."""
    
    _services = {}
    
    @classmethod
    def register_service(cls, name: str, service_class: type):
        """Register a pairing service implementation."""
        cls._services[name] = service_class
    
    @classmethod
    def create_service(cls, name: str, **kwargs) -> PairingService:
        """Create an instance of a registered pairing service."""
        if name not in cls._services:
            raise ValueError(f"Unknown pairing service: {name}")
        return cls._services[name](**kwargs)
    
    @classmethod
    def get_available_services(cls) -> List[str]:
        """Get list of available service names."""
        return list(cls._services.keys())
