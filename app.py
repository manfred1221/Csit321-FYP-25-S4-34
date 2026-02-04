import os

from routes.security_officer.security_officer_controller import ENABLE_GAN_ATTACK
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

from flask import Flask, request, jsonify, session, render_template, redirect, url_for, send_from_directory, Response
from flask_cors import CORS
from functools import wraps
import logging
from werkzeug.utils import secure_filename
import uuid
from jinja2 import ChoiceLoader, FileSystemLoader
from datetime import datetime, timedelta
import numpy as np


from config import Config
# from db import get_db_connection
from user import User, Resident
from access_log import AccessLog
from psycopg2.extras import RealDictCursor
from database import DATABASE_URL, get_db_connection

# Security Officer imports
try:
    from routes.security_officer.security_officer_model import SecurityOfficer, db, FaceEmbedding, log_access, Visitor, AccessLog
    from routes.security_officer.security_officer_controller import (
        image_to_embedding,
        monitor_camera,
        manual_override,
        view_profile,
        update_profile,
        delete_account,
        deactivate_account,
        verify_face as face_verify
    )
    SECURITY_OFFICER_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Security officer modules not available: {e}")
    SECURITY_OFFICER_AVAILABLE = False

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Support both frontend and templates folders
app.jinja_loader = ChoiceLoader([
    FileSystemLoader((os.path.join(BASE_DIR, 'templates'))),
    FileSystemLoader((os.path.join(BASE_DIR, 'frontend'))),
])

app.config['SECRET_KEY'] = Config.SECRET_KEY
app.config['PERMANENT_SESSION_LIFETIME'] = Config.SESSION_LIFETIME
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
CORS(app)

# ============================================================
# REGISTER BCE BLUEPRINT - Uses clean 3-layer architecture
# ============================================================
try:
    from boundary import staff_bp
    app.register_blueprint(staff_bp, url_prefix='/api/staff')
    logger.info("✅ Staff BCE blueprint registered at /api/staff")
except ImportError as e:
    logger.error(f"❌ Could not import staff blueprint: {e}")
# ============================================================
# ============================================================
# REGISTER RESIDENT BLUEPRINTS - For resident portal
# ============================================================
try:
    from routes.auth_routes import auth_bp
    from routes.resident_routes import resident_bp
    from routes.visitor_routes import visitor_bp
    
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(resident_bp, url_prefix='/api/resident')
    app.register_blueprint(visitor_bp, url_prefix='/api/visitor')
    
    logger.info("✅ Resident blueprints registered:")
    logger.info("   - /api/auth (authentication)")
    logger.info("   - /api/resident (resident features)")
    logger.info("   - /api/visitor (visitor management)")
except ImportError as e:
    logger.error(f"❌ Could not import resident blueprints: {e}")
# ============================================================
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('admin_login'))
        user = User.get_by_id(session['user_id'])
        if not user or user['role'] != 'Admin':
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated

def check_user_has_face_embedding(user):
    """Check if user has a registered face embedding"""
    if not user:
        return None

    user_role = user.get('role', '').lower()
    user_id = user.get('id')

    try:
        from psycopg2.extras import RealDictCursor
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Determine user type and reference ID based on role
        if user_role == 'admin':
            user_type = 'admin'
            reference_id = user_id
        elif user_role in ['internal_staff', 'staff', 'temp_worker']:
            user_type = 'staff'
            reference_id = user_id
        elif user_role == 'resident':
            user_type = 'resident'
            resident_id = user.get('resident_id')
            if not resident_id:
                cursor.close()
                conn.close()
                return None
            reference_id = resident_id
        else:
            cursor.close()
            conn.close()
            return None

        cursor.execute("""
            SELECT embedding_id FROM face_embeddings
            WHERE reference_id = %s AND user_type = %s
            LIMIT 1
        """, (reference_id, user_type))
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        return result['embedding_id'] if result else None
    except Exception as e:
        logger.error(f"Error checking face embedding: {e}")
        return None


# ============================================
# AUTHENTICATION ROUTES
# ============================================



@app.route('/')
def index():
    """Redirect to unified login page"""
    return redirect(url_for('unified_login'))

@app.route('/login', methods=['GET'])
def unified_login():
    """Serve unified login page for all user types"""
    # Clear any existing session
    session.clear()
    return send_from_directory('templates', 'login.html')

@app.route('/admin/login', methods=['POST'])
def admin_login():
    """
    Unified login - routes based on role_id from database.
    role_id 1 = Admin
    role_id 2 = Resident  
    role_id 3 = Visitor/Internal Staff
    role_id 4 = Security Officer
    """
    
    data = request.json or {}
    username = data.get('username', '').strip()
    password = data.get('password', '')
    
    if not username:
        return jsonify({'success': False, 'message': 'Username is required'}), 400

    logger.info(f"🔑 Login attempt: username={username}")

    # ============================================================
    # 1. TRY SECURITY OFFICER (numeric username = officer_id)
    # ============================================================
    if username.isdigit() and SECURITY_OFFICER_AVAILABLE:
        try:
            officer = SecurityOfficer.query.get(int(username))
            if officer and officer.active:
                session['officer_id'] = officer.officer_id
                session['officer_name'] = officer.full_name
                session['role'] = 'security_officer'
                session.permanent = True
                
                logger.info(f"✅ Security officer login: officer_id={officer.officer_id}")
                
                return jsonify({
                    'success': True,
                    'role': 'security_officer',
                    'user_data': {
                        'officer_id': officer.officer_id,
                        'full_name': officer.full_name
                    },
                    'redirect': '/security-dashboard'
                }), 200
        except Exception as e:
            logger.debug(f"Security officer check failed: {e}")
            pass

    # ============================================================
    # 2. AUTHENTICATE FROM users TABLE
    # ============================================================
    try:
        user = User.authenticate(username, password)
    except Exception as e:
        logger.error(f"❌ Authentication failed: {e}")
        user = None

    if not user:
        logger.warning(f"❌ Login failed: {username} - Invalid credentials")
        return jsonify({'success': False, 'message': 'Invalid username or password'}), 401

    # Extract user info
    role_id = user.get('role_id')
    role_name = user.get('role', '')
    user_id = user.get('id')
    
    logger.info(f"✅ User found: {username} | user_id={user_id} | role_id={role_id} | role_name={role_name}")

    # ============================================================
    # ROUTE BASED ON role_id (THE KEY!)
    # ============================================================
    
    # 🔴 ADMIN (role_id = 1)
    if role_id == 1:
        session['user_id'] = user_id
        session['username'] = user['username']
        session['role'] = 'Admin'
        session.permanent = True
        
        logger.info(f"✅ Admin logged in: {username}")
        
        return jsonify({
            'success': True,
            'role': 'Admin',
            'user_data': {
                'user_id': user_id,
                'username': user['username'],
                'full_name': user.get('full_name')
            },
            'redirect': '/admin/profile'
        }), 200

    # 🟢 RESIDENT (role_id = 2)
    elif role_id == 2:
        resident_id = user.get('resident_id')
        
        if not resident_id:
            logger.warning(f"⚠️ Resident {username} has no resident_id, using user_id")
            resident_id = user_id
        
        session['user_id'] = user_id
        session['resident_id'] = resident_id
        session['username'] = user['username']
        session['role'] = 'Resident'
        session.permanent = True
        
        logger.info(f"✅ Resident logged in: {username} | resident_id={resident_id}")
        
        return jsonify({
            'success': True,
            'role': 'Resident',
            'user_data': {
                'user_id': user_id,
                'resident_id': resident_id,
                'username': user['username'],
                'full_name': user.get('full_name', user['username'])
            },
            'redirect': f'/resident/dashboard?resident_id={resident_id}'
        }), 200

    # 🟡 VISITOR or INTERNAL STAFF (role_id = 3)
    elif role_id == 3 or role_id == 9:
        # Check if it's a visitor or internal staff based on role_name
        if 'visitor' in role_name.lower():
            # VISITOR
            visitor_id = user_id  # Assuming user_id maps to visitor
            
            session['user_id'] = user_id
            session['visitor_id'] = visitor_id
            session['username'] = user['username']
            session['role'] = 'Visitor'
            session.permanent = True
            
            logger.info(f"✅ Visitor logged in: {username}")
            
            return jsonify({
                'success': True,
                'role': 'Visitor',
                'user_data': {
                    'user_id': user_id,
                    'visitor_id': visitor_id,
                    'username': user['username']
                },
                'redirect': f'/visitor/dashboard?visitor_id={visitor_id}'
            }), 200
        else:
            # INTERNAL STAFF
            staff_id = user_id
            
            session['user_id'] = user_id
            session['staff_id'] = staff_id
            session['username'] = user['username']
            session['role'] = 'Internal_Staff'
            session.permanent = True
            
            logger.info(f"✅ Internal Staff logged in: {username}")
            
            return jsonify({
                'success': True,
                'role': 'Internal_Staff',
                'user_data': {
                    'user_id': user_id,
                    'staff_id': staff_id,
                    'username': user['username']
                },
                'redirect': f'/staff/dashboard?staff_id={staff_id}'
            }), 200

    # 🔵 SECURITY OFFICER via users table (role_id = 4)
    elif role_id == 4:
        session['user_id'] = user_id  # The ID from the 'users' table (e.g., 7)
        session['username'] = user['username']
        session['role'] = 'security_officer'
        
        # ✅ NEW: Fetch the REAL officer_id from the security_officers table
        # We use the user_id to find the linked profile
        officer_profile = SecurityOfficer.query.filter_by(user_id=user_id).first()
        
        if officer_profile:
            # Store the ACTUAL officer_id (e.g., 1)
            session['officer_id'] = officer_profile.officer_id 
            session['officer_name'] = officer_profile.full_name
        else:
            # Fallback: If no profile exists yet, use user_id to prevent crashes
            # (You should probably create the profile if it's missing)
            logger.warning(f"⚠️ User {username} has no Security Officer profile!")
            session['officer_id'] = user_id 

        session.permanent = True
        
        logger.info(f"✅ Security Officer logged in: {username}")
        
        return jsonify({
            'success': True,
            'role': 'security_officer',
            'redirect': '/security-dashboard'
        }), 200

    # ⚫ UNKNOWN ROLE
    else:
        logger.error(f"❌ Unknown role_id: {role_id} for user {username}")
        return jsonify({
            'success': False,
            'message': f'Your account type (role_id: {role_id}) is not configured. Contact administrator.'
        }), 401

    

