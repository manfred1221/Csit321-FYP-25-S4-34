// Check authentication
const user = checkAuth();
if (user && user.type !== 'resident') {
    window.location.href = 'index.html';
}

// Update user info in sidebar
document.getElementById('userName').textContent = user.full_name || user.username;
document.getElementById('userEmail').textContent = user.email;

let allVisitors = [];
let currentVisitorId = null;
let videoStream = null;
let capturedImageData = null;

// Load visitors on page load
loadVisitors();

// Search functionality
document.getElementById('searchInput').addEventListener('input', (e) => {
    const searchTerm = e.target.value.toLowerCase();
    const filteredVisitors = allVisitors.filter(v => 
        v.visitor_name.toLowerCase().includes(searchTerm) ||
        v.contact_number.includes(searchTerm)
    );
    displayVisitors(filteredVisitors);
});

// Load all visitors
async function loadVisitors() {
    const endpoint = API_CONFIG.ENDPOINTS.RESIDENT.GET_VISITORS(user.id);
    const result = await apiCall(endpoint);
    
    if (result.success) {
        allVisitors = result.data.visitors || [];
        displayVisitors(allVisitors);
    }
}

// Display visitors in table
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

// Get status badge color
function getStatusBadge(status) {
    switch(status) {
        case 'APPROVED': return 'success';
        case 'PENDING': return 'warning';
        case 'DENIED': return 'danger';
        default: return 'info';
    }
}

// Open add visitor modal
function openAddVisitorModal() {
    document.getElementById('modalTitle').textContent = 'Add New Visitor';
    document.getElementById('visitorForm').reset();
    document.getElementById('visitorId').value = '';
    
    // Set default dates (today to tomorrow)
    const now = new Date();
    const tomorrow = new Date(now.getTime() + 24 * 60 * 60 * 1000);
    document.getElementById('startTime').value = formatDateForInput(now);
    document.getElementById('endTime').value = formatDateForInput(tomorrow);
    
    // Set default unit from user profile
    document.getElementById('visitingUnit').value = user.unit_number || '';
    
    document.getElementById('visitorModal').classList.add('active');
}

// Close visitor modal
function closeVisitorModal() {
    document.getElementById('visitorModal').classList.remove('active');
    document.getElementById('modalMessage').style.display = 'none';
}

// Edit visitor
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

// Save visitor (create or update)
async function saveVisitor() {
    const visitorId = document.getElementById('visitorId').value;
    const formData = {
        visitor_name: document.getElementById('visitorName').value,
        contact_number: document.getElementById('contactNumber').value,
        visiting_unit: document.getElementById('visitingUnit').value,
        start_time: document.getElementById('startTime').value,
        end_time: document.getElementById('endTime').value,
    };
    
    // Validate
    if (!formData.visitor_name || !formData.contact_number || !formData.visiting_unit || 
        !formData.start_time || !formData.end_time) {
        showMessage('modalMessage', 'Please fill in all required fields', 'error');
        return;
    }
    
    let result;
    if (visitorId) {
        // Update existing visitor
        const endpoint = API_CONFIG.ENDPOINTS.RESIDENT.UPDATE_VISITOR(user.id, visitorId);
        result = await apiCall(endpoint, {
            method: 'PUT',
            body: JSON.stringify(formData)
        });
    } else {
        // Create new visitor
        const endpoint = API_CONFIG.ENDPOINTS.RESIDENT.CREATE_VISITOR(user.id);
        result = await apiCall(endpoint, {
            method: 'POST',
            body: JSON.stringify(formData)
        });
    }
    
    if (result.success) {
        showMessage('modalMessage', 'Visitor saved successfully!', 'success');
        setTimeout(() => {
            closeVisitorModal();
            loadVisitors();
        }, 1500);
    } else {
        showMessage('modalMessage', 'Error saving visitor: ' + result.error, 'error');
    }
}

// Delete visitor
async function deleteVisitor(visitorId) {
    if (!confirm('Are you sure you want to delete this visitor?')) return;
    
    const endpoint = API_CONFIG.ENDPOINTS.RESIDENT.DELETE_VISITOR(user.id, visitorId);
    const result = await apiCall(endpoint, { method: 'DELETE' });
    
    if (result.success) {
        alert('Visitor deleted successfully!');
        loadVisitors();
    } else {
        alert('Error deleting visitor: ' + result.error);
    }
}

// Face Upload Modal Functions
let faceStream = null;

function openFaceUploadModal(visitorId) {
    currentVisitorId = visitorId;
    document.getElementById('faceVisitorId').value = visitorId;
    document.getElementById('faceUploadModal').classList.add('active');
    resetFaceUpload();
}

function closeFaceUploadModal() {
    stopFaceCamera();
    resetFaceUpload();
    document.getElementById('faceUploadModal').classList.remove('active');
}

function resetFaceUpload() {
    const video = document.getElementById('video');
    const preview = document.getElementById('capturedImage');
    const faceStatus = document.getElementById('faceStatus');
    const startBtn = document.getElementById('startCameraBtn');
    const captureBtn = document.getElementById('capturePhotoBtn');
    const uploadBtn = document.getElementById('uploadPhotoBtn');
    
    video.style.display = 'none';
    preview.style.display = 'none';
    
    startBtn.disabled = false;
    startBtn.textContent = 'Start Camera';
    captureBtn.disabled = true;
    uploadBtn.disabled = true;
    
    faceStatus.textContent = 'Ready to capture visitor\'s face';
    faceStatus.style.background = '#f3f4f6';
    faceStatus.style.color = '#111827';
    
    document.getElementById('faceModalMessage').style.display = 'none';
    
    stopFaceCamera();
}

