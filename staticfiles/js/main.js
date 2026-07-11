// Main JavaScript for TTSA Chess Academy
document.addEventListener('DOMContentLoaded', function() {
    initializeMobileMenu();
    initializeNotifications();
    initializeTooltips();
    initializeAnimations();
});

// Mobile Menu Toggle
function initializeMobileMenu() {
    const mobileMenuToggle = document.getElementById('mobileMenuToggle');
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('mobileMenuOverlay');
    
    if (mobileMenuToggle && sidebar && overlay) {
        mobileMenuToggle.addEventListener('click', function() {
            sidebar.classList.toggle('open');
            overlay.classList.toggle('hidden');
        });
        
        overlay.addEventListener('click', function() {
            sidebar.classList.remove('open');
            overlay.classList.add('hidden');
        });
    }
}

// Notification System
function initializeNotifications() {
    // Auto-hide notifications after 5 seconds
    const notifications = document.querySelectorAll('.notification');
    notifications.forEach(notification => {
        setTimeout(() => {
            notification.style.opacity = '0';
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            }, 300);
        }, 5000);
    });
}

// Tooltip System
function initializeTooltips() {
    const tooltips = document.querySelectorAll('[data-tooltip]');
    tooltips.forEach(tooltip => {
        tooltip.addEventListener('mouseenter', function() {
            const tooltipText = this.getAttribute('data-tooltip');
            const tooltipElement = document.createElement('div');
            tooltipElement.className = 'tooltip-content';
            tooltipElement.textContent = tooltipText;
            tooltipElement.style.cssText = `
                position: absolute;
                bottom: 100%;
                left: 50%;
                transform: translateX(-50%);
                background: #1f2937;
                color: white;
                padding: 0.5rem;
                border-radius: 0.25rem;
                font-size: 0.875rem;
                white-space: nowrap;
                z-index: 1000;
                pointer-events: none;
                opacity: 0;
                transition: opacity 0.3s ease;
            `;
            
            this.style.position = 'relative';
            this.appendChild(tooltipElement);
            
            setTimeout(() => {
                tooltipElement.style.opacity = '1';
            }, 10);
        });
        
        tooltip.addEventListener('mouseleave', function() {
            const tooltipContent = this.querySelector('.tooltip-content');
            if (tooltipContent) {
                tooltipContent.style.opacity = '0';
                setTimeout(() => {
                    if (tooltipContent.parentNode) {
                        tooltipContent.parentNode.removeChild(tooltipContent);
                    }
                }, 300);
            }
        });
    });
}

// Animation System
function initializeAnimations() {
    // Intersection Observer for fade-in animations
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };
    
    const observer = new IntersectionObserver(function(entries) {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);
    
    // Observe elements with fade-in class
    const fadeElements = document.querySelectorAll('.fade-in');
    fadeElements.forEach(element => {
        element.style.opacity = '0';
        element.style.transform = 'translateY(20px)';
        element.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
        observer.observe(element);
    });
}

// Utility Functions
function showNotification(message, type = 'info', duration = 5000) {
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    
    // Style the notification
    notification.style.cssText = `
        position: fixed;
        top: 5rem;
        right: 1rem;
        z-index: 1000;
        padding: 1rem;
        border-radius: 0.5rem;
        box-shadow: 0 10px 15px rgba(0, 0, 0, 0.1);
        animation: slideIn 0.3s ease;
        max-width: 300px;
    `;
    
    // Set color based on type
    const colors = {
        'success': 'linear-gradient(135deg, #10b981, #34d399)',
        'warning': 'linear-gradient(135deg, #f59e0b, #fbbf24)',
        'error': 'linear-gradient(135deg, #ef4444, #f87171)',
        'info': 'linear-gradient(135deg, #6366f1, #8b5cf6)'
    };
    
    notification.style.background = colors[type] || colors.info;
    notification.style.color = 'white';
    
    document.body.appendChild(notification);
    
    // Auto-hide
    setTimeout(() => {
        notification.style.opacity = '0';
        notification.style.transform = 'translateX(100%)';
        setTimeout(() => {
            if (notification.parentNode) {
                document.body.removeChild(notification);
            }
        }, 300);
    }, duration);
    
    return notification;
}

function showModal(title, content, actions = []) {
    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.style.cssText = `
        position: fixed;
        inset: 0;
        background: rgba(0, 0, 0, 0.5);
        z-index: 1000;
        display: flex;
        align-items: center;
        justify-content: center;
        animation: fadeIn 0.3s ease;
    `;
    
    const modalContent = document.createElement('div');
    modalContent.className = 'modal-content';
    modalContent.style.cssText = `
        background: white;
        border-radius: 1rem;
        padding: 2rem;
        max-width: 28rem;
        width: 90%;
        box-shadow: 0 25px 50px rgba(0, 0, 0, 0.25);
        animation: slideIn 0.3s ease;
    `;
    
    modalContent.innerHTML = `
        <h2 class="text-2xl font-bold mb-4">${title}</h2>
        <div class="mb-6">${content}</div>
        <div class="flex space-x-3 justify-end">
            ${actions.map(action => `
                <button onclick="${action.onclick}" class="btn ${action.class || 'btn-secondary'}">
                    ${action.text}
                </button>
            `).join('')}
        </div>
    `;
    
    modal.appendChild(modalContent);
    document.body.appendChild(modal);
    
    // Close on background click
    modal.addEventListener('click', function(e) {
        if (e.target === modal) {
            closeModal(modal);
        }
    });
    
    return modal;
}

