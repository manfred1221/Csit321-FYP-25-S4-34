// Check authentication
let user = null;

document.addEventListener('DOMContentLoaded', async () => {
    // Use the async server-side check you wrote in config.js
    user = await checkAuth(); 
    
    if (!user) return; // checkAuth already redirects to /login if null

    if (user.role !== 'Resident') {
        window.location.href = '/login';
        return;
    }

    // Initialize the page once user is confirmed
    document.getElementById('userName').textContent = user.full_name || user.username;
    const emailEl = document.getElementById('userEmail');
    if (emailEl) emailEl.textContent = user.email || (user.username + '@condo.com');

    loadProfile();
});

// Update user info in sidebar
// document.getElementById('userName').textContent = user.full_name || user.username;
// document.getElementById('userEmail').textContent = user.email;

let originalProfileData = {};
let isEditing = false;

// Load profile data on page load
// loadProfile();

async function loadProfile() {
    const endpoint = API_CONFIG.ENDPOINTS.RESIDENT.GET_PROFILE(user.resident_id);
    const result = await apiCall(endpoint);
    
    if (result.success) {
        const profile = result.data;
        originalProfileData = { ...profile };
        
        document.getElementById('fullName').value = profile.full_name || '';
        document.getElementById('unitNumber').value = profile.unit_number || '';
        document.getElementById('contactNumber').value = profile.contact_number || '';
        document.getElementById('email').value = profile.email || '';
    }
}

function toggleEdit() {
    isEditing = !isEditing;
    const formInputs = document.querySelectorAll('#profileForm input');
    const editBtn = document.getElementById('editBtn');
    const editActions = document.getElementById('editActions');
    
    if (isEditing) {
        formInputs.forEach(input => input.disabled = false);
        editBtn.style.display = 'none';
        editActions.style.display = 'block';
    } else {
        formInputs.forEach(input => input.disabled = true);
        editBtn.style.display = 'block';
        editActions.style.display = 'none';
    }
}

function cancelEdit() {
    // Restore original values
    document.getElementById('fullName').value = originalProfileData.full_name || '';
    document.getElementById('unitNumber').value = originalProfileData.unit_number || '';
    document.getElementById('contactNumber').value = originalProfileData.contact_number || '';
    document.getElementById('email').value = originalProfileData.email || '';
    
    toggleEdit();
    document.getElementById('message').style.display = 'none';
}

async function saveProfile() {
    // 1. Collect data from the form
    const formData = {
        full_name: document.getElementById('fullName').value,
        unit_number: document.getElementById('unitNumber').value,
        contact_number: document.getElementById('contactNumber').value,
        email: document.getElementById('email').value,
    };
    
    // 2. Use the resident_id from the session user
    const residentId = user.resident_id || user.user_id;
    const endpoint = API_CONFIG.ENDPOINTS.RESIDENT.UPDATE_PROFILE(residentId);
    
    // 3. Make the API call to your Flask backend
    const result = await apiCall(endpoint, {
        method: 'PUT',
        body: JSON.stringify(formData)
    });
    
    if (result.success) {
        showMessage('message', 'Profile updated! Reloading...', 'success');
        
        // 4. THE SHORTCUT: Reload the page after 1.5 seconds
        // This forces the sidebar and session to refresh without extra code
        setTimeout(() => {
            window.location.reload();
        }, 1500);
    } else {
        showMessage('message', 'Error: ' + result.error, 'error');
    }
}

let faceAccessEnabled = true;
async function toggleFaceAccess() {
    if (!confirm('Are you sure you want to temporarily disable face access? You will need to use alternative access methods.')) {
        return;
    }
    
    const endpoint = API_CONFIG.ENDPOINTS.RESIDENT.DISABLE_FACE_ACCESS(user.resident_id);
    const result = await apiCall(endpoint, { method: 'POST' });
    
    if (result.success) {
        faceAccessEnabled = false;
        document.getElementById('faceStatus').textContent = 'Disabled';
        document.getElementById('faceStatus').className = 'badge badge-danger';
        alert('Face access has been temporarily disabled. Contact admin to re-enable.');
    } else {
        alert('Error disabling face access: ' + result.error);
    }
}

function changePassword() {
    alert('Password change functionality would be implemented here. Please contact admin for now.');
}

async function deleteAccount() {
    const confirmation = prompt('This action cannot be undone. Type "DELETE" to confirm account deletion:');
    
    if (confirmation !== 'DELETE') {
        alert('Account deletion cancelled.');
        return;
    }
    
    const endpoint = API_CONFIG.ENDPOINTS.RESIDENT.DELETE_PROFILE(user.resident_id);
    const result = await apiCall(endpoint, { method: 'DELETE' });
    
    if (result.success) {
        alert('Your account has been deleted. You will be logged out.');
        logout();
    } else {
        alert('Error deleting account: ' + result.error);
    }
}