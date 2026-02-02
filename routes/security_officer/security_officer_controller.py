from flask import jsonify, request, Response
from datetime import datetime
import numpy as np
import cv2
from .security_officer_model import get_officer, deactivate_officer, get_embedding, log_access, db, SecurityOfficer, AccessLog, FaceEmbedding
import base64
from PIL import Image  
import io
from io import BytesIO
from facenet_pytorch import MTCNN, InceptionResnetV1
import torch

resnet = InceptionResnetV1(pretrained='vggface2').eval()


def manual_override(officer_id=None):
    """
    Manually opens the gate and logs the action.
    `officer_id` is optional; pass if you want to track who did it.
    """
    try:
        # Here you would trigger actual gate hardware in a real system
        # For now, we simulate success
        access_result = "granted"
        recognized_person = "manual_override"

        # Log the manual override event
        log = AccessLog(
            access_time=datetime.utcnow(),
            recognized_person=recognized_person,
            person_type="security_officer",
            confidence=1.0,
            access_result=access_result
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
        return jsonify({
            "officer_id": officer.officer_id,
            "full_name": officer.full_name,
            "contact_number": officer.contact_number,
            "shift": officer.shift,
            "active": officer.active
        }), 200
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

# Set device
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# FaceNet components
mtcnn = MTCNN(image_size=160, margin=20, device=device)
resnet = InceptionResnetV1(pretrained='vggface2').eval().to(device)

ENABLE_GAN_ATTACK = True
import torch.nn.functional as F

def gan_impersonation_attack(face_tensor, target_embedding, *, steps: int = 10, alpha: float = 0.02):
    """
    face_tensor: (1, 3, 160, 160)
    target_embedding: (512,)
    returns adversarial face tensor
    """
    adv_face = face_tensor.clone().detach().requires_grad_(True)

    target_embedding = torch.tensor(
        target_embedding, dtype=torch.float32, device=face_tensor.device
    ).unsqueeze(0)

    optimizer = torch.optim.Adam([adv_face], lr=0.01)

    for _ in range(steps):
        optimizer.zero_grad()

        adv_embedding = resnet(adv_face)

        # ❗ maximize similarity to target identity
        loss = -F.cosine_similarity(adv_embedding, target_embedding).mean()

        loss.backward()
        optimizer.step()

        # keep image valid
        adv_face.data = torch.clamp(adv_face.data, -1, 1)

    return adv_face.detach()


def image_to_embedding(image_base64):
    """Convert base64 image to FaceNet embedding (512-D)"""

    # Remove data URL prefix if present
    if "," in image_base64:
        image_base64 = image_base64.split(",", 1)[1]

    img_bytes = base64.b64decode(image_base64)
    img = Image.open(BytesIO(img_bytes)).convert("RGB")

    # 🔑 Detect & align face
    face = mtcnn(img)

    if face is None:
        return None  # no face detected

    face = face.unsqueeze(0).to(device)

    if ENABLE_GAN_ATTACK:
        target_embedding = get_random_target_embedding()
        face = gan_impersonation_attack(face, target_embedding)

    with torch.no_grad():
        embedding = resnet(face)

    return embedding.cpu().numpy().flatten()  # 512-D

from sqlalchemy.sql import func

def get_random_target_embedding():
    fe = FaceEmbedding.query.filter(
        FaceEmbedding.user_type.in_(["resident", "visitor"]),
        FaceEmbedding.reference_id != None
    ).order_by(func.random()).first()
    return np.array(fe.embedding, dtype=np.float32)


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

    embedding_vector = image_to_embedding(image_base64)

    # 1. Try to find existing officer by comparing embeddings
    all_embeddings = FaceEmbedding.query.filter_by(user_type="security_officer").all()
    threshold = 0.8  # cosine similarity threshold
    def cosine_similarity(a,b):
        return np.dot(a,b)/(np.linalg.norm(a)*np.linalg.norm(b))

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

    # 2. If found, return success
    if matched_officer:
        return jsonify({
            "status":"success",
            "message":f"Face verified for {matched_officer.full_name}",
            "officer_id": matched_officer.officer_id
        })

    # 3. If not found, create new officer
    if not officer_id:
        # Require at least full_name
        full_name = data.get("full_name","New Officer")
        new_officer = SecurityOfficer(full_name=full_name)
        db.session.add(new_officer)
        db.session.commit()
        officer_id = new_officer.officer_id
    else:
        new_officer = SecurityOfficer.query.get(officer_id)
        if not new_officer:
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
        "status":"success",
        "message":f"New officer registered: {new_officer.full_name}",
        "officer_id": officer_id
    })

camera = cv2.VideoCapture(0)  # 0 = default webcam

def generate_frames():
    while True:
        success, frame = camera.read()
        if not success:
            break
        else:
            # Encode frame as JPEG
            ret, buffer = cv2.imencode('.jpg', frame)
            frame_bytes = buffer.tobytes()
            # Yield frame in multipart format
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

def monitor_camera():
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')
