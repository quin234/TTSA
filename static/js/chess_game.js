// This file contains helper functions only
// Main game logic and variables are in HTML template

// Variables that are safe to declare in this file
let gameTimer = null;
let secondsElapsed = 0;
let learningMode = false;

// Chess piece Unicode symbols are declared in HTML template

// Daily tips
const dailyTips = [
    "Control the center of the board! Pieces in the center have more mobility and can influence more squares.",
    "Develop your knights before bishops. Knights are generally easier to develop early in the game.",
    "Castle early! It's important to keep your king safe and connect your rooks.",
    "Don't move the same piece twice in the opening unless necessary. Develop all your pieces first.",
    "Pawn structure is crucial. Avoid creating weak pawns that can be easily attacked.",
    "Every move should have a purpose. Ask yourself 'What does this move accomplish?'",
    "Control open files with your rooks. Rooks are powerful on open and semi-open files.",
    "The bishop pair is powerful. Two bishops working together can control many squares.",
    "When ahead in material, exchange pieces to simplify the position.",
    "In the endgame, king activity becomes crucial. Don't be afraid to use your king as an active piece."
];

// These functions are handled in HTML template to avoid conflicts
// document.addEventListener('DOMContentLoaded', function() { ... });
// function initializeGame() { ... }

// Helper functions that don't depend on global game state
function renderBoard() {
    // This function is now handled in HTML template
    console.log('renderBoard called - this should be handled in HTML template');
}

// Functions that reference global game variables are now handled in HTML template
// to avoid conflicts and scoping issues

// All game logic functions are now handled in HTML template
// This file only contains utility functions that don't depend on global game state
