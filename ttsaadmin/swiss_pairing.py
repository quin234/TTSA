"""
Swiss Pairing Algorithm Service

This module implements a comprehensive Swiss pairing algorithm following FIDE principles:
- Pair players with similar scores
- Avoid repeat opponents
- Balance colors
- Handle byes correctly
- Support multiple sections
"""

from django.db import transaction, models
from django.utils import timezone
from django.core.exceptions import ValidationError
from decimal import Decimal
from typing import List, Dict, Tuple, Optional
import logging

from .models import (
    Tournament, TournamentPlayer, TournamentRound, TournamentGame, 
    TournamentPairing, TournamentStanding
)

logger = logging.getLogger(__name__)


class SwissPairingService:
    """Swiss pairing algorithm service following FIDE principles"""
    
    def __init__(self, tournament: Tournament):
        self.tournament = tournament
        self.current_round = tournament.tournament_rounds.count() + 1
        
    def generate_pairings(self, round_number: int = None) -> List[TournamentPairing]:
        """
        Generate Swiss pairings for a round
        
        Args:
            round_number: Round number to generate pairings for (defaults to next round)
            
        Returns:
            List of TournamentPairing objects
            
        Raises:
            ValidationError: If pairing cannot be generated
        """
        if round_number is None:
            round_number = self.current_round
            
        logger.info(f"Generating Swiss pairings for {self.tournament.name}, Round {round_number}")
        
        with transaction.atomic():
            # Validate tournament state
            self._validate_pairing_request(round_number)
            
            # Get players for pairing
            players = self._get_players_for_pairing(round_number)
            
            if len(players) < 2:
                raise ValidationError("Need at least 2 players to generate pairings")
            
            # Calculate current standings
            standings = self._calculate_current_standings(players, round_number - 1)
            
            # Generate pairings
            pairings = self._pair_players_swiss(players, standings, round_number)
            
            # Create round and games
            round_obj = self._create_round(round_number, pairings)
            
            logger.info(f"Generated {len(pairings)} pairings for Round {round_number}")
            return pairings
    
    def _validate_pairing_request(self, round_number: int):
        """Validate that pairings can be generated for this round"""
        # Check if round already exists
        if self.tournament.tournament_rounds.filter(round_number=round_number).exists():
            raise ValidationError(f"Round {round_number} already exists")
        
        # Check if previous round is completed
        if round_number > 1:
            prev_round = self.tournament.tournament_rounds.filter(round_number=round_number - 1).first()
            if not prev_round or prev_round.status != 'completed':
                raise ValidationError(f"Previous round must be completed before generating Round {round_number}")
        
        # Check if tournament has enough players
        active_players = self.tournament.players.filter(status='registered').count()
        if active_players < 2:
            raise ValidationError("Need at least 2 registered players")
    
    def _get_players_for_pairing(self, round_number: int) -> List[TournamentPlayer]:
        """Get eligible players for pairing"""
        players = list(self.tournament.players.filter(status='registered').order_by('-rating'))
        
        # For first round, sort by rating (highest first)
        if round_number == 1:
            return players
        
        # For subsequent rounds, sort by score and rating
        standings = self._calculate_current_standings(players, round_number - 1)
        
        # Create player standings mapping
        player_scores = {standing['player'].id: standing['points'] for standing in standings}
        
        # Sort by score (descending), then by rating (descending)
        players.sort(key=lambda p: (player_scores.get(p.id, Decimal('0')), p.rating), reverse=True)
        
        return players
    
    def _calculate_current_standings(self, players: List[TournamentPlayer], round_number: int) -> List[TournamentStanding]:
        """Calculate current standings up to specified round"""
        standings = []
        
        for player in players:
            # Get games up to this round
            games = self.tournament.games.filter(
                round_number__lte=round_number
            ).filter(
                models.Q(white_player=player) | models.Q(black_player=player)
            )
            
            # Calculate statistics
            points = Decimal('0')
            wins = 0
            draws = 0
            losses = 0
            white_games = 0
            black_games = 0
            
            for game in games:
                if game.white_player == player:
                    white_games += 1
                    if game.result == '1-0':
                        points += Decimal('1')
                        wins += 1
                    elif game.result == '½-½':
                        points += Decimal('0.5')
                        draws += 1
                    elif game.result == '0-1':
                        losses += 1
                else:  # black player
                    black_games += 1
                    if game.result == '0-1':
                        points += Decimal('1')
                        wins += 1
                    elif game.result == '½-½':
                        points += Decimal('0.5')
                        draws += 1
                    elif game.result == '1-0':
                        losses += 1
            
            # Calculate tie-breaks
            buchholz = self._calculate_buchholz(player, round_number)
            sonneborn_berger = self._calculate_sonneborn_berger(player, round_number)
            
            standings.append({
                'player': player,
                'points': points,
                'wins': wins,
                'draws': draws,
                'losses': losses,
                'white_games': white_games,
                'black_games': black_games,
                'buchholz': buchholz,
                'sonneborn_berger': sonneborn_berger
            })
        
        return standings
    
    def _calculate_buchholz(self, player: TournamentPlayer, round_number: int) -> Decimal:
        """Calculate Buchholz tie-break score"""
        total = Decimal('0')
        
        # Get opponents up to this round
        games = self.tournament.games.filter(
            round_number__lte=round_number
        ).filter(
            models.Q(white_player=player) | models.Q(black_player=player)
        )
        
        for game in games:
            opponent = game.black_player if game.white_player == player else game.white_player
            opponent_score = self._get_player_score(opponent, round_number)
            total += opponent_score
        
        return total
    
    def _calculate_sonneborn_berger(self, player: TournamentPlayer, round_number: int) -> Decimal:
        """Calculate Sonneborn-Berger tie-break score"""
        total = Decimal('0')
        
        games = self.tournament.games.filter(
            round_number__lte=round_number
        ).filter(
            models.Q(white_player=player) | models.Q(black_player=player)
        )
        
        for game in games:
            opponent = game.black_player if game.white_player == player else game.white_player
            opponent_score = self._get_player_score(opponent, round_number)
            
            if game.white_player == player:
                if game.result == '1-0':
                    total += opponent_score
                elif game.result == '½-½':
                    total += opponent_score / Decimal('2')
            else:  # black player
                if game.result == '0-1':
                    total += opponent_score
                elif game.result == '½-½':
                    total += opponent_score / Decimal('2')
        
        return total
    
    def _get_player_score(self, player: TournamentPlayer, round_number: int) -> Decimal:
        """Get player's score up to specified round"""
        games = self.tournament.games.filter(
            round_number__lte=round_number
        ).filter(
            models.Q(white_player=player) | models.Q(black_player=player)
        )
        
        points = Decimal('0')
        for game in games:
            if game.white_player == player:
                if game.result == '1-0':
                    points += Decimal('1')
                elif game.result == '½-½':
                    points += Decimal('0.5')
            else:  # black player
                if game.result == '0-1':
                    points += Decimal('1')
                elif game.result == '½-½':
                    points += Decimal('0.5')
        
        return points
    
    def _pair_players_swiss(self, players: List[TournamentPlayer], standings: List[Dict], round_number: int) -> List[TournamentPairing]:
        """Implement Swiss pairing algorithm following FIDE principles"""
        pairings = []
        paired_players = set()
        
        # Handle odd number of players - give bye to lowest-scoring player
        if len(players) % 2 == 1:
            bye_player = self._select_bye_player(players, standings)
            paired_players.add(bye_player.id)
            logger.info(f"Bye given to {bye_player.player_name}")
        
        # Group players by score
        score_groups = self._group_players_by_score(players, standings)
        
        # Pair within score groups
        for score, group_players in score_groups.items():
            available_players = [p for p in group_players if p.id not in paired_players]
            
            while len(available_players) >= 2:
                # Try to pair first available player
                player1 = available_players[0]
                player2 = self._find_opponent(player1, available_players[1:], standings, round_number)
                
                if player2:
                    # Create pairing
                    white, black = self._assign_colors(player1, player2, standings, round_number)
                    
                    pairing = TournamentPairing(
                        tournament=self.tournament,
                        round_number=round_number,
                        white_player=white,
                        black_player=black,
                        board_number=len(pairings) + 1,
                        white_score=self._get_player_score(white, round_number - 1),
                        black_score=self._get_player_score(black, round_number - 1),
                        mutual_games=self._count_mutual_games(white, black, round_number - 1)
                    )
                    
                    pairings.append(pairing)
                    paired_players.add(player1.id)
                    paired_players.add(player2.id)
                    available_players.remove(player1)
                    available_players.remove(player2)
                else:
                    # No suitable opponent found, try next player
                    available_players.remove(player1)
        
        # Handle any remaining players (shouldn't happen with proper algorithm)
        unpaired = [p for p in players if p.id not in paired_players]
        if unpaired:
            logger.warning(f"Unpaired players after Swiss algorithm: {[p.player_name for p in unpaired]}")
        
        return pairings
    
    def _select_bye_player(self, players: List[TournamentPlayer], standings: List[Dict]) -> TournamentPlayer:
        """Select player to receive bye (lowest-scoring player without previous bye)"""
        # Sort by score (ascending), then by rating (ascending)
        player_scores = {s['player'].id: s['points'] for s in standings}
        
        eligible_players = [p for p in players if not self._has_received_bye(p, self.current_round - 1)]
        
        if not eligible_players:
            # All players have had byes, select lowest scoring
            eligible_players = players
        
        eligible_players.sort(key=lambda p: (player_scores.get(p.id, Decimal('0')), p.rating))
        return eligible_players[0]
    
    def _has_received_bye(self, player: TournamentPlayer, round_number: int) -> bool:
        """Check if player has received a bye in previous rounds"""
        return player.bye_rounds.filter(round_number__lte=round_number).exists()
    
    def _group_players_by_score(self, players: List[TournamentPlayer], standings: List[Dict]) -> Dict[Decimal, List[TournamentPlayer]]:
        """Group players by their current score"""
        score_groups = {}
        
        for player in players:
            score = Decimal('0')
            for standing in standings:
                if standing['player'] == player:
                    score = standing['points']
                    break
            
            if score not in score_groups:
                score_groups[score] = []
            score_groups[score].append(player)
        
        return score_groups
    
    def _find_opponent(self, player: TournamentPlayer, candidates: List[TournamentPlayer], standings: List[Dict], round_number: int) -> Optional[TournamentPlayer]:
        """Find suitable opponent for player following Swiss rules"""
        for candidate in candidates:
            if self._can_pair(player, candidate, round_number):
                return candidate
        return None
    
    def _can_pair(self, player1: TournamentPlayer, player2: TournamentPlayer, round_number: int) -> bool:
        """Check if two players can be paired according to Swiss rules"""
        # Don't pair same player
        if player1.id == player2.id:
            return False
        
        # Check if they've played before
        mutual_games = self._count_mutual_games(player1, player2, round_number - 1)
        if mutual_games > 0:
            return False
        
        # Additional FIDE rules can be added here
        return True
    
    def _count_mutual_games(self, player1: TournamentPlayer, player2: TournamentPlayer, round_number: int) -> int:
        """Count how many times two players have faced each other"""
        return self.tournament.games.filter(
            round_number__lte=round_number
        ).filter(
            models.Q(white_player=player1, black_player=player2) |
            models.Q(white_player=player2, black_player=player1)
        ).count()
    
    def _assign_colors(self, player1: TournamentPlayer, player2: TournamentPlayer, standings: List[Dict], round_number: int) -> Tuple[TournamentPlayer, TournamentPlayer]:
        """Assign colors to players trying to balance color preferences"""
        # Get color history
        player1_white = self._get_color_count(player1, 'white', round_number - 1)
        player1_black = self._get_color_count(player1, 'black', round_number - 1)
        player2_white = self._get_color_count(player2, 'white', round_number - 1)
        player2_black = self._get_color_count(player2, 'black', round_number - 1)
        
        # Calculate color imbalance
        player1_imbalance = player1_white - player1_black
        player2_imbalance = player2_white - player2_black
        
        # Try to balance colors
        if abs(player1_imbalance) > abs(player2_imbalance):
            # Player1 has larger imbalance, give them their less frequent color
            if player1_imbalance > 0:
                return player2, player1  # player1 gets black
            else:
                return player1, player2  # player1 gets white
        elif abs(player2_imbalance) > abs(player1_imbalance):
            # Player2 has larger imbalance, give them their less frequent color
            if player2_imbalance > 0:
                return player1, player2  # player2 gets black
            else:
                return player2, player1  # player2 gets white
        else:
            # Both have similar imbalance, alternate or random
            if round_number % 2 == 1:
                return player1, player2
            else:
                return player2, player1
    
    def _get_color_count(self, player: TournamentPlayer, color: str, round_number: int) -> int:
        """Count how many times player has played with specified color"""
        if color == 'white':
            return self.tournament.games.filter(
                round_number__lte=round_number,
                white_player=player
            ).count()
        else:
            return self.tournament.games.filter(
                round_number__lte=round_number,
                black_player=player
            ).count()
    
    def _create_round(self, round_number: int, pairings: List[TournamentPairing]) -> TournamentRound:
        """Create tournament round and games from pairings"""
        # Create round
        round_obj = TournamentRound.objects.create(
            tournament=self.tournament,
            round_number=round_number,
            status='pairing',
            time_control=self.tournament.time_control,
            pairings_generated_at=timezone.now()
        )
        
        # Add bye players to round
        for player in self.tournament.players.filter(status='registered'):
            if player.id not in [p.white_player.id for p in pairings] and player.id not in [p.black_player.id for p in pairings]:
                round_obj.bye_players.add(player)
        
        # Create games from pairings
        for i, pairing in enumerate(pairings):
            game = TournamentGame.objects.create(
                tournament=self.tournament,
                round_number=round_number,
                board_number=i + 1,
                white_player=pairing.white_player,
                black_player=pairing.black_player,
                scheduled_time=timezone.now(),  # Should be configurable
                status='scheduled'
            )
            
            # Save pairing
            pairing.save()
        
        # Update round status
        round_obj.status = 'active'
        round_obj.save()
        
        return round_obj


