// Check authentication
let user = null;

document.addEventListener('DOMContentLoaded', async () => {
    user = await checkAuth(); 
    
    if (!user) return; 

    if (user.role !== 'Resident') {
        window.location.href = '/login';
        return;
    }

    // Initialize UI
    document.getElementById('userName').textContent = user.full_name || user.username;
    const emailEl = document.getElementById('userEmail');
    if (emailEl) emailEl.textContent = user.email || (user.username + '@condo.com');

    // 1. Initial load
    loadAlerts(); 

    // 2. Set the interval ONCE here, outside the loadAlerts function
    setInterval(() => {
        if (user) loadAlerts();
    }, 30000);
});

async function loadAlerts() {
    // Ensure we use resident_id from the authenticated user
    const residentId = user.resident_id || user.user_id; 
    const endpoint = API_CONFIG.ENDPOINTS.RESIDENT.ALERTS(residentId);
    const result = await apiCall(endpoint);
    
    if (result.success) {
        allAlerts = result.data.alerts || [];
        displayAlerts(allAlerts);
        updateUnreadCount();
    }
}

function displayAlerts(alerts) {
    const alertsList = document.getElementById('alertsList');
    const emptyState = document.getElementById('emptyState');
    
    if (alerts.length === 0) {
        alertsList.innerHTML = '';
        emptyState.style.display = 'block';
        return;
    }
    
    emptyState.style.display = 'none';
    alertsList.innerHTML = alerts.map(alert => `
        <div class="card ${alert.status === 'UNREAD' ? 'alert-unread' : ''}" style="margin-bottom: 15px; ${alert.status === 'UNREAD' ? 'border-left: 4px solid var(--danger-color);' : ''}">
            <div class="card-body">
                <div class="flex justify-between items-center">
                    <div style="flex: 1;">
                        <div class="flex items-center gap-10">
                            <span style="font-size: 24px;">⚠️</span>
                            <div>
                                <h3 style="margin-bottom: 5px; font-size: 16px;">
                                    ${alert.status === 'UNREAD' ? '<strong>' : ''}
                                    ${alert.description || 'Security Alert'}
                                    ${alert.status === 'UNREAD' ? '</strong>' : ''}
                                </h3>
                                <p style="color: var(--text-secondary); font-size: 14px; margin: 0;">
                                    ${formatDateTime(alert.timestamp)}
                                </p>
                            </div>
                        </div>
                    </div>
                    <div>
                        ${alert.status === 'UNREAD' 
                            ? `<button class="btn btn-sm btn-primary" onclick="markAsRead(${alert.alert_id})">Mark as Read</button>`
                            : `<span class="badge badge-success">Read</span>`
                        }
                    </div>
                </div>
            </div>
        </div>
    `).join('');
}

function updateUnreadCount() {
    const unreadCount = allAlerts.filter(a => a.status === 'UNREAD').length;
    document.getElementById('unreadCount').textContent = `${unreadCount} Unread`;
}

function markAsRead(alertId) {
    // In real implementation, you'd call an API to mark as read
    const alert = allAlerts.find(a => a.alert_id === alertId);
    if (alert) {
        alert.status = 'READ';
        displayAlerts(allAlerts);
        updateUnreadCount();
    }
}

function markAllAsRead() {
    if (!confirm('Mark all alerts as read?')) return;
    
    // In real implementation, you'd call an API
    allAlerts.forEach(alert => {
        alert.status = 'READ';
    });
    
    displayAlerts(allAlerts);
    updateUnreadCount();
}

function clearReadAlerts() {
    if (!confirm('Delete all read alerts? This cannot be undone.')) return;
    
    allAlerts = allAlerts.filter(a => a.status === 'UNREAD');
    displayAlerts(allAlerts);
    updateUnreadCount();
}
