import os

from routes.security_officer.security_officer_model import SecurityOfficer
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
def portal_choice():
    return render_template('/portal.html')

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():

    if request.method == 'GET':
        session.clear()
        if 'user_id' in session:
            return redirect(url_for('admin_profile'))
        return render_template('index.html')

    # POST (login)
    data = request.json
    username = data.get('username')
    password = data.get('password')

    user = User.authenticate(username, password)

    if user and user['role'] == 'Admin':
        session['user_id'] = user['id']
        session['username'] = user['username']
        session['role'] = user['role']
        session.permanent = True

        return jsonify({'success': True})

    return jsonify({'success': False, 'message': 'Invalid credentials'}), 401

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
    return send_from_directory('frontend', 'resident-dashboard.html')

@app.route('/resident/profile')
def resident_profile():
    """Sere resident profile page"""
    return send_from_directory('frontend', 'resident-profile.html')

@app.route('/resident/face-registration')
def resident_face_registration():
    """Serve resident face registration page"""
    return send_from_directory('frontend', 'resident-face-registration.html')

@app.route('/resident/visitors')
def resident_visitors():
    """Serve resident visitors management page"""
    return send_from_directory('frontend', 'resident-visitors.html')

@app.route('/resident/access-history')
def resident_access_history():
    """Serve resident access history page"""
    return send_from_directory('frontend', 'resident-access-history.html')

@app.route('/resident/alerts')
def resident_alerts():
    """Serve resident alerts page"""
    return send_from_directory('frontend', 'resident-alerts.html')

# Visitor Routes
@app.route('/frontend/visitor-dashboard.html')
@app.route('/visitor/dashboard')
def visitor_dashboard():
    """Serve visitor dashboard"""
    return send_from_directory('frontend', 'visitor-dashboard.html')

# Staff Routes
@app.route('/frontend/staff-dashboard.html')
@app.route('/staff/dashboard')
def staff_dashboard():
    """Serve staff dashboard"""
    return send_from_directory('frontend', 'staff-dashboard.html')

@app.route('/frontend/staff-profile.html')
@app.route('/staff/profile')
def staff_profile():
    """Serve staff profile page"""
    return send_from_directory('frontend', 'staff-profile.html')

@app.route('/frontend/staff-schedule.html')
@app.route('/staff/schedule')
def staff_schedule():
    """Serve staff schedule page"""
    return send_from_directory('frontend', 'staff-schedule.html')

@app.route('/frontend/staff-attendance.html')
@app.route('/staff/attendance')
def staff_attendance():
    """Serve staff attendance page"""
    return send_from_directory('frontend', 'staff-attendance.html')

# Security Officer Routes
def officer_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'officer_id' not in session:
            return redirect(url_for('security_login'))
        officer = SecurityOfficer.query.get(session['officer_id'])
        if not officer:
            session.clear()
            return redirect(url_for('security_login'))
        return f(*args, **kwargs)
    return decorated

@app.route("/security/login", methods=["GET", "POST"])
def security_login():
    if request.method == "GET":
        return render_template("login.html")

    # POST: handle login
    data = request.json
    if not data:
        return jsonify({"success": False, "message": "No data provided"}), 400

    officer_id = data.get("user_id")
    if not officer_id:
        return jsonify({"success": False, "message": "Missing user_id"}), 400

    officer = SecurityOfficer.query.get(officer_id)
    if not officer:
        return jsonify({"success": False, "message": "Officer not found"}), 404

    # Store officer info in session
    session['officer_id'] = officer.officer_id
    session['officer_name'] = officer.full_name

    return jsonify({"success": True, "redirect": "/security-dashboard"})

@app.route("/security-dashboard")
@officer_required
def security_dashboard():
    officer = SecurityOfficer.query.get(session['officer_id'])
    access_logs = AccessLog.query.order_by(AccessLog.log_id.asc()).all()
    granted_count = AccessLog.query.filter_by(access_result='granted').count()
    return render_template("security-dashboard.html", officer=officer, logs=access_logs, granted_count=granted_count)


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
@officer_required
def security_logout():
    session.pop('officer_id', None)
    session.pop('officer_name', None)
    return redirect(url_for('security_login'))

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


