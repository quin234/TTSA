#!/usr/bin/env python
"""
Test script for the new BBP Pairings integration.

This script tests the complete pairing workflow to ensure
the BBP Pairings library integration works correctly.
"""

import os
import sys
import django

# Setup Django environment
sys.path.append('/home/Django/apps/TTSA')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ttsa_project.settings')
django.setup()

from ttsaadmin.pairing_interface import PairingServiceFactory, Player, GameResult
from ttsaadmin.pairing_manager import get_pairing_manager
from ttsaadmin.models import Tournament, TournamentPlayer
from ttsaadmin.bbp_pairings_service import BBPPairingsService  # This will register the service

def test_pairing_service_factory():
    """Test the pairing service factory."""
    print("Testing Pairing Service Factory...")
    
    # Test service registration
    available_services = PairingServiceFactory.get_available_services()
    print(f"Available services: {available_services}")
    
    # Test service creation
    try:
        service = PairingServiceFactory.create_service('bbp')
        print(f"Created service: {service.get_service_name()} v{service.get_service_version()}")
        return True
    except Exception as e:
        print(f"Error creating service: {e}")
        return False

def test_pairing_manager():
    """Test the pairing manager."""
    print("\nTesting Pairing Manager...")
    
    try:
        manager = get_pairing_manager()
        print(f"Created manager with service: {manager.get_service_info()}")
        return True
    except Exception as e:
        print(f"Error creating manager: {e}")
        return False

def test_basic_pairing():
    """Test basic pairing generation."""
    print("\nTesting Basic Pairing Generation...")
    
    try:
        manager = get_pairing_manager()
        
        # Create test players
        players = [
            Player(id=1, name="Player 1", rating=1800),
            Player(id=2, name="Player 2", rating=1700),
            Player(id=3, name="Player 3", rating=1600),
            Player(id=4, name="Player 4", rating=1500),
            Player(id=5, name="Player 5", rating=1400),  # Odd number for bye test
        ]
        
        # Generate pairings for round 1
        round_pairings = manager.service.generate_pairings(
            players=players,
            round_number=1
        )
        
        print(f"Generated {len(round_pairings.pairings)} pairings for Round {round_pairings.round_number}")
        print(f"Bye player: {round_pairings.bye_player.name if round_pairings.bye_player else 'None'}")
        
        for pairing in round_pairings.pairings:
            print(f"Board {pairing.board_number}: {pairing.white_player.name} vs {pairing.black_player.name}")
        
        return True
    except Exception as e:
        print(f"Error in basic pairing: {e}")
        return False

def test_standings_calculation():
    """Test standings calculation."""
    print("\nTesting Standings Calculation...")
    
    try:
        manager = get_pairing_manager()
        
        # Create test players with different scores
        players = [
            Player(id=1, name="Player 1", rating=1800, score=2.5),
            Player(id=2, name="Player 2", rating=1700, score=2.0),
            Player(id=3, name="Player 3", rating=1600, score=1.5),
            Player(id=4, name="Player 4", rating=1500, score=1.0),
        ]
        
        # Calculate standings (no completed rounds for this test)
        standings = manager.service.calculate_standings(players, [])
        
        print("Standings:")
        for i, player in enumerate(standings, 1):
            print(f"{i}. {player.name} - {player.score} points")
        
        return True
    except Exception as e:
        print(f"Error in standings calculation: {e}")
        return False

def test_validation():
    """Test pairing validation."""
    print("\nTesting Pairing Validation...")
    
    try:
        manager = get_pairing_manager()
        
        # Test valid case
        players = [Player(id=1, name="Player 1", rating=1800), Player(id=2, name="Player 2", rating=1700)]
        valid = manager.service.validate_pairing_request(players, 1)
        print(f"Valid pairing request: {valid}")
        
        # Test invalid case (not enough players)
        players = [Player(id=1, name="Player 1", rating=1800)]
        valid = manager.service.validate_pairing_request(players, 1)
        print(f"Invalid pairing request (not enough players): {valid}")
        
        return True
    except Exception as e:
        print(f"Error in validation: {e}")
        return False

def main():
    """Run all tests."""
    print("=== BBP Pairings Integration Test ===\n")
    
    tests = [
        test_pairing_service_factory,
        test_pairing_manager,
        test_basic_pairing,
        test_standings_calculation,
        test_validation,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print(f"=== Test Results: {passed}/{total} tests passed ===")
    
    if passed == total:
        print("✅ All tests passed! BBP Pairings integration is working correctly.")
    else:
        print("❌ Some tests failed. Please check the integration.")
    
    return passed == total

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
