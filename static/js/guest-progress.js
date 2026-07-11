// Guest Progress Tracking System
// Stores guest user progress in localStorage

const GuestProgress = {
    // Initialize guest progress
    init: function() {
        if (!this.getGuestId()) {
            this.createGuestId();
        }
        this.syncProgress();
    },
    
    // Generate a unique guest ID
    createGuestId: function() {
        const guestId = 'guest_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
        localStorage.setItem('ttsa_guest_id', guestId);
        localStorage.setItem('ttsa_guest_created', new Date().toISOString());
        return guestId;
    },
    
    // Get guest ID
    getGuestId: function() {
        return localStorage.getItem('ttsa_guest_id');
    },
    
    // Check if user is a guest
    isGuest: function() {
        return this.getGuestId() !== null;
    },
    
    // Get all guest progress data
    getProgress: function() {
        const guestId = this.getGuestId();
        if (!guestId) return null;
        
        const progress = localStorage.getItem('ttsa_guest_progress_' + guestId);
        return progress ? JSON.parse(progress) : this.getDefaultProgress();
    },
    
    // Get default progress structure
    getDefaultProgress: function() {
        return {
            guest_id: this.getGuestId(),
            created_at: localStorage.getItem('ttsa_guest_created'),
            last_updated: new Date().toISOString(),
            games_played: 0,
            games_won: 0,
            games_lost: 0,
            games_drawn: 0,
            current_rating: 800,
            coins: 100,
            experience_points: 0,
            level: 1,
            learning_streak: 0,
            last_played: null,
            completed_lessons: [],
            solved_puzzles: [],
            achievements: [],
            settings: {
                difficulty: 'beginner',
                learning_mode: false,
                sound_enabled: true,
                animations_enabled: true
            }
        };
    },
    
    // Save progress to localStorage
    saveProgress: function(progress) {
        const guestId = this.getGuestId();
        if (!guestId) return false;
        
        progress.last_updated = new Date().toISOString();
        localStorage.setItem('ttsa_guest_progress_' + guestId, JSON.stringify(progress));
        return true;
    },
    
    // Update specific progress field
    updateField: function(field, value) {
        const progress = this.getProgress();
        if (progress) {
            progress[field] = value;
            this.saveProgress(progress);
        }
    },
    
    // Record a completed game
    recordGame: function(result, difficulty, moves, time) {
        const progress = this.getProgress();
        if (!progress) return false;
        
        progress.games_played += 1;
        
        if (result === 'win') {
            progress.games_won += 1;
            progress.current_rating += 25;
            progress.coins += 10;
            progress.experience_points += 50;
        } else if (result === 'draw') {
            progress.games_drawn += 1;
            progress.current_rating += 10;
            progress.coins += 5;
            progress.experience_points += 25;
        } else if (result === 'loss') {
            progress.games_lost += 1;
            progress.current_rating -= 15;
            progress.experience_points += 10;
        }
        
        // Update level based on experience
        progress.level = Math.floor(progress.experience_points / 1000) + 1;
        
        // Update learning streak
        const today = new Date().toDateString();
        if (progress.last_played === today) {
            progress.learning_streak += 1;
        } else if (progress.last_played !== today) {
            const lastPlayed = new Date(progress.last_played);
            const todayDate = new Date();
            const diffDays = Math.floor((todayDate - lastPlayed) / (1000 * 60 * 60 * 24));
            
            if (diffDays === 1) {
                progress.learning_streak += 1;
            } else if (diffDays > 1) {
                progress.learning_streak = 1;
            }
        }
        
        progress.last_played = today;
        
        this.saveProgress(progress);
        return true;
    },
    
    // Record a completed lesson
    recordLesson: function(lessonId, points) {
        const progress = this.getProgress();
        if (!progress) return false;
        
        if (!progress.completed_lessons.includes(lessonId)) {
            progress.completed_lessons.push(lessonId);
            progress.coins += points;
            progress.experience_points += points * 2;
            progress.level = Math.floor(progress.experience_points / 1000) + 1;
            this.saveProgress(progress);
        }
        
        return true;
    },
    
    // Record a solved puzzle
    recordPuzzle: function(puzzleId, difficulty) {
        const progress = this.getProgress();
        if (!progress) return false;
        
        if (!progress.solved_puzzles.includes(puzzleId)) {
            progress.solved_puzzles.push(puzzleId);
            const coins = difficulty === 'beginner' ? 5 : 10;
            progress.coins += coins;
            progress.experience_points += coins * 2;
            progress.level = Math.floor(progress.experience_points / 1000) + 1;
            this.saveProgress(progress);
        }
        
        return true;
    },
    
    // Update settings
    updateSettings: function(settings) {
        const progress = this.getProgress();
        if (!progress) return false;
        
        progress.settings = { ...progress.settings, ...settings };
        this.saveProgress(progress);
        return true;
    },
    
    // Get guest stats for display
    getStats: function() {
        const progress = this.getProgress();
        if (!progress) return null;
        
        return {
            rating: progress.current_rating,
            coins: progress.coins,
            level: progress.level,
            experience_points: progress.experience_points,
            learning_streak: progress.learning_streak,
            games_played: progress.games_played,
            games_won: progress.games_won,
            games_lost: progress.games_lost,
            games_drawn: progress.games_drawn,
            completed_lessons: progress.completed_lessons.length,
            solved_puzzles: progress.solved_puzzles.length
        };
    },
    
    // Export guest progress for account transfer
    exportProgress: function() {
        const progress = this.getProgress();
        if (!progress) return null;
        
        return {
            guest_data: progress,
            export_timestamp: new Date().toISOString()
        };
    },
    
    // Clear guest progress (after account transfer)
    clearProgress: function() {
        const guestId = this.getGuestId();
        if (guestId) {
            localStorage.removeItem('ttsa_guest_progress_' + guestId);
            localStorage.removeItem('ttsa_guest_id');
            localStorage.removeItem('ttsa_guest_created');
        }
    },
    
    // Sync progress with server (for authenticated users)
    syncProgress: function() {
        // This would be used to sync guest progress when user logs in
        const guestId = this.getGuestId();
        if (guestId && !this.isGuest()) {
            // User is now authenticated, prepare for transfer
            const progress = this.exportProgress();
            if (progress) {
                localStorage.setItem('ttsa_pending_transfer', JSON.stringify(progress));
            }
        }
    },
    
    // Get display data for templates
    getDisplayData: function() {
        const stats = this.getStats();
        if (!stats) return null;
        
        return {
            is_guest: true,
            rating: stats.rating,
            coins: stats.coins,
            level: stats.level,
            learning_streak: stats.learning_streak,
            completed_lessons: stats.completed_lessons,
            solved_puzzles: stats.solved_puzzles
        };
    }
};

