import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import logging

from config import Config
from database import get_db_connection
from user import User
from access_log import AccessLog

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = Config.SECRET_KEY
CORS(app)

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
            logger.warning(f"Face extraction failed: {error}")
            AccessLog.create(None, 'denied', None, 'unknown')
            return jsonify({
                'success': True,
                'recognized': False,
                'message': error
            })
        
        # Use the recognize_face function which queries database directly
        threshold = Config.FACE_RECOGNITION['threshold']
        user_id, username, full_name, distance = recognize_face(embedding, threshold)
        
        if user_id:
            # Calculate confidence percentage
            confidence = max(0, min(100, int((1 - distance / 2) * 100)))
            
            # Create access log
            AccessLog.create(
                recognized_person=full_name,
                access_result='granted',
                confidence=confidence / 100,
                person_type='resident'
            )
            
            logger.info(f"✓ Access granted: {full_name} (confidence: {confidence}%)")
            
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
            logger.warning(f"✗ Access denied: Face not recognized (distance: {distance:.4f})")
            AccessLog.create(
                recognized_person=None,
                access_result='denied',
                confidence=None,
                person_type='unknown'
            )
            return jsonify({
                'success': True,
                'recognized': False,
                'message': 'Face not recognized. Access denied.'
            })
    
    except Exception as e:
        logger.error(f"Recognition error: {e}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/stats')
def api_stats():
    """Get access statistics"""
    try:
        stats = AccessLog.get_stats(days=30)
        return jsonify({'success': True, 'stats': stats})
    except Exception as e:
        logger.error(f"Stats error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/recent-logs')
def api_recent_logs():
    """Get recent access logs"""
    try:
        limit = request.args.get('limit', 10, type=int)
        logs = AccessLog.get_recent(limit=limit)
        return jsonify({'success': True, 'logs': logs})
    except Exception as e:
        logger.error(f"Recent logs error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/today-logs')
def api_today_logs():
    """Get today's access logs"""
    try:
        logs = AccessLog.get_today()
        return jsonify({'success': True, 'logs': logs})
    except Exception as e:
        logger.error(f"Today logs error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

def init_app():
    """Initialize camera application"""
    # Test database connection
    try:
        conn = get_db_connection()
        conn.close()
        logger.info("✓ Database connection successful")
    except Exception as e:
        logger.error(f"✗ Database connection failed: {e}")
        raise e
    
    logger.info("✓ Camera application initialized")

if __name__ == '__main__':
    init_app()
    print("\n" + "=" * 60)
    print("FACE RECOGNITION - CAMERA VERIFICATION")
    print("=" * 60)
    print(f"\nCamera Page: http://localhost:{Config.CAM_PORT}/")
    print("=" * 60 + "\n")
    app.run(host=Config.HOST, port=Config.CAM_PORT, debug=Config.DEBUG)