function closeModal(modal) {
    if (modal && modal.parentNode) {
        modal.style.opacity = '0';
        setTimeout(() => {
            document.body.removeChild(modal);
        }, 300);
    }
}

function confirmAction(message, onConfirm, onCancel = null) {
    const modal = showModal(
        'Confirm Action',
        `<p>${message}</p>`,
        [
            {
                text: 'Cancel',
                class: 'btn-secondary',
                onclick: `closeModal(this.closest('.modal')); ${onCancel ? onCancel + '()' : ''}`
            },
            {
                text: 'Confirm',
                class: 'btn-primary',
                onclick: `closeModal(this.closest('.modal')); ${onConfirm}()`
            }
        ]
    );
    
    return modal;
}

// Loading States
function showLoading(element, text = 'Loading...') {
    const loadingDiv = document.createElement('div');
    loadingDiv.className = 'loading-container';
    loadingDiv.innerHTML = `
        <div class="loading"></div>
        <span class="ml-2">${text}</span>
    `;
    loadingDiv.style.cssText = `
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 2rem;
        color: #6b7280;
    `;
    
    if (element) {
        element.innerHTML = '';
        element.appendChild(loadingDiv);
    }
    
    return loadingDiv;
}

function hideLoading(element, content) {
    if (element && element.querySelector('.loading-container')) {
        element.innerHTML = content || '';
    }
}

// Form Helpers
function serializeForm(form) {
    const formData = new FormData(form);
    const data = {};
    
    for (let [key, value] of formData.entries()) {
        data[key] = value;
    }
    
    return data;
}

function validateForm(form, rules) {
    const errors = {};
    
    for (let field in rules) {
        const element = form.querySelector(`[name="${field}"]`);
        if (!element) continue;
        
        const value = element.value.trim();
        const fieldRules = rules[field];
        
        // Required validation
        if (fieldRules.required && !value) {
            errors[field] = `${fieldRules.label || field} is required`;
            continue;
        }
        
        // Length validation
        if (fieldRules.minLength && value.length < fieldRules.minLength) {
            errors[field] = `${fieldRules.label || field} must be at least ${fieldRules.minLength} characters`;
        }
        
        if (fieldRules.maxLength && value.length > fieldRules.maxLength) {
            errors[field] = `${fieldRules.label || field} must be no more than ${fieldRules.maxLength} characters`;
        }
        
        // Pattern validation
        if (fieldRules.pattern && !fieldRules.pattern.test(value)) {
            errors[field] = fieldRules.message || `${fieldRules.label || field} is invalid`;
        }
    }
    
    return errors;
}

function displayFormErrors(form, errors) {
    // Clear previous errors
    form.querySelectorAll('.error-message').forEach(error => {
        error.remove();
    });
    
    form.querySelectorAll('.form-input').forEach(input => {
        input.classList.remove('border-red-500');
    });
    
    // Display new errors
    for (let field in errors) {
        const element = form.querySelector(`[name="${field}"]`);
        if (element) {
            element.classList.add('border-red-500');
            
            const errorDiv = document.createElement('div');
            errorDiv.className = 'error-message text-red-500 text-sm mt-1';
            errorDiv.textContent = errors[field];
            
            element.parentNode.appendChild(errorDiv);
        }
    }
}

// API Helpers
async function apiRequest(url, options = {}) {
    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        }
    };
    
    const finalOptions = { ...defaultOptions, ...options };
    
    try {
        const response = await fetch(url, finalOptions);
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.message || 'Request failed');
        }
        
        return data;
    } catch (error) {
        console.error('API request failed:', error);
        showNotification(error.message || 'An error occurred', 'error');
        throw error;
    }
}

// Cookie Helper
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

// Local Storage Helpers
function setLocalStorage(key, value) {
    try {
        localStorage.setItem(key, JSON.stringify(value));
        return true;
    } catch (error) {
        console.error('Failed to save to localStorage:', error);
        return false;
    }
}

function getLocalStorage(key, defaultValue = null) {
    try {
        const item = localStorage.getItem(key);
        return item ? JSON.parse(item) : defaultValue;
    } catch (error) {
        console.error('Failed to read from localStorage:', error);
        return defaultValue;
    }
}

function removeLocalStorage(key) {
    try {
        localStorage.removeItem(key);
        return true;
    } catch (error) {
        console.error('Failed to remove from localStorage:', error);
        return false;
    }
}

// Game Helpers
function formatTime(seconds) {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes.toString().padStart(2, '0')}:${remainingSeconds.toString().padStart(2, '0')}`;
}

function formatDate(date) {
    return new Intl.DateTimeFormat('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    }).format(new Date(date));
}

function formatNumber(num) {
    return new Intl.NumberFormat().format(num);
}

// Theme Helpers
function setTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    setLocalStorage('theme', theme);
}

function getTheme() {
    return getLocalStorage('theme', 'light');
}

// Initialize theme
document.addEventListener('DOMContentLoaded', function() {
    const theme = getTheme();
    setTheme(theme);
});

// Export functions for use in other scripts
window.TTSA = {
    showNotification,
    showModal,
    closeModal,
    confirmAction,
    showLoading,
    hideLoading,
    serializeForm,
    validateForm,
    displayFormErrors,
    apiRequest,
    getCookie,
    setLocalStorage,
    getLocalStorage,
    removeLocalStorage,
    formatTime,
    formatDate,
    formatNumber,
    setTheme,
    getTheme
};
