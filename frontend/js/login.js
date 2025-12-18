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
            const response = await fetch(API_CONFIG.BASE_URL + API_CONFIG.ENDPOINTS.STAFF.LOGIN, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            });
            
            const result = await response.json();
            
            if (response.ok && result.staff_id) {
                const staffData = {
                    id: result.staff_id || result.user_id,
                    staff_id: result.staff_id || result.user_id,
                    user_id: result.user_id,
                    username: result.username,
                    full_name: result.name || result.username,
                    position: result.role,
                    type: 'staff',
                    email: result.email || `${username}@condo.com`
                };
                
                localStorage.setItem('user', JSON.stringify(staffData));
                localStorage.setItem('auth_token', result.token);
                
                showMessage('message', 'Login successful!', 'success');
                setTimeout(() => window.location.href = '/staff/dashboard', 1000);
                return;
            } else {
                showMessage('message', result.error || 'Login failed', 'error');
            }
        }
        
        // ========================================
        // RESIDENT - Real Backend API 
        // ========================================
        else if (userType === 'resident') {
            console.log('🔵 RESIDENT LOGIN STARTED');
            
            const response = await fetch(API_CONFIG.BASE_URL + '/api/auth/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            });
            
            const result = await response.json();
            console.log('🔵 API Response:', result);
            
            if (response.ok && result.resident_id) {
                const residentData = {
                    id: result.resident_id,
                    resident_id: result.resident_id,
                    user_id: result.user_id,
                    username: result.username,
                    full_name: result.full_name || result.username,
                    type: 'resident',
                    email: result.email || `${username}@condo.com`,
                    unit_number: result.unit_number || 'N/A',
                    contact_number: result.contact_number || 'N/A',
                    role: result.role
                };
                
                console.log('🔵 Storing residentData:', residentData);
                localStorage.setItem('user', JSON.stringify(residentData));
                localStorage.setItem('auth_token', result.token);
                
                console.log('🔵 Verify stored data:', JSON.parse(localStorage.getItem('user')));
                
                showMessage('message', 'Login successful!', 'success');
                
                console.log('🔵 About to redirect to /resident/dashboard');
                setTimeout(() => {
                    console.log('🔵 REDIRECTING NOW');
                    window.location.href = '/resident/dashboard';
                }, 1000);
                return;
            } else {
                showMessage('message', result.error || 'Login failed', 'error');
            }
        }
        
        // ========================================
        // VISITOR, ADMIN - Mock
        // ========================================
        else {
            const mockUser = {
                id: userType === 'visitor' ? 101 : 999,
                username: username,
                type: userType,
                full_name: username,
                email: `${username}@example.com`
            };
            
            localStorage.setItem('user', JSON.stringify(mockUser));
            localStorage.setItem('auth_token', 'mock_token_' + Date.now());
            
            if (userType === 'visitor') {
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