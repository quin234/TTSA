/**
 * Chess Sound Manager
 * Generates professional chess sound effects using Web Audio API
 * Similar to Lichess sound effects
 */

class ChessSoundManager {
    constructor() {
        this.audioContext = null;
        this.enabled = true;
        this.volume = 0.5;
        this.sounds = {};
        this.currentlyPlaying = new Set();
        this.initialized = false;
    }

    /**
     * Initialize the audio context (must be called after user interaction)
     */
    init() {
        if (this.initialized) return;
        
        try {
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
            this.initialized = true;
            this.loadSettings();
        } catch (e) {
            console.warn('Web Audio API not supported:', e);
        }
    }

    /**
     * Load sound settings from localStorage
     */
    loadSettings() {
        const settings = localStorage.getItem('chess_sound_settings');
        if (settings) {
            const parsed = JSON.parse(settings);
            this.enabled = parsed.enabled !== false;
            this.volume = parsed.volume || 0.5;
        }
    }

    /**
     * Save sound settings to localStorage
     */
    saveSettings() {
        localStorage.setItem('chess_sound_settings', JSON.stringify({
            enabled: this.enabled,
            volume: this.volume
        }));
    }

    /**
     * Enable or disable sounds
     */
    setEnabled(enabled) {
        this.enabled = enabled;
        this.saveSettings();
    }

    /**
     * Set volume (0.0 to 1.0)
     */
    setVolume(volume) {
        this.volume = Math.max(0, Math.min(1, volume));
        this.saveSettings();
    }

    /**
     * Generate a simple oscillator-based sound
     */
    playTone(frequency, duration, type = 'sine', volume = 1.0) {
        if (!this.enabled) {
            return;
        }
        
        if (!this.audioContext) {
            this.init();
            if (!this.audioContext) {
                return;
            }
        }

        // Resume audio context if suspended
        if (this.audioContext.state === 'suspended') {
            this.audioContext.resume();
        }

        const oscillator = this.audioContext.createOscillator();
        const gainNode = this.audioContext.createGain();

        oscillator.connect(gainNode);
        gainNode.connect(this.audioContext.destination);

        oscillator.type = type;
        oscillator.frequency.setValueAtTime(frequency, this.audioContext.currentTime);

        const actualVolume = volume * this.volume;
        gainNode.gain.setValueAtTime(actualVolume, this.audioContext.currentTime);
        gainNode.gain.exponentialRampToValueAtTime(0.01, this.audioContext.currentTime + duration);

        oscillator.start(this.audioContext.currentTime);
        oscillator.stop(this.audioContext.currentTime + duration);
    }

    /**
     * Play move sound (short, crisp click)
     */
    playMove() {
        if (!this.enabled) {
            return;
        }
        
        if (!this.audioContext) {
            this.init();
            if (!this.audioContext) {
                return;
            }
        }
        
        // Create a click-like sound using multiple frequencies
        const now = this.audioContext.currentTime;
        
        // Primary click
        this.playTone(800, 0.05, 'sine', 0.3);
        setTimeout(() => this.playTone(1200, 0.03, 'sine', 0.2), 10);
    }

    /**
     * Play capture sound (deeper, more resonant)
     */
    playCapture() {
        if (!this.enabled || !this.audioContext) return;
        
        const now = this.audioContext.currentTime;
        
        // Create a more complex capture sound
        this.playTone(400, 0.08, 'triangle', 0.4);
        setTimeout(() => this.playTone(600, 0.06, 'sine', 0.3), 15);
        setTimeout(() => this.playTone(200, 0.1, 'sine', 0.25), 30);
    }

    /**
     * Play check sound (alert, higher pitch)
     */
    playCheck() {
        if (!this.enabled || !this.audioContext) return;
        
        const now = this.audioContext.currentTime;
        
        // Alert-like sound
        this.playTone(880, 0.1, 'square', 0.35);
        setTimeout(() => this.playTone(1100, 0.08, 'square', 0.3), 50);
        setTimeout(() => this.playTone(880, 0.06, 'square', 0.25), 100);
    }

