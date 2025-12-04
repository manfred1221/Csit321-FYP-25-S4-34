import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import logging
from datetime import date

from config import Config
from database import create_database, init_pool, init_schema
from user import User
from access_log import AccessLog

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = Config.SECRET_KEY
CORS(app)

@app.before_request
def check_expired_workers():
    User.check_expired_temp_workers()

@app.route('/')
def camera_page():
    return render_template('camera.html')

@app.route('/api/recognize', methods=['POST'])
def api_recognize():
    data = request.json
    
    if not data or 'image' not in data:
        return jsonify({'success': False, 'message': 'No image provided'}), 400
    
    try:
        from model import extract_embedding_from_base64, recognize_face
        
        embedding, error = extract_embedding_from_base64(data['image'])
        
        if error:
            AccessLog.create(None, 'denied', None)
            return jsonify({
                'success': True,
                'recognized': False,
                'message': error
            })
        
        users = User.get_with_face()
        
        if not users:
            AccessLog.create(None, 'denied', None)
            return jsonify({
                'success': True,
                'recognized': False,
                'message': 'No registered users in system'
            })
        
        threshold = Config.FACE_RECOGNITION['threshold']
        user_id, username, full_name, distance = recognize_face(embedding, users, threshold)
        
        if user_id:
            user = User.get_by_id(user_id)
            
            if user.get('role') == 'TEMP_WORKER':
                if not User.is_temp_worker_valid(user):
                    AccessLog.create(user_id, 'denied', None)
                    return jsonify({
                        'success': True,
                        'recognized': False,
                        'message': 'Access period expired or not started'
                    })
            
            confidence = max(0, min(100, int((1 - distance / 2) * 100)))
            AccessLog.create(user_id, 'granted', confidence / 100)
            
            return jsonify({
                'success': True,
                'recognized': True,
                'user_id': user_id,
                'username': username,
                'full_name': full_name,
                'confidence': confidence,
                'message': f'Welcome, {full_name}!'
            })
        else:
            AccessLog.create(None, 'denied', None)
            return jsonify({
                'success': True,
                'recognized': False,
                'message': 'Face not recognized. Access denied.'
            })
    
    except Exception as e:
        logger.error(f"Recognition error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

def init_app():
    create_database()
    init_pool()
    init_schema()
    logger.info("Camera application initialized")

if __name__ == '__main__':
    init_app()
    print("\n" + "=" * 60)
    print("FACE RECOGNITION - CAMERA VERIFICATION")
    print("=" * 60)
    print(f"\nCamera Page: http://localhost:{Config.CAM_PORT}/")
    print("=" * 60 + "\n")
    app.run(host=Config.HOST, port=Config.CAM_PORT, debug=Config.DEBUG)
