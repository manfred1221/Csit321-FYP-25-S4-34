from flask_sqlalchemy import SQLAlchemy
from pgvector.sqlalchemy import Vector
from datetime import datetime
from sqlalchemy.dialects.postgresql import VARCHAR

db = SQLAlchemy()

class SecurityOfficer(db.Model):
    __tablename__ = "security_officers"
    officer_id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    contact_number = db.Column(db.String(20))
    shift = db.Column(db.String(50))
    active = db.Column(db.Boolean, default=True)
    registered_at = db.Column(db.DateTime, default=datetime.utcnow)

class Resident(db.Model):
    __tablename__ = "residents"

    resident_id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    unit_number = db.Column(db.String(10), nullable=False)
    contact_number = db.Column(db.String(20))
    
    # Foreign key to User table if residents have login accounts
    user_id = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=True)

    registered_at = db.Column(db.DateTime, default=datetime.utcnow)

class Visitor(db.Model):
    __tablename__ = "visitors"

    visitor_id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    contact_number = db.Column(db.String(20))
    visiting_unit = db.Column(db.String(20))
    check_in = db.Column(db.DateTime)
    check_out = db.Column(db.DateTime)

    def __repr__(self):
        return f"<Visitor {self.visitor_id} - {self.full_name}>"


class FaceEmbedding(db.Model):
    __tablename__ = "face_embeddings"
    embedding_id = db.Column(db.Integer, primary_key=True)
    user_type = db.Column(db.String(20))  # resident, visitor, security_officer
    reference_id = db.Column(db.Integer, nullable=False)
    embedding = db.Column(Vector(512))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    image_filename = db.Column(VARCHAR(255))  # <-- Add this

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
    """
    Log access event with proper user type categorization

    Args:
        recognized_person: Name of the person
        person_type: User type from face_embeddings (resident, visitor, security_officer, internal_staff, temp_staff, ADMIN)
        confidence: Recognition confidence score
        result: 'granted' or 'denied'
        embedding_id: Reference to face embedding
    """
    print("🔥 LOG_ACCESS CALLED:", recognized_person, person_type, confidence, result)

    # Normalize person_type to match database constraints
    valid_types = ['resident', 'visitor', 'security_officer', 'internal_staff', 'temp_staff', 'ADMIN', 'unknown']

    if person_type not in valid_types:
        # Handle edge cases - map similar types
        type_mapping = {
            'RESIDENT': 'resident',
            'VISITOR': 'visitor',
            'SECURITY_OFFICER': 'security_officer',
            'INTERNAL_STAFF': 'internal_staff',
            'Internal_Staff': 'internal_staff',
            'TEMP_STAFF': 'temp_staff',
            'Temp_Staff': 'temp_staff',
            'TEMP_WORKER': 'temp_staff',
            'temp_worker': 'temp_staff',
            'admin': 'ADMIN'
        }
        person_type = type_mapping.get(person_type, 'unknown')

    # 🔒 HARD CLAMP (keep this forever)
    confidence = float(confidence)
    confidence = max(0.0, min(confidence, 1.0))

    log = AccessLog(
        recognized_person=recognized_person,
        person_type=person_type,
        confidence=confidence,
        access_result=result,
        embedding_id=embedding_id
    )
    try:
        db.session.add(log)
        db.session.commit()
        print("✅ ACCESS LOG COMMITTED:", log.log_id)
    except Exception as e:
        db.session.rollback()
        print("❌ ACCESS LOG FAILED:", str(e))
        raise e

def get_embedding(user_type, reference_id):
    return FaceEmbedding.query.filter_by(user_type=user_type, reference_id=reference_id).first()


class Role(db.Model):
    __tablename__ = 'roles'
    role_id = db.Column(db.Integer, primary_key=True)
    role_name = db.Column(db.String(50), unique=True, nullable=False)

    users = db.relationship("User", back_populates="role")


class User(db.Model):
    __tablename__ = 'users'
    user_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.Text, nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.role_id'), nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    role = db.relationship("Role", back_populates="users")