# ============================================
# VISITOR ROUTES (from visitor_routes.py)
# ============================================

@app.route("/api/visitor/visitors", methods=["POST"])
def create_visitor_entry():
    """UC-R8 Create Visitor Entry (stub)"""
    payload = request.get_json() or {}
    return jsonify({"message": "Visitor entry created (stub)", "payload": payload}), 201

@app.route("/api/visitor/visitors", methods=["GET"])
def view_registered_visitors():
    """UC-R10 View Registered Visitors (stub)"""
    demo_visitors = [
        {
            "visitor_id": 1,
            "full_name": "Mary Lee",
            "visiting_unit": "B-12-05",
            "check_in": "2025-11-12T11:06:13",
        }
    ]
    return jsonify(demo_visitors), 200


# ============================================
# RESIDENT ROUTES (from resident_routes.py)
# ============================================

def parse_iso(dt_str):
    """Parse ISO datetime string safely; return None if invalid."""
    if not dt_str:
        return None
    try:
        return datetime.fromisoformat(dt_str)
    except ValueError:
        return None


@app.route("/api/resident/register-face", methods=["POST"])
def register_face():
    """UC-R1: Register Face Data"""
    data = request.get_json() or {}
    resident_id = data.get("resident_id")
    image_data = data.get("image_data")

    if not resident_id or not image_data:
        return jsonify({
            "error": "Missing fields",
            "required": ["resident_id", "image_data"]
        }), 400

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            "SELECT resident_id FROM residents WHERE resident_id = %s;",
            (resident_id,)
        )
        row = cur.fetchone()
        if not row:
            cur.close()
            conn.close()
            return jsonify({"error": "Resident not found"}), 404

        cur.execute(
            """
            INSERT INTO face_embeddings (user_type, reference_id, embedding)
            VALUES ('resident', %s, NULL)
            RETURNING embedding_id;
            """,
            (resident_id,)
        )
        embedding_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()

        return jsonify({
            "message": "Face data registered (placeholder, no embedding yet)",
            "resident_id": resident_id,
            "embedding_id": embedding_id
        }), 201

    except Exception as e:
        return jsonify({"error": "DB error while saving face data", "details": str(e)}), 500

@app.route("/api/resident/<int:resident_id>", methods=["GET"])
def view_personal_data(resident_id):
    """UC-R2: View Personal Data"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT r.resident_id,
                   r.full_name,
                   r.unit_number,
                   r.contact_number,
                   r.registered_at,
                   u.email
            FROM residents r
            LEFT JOIN users u ON r.user_id = u.user_id
            WHERE r.resident_id = %s;
            """,
            (resident_id,)
        )
        row = cur.fetchone()
        cur.close()
        conn.close()

        if not row:
            return jsonify({"error": "Resident not found"}), 404

        resident = {
            "resident_id": row[0],
            "full_name": row[1],
            "unit_number": row[2],
            "contact_number": row[3],
            "registered_at": row[4].isoformat() if row[4] else None,
            "email": row[5],
        }
        return jsonify(resident), 200

    except Exception as e:
        return jsonify({"error": "DB error while reading resident", "details": str(e)}), 500

@app.route("/api/resident/<int:resident_id>", methods=["PUT"])
def update_personal_data(resident_id):
    """UC-R3: Update Personal Data"""
    data = request.get_json() or {}

    allowed_fields = {
        "full_name": "full_name",
        "contact_number": "contact_number",
        "unit_number": "unit_number",
    }

    sets = []
    params = []
    for json_key, col in allowed_fields.items():
        if json_key in data:
            sets.append(f"{col} = %s")
            params.append(data[json_key])

    if not sets:
        return jsonify({"error": "No updatable fields provided"}), 400

    params.append(resident_id)

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            f"""
            UPDATE residents
            SET {", ".join(sets)}
            WHERE resident_id = %s
            RETURNING resident_id;
            """,
            tuple(params)
        )
        row = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()

        if not row:
            return jsonify({"error": "Resident not found"}), 404

        return jsonify({
            "message": "Personal data updated",
            "resident_id": resident_id,
            "updated_fields": {k: v for k, v in data.items() if k in allowed_fields}
        }), 200

    except Exception as e:
        return jsonify({"error": "DB error while updating resident", "details": str(e)}), 500

