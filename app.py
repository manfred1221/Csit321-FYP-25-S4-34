import os

# Render/Gunicorn: don't import optional stuff at module import-time
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

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
from user import User, Resident
from access_log import AccessLog
from psycopg2.extras import RealDictCursor
from database import DATABASE_URL, get_db_connection

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# ✅ Keep flag here (instead of importing from security_officer_controller)
# If you later want to switch it on/off, use ENV: ENABLE_GAN_ATTACK=true/false
ENABLE_GAN_ATTACK = os.getenv("ENABLE_GAN_ATTACK", "false").lower() in ("1", "true", "yes", "y")

# ============================================================
# Optional Security Officer imports (safe on Render)
# ============================================================
try:
    from routes.security_officer.security_officer_model import (
        SecurityOfficer, db, FaceEmbedding, log_access, Visitor, AccessLog as SOAccessLog
    )
    from routes.security_officer.security_officer_controller import (
        image_to_embedding,
        monitor_camera,
        manual_override as so_manual_override_fn,
        view_profile as so_view_profile_fn,
        update_profile as so_update_profile_fn,
        delete_account as so_delete_account_fn,
        deactivate_account as so_deactivate_account_fn,
        verify_face as face_verify
    )
    SECURITY_OFFICER_AVAILABLE = True
except Exception as e:
    logger.warning(f"Security officer modules not available: {e}")
    SECURITY_OFFICER_AVAILABLE = False
    SecurityOfficer = None
    db = None
    FaceEmbedding = None
    log_access = None
    Visitor = None
    SOAccessLog = None
    image_to_embedding = None
    monitor_camera = None
    so_manual_override_fn = None
    so_view_profile_fn = None
    so_update_profile_fn = None
    so_delete_account_fn = None
    so_deactivate_account_fn = None
    face_verify = None


# ============================================================
# Helpers
# ============================================================
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "pdf"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("admin_login"))
        user = User.get_by_id(session["user_id"])
        if not user or user.get("role") != "Admin":
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    return decorated

def check_user_has_face_embedding(user):
    """Check if user has a registered face embedding"""
    if not user:
        return None

    user_role = (user.get("role") or "").lower()
    user_id = user.get("id")

    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        if user_role == "admin":
            user_type = "admin"
            reference_id = user_id
        elif user_role in ["internal_staff", "staff", "temp_worker"]:
            user_type = "staff"
            reference_id = user_id
        elif user_role == "resident":
            user_type = "resident"
            resident_id = user.get("resident_id")
            if not resident_id:
                cursor.close()
                conn.close()
                return None
            reference_id = resident_id
        else:
            cursor.close()
            conn.close()
            return None

        cursor.execute(
            """
            SELECT embedding_id FROM face_embeddings
            WHERE reference_id = %s AND user_type = %s
            LIMIT 1
            """,
            (reference_id, user_type),
        )
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        return result["embedding_id"] if result else None
    except Exception as e:
        logger.error(f"Error checking face embedding: {e}")
        return None


