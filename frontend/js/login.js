document.getElementById('loginForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    const userType = document.getElementById('userType').value;
    
    // Mock login - In production, call your auth API
    // For now, we'll simulate a successful login
    
    const mockUser = {
        id: userType === 'resident' ? 1 : 101,
        username: username,
        type: userType,
        full_name: username,
        email: `${username}@example.com`
    };
    
    // Store user data
    localStorage.setItem('user', JSON.stringify(mockUser));
    localStorage.setItem('auth_token', 'mock_token_' + Date.now());
    
    // Redirect based on user type
    if (userType === 'resident') {
        window.location.href = 'resident-dashboard.html';
    } else if (userType === 'visitor') {
        window.location.href = 'visitor-dashboard.html';
    } else {
        window.location.href = 'admin-dashboard.html';
    }
});

// Forgot password handler
document.getElementById('forgotPassword').addEventListener('click', (e) => {
    e.preventDefault();
    alert('Password reset functionality will be implemented. Please contact admin.');
});