@app.route('/admin/logout')
def admin_logout():
    """Admin logout - User Story: Logout so no one can use account"""
    session.clear()
    return redirect(url_for('admin_login'))


# ============================================
# FRONTEND ROUTES - Serve HTML files for all roles
# ============================================

# Serve main login page
@app.route('/login')
def frontend_login():
    """Serve the main login page for all user types"""
    return send_from_directory('frontend', 'index.html')

# Resident Routes
@app.route('/resident/dashboard')
def resident_dashboard():
    """Serve resident dashboard"""
    if 'user_id' not in session or session.get('role') != 'Resident':
        return redirect(url_for('unified_login'))
    return send_from_directory('frontend', 'resident-dashboard.html')

@app.route('/resident/profile')
def resident_profile():
    """Serve resident profile page"""
    if 'user_id' not in session or session.get('role') != 'Resident':
        return redirect(url_for('unified_login'))
    return send_from_directory('frontend', 'resident-profile.html')

@app.route('/resident/face-registration')
def resident_face_registration():
    """Serve resident face registration page"""
    if 'user_id' not in session or session.get('role') != 'Resident':
        return redirect(url_for('unified_login'))
    return send_from_directory('frontend', 'resident-face-registration.html')

@app.route('/resident/visitors')
def resident_visitors():
    """Serve resident visitors management page"""
    if 'user_id' not in session or session.get('role') != 'Resident':
        return redirect(url_for('unified_login'))
    return send_from_directory('frontend', 'resident-visitors.html')

@app.route('/resident/access-history')
def resident_access_history():
    """Serve resident access history page"""
    if 'user_id' not in session or session.get('role') != 'Resident':
        return redirect(url_for('unified_login'))
    return send_from_directory('frontend', 'resident-access-history.html')

@app.route('/resident/alerts')
def resident_alerts():
    """Serve resident alerts page"""
    if 'user_id' not in session or session.get('role') != 'Resident':
        return redirect(url_for('unified_login'))
    return send_from_directory('frontend', 'resident-alerts.html')

# Visitor Routes
@app.route('/frontend/visitor-dashboard.html')
@app.route('/visitor/dashboard')
def visitor_dashboard():
    """Serve visitor dashboard"""
    if 'user_id' not in session or session.get('role') != 'Visitor':
        return redirect(url_for('unified_login'))
    return send_from_directory('frontend', 'visitor-dashboard.html')

# Staff Routes 
@app.route('/frontend/staff-dashboard.html')
@app.route('/staff/dashboard')
def staff_dashboard():
    """Serve staff dashboard"""
    if 'user_id' not in session or session.get('role') != 'Internal_Staff':
        return redirect(url_for('unified_login'))
    return send_from_directory('frontend', 'staff-dashboard.html')

@app.route('/frontend/staff-profile.html')
@app.route('/staff/profile')
def staff_profile():
    """Serve staff profile page"""
    if 'user_id' not in session or session.get('role') != 'Internal_Staff':
        return redirect(url_for('unified_login'))
    return send_from_directory('frontend', 'staff-profile.html')

@app.route('/frontend/staff-schedule.html')
@app.route('/staff/schedule')
def staff_schedule():
    """Serve staff schedule page"""
    if 'user_id' not in session or session.get('role') != 'Internal_Staff':
        return redirect(url_for('unified_login'))
    return send_from_directory('frontend', 'staff-schedule.html')

@app.route('/frontend/staff-attendance.html')
@app.route('/staff/attendance')
def staff_attendance():
    """Serve staff attendance page"""
    if 'user_id' not in session or session.get('role') != 'Internal_Staff':
        return redirect(url_for('unified_login'))
    return send_from_directory('frontend', 'staff-attendance.html')

@app.route('/frontend/staff-face-enroll.html')
@app.route('/staff/face-enroll')
def staff_face_enroll():
    """Serve staff face enrollment page"""
    return send_from_directory('frontend', 'staff-face-enroll.html')

# Security Officer Routes
def officer_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'officer_id' not in session or session.get('role') != 'security_officer':
            return redirect(url_for('unified_login'))
        return f(*args, **kwargs)
    return decorated



@app.route("/security-dashboard")
@officer_required
def security_dashboard():
    """Security officer dashboard - verified via decorator"""
    # The decorator already ensures session['officer_id'] exists
    officer_id = session.get('officer_id')
    officer = SecurityOfficer.query.get(officer_id)
    
    # If for some reason the DB record is gone, clear session and exit
    if not officer:
        session.clear()
        return redirect(url_for('unified_login'))
    
    access_logs = AccessLog.query.order_by(AccessLog.log_id.desc()).limit(50).all()
    granted_count = AccessLog.query.filter_by(access_result='granted').count()
    
    return render_template("security-dashboard.html", 
                         officer=officer, 
                         logs=access_logs, 
                         granted_count=granted_count)

@app.route("/security-deactivate")
@officer_required
def deactivate():
    officer = SecurityOfficer.query.get(session['officer_id'])
    return render_template("security-deactivate.html", officer=officer)

@app.route("/security-override")
@officer_required
def manual_override():
    officer = SecurityOfficer.query.get(session['officer_id'])
    return render_template("security-override.html", officer=officer)

@app.route("/security-view-profile")
@officer_required
def view_profile():
    officer = SecurityOfficer.query.get(session['officer_id'])
    return render_template("security-view-profile.html", officer=officer)


@app.route("/security-update-profile", methods=["GET", "POST"])
@officer_required
def update_profile():   
    officer = SecurityOfficer.query.get(session['officer_id'])
    return render_template("security-update-profile.html", officer=officer)

