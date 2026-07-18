# Stockfish Chess Engine Integration Documentation

## Overview

This document describes the integration of the Stockfish chess engine into the TTSA chess application using the UCI (Universal Chess Interface) protocol. The integration is designed to be modular, allowing for easy replacement with other UCI-compatible engines while maintaining all existing UI and gameplay functionality.

## Architecture

### Components

1. **Stockfish Service** (`ttsa_app/stockfish_service.py`)
   - UCI protocol handler for communicating with Stockfish
   - Engine lifecycle management (startup/shutdown)
   - Singleton pattern for single engine instance
   - Error handling and retry logic

2. **Stockfish Configuration** (`ttsa_app/stockfish_config.py`)
   - Centralized configuration management
   - Difficulty level settings
   - Executable path detection
   - Easy engine replacement capability

3. **Django API Endpoint** (`ttsa_app/views.py:stockfish_move`)
   - REST API for move requests
   - Difficulty mapping
   - Graceful error handling
   - Fallback indicators

4. **Frontend Integration** (`templates/ttsa_app/chess_game.html`)
   - Async move requests to Stockfish API
   - Fallback to custom engine on failure
   - Seamless user experience

5. **Management Commands**
   - `python manage.py start_stockfish` - Manual engine start
   - `python manage.py stop_stockfish` - Manual engine stop

## Installation

### Prerequisites

- Stockfish chess engine executable
- Python 3.8+
- Django 5.1.1+

### Stockfish Installation

