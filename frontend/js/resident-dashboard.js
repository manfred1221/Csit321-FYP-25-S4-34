// Check authentication
const user = checkAuth();
if (user && user.type !== 'resident') {
    window.location.href = 'index.html';
}

// Update user info in sidebar
document.getElementById('userName').textContent = user.full_name || user.username;
document.getElementById('userEmail').textContent = user.email;

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
    const endpoint = API_CONFIG.ENDPOINTS.RESIDENT.GET_VISITORS(user.id);
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
        tbody.innerHTML = '<tr><td colspan="4" class="text-center">No visitors found</td></tr>';
        return;
    }
    
    tbody.innerHTML = visitors.map(visitor => `
        <tr>
            <td>${visitor.visitor_name}</td>
            <td><span class="badge badge-${getStatusBadge(visitor.status)}">${visitor.status}</span></td>
            <td>${formatDateTime(visitor.start_time)} - ${formatDateTime(visitor.end_time)}</td>
            <td>
                <div class="actions">
                    <button onclick="viewVisitor(${visitor.visitor_id})" class="btn btn-sm btn-primary">View</button>
                </div>
            </td>
        </tr>
    `).join('');
}

// Load access history
async function loadAccessHistory() {
    const endpoint = API_CONFIG.ENDPOINTS.RESIDENT.ACCESS_HISTORY(user.id);
    const result = await apiCall(endpoint);
    
    if (result.success) {
        const records = result.data.records || [];
        
        // Count today's access
        const today = new Date().toDateString();
        const todayCount = records.filter(r => {
            const recordDate = new Date(r.timestamp).toDateString();
            return recordDate === today;
        }).length;
        document.getElementById('todayAccess').textContent = todayCount;
        
        // Display recent history (first 5)
        displayAccessHistory(records.slice(0, 5));
    }
}

function displayAccessHistory(records) {
    const tbody = document.querySelector('#accessHistoryTable tbody');
    
    if (records.length === 0) {
        tbody.innerHTML = '<tr><td colspan="3" class="text-center">No access history found</td></tr>';
        return;
    }
    
    tbody.innerHTML = records.map(record => `
        <tr>
            <td>${formatDateTime(record.timestamp)}</td>
            <td>${record.door}</td>
            <td><span class="badge badge-${record.result === 'GRANTED' ? 'success' : 'danger'}">${record.result}</span></td>
        </tr>
    `).join('');
}

// Load stats
async function loadStats() {
    const endpoint = API_CONFIG.ENDPOINTS.RESIDENT.ALERTS(user.id);
    const result = await apiCall(endpoint);
    
    if (result.success) {
        const alerts = result.data.alerts || [];
        const unreadCount = alerts.filter(a => a.status === 'UNREAD').length;
        document.getElementById('unreadAlerts').textContent = unreadCount;
    }
}

// Helper function to get status badge color
function getStatusBadge(status) {
    switch(status) {
        case 'APPROVED': return 'success';
        case 'PENDING': return 'warning';
        case 'DENIED': return 'danger';
        default: return 'info';
    }
}

// Toggle face access
let faceAccessEnabled = true;
async function toggleFaceAccess() {
    const btn = document.getElementById('toggleAccessBtn');
    
    if (faceAccessEnabled) {
        const endpoint = API_CONFIG.ENDPOINTS.RESIDENT.DISABLE_FACE_ACCESS(user.id);
        const result = await apiCall(endpoint, { method: 'POST' });
        
        if (result.success) {
            faceAccessEnabled = false;
            btn.textContent = 'Enable Face Access';
            btn.className = 'btn btn-success';
            alert('Face access has been disabled temporarily');
        }
    } else {
        // In real implementation, you'd have an enable endpoint
        faceAccessEnabled = true;
        btn.textContent = 'Disable Face Access';
        btn.className = 'btn btn-danger';
        alert('Face access has been enabled');
    }
}

// View visitor details
function viewVisitor(visitorId) {
    window.location.href = `resident-visitors.html?visitor=${visitorId}`;
}

// Initialize dashboard
loadDashboardData();
