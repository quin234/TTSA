/**
 * Realistic Chess Sound Manager
 * Generates professional wooden chess sound effects using Web Audio API
 * Similar to Lichess realistic wooden piece sounds
 */

class ChessSoundManager {
    constructor() {
        this.audioContext = null;
        this.enabled = true;
        this.volume = 0.6;
        this.sounds = {};
        this.currentlyPlaying = new Set();
        this.initialized = false;
        this.moveSoundBuffer = null;
        this.captureSoundBuffer = null;
        this.checkSoundBuffer = null;
        this.castleSoundBuffer = null;
        this.promotionSoundBuffer = null;
        this.gameEndSoundBuffer = null;
        this.drawSoundBuffer = null;
        this.lastSoundTime = null;
        this.lastSoundId = null;
        this.audioBuffers = new Map(); // Cache for loaded audio files
    }

    /**
     * Initialize the audio context (must be called after user interaction)
     */
    async init() {
        if (this.initialized) return;
        
        try {
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
            this.initialized = true;
            this.loadSettings();
            await this.loadSoundFiles();
        } catch (e) {
            console.warn('Web Audio API not supported:', e);
        }
    }

    /**
     * Load real audio files for chess sounds
     */
    async loadSoundFiles() {
        if (!this.audioContext) return;
        
        try {
            // Load the Black move sound for regular moves
            const moveResponse = await fetch('/static/sounds/Black move sound.mp3');
            const moveArrayBuffer = await moveResponse.arrayBuffer();
            const moveAudioBuffer = await this.audioContext.decodeAudioData(moveArrayBuffer);
            
            // Truncate the move sound for even faster playback
            const truncatedMoveBuffer = this.truncateAudioBuffer(moveAudioBuffer, 0.15, 0.6);
            
            // Store the truncated move sound buffer
            this.audioBuffers.set('move_sound', truncatedMoveBuffer);
            this.moveSoundBuffer = truncatedMoveBuffer;
            
            // Load the piece capture sound for captures
            try {
                const captureResponse = await fetch('/static/sounds/piece capture.mp3');
                const captureArrayBuffer = await captureResponse.arrayBuffer();
                const captureAudioBuffer = await this.audioContext.decodeAudioData(captureArrayBuffer);
                
                // Truncate the capture sound for even faster playback
                const truncatedCaptureBuffer = this.truncateAudioBuffer(captureAudioBuffer, 0.2, 0.5);
                
                // Store the truncated capture sound buffer
                this.audioBuffers.set('capture_sound', truncatedCaptureBuffer);
                this.captureSoundBuffer = truncatedCaptureBuffer;
                
                console.log('Capture sound loaded and truncated successfully');
            } catch (captureError) {
                console.warn('Failed to load capture sound, using move sound for captures:', captureError);
                // Fallback: use truncated move sound for captures
                this.captureSoundBuffer = truncatedMoveBuffer;
            }
            
            // Use the truncated Black move sound for other effects with processing
            this.checkSoundBuffer = truncatedMoveBuffer;
            this.castleSoundBuffer = truncatedMoveBuffer;
            this.promotionSoundBuffer = truncatedMoveBuffer;
            this.gameEndSoundBuffer = truncatedMoveBuffer;
            this.drawSoundBuffer = truncatedMoveBuffer;
            
            console.log('Chess sounds loaded and truncated successfully');
            
        } catch (error) {
            console.warn('Failed to load Black move sound:', error);
            // Fallback to synthesized sounds if loading fails
            this.generateFallbackSounds();
        }
    }

    /**
     * Truncate audio buffer by removing left and right portions
     */
    truncateAudioBuffer(originalBuffer, startRatio = 0.1, endRatio = 0.8) {
        const sampleRate = originalBuffer.sampleRate;
        const channels = originalBuffer.numberOfChannels;
        const originalLength = originalBuffer.length;
        
        // Calculate start and end sample positions
        const startPos = Math.floor(originalLength * startRatio);
        const endPos = Math.floor(originalLength * endRatio);
        const newLength = endPos - startPos;
        
        // Create new truncated buffer
        const truncatedBuffer = this.audioContext.createBuffer(channels, newLength, sampleRate);
        
        // Copy audio data from original to truncated buffer
        for (let channel = 0; channel < channels; channel++) {
            const originalData = originalBuffer.getChannelData(channel);
            const truncatedData = truncatedBuffer.getChannelData(channel);
            
            for (let i = 0; i < newLength; i++) {
                truncatedData[i] = originalData[startPos + i];
            }
        }
        
        return truncatedBuffer;
    }

