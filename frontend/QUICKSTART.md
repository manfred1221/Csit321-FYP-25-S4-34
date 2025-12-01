# 🚀 Quick Start Guide

## Setup in 3 Steps

### Step 1: Start Your Backend
```bash
cd your-backend-directory
python app.py
```
Your Flask backend should be running on `http://localhost:5001`

### Step 2: Serve the Frontend
Open a new terminal in the frontend directory:

**Option A - Python HTTP Server:**
```bash
python -m http.server 8000
```
Then open: `http://localhost:8000`

**Option B - Just open the file:**
- Double-click `index.html` in your file explorer
- Some features may be limited due to CORS

### Step 3: Login and Test

**Test as Resident:**
- Username: `john`
- Password: `anything`
- User Type: `Resident`

**Test as Visitor:**
- Username: `visitor1`
- Password: `anything`
- User Type: `Visitor`

## 📱 What to Test

### Resident Flow:
1. ✅ **Dashboard** - View overview and statistics
2. ✅ **Face Registration** - Click "Start Camera" and capture your face
3. ✅ **Add Visitor** - Create a new visitor with time window
4. ✅ **Upload Visitor Face** - Capture visitor's facial photo
5. ✅ **View Access History** - Check your access logs
6. ✅ **Check Alerts** - View security notifications

### Visitor Flow:
1. ✅ **Login** as visitor
2. ✅ **View QR Code** - For entrance access
3. ✅ **Check Visit Window** - Confirm your access times

## 🎯 API Integration

The frontend automatically calls your backend APIs:

- `POST /api/resident/register-face` - Face registration
- `GET /api/resident/<id>` - Get profile
- `POST /api/resident/<id>/visitors` - Create visitor
- `GET /api/resident/<id>/access-history` - Access logs
- And more...

All endpoints are configured in `js/config.js`

## 🔧 Common Issues

**Camera not working?**
- Grant camera permissions when prompted
- Try using Chrome or Firefox
- If on HTTPS, ensure valid certificate

**API errors?**
- Check backend is running on port 5001
- Look at browser console (F12) for errors
- Verify CORS is enabled in Flask:
  ```python
  from flask_cors import CORS
  CORS(app)
  ```

**Data not showing?**
- Open browser DevTools (F12)
- Check Network tab for failed requests
- Ensure backend is returning correct JSON format

## 📝 Development Tips

1. **Browser DevTools (F12)** is your friend:
   - Console: See JavaScript errors
   - Network: Monitor API calls
   - Application: Check localStorage

2. **Test with multiple browser tabs** to simulate resident and visitor

3. **Mock data** is currently used for login - replace with real authentication in production

## 🎨 Customization

**Change colors:**
Edit `css/styles.css` - Look for `:root` variables:
```css
:root {
    --primary-color: #2563eb;  /* Change this */
    --success-color: #10b981;
    --danger-color: #ef4444;
}
```

**Add new pages:**
1. Create HTML file
2. Add JS file in `js/` folder  
3. Update sidebar navigation
4. Add API endpoint in `config.js`

## 📚 File Structure

```
frontend/
├── index.html              # Login page
├── resident-*.html         # Resident pages
├── visitor-dashboard.html  # Visitor page
├── css/
│   └── styles.css         # All styles
├── js/
│   ├── config.js          # API config
│   └── *.js              # Page scripts
└── README.md             # Full documentation
```

## 🚀 Ready to Deploy?

Before production deployment:
1. ✅ Implement real authentication
2. ✅ Enable HTTPS
3. ✅ Add input validation
4. ✅ Set up proper CORS
5. ✅ Minify CSS/JS files
6. ✅ Add error tracking
7. ✅ Test on multiple devices

---

**Need Help?** Check the full README.md for detailed documentation!
