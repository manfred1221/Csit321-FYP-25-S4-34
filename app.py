import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

from flask import (
    Flask, request, jsonify, session, render_template,
    redirect, url_for, send_from_directory
)
from flask_cors import CORS
from functools import wraps
import logging
from jinja2 import ChoiceLoader, FileSystemLoader
from datetime import datetime

from config import Config
from user import User, Resident
from access_log import AccessLog
from psycopg2.extras import RealDictCursor
from database import get_db_connection

# ------------------------------------------------------------
# Logging
# ------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Support both templates and frontend folders
app.jinja_loader = ChoiceLoader([
    FileSystemLoader(os.path.join(BASE_DIR, 'templates')),
    FileSystemLoader(os.path.join(BASE_DIR, 'frontend')),
])

app.config['SECRET_KEY'] = Config.SECRET_KEY
app.config['PERMANENT_SESSION_LIFETIME'] = Config.SESSION_LIFETIME
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
CORS(app)

# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------
def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('admin_login'))
        user = User.get_by_id(session['user_id'])
        if not user or user.get('role') != 'Admin':
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated


def officer_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'officer_id' not in session:
            return redirect(url_for('security_login'))
        return f(*args, **kwargs)
    return decorated


def check_user_has_face_embedding(user):
    if not user:
        return None

    user_role = (user.get('role') or '').lower()
    user_id = user.get('user_id') or user.get('id')

    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

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
# PORTAL + LOGIN
# ============================================
@app.route('/')
def portal_choice():
    # templates/portal.html
    return render_template('portal.html')


@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    # GET -> templates/admin_login.html
    if request.method == 'GET':
        if 'user_id' in session:
            user = User.get_by_id(session['user_id'])
            if user and user.get('role') == 'Admin':
                return redirect(url_for('admin_profile'))
        return render_template('admin_login.html')

    # POST -> expects JSON from admin_login.html fetch()
    data = request.get_json(silent=True) or {}
    user = User.authenticate(data.get('username'), data.get('password'))

    if user and user.get('role') == 'Admin':
        session['user_id'] = user.get('user_id') or user.get('id')
        session['username'] = user.get('username')
        session['role'] = user.get('role')
        session.permanent = True

        # Optional temp-worker expiry check (only if your User class has it)
        try:
            if hasattr(User, "check_expired_temp_workers"):
                expired_count = User.check_expired_temp_workers()
                if expired_count:
                    logger.info(f"Deactivated {expired_count} expired temporary workers")
        except Exception as e:
            logger.warning(f"Temp worker expiry check failed: {e}")

        return jsonify({'success': True})

    return jsonify({'success': False, 'message': 'Invalid credentials or not admin'}), 401


@app.route('/admin/logout')
def admin_logout():
    session.clear()
    return redirect(url_for('admin_login'))


# ============================================
# ADMIN PAGES
# ============================================
@app.route('/admin')
@admin_required
def admin_dashboard():
    return redirect(url_for('admin_profile'))


@app.route('/admin/profile')
@admin_required
def admin_profile():
    # templates/admin_profile.html
    user = User.get_by_id(session['user_id'])
    if user:
        user['face_encoding_path'] = check_user_has_face_embedding(user)
    return render_template('admin_profile.html', user=user)


@app.route('/admin/users')
@admin_required
def admin_users_page():
    # templates/admin_users.html
    users = User.get_all()
    return render_template('admin_users.html', users=users)


@app.route('/admin/users/add', methods=['GET'])
@admin_required
def admin_add_user_page():
    # templates/admin_add_user.html
    return render_template('admin_add_user.html')


@app.route('/admin/users/add', methods=['POST'])
@admin_required
def admin_add_user_submit():
    data = request.get_json(silent=True) or request.form.to_dict()
    user_id = User.create(data)
    return jsonify({"success": True, "user_id": user_id}), 201


@app.route('/admin/users/<int:user_id>/edit', methods=['GET'])
@admin_required
def admin_edit_user_page(user_id):
    # templates/admin_edit_user.html
    user = User.get_by_id(user_id)
    if not user:
        return "User not found", 404
    return render_template('admin_edit_user.html', user=user)


