// Chess Game Logic
let game;
let board;
let selectedSquare = null;
let moveHistory = [];
let gameTimer = null;
let secondsElapsed = 0;
let learningMode = false;
let currentDifficulty = '{{ difficulty }}';

// Chess piece Unicode symbols
const pieces = {
    'wK': '♔', 'wQ': '♕', 'wR': '♖', 'wB': '♗', 'wN': '♘', 'wP': '♙',
    'bK': '♚', 'bQ': '♛', 'bR': '♜', 'bB': '♝', 'bN': '♞', 'bP': '♟'
};

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

// Initialize the game
document.addEventListener('DOMContentLoaded', function() {
    initializeGame();
    setupEventListeners();
    startTimer();
    updateDailyTip();
});

function initializeGame() {
    game = new Chess();
    board = document.getElementById('chessBoard');
    renderBoard();
    updateTurnIndicator();
    updateMoveCount();
}

function renderBoard() {
    board.innerHTML = '';
    const boardArray = game.board();
    
    for (let row = 0; row < 8; row++) {
        for (let col = 0; col < 8; col++) {
            const square = document.createElement('div');
            square.className = 'chess-square';
            square.className += (row + col) % 2 === 0 ? ' light' : ' dark';
            square.dataset.row = row;
            square.dataset.col = col;
            square.dataset.square = String.fromCharCode(97 + col) + (8 - row);
            
            const piece = boardArray[row][col];
            if (piece) {
                const pieceSymbol = pieces[piece.color + piece.type.toUpperCase()];
                square.textContent = pieceSymbol;
                square.dataset.piece = piece.color + piece.type;
            }
            
            square.addEventListener('click', handleSquareClick);
            board.appendChild(square);
        }
    }
}

function handleSquareClick(event) {
    const square = event.target;
    const squareName = square.dataset.square;
    
    if (selectedSquare) {
        // Try to make a move
        const move = game.move({
            from: selectedSquare,
            to: squareName,
            promotion: 'q' // Always promote to queen for simplicity
        });
        
        if (move) {
            // Move was successful
            moveHistory.push(move);
            renderBoard();
            updateTurnIndicator();
            updateMoveCount();
            updateMoveHistory();
            updateProgress();
            
            // Check for game over
            if (game.game_over()) {
                endGame();
            } else {
                // AI move
                setTimeout(makeAIMove, 500);
            }
            
            selectedSquare = null;
            clearHighlights();
        } else {
            // Invalid move, try selecting new square
            clearHighlights();
            selectSquare(square);
        }
    } else {
        // Select a square
        selectSquare(square);
    }
}

function selectSquare(square) {
    const piece = square.dataset.piece;
    if (!piece) return;
    
    const pieceColor = piece[0];
    const currentTurn = game.turn();
    
    if ((currentTurn === 'w' && pieceColor === 'w') || 
        (currentTurn === 'b' && pieceColor === 'b')) {
        selectedSquare = square.dataset.square;
        square.classList.add('selected');
        highlightValidMoves(square.dataset.square);
        
        if (learningMode) {
            showPieceInfo(piece);
        }
    }
}

function highlightValidMoves(square) {
    const moves = game.moves({ square: square, verbose: true });
    
    moves.forEach(move => {
        const targetSquare = document.querySelector(`[data-square="${move.to}"]`);
        if (targetSquare) {
            if (move.captured) {
                targetSquare.classList.add('capture-move');
            } else {
                targetSquare.classList.add('valid-move');
            }
        }
    });
}

function clearHighlights() {
    document.querySelectorAll('.chess-square').forEach(square => {
        square.classList.remove('selected', 'valid-move', 'capture-move', 'hint-square');
    });
}

function makeAIMove() {
    const moves = game.moves();
    if (moves.length === 0) return;
    
    // Simple AI based on difficulty
    let selectedMove;
    
    switch(currentDifficulty) {
        case 'beginner':
            // Random move with preference for captures
            const captureMoves = moves.filter(move => move.includes('x'));
            selectedMove = captureMoves.length > 0 && Math.random() < 0.7 ? 
                captureMoves[Math.floor(Math.random() * captureMoves.length)] :
                moves[Math.floor(Math.random() * moves.length)];
            break;
            
        case 'easy':
            // Prefer captures and checks
            const goodMoves = moves.filter(move => {
                return move.includes('x') || move.includes('+');
            });
            selectedMove = goodMoves.length > 0 ? 
                goodMoves[Math.floor(Math.random() * goodMoves.length)] :
                moves[Math.floor(Math.random() * moves.length)];
            break;
            
        case 'intermediate':
            // Simple evaluation
            selectedMove = getBestMoveIntermediate(moves);
            break;
            
        case 'advanced':
        case 'expert':
        case 'master':
            // Better evaluation (simplified)
            selectedMove = getBestMoveAdvanced(moves);
            break;
            
        default:
            selectedMove = moves[Math.floor(Math.random() * moves.length)];
    }
    
    const move = game.move(selectedMove);
    if (move) {
        moveHistory.push(move);
        renderBoard();
        updateTurnIndicator();
        updateMoveCount();
        updateMoveHistory();
        updateProgress();
        
        if (game.game_over()) {
            endGame();
        }
    }
}

