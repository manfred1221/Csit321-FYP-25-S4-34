// Staff Profile JavaScript
let currentUser = null;
let profileData = null;

window.addEventListener('DOMContentLoaded', function() {
    // Check authentication
    const user = JSON.parse(localStorage.getItem('user') || 'null');
    
    if (!user || user.type !== 'staff') {
        alert('Please login as staff first!');
        window.location.href = 'index.html';
        return;
    }
    
    currentUser = user;
    
    // Display user info in sidebar
    displayUserInfo();
    
    // Load profile
    loadProfile();
    
    // Setup event listeners
    setupEventListeners();
});

function displayUserInfo() {
    const name = currentUser.full_name || currentUser.username;
    const position = currentUser.position || 'Staff';
    
    document.getElementById('staffName').textContent = name;
    document.getElementById('staffPosition').textContent = position;
}

function setupEventListeners() {
    // Logout
    document.getElementById('logoutBtn').addEventListener('click', function(e) {
        e.preventDefault();
        if (confirm('Are you sure you want to logout?')) {
            localStorage.removeItem('user');
            localStorage.removeItem('auth_token');
            window.location.href = '/admin/login';
        }
    });
    
    // Edit button
    document.getElementById('editBtn').addEventListener('click', toggleEditMode);
    
    // Cancel button
    document.getElementById('cancelBtn').addEventListener('click', cancelEdit);
    
    // Profile form submit
    document.getElementById('profileForm').addEventListener('submit', saveProfile);
    
    // Delete account button
    document.getElementById('deleteBtn').addEventListener('click', deleteAccount);
}

async function loadProfile() {
    try {
        const endpoint = API_CONFIG.ENDPOINTS.STAFF.GET_PROFILE(currentUser.staff_id);
        const result = await staffApiCall(endpoint);
        
        if (result.success) {
            profileData = result.data;
            displayProfile(profileData);
        } else {
            showMessage('Error loading profile: ' + result.error, 'error');
        }
    } catch (error) {
        console.error('Load profile error:', error);
        showMessage('Error loading profile', 'error');
    }
}

function displayProfile(profile) {
    // Display in view mode
    document.getElementById('viewName').textContent = profile.full_name || 'N/A';
    document.getElementById('viewPosition').textContent = profile.position || 'N/A';
    document.getElementById('viewContact').textContent = profile.contact_number || 'N/A';
    document.getElementById('viewEmail').textContent = profile.email || 'N/A';
    document.getElementById('viewUsername').textContent = profile.username || 'N/A';
    
    const statusBadge = profile.is_active ? 
        '<span class="badge badge-success">Active</span>' : 
        '<span class="badge badge-danger">Inactive</span>';
    document.getElementById('viewStatus').innerHTML = statusBadge;
    
    const registeredDate = profile.registered_at ? 
        new Date(profile.registered_at).toLocaleDateString() : 
        'N/A';
    document.getElementById('viewRegistered').textContent = registeredDate;
    
    // Fill edit form
    document.getElementById('editName').value = profile.full_name || '';
    document.getElementById('editContact').value = profile.contact_number || '';
    document.getElementById('editPosition').value = profile.position || '';
}

function toggleEditMode() {
    document.getElementById('viewMode').style.display = 'none';
    document.getElementById('editMode').style.display = 'block';
    document.getElementById('editBtn').style.display = 'none';
}

function cancelEdit() {
    document.getElementById('viewMode').style.display = 'block';
    document.getElementById('editMode').style.display = 'none';
    document.getElementById('editBtn').style.display = 'inline-block';
    hideMessage();
}

async function saveProfile(e) {
    e.preventDefault();
    
    const updatedData = {
        full_name: document.getElementById('editName').value.trim(),
        contact_number: document.getElementById('editContact').value.trim(),
        position: document.getElementById('editPosition').value.trim()
    };
    
    if (!updatedData.full_name || !updatedData.contact_number || !updatedData.position) {
        showMessage('All fields are required', 'error');
        return;
    }
    
    try {
        const endpoint = API_CONFIG.ENDPOINTS.STAFF.UPDATE_PROFILE(currentUser.staff_id);
        const result = await staffApiCall(endpoint, {
            method: 'PUT',
            body: JSON.stringify(updatedData)
        });
        
        if (result.success) {
            showMessage('✅ Profile updated successfully!', 'success');
            
            // Update local storage
            currentUser.full_name = updatedData.full_name;
            currentUser.position = updatedData.position;
            localStorage.setItem('user', JSON.stringify(currentUser));
            
            // Reload profile
            await loadProfile();
            
            // Switch back to view mode
            setTimeout(() => {
                cancelEdit();
            }, 1500);
        } else {
            showMessage('❌ ' + (result.error || 'Update failed'), 'error');
        }
    } catch (error) {
        console.error('Save profile error:', error);
        showMessage('❌ Error updating profile', 'error');
    }
}

async function deleteAccount() {
    const confirmation = prompt('⚠️ This action cannot be undone!\n\nType "DELETE" to confirm account deletion:');
    
    if (confirmation !== 'DELETE') {
        alert('Account deletion cancelled');
        return;
    }
    
    const finalConfirm = confirm('Are you absolutely sure you want to delete your account?\n\nThis will:\n- Remove your access\n- Delete your data\n- Sign you out immediately');
    
    if (!finalConfirm) {
        return;
    }
    
    try {
        const endpoint = API_CONFIG.ENDPOINTS.STAFF.DELETE_ACCOUNT(currentUser.staff_id);
        const result = await staffApiCall(endpoint, {
            method: 'DELETE'
        });
        
        if (result.success) {
            alert('✅ Account deleted successfully\n\nYou will be logged out now.');
            
            // Clear storage and redirect
            localStorage.removeItem('user');
            localStorage.removeItem('auth_token');
            window.location.href = 'index.html';
        } else {
            alert('❌ Error deleting account: ' + result.error);
        }
    } catch (error) {
        console.error('Delete account error:', error);
        alert('❌ Error deleting account');
    }
}

function showMessage(message, type) {
    const messageDiv = document.getElementById('profileMessage');
    messageDiv.textContent = message;
    messageDiv.className = `message ${type}`;
    messageDiv.style.display = 'block';
    
    setTimeout(() => {
        hideMessage();
    }, 5000);
}

function hideMessage() {
    const messageDiv = document.getElementById('profileMessage');
    messageDiv.style.display = 'none';
}
