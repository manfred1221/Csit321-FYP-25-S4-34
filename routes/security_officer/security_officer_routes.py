from flask import Blueprint, request, jsonify, Response
from .security_officer_model import SecurityOfficer, db, FaceEmbedding, log_access
import numpy as np
from .security_officer_controller import image_to_embedding
from .security_officer_controller import (
    monitor_camera,
    manual_override,
    view_profile,
    update_profile,
    delete_account,
    deactivate_account,
    verify_face as face_verify
)

security_officer_bp = Blueprint("security_officer", __name__)


@security_officer_bp.route("/manual_override", methods=["POST"])
def route_manual_override():
    data = request.get_json() or {}
    officer_id = data.get("officer_id")
    result = manual_override(officer_id)
    return jsonify(result)

@security_officer_bp.route("/profile/<int:officer_id>", methods=["GET"])
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


@security_officer_bp.route("/profile/<int:officer_id>", methods=["PUT"])
def route_update_profile(officer_id):
    return update_profile(officer_id, request.json)

@security_officer_bp.route("/account/<int:officer_id>", methods=["DELETE"])
def route_delete_account(officer_id):
    return delete_account(officer_id)

@security_officer_bp.route("/face_verify", methods=["POST"])
def verify_face_route():
    return face_verify()

@security_officer_bp.route("/deactivate_account/<int:officer_id>", methods=["POST"])
def route_deactivate_account(officer_id):
    return deactivate_account(officer_id)

@security_officer_bp.route("/monitor_camera")
def route_monitor_camera():
    from .security_officer_controller import monitor_camera
    return monitor_camera()

@security_officer_bp.route("/test", methods=["GET"])
def test_route():
    return jsonify({"status": "ok"})

@security_officer_bp.route("/register_officer", methods=["POST"])
def register_officer():
    """
    Completes registration for new officer
    Receives: { "officer_id", "full_name", "contact_number", "shift", "image" }
    """
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

    # Store embedding
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


@security_officer_bp.route("/verify_face", methods=["POST"])
def verify_face():
    """
    Receives JSON: { "image": "<base64>", "officer_id": optional }
    If face exists: verify
    If new: create officer and embedding
    """
    data = request.get_json()
    image_base64 = data.get("image")
    officer_id = data.get("officer_id")

    if not image_base64:
        return jsonify({"status":"error","message":"No image provided"}), 400

    # Convert image to embedding
    embedding_vector = image_to_embedding(image_base64)

    # Try to match existing embeddings
    all_embeddings = FaceEmbedding.query.filter_by(user_type="security_officer").all()
    threshold = 0.8  # cosine similarity threshold

    def cosine_similarity(a, b):
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

    matched_officer = None
    for fe in all_embeddings:
        sim = cosine_similarity(embedding_vector, fe.embedding)
        if sim > threshold:
            matched_officer = SecurityOfficer.query.get(fe.reference_id)
            log_access(
                recognized_person=matched_officer.full_name,
                person_type="security_officer",
                confidence=float(sim),
                result="granted",
                embedding_id=fe.embedding_id
            )
            break

    # If recognized, return success
    if matched_officer:
        return jsonify({
            "status": "success",
            "message": f"Face verified for {matched_officer.full_name}",
            "officer_id": matched_officer.officer_id
        })

    # If not recognized, create new officer as "New Officer"
    new_officer = SecurityOfficer(full_name="New Officer")
    db.session.add(new_officer)
    db.session.commit()
    officer_id = new_officer.officer_id

    # Store embedding
    new_embedding = FaceEmbedding(
        user_type="security_officer",
        reference_id=officer_id,
        embedding=embedding_vector
    )
    db.session.add(new_embedding)
    db.session.commit()

    log_access(
        recognized_person=new_officer.full_name,
        person_type="security_officer",
        confidence=1.0,
        result="granted",
        embedding_id=new_embedding.embedding_id
    )

    return jsonify({
        "status": "success",
        "message": f"New officer registered: {new_officer.full_name}",
        "officer_id": officer_id
    })