function getBestMoveIntermediate(moves) {
    // Simple material-based evaluation
    let bestMove = moves[0];
    let bestScore = -Infinity;
    
    moves.forEach(move => {
        const gameCopy = new Chess(game.fen());
        gameCopy.move(move);
        const score = evaluatePosition(gameCopy);
        if (score > bestScore) {
            bestScore = score;
            bestMove = move;
        }
    });
    
    return bestMove;
}

function getBestMoveAdvanced(moves) {
    // More sophisticated evaluation
    let bestMove = moves[0];
    let bestScore = -Infinity;
    
    moves.forEach(move => {
        const gameCopy = new Chess(game.fen());
        gameCopy.move(move);
        const score = evaluatePositionAdvanced(gameCopy);
        if (score > bestScore) {
            bestScore = score;
            bestMove = move;
        }
    });
    
    return bestMove;
}

function evaluatePosition(game) {
    const pieceValues = {
        'p': 1, 'n': 3, 'b': 3, 'r': 5, 'q': 9, 'k': 0
    };
    
    let score = 0;
    const board = game.board();
    
    for (let row = 0; row < 8; row++) {
        for (let col = 0; col < 8; col++) {
            const piece = board[row][col];
            if (piece) {
                const value = pieceValues[piece.type];
                score += piece.color === 'w' ? value : -value;
            }
        }
    }
    
    return game.turn() === 'b' ? score : -score;
}

function evaluatePositionAdvanced(game) {
    // More advanced evaluation considering position factors
    let score = evaluatePosition(game);
    
    // Add positional factors
    const board = game.board();
    
    // Center control
    const centerSquares = [[3,3], [3,4], [4,3], [4,4]];
    centerSquares.forEach(([row, col]) => {
        const piece = board[row][col];
        if (piece) {
            score += piece.color === 'w' ? 0.1 : -0.1;
        }
    });
    
    // King safety (simplified)
    // Add more sophisticated evaluation here
    
    return score;
}

function updateTurnIndicator() {
    const indicator = document.getElementById('turnIndicator');
    const isWhiteTurn = game.turn() === 'w';
    
    indicator.innerHTML = `
        <div class="w-3 h-3 bg-${isWhiteTurn ? 'white' : 'gray-800'} rounded-full border-2 border-purple-500"></div>
        <span class="font-semibold text-purple-700">${isWhiteTurn ? 'White' : 'Black'}'s Turn</span>
    `;
}

function updateMoveCount() {
    document.getElementById('moveCount').textContent = game.history().length;
}

function updateMoveHistory() {
    const historyDiv = document.getElementById('moveHistory');
    const moves = game.history();
    
    if (moves.length === 0) {
        historyDiv.innerHTML = '<div class="text-gray-400 text-center">No moves yet</div>';
        return;
    }
    
    let html = '';
    for (let i = 0; i < moves.length; i += 2) {
        const moveNum = Math.floor(i / 2) + 1;
        const whiteMove = moves[i];
        const blackMove = moves[i + 1];
        
        html += `
            <div class="flex justify-between py-1 px-2 rounded hover:bg-gray-50">
                <span class="font-semibold">${moveNum}.</span>
                <span>${whiteMove}</span>
                ${blackMove ? `<span>${blackMove}</span>` : '<span></span>'}
            </div>
        `;
    }
    
    historyDiv.innerHTML = html;
    historyDiv.scrollTop = historyDiv.scrollHeight;
}

function updateProgress() {
    const moves = game.history().length;
    const maxMoves = 40; // Average game length
    const progress = Math.min((moves / maxMoves) * 100, 100);
    
    document.getElementById('progressBar').style.width = progress + '%';
}