@app.route("/api/resident/<int:resident_id>", methods=["DELETE"])
def delete_personal_data(resident_id):
    """UC-R4: Delete Personal Data"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM residents WHERE resident_id = %s RETURNING resident_id;",
            (resident_id,)
        )
        row = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()

        if not row:
            return jsonify({"error": "Resident not found"}), 404

        return jsonify({
            "message": "Resident account deleted",
            "resident_id": resident_id
        }), 200

    except Exception as e:
        return jsonify({"error": "DB error while deleting resident", "details": str(e)}), 500

@app.route("/api/resident/<int:user_id>/access-history", methods=["GET"])
def view_personal_access_history(resident_id):
    """UC-R22: View Personal Access History"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            "SELECT full_name FROM residents WHERE resident_id = %s;",
            (resident_id,)
        )
        row = cur.fetchone()
        if not row:
            cur.close()
            conn.close()
            return jsonify({"error": "Resident not found"}), 404
        full_name = row[0]

        cur.execute(
            """
            SELECT access_time,
                   person_type,
                   confidence,
                   access_result
            FROM access_logs
            WHERE person_type = 'resident' AND recognized_person = %s
            ORDER BY access_time DESC;
            """,
            (full_name,)
        )
        logs = cur.fetchall()
        cur.close()
        conn.close()

        records = [
            {
                "timestamp": r[0].isoformat() if r[0] else None,
                "person_type": r[1],
                "confidence": r[2],
                "result": r[3],
            }
            for r in logs
        ]

        return jsonify({
            "resident_id": resident_id,
            "resident_name": full_name,
            "records": records
        }), 200

    except Exception as e:
        return jsonify({"error": "DB error while reading access history", "details": str(e)}), 500

@app.route("/api/resident/<int:user_id>/visitors", methods=["POST"])
def create_visitor(resident_id):
    """UC-R8: Create Visitor Entry"""
    data = request.get_json() or {}
    required = ["full_name", "contact_number", "visiting_unit"]
    missing = [f for f in required if f not in data]
    if missing:
        return jsonify({"error": "Missing fields", "missing": missing}), 400

    check_in_str = data.get("check_in")
    check_out_str = data.get("check_out")

    check_in = parse_iso(check_in_str) if check_in_str else None
    check_out = parse_iso(check_out_str) if check_out_str else None

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            "SELECT resident_id FROM residents WHERE resident_id = %s;",
            (resident_id,)
        )
        if not cur.fetchone():
            cur.close()
            conn.close()
            return jsonify({"error": "Resident not found"}), 404

        cur.execute(
            """
            INSERT INTO visitors (full_name, contact_number, visiting_unit, check_in, check_out, approved_by)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING visitor_id;
            """,
            (
                data["full_name"],
                data["contact_number"],
                data["visiting_unit"],
                check_in,
                check_out,
                resident_id
            )
        )
        visitor_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()

        return jsonify({
            "message": "Visitor entry created",
            "resident_id": resident_id,
            "visitor_id": visitor_id,
            "full_name": data["full_name"]
        }), 201

    except Exception as e:
        return jsonify({"error": "DB error while creating visitor", "details": str(e)}), 500

