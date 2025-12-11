import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import random
from flask import Flask, send_from_directory, render_template, jsonify, request, redirect
from werkzeug.security import generate_password_hash
from flask_cors import CORS
from routes.security_officer.security_officer_routes import security_officer_bp
from routes.security_officer.security_officer_model import db, User, Role, SecurityOfficer, AccessLog, FaceEmbedding, log_access
import torch

import io
import base64
import numpy as np
from PIL import Image
from facenet_pytorch import InceptionResnetV1, MTCNN
from sqlalchemy import select
from sqlalchemy.orm import load_only

# initialize MTCNN and FaceNet once (module-level)
mtcnn = MTCNN(image_size=160, margin=0, min_face_size=40)
resnet = InceptionResnetV1(pretrained='vggface2').eval()

backend_security = Flask(__name__)
CORS(backend_security, resources={r"/api/*": {"origins": "*"}}, supports_credentials=True)


# PostgreSQL config
backend_security.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:joshua1102@localhost:5432/CSIT321: Face Recognition'
backend_security.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(backend_security)
with backend_security.app_context():
    db.create_all()

# Register blueprint
backend_security.register_blueprint(security_officer_bp, url_prefix="/api/security_officer")

from flask import request, jsonify, render_template, redirect

@backend_security.route("/login", methods=["GET", "POST"])
def login():
    # Show login page
    if request.method == "GET":
        return render_template("login.html")

    # Handle login POST
    try:
        data = request.get_json()

        if data is None:
            return jsonify({"success": False, "message": "Invalid JSON payload"}), 400

        user_type = data.get("user_type")
        user_id = data.get("user_id")

        if not user_type or not user_id:
            return jsonify({"success": False, "message": "Missing user_type or user_id"}), 400

        # Validate based on user type
        if user_type == "security_officer":
            officer = SecurityOfficer.query.get(user_id)
            if not officer:
                return jsonify({"success": False, "message": "Security officer not found"}), 404

            return jsonify({
                "success": True,
                "redirect": f"/?officer_id={officer.officer_id}"
            })

        # Placeholder for residents/visitors
        return jsonify({"success": False, "message": "Unsupported user type"}), 400

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@backend_security.route("/")
def index():
    officer_id = request.args.get("officer_id", type=int)
    
    if not officer_id:
        return redirect("/login")

    officer = SecurityOfficer.query.get(officer_id)
    if not officer:
        return "Officer not found", 404

    access_logs = AccessLog.query.order_by(AccessLog.log_id.asc()).all()

    return render_template("security-dashboard.html",
                           officer=officer,
                           logs=access_logs)


@backend_security.route("/security-deactivate")
def deactivate():
    officer_id = request.args.get("officer_id", type=int)
    if not officer_id:
        return redirect("/login")

    officer = SecurityOfficer.query.get(officer_id)
    if not officer:
        return "Officer not found", 404
    
    return render_template("security-deactivate.html", officer=officer)

@backend_security.route("/security-override")
def manual_override():
    officer_id = request.args.get("officer_id", type=int)
    if not officer_id:
        return redirect("/login")

    officer = SecurityOfficer.query.get(officer_id)
    if not officer:
        return "Officer not found", 404
    
    return render_template("security-override.html", officer=officer)

@backend_security.route("/security-view-profile")
def view_profile():
    officer_id = request.args.get("officer_id", type=int)
    if not officer_id:
        return redirect("/login")

    officer = SecurityOfficer.query.get(officer_id)
    if not officer:
        return "Officer not found", 404

    return render_template("security-view-profile.html", officer=officer)


@backend_security.route("/security-update-profile")
def update_profile():   
    officer_id = request.args.get("officer_id", type=int)
    if not officer_id:
        return redirect("/login")

    officer = SecurityOfficer.query.get(officer_id)
    if not officer:
        return "Officer not found", 404
    
    return render_template("security-update-profile.html", officer=officer)

