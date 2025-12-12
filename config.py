import os
from datetime import timedelta

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'face-recognition-secret-key-2024')
    SESSION_LIFETIME = timedelta(hours=24)
    
    HOST = '0.0.0.0'
    PORT = 5001
    CAM_PORT = 5002
    DEBUG = False
    
    # Database config - matches db.py
    DATABASE_CONFIG = {
        'dbname': os.environ.get('DB_NAME', 'csit321_face_recognition'),
        'user': os.environ.get('DB_USER', 'postgres'),
        'password': os.environ.get('DB_PASSWORD', 'joshua1102'),
        'host': os.environ.get('DB_HOST', 'localhost'),
        'port': os.environ.get('DB_PORT', '5432')
    }
    
    FACE_RECOGNITION = {
        'threshold': 1.1,
        'upload_dir': os.path.join(os.path.dirname(__file__), 'uploads'),
        'encoding_dir': os.path.join(os.path.dirname(__file__), 'face_encodings'),
        'id_doc_dir': os.path.join(os.path.dirname(__file__), 'id_documents')
    }
    
    # Role IDs from database
    ROLES = {
        'ADMIN': 1,
        'RESIDENT': 2,
        'VISITOR': 3,
        'SECURITY': 4
    }