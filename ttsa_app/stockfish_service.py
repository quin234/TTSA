"""
Stockfish Chess Engine Service
Handles UCI protocol communication with Stockfish engine
"""

import subprocess
import threading
import queue
import logging
import os
import time
from typing import Optional, Dict, Any
from enum import Enum

logger = logging.getLogger(__name__)


class DifficultyLevel(Enum):
    """Stockfish difficulty levels"""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    MASTER = "master"


class StockfishConfig:
    """Stockfish engine configuration"""
    
    DIFFICULTY_SETTINGS = {
        DifficultyLevel.BEGINNER: {
            'skill_level': 0,
            'depth': 1,
            'movetime': 100,  # 100ms thinking time
            'nodes': 1000,
        },
        DifficultyLevel.INTERMEDIATE: {
            'skill_level': 10,
            'depth': 10,
            'movetime': 500,  # 500ms thinking time
            'nodes': 100000,
        },
        DifficultyLevel.MASTER: {
            'skill_level': 20,
            'depth': 25,
            'movetime': 5000,  # 5s thinking time for complex analysis
            'nodes': 10000000,
        }
    }


class UCIProtocol:
    """UCI Protocol handler for Stockfish communication"""
    
    def __init__(self, engine_path: str):
        self.engine_path = engine_path
        self.process: Optional[subprocess.Popen] = None
        self.output_queue = queue.Queue()
        self.reader_thread: Optional[threading.Thread] = None
        self.is_initialized = False
        self.lock = threading.Lock()
        
    def start(self) -> bool:
        """Start the Stockfish engine"""
        try:
            if not os.path.exists(self.engine_path):
                logger.error(f"Stockfish executable not found at: {self.engine_path}")
                return False
            
            self.process = subprocess.Popen(
                self.engine_path,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # Start reader thread
            self.reader_thread = threading.Thread(target=self._read_output, daemon=True)
            self.reader_thread.start()
            
            # Give the process a moment to start
            import time
            time.sleep(0.5)
            
            # Initialize UCI
            self.send_command("uci")
            response = self.wait_for_response("uciok", timeout=10000)
            
            if not response:
                logger.error("Failed to initialize UCI protocol - no uciok response")
                self.stop()
                return False
            
            self.is_initialized = True
            logger.info("Stockfish engine started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start Stockfish engine: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def stop(self):
        """Stop the Stockfish engine"""
        with self.lock:
            if self.process:
                try:
                    self.send_command("quit")
                    self.process.terminate()
                    self.process.wait(timeout=2)
                except:
                    self.process.kill()
                finally:
                    self.process = None
                    self.is_initialized = False
                    logger.info("Stockfish engine stopped")
    
    def send_command(self, command: str):
        """Send command to Stockfish"""
        if self.process and self.process.stdin:
            try:
                self.process.stdin.write(command + "\n")
                self.process.stdin.flush()
                logger.debug(f"Sent command: {command}")
            except Exception as e:
                logger.error(f"Failed to send command: {e}")
    
    def _read_output(self):
        """Read output from Stockfish engine"""
        if self.process and self.process.stdout:
            for line in self.process.stdout:
                line = line.strip()
                if line:
                    self.output_queue.put(line)
                    logger.debug(f"Received: {line}")
    
    def wait_for_response(self, expected: str, timeout: int = 5000) -> bool:
        """Wait for specific response from engine"""
        import time
        start_time = time.time()
        
        while time.time() - start_time < timeout / 1000:
            try:
                response = self.output_queue.get(timeout=0.1)
                if expected in response:
                    return True
            except queue.Empty:
                continue
        
        return False
    
    def get_best_move(self, fen: str, difficulty: DifficultyLevel) -> Optional[str]:
        """Get best move from Stockfish with error handling and retries"""
        if not self.is_initialized:
            logger.error("Engine not initialized")
            return None
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                settings = StockfishConfig.DIFFICULTY_SETTINGS[difficulty]
                
                with self.lock:
                    # Clear any previous output
                    while not self.output_queue.empty():
                        try:
                            self.output_queue.get_nowait()
                        except queue.Empty:
                            break
                    
                    # Set position
                    self.send_command(f"position fen {fen}")
                    
                    # Configure engine based on difficulty
                    self.send_command(f"setoption name Skill Level value {settings['skill_level']}")
                    self.send_command(f"setoption name Contempt value 0")
                    
                    # For master level, disable strength limiting for maximum performance
                    if difficulty == DifficultyLevel.MASTER:
                        self.send_command("setoption name UCI_LimitStrength value false")
                        self.send_command("setoption name Threads value 4")
                        self.send_command("setoption name Hash value 256")
                    else:
                        self.send_command("setoption name UCI_LimitStrength value true")
                    
                    # Search for best move
                    if settings['movetime']:
                        self.send_command(f"go movetime {settings['movetime']}")
                    else:
                        self.send_command(f"go depth {settings['depth']}")
                    
                    # Wait for bestmove response
                    start_time = time.time()
                    timeout = settings['movetime'] + 2000 if settings['movetime'] else 5000
                    
                    while time.time() - start_time < timeout / 1000:
                        try:
                            response = self.output_queue.get(timeout=0.1)
                            if response.startswith("bestmove"):
                                parts = response.split()
                                if len(parts) >= 2 and parts[1] != "(none)":
                                    logger.info(f"Best move: {parts[1]}")
                                    return parts[1]
                                else:
                                    logger.warning("No best move found")
                                    return None
                        except queue.Empty:
                            continue
                    
                    logger.warning(f"Timeout waiting for best move (attempt {attempt + 1}/{max_retries})")
                    
            except Exception as e:
                logger.error(f"Error getting best move (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    # Try to reinitialize engine
                    time.sleep(0.5)
                    if not self.isready():
                        logger.info("Attempting to reinitialize engine")
                        self.stop()
                        if self.start():
                            continue
        
        logger.error("Failed to get best move after all retries")
        return None
    
    def isready(self) -> bool:
        """Check if engine is ready"""
        if not self.is_initialized:
            return False
        
        try:
            self.send_command("isready")
            return self.wait_for_response("readyok", timeout=1000)
        except:
            return False


class StockfishService:
    """Singleton Stockfish service for managing engine lifecycle"""
    
    _instance = None
    _uci_protocol: Optional[UCIProtocol] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._uci_protocol is None:
            # Default Stockfish path - should be configurable
            stockfish_paths = [
                "stockfish.exe",  # Windows
                "stockfish",      # Linux/Mac
                "/usr/bin/stockfish",
                "/usr/local/bin/stockfish",
            ]
            
            self.engine_path = None
            for path in stockfish_paths:
                if os.path.exists(path):
                    self.engine_path = path
                    break
            
            if not self.engine_path:
                logger.warning("Stockfish executable not found in standard locations")
            
            self._uci_protocol = UCIProtocol(self.engine_path) if self.engine_path else None
    
    def start_engine(self) -> bool:
        """Start the Stockfish engine"""
        if not self._uci_protocol:
            logger.error("UCI protocol not initialized - Stockfish not found")
            return False
        
        return self._uci_protocol.start()
    
    def stop_engine(self):
        """Stop the Stockfish engine"""
        if self._uci_protocol:
            self._uci_protocol.stop()
    
    def get_best_move(self, fen: str, difficulty: DifficultyLevel) -> Optional[str]:
        """Get best move for given position with fallback handling"""
        if not self._uci_protocol:
            warning_msg = "Stockfish engine not available - custom engine will be used as fallback"
            logger.warning(warning_msg)
            return None
        
        try:
            return self._uci_protocol.get_best_move(fen, difficulty)
        except Exception as e:
            logger.error(f"Error getting best move from Stockfish: {e}")
            return None
    
    def is_engine_ready(self) -> bool:
        """Check if engine is ready"""
        return self._uci_protocol and self._uci_protocol.isready()
    
    def is_engine_available(self) -> bool:
        """Check if Stockfish is available"""
        return self._uci_protocol is not None


# Global instance
stockfish_service = StockfishService()