    /**
     * Generate fallback synthesized sounds if audio file loading fails
     */
    generateFallbackSounds() {
        console.log('Using fallback synthesized sounds');
        this.moveSoundBuffer = this.createWoodenMoveSound();
        this.captureSoundBuffer = this.createWoodenCaptureSound();
        this.checkSoundBuffer = this.createWoodenCheckSound();
        this.castleSoundBuffer = this.createWoodenCastleSound();
        this.promotionSoundBuffer = this.createWoodenPromotionSound();
        this.gameEndSoundBuffer = this.createWoodenGameEndSound(true);
        this.drawSoundBuffer = this.createWoodenGameEndSound(false);
    }

    /**
     * Create a wooden piece move sound with natural resonance
     */
    createWoodenMoveSound() {
        const sampleRate = this.audioContext.sampleRate;
        const duration = 0.15;
        const buffer = this.audioContext.createBuffer(2, Math.floor(sampleRate * duration), sampleRate);
        
        for (let channel = 0; channel < 2; channel++) {
            const channelData = buffer.getChannelData(channel);
            
            for (let i = 0; i < channelData.length; i++) {
                const t = i / sampleRate;
                
                // Wooden click with harmonics and natural decay
                let sample = 0;
                
                // Primary wooden tap frequency (around 800Hz)
                sample += Math.sin(2 * Math.PI * 800 * t) * Math.exp(-t * 25) * 0.4;
                
                // Wood resonance harmonics
                sample += Math.sin(2 * Math.PI * 1200 * t) * Math.exp(-t * 30) * 0.25;
                sample += Math.sin(2 * Math.PI * 1600 * t) * Math.exp(-t * 35) * 0.15;
                
                // Board resonance (lower frequencies)
                sample += Math.sin(2 * Math.PI * 200 * t) * Math.exp(-t * 15) * 0.3;
                sample += Math.sin(2 * Math.PI * 400 * t) * Math.exp(-t * 20) * 0.2;
                
                // Add subtle noise for wood texture
                const noise = (Math.random() - 0.5) * 0.02 * Math.exp(-t * 50);
                sample += noise;
                
                // Apply envelope
                const envelope = Math.exp(-t * 8);
                channelData[i] = sample * envelope;
            }
        }
        
        return buffer;
    }

    /**
     * Create a wooden piece capture sound with deeper resonance
     */
    createWoodenCaptureSound() {
        const sampleRate = this.audioContext.sampleRate;
        const duration = 0.25;
        const buffer = this.audioContext.createBuffer(2, Math.floor(sampleRate * duration), sampleRate);
        
        for (let channel = 0; channel < 2; channel++) {
            const channelData = buffer.getChannelData(channel);
            
            for (let i = 0; i < channelData.length; i++) {
                const t = i / sampleRate;
                
                // Capture sound - deeper, more resonant
                let sample = 0;
                
                // Primary impact (lower frequency for capture)
                sample += Math.sin(2 * Math.PI * 400 * t) * Math.exp(-t * 20) * 0.5;
                
                // Wood harmonics for capture
                sample += Math.sin(2 * Math.PI * 600 * t) * Math.exp(-t * 25) * 0.3;
                sample += Math.sin(2 * Math.PI * 800 * t) * Math.exp(-t * 30) * 0.2;
                
                // Deep board resonance
                sample += Math.sin(2 * Math.PI * 150 * t) * Math.exp(-t * 12) * 0.4;
                sample += Math.sin(2 * Math.PI * 300 * t) * Math.exp(-t * 18) * 0.25;
                
                // Secondary impact for capture feel
                if (t > 0.05) {
                    sample += Math.sin(2 * Math.PI * 500 * (t - 0.05)) * Math.exp(-(t - 0.05) * 15) * 0.3;
                }
                
                // Wood texture noise
                const noise = (Math.random() - 0.5) * 0.03 * Math.exp(-t * 40);
                sample += noise;
                
                // Envelope for capture
                const envelope = Math.exp(-t * 6);
                channelData[i] = sample * envelope;
            }
        }
        
        return buffer;
    }

