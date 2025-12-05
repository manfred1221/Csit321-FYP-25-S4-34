// Staff Dashboard JavaScript

let currentUser = null;

// Load user data
window.addEventListener('DOMContentLoaded', function() {
    console.log('Staff dashboard loading...');
    
    // Check if logged in
    const user = JSON.parse(localStorage.getItem('user') || 'null');
    
    console.log('Current user:', user);
    
    if (!user) {
        alert('Please login first!');
        window.location.href = 'index.html';  // ← CHANGED
        return;
    }
    
    if (user.type !== 'staff') {
        alert('This page is for staff only!');
        window.location.href = 'index.html';  // ← CHANGED
        return;
    }
    
    currentUser = user;
    
    // Display user info
    displayUserInfo();
    
    // Load dashboard data
    loadProfile();
    loadTodaySchedule();
    loadRecentAttendance();
    
    // Setup event listeners
    setupEventListeners();
});

function displayUserInfo() {
    const name = currentUser.full_name || currentUser.username;
    const position = currentUser.position || 'Staff';
    
    document.getElementById('staffName').textContent = name;
    document.getElementById('staffPosition').textContent = position;
    document.getElementById('welcomeName').textContent = name;
    document.getElementById('workStatus').textContent = 'Active';
}

function setupEventListeners() {
    // Logout button
    document.getElementById('logoutBtn').addEventListener('click', function(e) {
        e.preventDefault();
        if (confirm('Are you sure you want to logout?')) {
            localStorage.removeItem('user');
            localStorage.removeItem('auth_token');
            window.location.href = 'index.html';  // ← CHANGED
        }
    });
    
    // Clock in button
    document.getElementById('clockInBtn').addEventListener('click', function() {
        recordAttendance('entry');
    });
    
    // Clock out button
    document.getElementById('clockOutBtn').addEventListener('click', function() {
        recordAttendance('exit');
    });
}

async function loadProfile() {
    try {
        const endpoint = API_CONFIG.ENDPOINTS.STAFF.GET_PROFILE(currentUser.staff_id);
        console.log('Loading profile from:', endpoint);
        
        const result = await staffApiCall(endpoint);
        
        console.log('Profile result:', result);
        
        if (result.success) {
            const profile = result.data;
            document.getElementById('profileInfo').innerHTML = `
                <p><strong>Name:</strong> ${profile.full_name}</p>
                <p><strong>Position:</strong> ${profile.position}</p>
                <p><strong>Contact:</strong> ${profile.contact_number}</p>
                <p><strong>Email:</strong> ${profile.email || 'N/A'}</p>
                <p><strong>Status:</strong> <span class="badge badge-success">${profile.is_active ? 'Active' : 'Inactive'}</span></p>
            `;
        } else {
            document.getElementById('profileInfo').innerHTML = `<p class="error">Error: ${result.error}</p>`;
        }
    } catch (error) {
        console.error('Load profile error:', error);
        document.getElementById('profileInfo').innerHTML = '<p class="error">Error loading profile</p>';
    }
}

async function loadTodaySchedule() {
    try {
        const today = new Date().toISOString().split('T')[0];
        const endpoint = API_CONFIG.ENDPOINTS.STAFF.GET_SCHEDULE(currentUser.staff_id) + 
            `?start_date=${today}&end_date=${today}`;
        
        console.log('Loading schedule from:', endpoint);
        
        const result = await staffApiCall(endpoint);
        
        console.log('Schedule result:', result);
        
        if (result.success && result.data.schedules.length > 0) {
            const schedules = result.data.schedules;
            let html = '<div>';
            schedules.forEach(schedule => {
                html += `
                    <div style="padding: 10px; margin-bottom: 10px; border-left: 3px solid #2563eb; background: #f9fafb;">
                        <p><strong>Time:</strong> ${schedule.shift_start} - ${schedule.shift_end}</p>
                        <p><strong>Task:</strong> ${schedule.task_description}</p>
                    </div>
                `;
            });
            html += '</div>';
            document.getElementById('todaySchedule').innerHTML = html;
        } else {
            document.getElementById('todaySchedule').innerHTML = '<p>No schedule for today</p>';
        }
    } catch (error) {
        console.error('Load schedule error:', error);
        document.getElementById('todaySchedule').innerHTML = '<p class="error">Error loading schedule</p>';
    }
}

async function loadRecentAttendance() {
    try {
        const endpoint = API_CONFIG.ENDPOINTS.STAFF.GET_ATTENDANCE(currentUser.staff_id);
        
        console.log('Loading attendance from:', endpoint);
        
        const result = await staffApiCall(endpoint);
        
        console.log('Attendance result:', result);
        
        if (result.success && result.data.records.length > 0) {
            const records = result.data.records.slice(0, 5); // Show last 5
            let html = '';
            
            records.forEach(record => {
                const entryDate = new Date(record.entry_time).toLocaleDateString();
                const entryTime = new Date(record.entry_time).toLocaleTimeString();
                const exitTime = record.exit_time ? new Date(record.exit_time).toLocaleTimeString() : '-';
                const hours = record.duration_hours ? record.duration_hours.toFixed(2) : '-';
                
                html += `
                    <tr>
                        <td>${entryDate}</td>
                        <td>${entryTime}</td>
                        <td>${exitTime}</td>
                        <td>${hours}</td>
                        <td>${record.location || 'N/A'}</td>
                    </tr>
                `;
            });
            
            document.getElementById('attendanceTableBody').innerHTML = html;
            
            // Calculate week hours
            const weekHours = records
                .filter(r => r.duration_hours)
                .reduce((sum, r) => sum + r.duration_hours, 0);
            document.getElementById('weekHours').textContent = weekHours.toFixed(1) + ' hrs';
            
        } else {
            document.getElementById('attendanceTableBody').innerHTML = 
                '<tr><td colspan="5" style="text-align:center;">No attendance records</td></tr>';
            document.getElementById('weekHours').textContent = '0 hrs';
        }
    } catch (error) {
        console.error('Load attendance error:', error);
        document.getElementById('attendanceTableBody').innerHTML = 
            '<tr><td colspan="5" style="text-align:center;">Error loading attendance</td></tr>';
    }
}

async function recordAttendance(action) {
    const messageDiv = document.getElementById('actionMessage');
    
    try {
        console.log('Recording attendance:', action);
        
        const result = await staffApiCall(
            API_CONFIG.ENDPOINTS.STAFF.RECORD_ATTENDANCE,
            {
                method: 'POST',
                body: JSON.stringify({
                    staff_id: currentUser.staff_id,
                    action: action,
                    confidence: 0.95,
                    location: 'Main Gate'
                })
            }
        );
        
        console.log('Attendance record result:', result);
        
        if (result.success) {
            messageDiv.textContent = result.data.message;
            messageDiv.className = 'message success';
            messageDiv.style.display = 'block';
            
            // Reload attendance
            setTimeout(() => {
                loadRecentAttendance();
                messageDiv.style.display = 'none';
            }, 2000);
        } else {
            messageDiv.textContent = result.error || 'Failed to record attendance';
            messageDiv.className = 'message error';
            messageDiv.style.display = 'block';
        }
    } catch (error) {
        console.error('Record attendance error:', error);
        messageDiv.textContent = 'Error recording attendance: ' + error.message;
        messageDiv.className = 'message error';
        messageDiv.style.display = 'block';
    }
}