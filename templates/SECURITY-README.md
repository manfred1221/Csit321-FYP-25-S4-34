# Security Officer Frontend - 6 Pages

## 📦 Package Contents

This package contains a complete security officer dashboard with 6 professional pages, all styled with the same CSS as the resident pages (dark sidebar, blue theme).

## 📄 Pages Included

### 1. **security-dashboard.html** (Monitor Cameras)
- **Purpose**: Main dashboard for security officers
- **Features**:
  - Live camera feeds from 4 locations (Main Entrance, Parking A, Lobby, Back Entrance)
  - Real-time statistics (Active Cameras, Today's Events, Active Visitors, Alerts)
  - Recent alerts section
  - Access event log table
  - Camera controls (Start/Stop/Snapshot for each camera)
- **Use Case**: Primary monitoring page where officers watch all entry points

### 2. **security-override.html** (Manual Override)
- **Purpose**: Bypass face recognition and manually control access
- **Features**:
  - Emergency door control (open gates manually)
  - Grant access to specific persons
  - Dropdown for door/gate selection
  - Reason logging for all overrides
  - Recent manual override history
- **Use Case**: When face recognition fails or emergency situations require manual intervention

### 3. **security-view-profile.html** (View Profile)
- **Purpose**: Display officer information
- **Features**:
  - Personal information display (Name, ID, Email, Phone, Shift)
  - Work statistics (Shifts Completed, Manual Overrides, Incidents)
  - Certifications & training display
  - Print profile button
- **Use Case**: Officers can view their profile and work history

### 4. **security-update-profile.html** (Update Profile)
- **Purpose**: Edit officer information
- **Features**:
  - Edit personal details (Name, Contact, Email, Shift preference)
  - Emergency contact information
  - Change password section
  - Form validation
- **Use Case**: Officers can update their contact info and preferences

### 5. **security-deactivate.html** (Deactivate Account)
- **Purpose**: Account deactivation for officers leaving
- **Features**:
  - Warning alerts about permanent action
  - Reason selection dropdown
  - Comments field
  - Password confirmation
  - Checkbox confirmation
  - Supervisor contact information
- **Use Case**: When an officer resigns, retires, or transfers

### 6. **security-face-verification.html** (Face Verification)
- **Purpose**: Verify identity using facial recognition
- **Features**:
  - Live camera feed for face scanning
  - Start/Stop camera controls
  - Verify Face button with simulated recognition
  - Success/Failure results with confidence scores
  - Verification statistics
  - Recent verification history table
  - Grant access or manual override options
- **Use Case**: Real-time face verification at entry points

## 🎨 Styling

All pages use the shared `css/styles.css` which includes:
- Dark sidebar (#1f2937)
- Blue primary color (#2563eb)
- Card-based layouts
- Responsive design
- Professional badges and alerts
- Camera feed styling
- Table styling
- Form styling

## 🚀 How to Use

1. **Extract the zip file**
2. **File structure should be**:
   ```
   your-project/
   ├── security-dashboard.html
   ├── security-override.html
   ├── security-view-profile.html
   ├── security-update-profile.html
   ├── security-deactivate.html
   ├── security-face-verification.html
   └── css/
       └── styles.css
   ```
3. **Open any page in a browser** to test
4. **Navigation works between all pages** via the sidebar

## 📱 Features

### Camera Functionality
- Uses `navigator.mediaDevices.getUserMedia()` for webcam access
- Real camera feed display
- Capture snapshots
- Multiple camera support

### Simulated Features
- Face verification results (90%+ confidence = success)
- Access log generation
- Statistics updates
- Alert system

## 🔌 Backend Integration Points

To connect to your Flask backend on port 5002:

### API Endpoints Needed:
1. **GET /api/security/statistics** - Dashboard stats
2. **GET /api/security/access-logs** - Recent access events
3. **GET /api/security/alerts** - Active alerts
4. **POST /api/security/access/override** - Manual door control
5. **POST /api/security/face/verify** - Face verification
6. **GET /api/security/profile** - Officer profile
7. **PUT /api/security/profile** - Update profile

### Example Integration:
```javascript
// In security-dashboard.html, replace simulation with:
async function loadStatistics() {
    const response = await fetch('http://localhost:5002/api/security/statistics');
    const data = await response.json();
    document.getElementById('activeCameras').textContent = data.active_cameras;
    document.getElementById('todayEvents').textContent = data.today_events;
    // etc.
}
```

## ⚡ Quick Start

```bash
# Option 1: Python HTTP Server
cd your-project
python -m http.server 8000
# Then open: http://localhost:8000/security-dashboard.html

# Option 2: VS Code Live Server
# Right-click on security-dashboard.html → "Open with Live Server"
```

## 📝 Notes

- All camera features require HTTPS or localhost to work (browser security)
- Face verification is currently simulated - connect to your backend for real recognition
- Manual overrides are logged in the UI but need backend integration for persistence
- All forms have client-side validation

## 🎓 For Your FYP Report

**Technology Stack:**
- Frontend: HTML5, CSS3, Vanilla JavaScript
- Camera: WebRTC (getUserMedia API)
- Styling: Custom CSS with responsive grid layout
- Backend: Flask (Python) - Port 5002

**Key Features to Highlight:**
- Multi-camera monitoring system
- Real-time face verification
- Manual override with audit trail
- Role-based access control
- Professional security dashboard UI

## 📞 Support

All pages are fully functional prototypes. For backend integration help, refer to your `backend_securityguard.py` file.

---

**Created for**: CSIT321 FYP - Facial Recognition Condominium Access Control System  
**Pages**: 6 complete security officer pages  
**Style**: Professional dark theme matching resident pages
