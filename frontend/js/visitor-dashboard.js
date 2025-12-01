// Check authentication
const user = checkAuth();
if (user && user.type !== 'visitor') {
    window.location.href = 'index.html';
}

// Mock visitor data - In production, this would come from the backend
const mockVisitorData = {
    visitor_id: user.id,
    visitor_name: user.full_name || user.username,
    visiting_unit: "B-12-05",
    contact_number: "98765432",
    start_time: "2025-12-01T10:00:00",
    end_time: "2025-12-01T18:00:00",
    status: "APPROVED",
    face_registered: true  // Whether visitor's face photo has been uploaded
};

// Load visitor information
loadVisitorInfo();

function loadVisitorInfo() {
    displayVisitStatus(mockVisitorData);
    displayVisitDetails(mockVisitorData);
    displayFaceRecognitionStatus(mockVisitorData);
}

function displayVisitStatus(visitor) {
    const statusDiv = document.getElementById('visitStatus');
    const now = new Date();
    const startTime = new Date(visitor.start_time);
    const endTime = new Date(visitor.end_time);
    
    let statusHTML = '';
    let statusBadge = '';
    let statusMessage = '';
    
    if (visitor.status === 'PENDING') {
        statusBadge = '<span class="badge badge-warning" style="font-size: 18px; padding: 10px 20px;">PENDING APPROVAL</span>';
        statusMessage = 'Your visit request is pending approval from the resident.';
    } else if (visitor.status === 'DENIED') {
        statusBadge = '<span class="badge badge-danger" style="font-size: 18px; padding: 10px 20px;">ACCESS DENIED</span>';
        statusMessage = 'Your visit request has been denied. Please contact the resident.';
    } else if (now < startTime) {
        statusBadge = '<span class="badge badge-info" style="font-size: 18px; padding: 10px 20px;">SCHEDULED</span>';
        const hoursUntil = Math.round((startTime - now) / (1000 * 60 * 60));
        statusMessage = `Your visit starts in ${hoursUntil} hours. Please arrive on time.`;
    } else if (now >= startTime && now <= endTime) {
        statusBadge = '<span class="badge badge-success" style="font-size: 18px; padding: 10px 20px;">ACTIVE ACCESS</span>';
        statusMessage = 'You have active access. Show your QR code at the entrance.';
    } else {
        statusBadge = '<span class="badge badge-secondary" style="font-size: 18px; padding: 10px 20px;">EXPIRED</span>';
        statusMessage = 'Your visit window has expired. Please contact the resident for a new visit.';
    }
    
    statusHTML = `
        <div style="padding: 20px 0;">
            ${statusBadge}
            <p style="margin-top: 15px; color: var(--text-secondary);">${statusMessage}</p>
        </div>
    `;
    
    statusDiv.innerHTML = statusHTML;
}

function displayVisitDetails(visitor) {
    document.getElementById('visitorName').textContent = visitor.visitor_name;
    document.getElementById('visitingUnit').textContent = visitor.visiting_unit;
    document.getElementById('visitWindow').textContent = 
        `${formatDateTime(visitor.start_time)} to ${formatDateTime(visitor.end_time)}`;
    document.getElementById('contactNumber').textContent = visitor.contact_number;
}