@app.route("/api/update-officer", methods=["POST"])
@officer_required
def api_update_officer():
    data = request.json
    officer = SecurityOfficer.query.get(session['officer_id'])

    officer.full_name = data.get("full_name", officer.full_name)
    officer.contact_number = data.get("contact_number", officer.contact_number)
    officer.shift = data.get("shift", officer.shift)

    db.session.commit()
    return jsonify({"success": True, "message": "Profile updated"}), 200

@app.route("/security-face-verification")
@officer_required
def face_verification():
    officer = SecurityOfficer.query.get(session['officer_id'])

    logs = AccessLog.query.order_by(AccessLog.access_time.desc()).limit(10).all()
    threshold = 0.65

    # Fetch all logs for today
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    logs = AccessLog.query.filter(AccessLog.access_time >= today_start).order_by(AccessLog.access_time.desc()).all()

    success_count = 0
    fail_count = 0
    total_time = 0.0
    count_time = 0

    # Prepare data for template
    log_data = []
    for log in logs:
        confidence = log.confidence or 0
        verified = confidence >= threshold

        if verified:
            success_count += 1
        else:
            fail_count += 1

        # optional: track average verification time if stored
        if hasattr(log, "verification_time") and log.verification_time:
            total_time += log.verification_time
            count_time += 1

        log_data.append({
            "time": log.access_time.strftime("%H:%M:%S"),
            "person": log.recognized_person,
            "type": log.person_type.capitalize(),
            "confidence": round(confidence * 100, 2),
            "verified": verified,
            "officer": officer.full_name
        })

    avg_time = round(total_time / count_time, 2) if count_time else 0

    return render_template(
        "security-face-verification.html",
        officer=officer,
        access_logs=log_data,
        success_count=success_count,
        fail_count=fail_count,
        avg_time=avg_time,
        threshold=threshold
    )

@app.route("/security/logout")
def security_logout():
    """Security officer logout"""
    session.clear()
    return redirect(url_for('unified_login'))


@app.route('/frontend/index.html')
def frontend_login_redirect():
    """Redirect old frontend login to unified login"""
    return redirect(url_for('unified_login'))

# Serve CSS and other static assets from frontend folder
@app.route('/frontend/css/<path:filename>')
def frontend_css(filename):
    """Serve CSS files from frontend/css"""
    return send_from_directory('frontend/css', filename)

@app.route('/templates/css/<path:filename>')
def template_css(filename):
    return send_from_directory(os.path.join(app.root_path, 'templates', 'css'), filename)

@app.route('/frontend/js/<path:filename>')
def frontend_js(filename):
    """Serve JavaScript files from frontend/js"""
    return send_from_directory('frontend/js', filename)

@app.route('/frontend/<path:filename>')
def frontend_static(filename):
    """Serve other static files from frontend folder"""
    return send_from_directory('frontend', filename)


# ============================================
# AUTH ROUTES (from auth_routes.py)
# ============================================

@app.route("/api/auth/login", methods=["POST"])
def auth_login():
    """UC-R6 Login - Resident authentication"""
    data = request.get_json(silent=True) or {}
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400

    # Authenticate against real database
    user = User.authenticate(username, password)

    if not user:
        return jsonify({"error": "Invalid username or password"}), 401

    # Check if user is a resident
    if user["role"] not in ["Resident", "RESIDENT"]:
        return jsonify({"error": "Invalid username or password"}), 401

    # In future generate JWT here
    token = "fake-token-123"

    return jsonify({
        "user_id": user["id"],
        "resident_id": user.get("resident_id"),
        "username": user["username"],
        "role": user["role"],
        "token": token,
        "message": "Login successful",
    }), 200

@app.route("/api/auth/logout", methods=["POST"])
def auth_logout():
    """UC-R7 Logout"""
    return jsonify({"message": "Logout successful (mock)"}), 200

@app.route("/api/staff/login", methods=["POST"])
def staff_login():
    """Staff authentication"""
    data = request.get_json(silent=True) or {}
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400

    # Authenticate against real database
    user = User.authenticate(username, password)

    if not user:
        return jsonify({"error": "Invalid username or password"}), 401

    # Check if user is internal staff
    if user["role"] not in ["Internal_Staff", "INTERNAL_STAFF", "Staff"]:
        return jsonify({"error": "Invalid username or password"}), 401

    # Generate token
    token = "fake-staff-token-123"

    return jsonify({
        "user_id": user["id"],
        "staff_id": user.get("id"),
        "username": user["username"],
        "role": user["role"],
        "token": token,
        "message": "Login successful",
        "name": user.get("username"),
        "email": user.get("email", "")
    }), 200

@app.route('/api/auth/check-session', methods=['GET'])
def check_session():
    """Check if user is authenticated via Flask session"""
    uid = session.get('user_id') or session.get('officer_id')
    
    if not uid:
        return jsonify({'authenticated': False}), 401
    
    user_data = {
        'user_id': session.get('user_id'),
        'username': session.get('username'),
        'role': session.get('role'),
        'resident_id': session.get('resident_id'),
        'visitor_id': session.get('visitor_id'),
        'officer_id': session.get('officer_id'),
        'staff_id': session.get('staff_id')
    }
    
    # Remove None values
    user_data = {k: v for k, v in user_data.items() if v is not None}
    
    return jsonify({'authenticated': True, 'user': user_data}), 200


@app.route('/api/auth/logout', methods=['POST'])
def api_logout():
    """Logout endpoint - clears Flask session"""
    session.clear()
    return jsonify({'success': True, 'message': 'Logged out'}), 200






# ============================================
# SECURITY OFFICER ROUTES (from security_officer_routes.py)
# ============================================

