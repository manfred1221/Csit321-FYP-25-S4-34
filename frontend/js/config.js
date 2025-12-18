// API Configuration - Uses relative URLs to work on any network
// This allows the app to work regardless of which network you're connected to
//const API_BASE = '';  // Empty string means relative URLs
const API_BASE = 'http://127.0.0.1:5001';  // Correct port!
const API_CONFIG = {
    BASE_URL: API_BASE,
    STAFF_BASE_URL: API_BASE, 
    ENDPOINTS: {
        // Auth endpoints (you'll need to add these to your backend)
        LOGIN: '/api/auth/login',
        LOGOUT: '/api/auth/logout',
        REGISTER: '/api/auth/register',
        
        // Resident endpoints
        RESIDENT: {
            REGISTER_FACE: '/api/resident/register-face',
            GET_PROFILE: (residentId) => `/api/resident/${residentId}`,
            UPDATE_PROFILE: (residentId) => `/api/resident/${residentId}`,
            DELETE_PROFILE: (residentId) => `/api/resident/${residentId}`,
            ACCESS_HISTORY: (residentId) => `/api/resident/${residentId}/access-history`,
            ALERTS: (residentId) => `/api/resident/${residentId}/alerts`,
            DISABLE_FACE_ACCESS: (residentId) => `/api/resident/${residentId}/face-access/disable`,
            
            // Visitor management
            CREATE_VISITOR: (residentId) => `/api/resident/${residentId}/visitors`,
            GET_VISITORS: (residentId) => `/api/resident/${residentId}/visitors`,
            UPDATE_VISITOR: (residentId, visitorId) => `/api/resident/${residentId}/visitors/${visitorId}`,
            DELETE_VISITOR: (residentId, visitorId) => `/api/resident/${residentId}/visitors/${visitorId}`,
            SET_VISITOR_TIME: (residentId, visitorId) => `/api/resident/${residentId}/visitors/${visitorId}/time-window`,
            UPLOAD_VISITOR_FACE: (residentId, visitorId) => `/api/resident/${residentId}/visitors/${visitorId}/face-image`,
            VISITOR_ACCESS_HISTORY: (residentId, visitorId) => `/api/resident/${residentId}/visitors/${visitorId}/access-history`,
        },
        
        // Visitor endpoints  
        VISITOR: {
            CHECK_IN: '/api/visitor/check-in',
            CHECK_OUT: '/api/visitor/check-out',
            GET_STATUS: (visitorId) => `/api/visitor/${visitorId}/status`,
        },
        
        // Staff endpoints
        STAFF: {
            LOGIN: '/api/staff/login',
            LOGOUT: '/api/staff/logout',
            GET_PROFILE: (staffId) => `/api/staff/${staffId}/profile`,
            UPDATE_PROFILE: (staffId) => `/api/staff/${staffId}/profile`,
            DELETE_ACCOUNT: (staffId) => `/api/staff/${staffId}`,
            GET_SCHEDULE: (staffId) => `/api/staff/${staffId}/schedule`,
            RECORD_ATTENDANCE: '/api/staff/attendance/record',
            GET_ATTENDANCE: (staffId) => `/api/staff/${staffId}/attendance`,
            GET_TOTAL_HOURS: (staffId) => `/api/staff/${staffId}/total-hours`,
        },

        // Offline recognition
        OFFLINE_RECOGNIZE: '/api/resident/offline/recognize',
    }
};

// Helper function to make API calls
async function apiCall(endpoint, options = {}, useStaffBackend = false) {
    // Use staff backend if specified 
    const baseUrl = useStaffBackend ? API_CONFIG.STAFF_BASE_URL : API_CONFIG.BASE_URL;
    const url = `${baseUrl}${endpoint}`;
    
    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json',
        },
    };
    
    // Add auth token if exists
    const token = localStorage.getItem('auth_token');
    if (token) {
        defaultOptions.headers['Authorization'] = `Bearer ${token}`;
    }
    
    const finalOptions = {
        ...defaultOptions,
        ...options,
        headers: {
            ...defaultOptions.headers,
            ...options.headers,
        },
    };
    
    try {
        const response = await fetch(url, finalOptions);
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'API call failed');
        }
        
        return { success: true, data };
    } catch (error) {
        console.error('API Error:', error);
        return { success: false, error: error.message };
    }
}


// Helper function to show messages
function showMessage(elementId, message, type = 'success') {
    const messageEl = document.getElementById(elementId);
    if (messageEl) {
        messageEl.textContent = message;
        messageEl.className = `message ${type}`;
        messageEl.style.display = 'block';
        
        // Auto hide after 5 seconds
        setTimeout(() => {
            messageEl.style.display = 'none';
        }, 5000);
    }
}
// Helper function for staff API calls 
async function staffApiCall(endpoint, options = {}) {
    return apiCall(endpoint, options, true); // Use staff backend
}
// Helper function to format date/time
function formatDateTime(dateString) {
    const date = new Date(dateString);
    return date.toLocaleString();
}

// Helper function to format date for input
function formatDateForInput(dateString) {
    const date = new Date(dateString);
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');
    return `${year}-${month}-${day}T${hours}:${minutes}`;
}

// Check if user is logged in
function checkAuth() {
    const user = JSON.parse(localStorage.getItem('user') || 'null');
    if (!user) {
        window.location.href = 'index.html';
        return null;
    }
    return user;
}

// Logout function
function logout() {
    localStorage.removeItem('user');
    localStorage.removeItem('auth_token');
    window.location.href = 'index.html';
}