// Security Dashboard JavaScript

// Check if user is logged in and is security officer
const user = JSON.parse(localStorage.getItem('user') || '{}');
if (!user.username || user.user_type !== 'SECURITY') {
    window.location.href = 'index.html';
}

// Display user info
document.getElementById('userName').textContent = user.full_name || 'Security Officer';
document.getElementById('userEmail').textContent = user.email || 'security@example.com';

// API helper function
async function apiCall(endpoint, options = {}) {
    try {
        const response = await fetch(`${API_CONFIG.BASE_URL}${endpoint}`, {
            ...options,
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            }
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        return await response.json();
    } catch (error) {
        console.error('API call failed:', error);
        throw error;
    }
}

// Load dashboard data
async function loadDashboardData() {
    try {
        // Load statistics
        await loadStatistics();
        
        // Load recent activity
        await loadRecentActivity();
        
        // Load current visitors
        await loadCurrentVisitors();
    } catch (error) {
        console.error('Failed to load dashboard:', error);
        showError('Failed to load dashboard data');
    }
}

// Load statistics
async function loadStatistics() {
    try {
        const stats = await apiCall('/api/security/statistics');
        
        document.getElementById('totalResidents').textContent = stats.total_residents || 0;
        document.getElementById('activeVisitors').textContent = stats.active_visitors || 0;
        document.getElementById('todayAccess').textContent = stats.today_access_count || 0;
        document.getElementById('alertsToday').textContent = stats.alerts_today || 0;
    } catch (error) {
        console.error('Failed to load statistics:', error);
    }
}

// Load recent access activity
async function loadRecentActivity() {
    try {
        const activity = await apiCall('/api/security/recent-access?limit=10');
        
        const tbody = document.getElementById('recentActivityTable');
        
        if (!activity || activity.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" class="text-center">No recent activity</td></tr>';
            return;
        }
        
        tbody.innerHTML = activity.map(log => `
            <tr>
                <td>${formatTime(log.access_time)}</td>
                <td>${log.person_name}</td>
                <td><span class="badge ${log.person_type === 'RESIDENT' ? 'badge-primary' : 'badge-secondary'}">${log.person_type}</span></td>
                <td>${log.access_point}</td>
                <td><span class="badge ${log.access_result === 'GRANTED' ? 'badge-success' : 'badge-danger'}">${log.access_result}</span></td>
                <td>
                    <button class="btn btn-sm btn-secondary" onclick="viewDetails(${log.log_id})">
                        View
                    </button>
                </td>
            </tr>
        `).join('');
    } catch (error) {
        console.error('Failed to load activity:', error);
        document.getElementById('recentActivityTable').innerHTML = 
            '<tr><td colspan="6" class="text-center text-error">Failed to load activity</td></tr>';
    }
}

// Load current visitors in building
async function loadCurrentVisitors() {
    try {
        const visitors = await apiCall('/api/security/current-visitors');
        
        const tbody = document.getElementById('currentVisitorsTable');
        const countBadge = document.getElementById('visitorCount');
        
        countBadge.textContent = visitors.length;
        
        if (!visitors || visitors.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" class="text-center">No visitors currently in building</td></tr>';
            return;
        }
        
        tbody.innerHTML = visitors.map(visitor => `
            <tr>
                <td>${visitor.visitor_name}</td>
                <td>${visitor.visiting_unit}</td>
                <td>${formatTime(visitor.entry_time)}</td>
                <td>${formatTime(visitor.expected_exit)}</td>
                <td><span class="badge badge-success">IN BUILDING</span></td>
            </tr>
        `).join('');
    } catch (error) {
        console.error('Failed to load visitors:', error);
        document.getElementById('currentVisitorsTable').innerHTML = 
            '<tr><td colspan="5" class="text-center text-error">Failed to load visitors</td></tr>';
    }
}

// Refresh activity
async function refreshActivity() {
    const btn = event.target;
    btn.disabled = true;
    btn.textContent = '🔄 Refreshing...';
    
    try {
        await loadDashboardData();
        btn.textContent = '✅ Refreshed!';
        setTimeout(() => {
            btn.textContent = '🔄 Refresh';
            btn.disabled = false;
        }, 2000);
    } catch (error) {
        btn.textContent = '❌ Failed';
        setTimeout(() => {
            btn.textContent = '🔄 Refresh';
            btn.disabled = false;
        }, 2000);
    }
}

// View access log details
function viewDetails(logId) {
    window.location.href = `security-access-logs.html?log_id=${logId}`;
}

// Export today's report
async function exportReport() {
    try {
        const btn = event.target;
        btn.disabled = true;
        btn.textContent = '📄 Generating...';
        
        const report = await apiCall('/api/security/export-report');
        
        // Create CSV
        const csv = generateCSV(report);
        const blob = new Blob([csv], { type: 'text/csv' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `security-report-${new Date().toISOString().split('T')[0]}.csv`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
        
        btn.textContent = '✅ Downloaded!';
        setTimeout(() => {
            btn.textContent = '📄 Export Today\'s Report';
            btn.disabled = false;
        }, 2000);
    } catch (error) {
        console.error('Export failed:', error);
        alert('Failed to export report');
        event.target.disabled = false;
        event.target.textContent = '📄 Export Today\'s Report';
    }
}

// Generate CSV from report data
function generateCSV(data) {
    const headers = ['Time', 'Name', 'Type', 'Location', 'Result'];
    const rows = data.map(row => [
        row.access_time,
        row.person_name,
        row.person_type,
        row.access_point,
        row.access_result
    ]);
    
    const csvContent = [
        headers.join(','),
        ...rows.map(row => row.join(','))
    ].join('\n');
    
    return csvContent;
}

// Helper: Format time
function formatTime(timestamp) {
    if (!timestamp) return 'N/A';
    const date = new Date(timestamp);
    return date.toLocaleString('en-SG', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// Helper: Show error message
function showError(message) {
    // You can implement a toast notification here
    console.error(message);
}

// Auto-refresh every 30 seconds
setInterval(loadDashboardData, 30000);

// Initial load
loadDashboardData();
