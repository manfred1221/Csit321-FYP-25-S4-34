// Check authentication
const user = checkAuth();
if (user && user.type !== 'resident') {
    window.location.href = 'index.html';
}

// Update user info in sidebar
document.getElementById('userName').textContent = user.full_name || user.username;
document.getElementById('userEmail').textContent = user.email;

let allRecords = [];
let filteredRecords = [];

// Load access history on page load
loadAccessHistory();

async function loadAccessHistory() {
    const endpoint = API_CONFIG.ENDPOINTS.RESIDENT.ACCESS_HISTORY(user.id);
    const result = await apiCall(endpoint);
    
    if (result.success) {
        allRecords = result.data.records || [];
        filteredRecords = [...allRecords];
        displayRecords(filteredRecords);
        updateStatistics(filteredRecords);
    }
}

function displayRecords(records) {
    const tbody = document.querySelector('#accessHistoryTable tbody');
    
    if (records.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" class="text-center">No access records found</td></tr>';
        return;
    }
    
    tbody.innerHTML = records.map(record => `
        <tr>
            <td>${formatDateTime(record.timestamp)}</td>
            <td>${record.door || 'Unknown'}</td>
            <td><span class="badge badge-info">Face Recognition</span></td>
            <td><span class="badge badge-${record.result === 'GRANTED' ? 'success' : 'danger'}">${record.result}</span></td>
        </tr>
    `).join('');
}

function updateStatistics(records) {
    const totalAccesses = records.length;
    const grantedCount = records.filter(r => r.result === 'GRANTED').length;
    const deniedCount = records.filter(r => r.result === 'DENIED').length;
    
    // Count this month
    const now = new Date();
    const firstDayOfMonth = new Date(now.getFullYear(), now.getMonth(), 1);
    const monthCount = records.filter(r => {
        const recordDate = new Date(r.timestamp);
        return recordDate >= firstDayOfMonth;
    }).length;
    
    document.getElementById('totalAccesses').textContent = totalAccesses;
    document.getElementById('grantedCount').textContent = grantedCount;
    document.getElementById('deniedCount').textContent = deniedCount;
    document.getElementById('monthCount').textContent = monthCount;
}

function applyFilters() {
    const dateFrom = document.getElementById('dateFrom').value;
    const dateTo = document.getElementById('dateTo').value;
    const resultFilter = document.getElementById('resultFilter').value;
    
    filteredRecords = allRecords.filter(record => {
        const recordDate = new Date(record.timestamp);
        
        // Date from filter
        if (dateFrom) {
            const fromDate = new Date(dateFrom);
            if (recordDate < fromDate) return false;
        }
        
        // Date to filter
        if (dateTo) {
            const toDate = new Date(dateTo);
            toDate.setHours(23, 59, 59, 999); // End of day
            if (recordDate > toDate) return false;
        }
        
        // Result filter
        if (resultFilter && record.result !== resultFilter) return false;
        
        return true;
    });
    
    displayRecords(filteredRecords);
    updateStatistics(filteredRecords);
}

function exportHistory() {
    if (filteredRecords.length === 0) {
        alert('No records to export');
        return;
    }
    
    // Create CSV content
    let csvContent = "data:text/csv;charset=utf-8,";
    csvContent += "Date & Time,Location,Access Method,Result\n";
    
    filteredRecords.forEach(record => {
        const row = [
            formatDateTime(record.timestamp),
            record.door || 'Unknown',
            'Face Recognition',
            record.result
        ].join(',');
        csvContent += row + "\n";
    });
    
    // Create download link
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `access_history_${new Date().toISOString().split('T')[0]}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

// Set default date filters (last 30 days)
const today = new Date();
const thirtyDaysAgo = new Date(today.getTime() - 30 * 24 * 60 * 60 * 1000);
document.getElementById('dateTo').valueAsDate = today;
document.getElementById('dateFrom').valueAsDate = thirtyDaysAgo;
