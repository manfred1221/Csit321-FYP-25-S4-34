// API Configuration - Uses relative URLs to work on any environment
// Empty string means "same origin" (localhost or Render)
const API_BASE = '';

const API_CONFIG = {
    BASE_URL: API_BASE,
    STAFF_BASE_URL: API_BASE,
    ENDPOINTS: {
        // Auth endpoints
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
            UPDATE_VISITOR: (residentId, visitorId) =>
                `/api/resident/${residentId}/visitors/${visitorId}`,
            DELETE_VISITOR: (residentId, visitorId) =>
                `/api/resident/${residentId}/visitors/${visitorId}`,
            SET_VISITOR_TIME: (residentId, visitorId) =>
                `/api/resident/${residentId}/visitors/${visitorId}/time-window`,
            UPLOAD_VISITOR_FACE: (residentId, visitorId) =>
                `/api/resident/${residentId}/visitors/${visitorId}/face-image`,
            VISITOR_ACCESS_HISTORY: (residentId, visitorId) =>
                `/api/resident/${residentId}/visitors/${visitorId}/access-history`,
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

// ==============================
// Generic API helper
// ==============================
async function apiCall(endpoint, options = {}, useStaffBackend = false) {
    const baseUrl = useStaffBackend
        ? API_CONFIG.STAFF_BASE_URL
        : API_CONFIG.BASE_URL;

    const url = `${baseUrl}${endpoint}`;

    const defaultOptions = {
        credentials: 'include', // ✅ IMPORTANT for Flask session cookies
        headers: {
            'Content-Type': 'application/json',
        },
    };

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

// ==============================
// Helpers
// ==============================
function showMessage(elementId, message, type = 'success') {
    const el = document.getElementById(elementId);
    if (!el) return;

    el.textContent = message;
    el.className = `message ${type}`;
    el.style.display = 'block';

    setTimeout(() => {
        el.style.display = 'none';
    }, 5000);
}

async function staffApiCall(endpoint, options = {}) {
    return apiCall(endpoint, options, true);
}

function formatDateTime(dateString) {
    return new Date(dateString).toLocaleString();
}

function formatDateForInput(dateString) {
    const d = new Date(dateString);
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(
        d.getDate()
    ).padStart(2, '0')}T${String(d.getHours()).padStart(2, '0')}:${String(
        d.getMinutes()
    ).padStart(2, '0')}`;
}

// ==============================
// Auth helpers (Flask session based)
// ==============================
async function checkAuth() {
    try {
        const response = await fetch('/api/auth/check-session', {
            method: 'GET',
            credentials: 'include',
        });

        const data = await response.json();

        if (!data.authenticated) {
            window.location.href = '/login';
            return null;
        }

        return data.user;
    } catch (error) {
        console.error('Auth check failed:', error);
        window.location.href = '/login';
        return null;
    }
}

async function logout() {
    try {
        await fetch('/api/auth/logout', {
            method: 'POST',
            credentials: 'include',
        });
    } catch (error) {
        console.error('Logout error:', error);
    }

    window.location.href = '/login';
}
