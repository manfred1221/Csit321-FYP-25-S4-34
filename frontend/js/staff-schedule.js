let currentUser = null;

document.addEventListener('DOMContentLoaded', async () => {
    // 1. Verify Session
    currentUser = await checkAuth(); 
    
    if (!currentUser) return;

    // 2. Role Check
    const allowedRoles = ['Internal_Staff', 'Staff', 'Security', 'internal_staff'];
    if (!allowedRoles.includes(currentUser.role)) {
        window.location.href = '/login';
        return;
    }

    // 3. Update Sidebar UI
    const name = currentUser.full_name || currentUser.username;
    document.getElementById('staffNameSidebar').textContent = name;
    document.getElementById('staffRoleSidebar').textContent = currentUser.role || 'Staff Member';

    // 4. Initialize Dates (Today + 7 Days)
    const today = new Date();
    const weekAhead = new Date(today.getTime() + 7 * 24 * 60 * 60 * 1000);
    
    document.getElementById('startDate').value = today.toISOString().split('T')[0];
    document.getElementById('endDate').value = weekAhead.toISOString().split('T')[0];
    
    // 5. Load Data & Listeners
    loadSchedule();
    setupEventListeners();
});

function setupEventListeners() {
    // Logout
    const logoutBtn = document.getElementById('logoutBtn');
    if(logoutBtn) {
        logoutBtn.addEventListener('click', async (e) => {
            e.preventDefault();
            if (confirm('Are you sure you want to logout?')) {
                await logout(); 
            }
        });
    }
    
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
    
    const staffId = currentUser.staff_id || currentUser.user_id;

    try {
        // Construct URL with query parameters
        const url = `/api/staff/${staffId}/schedule?start_date=${startDate}&end_date=${endDate}`;
        
        const response = await fetch(url);
        const result = await response.json();
        
        // Handle response
        if (result.schedules && result.schedules.length > 0) {
            displaySchedule(result.schedules);
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
    // Group by date to make the list readable
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
                <h3 style="color: #2563eb; border-bottom: 2px solid #e2e8f0; padding-bottom: 10px; margin-bottom: 15px; font-size: 16px;">
                    ${dayName}, ${formattedDate}
                </h3>
        `;
        
        groupedByDate[date].forEach(schedule => {
            const duration = calculateDuration(schedule.shift_start, schedule.shift_end);
            const taskDesc = schedule.task_description || 'No specific task assigned';
            
            html += `
                <div style="background: #f8fafc; border-left: 4px solid #10b981; padding: 20px; margin-bottom: 15px; border-radius: 4px; box-shadow: 0 1px 2px rgba(0,0,0,0.05);">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; flex-wrap: wrap;">
                        <div>
                            <p style="margin: 0; font-size: 15px; font-weight: 600; color: #1e293b;">
                                🕐 ${schedule.shift_start} - ${schedule.shift_end}
                            </p>
                            <p style="margin: 5px 0 0; font-size: 13px; color: #64748b;">
                                ⌛ Duration: ${duration}
                            </p>
                        </div>
                        ${schedule.location ? `<span class="badge badge-info" style="font-size: 12px;">📍 ${schedule.location}</span>` : ''}
                    </div>
                    
                    <div style="margin-top: 10px; padding-top: 10px; border-top: 1px solid #e2e8f0;">
                        <p style="margin: 0; color: #475569; font-size: 14px;"><strong>📋 Task:</strong> ${taskDesc}</p>
                    </div>
                </div>
            `;
        });
        
        html += '</div>';
    });
    
    document.getElementById('scheduleList').innerHTML = html;
}

function calculateDuration(startTime, endTime) {
    // Helper to calculate hours between two time strings (HH:MM:SS)
    const start = new Date(`2000-01-01 ${startTime}`);
    const end = new Date(`2000-01-01 ${endTime}`);
    
    let diff = end - start;
    if (diff < 0) {
        // Handle overnight shifts (e.g. 23:00 to 07:00)
        diff += 24 * 60 * 60 * 1000;
    }
    
    const hours = Math.floor(diff / (1000 * 60 * 60));
    const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
    
    if (minutes > 0) {
        return `${hours}h ${minutes}m`;
    }
    return `${hours}h`;
}