    /**
     * Create a check alert sound with wooden character
     */
    createWoodenCheckSound() {
        const sampleRate = this.audioContext.sampleRate;
        const duration = 0.3;
        const buffer = this.audioContext.createBuffer(2, Math.floor(sampleRate * duration), sampleRate);
        
        for (let channel = 0; channel < 2; channel++) {
            const channelData = buffer.getChannelData(channel);
            
            for (let i = 0; i < channelData.length; i++) {
                const t = i / sampleRate;
                
                // Check alert - three distinct wooden taps
                let sample = 0;
                
                // First tap
                if (t < 0.08) {
                    sample += Math.sin(2 * Math.PI * 1000 * t) * Math.exp(-t * 30) * 0.4;
                    sample += Math.sin(2 * Math.PI * 1500 * t) * Math.exp(-t * 35) * 0.2;
                }
                
                // Second tap
                if (t > 0.08 && t < 0.16) {
                    const tapTime = t - 0.08;
                    sample += Math.sin(2 * Math.PI * 1000 * tapTime) * Math.exp(-tapTime * 30) * 0.4;
                    sample += Math.sin(2 * Math.PI * 1500 * tapTime) * Math.exp(-tapTime * 35) * 0.2;
                }
                
                // Third tap
                if (t > 0.16) {
                    const tapTime = t - 0.16;
                    sample += Math.sin(2 * Math.PI * 1000 * tapTime) * Math.exp(-tapTime * 30) * 0.4;
                    sample += Math.sin(2 * Math.PI * 1500 * tapTime) * Math.exp(-tapTime * 35) * 0.2;
                }
                
                // Wood resonance
                sample += Math.sin(2 * Math.PI * 200 * t) * Math.exp(-t * 10) * 0.2;
                
                // Wood texture
                const noise = (Math.random() - 0.5) * 0.02 * Math.exp(-t * 50);
                sample += noise;
                
                channelData[i] = sample;
            }
        }
        
        return buffer;
    }

    /**
     * Create a castling sound with sweeping wooden movement
     */
    createWoodenCastleSound() {
        const sampleRate = this.audioContext.sampleRate;
        const duration = 0.4;
        const buffer = this.audioContext.createBuffer(2, Math.floor(sampleRate * duration), sampleRate);
        
        for (let channel = 0; channel < 2; channel++) {
            const channelData = buffer.getChannelData(channel);
            
            for (let i = 0; i < channelData.length; i++) {
                const t = i / sampleRate;
                
                // Castling - sweeping wooden sounds
                let sample = 0;
                
                // King movement (lower pitch)
                const kingFreq = 300 + t * 200; // Sweep up
                sample += Math.sin(2 * Math.PI * kingFreq * t) * Math.exp(-t * 8) * 0.3;
                
                // Rook movement (higher pitch)
                if (t > 0.1) {
                    const rookTime = t - 0.1;
                    const rookFreq = 600 + rookTime * 300;
                    sample += Math.sin(2 * Math.PI * rookFreq * rookTime) * Math.exp(-rookTime * 10) * 0.25;
                }
                
                // Wood harmonics
                sample += Math.sin(2 * Math.PI * 800 * t) * Math.exp(-t * 20) * 0.15;
                sample += Math.sin(2 * Math.PI * 1200 * t) * Math.exp(-t * 25) * 0.1;
                
                // Board resonance
                sample += Math.sin(2 * Math.PI * 150 * t) * Math.exp(-t * 8) * 0.2;
                
                // Wood texture
                const noise = (Math.random() - 0.5) * 0.02 * Math.exp(-t * 40);
                sample += noise;
                
                channelData[i] = sample;
            }
        }
        
        return buffer;
    }

    /**
     * Create a promotion sound with uplifting wooden tones
     */
    createWoodenPromotionSound() {
        const sampleRate = this.audioContext.sampleRate;
        const duration = 0.5;
        const buffer = this.audioContext.createBuffer(2, Math.floor(sampleRate * duration), sampleRate);
        
        for (let channel = 0; channel < 2; channel++) {
            const channelData = buffer.getChannelData(channel);
            
            for (let i = 0; i < channelData.length; i++) {
                const t = i / sampleRate;
                
                // Promotion - ascending wooden tones
                let sample = 0;
                
                // Ascending notes (C-E-G-C)
                const notes = [523, 659, 784, 1047]; // C5, E5, G5, C6
                const noteTimes = [0, 0.1, 0.2, 0.3];
                
                for (let j = 0; j < notes.length; j++) {
                    if (t >= noteTimes[j]) {
                        const noteTime = t - noteTimes[j];
                        sample += Math.sin(2 * Math.PI * notes[j] * noteTime) * 
                                 Math.exp(-noteTime * 15) * 0.3 * (1 - j * 0.05);
                        
                        // Wood harmonics for each note
                        sample += Math.sin(2 * Math.PI * (notes[j] * 1.5) * noteTime) * 
                                 Math.exp(-noteTime * 20) * 0.15 * (1 - j * 0.05);
                    }
                }
                
                // Wood resonance throughout
                sample += Math.sin(2 * Math.PI * 200 * t) * Math.exp(-t * 10) * 0.15;
                
                // Celebratory wood texture
                const noise = (Math.random() - 0.5) * 0.025 * Math.exp(-t * 30);
                sample += noise;
                
                channelData[i] = sample;
            }
        }
        
        return buffer;
    }

