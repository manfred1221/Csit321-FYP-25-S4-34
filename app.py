import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

from flask import Flask, request, jsonify, session, render_template, redirect, url_for, send_from_directory
from flask_cors import CORS
from functools import wraps
import logging
from werkzeug.utils import secure_filename
import uuid

from config import Config
from db import get_db_connection
from user import User, Resident
from access_log import AccessLog

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = Config.SECRET_KEY
app.config['PERMANENT_SESSION_LIFETIME'] = Config.SESSION_LIFETIME
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
CORS(app)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('admin_login'))
        user = User.get_by_id(session['user_id'])
        if not user or user['role'] != 'Admin':
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated

def check_user_has_face_embedding(user):
    """Check if user has a registered face embedding"""
    if not user:
        return None
    
    resident_id = user.get('resident_id')
    if not resident_id:
        return None
    
    try:
        from psycopg2.extras import RealDictCursor
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("""
            SELECT embedding_id FROM face_embeddings 
            WHERE reference_id = %s AND user_type = 'resident'
            LIMIT 1
        """, (resident_id,))
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        return result['embedding_id'] if result else None
    except Exception as e:
        logger.error(f"Error checking face embedding: {e}")
        return None


# ============================================
# AUTHENTICATION ROUTES
# ============================================

@app.route('/')
def index():
    return redirect(url_for('admin_login'))

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """Admin login - User Story: Login to manage users"""
    if request.method == 'GET':
        if 'user_id' in session:
            user = User.get_by_id(session['user_id'])
            if user and user['role'] == 'Admin':
                return redirect(url_for('admin_profile'))
        return render_template('admin_login.html')
    
    data = request.json
    user = User.authenticate(data.get('username'), data.get('password'))
    
    if user and user['role'] == 'Admin':
        session['user_id'] = user['id']
        session['username'] = user['username']
        session['role'] = user['role']
        session.permanent = True
        
        # Check for expired temp workers on admin login
        expired_count = User.check_expired_temp_workers()
        if expired_count > 0:
            logger.info(f"Deactivated {expired_count} expired temporary workers")
        
        return jsonify({'success': True})
    
    return jsonify({'success': False, 'message': 'Invalid credentials or not admin'}), 401

@app.route('/admin/logout')
def admin_logout():
    """Admin logout - User Story: Logout so no one can use account"""
    session.clear()
    return redirect(url_for('admin_login'))


# ============================================
# PROFILE ROUTES
# ============================================

@app.route('/admin')
@admin_required
def admin_dashboard():
    return redirect(url_for('admin_profile'))

@app.route('/admin/profile')
@admin_required
def admin_profile():
    user = User.get_by_id(session['user_id'])
    user['face_encoding_path'] = check_user_has_face_embedding(user)
    return render_template('admin_profile.html', user=user)

