// Check authentication
const user = checkAuth();
if (!user || user.type !== 'resident') {
    window.location.href = 'index.html';
}

// Update user info in sidebar
document.getElementById('userName').textContent = user.full_name || user.username;
document.getElementById('userEmail').textContent = user.email;

const video = document.getElementById('video');
const canvas = document.getElementById('canvas');
const preview = document.getElementById('preview');
const status = document.getElementById('status');
const startBtn = document.getElementById('startBtn');
const captureBtn = document.getElementById('captureBtn');
const uploadBtn = document.getElementById('uploadBtn');

let stream = null;

// Start camera
startBtn.onclick = async () => {
    try {
        stream = await navigator.mediaDevices.getUserMedia({ 
            video: { 
                facingMode: "user",
                width: { ideal: 640 },
                height: { ideal: 480 }
            }, 
            audio: false 
        });
        
        video.srcObject = stream;
        video.style.display = 'block';
        preview.style.display = 'none';
        
        captureBtn.disabled = false;
        uploadBtn.disabled = true;
        startBtn.disabled = true;
        
        status.textContent = "Camera started – position your face in the frame";
        status.style.background = '#d1fae5';
        status.style.color = '#065f46';
        
    } catch (e) {
        console.error('Camera error:', e);
        status.textContent = "Cannot access camera: " + e.message;
        status.style.background = '#fee2e2';
        status.style.color = '#991b1b';
    }
};

// Capture image from video
captureBtn.onclick = () => {
    const ctx = canvas.getContext('2d');
    
    // Set canvas size to match video
    canvas.width = video.videoWidth || 640;
    canvas.height = video.videoHeight || 480;
    
    // Draw video frame to canvas
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    
    // Convert to data URL
    const dataUrl = canvas.toDataURL('image/jpeg', 0.9);
    
    // Show preview
    preview.src = dataUrl;
    preview.style.display = 'block';
    
    // Hide video
    video.style.display = 'none';
    
    // Stop camera stream
    if (stream) {
        stream.getTracks().forEach(track => track.stop());
        stream = null;
    }
    
    // Update buttons
    captureBtn.disabled = true;
    uploadBtn.disabled = false;
    startBtn.disabled = false;
    startBtn.textContent = '🔄 Retake Photo';
    
    status.textContent = "Preview ready – click 'Register Face Data' to upload";
    status.style.background = '#dbeafe';
    status.style.color = '#1e40af';
};

// Upload face data to backend
uploadBtn.onclick = async () => {
    try {
        status.textContent = "Uploading face data...";
        status.style.background = '#fef3c7';
        status.style.color = '#92400e';
        
        uploadBtn.disabled = true;
        uploadBtn.innerHTML = '<span class="loading"></span> Uploading...';
        
        // Get image data from canvas
        const imageData = canvas.toDataURL('image/jpeg', 0.9);
        
        const endpoint = API_CONFIG.ENDPOINTS.RESIDENT.REGISTER_FACE;
        const result = await apiCall(endpoint, {
            method: 'POST',
            body: JSON.stringify({
                resident_id: user.resident_id,
                image_data: imageData
            })
        });
        
        if (result.success) {
            status.textContent = "✅ Face data registered successfully! You can now use facial recognition for access.";
            status.style.background = '#d1fae5';
            status.style.color = '#065f46';
            
            // Update registration status
            document.getElementById('registrationStatus').innerHTML = `
                <p>Current Status: <span class="badge badge-success">Registered</span></p>
                <p>Last Updated: <span id="lastUpdated">${new Date().toLocaleString()}</span></p>
            `;
            
            // Reset after 3 seconds
            setTimeout(() => {
                preview.style.display = 'none';
                startBtn.textContent = 'Start Camera';
                startBtn.disabled = false;
                uploadBtn.disabled = true;
                uploadBtn.innerHTML = '✅ Register Face Data';
                status.textContent = "Ready to capture your face";
                status.style.background = '#f3f4f6';
                status.style.color = '#111827';
            }, 3000);
            
        } else {
            throw new Error(result.error || 'Upload failed');
        }
        
    } catch (error) {
        console.error('Upload error:', error);
        status.textContent = "❌ Error uploading face data: " + error.message;
        status.style.background = '#fee2e2';
        status.style.color = '#991b1b';
        
        uploadBtn.disabled = false;
        uploadBtn.innerHTML = '✅ Register Face Data';
    }
};

// Clean up on page unload
window.addEventListener('beforeunload', () => {
    if (stream) {
        stream.getTracks().forEach(track => track.stop());
    }
});