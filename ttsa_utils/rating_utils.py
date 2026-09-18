"""Rating calculation utilities for tournaments"""

import logging
from elote import Glicko2Competitor

logger = logging.getLogger(__name__)


def update_tournament_ratings(tournament):
    """Update player ratings using Glicko-2 algorithm after tournament games."""
    from ttsaadmin.models import TournamentPlayer, TournamentGame

    logger.info(f"Starting rating update for tournament {tournament.id} ({tournament.name})")

    # Get all players in the tournament with their current ratings
    players = {}
    for tp in tournament.players.all():
        logger.info(f"Player {tp.player_name} - Current rating: {tp.rating}")
        # Use Glicko-2 competitor with player's current rating
        # If player doesn't have RD/volatility stored, use defaults
        players[tp.id] = Glicko2Competitor(
            initial_rating=tp.rating,
            initial_rd=getattr(tp, 'rating_deviation', 350),
            initial_volatility=getattr(tp, 'volatility', 0.06)
        )

    # Process all completed games
    completed_games = tournament.games.filter(
        result__in=['1-0', '0-1', '½-½']
    ).select_related('white_player', 'black_player')

    logger.info(f"Found {completed_games.count()} completed games for rating calculation")

    for game in completed_games:
        white_player_id = game.white_player.id
        black_player_id = game.black_player.id

        if white_player_id not in players or black_player_id not in players:
            logger.warning(f"Skipping game {game.id} - missing player references")
            continue

        white_player = players[white_player_id]
        black_player = players[black_player_id]

        logger.info(f"Processing game {game.id}: {game.white_player.player_name} vs {game.black_player.player_name}, result: {game.result}")

        # Convert chess result to score format (from white's perspective)
        if game.result == '1-0':
            white_player.beat(black_player)
        elif game.result == '0-1':
            black_player.beat(white_player)
        elif game.result == '½-½':
            white_player.draw(black_player)

    # Update player ratings in database
    for player_id, competitor in players.items():
        try:
            tp = TournamentPlayer.objects.get(id=player_id)
            old_rating = tp.rating
            tp.rating = int(competitor.rating)
            # Store additional Glicko-2 metrics if model supports them
            if hasattr(tp, 'rating_deviation'):
                tp.rating_deviation = competitor.rd
            if hasattr(tp, 'volatility'):
                tp.volatility = competitor.volatility
            tp.save()
            logger.info(f"Updated {tp.player_name}: {old_rating} -> {tp.rating} (RD: {competitor.rd}, Vol: {competitor.volatility})")
        except TournamentPlayer.DoesNotExist:
            logger.error(f"TournamentPlayer {player_id} not found")
            continue

    logger.info(f"Rating update completed for tournament {tournament.id}")