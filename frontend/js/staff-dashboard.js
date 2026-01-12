let currentUser = null;

document.addEventListener('DOMContentLoaded', async () => {
    // 1. Verify Session
    currentUser = await checkAuth(); 
    
    if (!currentUser) return;

    // 2. Role Check (Allow Internal Staff and Security)
    const allowedRoles = ['Internal_Staff', 'Staff', 'Security', 'internal_staff'];
    if (!allowedRoles.includes(currentUser.role)) {
        window.location.href = '/login';
        return;
    }
    
    // 3. Update UI with User Info
    updateUserInfo();
    
    // 4. Load Dashboard Data
    loadDashboardStats();
    loadTodaySchedule();
    loadRecentAttendance();
    
    // 5. Setup Buttons
    setupEventListeners();
});

function updateUserInfo() {
    const name = currentUser.full_name || currentUser.username;
    // Update Sidebar
    document.getElementById('staffNameSidebar').textContent = name;
    document.getElementById('staffRoleSidebar').textContent = currentUser.role || 'Staff Member';
    // Update Header
    document.getElementById('welcomeName').textContent = name;
}

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
    
    // Clock In/Out
    document.getElementById('clockInBtn').addEventListener('click', () => handleAttendance('entry'));
    document.getElementById('clockOutBtn').addEventListener('click', () => handleAttendance('exit'));
}

async function loadDashboardStats() {
    try {
        // Fetch hours and status
        // Note: Using attendance endpoint to calc stats if a specific stats endpoint doesn't exist
        const staffId = currentUser.staff_id || currentUser.user_id;
        const response = await fetch(`/api/staff/${staffId}/attendance`);
        const result = await response.json();

        if (result.success && result.data.records) {
            const records = result.data.records;
            
            // Check if currently clocked in (last record has entry but no exit)
            const lastRecord = records[0];
            const isClockedIn = lastRecord && lastRecord.entry_time && !lastRecord.exit_time;
            
            updateStatusUI(isClockedIn);
            
            // Calculate Hours (Simple client-side calculation)
            // You can replace this with a backend endpoint /api/staff/stats if you have one
            const now = new Date();
            const startOfWeek = new Date(now.setDate(now.getDate() - now.getDay()));
            const startOfMonth = new Date(now.getFullYear(), now.getMonth(), 1);
            
            let weekHours = 0;
            let monthHours = 0;

            records.forEach(r => {
                if(r.duration_hours) {
                    const entryDate = new Date(r.entry_time);
                    if(entryDate >= startOfWeek) weekHours += r.duration_hours;
                    if(entryDate >= startOfMonth) monthHours += r.duration_hours;
                }
            });

            document.getElementById('weekHours').textContent = weekHours.toFixed(1) + ' hrs';
            document.getElementById('monthHours').textContent = monthHours.toFixed(1) + ' hrs';
        }
    } catch (error) {
        console.error('Error loading stats:', error);
    }
}

function updateStatusUI(isClockedIn) {
    const statusEl = document.getElementById('workStatus');
    const inBtn = document.getElementById('clockInBtn');
    const outBtn = document.getElementById('clockOutBtn');

    if (isClockedIn) {
        statusEl.textContent = 'On Duty';
        statusEl.className = 'stat-value active';
        statusEl.style.color = '#10b981'; // Green
        inBtn.disabled = true;
        inBtn.classList.replace('btn-primary', 'btn-secondary');
        outBtn.disabled = false;
        outBtn.classList.replace('btn-secondary', 'btn-primary');
    } else {
        statusEl.textContent = 'Off Duty';
        statusEl.className = 'stat-value inactive';
        statusEl.style.color = '#64748b'; // Gray
        inBtn.disabled = false;
        inBtn.classList.replace('btn-secondary', 'btn-primary');
        outBtn.disabled = true;
        outBtn.classList.replace('btn-primary', 'btn-secondary');
    }
}

async function loadTodaySchedule() {
    const today = new Date().toISOString().split('T')[0];
    const staffId = currentUser.staff_id || currentUser.user_id;
    
    try {
        const response = await fetch(`/api/staff/${staffId}/schedule?start_date=${today}&end_date=${today}`);
        const result = await response.json();
        
        const container = document.getElementById('todaySchedule');
        
        if (result.schedules && result.schedules.length > 0) {
            container.innerHTML = result.schedules.map(s => `
                <div style="background: #f8fafc; border-left: 4px solid #3b82f6; padding: 12px; margin-bottom: 8px; border-radius: 4px;">
                    <div style="display:flex; justify-content:space-between; margin-bottom: 5px;">
                        <strong>${s.shift_name || 'Shift'}</strong>
                        <span class="badge badge-info">${s.shift_start} - ${s.shift_end}</span>
                    </div>
                    <div style="font-size: 13px; color: #64748b;">${s.task_description || 'No specific tasks'}</div>
                </div>
            `).join('');
        } else {
            container.innerHTML = '<p style="text-align: center; color: #64748b;">No shifts scheduled for today.</p>';
        }
    } catch (error) {
        document.getElementById('todaySchedule').innerHTML = '<p style="text-align: center; color: #ef4444;">Error loading schedule.</p>';
    }
}

async function loadRecentAttendance() {
    const staffId = currentUser.staff_id || currentUser.user_id;
    try {
        const response = await fetch(`/api/staff/${staffId}/attendance`);
        const result = await response.json();
        
        const tbody = document.getElementById('attendanceTableBody');
        
        if (result.success && result.data.records && result.data.records.length > 0) {
            tbody.innerHTML = result.data.records.slice(0, 5).map(r => `
                <tr>
                    <td>${new Date(r.entry_time).toLocaleDateString()}</td>
                    <td>${new Date(r.entry_time).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</td>
                    <td>${r.exit_time ? new Date(r.exit_time).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}) : '-'}</td>
                    <td>${r.duration_hours ? r.duration_hours.toFixed(2) + ' hrs' : '-'}</td>
                </tr>
            `).join('');
        } else {
            tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;">No recent attendance records.</td></tr>';
        }
    } catch (error) {
        console.error(error);
    }
}

async function handleAttendance(action) {
    const msgDiv = document.getElementById('actionMessage');
    msgDiv.style.display = 'none';
    
    // Ensure we have the staff ID
    const staffId = currentUser.staff_id || currentUser.user_id;
    
    try {
        const response = await fetch('/api/staff/record-attendance', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                staff_id: staffId,
                action: action, // 'entry' or 'exit'
                location: 'Main Gate',
                confidence: 1.0 // Manual entry implies 100% confidence
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            msgDiv.textContent = `✅ Success: ${result.data.message}`;
            msgDiv.className = 'message success'; // Ensure you have CSS for .message.success
            msgDiv.style.background = '#dcfce7';
            msgDiv.style.color = '#166534';
            
            // Refresh data
            loadDashboardStats();
            loadRecentAttendance();
        } else {
            msgDiv.textContent = `❌ Error: ${result.error}`;
            msgDiv.style.background = '#fee2e2';
            msgDiv.style.color = '#b91c1c';
        }
        msgDiv.style.display = 'block';
        
    } catch (error) {
        msgDiv.textContent = '❌ Network Error';
        msgDiv.style.display = 'block';
    }
}