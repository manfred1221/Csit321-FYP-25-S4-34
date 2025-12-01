# Condominium Facial Recognition System - Frontend

A comprehensive HTML/CSS/JavaScript frontend for a condominium facial recognition access control system.

## 📋 Project Overview

This frontend interfaces with your Flask backend to provide:
- **Resident Portal**: Manage personal data, face registration, visitors, and access history
- **Visitor Portal**: View visit details and access QR codes
- **Real-time Notifications**: Security alerts for unauthorized access attempts

## 🗂️ Project Structure

```
project/
├── index.html                          # Login page
├── register.html                       # Registration page (to be created)
├── resident-dashboard.html             # Resident main dashboard
├── resident-profile.html               # Resident profile management
├── resident-face-registration.html     # Face data capture and upload
├── resident-visitors.html              # Visitor management
├── resident-access-history.html        # Personal access logs
├── resident-alerts.html                # Security alerts
├── visitor-dashboard.html              # Visitor check-in portal
├── css/
│   └── styles.css                      # Main stylesheet
└── js/
    ├── config.js                       # API configuration
    ├── login.js                        # Login functionality
    ├── resident-dashboard.js           # Dashboard logic
    ├── resident-profile.js             # Profile management
    ├── resident-face-registration.js   # Face capture logic
    ├── resident-visitors.js            # Visitor management
    ├── resident-access-history.js      # Access history
    ├── resident-alerts.js              # Alerts handling
    └── visitor-dashboard.js            # Visitor portal
```

## 🚀 Getting Started

### Prerequisites
- A web browser (Chrome, Firefox, Safari, Edge)
- Your Flask backend running on `http://localhost:5001`
- A web server to serve the HTML files (or just open index.html directly)

### Installation

1. **Clone or download the files** to your local machine

2. **Update API Configuration** (if needed)
   - Open `js/config.js`
   - Update `BASE_URL` if your backend is on a different port/host:
   ```javascript
   const API_CONFIG = {
       BASE_URL: 'http://localhost:5001',  // Change this if needed
       // ...
   };
   ```

3. **Start your Flask backend**
   ```bash
   python app.py
   ```

4. **Serve the frontend**
   
   Option A - Simple HTTP Server (Python):
   ```bash
   python -m http.server 8000
   ```
   Then visit: `http://localhost:8000`
   
   Option B - Live Server (VS Code Extension):
   - Install "Live Server" extension
   - Right-click on `index.html` → "Open with Live Server"
   
   Option C - Direct File Access:
   - Simply open `index.html` in your browser
   - Note: Some features may not work due to CORS restrictions

## 📱 Features by User Type

### Resident Features
✅ **UC-R1**: Register Face Data
✅ **UC-R2**: View Personal Data  
✅ **UC-R3**: Update Personal Data
✅ **UC-R4**: Delete Personal Data
✅ **UC-R8**: Create Visitor Entry
✅ **UC-R9**: Set Visitor Time Period
✅ **UC-R10**: View Registered Visitors
✅ **UC-R11**: Update Visitor Information
✅ **UC-R12**: Delete/Cancel Visitor Access
✅ **UC-R13**: Create Visitor with Time Window
✅ **UC-R14**: Upload Visitor Facial Image
✅ **UC-R15**: View Visitor List
✅ **UC-R16**: Update Visitor Details
✅ **UC-R17**: Cancel Visitor Access
✅ **UC-R19**: Temporarily Disable Face Access
✅ **UC-R20**: Receive Unauthorized Access Alerts
✅ **UC-R22**: View Personal Access History
✅ **UC-R23**: View Visitor Access History

### Visitor Features
✅ View visit status and details
✅ Access QR code for entry
✅ Check visit time window

## 🎨 Pages Description

### 1. Login Page (`index.html`)
- User authentication
- Role selection (Resident/Visitor/Admin)
- Mock login (for development)

### 2. Resident Dashboard (`resident-dashboard.html`)
- Overview statistics
- Recent visitors list
- Recent access history
- Quick actions (add visitor, update face, disable access)