    /**
     * Create a game end sound (victory or draw)
     */
    createWoodenGameEndSound(victory = true) {
        const sampleRate = this.audioContext.sampleRate;
        const duration = 0.6;
        const buffer = this.audioContext.createBuffer(2, Math.floor(sampleRate * duration), sampleRate);
        
        for (let channel = 0; channel < 2; channel++) {
            const channelData = buffer.getChannelData(channel);
            
            for (let i = 0; i < channelData.length; i++) {
                const t = i / sampleRate;
                
                // Game end sound
                let sample = 0;
                
                if (victory) {
                    // Victory - ascending major chord
                    const notes = [523, 659, 784, 1047]; // C5, E5, G5, C6
                    const noteTimes = [0, 0.12, 0.24, 0.36];
                    
                    for (let j = 0; j < notes.length; j++) {
                        if (t >= noteTimes[j]) {
                            const noteTime = t - noteTimes[j];
                            sample += Math.sin(2 * Math.PI * notes[j] * noteTime) * 
                                     Math.exp(-noteTime * 12) * 0.35;
                            
                            // Wood harmonics
                            sample += Math.sin(2 * Math.PI * (notes[j] * 1.5) * noteTime) * 
                                     Math.exp(-noteTime * 18) * 0.2;
                        }
                    }
                } else {
                    // Draw/loss - descending or neutral
                    const notes = [784, 659, 523, 392]; // G5, E5, C5, G4
                    const noteTimes = [0, 0.12, 0.24, 0.36];
                    
                    for (let j = 0; j < notes.length; j++) {
                        if (t >= noteTimes[j]) {
                            const noteTime = t - noteTimes[j];
                            sample += Math.sin(2 * Math.PI * notes[j] * noteTime) * 
                                     Math.exp(-noteTime * 12) * 0.3;
                            
                            // Wood harmonics
                            sample += Math.sin(2 * Math.PI * (notes[j] * 1.5) * noteTime) * 
                                     Math.exp(-noteTime * 18) * 0.15;
                        }
                    }
                }
                
                // Deep board resonance for finality
                sample += Math.sin(2 * Math.PI * 100 * t) * Math.exp(-t * 8) * 0.2;
                
                // Wood texture
                const noise = (Math.random() - 0.5) * 0.02 * Math.exp(-t * 35);
                sample += noise;
                
                channelData[i] = sample;
            }
        }
        
        return buffer;
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
     * Play a sound buffer with deduplication
     */
    playSoundBuffer(buffer) {
        if (!this.enabled || !buffer || !this.audioContext) return;
        
        // Resume audio context if suspended
        if (this.audioContext.state === 'suspended') {
            this.audioContext.resume();
        }
        
        // Prevent duplicate sounds within 50ms
        const now = this.audioContext.currentTime;
        const soundId = buffer.toString();
        
        if (this.lastSoundTime && this.lastSoundId === soundId && (now - this.lastSoundTime) < 0.05) {
            return; // Skip duplicate sound
        }
        
        this.lastSoundTime = now;
        this.lastSoundId = soundId;
        
        const source = this.audioContext.createBufferSource();
        const gainNode = this.audioContext.createGain();
        
        source.buffer = buffer;
        source.connect(gainNode);
        gainNode.connect(this.audioContext.destination);
        
        gainNode.gain.setValueAtTime(this.volume, this.audioContext.currentTime);
        
        source.start(this.audioContext.currentTime);
        
        // Clean up after sound finishes
        source.onended = () => {
            if (this.lastSoundId === soundId && Math.abs(this.audioContext.currentTime - this.lastSoundTime) > 0.1) {
                this.lastSoundId = null;
            }
        };
    }

    /**
     * Play move sound (realistic wooden piece movement)
     */
    async playMove() {
        if (!this.enabled) return;
        
        await this.init();
        if (this.moveSoundBuffer) {
            this.playProcessedSound(this.moveSoundBuffer, 'move');
        }
    }

    /**
     * Play capture sound (realistic wooden capture)
     */
    async playCapture() {
        if (!this.enabled) return;
        
        await this.init();
        if (this.captureSoundBuffer) {
            this.playProcessedSound(this.captureSoundBuffer, 'capture');
        }
    }

    /**
     * Play check sound (wooden alert taps)
     */
    async playCheck() {
        if (!this.enabled) return;
        
        await this.init();
        if (this.checkSoundBuffer) {
            this.playProcessedSound(this.checkSoundBuffer, 'check');
        }
    }

    /**
     * Play castle sound (sweeping wooden movement)
     */
    async playCastle() {
        if (!this.enabled) return;
        
        await this.init();
        if (this.castleSoundBuffer) {
            this.playProcessedSound(this.castleSoundBuffer, 'castle');
        }
    }

    /**
     * Play promotion sound (uplifting wooden tones)
     */
    async playPromotion() {
        if (!this.enabled) return;
        
        await this.init();
        if (this.promotionSoundBuffer) {
            this.playProcessedSound(this.promotionSoundBuffer, 'promotion');
        }
    }

    /**
     * Play game end sound (wooden victory/draw)
     */
    async playGameEnd(won = true) {
        if (!this.enabled) return;
        
        await this.init();
        const soundType = won ? 'gameEnd' : 'draw';
        const buffer = won ? this.gameEndSoundBuffer : this.drawSoundBuffer;
        if (buffer) {
            this.playProcessedSound(buffer, soundType);
        }
    }

    /**
     * Play draw sound (neutral wooden conclusion)
     */
    async playDraw() {
        if (!this.enabled) return;
        
        await this.init();
        if (this.drawSoundBuffer) {
            this.playProcessedSound(this.drawSoundBuffer, 'draw');
        }
    }

    /**
     * Play illegal move sound (error wood tap)
     */
    async playIllegal() {
        if (!this.enabled) return;
        
        await this.init();
        if (this.moveSoundBuffer) {
            this.playProcessedSound(this.moveSoundBuffer, 'illegal');
        }
    }

    /**
     * Play processed sound with effects based on sound type
     */
    playProcessedSound(buffer, soundType) {
        if (!this.enabled || !buffer || !this.audioContext) return;
        
        // Resume audio context if suspended
        if (this.audioContext.state === 'suspended') {
            this.audioContext.resume();
        }
        
        // Prevent duplicate sounds within 50ms
        const now = this.audioContext.currentTime;
        const soundId = soundType;
        
        if (this.lastSoundTime && this.lastSoundId === soundId && (now - this.lastSoundTime) < 0.05) {
            return; // Skip duplicate sound
        }
        
        this.lastSoundTime = now;
        this.lastSoundId = soundId;
        
        const source = this.audioContext.createBufferSource();
        const gainNode = this.audioContext.createGain();
        
        source.buffer = buffer;
        source.connect(gainNode);
        gainNode.connect(this.audioContext.destination);
        
        // Apply processing based on sound type
        let volume = this.volume;
        let playbackRate = 1.0;
        
        switch(soundType) {
            case 'capture':
                volume *= 1.2; // Slightly louder for captures
                playbackRate = 0.9; // Slightly deeper
                break;
            case 'check':
                volume *= 1.3; // Louder for check
                playbackRate = 1.1; // Slightly higher pitch
                break;
            case 'castle':
                volume *= 1.1;
                playbackRate = 0.95; // Slightly deeper for castling
                break;
            case 'promotion':
                volume *= 1.4; // Louder for promotion
                playbackRate = 1.2; // Higher pitch for promotion
                break;
            case 'gameEnd':
                volume *= 1.5; // Louder for game end
                playbackRate = 1.3; // Higher pitch for victory
                break;
            case 'draw':
                volume *= 1.2;
                playbackRate = 0.85; // Lower pitch for draw
                break;
            case 'illegal':
                volume *= 0.6; // Quieter for illegal moves
                playbackRate = 0.7; // Lower pitch for error
                break;
            default: // move
                volume *= 1.0;
                playbackRate = 1.0;
        }
        
        source.playbackRate.setValueAtTime(playbackRate, this.audioContext.currentTime);
        gainNode.gain.setValueAtTime(volume, this.audioContext.currentTime);
        
        source.start(this.audioContext.currentTime);
        
        // Clean up after sound finishes
        source.onended = () => {
            if (this.lastSoundId === soundId && Math.abs(this.audioContext.currentTime - this.lastSoundTime) > 0.1) {
                this.lastSoundId = null;
            }
        };
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
        
        // Determine sound type based on move - check takes priority
        if (gameState && gameState.in_check) {
            // Play check sound instead of move sound when in check
            this.playCheck();
        } else if (move.captured) {
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
