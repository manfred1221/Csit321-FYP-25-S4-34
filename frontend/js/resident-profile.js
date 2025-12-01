// Check authentication
const user = checkAuth();
if (user && user.type !== 'resident') {
    window.location.href = 'index.html';
}

// Update user info in sidebar
document.getElementById('userName').textContent = user.full_name || user.username;
document.getElementById('userEmail').textContent = user.email;

let originalProfileData = {};
let isEditing = false;

// Load profile data on page load
loadProfile();

async function loadProfile() {
    const endpoint = API_CONFIG.ENDPOINTS.RESIDENT.GET_PROFILE(user.id);
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
    const formData = {
        full_name: document.getElementById('fullName').value,
        unit_number: document.getElementById('unitNumber').value,
        contact_number: document.getElementById('contactNumber').value,
        email: document.getElementById('email').value,
    };
    
    const endpoint = API_CONFIG.ENDPOINTS.RESIDENT.UPDATE_PROFILE(user.id);
    const result = await apiCall(endpoint, {
        method: 'PUT',
        body: JSON.stringify(formData)
    });
    
    if (result.success) {
        showMessage('message', 'Profile updated successfully!', 'success');
        originalProfileData = { ...formData };
        
        // Update user in localStorage
        const updatedUser = { ...user, ...formData };
        localStorage.setItem('user', JSON.stringify(updatedUser));
        
        // Update sidebar
        document.getElementById('userName').textContent = formData.full_name;
        document.getElementById('userEmail').textContent = formData.email;
        
        setTimeout(() => {
            toggleEdit();
        }, 1500);
    } else {
        showMessage('message', 'Error updating profile: ' + result.error, 'error');
    }
}

let faceAccessEnabled = true;
async function toggleFaceAccess() {
    if (!confirm('Are you sure you want to temporarily disable face access? You will need to use alternative access methods.')) {
        return;
    }
    
    const endpoint = API_CONFIG.ENDPOINTS.RESIDENT.DISABLE_FACE_ACCESS(user.id);
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
    
    const endpoint = API_CONFIG.ENDPOINTS.RESIDENT.DELETE_PROFILE(user.id);
    const result = await apiCall(endpoint, { method: 'DELETE' });
    
    if (result.success) {
        alert('Your account has been deleted. You will be logged out.');
        logout();
    } else {
        alert('Error deleting account: ' + result.error);
    }
}
