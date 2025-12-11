// Staff Dashboard JavaScript
let currentUser = null;

window.addEventListener('DOMContentLoaded', function() {
    // Check authentication
    const user = JSON.parse(localStorage.getItem('user') || 'null');
    
    if (!user || user.type !== 'staff') {
        alert('Please login as staff first!');
        window.location.href = 'index.html';
        return;
    }
    
    currentUser = user;
    
    // Display user info
    displayUserInfo();
    
    // Load dashboard data
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
    // Logout
    document.getElementById('logoutBtn').addEventListener('click', function(e) {
        e.preventDefault();
        if (confirm('Are you sure you want to logout?')) {
            localStorage.removeItem('user');
            localStorage.removeItem('auth_token');
            window.location.href = 'index.html';
        }
    });
    
    // Clock in/out buttons
    document.getElementById('clockInBtn').addEventListener('click', () => recordAttendance('entry'));
    document.getElementById('clockOutBtn').addEventListener('click', () => recordAttendance('exit'));
}

async function loadTodaySchedule() {
    try {
        const today = new Date().toISOString().split('T')[0];
        const staffId = currentUser.staff_id || currentUser.user_id || currentUser.id;

        // Use our new staff schedules API
        const response = await fetch(`${API_CONFIG.BASE_URL}/api/staff/schedules?staff_id=${staffId}`);
        const result = await response.json();

        if (result.success && result.schedules && result.schedules.length > 0) {
            // Filter schedules for today
            const todaySchedules = result.schedules.filter(schedule => {
                return schedule.start_date <= today && schedule.end_date >= today;
            });

            if (todaySchedules.length > 0) {
                let html = '';

                todaySchedules.forEach(schedule => {
                    html += `
                        <div style="padding: 15px; margin-bottom: 10px; border-left: 4px solid #2563eb; background: #f9fafb; border-radius: 4px;">
                            <p style="margin: 5px 0;"><strong>🔄 Shift:</strong> ${schedule.shift_name || 'Assigned Shift'}</p>
                            <p style="margin: 5px 0;"><strong>⏰ Time:</strong> ${schedule.start_time} - ${schedule.end_time}</p>
                            <p style="margin: 5px 0;"><strong>📍 Location:</strong> ${schedule.location || 'N/A'}</p>
                            ${schedule.notes ? `<p style="margin: 5px 0;"><strong>📋 Notes:</strong> ${schedule.notes}</p>` : ''}
                        </div>
                    `;
                });

                document.getElementById('todaySchedule').innerHTML = html;
            } else {
                document.getElementById('todaySchedule').innerHTML = '<p style="text-align: center; color: #6b7280; padding: 20px;">No schedule for today</p>';
            }
        } else {
            document.getElementById('todaySchedule').innerHTML = '<p style="text-align: center; color: #6b7280; padding: 20px;">No schedule assigned yet</p>';
        }
    } catch (error) {
        console.error('Load schedule error:', error);
        document.getElementById('todaySchedule').innerHTML = '<p style="text-align: center; color: #ef4444;">Error loading schedule</p>';
    }
}

async function loadRecentAttendance() {
    try {
        const endpoint = API_CONFIG.ENDPOINTS.STAFF.GET_ATTENDANCE(currentUser.staff_id);
        const result = await staffApiCall(endpoint);
        
        if (result.success && result.data.records && result.data.records.length > 0) {
            const records = result.data.records.slice(0, 5);
            let html = '';
            
            records.forEach(record => {
                const entryDate = new Date(record.entry_time).toLocaleDateString();
                const entryTime = new Date(record.entry_time).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
                const exitTime = record.exit_time ? new Date(record.exit_time).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}) : '-';
                const hours = record.duration_hours ? record.duration_hours.toFixed(2) : '-';
                
                html += `
                    <tr>
                        <td>${entryDate}</td>
                        <td>${entryTime}</td>
                        <td>${exitTime}</td>
                        <td>${hours} hrs</td>
                    </tr>
                `;
            });
            
            document.getElementById('attendanceTableBody').innerHTML = html;
            
            // Calculate stats
            const now = new Date();
            const weekAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
            const monthAgo = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
            
            const weekHours = records
                .filter(r => new Date(r.entry_time) >= weekAgo && r.duration_hours)
                .reduce((sum, r) => sum + r.duration_hours, 0);
                
            const monthHours = records
                .filter(r => new Date(r.entry_time) >= monthAgo && r.duration_hours)
                .reduce((sum, r) => sum + r.duration_hours, 0);
            
            document.getElementById('weekHours').textContent = weekHours.toFixed(1) + ' hrs';
            document.getElementById('monthHours').textContent = monthHours.toFixed(1) + ' hrs';
            
        } else {
            document.getElementById('attendanceTableBody').innerHTML = 
                '<tr><td colspan="4" style="text-align:center;">No attendance records</td></tr>';
            document.getElementById('weekHours').textContent = '0 hrs';
            document.getElementById('monthHours').textContent = '0 hrs';
        }
    } catch (error) {
        console.error('Load attendance error:', error);
        document.getElementById('attendanceTableBody').innerHTML = 
            '<tr><td colspan="4" style="text-align:center; color: #ef4444;">Error loading attendance</td></tr>';
    }
}

async function recordAttendance(action) {
    const messageDiv = document.getElementById('actionMessage');
    
    try {
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
        
        if (result.success) {
            messageDiv.textContent = '✅ ' + result.data.message;
            messageDiv.className = 'message success';
            messageDiv.style.display = 'block';
            
            setTimeout(() => {
                loadRecentAttendance();
                messageDiv.style.display = 'none';
            }, 2000);
        } else {
            messageDiv.textContent = '❌ ' + (result.error || 'Failed to record attendance');
            messageDiv.className = 'message error';
            messageDiv.style.display = 'block';
        }
    } catch (error) {
        console.error('Record attendance error:', error);
        messageDiv.textContent = '❌ Error: ' + error.message;
        messageDiv.className = 'message error';
        messageDiv.style.display = 'block';
    }
}
