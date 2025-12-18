// Global user variable - accessible by all functions
let user = null;

document.addEventListener('DOMContentLoaded', () => {
    // Check authentication and store in global variable
    user = checkAuth();
    if (!user) return;

    if (user.type !== 'resident') {
        window.location.href = '/';
        return;
    }

    // Update user info in sidebar
    document.getElementById('userName').textContent = user.full_name || user.username;
    document.getElementById('userEmail').textContent = user.email;

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
    const endpoint = API_CONFIG.ENDPOINTS.RESIDENT.GET_VISITORS(user.resident_id);
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
    const endpoint = API_CONFIG.ENDPOINTS.RESIDENT.ACCESS_HISTORY(user.resident_id);
    const result = await apiCall(endpoint);
    
    if (result.success) {
        const history = result.data.access_logs || [];
        
        // Display recent access (first 5)
        const recentAccess = history.slice(0, 5);
        displayRecentAccessHistory(recentAccess);
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
    const endpoint = API_CONFIG.ENDPOINTS.RESIDENT.ALERTS(user.resident_id);
    const result = await apiCall(endpoint);
    
    if (result.success) {
        const alerts = result.data.alerts || [];
        const unreadAlerts = alerts.filter(a => a.status === 'UNREAD').length;
        document.getElementById('unreadAlerts').textContent = unreadAlerts;
    }
    
    // You can add more stats here from other endpoints
    // For now, access history count is handled by loadAccessHistory
}

// Toggle face access
async function toggleFaceAccess() {
    if (!confirm('Are you sure you want to temporarily disable face access?')) {
        return;
    }
    
    const endpoint = API_CONFIG.ENDPOINTS.RESIDENT.DISABLE_FACE_ACCESS(user.resident_id);
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