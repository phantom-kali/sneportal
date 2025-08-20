/* sneportal/static/js/base.js */

// Common utility functions
function showFeedback(message, type = 'success') {
    const feedback = document.createElement('div');
    feedback.className = `feedback ${type}`;
    feedback.textContent = message;
    
    let messages = document.querySelector('.messages');
    if (!messages) {
        messages = document.createElement('div');
        messages.className = 'messages';
        messages.setAttribute('role', 'alert');
        messages.setAttribute('aria-live', 'polite');
        document.querySelector('.container').insertBefore(messages, document.querySelector('main'));
    }
    messages.appendChild(feedback);
    
    setTimeout(() => feedback.remove(), 5000);
}

function setLoading(button, isLoading) {
    if (isLoading) {
        button.disabled = true;
        button.innerHTML = '<span class="loading"></span> Processing...';
    } else {
        button.disabled = false;
        button.innerHTML = button.getAttribute('data-original-text');
    }
}

// CSRF token setup for AJAX requests
const csrftoken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;

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

// Setup AJAX headers
function setupAjaxHeaders() {
    const headers = new Headers({
        'Content-Type': 'application/json',
        'X-CSRFToken': getCookie('csrftoken')
    });
    return headers;
}