if SECURITY_OFFICER_AVAILABLE:
    @app.route("/api/security_officer/manual_override", methods=["POST"])
    def route_manual_override():
        data = request.get_json() or {}
        officer_id = data.get("officer_id")
        result = manual_override(officer_id)
        return jsonify(result)

    @app.route("/api/security_officer/profile/<int:officer_id>", methods=["GET"])
    def get_profile(officer_id):
        officer = SecurityOfficer.query.get(officer_id)
        if not officer:
            return {"status": "error", "message": "Officer not found"}, 404
        return {
            "status": "success",
            "officer": {
                "officer_id": officer.officer_id,
                "full_name": officer.full_name,
                "contact_number": officer.contact_number,
                "shift": officer.shift
            }
        }

    @app.route("/api/security_officer/profile/<int:officer_id>", methods=["PUT"])
    def route_update_profile(officer_id):
        return update_profile(officer_id, request.json)

    @app.route("/api/security_officer/account/<int:officer_id>", methods=["DELETE"])
    def route_delete_account(officer_id):
        return delete_account(officer_id)

    @app.route("/api/security_officer/face_verify", methods=["POST"])
    def verify_face_route():
        return face_verify()

    @app.route("/api/security_officer/deactivate_account/<int:officer_id>", methods=["POST"])
    def route_deactivate_account(officer_id):
        data = request.get_json()
        password = data.get("password")

        if not password:
            return jsonify({"error": "Password is required to deactivate"}), 400

        officer = SecurityOfficer.query.get(officer_id)
        if not officer:
            return jsonify({"error": "Officer not found"}), 404

        # Check password (plain-text for now)
        if not officer.user or officer.user.password_hash != password:
            return jsonify({"error": "Password incorrect"}), 401

        # Deactivate officer
        officer.active = False  # your security_officers table is boolean, so False is fine

        # Deactivate linked user (string column: "active"/"inactive")
        officer.user.status = "inactive"  # <- important: set string, not False

        db.session.commit()

        return jsonify({"message": f"Officer {officer.full_name} deactivated successfully"})

    @app.route("/api/security_officer/monitor_camera")
    def route_monitor_camera():
        return monitor_camera()

    @app.route("/api/security_officer/test", methods=["GET"])
    def security_officer_test_route():
        return jsonify({"status": "ok"})

    @app.route("/api/security_officer/register_officer", methods=["POST"])
    def register_officer():
        """Completes registration for new officer"""
        data = request.get_json()
        officer_id = data.get("officer_id")
        full_name = data.get("full_name")
        contact_number = data.get("contact_number")
        shift = data.get("shift")
        image_base64 = data.get("image")

        if not all([officer_id, full_name, image_base64]):
            return jsonify({"status": "error", "message": "Missing required fields"}), 400

        officer = SecurityOfficer.query.get(officer_id)
        if not officer:
            return jsonify({"status": "error", "message": "Officer not found"}), 404

        officer.full_name = full_name
        officer.contact_number = contact_number
        officer.shift = shift
        db.session.commit()

        embedding_vector = image_to_embedding(image_base64)
        new_embedding = FaceEmbedding(
            user_type="security_officer",
            reference_id=officer_id,
            embedding=embedding_vector
        )
        db.session.add(new_embedding)
        db.session.commit()

        log_access(
            recognized_person=full_name,
            person_type="security_officer",
            confidence=1.0,
            result="granted",
            embedding_id=new_embedding.embedding_id
        )

        return jsonify({
            "status": "success",
            "message": f"Officer {full_name} registered",
            "officer_id": officer_id
        }), 200

    RATE_LIMIT = {}
    MAX_ATTEMPTS = 10
    WINDOW_SECONDS = 60


    def normalize(vec):
        vec = np.array(vec, dtype=np.float32)
        return vec / np.linalg.norm(vec)


    def cosine_similarity(a, b):
        return float(np.dot(a, b))


    @app.route("/api/security_officer/verify_face", methods=["POST"])
    def verify_face():

        try:
            data = request.get_json(force=True)
            image_base64 = data.get("image")

            officer_id = session.get("officer_id")

            if not officer_id:
                return jsonify({
                    "status": "error",
                    "message": "Session expired. Please login again."
                }), 401

            if not image_base64:
                return jsonify({
                    "status": "error",
                    "message": "Missing image"
                }), 400

            officer = SecurityOfficer.query.get(officer_id)
            if not officer or not officer.active:
                return jsonify({
                    "status": "error",
                    "message": "Unauthorized officer"
                }), 403

            # --- Generate embedding ---
            raw_embedding = image_to_embedding(image_base64)

            if raw_embedding is None:
                return jsonify({
                    "status": "error",
                    "message": "No face detected. Please try again."
                }), 400

            query_embedding = normalize(raw_embedding)

            embeddings = FaceEmbedding.query.filter(
                FaceEmbedding.user_type.in_(["resident", "visitor"])
            ).all()

            threshold = 0.65
            best_match = None
            best_score = 0.0

            for fe in embeddings:

                if fe.embedding is None or fe.reference_id is None:
                    continue

                db_embedding = np.array(fe.embedding, dtype=np.float32)
                if db_embedding.size != 512:
                    continue

                db_embedding = normalize(db_embedding)
                score = cosine_similarity(query_embedding, db_embedding)

                if score > best_score:
                    best_score = score
                    best_match = fe

            # ===============================
            # MATCH FOUND
            # ===============================
            if best_match and best_score >= threshold:

                if best_match.user_type == "resident":
                    from routes.security_officer.security_officer_model import Resident
                    person = Resident.query.get(best_match.reference_id)
                else:
                    person = Visitor.query.get(best_match.reference_id)

                # 🔒 CRITICAL SAFETY CHECK
                if person is None:
                    log_access(
                        recognized_person="Invalid reference",
                        person_type=best_match.user_type,
                        confidence=best_score,
                        result="denied",
                        embedding_id=best_match.embedding_id,
                        attack_type="gan_impersonation" if ENABLE_GAN_ATTACK else "none"
                    )

                    return jsonify({
                        "status": "error",
                        "result": "denied",
                        "message": "Matched embedding has no valid identity",
                        "confidence": float(round(best_score * 100, 2))
                    }), 401

                # ✅ VALID MATCH
                log_access(
                    recognized_person=person.full_name,
                    person_type=best_match.user_type,
                    confidence=best_score,
                    result="granted",
                    embedding_id=best_match.embedding_id,
                    attack_type="gan_impersonation" if ENABLE_GAN_ATTACK else "none"
                )

                return jsonify({
                    "status": "success",
                    "result": "granted",
                    "type": best_match.user_type.capitalize(),
                    "person_type": best_match.user_type,
                    "name": person.full_name,
                    "message": "Face recognized",
                    "confidence": float(round(best_score * 100, 2))
                })

            # ===============================
            # NO MATCH
            # ===============================
            log_access(
                recognized_person="Unknown",
                person_type="unknown",
                confidence=best_score,
                result="denied",
                embedding_id=None,
                attack_type="gan_impersonation" if ENABLE_GAN_ATTACK else "none"
            )

            return jsonify({
                "status": "error",
                "result": "denied",
                "message": "Face not recognized",
                "confidence": float(round(best_score * 100, 2))
            }), 401

        except Exception as e:
            print("VERIFY FACE ERROR:", str(e))
            return jsonify({
                "status": "error",
                "message": "Internal server error during face verification"
            }), 500


    @app.route("/api/security_officer/upload_face_embedding", methods=["POST"])
    def upload_face_embedding():
        try:
            image_file = request.files['image']
            user_type = request.form['user_type']
            reference_id = int(request.form['reference_id'])

            filename = secure_filename(image_file.filename)
            save_path = os.path.join("static/uploads", filename)
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            image_file.save(save_path)

            embedding_vector = [0.0]*512

            new_embedding = FaceEmbedding(
                user_type=user_type,
                reference_id=reference_id,
                embedding=embedding_vector,
                image_filename=filename
            )
            db.session.add(new_embedding)
            db.session.commit()

            return jsonify({"status": "success", "message": "Face embedding stored", "embedding_id": new_embedding.embedding_id})

        except Exception as e:
            db.session.rollback()
            return jsonify({"status": "error", "message": str(e)}), 500

    @app.route("/api/security_officer/login", methods=["POST"])
    def security_officer_login():
        data = request.get_json()
        user_type = data.get("user_type")
        user_id = data.get("user_id")

        if not user_type or not user_id:
            return jsonify({"success": False, "message": "Missing login data"}), 400

        if user_type == "security_officer":
            user = SecurityOfficer.query.get(user_id)
            if not user:
                return jsonify({"success": False, "message": "Officer ID not found"}), 404

            return jsonify({
                "success": True,
                "message": "Login successful",
                "user_type": "security_officer",
                "id": user.officer_id,
                "name": user.full_name
            }), 200

        elif user_type == "resident":
            from routes.security_officer.security_officer_model import Resident as SOResident
            user = SOResident.query.get(user_id)
            if not user:
                return jsonify({"success": False, "message": "Resident ID not found"}), 404

            return jsonify({
                "success": True,
                "message": "Login successful",
                "user_type": "resident",
                "id": user.resident_id,
                "name": user.full_name
            }), 200

        elif user_type == "visitor":
            user = Visitor.query.get(user_id)
            if not user:
                return jsonify({"success": False, "message": "Visitor ID not found"}), 404

            return jsonify({
                "success": True,
                "message": "Login successful",
                "user_type": "visitor",
                "id": user.visitor_id,
                "name": user.full_name
            }), 200

        else:
            return jsonify({"success": False, "message": "Invalid user type"}), 400
        
    @app.route("/api/security_officer/change_password", methods=["POST"])
    @officer_required
    def change_password():
        from sqlalchemy import text
        data = request.get_json()

        current_password = data.get("current_password")
        new_password = data.get("new_password")

        if not current_password or not new_password:
            return jsonify({"error": "Missing fields"}), 400

        officer = SecurityOfficer.query.get(session["officer_id"])
        
        # user = User.query.get(officer.user_id)
        # if not user:
        #     return jsonify({"error": "Linked user not found"}), 404

        # ✅ Plain-text comparison
        if officer.user.password_hash != current_password:
            return jsonify({"error": "Current password is incorrect"}), 401
        
        # Update the user's password
        officer.user.password_hash = new_password
        db.session.commit()

        return jsonify({"message": "Password updated successfully"})


