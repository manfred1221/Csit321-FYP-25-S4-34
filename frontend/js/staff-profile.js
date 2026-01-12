let currentUser = null;

document.addEventListener('DOMContentLoaded', async () => {
    // 1. Verify Session
    currentUser = await checkAuth(); 
    
    if (!currentUser) return;

    // 2. Role Check
    const allowedRoles = ['Internal_Staff', 'Staff', 'Security', 'internal_staff'];
    if (!allowedRoles.includes(currentUser.role)) {
        window.location.href = '/login';
        return;
    }

    // 3. Update Sidebar UI
    const name = currentUser.full_name || currentUser.username;
    document.getElementById('staffNameSidebar').textContent = name;
    document.getElementById('staffRoleSidebar').textContent = currentUser.role || 'Staff Member';

    // 4. Load Profile Data
    loadProfile();
    setupEventListeners();
});

function setupEventListeners() {
    // Logout
    const logoutBtn = document.getElementById('logoutBtn');
    if(logoutBtn) {
        logoutBtn.addEventListener('click', async (e) => {
            e.preventDefault();
            if (confirm('Are you sure you want to logout?')) {
                await logout(); 
            }
        });
    }

    // Form Submit
    document.getElementById('profileForm').addEventListener('submit', saveProfile);
}

async function loadProfile() {
    const staffId = currentUser.staff_id || currentUser.user_id;
    try {
        const response = await fetch(`/api/staff/${staffId}/profile`);
        const result = await response.json();

        if (result.success) {
            displayProfile(result.data);
        } else {
            showMessage('Error loading profile data', 'error');
        }
    } catch (error) {
        console.error('Load profile error:', error);
        showMessage('Network error loading profile', 'error');
    }
}

function displayProfile(data) {
    // View Mode Fields
    document.getElementById('viewName').textContent = data.full_name || currentUser.username;
    document.getElementById('viewRole').textContent = data.position || currentUser.role;
    document.getElementById('viewEmail').textContent = data.email || 'N/A';
    document.getElementById('viewContact').textContent = data.contact_number || 'N/A';
    document.getElementById('viewJoined').textContent = data.created_at ? new Date(data.created_at).toLocaleDateString() : 'N/A';
    
    // Avatar Initials
    const name = data.full_name || currentUser.username;
    document.getElementById('avatarDisplay').textContent = name.charAt(0).toUpperCase();

    // Edit Mode Fields
    document.getElementById('editName').value = data.full_name || '';
    document.getElementById('editContact').value = data.contact_number || '';
}

function toggleEditMode() {
    document.getElementById('viewMode').style.display = 'none';
    document.getElementById('editMode').style.display = 'block';
    document.getElementById('editBtn').style.display = 'none';
    document.getElementById('profileMessage').style.display = 'none';
}

function cancelEdit() {
    document.getElementById('viewMode').style.display = 'block';
    document.getElementById('editMode').style.display = 'none';
    document.getElementById('editBtn').style.display = 'inline-block';
}

async function saveProfile(e) {
    e.preventDefault();
    const staffId = currentUser.staff_id || currentUser.user_id;
    const msgDiv = document.getElementById('profileMessage');

    const updatedData = {
        full_name: document.getElementById('editName').value,
        contact_number: document.getElementById('editContact').value
    };

    try {
        const response = await fetch(`/api/staff/${staffId}/profile`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(updatedData)
        });

        const result = await response.json();

        if (result.success) {
            showMessage('✅ Profile updated successfully!', 'success');
            // Refresh view
            loadProfile(); 
            // Update sidebar name immediately
            document.getElementById('staffNameSidebar').textContent = updatedData.full_name;
            cancelEdit();
        } else {
            showMessage('❌ ' + (result.message || 'Update failed'), 'error');
        }
    } catch (error) {
        showMessage('❌ Network error', 'error');
    }
}

async function deleteAccount() {
    if (!confirm('⚠️ Are you strictly sure? This action cannot be undone.')) return;
    
    const staffId = currentUser.staff_id || currentUser.user_id;
    
    try {
        const response = await fetch(`/api/staff/${staffId}/account`, {
            method: 'DELETE'
        });
        
        const result = await response.json();
        
        if (result.success) {
            alert('Account deleted. You will be logged out.');
            await logout();
        } else {
            alert('Failed to delete account: ' + result.message);
        }
    } catch (error) {
        alert('Network error deleting account');
    }
}

function showMessage(msg, type) {
    const el = document.getElementById('profileMessage');
    el.textContent = msg;
    el.className = `message ${type}`; // Ensure .message.success/error CSS exists
    el.style.display = 'block';
    el.style.padding = '10px';
    el.style.borderRadius = '6px';
    
    if(type === 'success') {
        el.style.background = '#dcfce7';
        el.style.color = '#166534';
    } else {
        el.style.background = '#fee2e2';
        el.style.color = '#b91c1c';
    }
}