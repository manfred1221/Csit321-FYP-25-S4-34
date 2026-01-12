// Global user variable
let user = null;
let allVisitors = [];
let currentVisitorId = null;
let faceStream = null;

document.addEventListener('DOMContentLoaded', async () => {
    // 1. Verify user via Flask session
    user = await checkAuth(); 
    
    if (!user) return; 

    // 2. Role Authorization
    if (user.role !== 'Resident') {
        window.location.href = '/login';
        return;
    }

    // 3. Initialize Sidebar UI
    document.getElementById('userName').textContent = user.full_name || user.username;
    const emailEl = document.getElementById('userEmail');
    if (emailEl) emailEl.textContent = user.email || (user.username + '@condo.com');

    // 4. Setup Search Listener (Moved inside to ensure DOM is ready)
    document.getElementById('searchInput').addEventListener('input', (e) => {
        const searchTerm = e.target.value.toLowerCase();
        const filteredVisitors = allVisitors.filter(v => 
            v.visitor_name.toLowerCase().includes(searchTerm) ||
            v.contact_number.includes(searchTerm)
        );
        displayVisitors(filteredVisitors);
    });

    // 5. Initial Data Load
    loadVisitors(); 
});

// --- Core Data Functions ---

async function loadVisitors() {
    // Use resident_id with a fallback to user_id for API routes
    const residentId = user.resident_id || user.user_id;
    const endpoint = API_CONFIG.ENDPOINTS.RESIDENT.GET_VISITORS(residentId);
    const result = await apiCall(endpoint);
    
    if (result.success) {
        allVisitors = result.data.visitors || [];
        displayVisitors(allVisitors);
    }
}

function displayVisitors(visitors) {
    const tbody = document.querySelector('#visitorsTable tbody');
    
    if (visitors.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="text-center">No visitors found</td></tr>';
        return;
    }
    
    tbody.innerHTML = visitors.map(visitor => `
        <tr>
            <td>${visitor.visitor_name}</td>
            <td>${visitor.contact_number || 'N/A'}</td>
            <td><span class="badge badge-${getStatusBadge(visitor.status)}">${visitor.status}</span></td>
            <td>
                ${formatDateTime(visitor.start_time)}<br>
                <small>to ${formatDateTime(visitor.end_time)}</small>
            </td>
            <td>
                <div class="actions">
                    <button onclick="editVisitor(${visitor.visitor_id})" class="btn btn-sm btn-primary">Edit</button>
                    <button onclick="openFaceUploadModal(${visitor.visitor_id})" class="btn btn-sm btn-success">Face</button>
                    <button onclick="viewVisitorHistory(${visitor.visitor_id}, '${visitor.visitor_name}')" class="btn btn-sm btn-secondary">History</button>
                    <button onclick="deleteVisitor(${visitor.visitor_id})" class="btn btn-sm btn-danger">Delete</button>
                </div>
            </td>
        </tr>
    `).join('');
}

function getStatusBadge(status) {
    switch(status) {
        case 'APPROVED': return 'success';
        case 'PENDING': return 'warning';
        case 'DENIED': return 'danger';
        default: return 'info';
    }
}

// --- Modal & Form Functions ---

function openAddVisitorModal() {
    document.getElementById('modalTitle').textContent = 'Add New Visitor';
    document.getElementById('visitorForm').reset();
    document.getElementById('visitorId').value = '';
    
    const now = new Date();
    const tomorrow = new Date(now.getTime() + 24 * 60 * 60 * 1000);
    document.getElementById('startTime').value = formatDateForInput(now);
    document.getElementById('endTime').value = formatDateForInput(tomorrow);
    
    // Set default unit from user context
    document.getElementById('visitingUnit').value = user.unit_number || '';
    document.getElementById('visitorModal').classList.add('active');
}

function closeVisitorModal() {
    document.getElementById('visitorModal').classList.remove('active');
    document.getElementById('modalMessage').style.display = 'none';
}

function editVisitor(visitorId) {
    const visitor = allVisitors.find(v => v.visitor_id === visitorId);
    if (!visitor) return;
    
    document.getElementById('modalTitle').textContent = 'Edit Visitor';
    document.getElementById('visitorId').value = visitor.visitor_id;
    document.getElementById('visitorName').value = visitor.visitor_name;
    document.getElementById('contactNumber').value = visitor.contact_number || '';
    document.getElementById('visitingUnit').value = visitor.visiting_unit || '';
    document.getElementById('startTime').value = formatDateForInput(visitor.start_time);
    document.getElementById('endTime').value = formatDateForInput(visitor.end_time);
    
    document.getElementById('visitorModal').classList.add('active');
}