@backend_security.route("/api/update-officer", methods=["POST"])
def api_update_officer():
    data = request.json
    print("DEBUG JSON:", data)

    # Try query params first
    officer_id = request.args.get("officer_id", type=int)

    # If not found, try JSON body
    if not officer_id:
        officer_id = data.get("officer_id")

    # Final check
    if not officer_id:
        return jsonify({"success": False, "message": "Missing officer_id"}), 400


    officer = db.session.get(SecurityOfficer, officer_id)
    if not officer:
        return jsonify({"success": False, "message": "Officer not found"}), 404

    print("DEBUG OFFICER BEFORE:", officer.full_name, officer.contact_number, officer.shift)

    officer.full_name = data.get("full_name", officer.full_name)
    officer.contact_number = data.get("contact_number", officer.contact_number)
    officer.shift = data.get("shift", officer.shift)

    db.session.commit()
    print("DEBUG OFFICER AFTER:", officer.full_name, officer.contact_number, officer.shift)

    return jsonify({"success": True, "message": "Profile updated"}), 200


@backend_security.route("/security-face-verification")
def face_verification():
    officer_id = request.args.get("officer_id", type=int)
    if not officer_id:
        return redirect("/login")

    officer = SecurityOfficer.query.get(officer_id)
    if not officer:
        return "Officer not found", 404
    
    return render_template("security-face-verification.html", officer=officer)   


# @backend_security.route("/index2")
# def index2():
#     return render_template("index2.html")

# Optional: serve static files if needed
@backend_security.route("/static/<path:filename>")
def serve_static(filename):
    return send_from_directory("static", filename)

def image_from_base64(base64_data):
    # base64_data should be "data:image/png;base64,AAA..." or raw base64
    if base64_data.startswith('data:'):
        base64_data = base64_data.split(',', 1)[1]
    image_bytes = base64.b64decode(base64_data)
    return Image.open(io.BytesIO(image_bytes)).convert('RGB')

def compute_embedding(pil_img):
    # detect & crop face with MTCNN, returns 512-d numpy array or None
    face = mtcnn(pil_img)
    if face is None:
        return None
    # face is a torch Tensor (3,160,160) normalized by MTCNN; pass to resnet
    with torch.no_grad():
        emb = resnet(face.unsqueeze(0))   # shape (1,512)
    emb_np = emb.cpu().numpy().reshape(-1)
    # normalize to unit vector (cosine similarity)
    emb_np = emb_np / np.linalg.norm(emb_np)
    return emb_np