class StandingsService:
    """Service for calculating and managing tournament standings"""
    
    def __init__(self, tournament: Tournament):
        self.tournament = tournament
    
    def update_standings(self, round_number: int = None):
        """Update standings for specified round (or latest round)"""
        if round_number is None:
            # Get latest completed round
            latest_round = self.tournament.rounds.filter(status='completed').order_by('-round_number').first()
            if not latest_round:
                return
            round_number = latest_round.round_number
        
        logger.info(f"Updating standings for {self.tournament.name}, Round {round_number}")
        
        with transaction.atomic():
            # Delete existing standings for this round
            TournamentStanding.objects.filter(
                tournament=self.tournament,
                round_number=round_number
            ).delete()
            
            # Get all players
            players = self.tournament.players.filter(status='registered')
            
            # Calculate standings for each player
            standings_list = []
            for player in players:
                standing = self._calculate_player_standing(player, round_number)
                standings_list.append(standing)
            
            # Sort and assign ranks
            standings_list.sort(key=lambda s: (
                -s['points'],
                -s['buchholz'],
                -s['sonneborn_berger'],
                s['player'].player_name
            ))
            
            # Create standing records
            for rank, standing_data in enumerate(standings_list, 1):
                TournamentStanding.objects.create(
                    tournament=self.tournament,
                    player=standing_data['player'],
                    round_number=round_number,
                    points=standing_data['points'],
                    games_played=standing_data['games_played'],
                    wins=standing_data['wins'],
                    draws=standing_data['draws'],
                    losses=standing_data['losses'],
                    buchholz=standing_data['buchholz'],
                    sonneborn_berger=standing_data['sonneborn_berger'],
                    cumulative_score=standing_data['cumulative_score'],
                    white_games=standing_data['white_games'],
                    black_games=standing_data['black_games'],
                    rank=rank
                )
        
        logger.info(f"Updated standings for {len(standings_list)} players")
    
    def _calculate_player_standing(self, player: TournamentPlayer, round_number: int) -> Dict:
        """Calculate standing for a single player"""
        # Get games up to this round
        games = self.tournament.games.filter(
            round_number__lte=round_number
        ).filter(
            models.Q(white_player=player) | models.Q(black_player=player)
        )
        
        # Calculate basic statistics
        points = Decimal('0')
        wins = 0
        draws = 0
        losses = 0
        white_games = 0
        black_games = 0
        cumulative_scores = []
        
        for game in games:
            game_points = Decimal('0')
            if game.white_player == player:
                white_games += 1
                if game.result == '1-0':
                    game_points = Decimal('1')
                    wins += 1
                elif game.result == '½-½':
                    game_points = Decimal('0.5')
                    draws += 1
                elif game.result == '0-1':
                    losses += 1
            else:  # black player
                black_games += 1
                if game.result == '0-1':
                    game_points = Decimal('1')
                    wins += 1
                elif game.result == '½-½':
                    game_points = Decimal('0.5')
                    draws += 1
                elif game.result == '1-0':
                    losses += 1
            
            points += game_points
            cumulative_scores.append(points)
        
        # Calculate tie-breaks
        buchholz = self._calculate_buchholz(player, round_number)
        sonneborn_berger = self._calculate_sonneborn_berger(player, round_number)
        cumulative_score = sum(cumulative_scores) if cumulative_scores else Decimal('0')
        
        return {
            'player': player,
            'points': points,
            'games_played': games.count(),
            'wins': wins,
            'draws': draws,
            'losses': losses,
            'buchholz': buchholz,
            'sonneborn_berger': sonneborn_berger,
            'cumulative_score': cumulative_score,
            'white_games': white_games,
            'black_games': black_games
        }
    
    def _calculate_buchholz(self, player: TournamentPlayer, round_number: int) -> Decimal:
        """Calculate Buchholz tie-break score"""
        total = Decimal('0')
        
        games = self.tournament.games.filter(
            round_number__lte=round_number
        ).filter(
            models.Q(white_player=player) | models.Q(black_player=player)
        )
        
        for game in games:
            opponent = game.black_player if game.white_player == player else game.white_player
            opponent_score = self._get_player_score(opponent, round_number)
            total += opponent_score
        
        return total
    
    def _calculate_sonneborn_berger(self, player: TournamentPlayer, round_number: int) -> Decimal:
        """Calculate Sonneborn-Berger tie-break score"""
        total = Decimal('0')
        
        games = self.tournament.games.filter(
            round_number__lte=round_number
        ).filter(
            models.Q(white_player=player) | models.Q(black_player=player)
        )
        
        for game in games:
            opponent = game.black_player if game.white_player == player else game.white_player
            opponent_score = self._get_player_score(opponent, round_number)
            
            if game.white_player == player:
                if game.result == '1-0':
                    total += opponent_score
                elif game.result == '½-½':
                    total += opponent_score / Decimal('2')
            else:  # black player
                if game.result == '0-1':
                    total += opponent_score
                elif game.result == '½-½':
                    total += opponent_score / Decimal('2')
        
        return total
    
    def _get_player_score(self, player: TournamentPlayer, round_number: int) -> Decimal:
        """Get player's score up to specified round"""
        games = self.tournament.games.filter(
            round_number__lte=round_number
        ).filter(
            models.Q(white_player=player) | models.Q(black_player=player)
        )
        
        points = Decimal('0')
        for game in games:
            if game.white_player == player:
                if game.result == '1-0':
                    points += Decimal('1')
                elif game.result == '½-½':
                    points += Decimal('0.5')
            else:  # black player
                if game.result == '0-1':
                    points += Decimal('1')
                elif game.result == '½-½':
                    points += Decimal('0.5')
        
        return points