async function saveVisitor() {
    const visitorId = document.getElementById('visitorId').value;
    const resId = user.resident_id || user.user_id; //

    const formData = {
        visitor_name: document.getElementById('visitorName').value,
        contact_number: document.getElementById('contactNumber').value,
        visiting_unit: document.getElementById('visitingUnit').value,
        start_time: document.getElementById('startTime').value,
        end_time: document.getElementById('endTime').value,
    };
    
    if (!formData.visitor_name || !formData.contact_number || !formData.visiting_unit) {
        showMessage('modalMessage', 'Please fill in all required fields', 'error');
        return;
    }
    
    const endpoint = visitorId ? 
        API_CONFIG.ENDPOINTS.RESIDENT.UPDATE_VISITOR(resId, visitorId) : 
        API_CONFIG.ENDPOINTS.RESIDENT.CREATE_VISITOR(resId);
    
    const result = await apiCall(endpoint, {
        method: visitorId ? 'PUT' : 'POST',
        body: JSON.stringify(formData)
    });
    
    if (result.success) {
        showMessage('modalMessage', 'Visitor saved!', 'success');
        setTimeout(() => { closeVisitorModal(); loadVisitors(); }, 1500);
    } else {
        showMessage('modalMessage', 'Error: ' + result.error, 'error');
    }
}

async function deleteVisitor(visitorId) {
    if (!confirm('Delete this visitor?')) return;
    const resId = user.resident_id || user.user_id;
    const endpoint = API_CONFIG.ENDPOINTS.RESIDENT.DELETE_VISITOR(resId, visitorId);
    const result = await apiCall(endpoint, { method: 'DELETE' });
    
    if (result.success) {
        loadVisitors();
    } else {
        alert('Error: ' + result.error);
    }
}

// --- Face Registration Functions ---

function openFaceUploadModal(visitorId) {
    currentVisitorId = visitorId;
    document.getElementById('faceVisitorId').value = visitorId;
    document.getElementById('faceUploadModal').classList.add('active');
    resetFaceUpload();
}

function closeFaceUploadModal() {
    stopFaceCamera();
    document.getElementById('faceUploadModal').classList.remove('active');
}

function stopFaceCamera() {
    if (faceStream) {
        faceStream.getTracks().forEach(track => track.stop());
        faceStream = null;
    }
}

function resetFaceUpload() {
    document.getElementById('video').style.display = 'none';
    document.getElementById('capturedImage').style.display = 'none';
    document.getElementById('startCameraBtn').disabled = false;
    document.getElementById('capturePhotoBtn').disabled = true;
    document.getElementById('uploadPhotoBtn').disabled = true;
    document.getElementById('faceStatus').textContent = 'Ready to capture face';
}

document.getElementById('startCameraBtn').onclick = async () => {
    try {
        faceStream = await navigator.mediaDevices.getUserMedia({ video: true });
        const video = document.getElementById('video');
        video.srcObject = faceStream;
        video.style.display = 'block';
        document.getElementById('startCameraBtn').disabled = true;
        document.getElementById('capturePhotoBtn').disabled = false;
    } catch (e) {
        alert("Camera access denied: " + e.message);
    }
};

document.getElementById('capturePhotoBtn').onclick = () => {
    const video = document.getElementById('video');
    const canvas = document.getElementById('canvas');
    const preview = document.getElementById('capturedImage');
    
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext('2d').drawImage(video, 0, 0);
    
    preview.src = canvas.toDataURL('image/jpeg');
    preview.style.display = 'block';
    video.style.display = 'none';
    
    stopFaceCamera();
    document.getElementById('capturePhotoBtn').disabled = true;
    document.getElementById('uploadPhotoBtn').disabled = false;
    document.getElementById('startCameraBtn').disabled = false;
};

document.getElementById('uploadPhotoBtn').onclick = async () => {
    const resId = user.resident_id || user.user_id;
    const visitorId = document.getElementById('faceVisitorId').value;
    const canvas = document.getElementById('canvas');
    const imageData = canvas.toDataURL('image/jpeg');
    
    const endpoint = API_CONFIG.ENDPOINTS.RESIDENT.UPLOAD_VISITOR_FACE(resId, visitorId);
    const result = await apiCall(endpoint, {
        method: 'POST',
        body: JSON.stringify({ image_data: imageData })
    });
    
    if (result.success) {
        showMessage('faceModalMessage', 'Face uploaded successfully!', 'success');
        setTimeout(closeFaceUploadModal, 1500);
    } else {
        showMessage('faceModalMessage', 'Upload failed: ' + result.error, 'error');
    }
};

async function viewVisitorHistory(visitorId, visitorName) {
    document.getElementById('historyVisitorName').textContent = `History for ${visitorName}`;
    document.getElementById('accessHistoryModal').classList.add('active');
    
    const resId = user.resident_id || user.user_id;
    const endpoint = API_CONFIG.ENDPOINTS.RESIDENT.VISITOR_ACCESS_HISTORY(resId, visitorId);
    const result = await apiCall(endpoint);
    
    const tbody = document.querySelector('#visitorAccessHistoryTable tbody');
    if (result.success) {
        const records = result.data.records || [];
        tbody.innerHTML = records.length ? records.map(r => `
            <tr>
                <td>${formatDateTime(r.timestamp)}</td>
                <td>${r.door}</td>
                <td><span class="badge badge-${r.result === 'GRANTED' ? 'success' : 'danger'}">${r.result}</span></td>
            </tr>
        `).join('') : '<tr><td colspan="3">No history found</td></tr>';
    }
}