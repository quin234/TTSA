"""
Stockfish Chess Engine Service
Handles UCI protocol communication with Stockfish engine
"""

import subprocess
import threading
import queue
import logging
import os
import random
import re
import time
from typing import Optional, Dict, Any
from enum import Enum

from .stockfish_config import find_stockfish_executable, get_difficulty_config

logger = logging.getLogger(__name__)


class DifficultyLevel(Enum):
    """Stockfish difficulty levels exposed by Play vs Computer"""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    MASTER = "master"


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
        """Get best move from Stockfish with error handling and retries.

        The selected difficulty controls not only Stockfish's Skill Level and
        search limits but also how often a weaker alternative line is chosen.
        This guarantees that Beginner/Intermediate actually play weaker moves
        instead of always returning the engine's top choice.
        """
        if not self.is_initialized:
            logger.error("Engine not initialized")
            return None

        max_retries = 3
        for attempt in range(max_retries):
            try:
                settings = get_difficulty_config(difficulty.value)
                multipv = max(1, settings.get('multipv', 1))
                blunder_chance = settings.get('blunder_chance', 0.0)
                second_best_only = settings.get('second_best_only', False)

                with self.lock:
                    # Clear any previous output
                    while not self.output_queue.empty():
                        try:
                            self.output_queue.get_nowait()
                        except queue.Empty:
                            break

                    # Set position
                    self.send_command(f"position fen {fen}")

                    # Engine resources per difficulty
                    self.send_command(f"setoption name Threads value {settings.get('threads', 1)}")
                    self.send_command(f"setoption name Hash value {settings.get('hash', 32)}")
                    self.send_command(f"setoption name MultiPV value {multipv}")

                    # Configure engine strength per difficulty
                    # UCI_Elo is only applied when within Stockfish's supported range (1320-3190).
                    # When UCI_Elo is active it controls the engine's skill, so don't send Skill Level.
                    if settings.get('use_uci_elo') and settings.get('uci_elo'):
                        self.send_command("setoption name UCI_LimitStrength value true")
                        self.send_command(f"setoption name UCI_Elo value {settings['uci_elo']}")
                    else:
                        self.send_command("setoption name UCI_LimitStrength value false")
                        self.send_command(f"setoption name Skill Level value {settings['skill_level']}")

                    self.send_command("setoption name Contempt value 0")

                    # Ensure option changes are applied before searching
                    self.send_command("isready")
                    if not self.wait_for_response("readyok", timeout=5000):
                        logger.warning("Engine did not respond to isready")

                    # Build go command with depth, time, and node limits
                    go_parts = [f"depth {settings['depth']}"]
                    if settings.get('movetime'):
                        go_parts.append(f"movetime {settings['movetime']}")
                    if settings.get('nodes'):
                        go_parts.append(f"nodes {settings['nodes']}")
                    self.send_command(f"go {' '.join(go_parts)}")

                    # Wait for bestmove response and collect MultiPV alternatives
                    start_time = time.time()
                    timeout = settings['movetime'] + 3000 if settings['movetime'] else 5000
                    best_move = None
                    alternatives: Dict[int, str] = {}
                    info_pattern = re.compile(r'\bmultipv\s+(\d+)\b.*?\bpv\s+(\S+)')

                    logger.info(
                        f"Searching for {difficulty.value}: "
                        f"skill={settings['skill_level']}, depth={settings['depth']}, "
                        f"movetime={settings.get('movetime')}, nodes={settings.get('nodes')}, "
                        f"multipv={multipv}, blunder_chance={blunder_chance}"
                    )

                    while time.time() - start_time < timeout / 1000:
                        try:
                            response = self.output_queue.get(timeout=0.1)
                            info_match = info_pattern.search(response)
                            if info_match:
                                rank = int(info_match.group(1))
                                move = info_match.group(2)
                                alternatives[rank] = move
                            if response.startswith("bestmove"):
                                parts = response.split()
                                if len(parts) >= 2 and parts[1] != "(none)":
                                    best_move = parts[1]
                                else:
                                    logger.warning("No best move found")
                                    return None
                                break
                        except queue.Empty:
                            continue

                    if best_move is None:
                        logger.warning(f"Timeout waiting for best move (attempt {attempt + 1}/{max_retries})")
                        continue

                    selected_move = self._select_move_for_difficulty(
                        best_move, alternatives, blunder_chance, second_best_only
                    )
                    logger.info(f"Selected move: {selected_move} (requested difficulty: {difficulty.value})")
                    return selected_move

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

    def _select_move_for_difficulty(
        self, best_move: str, alternatives: Dict[int, str],
        blunder_chance: float, second_best_only: bool
    ) -> str:
        """Return the engine's best move, or a weaker alternative depending on difficulty."""
        if not alternatives or blunder_chance <= 0 or random.random() >= blunder_chance:
            return best_move

        # Exclude the engine's top choice
        weaker_ranks = [rank for rank, move in alternatives.items() if rank != 1 and move != best_move]
        if not weaker_ranks:
            return best_move

        if second_best_only and 2 in weaker_ranks:
            return alternatives[2]

        chosen_rank = random.choice(weaker_ranks)
        return alternatives[chosen_rank]
    
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
            from .stockfish_config import find_stockfish_executable
            self.engine_path = find_stockfish_executable()
            
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
