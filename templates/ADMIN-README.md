# Admin Panel Frontend - 7 Pages

## 📦 Package Contents

Complete administrator dashboard for managing the condominium access control system. All pages use the same professional CSS styling (dark sidebar, blue theme).

## 📄 Pages Included

### 1. **admin_login.html** (Login Page)
- **Purpose**: Admin authentication page
- **Features**:
  - Admin username/password login
  - Link back to main login
  - Forgot password link
  - Redirects to user management on success
- **Use Case**: Secure entry point for administrators

### 2. **admin_users.html** (User Management)
- **Purpose**: Main dashboard for managing all users
- **Features**:
  - User statistics (Total Users, Active Residents, Security Officers, Pending Approvals)
  - Searchable user table with filters
  - Filter by role (Resident, Security, Staff, Admin)
  - Edit/Delete user actions
  - Approve pending registrations
  - Pagination
  - Export functionality
- **Use Case**: Central hub for user administration

### 3. **admin_add_user.html** (Add New User)
- **Purpose**: Create new user accounts
- **Features**:
  - Dynamic form fields based on role selection
  - Resident fields (Unit Number, Block, Move-in Date)
  - Security Officer fields (Officer ID, Shift, Start Date)
  - Staff fields (Department, Position)
  - Username/Password generation
  - Send welcome email option
  - Form validation
- **Use Case**: Onboard new residents, security officers, or staff

### 4. **admin_edit_user.html** (Edit User)
- **Purpose**: Modify existing user information
- **Features**:
  - Pre-filled user data
  - Edit personal information
  - Change account status (Active, Inactive, Suspended, Pending)
  - Reset password
  - Face registration status toggle
  - User activity statistics
  - Delete user option
- **Use Case**: Update user details or troubleshoot accounts

