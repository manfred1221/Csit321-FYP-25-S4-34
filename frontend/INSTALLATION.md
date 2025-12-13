# 🚀 INSTALLATION INSTRUCTIONS

## 📦 Package Contents

This ZIP file contains the complete frontend for your Facial Recognition Condominium System.

**Total Files: 23**
- 9 HTML pages
- 1 CSS file (in css/ folder)
- 9 JavaScript files (in js/ folder)
- 4 Documentation files (.md)

---

## 📥 Step 1: Extract the Files

1. Download `condo-facial-recognition-frontend.zip`
2. Extract to your project folder
3. You should see this structure:

```
frontend/
├── index.html                          ← Login page (START HERE)
├── demo.html                           ← Feature showcase
├── resident-dashboard.html
├── resident-profile.html
├── resident-face-registration.html
├── resident-visitors.html
├── resident-access-history.html
├── resident-alerts.html
├── visitor-dashboard.html
├── css/
│   └── styles.css
├── js/
│   ├── config.js                       ← IMPORTANT: Configure backend URL here
│   ├── login.js
│   ├── resident-dashboard.js
│   ├── resident-profile.js
│   ├── resident-face-registration.js
│   ├── resident-visitors.js
│   ├── resident-access-history.js
│   ├── resident-alerts.js
│   └── visitor-dashboard.js
├── README.md                           ← Full documentation
├── QUICKSTART.md                       ← Quick start guide
├── PROJECT_SUMMARY.md                  ← Project overview
└── VISITOR_FLOW.md                     ← Visitor access flow
```

---

## 🔧 Step 2: Configure Backend Connection

**IMPORTANT:** Edit `js/config.js` to match your backend URL

```javascript
const API_CONFIG = {
    BASE_URL: 'http://localhost:5001',  // ← Change if different
    // ...
};
```

If your Flask backend runs on a different port or server, update this URL.

---

## 🖥️ Step 3: Setup Your Backend

Make sure your Flask backend is ready:

**File: backend/app.py**
```python
from flask import Flask
from flask_cors import CORS

# Import your routes
from routes.resident_routes import resident_bp

app = Flask(__name__)
CORS(app)  # ← CRITICAL: Enable CORS for frontend to work

# Register blueprints
app.register_blueprint(resident_bp, url_prefix="/api/resident")

if __name__ == "__main__":
    app.run(debug=True, port=5001)
```

**Install CORS if needed:**
```bash
pip install flask-cors
```

---

## ▶️ Step 4: Run the Application

### Terminal 1 - Start Backend:
```bash
cd backend
python app.py
```

**Expected output:**
```
* Running on http://127.0.0.1:5001
* Debugger is active!
```

### Terminal 2 - Start Frontend:

**Option A: Python HTTP Server**
```bash
cd frontend
python -m http.server 8000
```

**Option B: VS Code Live Server**
1. Install "Live Server" extension
2. Right-click `index.html`
3. Select "Open with Live Server"

**Expected output:**
```
Serving HTTP on 0.0.0.0 port 8000
```

---

## 🌐 Step 5: Access the Application

Open your browser and go to:
```
http://localhost:8000
```

Or if using Live Server:
```
http://127.0.0.1:5500
```

---

## 🧪 Step 6: Test Login

**For Testing (Mock Authentication):**

**Resident Login:**
- Username: `john` (or any text)
- Password: `password` (or any text)
- User Type: `Resident`

**Visitor Login:**
- Username: `visitor1` (or any text)
- Password: `password` (or any text)
- User Type: `Visitor`

---

## ✅ Step 7: Test Features

### As Resident:
1. ✅ View Dashboard
2. ✅ Register Face (allow camera access)
3. ✅ Add Visitor
4. ✅ Upload Visitor Face Photo
5. ✅ View Access History
6. ✅ Check Alerts

### As Visitor:
1. ✅ View Visit Status
2. ✅ Check Face Registration Status
3. ✅ See Visit Time Window

---

## 🐛 Troubleshooting

### Problem 1: "CORS Error" in Browser Console
**Solution:** 
```python
# In backend/app.py
from flask_cors import CORS
CORS(app)  # Add this line
```