@app.route("/api/resident/<int:user_id>/visitors", methods=["GET"])
def view_registered_visitors_for_resident(resident_id):
    """UC-R10: View Registered Visitors"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            "SELECT resident_id FROM residents WHERE resident_id = %s;",
            (resident_id,)
        )
        if not cur.fetchone():
            cur.close()
            conn.close()
            return jsonify({"error": "Resident not found"}), 404

        cur.execute(
            """
            SELECT visitor_id,
                   full_name,
                   contact_number,
                   visiting_unit,
                   check_in,
                   check_out
            FROM visitors
            WHERE approved_by = %s
            ORDER BY check_in DESC;
            """,
            (resident_id,)
        )
        rows = cur.fetchall()
        cur.close()
        conn.close()

        visitors = [
            {
                "visitor_id": r[0],
                "full_name": r[1],
                "contact_number": r[2],
                "visiting_unit": r[3],
                "check_in": r[4].isoformat() if r[4] else None,
                "check_out": r[5].isoformat() if r[5] else None,
            }
            for r in rows
        ]

        return jsonify({
            "resident_id": resident_id,
            "visitors": visitors
        }), 200

    except Exception as e:
        return jsonify({"error": "DB error while reading visitors", "details": str(e)}), 500

@app.route("/api/resident/<int:user_id>/visitors/<int:visitor_id>", methods=["PUT"])
def update_visitor_info(resident_id, visitor_id):
    """UC-R12: Update Visitor Information"""
    data = request.get_json() or {}

    allowed_fields = {
        "full_name": "full_name",
        "contact_number": "contact_number",
        "visiting_unit": "visiting_unit",
    }

    sets = []
    params = []
    for json_key, col in allowed_fields.items():
        if json_key in data:
            sets.append(f"{col} = %s")
            params.append(data[json_key])

    if not sets:
        return jsonify({"error": "No updatable fields provided"}), 400

    params.extend([resident_id, visitor_id])

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            f"""
            UPDATE visitors
            SET {", ".join(sets)}
            WHERE approved_by = %s AND visitor_id = %s
            RETURNING visitor_id;
            """,
            tuple(params)
        )
        row = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()

        if not row:
            return jsonify({"error": "Visitor not found for this resident"}), 404

        return jsonify({
            "message": "Visitor information updated",
            "resident_id": resident_id,
            "visitor_id": visitor_id,
            "updated_fields": {k: v for k, v in data.items() if k in allowed_fields}
        }), 200

    except Exception as e:
        return jsonify({"error": "DB error while updating visitor", "details": str(e)}), 500

@app.route("/api/resident/<int:user_id>/visitors/<int:visitor_id>", methods=["DELETE"])
def cancel_visitor_access(resident_id, visitor_id):
    """UC-R13: Cancel Visitor Access"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            DELETE FROM visitors
            WHERE approved_by = %s AND visitor_id = %s
            RETURNING visitor_id;
            """,
            (resident_id, visitor_id)
        )
        row = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()

        if not row:
            return jsonify({"error": "Visitor not found for this resident"}), 404

        return jsonify({
            "message": "Visitor access cancelled",
            "resident_id": resident_id,
            "visitor_id": visitor_id
        }), 200

    except Exception as e:
        return jsonify({"error": "DB error while deleting visitor", "details": str(e)}), 500

@app.route("/api/resident/<int:user_id>/visitors/<int:visitor_id>/time-window", methods=["PUT"])
def set_visitor_time_period(resident_id, visitor_id):
    """UC-R9: Set Visitor Time Period"""
    data = request.get_json() or {}
    required = ["start_time", "end_time"]
    missing = [f for f in required if f not in data]
    if missing:
        return jsonify({"error": "Missing fields", "missing": missing}), 400

    start_ts = parse_iso(data["start_time"])
    end_ts = parse_iso(data["end_time"])
    if not start_ts or not end_ts:
        return jsonify({"error": "Invalid datetime format (use ISO 8601)"}), 400

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE visitors
            SET check_in = %s,
                check_out = %s
            WHERE approved_by = %s AND visitor_id = %s
            RETURNING visitor_id;
            """,
            (start_ts, end_ts, resident_id, visitor_id)
        )
        row = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()

        if not row:
            return jsonify({"error": "Visitor not found for this resident"}), 404

        return jsonify({
            "message": "Visitor time window updated",
            "resident_id": resident_id,
            "visitor_id": visitor_id,
            "start_time": data["start_time"],
            "end_time": data["end_time"]
        }), 200

    except Exception as e:
        return jsonify({"error": "DB error while updating time window", "details": str(e)}), 500