### 3. Face Registration (`resident-face-registration.html`)
- Camera integration for face capture
- Live video preview
- Photo capture and review
- Upload to backend

### 4. Visitor Management (`resident-visitors.html`)
- List all registered visitors
- Add new visitor with time window
- Edit visitor details
- Upload visitor face photo
- View visitor access history
- Delete visitors

### 5. Profile Management (`resident-profile.html`)
- View/edit personal information
- Toggle face access on/off
- Account deletion

### 6. Access History (`resident-access-history.html`)
- View all access attempts
- Filter by date range and result
- Export to CSV
- Access statistics

### 7. Alerts (`resident-alerts.html`)
- Unauthorized access notifications
- Mark as read/unread
- Auto-refresh every 30 seconds

### 8. Visitor Dashboard (`visitor-dashboard.html`)
- Visit status display
- QR code for access
- Visit details and time window

## 🔧 Configuration

### API Endpoints
All API endpoints are configured in `js/config.js`. The frontend maps to your backend routes:

```javascript
RESIDENT: {
    REGISTER_FACE: '/api/resident/register-face',
    GET_PROFILE: (residentId) => `/api/resident/${residentId}`,
    CREATE_VISITOR: (residentId) => `/api/resident/${residentId}/visitors`,
    // ... more endpoints
}
```

### Camera Permissions
The face registration feature requires camera access:
- Browser will prompt for camera permissions
- Ensure HTTPS if deploying to production (required for camera access on most browsers)

## 🎯 Usage Flow

### For Residents:

1. **Login** → Use "Resident" role
2. **Register Face** → Navigate to Face Registration, capture photo
3. **Add Visitors** → Go to Manage Visitors, click "Add New Visitor"
4. **Monitor Access** → Check Access History and Alerts

### For Visitors:

1. **Login** → Use "Visitor" role
2. **View Details** → See visit time window and unit
3. **Show QR Code** → Present at entrance for access

## 🔐 Security Notes

- This is a **development/demo version** with mock authentication
- In production, implement:
  - Real authentication with JWT tokens
  - HTTPS encryption
  - Input validation
  - CSRF protection
  - Rate limiting

## 🛠️ Customization

### Styling
Edit `css/styles.css` to customize:
- Colors (modify CSS variables in `:root`)
- Fonts
- Layout and spacing

### Adding New Features
1. Create new HTML page
2. Add corresponding JS file
3. Update navigation in sidebar
4. Add API endpoint in `config.js`

## 📊 Browser Compatibility

- ✅ Chrome 90+
- ✅ Firefox 88+
- ✅ Safari 14+
- ✅ Edge 90+

## 🐛 Troubleshooting

### Camera Not Working
- Check browser permissions
- Use HTTPS (required for camera in production)
- Ensure camera is not being used by another app

### API Calls Failing
- Verify backend is running on port 5001
- Check browser console for CORS errors
- Ensure `BASE_URL` in `config.js` is correct

### Data Not Showing
- Open browser DevTools (F12)
- Check Console for errors
- Verify backend is returning expected data format

## 🚀 Next Steps

To complete the system:

1. **Add Authentication Backend**
   - Implement real login/register endpoints
   - Add JWT token management
   - Session handling

2. **Enhance Security**
   - HTTPS deployment
   - Input sanitization
   - XSS protection

3. **Add More Features**
   - Admin dashboard
   - Real-time WebSocket notifications
   - PDF report generation
   - Multi-language support

4. **Optimize Performance**
   - Image compression before upload
   - Lazy loading for tables
   - Caching strategies

5. **Testing**
   - Unit tests for JS functions
   - Integration tests with backend
   - Cross-browser testing

## 📝 License

This is a final year project. Ensure proper attribution if used for commercial purposes.

## 👥 Support

For issues or questions related to this frontend:
1. Check the browser console for errors
2. Verify backend API responses
3. Review the API configuration in `config.js`

---

**Created for Final Year Project - Facial Recognition Condominium Access System**