### Problem 2: Camera Not Working
**Solution:**
- Grant camera permissions when prompted
- Use Chrome or Firefox (Safari may have issues)
- Ensure no other app is using the camera
- Try HTTPS if on production

### Problem 3: API Calls Return 404
**Solution:**
- Check backend is running on port 5001
- Verify `js/config.js` has correct BASE_URL
- Check your backend routes match the API endpoints

### Problem 4: Pages Load But No Data Shows
**Solution:**
- Open browser DevTools (F12)
- Check Console tab for JavaScript errors
- Check Network tab for API responses
- Verify backend is returning correct JSON format

### Problem 5: "Port Already in Use"
**Solution:**
```bash
# Use different port
python -m http.server 3000
# Then visit http://localhost:3000
```

---

## 📱 Browser Requirements

**Supported Browsers:**
- ✅ Chrome 90+
- ✅ Firefox 88+
- ✅ Safari 14+
- ✅ Edge 90+

**Required Permissions:**
-  Camera access (for face registration)
- 🔐 JavaScript enabled
- 💾 LocalStorage enabled

---

## 🔐 Security Notes

**Current Setup (Development):**
- ⚠️ Mock authentication (for testing only)
- ⚠️ No real token validation
- ⚠️ Sessions stored in localStorage

**For Production Deployment:**
- ✅ Implement real JWT authentication
- ✅ Use HTTPS (required for camera access)
- ✅ Add input validation
- ✅ Enable CSRF protection
- ✅ Implement rate limiting
- ✅ Use secure session management

---

## 📚 Documentation Files

**README.md** - Complete documentation with all features

**QUICKSTART.md** - Quick setup guide

**PROJECT_SUMMARY.md** - Project overview and technical details

**VISITOR_FLOW.md** - Detailed visitor access workflow

---

## 🎯 Project Structure

```
Your Full Project:
├── backend/                    ← Your existing Flask backend
│   ├── app.py
│   ├── routes/
│   │   ├── resident_routes.py
│   │   └── visitor_routes.py
│   └── requirements.txt
│
└── frontend/                   ← Downloaded files go here
    ├── index.html
    ├── *.html files
    ├── css/
    ├── js/
    └── *.md documentation
```

---

## 📊 Features Included

### Resident Portal:
✅ Face Registration with Camera
✅ Profile Management
✅ Visitor Management (CRUD)
✅ Visitor Face Upload
✅ Access History with Filters
✅ CSV Export
✅ Security Alerts
✅ Temporary Access Control

### Visitor Portal:
✅ Visit Status Display
✅ Face Registration Status
✅ Time Window Information
✅ Access Instructions

### UI/UX:
✅ Responsive Design
✅ Professional Interface
✅ Real-time Camera Preview
✅ Form Validation
✅ Loading States
✅ Success/Error Messages

---

## 🚀 Next Steps

1. ✅ Extract files
2. ✅ Configure backend URL
3. ✅ Enable CORS in Flask
4. ✅ Start backend server
5. ✅ Start frontend server
6. ✅ Test in browser
7. ✅ Test all features

---

## 💡 Tips

1. **Always start backend first**, then frontend
2. **Check browser console** (F12) for any errors
3. **Use Chrome DevTools** to debug API calls
4. **Read QUICKSTART.md** for rapid setup
5. **Check VISITOR_FLOW.md** to understand the system

---

## 📞 Need Help?

**Common Issues:**
- Backend not responding → Check if running on port 5001
- CORS errors → Add `CORS(app)` to Flask
- Camera not working → Check browser permissions
- Login issues → Check browser console for errors

**Documentation:**
- Technical details: README.md
- Quick guide: QUICKSTART.md
- Visitor flow: VISITOR_FLOW.md
- Project info: PROJECT_SUMMARY.md

---

## ✨ You're Ready!

Everything you need is in this package. Just follow the steps above and you'll have a working facial recognition system!

**Good luck with your Final Year Project! 🎓**

---

**Package Version:** 1.0
**Created:** December 2024
**Technology:** HTML5 + CSS3 + JavaScript + Flask
**Project:** Facial Recognition Condominium Access System
