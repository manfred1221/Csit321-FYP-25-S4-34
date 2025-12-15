// Staff Attendance JavaScript
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
    
    // Set default dates (last 30 days)
    const today = new Date();
    const monthAgo = new Date(today.getTime() - 30 * 24 * 60 * 60 * 1000);
    
    document.getElementById('startDate').value = monthAgo.toISOString().split('T')[0];
    document.getElementById('endDate').value = today.toISOString().split('T')[0];
    
    // Load attendance
    loadAttendance();
    
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
    document.getElementById('filterBtn').addEventListener('click', loadAttendance);
}

async function loadAttendance() {
    const startDate = document.getElementById('startDate').value;
    const endDate = document.getElementById('endDate').value;
    
    try {
        let endpoint = API_CONFIG.ENDPOINTS.STAFF.GET_ATTENDANCE(currentUser.staff_id);
        
        if (startDate && endDate) {
            endpoint += `?start_date=${startDate}&end_date=${endDate}`;
        }
        
        const result = await staffApiCall(endpoint);
        
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
        const entryDate = new Date(record.entry_time).toLocaleDateString();
        const entryTime = new Date(record.entry_time).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
        const exitTime = record.exit_time ? 
            new Date(record.exit_time).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}) : 
            '<span style="color: #f59e0b;">In Progress</span>';
        
        const hours = record.duration_hours ? 
            record.duration_hours.toFixed(2) + ' hrs' : 
            '<span style="color: #6b7280;">-</span>';
        
        const location = record.location || 'N/A';
        const method = record.verification_method || 'Manual';
        
        html += `
            <tr>
                <td>${entryDate}</td>
                <td><span class="badge badge-success">${entryTime}</span></td>
                <td>${exitTime}</td>
                <td><strong>${hours}</strong></td>
                <td>${location}</td>
                <td>${method}</td>
            </tr>
        `;
    });
    
    document.getElementById('attendanceTableBody').innerHTML = html;
}

function calculateStats(records) {
    const now = new Date();
    const weekAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
    const monthAgo = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
    
    // Week hours
    const weekHours = records
        .filter(r => new Date(r.entry_time) >= weekAgo && r.duration_hours)
        .reduce((sum, r) => sum + r.duration_hours, 0);
    
    // Month hours
    const monthHours = records
        .filter(r => new Date(r.entry_time) >= monthAgo && r.duration_hours)
        .reduce((sum, r) => sum + r.duration_hours, 0);
    
    // Total days (unique dates with completed attendance)
    const uniqueDates = new Set(
        records
            .filter(r => r.exit_time)
            .map(r => new Date(r.entry_time).toDateString())
    );
    
    document.getElementById('weekHours').textContent = weekHours.toFixed(1) + ' hrs';
    document.getElementById('monthHours').textContent = monthHours.toFixed(1) + ' hrs';
    document.getElementById('totalDays').textContent = uniqueDates.size;
}