@app.route('/api/staff/<int:staff_id>/schedule', methods=['GET'])
def get_staff_schedule(staff_id):
    """Get staff schedule from temp_workers table"""
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        query = """
            SELECT user_id, work_start_date, work_end_date, 
                   work_schedule, work_details
            FROM temp_workers
            WHERE user_id = %s
        """
        params = [staff_id]
        
        if start_date and end_date:
            query += " AND work_start_date <= %s AND work_end_date >= %s"
            params.extend([end_date, start_date])
        
        query += " ORDER BY work_start_date"
        
        cur.execute(query, params)
        schedules = cur.fetchall()
        
        cur.close()
        conn.close()
        
        schedule_list = []
        for schedule in schedules:
            # Parse work_schedule (e.g., "Mon-Fri 0800-1700")
            work_schedule = schedule.get('work_schedule', '')
            shift_start = '08:00'
            shift_end = '17:00'
            
            # Try to extract time from work_schedule
            if work_schedule:
                # Example: "Mon-Fri 0800-1700" or "1000hrs"
                import re
                time_match = re.search(r'(\d{4})-(\d{4})', work_schedule)
                if time_match:
                    start_time = time_match.group(1)
                    end_time = time_match.group(2)
                    shift_start = f"{start_time[:2]}:{start_time[2:]}"
                    shift_end = f"{end_time[:2]}:{end_time[2:]}"
                else:
                    # Try "1000hrs" format
                    hrs_match = re.search(r'(\d{3,4})hrs?', work_schedule)
                    if hrs_match:
                        time_str = hrs_match.group(1).zfill(4)
                        shift_start = f"{time_str[:2]}:{time_str[2:]}"
                        shift_end = f"{int(time_str[:2])+8:02d}:{time_str[2:]}"
            
            schedule_list.append({
                'schedule_id': schedule.get('user_id'),
                'shift_date': schedule['work_start_date'].strftime('%Y-%m-%d') if schedule.get('work_start_date') else None,
                'shift_start': shift_start,
                'shift_end': shift_end,
                'task_description': schedule.get('work_details', 'Work shift'),
                'location': 'Main Office'
            })
        
        return jsonify({
            'success': True,
            'data': {'schedules': schedule_list}
        })
        
    except Exception as e:
        logger.error(f"Error fetching schedule: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    
@app.route('/api/staff/<int:staff_id>/attendance', methods=['GET'])
def get_staff_attendance(staff_id):
    """Get staff attendance history"""
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        query = """
            SELECT attendance_id, entry_time, exit_time, duration_hours,
                   location, verification_method
            FROM staff_attendance
            WHERE staff_id = %s
        """
        params = [staff_id]
        
        if start_date and end_date:
            query += " AND DATE(entry_time) BETWEEN %s AND %s"
            params.extend([start_date, end_date])
        
        query += " ORDER BY entry_time DESC"
        
        cur.execute(query, params)
        records = cur.fetchall()
        
        cur.close()
        conn.close()
        
        attendance_list = []
        for record in records:
            attendance_list.append({
                'attendance_id': record[0],
                'entry_time': record[1].isoformat() if record[1] else None,
                'exit_time': record[2].isoformat() if record[2] else None,
                'duration_hours': float(record[3]) if record[3] else None,
                'location': record[4],
                'verification_method': record[5]
            })
        
        return jsonify({
            'success': True,
            'data': {'records': attendance_list}
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================
# PROFILE ROUTES
# ============================================

@app.route('/admin')
@admin_required
def admin_dashboard():
    return redirect(url_for('admin_profile'))

@app.route('/admin/profile')
@admin_required
def admin_profile():
    try:
        user = User.get_by_id(session['user_id'])
        if not user:
            logger.error(f"admin_profile: User not found for session_id {session['user_id']}")
            return "User not found", 404

        user['face_encoding_path'] = check_user_has_face_embedding(user)
        return render_template('admin_profile.html', user=user)

    except Exception as e:
        logger.error(f"admin_profile error: {e}")
        return f"Internal Server Error: {e}", 500

@app.route('/admin/profile/update', methods=['POST'])
@admin_required
def admin_profile_update():
    """Update admin profile information"""
    user = User.get_by_id(session['user_id'])
    if not user:
        return jsonify({'success': False, 'message': 'User not found'}), 404

    data = request.json
    try:
        # Update user information
        update_data = {}
        if 'full_name' in data:
            update_data['full_name'] = data['full_name']
        if 'email' in data:
            update_data['email'] = data['email']
        if 'phone' in data:
            update_data['phone'] = data['phone']

        if update_data:
            User.update(session['user_id'], update_data)
            logger.info(f"Profile updated for user {user['id']}")
            return jsonify({'success': True, 'message': 'Profile updated successfully!'})
        else:
            return jsonify({'success': False, 'message': 'No fields to update'}), 400

    except Exception as e:
        logger.error(f"Profile update error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/admin/profile/upload', methods=['POST'])
@admin_required
def admin_profile_upload():
    """Upload face photo for the current admin user"""
    user = User.get_by_id(session['user_id'])
    if not user:
        return jsonify({'success': False, 'message': 'User not found'}), 404

    if 'photo' not in request.files:
        return jsonify({'success': False, 'message': 'No photo provided'}), 400

    photo = request.files['photo']

    if not photo or not allowed_file(photo.filename):
        return jsonify({'success': False, 'message': 'Invalid file type. Please use JPG or PNG.'}), 400

    try:
        filename = f"user_{user['id']}_{uuid.uuid4().hex}.jpg"
        photo_path = os.path.join(Config.FACE_RECOGNITION['upload_dir'], filename)
        photo.save(photo_path)

        from model import register_face_from_photo

        # For admin users, store face embedding directly with admin type
        # No need to create a resident record
        user_type = 'ADMIN'
        reference_id = user['id']

        embedding_id, error = register_face_from_photo(photo_path, reference_id, user_type)

        if error:
            os.remove(photo_path)
            return jsonify({'success': False, 'message': f'Face registration failed: {error}'}), 400

        logger.info(f"Face photo uploaded for admin user {user['id']}, embedding_id: {embedding_id}")
        return jsonify({'success': True, 'message': 'Photo uploaded and face registered successfully!', 'embedding_id': embedding_id})

    except Exception as e:
        logger.error(f"Profile photo upload error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


# ============================================
# USER MANAGEMENT ROUTES
# ============================================

@app.route('/admin/users')
@admin_required
def admin_users():
    """View all users - User Story: View all residents/temp workers"""
    role_filter = request.args.get('role', '')
    status_filter = request.args.get('status', '')

    users = User.get_all()

    if role_filter:
        users = [u for u in users if u.get('role') == role_filter]
    if status_filter:
        users = [u for u in users if u.get('status') == status_filter]

    return render_template('admin_users.html', users=users)

@app.route('/admin/users/<int:user_id>/edit', methods=["GET", "POST"])
@admin_required
def admin_users_edit(user_id):
    if request.method == "GET":
        user = User.get_by_id(user_id)
        if not user:
            return "User not found", 404
        return render_template('admin_edit_user.html', user=user)
    """Edit user page - User Story: Edit user details"""

    print("request.json", request.json)
    data = request.json

    data_dict = {
        'email': data['email'],
        'password': data['password'],
        'role': data['role'],
        'status': data.get('status'),
        'access_level': data.get('access_level', 'standard'),
        'full_name': data.get('full_name'),
        'phone': data.get('phone', ''),
        'unit_number': data.get('unit_number', 'N/A')
    }

    # Include temp worker fields if applicable
    if data['role'] == 'TEMP_WORKER':
        data_dict.update({
            'role': "temp_staff",
            'work_start_date': data.get('work_start_date'),
            'work_end_date': data.get('work_end_date'),
            'work_schedule': data.get('work_schedule', ''),
            'work_details': data.get('work_details', ''),
        })

    # Filter out None, empty strings, and other falsy values
    data_dict = {k: v for k, v in data_dict.items() if v not in (None, '', 'N/A')}
    print("data_dict", data_dict)

    User.update(user_id, data_dict)
    # print("user", user_id)
    user = User.get_by_id(user_id)

    print("user", user)
    if not user:
        return "User not found", 404

    return jsonify({'success': True, 'message': 'User updated successfully'})
    


@app.route('/admin/users/create', methods=['GET'])
@admin_required
def admin_users_add_page():
    """Render Add User form"""
    return render_template('admin_add_user.html')

@app.route('/admin/users/create', methods=['POST'])
@admin_required
def admin_users_create():
    """Create new user - User Story: Register new residents/temp workers"""
    data = request.json
    required = ['username', 'password', 'role']
    
    if not all(k in data for k in required):
        return jsonify({'success': False, 'message': 'Missing required fields'}), 400
    
    try:
        
        # Prepare dictionary for User.create
        data_dict = {
            'username': data['username'],
            'email': data['email'],
            'password': data['password'],
            'role': data['role'],
            'access_level': data.get('access_level', 'standard'),
            'full_name': data.get('full_name', data['username']),
            'phone': data.get('phone', ''),
            'unit_number': data.get('unit_number', 'N/A')
        }

        # Include temp worker fields if applicable
        if data['role'] == 'TEMP_WORKER':
            data_dict.update({
                'work_start_date': data.get('work_start_date'),
                'work_end_date': data.get('work_end_date'),
                'work_schedule': data.get('work_schedule', ''),
                'work_details': data.get('work_details', ''),
                'id_document_path': data.get('id_document_path')
            })

        user_id = User.create(data_dict)        
        # user_id = User.create(
        #     username=data['username'],
        #     password=data['password'],
        #     role=data['role'],
        #     full_name=data.get('full_name'),
        #     phone=data.get('phone'),
        #     unit_number=data.get('unit_number'),
        #     start_date=data.get('start_date'),
        #     end_date=data.get('end_date')
        # )
        return jsonify({'success': True, 'user_id': user_id})
    except Exception as e:
        logger.error(f"Create user error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/admin/users/<int:user_id>', methods=['PUT'])
@admin_required
def admin_users_update(user_id):
    """Update user - User Story: Edit resident/temp worker info"""
    data = request.json
    try:
        User.update(user_id, data)
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Update user error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/admin/users/<int:user_id>', methods=['DELETE'])
@admin_required
def admin_users_delete(user_id):
    """Delete user - User Story: Remove resident/temp worker"""
    try:
        User.delete(user_id)
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Delete user error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/admin/users/<int:user_id>/deactivate', methods=['POST'])
@admin_required
def admin_users_deactivate(user_id):
    """Deactivate user - User Story: Temporarily revoke access"""
    try:
        User.update(user_id, {'status': 'inactive'})
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Deactivate user error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/admin/users/<int:user_id>/reactivate', methods=['POST'])
@admin_required
def admin_users_reactivate(user_id):
    """Reactivate user - User Story: Restore access"""
    try:
        User.update(user_id, {'status': 'active'})
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Reactivate user error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/admin/users/<int:user_id>/upload-photo', methods=['POST'])
@admin_required
def admin_users_upload_photo(user_id):
    """Upload face photo for a user - User Story: Register face for facial recognition"""
    if 'photo' not in request.files:
        return jsonify({'success': False, 'message': 'No photo provided'}), 400

    photo = request.files['photo']

    if not photo or not allowed_file(photo.filename):
        return jsonify({'success': False, 'message': 'Invalid file type. Please use JPG or PNG.'}), 400

    try:
        user = User.get_by_id(user_id)
        if not user:
            return jsonify({'success': False, 'message': 'User not found'}), 404

        filename = f"user_{user_id}_{uuid.uuid4().hex}.jpg"
        photo_path = os.path.join(Config.FACE_RECOGNITION['upload_dir'], filename)
        photo.save(photo_path)

        from model import register_face_from_photo
        from psycopg2.extras import RealDictCursor

        user_role = user.get('role', '').lower()

        # Determine user type and reference ID based on role
        if user_role == 'admin':
            user_type = 'admin'
            reference_id = user_id
            embedding_id, error = register_face_from_photo(photo_path, reference_id, user_type)
        elif user_role in ['internal_staff', 'staff', 'temp_worker']:
            user_type = 'staff'
            reference_id = user_id
            embedding_id, error = register_face_from_photo(photo_path, reference_id, user_type)
        elif user_role == 'resident':
            # Only for residents, we need to ensure a resident record exists
            resident_id = user.get('resident_id')

            if not resident_id:
                conn = get_db_connection()
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                try:
                    cursor.execute("SELECT resident_id FROM residents WHERE user_id = %s", (user_id,))
                    existing = cursor.fetchone()

                    if existing:
                        resident_id = existing['resident_id']
                        logger.info(f"Found existing resident record: resident_id={resident_id}")
                    else:
                        cursor.execute("""
                            INSERT INTO residents (full_name, unit_number, contact_number, user_id)
                            VALUES (%s, %s, %s, %s)
                            RETURNING resident_id
                        """, (
                            user.get('full_name') or user.get('username') or f'User {user_id}',
                            user.get('unit_number') or 'N/A',
                            user.get('phone') or '',
                            user_id
                        ))
                        result = cursor.fetchone()
                        resident_id = result['resident_id']
                        conn.commit()
                        logger.info(f"Created resident record for user {user_id}: resident_id={resident_id}")
                except Exception as e:
                    conn.rollback()
                    os.remove(photo_path)
                    logger.error(f"Database error: {str(e)}")
                    return jsonify({'success': False, 'message': f'Failed to create resident record: {str(e)}'}), 400
                finally:
                    cursor.close()
                    conn.close()

            embedding_id, error = register_face_from_photo(photo_path, resident_id, 'resident')
        else:
            os.remove(photo_path)
            return jsonify({'success': False, 'message': f'Unsupported user role: {user_role}'}), 400

        if error:
            os.remove(photo_path)
            return jsonify({'success': False, 'message': f'Face registration failed: {error}'}), 400

        logger.info(f"Face photo uploaded for user {user_id} (role: {user_role}), embedding_id: {embedding_id}")
        return jsonify({'success': True, 'message': 'Photo uploaded successfully!', 'embedding_id': embedding_id})

    except Exception as e:
        logger.error(f"Upload error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/admin/users/<int:user_id>/upload-id-doc', methods=['POST'])
@admin_required
def admin_upload_id_doc(user_id):
    """Upload ID document - User Story: Register temp workers with ID documents"""
    if 'document' not in request.files:
        return jsonify({'success': False, 'message': 'No document provided'}), 400
    
    doc = request.files['document']
    
    if not doc or not allowed_file(doc.filename):
        return jsonify({'success': False, 'message': 'Invalid file type'}), 400
    
    try:
        ext = doc.filename.rsplit('.', 1)[1].lower()
        filename = f"id_doc_{user_id}_{uuid.uuid4().hex}.{ext}"
        doc_path = os.path.join(Config.FACE_RECOGNITION['id_doc_dir'], filename)
        doc.save(doc_path)
        
        User.update(user_id, {'id_document_path': filename})
        
        return jsonify({'success': True, 'message': 'ID document uploaded successfully!'})
    
    except Exception as e:
        logger.error(f"Upload ID doc error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


# ============================================
# ACCESS LOGS ROUTES
# ============================================

@app.route('/admin/logs')
@admin_required
def admin_logs():
    from access_log import AccessLog
    """View access logs - User Story: View entry and exit history"""
    user_filter = request.args.get('user_id', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    status_filter = request.args.get('status', '')
    
    logs = AccessLog.filter_logs(
        user_id=int(user_filter) if user_filter else None,
        date_from=date_from if date_from else None,
        date_to=date_to if date_to else None,
        status=status_filter if status_filter else None
    )
    
    users_for_filter = AccessLog.get_all_users_for_filter()
    
    return render_template('admin_logs.html', 
                         logs=logs,
                         users_for_filter=users_for_filter,
                         user_filter=user_filter,
                         date_from=date_from,
                         date_to=date_to,
                         status_filter=status_filter)


# ============================================
# TEMP WORKER MANAGEMENT
# ============================================

# @app.route('/admin/temp-workers')
# @admin_required
# def admin_temp_workers():
#     """View temporary workers with their schedules"""
#     users = User.get_all(role='TEMP_WORKER')
#     expiring_soon = User.get_expiring_temp_workers(days=7)
#     from datetime import date
#     today = date.today()
    
#     return render_template('admin_tempworker.html', 
#                          users=users, 
#                          expiring_soon=expiring_soon,
#                          today=today)

@app.route('/admin/temp-workers')
@admin_required
def admin_temp_workers():
    """View temporary workers with their schedules"""
    from datetime import date

    users = User.get_all(role='TEMP_WORKER')
    expiring_soon = User.get_expiring_temp_workers(days=7)
    today = date.today()

    for user in users:
        if user.work_end_date:
            user.days_left = (user.work_end_date.date() - today).days
        else:
            user.days_left = 0

    return render_template(
        'admin_tempworker.html',
        users=users,
        expiring_soon=expiring_soon,
        today=today
    )


@app.route('/admin/temp-workers/check-expired', methods=['POST'])
@admin_required
def admin_check_expired_temp_workers():
    """Manually check and deactivate expired temp workers"""
    try:
        count = User.check_expired_temp_workers()
        return jsonify({
            'success': True, 
            'message': f'Deactivated {count} expired temporary workers',
            'count': count
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


# ============================================
# RESIDENTS ROUTES
# ============================================

@app.route('/admin/residents')
@admin_required
def admin_residents():
    residents = Resident.get_all()
    return render_template('admin_residents.html', residents=residents)


# ============================================
# STATIC FILE ROUTES
# ============================================

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(Config.FACE_RECOGNITION['upload_dir'], filename)

@app.route('/id_documents/<filename>')
@admin_required
def id_document_file(filename):
    return send_from_directory(Config.FACE_RECOGNITION['id_doc_dir'], filename)


# ============================================
# API ROUTES FOR DASHBOARD
# ============================================

@app.route('/api/dashboard/stats')
@admin_required
def api_dashboard_stats():
    """Get dashboard statistics"""
    try:
        stats = AccessLog.get_stats(days=30)
        
        all_users = User.get_all()
        active_users = len([u for u in all_users if u.get('status') == 'active'])
        inactive_users = len([u for u in all_users if u.get('status') == 'inactive'])
        temp_workers = len([u for u in all_users if u.get('role') == 'TEMP_WORKER'])
        
        stats['total_users'] = len(all_users)
        stats['active_users'] = active_users
        stats['inactive_users'] = inactive_users
        stats['temp_workers'] = temp_workers
        
        return jsonify({'success': True, 'stats': stats})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


# ============================================
# INITIALIZATION
# ============================================

def init_app(app):
    # Create necessary folders
    os.makedirs(Config.FACE_RECOGNITION['upload_dir'], exist_ok=True)
    os.makedirs(Config.FACE_RECOGNITION['encoding_dir'], exist_ok=True)
    os.makedirs(Config.FACE_RECOGNITION['id_doc_dir'], exist_ok=True)

    # # Build DB URI from environment
    # dbname = os.getenv("DB_NAME", "CSIT321: Face Recognition")
    # user = os.getenv("DB_USER", "postgres")
    # password = os.getenv("DB_PASSWORD", "joshua1102")
    # host = os.getenv("DB_HOST", "localhost")
    # port = os.getenv("DB_PORT", "5432")

    # db_uri = f"postgresql://{user}:{password}@{host}:{port}/{dbname}"
    # app.config['SQLALCHEMY_DATABASE_URI'] = db_uri
    # app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Bind SQLAlchemy
    db.init_app(app)

    # Test database connection
    try:
        with app.app_context():
            conn = get_db_connection()
            conn.close()
            logger.info("Database connection successful")
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise e

    # Check expired temp workers
    try:
        with app.app_context():
            expired_count = User.check_expired_temp_workers()
            if expired_count > 0:
                logger.info(f"Deactivated {expired_count} expired temporary workers on startup")
    except Exception as e:
        logger.warning(f"Could not check expired temp workers: {e}")

    logger.info("Application initialized")



# ============================================
# STAFF SCHEDULE MANAGEMENT ROUTES
# ============================================

@app.route('/admin/staff-schedules')
@admin_required
def admin_staff_schedules():
    """Admin page for managing staff schedules"""
    # Get all internal staff users
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    cursor.execute("""
        SELECT u.user_id, u.username, u.email, r.role_name
        FROM users u
        JOIN roles r ON u.role_id = r.role_id
        WHERE r.role_id IN (8, 13)
        AND u.status = 'active'
        ORDER BY u.username
    """)
    staff_users = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('admin_staff_schedules.html', staff_users=staff_users)

@app.route('/api/admin/staff-schedules', methods=['GET'])
@admin_required
def get_staff_schedules():
    """Get all staff schedules or schedules for a specific staff member"""
    staff_id = request.args.get('staff_id')

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    if staff_id:
        cursor.execute("""
            SELECT s.*, u.username, u.email
            FROM staff_schedules s
            JOIN users u ON s.staff_id = u.user_id
            WHERE s.staff_id = %s
            ORDER BY s.shift_date DESC, s.shift_start
        """, (staff_id,))
    else:
        cursor.execute("""
            SELECT s.*, u.username, u.email
            FROM staff_schedules s
            JOIN users u ON s.staff_id = u.user_id
            ORDER BY s.shift_date DESC, s.shift_start
        """)

    schedules = cursor.fetchall()
    cursor.close()
    conn.close()

    # Convert to list of dicts and format dates
    schedules_list = []
    for schedule in schedules:
        schedule_dict = dict(schedule)
        # Convert date and time objects to strings
        if schedule_dict.get('shift_date'):
            schedule_dict['shift_date'] = schedule_dict['shift_date'].strftime('%Y-%m-%d')
        if schedule_dict.get('shift_start'):
            schedule_dict['shift_start'] = str(schedule_dict['shift_start'])
        if schedule_dict.get('shift_end'):
            schedule_dict['shift_end'] = str(schedule_dict['shift_end'])
        if schedule_dict.get('created_at'):
            schedule_dict['created_at'] = schedule_dict['created_at'].strftime('%Y-%m-%d %H:%M:%S')
        schedules_list.append(schedule_dict)

    return jsonify({'success': True, 'schedules': schedules_list})

@app.route('/api/admin/staff-schedules', methods=['POST'])
@admin_required
def create_staff_schedule():
    """Create a new staff schedule"""
    data = request.get_json()

    required_fields = ['staff_id', 'shift_date', 'shift_start', 'shift_end']
    for field in required_fields:
        if not data.get(field):
            return jsonify({'success': False, 'message': f'Missing required field: {field}'}), 400

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    try:
        cursor.execute("""
            INSERT INTO staff_schedules
            (staff_id, shift_date, shift_start, shift_end, task_description)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING schedule_id
        """, (
            data['staff_id'],
            data['shift_date'],
            data['shift_start'],
            data['shift_end'],
            data.get('task_description', '')
        ))

        result = cursor.fetchone()
        schedule_id = result['schedule_id']
        conn.commit()

        return jsonify({
            'success': True,
            'message': 'Schedule created successfully',
            'schedule_id': schedule_id
        })

    except Exception as e:
        conn.rollback()
        logger.error(f"Error creating schedule: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/api/admin/staff-schedules/<int:schedule_id>', methods=['PUT'])
@admin_required
def update_staff_schedule(schedule_id):
    """Update an existing staff schedule"""
    data = request.get_json()

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    try:
        cursor.execute("""
            UPDATE staff_schedules
            SET shift_date = %s,
                shift_start = %s,
                shift_end = %s,
                task_description = %s
            WHERE schedule_id = %s
        """, (
            data.get('shift_date'),
            data.get('shift_start'),
            data.get('shift_end'),
            data.get('task_description', ''),
            schedule_id
        ))

        conn.commit()

        if cursor.rowcount == 0:
            return jsonify({'success': False, 'message': 'Schedule not found'}), 404

        return jsonify({'success': True, 'message': 'Schedule updated successfully'})

    except Exception as e:
        conn.rollback()
        logger.error(f"Error updating schedule: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/api/admin/staff-schedules/<int:schedule_id>', methods=['DELETE'])
@admin_required
def delete_staff_schedule(schedule_id):
    """Delete a staff schedule"""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    try:
        cursor.execute("DELETE FROM staff_schedules WHERE schedule_id = %s", (schedule_id,))
        conn.commit()

        if cursor.rowcount == 0:
            return jsonify({'success': False, 'message': 'Schedule not found'}), 404

        return jsonify({'success': True, 'message': 'Schedule deleted successfully'})

    except Exception as e:
        conn.rollback()
        logger.error(f"Error deleting schedule: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# Staff view their own schedules
@app.route('/api/staff/schedules', methods=['GET'])
def get_my_schedules():
    """Get schedules for the logged-in staff member"""
    # For now, get staff_id from query params since we don't have full auth yet
    staff_id = request.args.get('staff_id')

    if not staff_id:
        return jsonify({'success': False, 'message': 'Staff ID required'}), 400

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    try:
        cursor.execute("""
            SELECT s.*, u.username, u.email
            FROM staff_schedules s
            JOIN users u ON s.staff_id = u.user_id
            WHERE s.staff_id = %s
            ORDER BY s.shift_date DESC, s.shift_start
        """, (staff_id,))

        schedules = cursor.fetchall()

        # Convert to list of dicts and format dates
        schedules_list = []
        for schedule in schedules:
            schedule_dict = dict(schedule)
            if schedule_dict.get('shift_date'):
                schedule_dict['shift_date'] = schedule_dict['shift_date'].strftime('%Y-%m-%d')
            if schedule_dict.get('shift_start'):
                schedule_dict['shift_start'] = str(schedule_dict['shift_start'])
            if schedule_dict.get('shift_end'):
                schedule_dict['shift_end'] = str(schedule_dict['shift_end'])
            schedules_list.append(schedule_dict)

        return jsonify({'success': True, 'schedules': schedules_list})

    except Exception as e:
        logger.error(f"Error fetching staff schedules: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# ============================================
# STAFF API ROUTES - For staff members to access their own data
# ============================================

@app.route('/api/staff/<int:staff_id>/profile', methods=['GET'])
def get_staff_profile(staff_id):
    """Get staff profile"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
            SELECT u.user_id as staff_id, u.username, u.full_name, u.email, 
                   u.contact_number, r.role_name as position, u.status as is_active, 
                   u.created_at as registered_at
            FROM users u
            LEFT JOIN roles r ON u.role_id = r.role_id
            WHERE u.user_id = %s AND r.role_id IN (8, 13)
        """, (staff_id,))
        
        staff = cur.fetchone()
        cur.close()
        conn.close()
        
        if not staff:
            return jsonify({'success': False, 'error': 'Staff not found'}), 404
        
        # Convert to dict and format dates
        staff_dict = dict(staff)
        staff_dict['is_active'] = staff_dict['is_active'] == 'active'
        if staff_dict.get('registered_at'):
            staff_dict['registered_at'] = staff_dict['registered_at'].isoformat()
        
        return jsonify({'success': True, 'data': staff_dict})
        
    except Exception as e:
        logger.error(f"Error getting staff profile: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/staff/<int:staff_id>/profile', methods=['PUT'])
def update_staff_profile(staff_id):
    """Update staff profile"""
    try:
        data = request.get_json()
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            UPDATE users
            SET full_name = %s, contact_number = %s
            WHERE user_id = %s
        """, (data.get('full_name'), data.get('contact_number'), staff_id))
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Profile updated successfully'})
        
    except Exception as e:
        logger.error(f"Error updating staff profile: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/staff/<int:staff_id>', methods=['DELETE'])
def delete_staff_account(staff_id):
    """Delete staff account"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Update status to inactive instead of deleting
        cur.execute("UPDATE users SET status = 'inactive' WHERE user_id = %s", (staff_id,))
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Account deactivated successfully'})
        
    except Exception as e:
        logger.error(f"Error deleting staff account: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/staff/enroll-face', methods=['POST'])
def enroll_staff_face():
    """Enroll staff member's face for biometric access"""
    try:
        data = request.get_json()
        staff_id = data.get('staff_id')
        image_data = data.get('image_data')  # Base64 encoded image
        
        if not staff_id or not image_data:
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400
        
        # Verify staff exists
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT u.user_id, u.username, u.full_name, r.role_name
            FROM users u
            LEFT JOIN roles r ON u.role_id = r.role_id
            WHERE u.user_id = %s AND r.role_id IN (8, 13)
        """, (staff_id,))
        
        staff = cursor.fetchone()
        
        if not staff:
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'error': 'Staff member not found'}), 404
        
        # Process the image data (remove data URL prefix if present)
        if ',' in image_data:
            image_data = image_data.split(',')[1]
        
        # Generate unique filename
        filename = f"staff_{staff_id}_{uuid.uuid4().hex[:8]}.jpg"
        
        # Check if face embedding already exists
        cursor.execute("""
            SELECT embedding_id FROM face_embeddings
            WHERE reference_id = %s AND user_type = 'staff'
        """, (staff_id,))
        
        existing = cursor.fetchone()
        
        if existing:
            # Update existing record
            cursor.execute("""
                UPDATE face_embeddings
                SET image_filename = %s,
                    embedding = NULL,
                    updated_at = NOW()
                WHERE reference_id = %s AND user_type = 'staff'
            """, (filename, staff_id))
            logger.info(f"Updated face enrollment for staff_id={staff_id}")
        else:
            # Insert new record
            cursor.execute("""
                INSERT INTO face_embeddings (reference_id, user_type, image_filename)
                VALUES (%s, 'staff', %s)
            """, (staff_id, filename))
            logger.info(f"Created face enrollment for staff_id={staff_id}")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Face enrolled successfully',
            'data': {
                'staff_id': staff_id,
                'filename': filename
            }
        })
        
    except Exception as e:
        logger.error(f"Error enrolling staff face: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/staff/attendance/record', methods=['POST'])
def record_staff_attendance():
    """Record staff clock in/out"""
    try:
        data = request.get_json()
        staff_id = data.get('staff_id')
        action = data.get('action')  # 'entry' or 'exit'
        location = data.get('location', 'Main Gate')
        verification_method = data.get('verification_method', 'Manual')
        
        if not staff_id or not action:
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        if action == 'entry':
            # Create new attendance record
            cursor.execute("""
                INSERT INTO staff_attendance (staff_id, entry_time, location, verification_method)
                VALUES (%s, NOW(), %s, %s)
                RETURNING attendance_id
            """, (staff_id, location, verification_method))
            
            result = cursor.fetchone()
            conn.commit()
            
            message = 'Clocked in successfully'
            
        elif action == 'exit':
            # Update existing record with exit time
            cursor.execute("""
                UPDATE staff_attendance
                SET exit_time = NOW(),
                    duration_hours = EXTRACT(EPOCH FROM (NOW() - entry_time)) / 3600
                WHERE staff_id = %s 
                AND exit_time IS NULL
                AND DATE(entry_time) = CURRENT_DATE
                RETURNING attendance_id
            """, (staff_id,))
            
            result = cursor.fetchone()
            
            if not result:
                cursor.close()
                conn.close()
                return jsonify({'success': False, 'error': 'No active clock-in found for today'}), 400
            
            conn.commit()
            message = 'Clocked out successfully'
        else:
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'error': 'Invalid action'}), 400
        
        cursor.close()
        conn.close()
        
        return jsonify({'success': True, 'message': message, 'data': {'attendance_id': result['attendance_id']}})
        
    except Exception as e:
        logger.error(f"Error recording attendance: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

import os

init_app(app)  # <-- put this BEFORE running

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port, debug=False)

    print("\n" + "=" * 60)
    print("FACE RECOGNITION - ADMIN PANEL")
    print("=" * 60)
    print(f"\nAdmin Panel: http://localhost:{Config.PORT}/admin/login")
    print(f"\nDefault admin: admin_user / password: admin123")
    print("=" * 60 + "\n")
