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
        
        # Get users with face embeddings
        users = User.get_with_face()

        matched_user = None
        user_type = None

        if not users:
            # Try direct recognition from database
            threshold = Config.FACE_RECOGNITION['threshold']
            user_id, username, full_name, distance = recognize_face(embedding, threshold)

            # If recognized, query for user_type from face_embeddings
            if user_id:
                conn = get_db_connection()
                cursor = conn.cursor()
                try:
                    # Try to find the face embedding and get user_type
                    cursor.execute("""
                        SELECT user_type, reference_id
                        FROM face_embeddings
                        WHERE (user_type = 'resident' AND reference_id = %s)
                           OR (user_type IN ('ADMIN', 'internal_staff', 'temp_staff', 'security_officer') AND reference_id = %s)
                        LIMIT 1
                    """, (user_id, user_id))
                    result = cursor.fetchone()
                    if result:
                        user_type = result[0]
                finally:
                    cursor.close()
                    conn.close()
        else:
            threshold = Config.FACE_RECOGNITION['threshold']
            user_id, username, full_name, distance = recognize_face_with_users(embedding, users, threshold)

            # Find the matched user to get their user_type
            if user_id:
                for user in users:
                    if user.get('id') == user_id:
                        matched_user = user
                        user_type = matched_user.get('user_type')
                        break

        if user_id:
            # Calculate confidence percentage
            confidence = max(0, min(100, int((1 - distance / 2) * 100)))

            # Determine person_type from user_type
            person_type = 'resident'  # default
            if user_type:
                # Map user_type to person_type for access logs (match database constraint)
                if user_type == 'ADMIN':
                    person_type = 'ADMIN'
                elif user_type == 'internal_staff':
                    person_type = 'internal_staff'
                elif user_type == 'temp_staff':
                    person_type = 'internal_staff'  # Map temp_staff to internal_staff for logs
                elif user_type == 'security_officer':
                    person_type = 'security_officer'
                elif user_type == 'visitor':
                    person_type = 'visitor'
                else:
                    person_type = 'resident'

            # Create access log
            AccessLog.create(
                recognized_person=full_name,
                access_result='granted',
                confidence=confidence / 100,
                person_type=person_type
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