"""
Stockfish Configuration Module
Allows easy configuration and replacement of UCI-compatible engines
"""

import os
from pathlib import Path

# Stockfish executable paths to search
STOCKFISH_PATHS = [
    "stockfish.exe",  # Windows
    "stockfish",      # Linux/Mac
    "/usr/bin/stockfish",
    "/usr/local/bin/stockfish",
    "/usr/games/stockfish",  # Ubuntu/Debian
    "/opt/homebrew/bin/stockfish",  # macOS Homebrew
    "C:\\Program Files\\Stockfish\\stockfish.exe",
    "C:\\Program Files (x86)\\Stockfish\\stockfish.exe",
]

# Default Stockfish configuration
STOCKFISH_CONFIG = {
    'executable': 'stockfish.exe',  # Stockfish executable in project root
    'auto_start': True,  # Automatically start engine on first request
    'auto_shutdown': False,  # Keep engine running between requests
    'timeout': 5000,  # Default timeout in milliseconds
    'max_retries': 3,  # Maximum retry attempts on failure
}

# Difficulty level configurations
# Play vs Computer exposes only three learner-focused levels.  Each is tuned
# to a target Elo band using Stockfish's Skill Level together with shallow
# search limits so weaker levels cannot "think" past their configured ceiling.
# UCI_Elo is not used because this binary produced erratic/illegal moves with
# it during testing; Skill Level gives stable, monotonic difficulty.
DIFFICULTY_CONFIG = {
    'beginner': {
        'elo_target': 750,
        # 'description': 'Simple moves, human-like mistakes, and missed tactics (~600-900 Elo)',
        'skill_level': 0,
        'use_uci_elo': False,
        'uci_elo': None,
        'limit_strength': False,
        'depth': 1,
        'movetime': 80,
        'nodes': 100,
        'threads': 1,
        'hash': 16,
        'multipv': 5,
        'blunder_chance': 0.6,
        'second_best_only': False,
    },
    'intermediate': {
        'elo_target': 1400,
        'description': '',
        'skill_level': 8,
        'use_uci_elo': False,
        'uci_elo': None,
        'limit_strength': False,
        'depth': 8,
        'movetime': 1000,
        'nodes': 8000,
        'threads': 1,
        'hash': 64,
        'multipv': 2,
        'blunder_chance': 0.12,
        'second_best_only': True,
    },
    'master': {
        'elo_target': 3000,
        # 'description': 'Full-strength Stockfish, always choosing the strongest moves (2000+ Elo)',
        'skill_level': 20,
        'use_uci_elo': False,
        'uci_elo': None,
        'limit_strength': False,
        'depth': 30,
        'movetime': 5000,
        'threads': 4,
        'hash': 256,
        'multipv': 1,
        'blunder_chance': 0.0,
        'second_best_only': False,
    },
}


def find_stockfish_executable() -> str:
    """Find Stockfish executable in standard locations"""
    for path in STOCKFISH_PATHS:
        if os.path.exists(path):
            return path
    
    # Check in project directory
    project_dir = Path(__file__).parent.parent
    for path in STOCKFISH_PATHS:
        full_path = project_dir / path
        if full_path.exists():
            return str(full_path)
    
    return None


def get_stockfish_config() -> dict:
    """Get current Stockfish configuration"""
    config = STOCKFISH_CONFIG.copy()
    
    # Auto-detect executable if not set
    if config['executable'] is None:
        config['executable'] = find_stockfish_executable()
    
    return config


def set_stockfish_executable(path: str):
    """Manually set Stockfish executable path"""
    if os.path.exists(path):
        STOCKFISH_CONFIG['executable'] = path
        return True
    return False


def get_difficulty_config(difficulty: str) -> dict:
    """Get configuration for specific difficulty level"""
    return DIFFICULTY_CONFIG.get(difficulty.lower(), DIFFICULTY_CONFIG['intermediate'])