@app.route("/api/resident/<int:user_id>/visitors/<int:visitor_id>/face-image", methods=["POST"])
def upload_visitor_facial_image(resident_id, visitor_id):
    """UC-R14: Upload Visitor Facial Image"""
    data = request.get_json() or {}
    image_data = data.get("image_data")

    if not image_data:
        return jsonify({
            "error": "Missing field",
            "required": ["image_data"]
        }), 400

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            """
            SELECT visitor_id, full_name
            FROM visitors
            WHERE approved_by = %s AND visitor_id = %s;
            """,
            (resident_id, visitor_id)
        )
        row = cur.fetchone()
        if not row:
            cur.close()
            conn.close()
            return jsonify({"error": "Visitor not found for this resident"}), 404

        cur.execute(
            """
            INSERT INTO face_embeddings (user_type, reference_id, embedding)
            VALUES ('visitor', %s, NULL)
            RETURNING embedding_id;
            """,
            (visitor_id,)
        )
        embedding_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()

        return jsonify({
            "message": "Visitor facial image stored (placeholder, no embedding yet)",
            "resident_id": resident_id,
            "visitor_id": visitor_id,
            "embedding_id": embedding_id
        }), 201

    except Exception as e:
        return jsonify({"error": "DB error while saving visitor face", "details": str(e)}), 500

