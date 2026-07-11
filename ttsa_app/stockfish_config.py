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
DIFFICULTY_CONFIG = {
    'beginner': {
        'skill_level': 0,
        'depth': 1,
        'movetime': 100,  # 100ms
        'nodes': 1000,
        'contempt': 0,
        'aggressiveness': 100,
    },
    'easy': {
        'skill_level': 3,
        'depth': 3,
        'movetime': 200,  # 200ms
        'nodes': 5000,
        'contempt': 0,
        'aggressiveness': 100,
    },
    'intermediate': {
        'skill_level': 10,
        'depth': 10,
        'movetime': 500,  # 500ms
        'nodes': 100000,
        'contempt': 0,
        'aggressiveness': 100,
    },
    'advanced': {
        'skill_level': 15,
        'depth': 15,
        'movetime': 1000,  # 1s
        'nodes': 500000,
        'contempt': 0,
        'aggressiveness': 100,
    },
    'expert': {
        'skill_level': 18,
        'depth': 18,
        'movetime': 2000,  # 2s
        'nodes': 1000000,
        'contempt': 0,
        'aggressiveness': 100,
    },
    'master': {
        'skill_level': 20,
        'depth': 20,
        'movetime': 3000,  # 3s
        'nodes': 10000000,
        'contempt': 0,
        'aggressiveness': 100,
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
