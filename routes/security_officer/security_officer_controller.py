from flask import jsonify, request, Response
from datetime import datetime
import base64
from io import BytesIO
import numpy as np

from PIL import Image  # keep if you still need it elsewhere

import os

ENABLE_GAN_ATTACK = os.getenv("ENABLE_GAN_ATTACK", "false").lower() == "true"


# ✅ Remote ML embedding (Cloud Run)
from ml_client import get_embedding as get_remote_embedding

# ✅ Your DB/model helpers
from .security_officer_model import (
    get_officer,
    deactivate_officer,
    log_access,
    db,
    SecurityOfficer,
    AccessLog,
    FaceEmbedding,
)
def image_to_embedding(image_base64: str):
    if not image_base64:
        raise ValueError("Missing image data")

    if "," in image_base64:
        image_base64 = image_base64.split(",", 1)[1]

    emb = get_remote_embedding(image_base64)
    if emb is None:
        raise ValueError("No face detected")

    return emb


# Optional: OpenCV camera streaming (won't crash if not installed)
try:
    import cv2
except Exception:
    cv2 = None


# -----------------------------
# Account / profile actions
# -----------------------------
def manual_override(officer_id=None):
    """
    Manually opens the gate and logs the action.
    officer_id is optional.
    """
    try:
        access_result = "granted"
        recognized_person = "manual_override"

        log = AccessLog(
            access_time=datetime.utcnow(),
            recognized_person=recognized_person,
            person_type="security_officer",
            confidence=1.0,
            access_result=access_result,
        )
        db.session.add(log)
        db.session.commit()

        return {"status": "success", "message": "Gate opened manually"}

    except Exception as e:
        db.session.rollback()
        return {"status": "error", "message": str(e)}


def view_profile(officer_id):
    officer = get_officer(officer_id)
    if officer:
        return jsonify(
            {
                "officer_id": officer.officer_id,
                "full_name": officer.full_name,
                "contact_number": officer.contact_number,
                "shift": officer.shift,
                "active": officer.active,
            }
        ), 200
    return jsonify({"error": "Officer not found"}), 404


def update_profile(officer_id, data):
    officer = get_officer(officer_id)
    if officer:
        for key, value in data.items():
            if hasattr(officer, key):
                setattr(officer, key, value)
        db.session.commit()
        return jsonify({"message": "Profile updated"}), 200
    return jsonify({"error": "Officer not found"}), 404


def delete_account(officer_id):
    officer = get_officer(officer_id)
    if officer:
        db.session.delete(officer)
        db.session.commit()
        return jsonify({"message": "Account deleted"}), 200
    return jsonify({"error": "Officer not found"}), 404


def deactivate_account(officer_id):
    officer = deactivate_officer(officer_id)
    if officer:
        return jsonify({"message": "Account deactivated"}), 200
    return jsonify({"error": "Officer not found"}), 404


# -----------------------------
# Face verification (REMOTE ML)
# -----------------------------
def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    denom = (np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)


def verify_face():
    """
    Receives JSON:
      {
        "image": "<base64 or dataURL>",
        "officer_id": optional,
        "full_name": optional (if creating new)
      }

    Flow:
      - Get embedding from Cloud Run ML service
      - Compare to existing security_officer embeddings
      - If match: return verified
      - Else: create officer (or use officer_id), store embedding, return registered
    """
    data = request.get_json(silent=True) or {}
    image_base64 = data.get("image")
    officer_id = data.get("officer_id")

    if not image_base64:
        return jsonify({"status": "error", "message": "No image provided"}), 400

    # ✅ Call Cloud Run ML
    embedding_list = get_remote_embedding(image_base64)
    if embedding_list is None:
        return jsonify({"status": "error", "message": "No face detected. Please try again."}), 400

    embedding_vector = np.array(embedding_list, dtype=np.float32)

    # 1) Match existing security officer
    all_embeddings = FaceEmbedding.query.filter_by(user_type="security_officer").all()

    threshold = 0.80  # cosine similarity threshold (tune as needed)
    matched_officer = None

    for fe in all_embeddings:
        try:
            stored = np.array(fe.embedding, dtype=np.float32)
        except Exception:
            continue

        sim = _cosine_similarity(embedding_vector, stored)
        if sim > threshold:
            matched_officer = SecurityOfficer.query.get(fe.reference_id)

            if matched_officer:
                log_access(
                    recognized_person=matched_officer.full_name,
                    person_type="security_officer",
                    confidence=float(sim),
                    result="granted",
                    embedding_id=fe.embedding_id,
                )
                break

    if matched_officer:
        return jsonify(
            {
                "status": "success",
                "message": f"Face verified for {matched_officer.full_name}",
                "officer_id": matched_officer.officer_id,
            }
        ), 200

    # 2) Not found -> create / attach officer
    if not officer_id:
        full_name = data.get("full_name") or "New Officer"
        new_officer = SecurityOfficer(full_name=full_name)
        db.session.add(new_officer)
        db.session.commit()
        officer_id = new_officer.officer_id
    else:
        new_officer = SecurityOfficer.query.get(officer_id)
        if not new_officer:
            new_officer = SecurityOfficer(full_name=data.get("full_name") or "New Officer")
            db.session.add(new_officer)
            db.session.commit()
            officer_id = new_officer.officer_id

    # 3) Store embedding for this officer
    new_embedding = FaceEmbedding(
        user_type="security_officer",
        reference_id=officer_id,
        embedding=embedding_vector.tolist(),  # store as JSON-serializable
    )
    db.session.add(new_embedding)
    db.session.commit()

    log_access(
        recognized_person=new_officer.full_name,
        person_type="security_officer",
        confidence=1.0,
        result="granted",
        embedding_id=new_embedding.embedding_id,
    )

    return jsonify(
        {
            "status": "success",
            "message": f"New officer registered: {new_officer.full_name}",
            "officer_id": officer_id,
        }
    ), 200


# -----------------------------
# Camera streaming (OPTIONAL)
# -----------------------------
_camera = None

def generate_frames():
    if cv2 is None:
        return
    global _camera
    if _camera is None:
        _camera = cv2.VideoCapture(0)

    while True:
        success, frame = _camera.read()
        if not success:
            break

        ret, buffer = cv2.imencode(".jpg", frame)
        if not ret:
            continue

        frame_bytes = buffer.tobytes()
        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n"
        )


def monitor_camera():
    if cv2 is None:
        return jsonify({
            "status": "error",
            "message": "Camera streaming disabled because opencv is not installed on this server."
        }), 501

    return Response(generate_frames(), mimetype="multipart/x-mixed-replace; boundary=frame")
