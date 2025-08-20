/* sneportal/static/js/session_list.js */

// Update active session times
function updateTimes() {
    document.querySelectorAll('.time-remaining').forEach(el => {
        let seconds = parseInt(el.dataset.seconds);
        if (seconds > 0) {
            seconds--;
            el.dataset.seconds = seconds;
            el.textContent = formatTime(seconds);
        }
    });
}

function formatTime(seconds) {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
}

// Stop session
async function stopSession(sessionId) {
    if (!confirm('Are you sure you want to stop this exam session?')) return;

    try {
        const response = await fetch('/exam/session-state/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: `session_id=${sessionId}&action=emergency_stop`
        });

        if (response.ok) {
            showFeedback('Session stopped successfully', 'success');
            location.reload();
        } else {
            showFeedback('Failed to stop session', 'error');
        }
    } catch (error) {
        showFeedback('Failed to stop session', 'error');
    }
}

// View session
function viewSession(sessionId) {
    window.location.href = `/exam/results/${sessionId}/`;
}

// Get CSRF token from cookies
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

// Show feedback message
function showFeedback(message, type = 'success') {
    const feedback = document.createElement('div');
    feedback.className = `feedback ${type}`;
    feedback.textContent = message;
    
    let messages = document.querySelector('.messages');
    if (!messages) {
        messages = document.createElement('div');
        messages.className = 'messages';
        document.querySelector('.container').insertBefore(messages, document.querySelector('main'));
    }
    messages.appendChild(feedback);
    
    setTimeout(() => feedback.remove(), 5000);
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Start time updates
    setInterval(updateTimes, 1000);

    // Auto-refresh page every minute to show new sessions
    setInterval(() => location.reload(), 60000);
});
