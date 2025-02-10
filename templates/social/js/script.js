// Handle login form submission
function handleLoginForm(event) {
    event.preventDefault();
    const form = event.target;
    const formData = new FormData(form);
    
    fetch(form.action, {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => handleLoginResponse(data))
    .catch(error => console.error('Error:', error));
}

// Handle the login response and redirect to OTP page
function handleLoginResponse(response) {
    if (response.status === 'success' && response.require_otp) {
        // Add email to OTP template URL
        const email = encodeURIComponent(response.user_data.email);
        const otpUrl = `${response.otp_template}?email=${email}`;
        window.location.href = otpUrl;
    } else {
        window.location.href = response.redirect_url || '/';
    }
}

// Handle OTP form submission
function handleOTPForm(event) {
    event.preventDefault();
    const form = event.target;
    const formData = new FormData(form);
    
    fetch(form.action, {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            window.location.href = data.redirect_url;
        }
    })
    .catch(error => console.error('Error:', error));
}

// Add event listeners when the document is loaded
document.addEventListener('DOMContentLoaded', function() {
    const loginForm = document.getElementById('loginForm');
    const otpForm = document.getElementById('otpForm');
    
    if (loginForm) {
        loginForm.addEventListener('submit', handleLoginForm);
    }
    
    if (otpForm) {
        otpForm.addEventListener('submit', handleOTPForm);
    }
}); 