@app.route("/api/resident/<int:user_id>/visitors/<int:visitor_id>/access-history", methods=["GET"])
def view_visitor_access_history(resident_id, visitor_id):
    """UC-R23: View Visitor Access History"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            """
            SELECT full_name
            FROM visitors
            WHERE approved_by = %s AND visitor_id = %s;
            """,
            (resident_id, visitor_id)
        )
        row = cur.fetchone()
        if not row:
            cur.close()
            conn.close()
            return jsonify({"error": "Visitor not found for this resident"}), 404
        full_name = row[0]

        cur.execute(
            """
            SELECT access_time,
                   person_type,
                   confidence,
                   access_result
            FROM access_logs
            WHERE person_type = 'visitor' AND recognized_person = %s
            ORDER BY access_time DESC;
            """,
            (full_name,)
        )
        logs = cur.fetchall()
        cur.close()
        conn.close()

        records = [
            {
                "timestamp": r[0].isoformat() if r[0] else None,
                "person_type": r[1],
                "confidence": r[2],
                "result": r[3],
            }
            for r in logs
        ]

        return jsonify({
            "resident_id": resident_id,
            "visitor_id": visitor_id,
            "visitor_name": full_name,
            "records": records
        }), 200

    except Exception as e:
        return jsonify({"error": "DB error while reading visitor history", "details": str(e)}), 500

@app.route("/api/resident/<int:user_id>/face-access/disable", methods=["POST"])
def temporarily_disable_face_access(resident_id):
    """UC-R19: Temporarily Disable Face Access (mock)"""
    return jsonify({
        "message": "Face access disabled temporarily (mock)",
        "resident_id": resident_id,
        "status": "DISABLED"
    }), 200

@app.route("/api/resident/<int:user_id>/alerts", methods=["GET"])
def receive_unauthorized_access_alert(resident_id):
    """UC-R20: Receive Unauthorized Access Alert (mock)"""
    recent_time = (datetime.now()).isoformat(timespec="seconds")
    alerts = [
        {
            "alert_id": 1,
            "timestamp": recent_time,
            "description": "Multiple failed face attempts at lobby door",
            "status": "UNREAD"
        }
    ]
    return jsonify({
        "resident_id": resident_id,
        "alerts": alerts
    }), 200

@app.route("/api/resident/offline/recognize", methods=["POST"])
def offline_recognition_mode():
    """UC-R21: Offline Recognition Mode (mock)"""
    data = request.get_json() or {}
    device_id = data.get("device_id")
    image_data = data.get("image_data")

    if not device_id or not image_data:
        return jsonify({
            "error": "Missing fields",
            "required": ["device_id", "image_data"]
        }), 400

    return jsonify({
        "message": "Offline recognition successful (mock)",
        "device_id": device_id,
        "matched_resident_id": 1,
        "confidence": 0.95,
        "name": "John Tan"
    }), 200

@app.route("/api/resident/test-db", methods=["GET"])
def test_db():
    """Test database connection"""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT NOW();")
    result = cur.fetchone()
    cur.close()
    conn.close()

    return jsonify({
        "db_connection": "OK",
        "server_time": str(result[0])
    }), 200


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
        return deactivate_account(officer_id)

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
            # raw_embedding = image_to_embedding(image_base64)
            # query_embedding = raw_embedding / np.linalg.norm(raw_embedding)

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

                if fe.embedding is None:
                    continue   # ⛔ skip broken rows

                db_embedding = np.array(fe.embedding, dtype=np.float32)

                if db_embedding.size != 512:
                    continue   # ⛔ corrupted vector

                db_embedding = normalize(db_embedding)

                score = cosine_similarity(query_embedding, db_embedding)

                if score > best_score:
                    best_score = score
                    best_match = fe

            if best_match and best_score >= threshold:

                if best_match.user_type == "resident":
                    from routes.security_officer.security_officer_model import Resident
                    person = Resident.query.get(best_match.reference_id)
                else:
                    person = Visitor.query.get(best_match.reference_id)

                log_access(
                    
                    recognized_person=person.full_name,
                    person_type=best_match.user_type,
                    confidence=best_score,
                    result="granted",
                    embedding_id=best_match.embedding_id,
                )

                return jsonify({
                    "status": "success",
                    "result": "granted",
                    "person_type": best_match.user_type,
                    "name": person.full_name,
                    "message": "Face recognized",   
                    "confidence": float(round(best_score * 100, 2))
                })

            # No match
            log_access(
                recognized_person="Unknown",
                person_type="unknown",
                confidence=best_score,
                result="denied",
                embedding_id=None,
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
        user_type = 'admin'
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

@app.route('/admin/users/<int:user_id>/edit')
@admin_required
def admin_users_edit(user_id):
    """Edit user page - User Story: Edit user details"""
    user = User.get_by_id(user_id)

    print("user", user)
    if not user:
        return "User not found", 404

    return render_template('admin_edit_user.html', user=user)

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

@app.route('/admin/temp-workers')
@admin_required
def admin_temp_workers():
    """View temporary workers with their schedules"""
    users = User.get_all(role='temp_staff')
    expiring_soon = User.get_expiring_temp_workers(days=7)
    from datetime import date
    today = date.today()
    
    return render_template('admin_tempworker.html', 
                         users=users, 
                         expiring_soon=expiring_soon,
                         today=today)

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
        WHERE r.role_name IN ('Internal_Staff', 'INTERNAL_STAFF', 'Staff')
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
            SELECT s.*, u.username, u.email,
                   a.username as assigned_by_username
            FROM staff_schedules s
            JOIN users u ON s.staff_user_id = u.user_id
            LEFT JOIN users a ON s.assigned_by_user_id = a.user_id
            WHERE s.staff_user_id = %s
            ORDER BY s.start_date DESC, s.start_time
        """, (staff_id,))
    else:
        cursor.execute("""
            SELECT s.*, u.username, u.email,
                   a.username as assigned_by_username
            FROM staff_schedules s
            JOIN users u ON s.staff_user_id = u.user_id
            LEFT JOIN users a ON s.assigned_by_user_id = a.user_id
            ORDER BY s.start_date DESC, s.start_time
        """)

    schedules = cursor.fetchall()
    cursor.close()
    conn.close()

    # Convert to list of dicts and format dates
    schedules_list = []
    for schedule in schedules:
        schedule_dict = dict(schedule)
        # Convert date and time objects to strings
        if schedule_dict.get('start_date'):
            schedule_dict['start_date'] = schedule_dict['start_date'].strftime('%Y-%m-%d')
        if schedule_dict.get('end_date'):
            schedule_dict['end_date'] = schedule_dict['end_date'].strftime('%Y-%m-%d')
        if schedule_dict.get('start_time'):
            schedule_dict['start_time'] = str(schedule_dict['start_time'])
        if schedule_dict.get('end_time'):
            schedule_dict['end_time'] = str(schedule_dict['end_time'])
        if schedule_dict.get('created_at'):
            schedule_dict['created_at'] = schedule_dict['created_at'].strftime('%Y-%m-%d %H:%M:%S')
        schedules_list.append(schedule_dict)

    return jsonify({'success': True, 'schedules': schedules_list})

