let currentUser = null;
let visitorData = null;

document.addEventListener('DOMContentLoaded', async () => {
    // 1. Verify Session
    currentUser = await checkAuth(); 
    
    if (!currentUser) return;

    // 2. Role Check
    if (currentUser.role !== 'Visitor') {
        window.location.href = '/login';
        return;
    }

    // 3. Update Sidebar UI
    const name = currentUser.full_name || currentUser.username;
    document.getElementById('visitorNameSidebar').textContent = name;
    document.getElementById('welcomeName').textContent = name;

    // 4. Initialize Data (Using session data + mock defaults if DB fields missing)
    // In a real scenario, you might fetch specific visit details from an API here
    visitorData = {
        visitor_name: name,
        visiting_unit: currentUser.unit_number || "Pending Assignment",
        contact_number: currentUser.phone || "N/A",
        // Defaulting to today 8am-8pm if no specific window found
        start_time: new Date().setHours(8,0,0), 
        end_time: new Date().setHours(20,0,0),
        status: currentUser.status === 'active' ? "APPROVED" : "PENDING",
        face_registered: !!currentUser.face_encoding_path // Convert to boolean
    };

    // 5. Render UI
    loadVisitorInfo();
    setupEventListeners();

    // 6. Auto-Refresh Status every minute
    setInterval(() => {
        if (visitorData) {
            displayVisitStatus(visitorData);
            displayFaceRecognitionStatus(visitorData);
        }
    }, 60000);
});

function setupEventListeners() {
    const logoutBtn = document.getElementById('logoutBtn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', async (e) => {
            e.preventDefault();
            if (confirm('Are you sure you want to logout?')) {
                await logout();
            }
        });
    }
}

function loadVisitorInfo() {
    if (!visitorData) return;
    displayVisitStatus(visitorData);
    displayVisitDetails(visitorData);
    displayFaceRecognitionStatus(visitorData);
}

function displayVisitStatus(visitor) {
    const statusDiv = document.getElementById('visitStatus');
    const now = new Date();
    const startTime = new Date(visitor.start_time);
    const endTime = new Date(visitor.end_time);
    
    let statusHTML = '';
    
    if (visitor.status === 'PENDING') {
        statusHTML = `
            <div class="status-large warning">PENDING APPROVAL</div>
            <p>Your visit request is waiting for resident approval.</p>`;
    } else if (visitor.status === 'DENIED') {
        statusHTML = `
            <div class="status-large danger">ACCESS DENIED</div>
            <p>Your visit request has been denied.</p>`;
    } else if (now < startTime) {
        const hoursUntil = Math.round((startTime - now) / (1000 * 60 * 60));
        statusHTML = `
            <div class="status-large info">SCHEDULED</div>
            <p>Your visit starts in ${hoursUntil} hours.</p>`;
    } else if (now >= startTime && now <= endTime) {
        statusHTML = `
            <div class="status-large success">ACTIVE ACCESS</div>
            <p>You have active access. You may enter.</p>`;
    } else {
        statusHTML = `
            <div class="status-large warning">EXPIRED</div>
            <p>Your visit window has closed.</p>`;
    }
    
    statusDiv.innerHTML = statusHTML;
}

function displayVisitDetails(visitor) {
    document.getElementById('visitorName').textContent = visitor.visitor_name;
    document.getElementById('visitingUnit').textContent = visitor.visiting_unit;
    
    // Format times
    const formatTime = (date) => new Date(date).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
    document.getElementById('visitWindow').textContent = `${formatTime(visitor.start_time)} - ${formatTime(visitor.end_time)}`;
    document.getElementById('contactNumber').textContent = visitor.contact_number;
}

function displayFaceRecognitionStatus(visitor) {
    const faceStatusDiv = document.getElementById('faceRecognitionStatus');
    const now = new Date();
    const startTime = new Date(visitor.start_time);
    const endTime = new Date(visitor.end_time);
    
    let html = '';
    
    if (!visitor.face_registered) {
        html = `
            <span class="icon-large">⚠️</span>
            <h3 style="color: #d97706; margin: 0;">Face Not Registered</h3>
            <p style="color: #64748b; margin-top: 10px;">Please contact security to register your face.</p>
        `;
    } else if (now >= startTime && now <= endTime && visitor.status === 'APPROVED') {
        html = `
            <span class="icon-large">😊</span>
            <h3 style="color: #10b981; margin: 0;">Ready for Access</h3>
            <p style="color: #64748b; margin-top: 10px;">Look at the camera to enter.</p>
        `;
    } else {
        html = `
            <span class="icon-large">⏳</span>
            <h3 style="color: #3b82f6; margin: 0;">Standby</h3>
            <p style="color: #64748b; margin-top: 10px;">Face recognition will activate during your visit window.</p>
        `;
    }
    
    faceStatusDiv.innerHTML = html;
}