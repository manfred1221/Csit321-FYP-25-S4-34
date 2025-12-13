// Staff Schedule JavaScript
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
    
    // Set default dates (today to 7 days ahead)
    const today = new Date();
    const weekAhead = new Date(today.getTime() + 7 * 24 * 60 * 60 * 1000);
    
    document.getElementById('startDate').value = today.toISOString().split('T')[0];
    document.getElementById('endDate').value = weekAhead.toISOString().split('T')[0];
    
    // Load schedule
    loadSchedule();
    
    // Setup event listeners
    setupEventListeners();
});

function displayUserInfo() {
    const name = currentUser.full_name || currentUser.username;
    const position = currentUser.position || 'Staff';
    
    document.getElementById('staffName').textContent = name;
    document.getElementById('staffPosition').textContent = position;
}

function setupEventListeners() {
    // Logout
    document.getElementById('logoutBtn').addEventListener('click', function(e) {
        e.preventDefault();
        if (confirm('Are you sure you want to logout?')) {
            localStorage.removeItem('user');
            localStorage.removeItem('auth_token');
            window.location.href = '/admin/login';
        }
    });
    
    // Filter button
    document.getElementById('filterBtn').addEventListener('click', loadSchedule);
}

async function loadSchedule() {
    const startDate = document.getElementById('startDate').value;
    const endDate = document.getElementById('endDate').value;
    
    if (!startDate || !endDate) {
        alert('Please select both start and end dates');
        return;
    }
    
    try {
        const endpoint = API_CONFIG.ENDPOINTS.STAFF.GET_SCHEDULE(currentUser.staff_id) + 
            `?start_date=${startDate}&end_date=${endDate}`;
        
        const result = await staffApiCall(endpoint);
        
        if (result.success && result.data.schedules && result.data.schedules.length > 0) {
            displaySchedule(result.data.schedules);
        } else {
            document.getElementById('scheduleList').innerHTML = 
                '<p style="text-align: center; color: #6b7280; padding: 40px;">No schedule found for selected period</p>';
        }
    } catch (error) {
        console.error('Load schedule error:', error);
        document.getElementById('scheduleList').innerHTML = 
            '<p style="text-align: center; color: #ef4444; padding: 40px;">Error loading schedule</p>';
    }
}

function displaySchedule(schedules) {
    // Group by date
    const groupedByDate = {};
    
    schedules.forEach(schedule => {
        const date = schedule.shift_date;
        if (!groupedByDate[date]) {
            groupedByDate[date] = [];
        }
        groupedByDate[date].push(schedule);
    });
    
    let html = '';
    
    // Sort dates
    const sortedDates = Object.keys(groupedByDate).sort();
    
    sortedDates.forEach(date => {
        const dateObj = new Date(date);
        const dayName = dateObj.toLocaleDateString('en-US', { weekday: 'long' });
        const formattedDate = dateObj.toLocaleDateString('en-US', { 
            year: 'numeric', 
            month: 'long', 
            day: 'numeric' 
        });
        
        html += `
            <div style="margin-bottom: 30px;">
                <h3 style="color: #2563eb; border-bottom: 2px solid #2563eb; padding-bottom: 10px; margin-bottom: 15px;">
                    ${dayName}, ${formattedDate}
                </h3>
        `;
        
        groupedByDate[date].forEach(schedule => {
            const duration = calculateDuration(schedule.shift_start, schedule.shift_end);
            
            html += `
                <div style="background: #f9fafb; border-left: 4px solid #10b981; padding: 20px; margin-bottom: 15px; border-radius: 4px;">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                        <div>
                            <p style="margin: 5px 0;"><strong>⏰ Time:</strong> ${schedule.shift_start} - ${schedule.shift_end}</p>
                            <p style="margin: 5px 0;"><strong>⌛ Duration:</strong> ${duration}</p>
                        </div>
                    </div>
                    <p style="margin: 5px 0;"><strong>📋 Task:</strong> ${schedule.task_description}</p>
                </div>
            `;
        });
        
        html += '</div>';
    });
    
    document.getElementById('scheduleList').innerHTML = html;
}

function calculateDuration(startTime, endTime) {
    const start = new Date(`2000-01-01 ${startTime}`);
    const end = new Date(`2000-01-01 ${endTime}`);
    const diff = end - start;
    const hours = Math.floor(diff / (1000 * 60 * 60));
    const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
    
    return `${hours}h ${minutes}m`;
}