@app.route('/admin/users/<int:user_id>/edit', methods=['POST'])
@admin_required
def admin_edit_user_submit(user_id):
    data = request.get_json(silent=True) or request.form.to_dict()
    User.update(user_id, data)
    return jsonify({"success": True}), 200


@app.route('/admin/temp-workers')
@admin_required
def admin_temp_workers_page():
    # template file in your folder looks like: admin_tempworker.html
    workers = User.get_all(role='TEMP_WORKER')
    return render_template('admin_tempworker.html', workers=workers)


@app.route('/admin/logs')
@admin_required
def admin_logs_page():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("""
        SELECT log_id, access_time, recognized_person, person_type, confidence, access_result
        FROM access_logs
        ORDER BY access_time DESC
        LIMIT 200;
    """)
    logs = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('admin_logs.html', logs=logs)


@app.route('/admin/staff-schedules')
@admin_required
def admin_staff_schedules_page():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("""
        SELECT ss.schedule_id, ss.staff_id, ss.shift_date, ss.shift_start, ss.shift_end, ss.task_description,
               s.full_name
        FROM staff_schedules ss
        LEFT JOIN staff s ON ss.staff_id = s.staff_id
        ORDER BY ss.shift_date DESC, ss.shift_start DESC
        LIMIT 200;
    """)
    schedules = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('admin_staff_schedules.html', schedules=schedules)


# ============================================
# FRONTEND STATIC PAGES (Resident / Staff / Visitor)
# ============================================
@app.route('/login')
def combined_login_page():
    # templates/login.html (your dropdown page)
    return render_template('login.html')


@app.route('/frontend/<path:filename>')
def frontend_static(filename):
    return send_from_directory('frontend', filename)


@app.route('/frontend/css/<path:filename>')
def frontend_css(filename):
    return send_from_directory('frontend/css', filename)


@app.route('/frontend/js/<path:filename>')
def frontend_js(filename):
    return send_from_directory('frontend/js', filename)


# Nice clean routes (use these in your sidebar links)
@app.route('/resident/dashboard')
def resident_dashboard():
    return send_from_directory('frontend', 'resident-dashboard.html')


@app.route('/resident/profile')
def resident_profile():
    return send_from_directory('frontend', 'resident-profile.html')


@app.route('/resident/face-registration')
def resident_face_registration():
    return send_from_directory('frontend', 'resident-face-registration.html')


@app.route('/resident/visitors')
def resident_visitors():
    return send_from_directory('frontend', 'resident-visitors.html')


@app.route('/resident/access-history')
def resident_access_history():
    return send_from_directory('frontend', 'resident-access-history.html')


@app.route('/resident/alerts')
def resident_alerts():
    return send_from_directory('frontend', 'resident-alerts.html')


@app.route('/staff/dashboard')
def staff_dashboard():
    return send_from_directory('frontend', 'staff-dashboard.html')


@app.route('/staff/profile')
def staff_profile():
    return send_from_directory('frontend', 'staff-profile.html')


@app.route('/staff/schedule')
def staff_schedule():
    return send_from_directory('frontend', 'staff-schedule.html')


@app.route('/staff/attendance')
def staff_attendance():
    return send_from_directory('frontend', 'staff-attendance.html')


@app.route('/visitor/dashboard')
def visitor_dashboard():
    return send_from_directory('frontend', 'visitor-dashboard.html')


