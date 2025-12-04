from flask_sqlalchemy import SQLAlchemy
from pgvector.sqlalchemy import Vector
from datetime import datetime

db = SQLAlchemy()

class SecurityOfficer(db.Model):
    __tablename__ = "security_officers"
    officer_id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    contact_number = db.Column(db.String(20))
    shift = db.Column(db.String(50))
    active = db.Column(db.Boolean, default=True)
    registered_at = db.Column(db.DateTime, default=datetime.utcnow)

class FaceEmbedding(db.Model):
    __tablename__ = "face_embeddings"
    embedding_id = db.Column(db.Integer, primary_key=True)
    user_type = db.Column(db.String(20))  # resident, visitor, security_officer
    reference_id = db.Column(db.Integer, nullable=False)
    embedding = db.Column(Vector(512))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class AccessLog(db.Model):
    __tablename__ = "access_logs"
    log_id = db.Column(db.Integer, primary_key=True)
    access_time = db.Column(db.DateTime, default=datetime.utcnow)
    recognized_person = db.Column(db.String(100))
    person_type = db.Column(db.String(20))  # resident, visitor, security_officer, unknown
    confidence = db.Column(db.Float)
    access_result = db.Column(db.String(20))  # granted or denied
    embedding_id = db.Column(db.Integer)

# Helper functions
def get_officer(officer_id):
    return SecurityOfficer.query.filter_by(officer_id=officer_id).first()

def deactivate_officer(officer_id):
    officer = get_officer(officer_id)
    if officer:
        officer.active = False
        db.session.commit()
    return officer

def log_access(recognized_person, person_type, confidence, result, embedding_id):
    log = AccessLog(
        recognized_person=recognized_person,
        person_type=person_type,
        confidence=confidence,
        access_result=result,
        embedding_id=embedding_id
    )
    db.session.add(log)
    db.session.commit()
    return log

def get_embedding(user_type, reference_id):
    return FaceEmbedding.query.filter_by(user_type=user_type, reference_id=reference_id).first()