# ============================================================
# APP FACTORY (Render / Gunicorn safe)
# ============================================================
def create_app():
    app = Flask(__name__)

    @app.get("/healthz")
    def healthz():
        return {"ok": True}, 200

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

    # Support both frontend and templates folders
    app.jinja_loader = ChoiceLoader([
        FileSystemLoader(os.path.join(BASE_DIR, "templates")),
        FileSystemLoader(os.path.join(BASE_DIR, "frontend")),
    ])

    app.config["SECRET_KEY"] = Config.SECRET_KEY
    app.config["PERMANENT_SESSION_LIFETIME"] = Config.SESSION_LIFETIME
    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024
    CORS(app)

    # ============================================================
    # REGISTER BCE BLUEPRINT
    # ============================================================
    try:
        from boundary import staff_bp
        app.register_blueprint(staff_bp, url_prefix="/api/staff")
        logger.info("✅ Staff BCE blueprint registered at /api/staff")
    except Exception as e:
        logger.error(f"❌ Could not import staff blueprint: {e}")

    # ============================================================
    # REGISTER RESIDENT BLUEPRINTS
    # ============================================================
    try:
        from routes.auth_routes import auth_bp
        from routes.resident_routes import resident_bp
        from routes.visitor_routes import visitor_bp

        app.register_blueprint(auth_bp, url_prefix="/api/auth")
        app.register_blueprint(resident_bp, url_prefix="/api/resident")
        app.register_blueprint(visitor_bp, url_prefix="/api/visitor")

        logger.info("✅ Resident blueprints registered:")
        logger.info("   - /api/auth (authentication)")
        logger.info("   - /api/resident (resident features)")
        logger.info("   - /api/visitor (visitor management)")
    except Exception as e:
        logger.error(f"❌ Could not import resident blueprints: {e}")

    # ============================================================
    # FRONTEND ROUTES
    # ============================================================
    @app.route("/")
    def index():
        return redirect(url_for("unified_login"))

    @app.route("/login", methods=["GET"])
    def unified_login():
        session.clear()
        return send_from_directory("templates", "login.html")

    # NOTE: you had 2x /login routes before. Keep ONE only.
    @app.route("/frontend/index.html")
    def frontend_login_redirect():
        return redirect(url_for("unified_login"))

    @app.route("/frontend/css/<path:filename>")
    def frontend_css(filename):
        return send_from_directory("frontend/css", filename)

    @app.route("/templates/css/<path:filename>")
    def template_css(filename):
        return send_from_directory(os.path.join(app.root_path, "templates", "css"), filename)

    @app.route("/frontend/js/<path:filename>")
    def frontend_js(filename):
        return send_from_directory("frontend/js", filename)

    @app.route("/frontend/<path:filename>")
    def frontend_static(filename):
        return send_from_directory("frontend", filename)

    # ============================================================
    # Security Officer page decorators + routes
    # ============================================================
    def officer_required(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if "officer_id" not in session or session.get("role") != "security_officer":
                return redirect(url_for("unified_login"))
            return f(*args, **kwargs)
        return decorated

    # =========================
    # AUTH ROUTE
    # =========================
    @app.route("/admin/login", methods=["POST"])
    def admin_login():
        data = request.json or {}
        username = (data.get("username") or "").strip()
        password = data.get("password") or ""

        if not username:
            return jsonify({"success": False, "message": "Username is required"}), 400

        logger.info(f"🔑 Login attempt: username={username}")

        # 1) Security Officer by numeric username (officer_id)
        if username.isdigit() and SECURITY_OFFICER_AVAILABLE:
            try:
                officer = SecurityOfficer.query.get(int(username))
                if officer and officer.active:
                    session["officer_id"] = officer.officer_id
                    session["officer_name"] = officer.full_name
                    session["role"] = "security_officer"
                    session.permanent = True

                    return jsonify({
                        "success": True,
                        "role": "security_officer",
                        "user_data": {
                            "officer_id": officer.officer_id,
                            "full_name": officer.full_name
                        },
                        "redirect": "/security-dashboard"
                    }), 200
            except Exception as e:
                logger.debug(f"Security officer check failed: {e}")

        # 2) users table auth
        try:
            user = User.authenticate(username, password)
        except Exception as e:
            logger.error(f"❌ Authentication failed: {e}")
            user = None

        if not user:
            return jsonify({"success": False, "message": "Invalid username or password"}), 401

        role_id = user.get("role_id")
        role_name = user.get("role", "")
        user_id = user.get("id")

        # Admin
        if role_id == 1:
            session["user_id"] = user_id
            session["username"] = user["username"]
            session["role"] = "Admin"
            session.permanent = True
            return jsonify({"success": True, "role": "Admin", "redirect": "/admin/profile"}), 200

        # Resident
        if role_id == 2:
            resident_id = user.get("resident_id") or user_id
            session["user_id"] = user_id
            session["resident_id"] = resident_id
            session["username"] = user["username"]
            session["role"] = "Resident"
            session.permanent = True
            return jsonify({"success": True, "role": "Resident", "redirect": f"/resident/dashboard?resident_id={resident_id}"}), 200

        # Visitor / Internal Staff
        if role_id in (3, 9):
            if "visitor" in role_name.lower():
                session["user_id"] = user_id
                session["visitor_id"] = user_id
                session["username"] = user["username"]
                session["role"] = "Visitor"
                session.permanent = True
                return jsonify({"success": True, "role": "Visitor", "redirect": f"/visitor/dashboard?visitor_id={user_id}"}), 200

            session["user_id"] = user_id
            session["staff_id"] = user_id
            session["username"] = user["username"]
            session["role"] = "Internal_Staff"
            session.permanent = True
            return jsonify({"success": True, "role": "Internal_Staff", "redirect": f"/staff/dashboard?staff_id={user_id}"}), 200

        # Security Officer via users table
        if role_id == 4 and SECURITY_OFFICER_AVAILABLE:
            session["user_id"] = user_id
            session["username"] = user["username"]
            session["role"] = "security_officer"

            officer_profile = SecurityOfficer.query.filter_by(user_id=user_id).first()
            if officer_profile:
                session["officer_id"] = officer_profile.officer_id
                session["officer_name"] = officer_profile.full_name
            else:
                logger.warning(f"⚠️ User {username} has no Security Officer profile!")
                session["officer_id"] = user_id

            session.permanent = True
            return jsonify({"success": True, "role": "security_officer", "redirect": "/security-dashboard"}), 200

        return jsonify({
            "success": False,
            "message": f"Your account type (role_id: {role_id}) is not configured. Contact administrator."
        }), 401

    @app.route("/admin/logout")
    def admin_logout():
        session.clear()
        return redirect(url_for("unified_login"))

    # =========================
    # SECURITY DASHBOARD PAGES
    # =========================
    @app.route("/security-dashboard")
    @officer_required
    def security_dashboard():
        if not SECURITY_OFFICER_AVAILABLE:
            return redirect(url_for("unified_login"))

        officer_id = session.get("officer_id")
        officer = SecurityOfficer.query.get(officer_id)
        if not officer:
            session.clear()
            return redirect(url_for("unified_login"))

        access_logs = SOAccessLog.query.order_by(SOAccessLog.log_id.desc()).limit(50).all()
        granted_count = SOAccessLog.query.filter_by(access_result="granted").count()

        return render_template(
            "security-dashboard.html",
            officer=officer,
            logs=access_logs,
            granted_count=granted_count,
        )

    @app.route("/security/logout")
    def security_logout():
        session.clear()
        return redirect(url_for("unified_login"))

    # ============================================================
    # SECURITY OFFICER API ROUTES
    # ============================================================
    if SECURITY_OFFICER_AVAILABLE:
        @app.route("/api/security_officer/manual_override", methods=["POST"])
        def route_manual_override():
            data = request.get_json() or {}
            officer_id = data.get("officer_id")
            result = so_manual_override_fn(officer_id)
            return jsonify(result)

        @app.route("/api/security_officer/face_verify", methods=["POST"])
        def verify_face_route():
            return face_verify()

        @app.route("/api/security_officer/monitor_camera")
        def route_monitor_camera():
            return monitor_camera()

        # ✅ IMPORTANT: avoid name conflicts with imported functions
        @app.route("/api/security_officer/verify_face", methods=["POST"])
        def verify_face_api():
            try:
                data = request.get_json(force=True)
                image_base64 = data.get("image")

                officer_id = session.get("officer_id")
                if not officer_id:
                    return jsonify({"status": "error", "message": "Session expired. Please login again."}), 401

                if not image_base64:
                    return jsonify({"status": "error", "message": "Missing image"}), 400

                officer = SecurityOfficer.query.get(officer_id)
                if not officer or not officer.active:
                    return jsonify({"status": "error", "message": "Unauthorized officer"}), 403

                # ✅ Use remote ML service (Cloud Run) instead of facenet/torch
                from ml_client import get_embedding as ml_get_embedding

                try:
                    raw_embedding = ml_get_embedding(image_base64)
                except Exception:
                    return jsonify({"status": "error", "message": "Face recognition service unavailable"}), 503

                if raw_embedding is None:
                    return jsonify({"status": "error", "message": "No face detected. Please try again."}), 400

                def normalize(vec):
                    vec = np.array(vec, dtype=np.float32)
                    n = np.linalg.norm(vec) + 1e-12
                    return vec / n

                def cosine_similarity(a, b):
                    return float(np.dot(a, b))

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

                if best_match and best_score >= threshold:
                    if best_match.user_type == "resident":
                        from routes.security_officer.security_officer_model import Resident as SOResident
                        person = SOResident.query.get(best_match.reference_id)
                    else:
                        person = Visitor.query.get(best_match.reference_id)

                    if person is None:
                        log_access(
                            recognized_person="Invalid reference",
                            person_type=best_match.user_type,
                            confidence=best_score,
                            result="denied",
                            embedding_id=best_match.embedding_id,
                            attack_type="gan_impersonation" if ENABLE_GAN_ATTACK else "none",
                        )
                        return jsonify({
                            "status": "error",
                            "result": "denied",
                            "message": "Matched embedding has no valid identity",
                            "confidence": float(round(best_score * 100, 2)),
                        }), 401

                    log_access(
                        recognized_person=person.full_name,
                        person_type=best_match.user_type,
                        confidence=best_score,
                        result="granted",
                        embedding_id=best_match.embedding_id,
                        attack_type="gan_impersonation" if ENABLE_GAN_ATTACK else "none",
                    )

                    return jsonify({
                        "status": "success",
                        "result": "granted",
                        "type": best_match.user_type.capitalize(),
                        "person_type": best_match.user_type,
                        "name": person.full_name,
                        "message": "Face recognized",
                        "confidence": float(round(best_score * 100, 2)),
                    })

                log_access(
                    recognized_person="Unknown",
                    person_type="unknown",
                    confidence=best_score,
                    result="denied",
                    embedding_id=None,
                    attack_type="gan_impersonation" if ENABLE_GAN_ATTACK else "none",
                )

                return jsonify({
                    "status": "error",
                    "result": "denied",
                    "message": "Face not recognized",
                    "confidence": float(round(best_score * 100, 2)),
                }), 401

            except Exception as e:
                logger.exception(f"VERIFY FACE ERROR: {e}")
                return jsonify({"status": "error", "message": "Internal server error during face verification"}), 500

    # ============================================================
    # Initialization
    # ============================================================
    def init_app(app):
        if not SECURITY_OFFICER_AVAILABLE:
            logger.warning("init_app called but SECURITY_OFFICER_AVAILABLE=False; skipping DB init.")
            return

        os.makedirs(Config.FACE_RECOGNITION["upload_dir"], exist_ok=True)
        os.makedirs(Config.FACE_RECOGNITION["encoding_dir"], exist_ok=True)
        os.makedirs(Config.FACE_RECOGNITION["id_doc_dir"], exist_ok=True)

        app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
        app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

        db.init_app(app)

        try:
            with app.app_context():
                conn = get_db_connection()
                conn.close()
                logger.info("Database connection successful")
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            raise

        try:
            with app.app_context():
                expired_count = User.check_expired_temp_workers()
                if expired_count > 0:
                    logger.info(f"Deactivated {expired_count} expired temporary workers on startup")
        except Exception as e:
            logger.warning(f"Could not check expired temp workers: {e}")

        logger.info("Application initialized")

    # run init after everything exists
    init_app(app)

    return app


# ---- THIS IS WHAT GUNICORN IMPORTS ----
app = create_app()

# ---- LOCAL DEV ONLY ----
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