@app.route('/admin/profile/upload', methods=['POST'])
@admin_required
def admin_profile_upload():
    """Upload face photo for the current admin user"""
    user = User.get_by_id(session['user_id'])
    if not user:
        return jsonify({'success': False, 'message': 'User not found'}), 404
    
    if 'photo' not in request.files:
        return jsonify({'success': False, 'message': 'No photo provided'}), 400
    
    photo = request.files['photo']
    
    if not photo or not allowed_file(photo.filename):
        return jsonify({'success': False, 'message': 'Invalid file type. Please use JPG or PNG.'}), 400
    
    try:
        filename = f"user_{user['id']}_{uuid.uuid4().hex}.jpg"
        photo_path = os.path.join(Config.FACE_RECOGNITION['upload_dir'], filename)
        photo.save(photo_path)
        
        from model import register_face_from_photo
        from psycopg2.extras import RealDictCursor
        
        resident_id = user.get('resident_id')
        
        # Auto-create resident record if not exists
        if not resident_id:
            conn = get_db_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            try:
                # First check if resident already exists for this user
                cursor.execute("SELECT resident_id FROM residents WHERE user_id = %s", (user['id'],))
                existing = cursor.fetchone()
                
                if existing:
                    resident_id = existing['resident_id']
                    logger.info(f"Found existing resident record: resident_id={resident_id}")
                else:
                    # Create new resident record
                    cursor.execute("""
                        INSERT INTO residents (full_name, unit_number, contact_number, user_id)
                        VALUES (%s, %s, %s, %s)
                        RETURNING resident_id
                    """, (
                        user.get('full_name') or user.get('username') or 'Admin',
                        'ADMIN',
                        user.get('phone') or '',
                        user['id']
                    ))
                    result = cursor.fetchone()
                    resident_id = result['resident_id']
                    conn.commit()
                    logger.info(f"Created resident record for user: resident_id={resident_id}")
            except Exception as e:
                conn.rollback()
                os.remove(photo_path)
                logger.error(f"Database error: {str(e)}")
                return jsonify({'success': False, 'message': f'Failed to create resident record: {str(e)}'}), 400
            finally:
                cursor.close()
                conn.close()
        
        embedding_id, error = register_face_from_photo(photo_path, resident_id, 'resident')
        
        if error:
            os.remove(photo_path)
            return jsonify({'success': False, 'message': f'Face registration failed: {error}'}), 400
        
        logger.info(f"Face photo uploaded for user {user['id']}, embedding_id: {embedding_id}")
        return jsonify({'success': True, 'message': 'Photo uploaded and face registered successfully!', 'embedding_id': embedding_id})
    
    except Exception as e:
        logger.error(f"Profile photo upload error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500




@app.route('/admin/users')
@admin_required
def admin_users():
    """View all users - User Story: View user accounts to manage information"""
    role_filter = request.args.get('role', '')
    status_filter = request.args.get('status', '')
    search_query = request.args.get('search', '')
    
    if search_query:
        users = User.search(
            search_query, 
            role=role_filter if role_filter else None,
            status=status_filter if status_filter else None
        )
    else:
        users = User.get_all(
            role=role_filter if role_filter else None,
            status=status_filter if status_filter else None
        )
    
    return render_template('admin_users.html', 
                         users=users, 
                         role_filter=role_filter,
                         status_filter=status_filter,
                         search_query=search_query)

@app.route('/admin/users/add', methods=['GET', 'POST'])
@admin_required
def admin_add_user():
    """Add new user - User Story: Create user accounts"""
    if request.method == 'GET':
        return render_template('admin_add_user.html')
    
    try:
        data = request.json
        
        # Validate required fields
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400
        
        if not data.get('username'):
            return jsonify({'success': False, 'message': 'Username is required'}), 400
        
        if not data.get('email'):
            return jsonify({'success': False, 'message': 'Email is required'}), 400
        
        if not data.get('password'):
            return jsonify({'success': False, 'message': 'Password is required'}), 400
        
        # Check if username already exists
        existing_user = User.get_by_username(data.get('username'))
        if existing_user:
            return jsonify({'success': False, 'message': 'Username already exists'}), 400
        
        user_data = {
            'username': data.get('username'),
            'email': data.get('email'),
            'password': data.get('password'),
            'full_name': data.get('full_name', data.get('username')),
            'phone': data.get('phone', ''),
            'role': data.get('role', 'Resident'),
            'unit_number': data.get('unit_number', 'N/A'),
            'access_level': data.get('access_level', 'standard'),
            'status': 'active'
        }
        
        # Add temp worker fields if applicable
        if data.get('role') == 'TEMP_WORKER':
            user_data['work_start_date'] = data.get('work_start_date')
            user_data['work_end_date'] = data.get('work_end_date')
            user_data['work_schedule'] = data.get('work_schedule', '')
            user_data['work_details'] = data.get('work_details', '')
        
        user_id = User.create(user_data)
        
        if not user_id or user_id == 0:
            return jsonify({'success': False, 'message': 'Failed to create user - invalid user_id'}), 500
        
        logger.info(f"Successfully created user with ID: {user_id}")
        return jsonify({'success': True, 'user_id': user_id})
    
    except ValueError as ve:
        logger.error(f"Validation error: {str(ve)}")
        return jsonify({'success': False, 'message': str(ve)}), 400
    except Exception as e:
        logger.error(f"Add user error: {type(e).__name__}: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({'success': False, 'message': f'{type(e).__name__}: {str(e)}'}), 500
    
@app.route('/admin/users/<int:user_id>/edit', methods=['GET', 'POST'])
@admin_required
def admin_edit_user(user_id):
    """Edit user - User Story: Update user information and access permissions"""
    user = User.get_by_id(user_id)
    if not user:
        return redirect(url_for('admin_users'))
    
    if request.method == 'GET':
        user['face_encoding_path'] = check_user_has_face_embedding(user)
        return render_template('admin_edit_user.html', user=user)
    
    try:
        data = request.json
        
        update_data = {
            'email': data.get('email'),
            'full_name': data.get('full_name'),
            'phone': data.get('phone'),
            'role': data.get('role'),
            'unit_number': data.get('unit_number'),
            'access_level': data.get('access_level'),
            'status': data.get('status')
        }
        
        if data.get('password'):
            update_data['password'] = data.get('password')
        
        # Add temp worker fields if applicable
        if data.get('role') == 'TEMP_WORKER':
            update_data['work_start_date'] = data.get('work_start_date')
            update_data['work_end_date'] = data.get('work_end_date')
            update_data['work_schedule'] = data.get('work_schedule')
            update_data['work_details'] = data.get('work_details')
        
        User.update(user_id, update_data)
        return jsonify({'success': True})
    
    except Exception as e:
        logger.error(f"Edit user error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/admin/users/<int:user_id>/delete', methods=['POST'])
@admin_required
def admin_delete_user(user_id):
    """Delete user - User Story: Delete user accounts to remove access"""
    try:
        # Prevent deleting yourself
        if user_id == session['user_id']:
            return jsonify({'success': False, 'message': 'Cannot delete your own account'}), 400
        
        User.delete(user_id)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/admin/users/bulk-delete', methods=['POST'])
@admin_required
def admin_bulk_delete():
    """Bulk delete - User Story: Delete multiple accounts in one action"""
    try:
        data = request.json
        user_ids = data.get('user_ids', [])
        
        if not user_ids:
            return jsonify({'success': False, 'message': 'No users selected'}), 400
        
        # Remove admin's own ID if present
        admin_id = session['user_id']
        if admin_id in user_ids:
            user_ids.remove(admin_id)
        
        if not user_ids:
            return jsonify({'success': False, 'message': 'Cannot delete your own account'}), 400
        
        count = User.bulk_delete(user_ids)
        return jsonify({'success': True, 'deleted_count': count})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/admin/users/<int:user_id>/deactivate', methods=['POST'])
@admin_required
def admin_deactivate_user(user_id):
    """Deactivate user - User Story: Temporarily suspend access without deleting data"""
    try:
        if user_id == session['user_id']:
            return jsonify({'success': False, 'message': 'Cannot deactivate your own account'}), 400
        
        success = User.deactivate(user_id)
        if success:
            return jsonify({'success': True, 'message': 'User deactivated successfully'})
        return jsonify({'success': False, 'message': 'User not found'}), 404
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/admin/users/<int:user_id>/activate', methods=['POST'])
@admin_required
def admin_activate_user(user_id):
    """Activate user - Reactivate a previously deactivated user"""
    try:
        success = User.activate(user_id)
        if success:
            return jsonify({'success': True, 'message': 'User activated successfully'})
        return jsonify({'success': False, 'message': 'User not found'}), 404
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


# ============================================
# PHOTO & DOCUMENT UPLOAD ROUTES
# ============================================

@app.route('/admin/users/<int:user_id>/upload-photo', methods=['POST'])
@admin_required
def admin_upload_user_photo(user_id):
    """Upload user face photo for recognition"""
    user = User.get_by_id(user_id)
    if not user:
        return jsonify({'success': False, 'message': 'User not found'}), 404
    
    if 'photo' not in request.files:
        return jsonify({'success': False, 'message': 'No photo provided'}), 400
    
    photo = request.files['photo']
    
    if not photo or not allowed_file(photo.filename):
        return jsonify({'success': False, 'message': 'Invalid file type'}), 400
    
    try:
        filename = f"user_{user_id}_{uuid.uuid4().hex}.jpg"
        photo_path = os.path.join(Config.FACE_RECOGNITION['upload_dir'], filename)
        photo.save(photo_path)
        
        from model import register_face_from_photo
        from psycopg2.extras import RealDictCursor
        
        resident_id = user.get('resident_id')
        
        # Auto-create resident record if not exists
        if not resident_id:
            conn = get_db_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            try:
                # First check if resident already exists for this user
                cursor.execute("SELECT resident_id FROM residents WHERE user_id = %s", (user_id,))
                existing = cursor.fetchone()
                
                if existing:
                    resident_id = existing['resident_id']
                    logger.info(f"Found existing resident record: resident_id={resident_id}")
                else:
                    # Create new resident record
                    cursor.execute("""
                        INSERT INTO residents (full_name, unit_number, contact_number, user_id)
                        VALUES (%s, %s, %s, %s)
                        RETURNING resident_id
                    """, (
                        user.get('full_name') or user.get('username') or f'User {user_id}',
                        user.get('unit_number') or 'N/A',
                        user.get('phone') or '',
                        user_id
                    ))
                    result = cursor.fetchone()
                    resident_id = result['resident_id']
                    conn.commit()
                    logger.info(f"Created resident record for user {user_id}: resident_id={resident_id}")
            except Exception as e:
                conn.rollback()
                os.remove(photo_path)
                logger.error(f"Database error: {str(e)}")
                return jsonify({'success': False, 'message': f'Failed to create resident record: {str(e)}'}), 400
            finally:
                cursor.close()
                conn.close()
        
        embedding_id, error = register_face_from_photo(photo_path, resident_id, 'resident')
        
        if error:
            os.remove(photo_path)
            return jsonify({'success': False, 'message': f'Face registration failed: {error}'}), 400
        
        return jsonify({'success': True, 'message': 'Photo uploaded successfully!', 'embedding_id': embedding_id})
    
    except Exception as e:
        logger.error(f"Upload error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/admin/users/<int:user_id>/upload-id-doc', methods=['POST'])
@admin_required
def admin_upload_id_doc(user_id):
    """Upload ID document - User Story: Register temp workers with ID documents"""
    if 'document' not in request.files:
        return jsonify({'success': False, 'message': 'No document provided'}), 400
    
    doc = request.files['document']
    
    if not doc or not allowed_file(doc.filename):
        return jsonify({'success': False, 'message': 'Invalid file type'}), 400
    
    try:
        ext = doc.filename.rsplit('.', 1)[1].lower()
        filename = f"id_doc_{user_id}_{uuid.uuid4().hex}.{ext}"
        doc_path = os.path.join(Config.FACE_RECOGNITION['id_doc_dir'], filename)
        doc.save(doc_path)
        
        # Update user record with document path
        User.update(user_id, {'id_document_path': filename})
        
        return jsonify({'success': True, 'message': 'ID document uploaded successfully!'})
    
    except Exception as e:
        logger.error(f"Upload ID doc error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


# ============================================
# ACCESS LOGS ROUTES
# ============================================

@app.route('/admin/logs')
@admin_required
def admin_logs():
    """View access logs - User Story: View entry and exit history"""
    user_filter = request.args.get('user_id', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    status_filter = request.args.get('status', '')
    
    logs = AccessLog.filter_logs(
        user_id=int(user_filter) if user_filter else None,
        date_from=date_from if date_from else None,
        date_to=date_to if date_to else None,
        status=status_filter if status_filter else None
    )
    
    users_for_filter = AccessLog.get_all_users_for_filter()
    
    return render_template('admin_logs.html', 
                         logs=logs,
                         users_for_filter=users_for_filter,
                         user_filter=user_filter,
                         date_from=date_from,
                         date_to=date_to,
                         status_filter=status_filter)


# ============================================
# TEMP WORKER MANAGEMENT
# ============================================

@app.route('/admin/temp-workers')
@app.route('/admin/temp-workers')
@admin_required
def admin_temp_workers():
    """View temporary workers with their schedules"""
    users = User.get_all(role='TEMP_WORKER')
    expiring_soon = User.get_expiring_temp_workers(days=7)
    from datetime import date
    today = date.today()
    
    return render_template('admin_tempworker.html', 
                         users=users, 
                         expiring_soon=expiring_soon,
                         today=today) 
@app.route('/admin/temp-workers/check-expired', methods=['POST'])
@admin_required
def admin_check_expired_temp_workers():
    """Manually check and deactivate expired temp workers"""
    try:
        count = User.check_expired_temp_workers()
        return jsonify({
            'success': True, 
            'message': f'Deactivated {count} expired temporary workers',
            'count': count
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


# ============================================
# RESIDENTS ROUTES
# ============================================

@app.route('/admin/residents')
@admin_required
def admin_residents():
    residents = Resident.get_all()
    return render_template('admin_residents.html', residents=residents)


# ============================================
# STATIC FILE ROUTES
# ============================================

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(Config.FACE_RECOGNITION['upload_dir'], filename)

@app.route('/id_documents/<filename>')
@admin_required
def id_document_file(filename):
    return send_from_directory(Config.FACE_RECOGNITION['id_doc_dir'], filename)


# ============================================
# API ROUTES FOR DASHBOARD
# ============================================

@app.route('/api/dashboard/stats')
@admin_required
def api_dashboard_stats():
    """Get dashboard statistics"""
    try:
        stats = AccessLog.get_stats(days=30)
        
        # Get user counts
        all_users = User.get_all()
        active_users = len([u for u in all_users if u.get('status') == 'active'])
        inactive_users = len([u for u in all_users if u.get('status') == 'inactive'])
        temp_workers = len([u for u in all_users if u.get('role') == 'TEMP_WORKER'])
        
        stats['total_users'] = len(all_users)
        stats['active_users'] = active_users
        stats['inactive_users'] = inactive_users
        stats['temp_workers'] = temp_workers
        
        return jsonify({'success': True, 'stats': stats})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


# ============================================
# INITIALIZATION
# ============================================

def init_app():
    os.makedirs(Config.FACE_RECOGNITION['upload_dir'], exist_ok=True)
    os.makedirs(Config.FACE_RECOGNITION['encoding_dir'], exist_ok=True)
    os.makedirs(Config.FACE_RECOGNITION['id_doc_dir'], exist_ok=True)
    
    try:
        conn = get_db_connection()
        conn.close()
        logger.info("Database connection successful")
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise e
    
    # Check for expired temp workers on startup
    try:
        expired_count = User.check_expired_temp_workers()
        if expired_count > 0:
            logger.info(f"Deactivated {expired_count} expired temporary workers on startup")
    except Exception as e:
        logger.warning(f"Could not check expired temp workers: {e}")
    
    logger.info("Application initialized")

if __name__ == '__main__':
    init_app()
    print("\n" + "=" * 60)
    print("FACE RECOGNITION - ADMIN PANEL")
    print("=" * 60)
    print(f"\nAdmin Panel: http://localhost:{Config.PORT}/admin/login")
    print(f"\nDefault admin: admin_user / password: admin123")
    print("=" * 60 + "\n")
    app.run(host=Config.HOST, port=Config.PORT, debug=False)