### 5. **admin_logs.html** (Access Logs)
- **Purpose**: View and analyze access events
- **Features**:
  - Real-time statistics (Today's Events, Success/Fail counts, Manual Overrides)
  - Advanced filtering (Date range, Location, Result, User Type)
  - Detailed log table with:
    - Timestamp
    - Location
    - Person identified
    - Confidence score
    - Result (Granted/Denied/Override)
  - Export to CSV
  - Pagination
  - View detailed log information
- **Use Case**: Security auditing and incident investigation

### 6. **camera.html** (Face Registration)
- **Purpose**: Register facial recognition data for visitors and residents
- **Features**:
  - Registration statistics (Total Faces, Residents, Visitors, Pending)
  - Dynamic form based on person type (Visitor/Resident)
  - Live camera feed for face capture
  - Capture and review face photo before registering
  - Visitor-specific fields (Visiting Unit, Host, Visit dates)
  - Resident-specific fields (Unit Number, Block, Email)
  - Recent registrations table
  - Approve/Reject pending registrations
  - View and delete face registrations
  - Retake photo option
- **Use Case**: Register new faces for access control system

### 7. **admin_profile.html** (Admin Profile)
- **Purpose**: Administrator account management
- **Features**:
  - View admin information
  - Update profile details
  - Change password with validation
  - Admin activity statistics:
    - Users Created
    - Users Modified
    - Users Deleted
    - Logs Reviewed
  - Last login tracking
- **Use Case**: Admin account settings and activity tracking

## 🎨 Design Features

All pages include:
- ✅ Dark sidebar navigation (#1f2937)
- ✅ Blue primary color scheme (#2563eb)
- ✅ Professional card layouts
- ✅ Responsive grid systems
- ✅ Status badges (Success/Warning/Danger/Info)
- ✅ Statistics cards
- ✅ Data tables with pagination
- ✅ Form validation
- ✅ Toast notifications
- ✅ Consistent navigation menu

## 🗂️ Navigation Structure

```
Admin Panel
├── 👥 Manage Users (admin_users.html)
├── ➕ Add User (admin_add_user.html)
├── 📋 Access Logs (admin_logs.html)
├── 📹 Cameras (camera.html)
├──  My Profile (admin_profile.html)
└── 🚪 Logout (admin_login.html)
```

## 🚀 Quick Start

### Option 1: Python HTTP Server
```bash
cd your-project
python -m http.server 8000
# Open: http://localhost:8000/admin_login.html
```

### Option 2: VS Code Live Server
Right-click `admin_login.html` → "Open with Live Server"

## 📂 File Structure

```
your-project/
├── admin_login.html          # Login page
├── admin_users.html          # User management
├── admin_add_user.html       # Add new user
├── admin_edit_user.html      # Edit existing user
├── admin_logs.html           # Access log viewer
├── admin_profile.html        # Admin profile
├── camera.html               # Camera management
└── css/
    └── styles.css            # Shared stylesheet
```

## 🔌 Backend Integration

### API Endpoints Needed:

**User Management:**
- `POST /api/admin/login` - Admin authentication
- `GET /api/admin/users` - List all users
- `POST /api/admin/users` - Create new user
- `PUT /api/admin/users/{id}` - Update user
- `DELETE /api/admin/users/{id}` - Delete user
- `GET /api/admin/users/{id}` - Get user details
- `PUT /api/admin/users/{id}/approve` - Approve pending user

**Access Logs:**
- `GET /api/admin/logs` - Fetch access logs
- `GET /api/admin/logs/stats` - Get statistics
- `GET /api/admin/logs/export` - Export to CSV

**Face Registration:**
- `GET /api/admin/faces` - List all registered faces
- `POST /api/admin/faces/register` - Register new face
- `GET /api/admin/faces/{id}` - Get face details
- `DELETE /api/admin/faces/{id}` - Delete face registration
- `PUT /api/admin/faces/{id}/approve` - Approve pending face

**Profile:**
- `GET /api/admin/profile` - Get admin profile
- `PUT /api/admin/profile` - Update admin profile
- `PUT /api/admin/profile/password` - Change password

### Example Integration:

```javascript
// In admin_users.html
async function loadUsers() {
    const response = await fetch('http://localhost:5003/api/admin/users');
    const data = await response.json();
    
    // Populate table
    data.users.forEach(user => {
        // Add row to table
    });
}
```

## 🎓 For Your FYP Report

**Admin Panel Features:**
- Complete CRUD operations for user management
- Role-based user creation (Resident/Security/Staff/Admin)
- Real-time access log monitoring with filtering
- Camera system integration
- Audit trail for admin actions
- Export functionality for reports

**Technology Stack:**
- Frontend: HTML5, CSS3, Vanilla JavaScript
- Design: Responsive grid layouts, card-based UI
- Backend: Flask (Python) - Port 5003 (recommended)
- Database: PostgreSQL integration via API

**Security Features:**
- Admin authentication required
- Password validation (min 8 characters)
- Account status management (Active/Inactive/Suspended)
- Audit logging for all admin actions

## 💡 Usage Tips

### User Management Workflow:
1. **Add User** → Create account with role
2. **Approve** → Approve pending registrations
3. **Edit** → Modify details or reset password
4. **Monitor** → Check access logs for activity
5. **Manage** → Suspend or delete if needed

### Camera Monitoring:
1. **View Status** → Check online/offline cameras
2. **Troubleshoot** → Fix offline cameras
3. **Configure** → Adjust recording settings
4. **Review** → Check footage via access logs

### Log Analysis:
1. **Filter** → By date, location, or result
2. **Identify** → Patterns or security concerns
3. **Export** → Generate reports for management
4. **Action** → Follow up on incidents

## 📊 Sample Data Included

- **5 sample users** (various roles)
- **7 access log entries** (different scenarios)
- **8 cameras** (1 offline for testing)
- **Statistics cards** (realistic numbers)

##  Default Admin Credentials

- **Username:** admin
- **Password:** (set in your backend)

*Remember to change default credentials in production!*

## 📝 Form Validation

All forms include:
- ✅ Required field validation
- ✅ Email format validation
- ✅ Password strength checks (min 8 chars)
- ✅ Matching password confirmation
- ✅ Role-specific field requirements

## 🎨 Customization

### Colors:
Edit `css/styles.css`:
```css
:root {
    --primary-color: #2563eb;  /* Blue - change to your brand color */
    --success-color: #10b981;  /* Green */
    --danger-color: #ef4444;   /* Red */
    --dark-bg: #1f2937;        /* Dark sidebar */
}
```

### Branding:
- Update `👑 Admin Panel` text in sidebar
- Modify logo/header in login page
- Add company name/logo

## 🐛 Testing

### Test Scenarios:
1. ✅ Login with admin credentials
2. ✅ Add user with different roles
3. ✅ Edit existing user
4. ✅ Filter and search users
5. ✅ View and filter access logs
6. ✅ Check camera status
7. ✅ Update admin profile

## 📞 Support

All pages are fully functional prototypes ready for backend integration.

---

**Created for**: CSIT321 FYP - Facial Recognition Condominium Access Control System  
**Pages**: 7 complete admin pages  
**Style**: Professional admin dashboard with dark sidebar theme