@backend_security.route("/api/verify-face", methods=["POST"])
def api_verify_face():
    """
    Expects JSON: { image: "<base64 data URI or raw base64>" }
    Returns JSON with match info.
    """
    payload = request.json or {}
    img_b64 = payload.get("image")
    if not img_b64:
        return jsonify({"success": False, "error": "No image provided"}), 400

    # decode and compute embedding
    try:
        pil_img = image_from_base64(img_b64)
    except Exception as e:
        return jsonify({"success": False, "error": f"Bad image: {str(e)}"}), 400

    emb = compute_embedding(pil_img)
    if emb is None:
        # no face detected
        # log unknown with confidence 0
        log = log_access("Unknown", "unknown", 0.0, "denied", None)
        return jsonify({"success": False, "result": "no_face", "message": "No face detected"}), 200

    # load all stored embeddings from DB
    # We'll build lists: embeddings (n,512), ids, user_types, reference_ids
    rows = FaceEmbedding.query.all()
    if not rows:
        # no embeddings in DB
        log = log_access("Unknown", "unknown", 0.0, "denied", None)
        return jsonify({"success": False, "result": "no_db_embeddings", "message": "No embeddings in database"}), 200

    db_embs = []
    db_meta = []  # tuples (embedding_id, user_type, reference_id)
    for r in rows:
        # r.embedding may be returned as a list/tuple — convert to np.array
        try:
            vec = np.array(r.embedding, dtype=np.float32)
        except Exception:
            # if pgvector returns memoryview, etc.
            vec = np.asarray(r.embedding, dtype=np.float32)
        # normalize (defensive)
        if np.linalg.norm(vec) == 0:
            continue
        vec = vec / np.linalg.norm(vec)
        db_embs.append(vec)
        db_meta.append((r.embedding_id, r.user_type, r.reference_id))

    db_embs = np.vstack(db_embs)  # shape (N,512)

    # compute cosine similarities: emb (1,512) dot rows -> (N,)
    sims = db_embs.dot(emb)  # because both are normalized, dot=cosine
    best_idx = int(np.argmax(sims))
    best_score = float(sims[best_idx])

    # threshold for match — tune as needed (0.75 default)
    THRESHOLD = 0.75

    emb_id, user_type, reference_id = db_meta[best_idx]

    # map reference_id to human-readable name (try known tables)
    name = "Unknown"
    try:
        if user_type == "security_officer":
            so = SecurityOfficer.query.filter_by(officer_id=reference_id).first()
            name = so.full_name if so else "Unknown Officer"
        elif user_type == "resident":
            try:
                from routes.security_officer.security_officer_model import Resident
                res = Resident.query.get(reference_id)
                if res:
                    name = getattr(res, "full_name", getattr(res, "name", str(reference_id)))
            except Exception:
                name = f"Resident:{reference_id}"
        elif user_type == "visitor":
            try:
                from routes.security_officer.security_officer_model import Visitor
                vis = Visitor.query.get(reference_id)
                if vis:
                    name = getattr(vis, "full_name", getattr(vis, "name", str(reference_id)))
            except Exception:
                name = f"Visitor:{reference_id}"
        elif user_type in ["internal_staff", "temp_staff", "TEMP_STAFF", "Internal_Staff"]:
            # Try to get staff name from internal_staff table or temp_staff table
            try:
                # Try internal_staff table
                from sqlalchemy import text
                result = db.session.execute(
                    text("SELECT full_name FROM internal_staff WHERE staff_id = :ref_id"),
                    {"ref_id": reference_id}
                ).fetchone()
                if result:
                    name = result[0]
                else:
                    # Try temp_staff table
                    result = db.session.execute(
                        text("SELECT full_name FROM temp_staff WHERE temp_id = :ref_id"),
                        {"ref_id": reference_id}
                    ).fetchone()
                    if result:
                        name = result[0]
                    else:
                        name = f"Staff:{reference_id}"
            except Exception as e:
                name = f"Staff:{reference_id}"
        elif user_type == "ADMIN":
            name = "Administrator"
        else:
            name = f"{user_type}:{reference_id}"
    except Exception:
        name = f"{user_type}:{reference_id}"

    # Determine verified or not
    if best_score >= THRESHOLD:
        result = "verified"
        access_result = "granted"
    else:
        result = "failed"
        access_result = "denied"

    # persist log
    # recognized_person store human-readable name, person_type store user_type
    log = log_access(recognized_person=name, person_type=user_type, confidence=float(best_score), result=access_result, embedding_id=emb_id)

    return jsonify({
        "success": True,
        "result": result,
        "name": name,
        "user_type": user_type,
        "confidence": round(best_score * 100, 2),  # percent
        "access_result": access_result,
        "log_id": log.log_id
    }), 200


# ==========================================================================================================================================
# Creating Admin User for Testing

    # Create a test admin user
@backend_security.route("/test_create_admin", methods=["GET", "POST"])
def test_create_admin():
    try:
        # Check if admin role exists
        admin_role = Role.query.filter_by(role_name="ADMIN").first()
        if not admin_role:
            admin_role = Role(role_name="ADMIN")
            db.session.add(admin_role)
            db.session.commit()

        # Create a sample admin user
        sample_admin = User(
             username=f"admin_test_{random.randint(1,1000)}",
            email=f"admin{random.randint(1,1000)}@example.com",
            password_hash=generate_password_hash("password123"),
            role_id=admin_role.role_id
        )

        # Insert into database
        db.session.add(sample_admin)
        db.session.commit()

        return jsonify({
            "status": "success",
            "message": "Admin user created",
            "user_id": sample_admin.user_id
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500


# Optional: list all users (for testing)
@backend_security.route("/test_list_users", methods=["GET"])
def test_list_users():
    users = User.query.all()
    result = []
    for u in users:
        role_name = u.role.role_name if u.role else None
        result.append({
            "user_id": u.user_id,
            "username": u.username,
            "email": u.email,
            "role": role_name
        })
    return jsonify(result)

if __name__ == "__main__":
    backend_security.run(debug=True, port=5001)