function stopFaceCamera() {
    if (faceStream) {
        faceStream.getTracks().forEach(track => track.stop());
        faceStream = null;
    }
}

// Start Camera
document.getElementById('startCameraBtn').onclick = async () => {
    const video = document.getElementById('video');
    const preview = document.getElementById('capturedImage');
    const faceStatus = document.getElementById('faceStatus');
    const startBtn = document.getElementById('startCameraBtn');
    const captureBtn = document.getElementById('capturePhotoBtn');
    
    try {
        faceStream = await navigator.mediaDevices.getUserMedia({ 
            video: { 
                facingMode: "user",
                width: { ideal: 640 },
                height: { ideal: 480 }
            }, 
            audio: false 
        });
        
        video.srcObject = faceStream;
        video.style.display = 'block';
        preview.style.display = 'none';
        
        startBtn.disabled = true;
        captureBtn.disabled = false;
        
        faceStatus.textContent = "Camera started — position visitor's face in the frame";
        faceStatus.style.background = '#d1fae5';
        faceStatus.style.color = '#065f46';
        
    } catch (e) {
        console.error('Camera error:', e);
        faceStatus.textContent = "Cannot access camera: " + e.message;
        faceStatus.style.background = '#fee2e2';
        faceStatus.style.color = '#991b1b';
    }
};

// Capture Photo
document.getElementById('capturePhotoBtn').onclick = () => {
    const video = document.getElementById('video');
    const canvas = document.getElementById('canvas');
    const preview = document.getElementById('capturedImage');
    const faceStatus = document.getElementById('faceStatus');
    const startBtn = document.getElementById('startCameraBtn');
    const captureBtn = document.getElementById('capturePhotoBtn');
    const uploadBtn = document.getElementById('uploadPhotoBtn');
    
    const ctx = canvas.getContext('2d');
    
    // Set canvas size
    canvas.width = video.videoWidth || 640;
    canvas.height = video.videoHeight || 480;
    
    // Draw video frame to canvas
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    
    // Show preview
    preview.src = canvas.toDataURL('image/jpeg', 0.9);
    preview.style.display = 'block';
    
    // Hide video
    video.style.display = 'none';
    
    // Stop camera
    stopFaceCamera();
    
    // Update buttons
    startBtn.disabled = false;
    startBtn.textContent = '🔄 Retake Photo';
    captureBtn.disabled = true;
    uploadBtn.disabled = false;
    
    faceStatus.textContent = "Preview ready — click 'Upload Image' to save";
    faceStatus.style.background = '#dbeafe';
    faceStatus.style.color = '#1e40af';
};

// Upload Face Image
document.getElementById('uploadPhotoBtn').onclick = async () => {
    const canvas = document.getElementById('canvas');
    const visitorId = document.getElementById('faceVisitorId').value;
    const faceStatus = document.getElementById('faceStatus');
    const uploadBtn = document.getElementById('uploadPhotoBtn');
    
    if (!canvas.width || !canvas.height) {
        showMessage('faceModalMessage', 'Please capture an image first', 'error');
        return;
    }
    
    try {
        faceStatus.textContent = 'Uploading visitor face image...';
        faceStatus.style.background = '#fef3c7';
        faceStatus.style.color = '#92400e';
        
        uploadBtn.disabled = true;
        uploadBtn.innerHTML = '<span class="loading"></span> Uploading...';
        
        const imageData = canvas.toDataURL('image/jpeg', 0.9);
        const endpoint = API_CONFIG.ENDPOINTS.RESIDENT.UPLOAD_VISITOR_FACE(user.id, visitorId);
        
        const result = await apiCall(endpoint, {
            method: 'POST',
            body: JSON.stringify({
                image_data: imageData
            })
        });
        
        if (result.success) {
            faceStatus.textContent = '✅ Visitor face image uploaded successfully!';
            faceStatus.style.background = '#d1fae5';
            faceStatus.style.color = '#065f46';
            
            setTimeout(() => {
                closeFaceUploadModal();
            }, 1500);
        } else {
            throw new Error(result.error || 'Upload failed');
        }
        
    } catch (error) {
        console.error('Upload error:', error);
        faceStatus.textContent = '❌ Error uploading image: ' + error.message;
        faceStatus.style.background = '#fee2e2';
        faceStatus.style.color = '#991b1b';
        
        uploadBtn.disabled = false;
        uploadBtn.innerHTML = 'Upload Image';
    }
};

// View visitor access history
async function viewVisitorHistory(visitorId, visitorName) {
    document.getElementById('historyVisitorName').textContent = `Access History for ${visitorName}`;
    document.getElementById('accessHistoryModal').classList.add('active');
    
    const endpoint = API_CONFIG.ENDPOINTS.RESIDENT.VISITOR_ACCESS_HISTORY(user.id, visitorId);
    const result = await apiCall(endpoint);
    
    const tbody = document.querySelector('#visitorAccessHistoryTable tbody');
    
    if (result.success) {
        const records = result.data.records || [];
        
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
    } else {
        tbody.innerHTML = '<tr><td colspan="3" class="text-center">Error loading history</td></tr>';
    }
}

function closeAccessHistoryModal() {
    document.getElementById('accessHistoryModal').classList.remove('active');
}