function displayFaceRecognitionStatus(visitor) {
    const faceStatusDiv = document.getElementById('faceRecognitionStatus');
    
    let statusHTML = '';
    
    if (!visitor.face_registered) {
        // Face not registered
        statusHTML = `
            <div style="padding: 20px;">
                <div style="font-size: 64px; margin-bottom: 20px;">⚠️</div>
                <h3 style="color: var(--warning-color); margin-bottom: 15px;">Face Not Registered</h3>
                <p style="color: var(--text-secondary); margin-bottom: 20px;">
                    Your facial recognition data has not been uploaded yet.
                </p>
                <div class="alert alert-warning" style="text-align: left;">
                    <strong>What to do:</strong>
                    <ul style="margin-top: 10px; padding-left: 20px;">
                        <li>Contact the resident who invited you</li>
                        <li>Ask them to upload your facial photo via the Visitor Management page</li>
                        <li>Once uploaded, you'll be able to use facial recognition for access</li>
                    </ul>
                </div>
            </div>
        `;
    } else {
        // Face registered - check visit status
        const now = new Date();
        const startTime = new Date(visitor.start_time);
        const endTime = new Date(visitor.end_time);
        
        if (visitor.status === 'PENDING') {
            statusHTML = `
                <div style="padding: 20px;">
                    <div style="font-size: 64px; margin-bottom: 20px;">⏳</div>
                    <h3 style="color: var(--warning-color); margin-bottom: 15px;">Pending Approval</h3>
                    <p style="color: var(--text-secondary);">
                        Your visit is pending approval from the resident. Face recognition will be active once approved.
                    </p>
                </div>
            `;
        } else if (visitor.status === 'DENIED') {
            statusHTML = `
                <div style="padding: 20px;">
                    <div style="font-size: 64px; margin-bottom: 20px;">❌</div>
                    <h3 style="color: var(--danger-color); margin-bottom: 15px;">Access Denied</h3>
                    <p style="color: var(--text-secondary);">
                        Your visit request has been denied. Please contact the resident.
                    </p>
                </div>
            `;
        } else if (now < startTime) {
            const hoursUntil = Math.round((startTime - now) / (1000 * 60 * 60));
            statusHTML = `
                <div style="padding: 20px;">
                    <div style="font-size: 64px; margin-bottom: 20px;">✅</div>
                    <h3 style="color: var(--success-color); margin-bottom: 15px;">Face Recognition Ready</h3>
                    <p style="color: var(--text-secondary); margin-bottom: 15px;">
                        Your facial recognition is registered and ready to use.
                    </p>
                    <div class="alert alert-info" style="text-align: left;">
                        <strong>⏰ Visit starts in ${hoursUntil} hours</strong>
                        <p style="margin-top: 10px; margin-bottom: 0;">
                            You can access the building using facial recognition starting at ${formatDateTime(startTime)}.
                        </p>
                    </div>
                </div>
            `;
        } else if (now >= startTime && now <= endTime) {
            statusHTML = `
                <div style="padding: 20px;">
                    <div style="font-size: 64px; margin-bottom: 20px;">🎯</div>
                    <h3 style="color: var(--success-color); margin-bottom: 15px;">Access Active</h3>
                    <p style="color: var(--text-secondary); margin-bottom: 20px;">
                        Your facial recognition access is currently active!
                    </p>
                    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 12px;">
                        <h4 style="margin-bottom: 15px; font-size: 18px;">How to Access:</h4>
                        <ol style="text-align: left; padding-left: 20px; line-height: 1.8;">
                            <li>Approach the entrance camera</li>
                            <li>Look directly at the camera</li>
                            <li>Wait for recognition (2-3 seconds)</li>
                            <li>Door will unlock automatically upon successful recognition</li>
                        </ol>
                    </div>
                    <div style="margin-top: 20px; padding: 15px; background: #fef3c7; border-radius: 8px; border-left: 4px solid var(--warning-color);">
                        <strong>⏰ Access expires at ${formatDateTime(endTime)}</strong>
                    </div>
                </div>
            `;
        } else {
            statusHTML = `
                <div style="padding: 20px;">
                    <div style="font-size: 64px; margin-bottom: 20px;">⏰</div>
                    <h3 style="color: var(--text-secondary); margin-bottom: 15px;">Visit Expired</h3>
                    <p style="color: var(--text-secondary);">
                        Your visit window has expired. Contact the resident for a new visit registration.
                    </p>
                </div>
            `;
        }
    }
    
    faceStatusDiv.innerHTML = statusHTML;
}

// Refresh status every minute
setInterval(() => {
    displayVisitStatus(mockVisitorData);
    displayFaceRecognitionStatus(mockVisitorData);
}, 60000);