# ============================================
# SECURITY OFFICER ROUTES
# ============================================
@app.route("/security/login", methods=["GET", "POST"])
def security_login():
    if request.method == "GET":
        # templates/login.html already supports security officer option
        return render_template("login.html")

    data = request.get_json(silent=True) or {}

    # Your current security_login expects user_id (not username/password)
    officer_id = data.get("user_id")
    if not officer_id:
        return jsonify({"success": False, "message": "Missing user_id"}), 400

    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            SELECT officer_id, full_name, active
            FROM security_officers
            WHERE officer_id = %s
            LIMIT 1;
        """, (officer_id,))
        officer = cur.fetchone()

        cur.close()
        conn.close()

        if not officer:
            return jsonify({"success": False, "message": "Officer not found"}), 404
        if officer.get("active") is False:
            return jsonify({"success": False, "message": "Officer account is inactive"}), 403

        session['officer_id'] = int(officer["officer_id"])
        session['officer_name'] = officer.get("full_name") or "Security Officer"
        session.permanent = True

        return jsonify({"success": True, "redirect": "/security-dashboard"}), 200

    except Exception as e:
        logger.error(f"Security login DB error: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/security-dashboard")
@officer_required
def security_dashboard():
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        officer = {
            "officer_id": session.get("officer_id"),
            "full_name": session.get("officer_name")
        }

        cur.execute("""
            SELECT log_id, access_time, recognized_person, person_type, confidence, access_result
            FROM access_logs
            ORDER BY log_id ASC
            LIMIT 200;
        """)
        logs = cur.fetchall()

        cur.close()
        conn.close()

        return render_template("security-dashboard.html", officer=officer, logs=logs)

    except Exception as e:
        logger.error(f"Security dashboard error: {e}")
        return f"Security dashboard error: {e}", 500


@app.route("/security/logout")
@officer_required
def security_logout():
    session.pop('officer_id', None)
    session.pop('officer_name', None)
    return redirect(url_for('security_login'))


# ============================================
# API AUTH ROUTES (Resident / Staff)
# ============================================
@app.route("/api/auth/login", methods=["POST"])
def auth_login():
    data = request.get_json(silent=True) or {}
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400

    user = User.authenticate(username, password)
    if not user:
        return jsonify({"error": "Invalid username or password"}), 401

    if user.get("role") not in ["Resident", "RESIDENT"]:
        return jsonify({"error": "Invalid username or password"}), 401

    token = "fake-token-123"
    return jsonify({
        "user_id": user.get("user_id") or user.get("id"),
        "resident_id": user.get("resident_id"),
        "username": user.get("username"),
        "role": user.get("role"),
        "token": token,
        "message": "Login successful",
    }), 200


@app.route("/api/staff/login", methods=["POST"])
def staff_login():
    data = request.get_json(silent=True) or {}
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400

    user = User.authenticate(username, password)
    if not user:
        return jsonify({"error": "Invalid username or password"}), 401

    if user.get("role") not in ["Internal_Staff", "INTERNAL_STAFF", "Staff"]:
        return jsonify({"error": "Invalid username or password"}), 401

    token = "fake-staff-token-123"
    uid = user.get("user_id") or user.get("id")

    return jsonify({
        "user_id": uid,
        "staff_id": uid,
        "username": user.get("username"),
        "role": user.get("role"),
        "token": token,
        "message": "Login successful",
        "name": user.get("username"),
        "email": user.get("email", "")
    }), 200


# ============================================
# INIT + MAIN
# ============================================
def init_app(app_):
    os.makedirs(Config.FACE_RECOGNITION['upload_dir'], exist_ok=True)
    os.makedirs(Config.FACE_RECOGNITION['encoding_dir'], exist_ok=True)
    os.makedirs(Config.FACE_RECOGNITION['id_doc_dir'], exist_ok=True)

    try:
        with app_.app_context():
            conn = get_db_connection()
            conn.close()
            logger.info("Database connection successful")
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise

    # Optional startup expiry check
    try:
        with app_.app_context():
            if hasattr(User, "check_expired_temp_workers"):
                expired_count = User.check_expired_temp_workers()
                if expired_count:
                    logger.info(f"Deactivated {expired_count} expired temporary workers on startup")
    except Exception as e:
        logger.warning(f"Could not check expired temp workers: {e}")

    logger.info("Application initialized")


if __name__ == '__main__':
    init_app(app)
    print("\n" + "=" * 60)
    print("FACE RECOGNITION - ADMIN PANEL")
    print("=" * 60)
    print(f"\nPortal: http://localhost:{Config.PORT}/")
    print(f"Login page: http://localhost:{Config.PORT}/login")
    print(f"Admin login: http://localhost:{Config.PORT}/admin/login")
    print("=" * 60 + "\n")
    app.run(host=Config.HOST, port=Config.PORT, debug=False)