function startTimer() {
    gameTimer = setInterval(() => {
        secondsElapsed++;
        const minutes = Math.floor(secondsElapsed / 60);
        const seconds = secondsElapsed % 60;
        document.getElementById('gameTimer').textContent = 
            `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
    }, 1000);
}

function stopTimer() {
    if (gameTimer) {
        clearInterval(gameTimer);
        gameTimer = null;
    }
}

function setupEventListeners() {
    // Difficulty selector
    document.getElementById('difficultySelect').addEventListener('change', function(e) {
        currentDifficulty = e.target.value;
        document.getElementById('difficultyDescription').textContent = 
            `{{ difficulty_levels[currentDifficulty].description }}`;
    });
    
    // Learning mode toggle
    document.getElementById('learningModeToggle').addEventListener('change', function(e) {
        learningMode = e.target.checked;
        const assistant = document.getElementById('learningAssistant');
        if (learningMode) {
            assistant.classList.remove('hidden');
            board.classList.add('learning-mode');
            updateLearningAssistant();
        } else {
            assistant.classList.add('hidden');
            board.classList.remove('learning-mode');
        }
    });
}

function startNewGame() {
    if (gameTimer) stopTimer();
    
    game = new Chess();
    moveHistory = [];
    secondsElapsed = 0;
    selectedSquare = null;
    
    renderBoard();
    updateTurnIndicator();
    updateMoveCount();
    updateMoveHistory();
    updateProgress();
    startTimer();
    
    closeGameOverModal();
}

function undoMove() {
    if (game.history().length < 2) return;
    
    game.undo();
    game.undo();
    moveHistory = moveHistory.slice(0, -2);
    
    renderBoard();
    updateTurnIndicator();
    updateMoveCount();
    updateMoveHistory();
    updateProgress();
}

function getHint() {
    if (game.turn() !== 'w') return;
    
    const moves = game.moves();
    if (moves.length === 0) return;
    
    // Get a good move
    const hintMove = getBestMoveIntermediate(moves);
    const fromSquare = hintMove.substring(0, 2);
    const toSquare = hintMove.substring(2, 4);
    
    // Highlight the hint
    clearHighlights();
    const fromEl = document.querySelector(`[data-square="${fromSquare}"]`);
    const toEl = document.querySelector(`[data-square="${toSquare}"]`);
    
    if (fromEl) fromEl.classList.add('hint-square');
    if (toEl) toEl.classList.add('hint-square');
    
    // Show hint message
    showNotification('💡 Hint: Try moving ' + fromSquare + ' to ' + toSquare, 'info');
}

function analyzePosition() {
    const evaluation = evaluatePosition(game);
    let message;
    
    if (evaluation > 2) {
        message = '🎯 You have a strong advantage!';
    } else if (evaluation > 0.5) {
        message = '👍 You have a slight advantage.';
    } else if (evaluation > -0.5) {
        message = '⚖️ The position is balanced.';
    } else if (evaluation > -2) {
        message = '⚠️ Your opponent has a slight advantage.';
    } else {
        message = '❌ Your opponent has a strong advantage.';
    }
    
    showNotification(message, evaluation > 0 ? 'success' : 'warning');
}

function flipBoard() {
    board.style.transform = board.style.transform === 'rotate(180deg)' ? 'rotate(0deg)' : 'rotate(180deg)';
    board.style.transition = 'transform 0.5s ease';
}

function learnMove() {
    const moves = game.moves();
    if (moves.length === 0) return;
    
    // Show explanation for a random legal move
    const randomMove = moves[Math.floor(Math.random() * moves.length)];
    const explanation = getMoveExplanation(randomMove);
    
    showNotification('📚 ' + explanation, 'info');
}

function getMoveExplanation(move) {
    // Simple move explanations
    if (move.includes('x')) {
        return 'This move captures a piece. Captures are usually good for gaining material advantage.';
    } else if (move.includes('+')) {
        return 'This move puts the opponent in check. Checks force your opponent to respond.';
    } else if (move.includes('O-O')) {
        return 'Castling moves your king to safety and develops your rook.';
    } else {
        return 'This move develops a piece and improves your position.';
    }
}

function showPieceInfo(piece) {
    const pieceType = piece[1];
    const explanations = {
        'P': 'Pawns are the soul of chess. They can be promoted to any piece when reaching the 8th rank.',
        'N': 'Knights jump in an L-shape. They are the only pieces that can jump over other pieces.',
        'B': 'Bishops move diagonally. Each player has one light-squared and one dark-squared bishop.',
        'R': 'Rooks move horizontally and vertically. They are powerful on open files.',
        'Q': 'The queen is the most powerful piece, combining rook and bishop movements.',
        'K': 'The king is the most important piece. The game ends when the king is checkmated.'
    };
    
    const explanation = explanations[pieceType] || 'A powerful chess piece.';
    document.getElementById('positionAnalysis').textContent = explanation;
}

function updateLearningAssistant() {
    if (!learningMode) return;
    
    // Update position analysis
    const evaluation = evaluatePosition(game);
    let analysis = 'Position is ';
    
    if (evaluation > 1) analysis += 'much better for White';
    else if (evaluation > 0.3) analysis += 'slightly better for White';
    else if (evaluation > -0.3) analysis += 'balanced';
    else if (evaluation > -1) analysis += 'slightly better for Black';
    else analysis += 'much better for Black';
    
    document.getElementById('positionAnalysis').textContent = analysis;
    
    // Update suggested moves
    const moves = game.moves();
    if (moves.length > 0) {
        const bestMove = getBestMoveIntermediate(moves);
        document.getElementById('suggestedMoves').textContent = 
            'Consider ' + bestMove + ' - ' + getMoveExplanation(bestMove);
    }
    
    // Update warnings
    const threats = findThreats();
    if (threats.length > 0) {
        document.getElementById('warnings').textContent = 'Watch out for: ' + threats.join(', ');
    } else {
        document.getElementById('warnings').textContent = 'No immediate threats detected.';
    }
}

function findThreats() {
    const threats = [];
    const board = game.board();
    
    // Check for undefended pieces
    for (let row = 0; row < 8; row++) {
        for (let col = 0; col < 8; col++) {
            const piece = board[row][col];
            if (piece && piece.color === game.turn()) {
                const square = String.fromCharCode(97 + col) + (8 - row);
                const attacks = game.attacks(square);
                
                // Check if piece is attacked
                let isAttacked = false;
                for (let r = 0; r < 8; r++) {
                    for (let c = 0; c < 8; c++) {
                        const attacker = board[r][c];
                        if (attacker && attacker.color !== piece.color) {
                            const attackerSquare = String.fromCharCode(97 + c) + (8 - r);
                            const attackerMoves = game.moves({ square: attackerSquare, verbose: true });
                            
                            if (attackerMoves.some(move => move.to === square)) {
                                threats.push(piece.type + ' at ' + square + ' is attacked');
                                isAttacked = true;
                                break;
                            }
                        }
                        if (isAttacked) break;
                    }
                    if (isAttacked) break;
                }
            }
        }
    }
    
    return threats.slice(0, 2); // Return max 2 threats
}

function endGame() {
    stopTimer();
    
    let result, icon, title, message;
    
    if (game.in_checkmate()) {
        if (game.turn() === 'b') {
            result = 'win';
            icon = '🏆';
            title = 'Victory!';
            message = 'Congratulations! You won the game!';
        } else {
            result = 'loss';
            icon = '😔';
            title = 'Defeat';
            message = 'The AI won this time. Try again!';
        }
    } else if (game.in_draw()) {
        result = 'draw';
        icon = '🤝';
        title = 'Draw';
        message = 'The game ended in a draw.';
    } else if (game.in_stalemate()) {
        result = 'draw';
        icon = '🤝';
        title = 'Stalemate';
        message = 'The game ended in stalemate.';
    } else {
        result = 'draw';
        icon = '🤝';
        title = 'Game Over';
        message = 'The game has ended.';
    }
    
    // Show game over modal
    document.getElementById('gameResultIcon').textContent = icon;
    document.getElementById('gameResultTitle').textContent = title;
    document.getElementById('gameResultMessage').textContent = message;
    document.getElementById('gameOverModal').classList.remove('hidden');
    
    // Save game to server
    saveGame(result);
}

function saveGame(result) {
    const formData = new FormData();
    formData.append('player_color', 'white');
    formData.append('difficulty', currentDifficulty);
    formData.append('pgn', game.pgn());
    formData.append('result', result);
    formData.append('moves_count', game.history().length);
    formData.append('time_elapsed', secondsElapsed);
    
    fetch('/api/save-game/', {
        method: 'POST',
        body: formData,
        headers: {
            'X-CSRFToken': getCookie('csrftoken')
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            console.log('Game saved successfully');
        }
    })
    .catch(error => {
        console.error('Error saving game:', error);
    });
}

function closeGameOverModal() {
    document.getElementById('gameOverModal').classList.add('hidden');
}

function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `fixed top-20 right-4 z-50 p-4 rounded-lg shadow-lg transform transition-all duration-300 translate-x-full`;
    
    // Set color based on type
    const colors = {
        'success': 'bg-green-500 text-white',
        'warning': 'bg-yellow-500 text-white',
        'error': 'bg-red-500 text-white',
        'info': 'bg-blue-500 text-white'
    };
    
    notification.className += ' ' + colors[type];
    notification.textContent = message;
    
    document.body.appendChild(notification);
    
    // Slide in
    setTimeout(() => {
        notification.classList.remove('translate-x-full');
    }, 100);
    
    // Remove after 3 seconds
    setTimeout(() => {
        notification.classList.add('translate-x-full');
        setTimeout(() => {
            document.body.removeChild(notification);
        }, 300);
    }, 3000);
}

function updateDailyTip() {
    const tipElement = document.getElementById('dailyTip');
    const randomTip = dailyTips[Math.floor(Math.random() * dailyTips.length)];
    tipElement.textContent = randomTip;
}

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}