#### Windows
1. Download Stockfish from https://stockfishchess.org/download/
2. Extract to a directory (e.g., `C:\Program Files\Stockfish\`)
3. Copy `stockfish.exe` to project root or configure path in settings

#### Linux
```bash
sudo apt-get install stockfish  # Ubuntu/Debian
# or download from https://stockfishchess.org/download/
```

#### macOS
```bash
brew install stockfish  # Homebrew
# or download from https://stockfishchess.org/download/
```

### Configuration

#### Automatic Detection
The system automatically searches for Stockfish in standard locations:
- `stockfish.exe` / `stockfish` (current directory)
- `/usr/bin/stockfish`
- `/usr/local/bin/stockfish`
- `/opt/homebrew/bin/stockfish` (macOS)
- `C:\Program Files\Stockfish\stockfish.exe`
- `C:\Program Files (x86)\Stockfish\stockfish.exe`

#### Manual Configuration
If automatic detection fails, set the executable path in `ttsa_app/stockfish_config.py`:

```python
STOCKFISH_CONFIG = {
    'executable': '/path/to/your/stockfish',
    # ... other settings
}
```

## Usage

### Difficulty Levels

Play vs Computer exposes three learner-focused difficulty levels mapped to Stockfish settings.  Lower levels also use `MultiPV` so the engine can deliberately pick a weaker alternative line, creating the human-like mistakes and inaccuracies learners need.

| Level | Target Elo | Skill Level | Depth | Move Time | Nodes | MultiPV | Blunder Chance |
|-------|------------|-------------|-------|-----------|-------|---------|----------------|
| Beginner | 600-900 | 0 | 1 | 80ms | 100 | 5 | 60% |
| Intermediate | 1200-1600 | 8 | 8 | 1,000ms | 8,000 | 2 | 12% |
| Master | 2000+ | 20 | 30 | 5,000ms | unlimited | 1 | 0% |

### API Endpoint

**Endpoint:** `/api/stockfish-move/`  
**Method:** POST  
**Parameters:**
- `fen`: Current board position in FEN notation
- `difficulty`: Difficulty level string

**Response:**
```json
{
    "success": true,
    "move": "e2e4",
    "engine": "stockfish",
    "difficulty": "intermediate"
}
```

**Error Response (with fallback):**
```json
{
    "success": false,
    "error": "Stockfish engine not available",
    "fallback": true
}
```

### Frontend Integration

The frontend automatically uses Stockfish when available and falls back to the custom engine:

```javascript
async function makeAIMove() {
    try {
        // Try Stockfish first
        const response = await fetch('/api/stockfish-move/', {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (result.success && result.move) {
            executeAIMove(result.move);
        } else {
            // Fallback to custom engine
            const bestMove = chessEngine.findBestMove(game, currentDifficulty);
            executeAIMove(bestMove);
        }
    } catch (error) {
        // Fallback to custom engine
        const bestMove = chessEngine.findBestMove(game, currentDifficulty);
        executeAIMove(bestMove);
    }
}
```

## Engine Lifecycle Management

### Automatic Startup
The engine starts automatically on the first move request if not already running.

### Manual Control
```bash
# Start engine manually
python manage.py start_stockfish

# Stop engine manually
python manage.py stop_stockfish
```

### Automatic Shutdown
The engine can be configured to shut down automatically when not in use (configurable in `stockfish_config.py`).

## Error Handling

### Graceful Degradation

The system implements multiple layers of fallback:

1. **Stockfish Unavailable**: Falls back to custom JavaScript engine
2. **Stockfish Error**: Retries up to 3 times with engine reinitialization
3. **API Failure**: Falls back to custom engine
4. **Invalid Move**: Attempts alternative move

### Error Logging

All errors are logged with appropriate severity:
- `INFO`: Normal operations
- `WARNING`: Fallback triggers, retries
- `ERROR`: Critical failures

## Replacing the Engine

The modular design allows easy replacement with any UCI-compatible engine:

### Step 1: Update Configuration
In `ttsa_app/stockfish_config.py`:
```python
STOCKFISH_PATHS = [
    "your_engine.exe",  # Your engine executable
    # ... other paths
]
```

### Step 2: Adjust UCI Commands (if needed)
Some engines may require different UCI commands. Update the `UCIProtocol` class in `stockfish_service.py`.

### Step 3: Test Difficulty Settings
Adjust `DIFFICULTY_CONFIG` in `stockfish_config.py` to match your engine's capabilities.

## Testing

### Manual Testing
1. Start the Django development server
2. Navigate to the chess game page
3. Select a difficulty level
4. Play against the AI
5. Check browser console for engine status messages

### Automated Testing
```bash
# Test engine availability
python manage.py shell
>>> from ttsa_app.stockfish_service import stockfish_service
>>> stockfish_service.is_engine_available()
True

# Test engine startup
>>> stockfish_service.start_engine()
True

# Test move calculation
>>> from ttsa_app.stockfish_service import DifficultyLevel
>>> stockfish_service.get_best_move("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", DifficultyLevel.INTERMEDIATE)
'e2e4'
```

## Performance Considerations

### Response Time
- Beginner: ~100ms
- Intermediate: ~500ms
- Master: ~3s

### Memory Usage
- Stockfish typically uses 50-200MB depending on depth
- Custom engine uses minimal memory

### CPU Usage
- Stockfish can use multiple threads (configurable)
- Custom engine runs in browser main thread

## Troubleshooting

### Stockfish Not Found
**Symptom:** "Stockfish engine not available" error  
**Solution:** 
1. Verify Stockfish is installed
2. Check executable path in configuration
3. Ensure file permissions are correct

### Engine Not Responding
**Symptom:** Timeout waiting for best move  
**Solution:**
1. Check if engine process is running
2. Verify UCI protocol compatibility
3. Check system logs for errors

### Fallback Always Triggered
**Symptom:** Always using custom engine  
**Solution:**
1. Check browser console for error messages
2. Verify Django server is running
3. Check API endpoint accessibility

## Security Considerations

- Engine runs on server side (no client-side security risks)
- FEN strings are validated by chess.js before processing
- No user input is directly executed by the engine
- Engine process is isolated from web application

## Future Enhancements

### Potential Improvements
1. **Multi-threading**: Support for multiple concurrent games
2. **Engine Pool**: Multiple engine instances for load balancing
3. **Analysis Mode**: Position analysis without move selection
4. **Opening Book Integration**: Use engine's opening book
5. **Tablebase Support**: Endgame tablebase integration
6. **Custom Engine Support**: Easy switching between engines

### Additional Engines
The modular design supports integration of:
- Leela Chess Zero (LCZero)
- Komodo Dragon
- Houdini
- Any UCI-compatible engine

## Maintenance

### Regular Updates
1. Update Stockfish to latest version periodically
2. Review and adjust difficulty settings based on user feedback
3. Monitor engine performance and resource usage

### Monitoring
- Track fallback rate (should be minimal)
- Monitor response times
- Check error logs regularly

## Support

For issues or questions:
1. Check this documentation first
2. Review error logs
3. Test with custom engine fallback
4. Consult Stockfish documentation: https://stockfishchess.org/

## License

Stockfish is licensed under GPL v3. Ensure compliance when distributing the application.