    /**
     * Play castle sound (longer, sweeping)
     */
    playCastle() {
        if (!this.enabled || !this.audioContext) return;
        
        const now = this.audioContext.currentTime;
        
        // Sweeping sound for castling
        this.playTone(300, 0.15, 'sine', 0.3);
        setTimeout(() => this.playTone(400, 0.12, 'sine', 0.35), 30);
        setTimeout(() => this.playTone(500, 0.1, 'sine', 0.3), 60);
        setTimeout(() => this.playTone(600, 0.08, 'sine', 0.25), 90);
    }

    /**
     * Play promotion sound (uplifting, celebratory)
     */
    playPromotion() {
        if (!this.enabled || !this.audioContext) return;
        
        const now = this.audioContext.currentTime;
        
        // Celebratory ascending tones
        this.playTone(523, 0.1, 'sine', 0.3);  // C5
        setTimeout(() => this.playTone(659, 0.1, 'sine', 0.35), 80);  // E5
        setTimeout(() => this.playTone(784, 0.12, 'sine', 0.4), 160);  // G5
        setTimeout(() => this.playTone(1047, 0.15, 'sine', 0.35), 240);  // C6
    }

    /**
     * Play game end sound (final, conclusive)
     */
    playGameEnd(won = true) {
        if (!this.enabled || !this.audioContext) return;
        
        const now = this.audioContext.currentTime;
        
        if (won) {
            // Victory sound - ascending major chord
            this.playTone(523, 0.2, 'sine', 0.35);  // C5
            setTimeout(() => this.playTone(659, 0.2, 'sine', 0.35), 100);  // E5
            setTimeout(() => this.playTone(784, 0.25, 'sine', 0.4), 200);  // G5
            setTimeout(() => this.playTone(1047, 0.3, 'sine', 0.35), 300);  // C6
        } else {
            // Loss/draw sound - descending
            this.playTone(784, 0.2, 'sine', 0.3);  // G5
            setTimeout(() => this.playTone(659, 0.2, 'sine', 0.3), 100);  // E5
            setTimeout(() => this.playTone(523, 0.25, 'sine', 0.35), 200);  // C5
            setTimeout(() => this.playTone(392, 0.3, 'sine', 0.3), 300);  // G4
        }
    }

    /**
     * Play draw sound (neutral, conclusive)
     */
    playDraw() {
        if (!this.enabled || !this.audioContext) return;
        
        const now = this.audioContext.currentTime;
        
        // Neutral concluding sound
        this.playTone(523, 0.15, 'sine', 0.3);  // C5
        setTimeout(() => this.playTone(523, 0.15, 'sine', 0.3), 150);  // C5
        setTimeout(() => this.playTone(392, 0.2, 'sine', 0.35), 300);  // G4
    }

    /**
     * Play illegal move sound (error, low pitch)
     */
    playIllegal() {
        if (!this.enabled || !this.audioContext) return;
        
        const now = this.audioContext.currentTime;
        
        // Error sound
        this.playTone(200, 0.1, 'sawtooth', 0.3);
        setTimeout(() => this.playTone(150, 0.1, 'sawtooth', 0.25), 50);
    }

    /**
     * Play sound based on move type
     */
    playMoveSound(move, gameState) {
        if (!this.enabled) {
            return;
        }
        
        // Initialize audio context on first interaction
        this.init();
        
        // Determine sound type based on move
        if (move.captured) {
            this.playCapture();
        } else if (move.flags && (move.flags.includes('k') || move.flags.includes('q'))) {
            // Castling
            this.playCastle();
        } else if (move.promotion) {
            this.playPromotion();
        } else {
            // Normal move
            this.playMove();
        }
        
        // Check for check
        if (gameState && gameState.in_check) {
            setTimeout(() => this.playCheck(), 200);
        }
    }

    /**
     * Play game end sound based on result
     */
    playEndSound(result) {
        if (!this.enabled) return;
        
        this.init();
        
        if (result === 'checkmate') {
            this.playGameEnd(true);
        } else if (result === 'stalemate' || result === 'draw') {
            this.playDraw();
        } else if (result === 'resignation') {
            this.playGameEnd(false);
        }
    }
}

// Create global instance
const chessSounds = new ChessSoundManager();

// Export for use in other files
if (typeof module !== 'undefined' && module.exports) {
    module.exports = chessSounds;
}
