# 📋 Visitor Access Flow - Facial Recognition System

## 🎯 Overview
This system uses **facial recognition ONLY** for visitor access - no QR codes, no cards, no manual check-ins.

---

## 👤 Complete Visitor Journey

### Step 1: Resident Registers Visitor
**Location:** Resident Portal → Manage Visitors

1. Resident logs into their account
2. Clicks "Add New Visitor"
3. Fills in visitor details:
   - Visitor name
   - Contact number
   - Visiting unit
   - Start time (e.g., 2025-12-01 10:00)
   - End time (e.g., 2025-12-01 18:00)
4. **Critical:** Clicks "Face" button and uploads visitor's facial photo
5. System status: Visitor created with face data ✅

---

### Step 2: Visitor Receives Access
**Location:** Visitor Portal

**Visitor logs in and sees:**
- ✅ **Face Recognition Ready** (if photo uploaded)
- ⚠️ **Face Not Registered** (if no photo uploaded)
- Visit time window
- Access instructions

**Status Messages:**

#### If Face Registered ✅
```
✅ Face Recognition Ready
Your facial recognition is registered and ready to use.

Access Active (during visit window)
🎯 Your facial recognition access is currently active!

How to Access:
1. Approach the entrance camera
2. Look directly at the camera
3. Wait for recognition (2-3 seconds)
4. Door unlocks automatically
```

#### If Face NOT Registered ⚠️
```
⚠️ Face Not Registered
Your facial recognition data has not been uploaded yet.

What to do:
- Contact the resident who invited you
- Ask them to upload your facial photo
- Once uploaded, you'll be able to use facial recognition
```

---

### Step 3: Physical Access at Entrance

**Hardware Required:**
- Facial recognition camera at entrance
- Face recognition backend processing
- Door lock system

**Access Process:**
1. Visitor approaches entrance camera
2. Camera captures visitor's face
3. Backend compares with registered visitor faces
4. **If match found + within time window:**
   - ✅ Access GRANTED
   - Door unlocks automatically
   - Log entry created
5. **If no match or outside time window:**
   - ❌ Access DENIED
   - Alert sent to resident
   - Log entry created

---

## 🔄 System Workflow

```
Resident → Add Visitor Details → Upload Visitor Face Photo
                                           ↓
                                  Backend Stores Face Data
                                           ↓
                                  Visitor Can Login & View Status
                                           ↓
                                  Visitor Arrives at Entrance
                                           ↓
                                  Camera Captures Face
                                           ↓
                                  Backend Recognition Process
                                           ↓
                        Check: Match Found? + Within Time Window?
                                           ↓
                            YES ✅                    NO ❌
                             ↓                         ↓
                      Grant Access              Deny Access
                      Unlock Door              Send Alert
                      Log Entry                Log Entry
```

---

## 🎨 Visitor Dashboard States

### State 1: Face Not Registered
```
⚠️ Face Not Registered
↓
Contact resident to upload photo
↓
Cannot access building yet
```

### State 2: Visit Pending Approval
```
⏳ Pending Approval
↓
Face registered but visit not approved
↓
Wait for resident approval
```

### State 3: Visit Scheduled (Future)
```
✅ Face Recognition Ready
↓
Visit starts in X hours
↓
Can access after start time
```

### State 4: Access Active (Current)
```
🎯 Access Active
↓
Within visit window
↓
Can access building NOW
↓
Face recognition working
```

### State 5: Visit Expired
```
⏰ Visit Expired
↓
Past end time
↓
Contact resident for new visit
```

---

## 💡 Key Points

### For Residents:
✅ **MUST upload visitor face photo** - this is mandatory for access
✅ Best practices for face photos:
  - Good lighting
  - Clear front-facing shot
  - No glasses/hats if possible
  - High resolution

### For Visitors:
✅ Check face registration status before arriving
✅ Arrive within scheduled time window
✅ At entrance:
  - Look directly at camera
  - Remove glasses/hat
  - Good lighting on face
  - Stay still for 2-3 seconds

### For System:
✅ Face recognition happens automatically
✅ No manual intervention needed
✅ Logs all access attempts
✅ Alerts for unauthorized attempts

---

## 🔐 Security Features

1. **Time-Based Access**
   - Access only within scheduled window
   - Automatic expiry

2. **Face Matching**
   - Compares captured face with registered photo
   - High accuracy threshold

3. **Audit Trail**
   - All access attempts logged
   - Timestamps recorded
   - Resident can view history

4. **Alerts**
   - Failed recognition attempts
   - Multiple failed attempts
   - Out-of-window access attempts

---

## 🚫 What This System Does NOT Use

❌ QR Codes
❌ Access Cards
❌ PIN Codes
❌ Manual Check-ins
❌ Phone Apps for Access

**Only:** Facial Recognition + Time Window

---

## 📊 Backend API Flow

### When Visitor Arrives:

```
1. Camera captures face
   ↓
2. POST /api/resident/offline/recognize
   {
     "device_id": "entrance-camera-1",
     "image_data": "base64_face_image"
   }
   ↓
3. Backend processes:
   - Extract face features
   - Compare with all registered visitors
   - Check time window
   - Verify approval status
   ↓
4. Response:
   {
     "matched_visitor_id": 101,
     "access": "GRANTED",
     "visitor_name": "John Doe"
   }
   ↓
5. Door System:
   - If GRANTED → Unlock door
   - If DENIED → Keep locked, send alert
```

---

## 🎯 Implementation Notes

### Current Implementation:
- ✅ Visitor face upload by resident
- ✅ Visitor status dashboard
- ✅ Face registration status display
- ✅ Time window validation
- ✅ Access instructions

### For Production:
- 🔧 Connect to actual face recognition engine
- 🔧 Integrate with door lock system
- 🔧 Real-time camera feed processing
- 🔧 Advanced face matching algorithms
- 🔧 Liveness detection (prevent photo spoofing)

---

**This is a pure facial recognition system - convenient, secure, and touchless!**