// Initialize guest progress on page load
document.addEventListener('DOMContentLoaded', function() {
    GuestProgress.init();
    
    // Make available globally
    window.GuestProgress = GuestProgress;
    
    // Sync guest stats to UI if guest
    if (GuestProgress.isGuest()) {
        updateGuestUI();
    }
});

// Update UI with guest progress
function updateGuestUI() {
    const stats = GuestProgress.getStats();
    if (!stats) return;
    
    // Update rating display
    const ratingElements = document.querySelectorAll('[data-guest-rating]');
    ratingElements.forEach(el => {
        el.textContent = stats.rating;
    });
    
    // Update coins display
    const coinsElements = document.querySelectorAll('[data-guest-coins]');
    coinsElements.forEach(el => {
        el.textContent = stats.coins;
    });
    
    // Update level display
    const levelElements = document.querySelectorAll('[data-guest-level]');
    levelElements.forEach(el => {
        el.textContent = stats.level;
    });
    
    // Update streak display
    const streakElements = document.querySelectorAll('[data-guest-streak]');
    streakElements.forEach(el => {
        el.textContent = stats.learning_streak;
    });
}

// Handle guest progress transfer on signup
function handleGuestTransfer() {
    const pendingTransfer = localStorage.getItem('ttsa_pending_transfer');
    if (pendingTransfer) {
        const transferData = JSON.parse(pendingTransfer);
        
        // Send to server during signup
        const transferInput = document.getElementById('guest_transfer_data');
        if (transferInput) {
            transferInput.value = JSON.stringify(transferData.guest_data);
        }
        
        // Clear pending transfer
        localStorage.removeItem('ttsa_pending_transfer');
    }
}

// Call transfer handler on signup page
if (window.location.pathname.includes('/signup')) {
    handleGuestTransfer();
}