@app.route('/api/admin/staff-schedules', methods=['POST'])
@admin_required
def create_staff_schedule():
    """Create a new staff schedule"""
    data = request.get_json()

    required_fields = ['staff_user_id', 'start_date', 'end_date', 'start_time', 'end_time']
    for field in required_fields:
        if not data.get(field):
            return jsonify({'success': False, 'message': f'Missing required field: {field}'}), 400

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    try:
        cursor.execute("""
            INSERT INTO staff_schedules
            (staff_user_id, assigned_by_user_id, shift_name, start_date, end_date,
             start_time, end_time, days_of_week, location, notes, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING schedule_id
        """, (
            data['staff_user_id'],
            session.get('user_id'),
            data.get('shift_name', ''),
            data['start_date'],
            data['end_date'],
            data['start_time'],
            data['end_time'],
            data.get('days_of_week', ''),
            data.get('location', ''),
            data.get('notes', ''),
            data.get('status', 'active')
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
            SET shift_name = %s, start_date = %s, end_date = %s,
                start_time = %s, end_time = %s, days_of_week = %s,
                location = %s, notes = %s, status = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE schedule_id = %s
        """, (
            data.get('shift_name', ''),
            data.get('start_date'),
            data.get('end_date'),
            data.get('start_time'),
            data.get('end_time'),
            data.get('days_of_week', ''),
            data.get('location', ''),
            data.get('notes', ''),
            data.get('status', 'active'),
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
            JOIN users u ON s.staff_user_id = u.user_id
            WHERE s.staff_user_id = %s
            AND s.status = 'active'
            ORDER BY s.start_date DESC, s.start_time
        """, (staff_id,))

        schedules = cursor.fetchall()

        # Convert to list of dicts and format dates
        schedules_list = []
        for schedule in schedules:
            schedule_dict = dict(schedule)
            if schedule_dict.get('start_date'):
                schedule_dict['start_date'] = schedule_dict['start_date'].strftime('%Y-%m-%d')
            if schedule_dict.get('end_date'):
                schedule_dict['end_date'] = schedule_dict['end_date'].strftime('%Y-%m-%d')
            if schedule_dict.get('start_time'):
                schedule_dict['start_time'] = str(schedule_dict['start_time'])
            if schedule_dict.get('end_time'):
                schedule_dict['end_time'] = str(schedule_dict['end_time'])
            schedules_list.append(schedule_dict)

        return jsonify({'success': True, 'schedules': schedules_list})

    except Exception as e:
        logger.error(f"Error fetching staff schedules: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        cursor.close()
        conn.close()



if __name__ == '__main__':
    from app import app
    init_app(app)
    print("\n" + "=" * 60)
    print("FACE RECOGNITION - ADMIN PANEL")
    print("=" * 60)
    print(f"\nAdmin Panel: http://localhost:{Config.PORT}/admin/login")
    print(f"\nDefault admin: admin_user / password: admin123")
    print("=" * 60 + "\n")
    app.run(host=Config.HOST, port=Config.PORT, debug=False)
