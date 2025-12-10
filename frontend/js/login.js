document.getElementById('loginForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    const userType = document.getElementById('userType').value;
    
    // Disable button while loading
    const submitBtn = e.target.querySelector('button[type="submit"]');
    const originalText = submitBtn.textContent;
    submitBtn.disabled = true;
    submitBtn.textContent = 'Logging in...';
    
    try {
        // ========================================
        // STAFF - Real Backend API 
        // ========================================
        if (userType === 'staff') {
            const result = await staffApiCall(API_CONFIG.ENDPOINTS.STAFF.LOGIN, {
                method: 'POST',
                body: JSON.stringify({ username, password })
            });
            
            if (result.success) {
                const staffData = {
                    id: result.data.staff_id,
                    staff_id: result.data.staff_id,
                    username: result.data.username,
                    full_name: result.data.full_name,
                    position: result.data.position,
                    type: 'staff',
                    email: result.data.email || `${username}@condo.com`
                };
                
                localStorage.setItem('user', JSON.stringify(staffData));
                localStorage.setItem('auth_token', result.data.token);
                
                showMessage('message', 'Login successful!', 'success');
                setTimeout(() => window.location.href = 'staff-dashboard.html', 1000);
                return;
            } else {
                showMessage('message', result.error || 'Login failed', 'error');
            }
        }
        
        // ========================================
        // RESIDENT, VISITOR, ADMIN - Mock (unchanged)
        // ========================================
        else {
            // Mock login for other user types (your existing code)
            const mockUser = {
                id: userType === 'resident' ? 1 : 101,
                username: username,
                type: userType,
                full_name: username,
                email: `${username}@example.com`
            };
            
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
        }
        
    } catch (error) {
        console.error('Login error:', error);
        showMessage('message', 'Login error: ' + error.message, 'error');
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = originalText;
    }
});