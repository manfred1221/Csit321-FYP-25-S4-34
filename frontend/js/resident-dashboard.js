// Global user variable - accessible by all functions
let user = null;

document.addEventListener('DOMContentLoaded', async () => {  // ⭐ Make it async
    // Check authentication and store in global variable
    user = await checkAuth();  // ⭐ Add await
    if (!user) return;

    // ⭐ Check user.role instead of user.type
    if (user.role !== 'Resident') {
        console.log('User is not a resident, role:', user.role);
        window.location.href = '/login';  // Redirect to login, not /
        return;
    }

    // Update user info in sidebar
    document.getElementById('userName').textContent = user.full_name || user.username || 'User';
    
    // Handle email display (might not be in session)
    const emailEl = document.getElementById('userEmail');
    if (emailEl) {
        emailEl.textContent = user.email || user.username + '@condo.com';
    }

    // Load dashboard data
    loadDashboardData();
});

// Load dashboard data
async function loadDashboardData() {
    await Promise.all([
        loadVisitors(),
        loadAccessHistory(),
        loadStats()
    ]);
}

// Load visitors
async function loadVisitors() {
    const residentId = user.resident_id || user.user_id;
    const endpoint = API_CONFIG.ENDPOINTS.RESIDENT.GET_VISITORS(residentId);
    const result = await apiCall(endpoint);
    
    if (result.success) {
        const visitors = result.data.visitors || [];
        
        // Update stats
        const activeVisitors = visitors.filter(v => v.status === 'APPROVED').length;
        document.getElementById('activeVisitors').textContent = activeVisitors;
        document.getElementById('totalVisitors').textContent = visitors.length;
        
        // Display recent visitors (first 5)
        const recentVisitors = visitors.slice(0, 5);
        displayRecentVisitors(recentVisitors);
    } else {
        console.log('Could not load visitors:', result.error);
        document.getElementById('activeVisitors').textContent = '0';
        document.getElementById('totalVisitors').textContent = '0';
    }
}

function displayRecentVisitors(visitors) {
    const tbody = document.querySelector('#recentVisitorsTable tbody');
    
    if (visitors.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" class="text-center">No visitors registered yet</td></tr>';
        return;
    }
    
    tbody.innerHTML = visitors.map(visitor => `
        <tr>
            <td>${visitor.full_name || visitor.visitor_name}</td>
            <td><span class="badge badge-${visitor.status === 'APPROVED' ? 'success' : 'warning'}">${visitor.status}</span></td>
            <td>${formatDateTime(visitor.check_in || visitor.start_time)}</td>
            <td>
                <button class="btn btn-sm btn-secondary" onclick="viewVisitor(${visitor.visitor_id})">View</button>
            </td>
        </tr>
    `).join('');
}

// Load access history
async function loadAccessHistory() {
    const residentId = user.resident_id || user.user_id;
    const endpoint = API_CONFIG.ENDPOINTS.RESIDENT.ACCESS_HISTORY(residentId);
    const result = await apiCall(endpoint);
    
    if (result.success) {
        const history = result.data.access_logs || [];
        
        // Update today's access count
        const today = new Date().toDateString();
        const todayCount = history.filter(h => {
            const logDate = new Date(h.timestamp).toDateString();
            return logDate === today;
        }).length;
        document.getElementById('todayAccess').textContent = todayCount;
        
        // Display recent access (first 5)
        const recentAccess = history.slice(0, 5);
        displayRecentAccessHistory(recentAccess);
    } else {
        console.log('Could not load access history:', result.error);
        document.getElementById('todayAccess').textContent = '0';
    }
}

function displayRecentAccessHistory(history) {
    const tbody = document.querySelector('#accessHistoryTable tbody');
    
    if (history.length === 0) {
        tbody.innerHTML = '<tr><td colspan="3" class="text-center">No access records yet</td></tr>';
        return;
    }
    
    tbody.innerHTML = history.map(record => `
        <tr>
            <td>${formatDateTime(record.timestamp)}</td>
            <td>${record.location || 'Main Gate'}</td>
            <td><span class="badge badge-${record.result === 'GRANTED' ? 'success' : 'danger'}">${record.result}</span></td>
        </tr>
    `).join('');
}

// Load stats
async function loadStats() {
    const residentId = user.resident_id || user.user_id;
    const endpoint = API_CONFIG.ENDPOINTS.RESIDENT.ALERTS(residentId);
    const result = await apiCall(endpoint);
    
    if (result.success) {
        const alerts = result.data.alerts || [];
        const unreadAlerts = alerts.filter(a => a.status === 'UNREAD').length;
        document.getElementById('unreadAlerts').textContent = unreadAlerts;
    } else {
        console.log('Could not load alerts:', result.error);
        document.getElementById('unreadAlerts').textContent = '0';
    }
}

// Toggle face access
async function toggleFaceAccess() {
    if (!confirm('Are you sure you want to temporarily disable face access?')) {
        return;
    }
    
    const residentId = user.resident_id || user.user_id;
    const endpoint = API_CONFIG.ENDPOINTS.RESIDENT.DISABLE_FACE_ACCESS(residentId);
    const result = await apiCall(endpoint, { method: 'POST' });
    
    if (result.success) {
        alert('Face access has been disabled temporarily. You can re-enable it in your profile settings.');
        
        // Update button
        const btn = document.getElementById('toggleAccessBtn');
        btn.textContent = 'Enable Face Access';
        btn.classList.remove('btn-danger');
        btn.classList.add('btn-success');
    } else {
        alert('Failed to toggle face access. Please try again.');
    }
}

// View visitor details (placeholder)
function viewVisitor(visitorId) {
    window.location.href = `/resident/visitors?visitor=${visitorId}`;
}