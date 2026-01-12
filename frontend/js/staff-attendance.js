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

    // 4. Initialize Dates (Last 30 Days)
    const today = new Date();
    const monthAgo = new Date(today.getTime() - 30 * 24 * 60 * 60 * 1000);
    document.getElementById('startDate').value = monthAgo.toISOString().split('T')[0];
    document.getElementById('endDate').value = today.toISOString().split('T')[0];
    
    // 5. Load Data & Listeners
    loadAttendance();
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
    document.getElementById('filterBtn').addEventListener('click', loadAttendance);
}

async function loadAttendance() {
    const staffId = currentUser.staff_id || currentUser.user_id;
    const startDate = document.getElementById('startDate').value;
    const endDate = document.getElementById('endDate').value;

    try {
        let url = `/api/staff/${staffId}/attendance`;
        if (startDate && endDate) {
            url += `?start_date=${startDate}&end_date=${endDate}`;
        }
        
        const response = await fetch(url);
        const result = await response.json();
        
        if (result.success && result.data.records && result.data.records.length > 0) {
            displayAttendance(result.data.records);
            calculateStats(result.data.records);
        } else {
            document.getElementById('attendanceTableBody').innerHTML = 
                '<tr><td colspan="6" style="text-align:center; padding: 40px; color: #6b7280;">No attendance records found</td></tr>';
            
            // Reset stats
            document.getElementById('weekHours').textContent = '0 hrs';
            document.getElementById('monthHours').textContent = '0 hrs';
            document.getElementById('totalDays').textContent = '0';
        }
    } catch (error) {
        console.error('Load attendance error:', error);
        document.getElementById('attendanceTableBody').innerHTML = 
            '<tr><td colspan="6" style="text-align:center; padding: 40px; color: #ef4444;">Error loading attendance</td></tr>';
    }
}

function displayAttendance(records) {
    let html = '';
    
    records.forEach(record => {
        const entryObj = new Date(record.entry_time);
        const entryDate = entryObj.toLocaleDateString();
        const entryTime = entryObj.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
        
        let exitTime = '-';
        if (record.exit_time) {
            exitTime = new Date(record.exit_time).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
        } else {
            exitTime = '<span style="color: #f59e0b; font-weight: bold;">In Progress</span>';
        }
        
        const hours = record.duration_hours ? 
            record.duration_hours.toFixed(2) + ' hrs' : 
            '-';
        
        const location = record.location || 'Main Gate';
        const method = record.verification_method || 'Manual';
        
        html += `
            <tr>
                <td>${entryDate}</td>
                <td><span class="badge badge-success">${entryTime}</span></td>
                <td>${exitTime}</td>
                <td><strong>${hours}</strong></td>
                <td>${location}</td>
                <td><span class="badge badge-info">${method}</span></td>
            </tr>
        `;
    });
    
    document.getElementById('attendanceTableBody').innerHTML = html;
}

function calculateStats(records) {
    const now = new Date();
    // Week starts 7 days ago
    const weekAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
    // Month starts 30 days ago (or you can use strict calendar month)
    const monthAgo = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
    
    // Calculate Week Hours
    const weekHours = records
        .filter(r => new Date(r.entry_time) >= weekAgo && r.duration_hours)
        .reduce((sum, r) => sum + r.duration_hours, 0);
    
    // Calculate Month Hours
    const monthHours = records
        .filter(r => new Date(r.entry_time) >= monthAgo && r.duration_hours)
        .reduce((sum, r) => sum + r.duration_hours, 0);
    
    // Calculate Total Days Worked (Unique dates in the result set)
    const uniqueDates = new Set(
        records.map(r => new Date(r.entry_time).toDateString())
    );
    
    document.getElementById('weekHours').textContent = weekHours.toFixed(1) + ' hrs';
    document.getElementById('monthHours').textContent = monthHours.toFixed(1) + ' hrs';
    document.getElementById('totalDays').textContent = uniqueDates.size;
}