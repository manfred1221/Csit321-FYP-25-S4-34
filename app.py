import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

from flask import Flask, request, jsonify, session, render_template, redirect, url_for, send_from_directory
from flask_cors import CORS
from functools import wraps
import logging
from werkzeug.utils import secure_filename
import uuid

from config import Config
from database import create_database, init_pool, init_schema
from user import User
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
        if not user or user['role'] != 'ADMIN':
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated

@app.before_request
def check_expired_workers():
    User.check_expired_temp_workers()

@app.route('/')
def index():
    return redirect(url_for('admin_login'))

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'GET':
        if 'user_id' in session:
            user = User.get_by_id(session['user_id'])
            if user and user['role'] == 'ADMIN':
                return redirect(url_for('admin_profile'))
        return render_template('admin_login.html')
    
    data = request.json
    user = User.authenticate(data.get('username'), data.get('password'))
    
    if user and user['role'] == 'ADMIN':
        session['user_id'] = user['id']
        session['username'] = user['username']
        session['role'] = user['role']
        session.permanent = True
        return jsonify({'success': True})
    
    return jsonify({'success': False, 'message': 'Invalid credentials or not admin'}), 401

@app.route('/admin/logout')
def admin_logout():
    session.clear()
    return redirect(url_for('admin_login'))

@app.route('/admin')
@admin_required
def admin_dashboard():
    return redirect(url_for('admin_profile'))

@app.route('/admin/profile')
@admin_required
def admin_profile():
    user = User.get_by_id(session['user_id'])
    return render_template('admin_profile.html', user=user)

@app.route('/admin/profile/upload', methods=['POST'])
@admin_required
def admin_upload_photo():
    user_id = session['user_id']
    
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
        encoding_path, error = register_face_from_photo(
            photo_path,
            user_id,
            Config.FACE_RECOGNITION['encoding_dir']
        )
        
        if error:
            os.remove(photo_path)
            return jsonify({'success': False, 'message': f'Face registration failed: {error}'}), 400
        
        User.update(user_id, {
            'photo_path': photo_path,
            'face_encoding_path': encoding_path
        })
        
        return jsonify({'success': True, 'message': 'Photo uploaded successfully!'})
    
    except Exception as e:
        logger.error(f"Upload error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/admin/users')
@admin_required
def admin_users():
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
    if request.method == 'GET':
        return render_template('admin_add_user.html')
    
    try:
        data = request.json
        
        if User.get_by_username(data.get('username')):
            return jsonify({'success': False, 'message': 'Username already exists'}), 400
        
        user_data = {
            'username': data.get('username'),
            'email': data.get('email'),
            'password': data.get('password'),
            'full_name': data.get('full_name'),
            'phone': data.get('phone'),
            'role': data.get('role', 'USER'),
            'access_level': data.get('access_level', 'standard')
        }
        
        if data.get('role') == 'TEMP_WORKER':
            user_data['work_start_date'] = data.get('work_start_date')
            user_data['work_end_date'] = data.get('work_end_date')
            user_data['work_schedule'] = data.get('work_schedule')
            user_data['work_details'] = data.get('work_details')
        
        user_id = User.create(user_data)
        
        return jsonify({'success': True, 'user_id': user_id})
    
    except Exception as e:
        logger.error(f"Add user error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/admin/users/<int:user_id>/edit', methods=['GET', 'POST'])
@admin_required
def admin_edit_user(user_id):
    user = User.get_by_id(user_id)
    if not user:
        return redirect(url_for('admin_users'))
    
    if request.method == 'GET':
        return render_template('admin_edit_user.html', user=user)
    
    try:
        data = request.json
        
        update_data = {
            'email': data.get('email'),
            'full_name': data.get('full_name'),
            'phone': data.get('phone'),
            'role': data.get('role'),
            'status': data.get('status'),
            'access_level': data.get('access_level')
        }
        
        if data.get('role') == 'TEMP_WORKER':
            update_data['work_start_date'] = data.get('work_start_date')
            update_data['work_end_date'] = data.get('work_end_date')
            update_data['work_schedule'] = data.get('work_schedule')
            update_data['work_details'] = data.get('work_details')
        
        if data.get('password'):
            update_data['password'] = data.get('password')
        
        User.update(user_id, update_data)
        return jsonify({'success': True})
    
    except Exception as e:
        logger.error(f"Edit user error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/admin/users/<int:user_id>/delete', methods=['POST'])
@admin_required
def admin_delete_user(user_id):
    try:
        User.delete(user_id)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/admin/users/bulk-delete', methods=['POST'])
@admin_required
def admin_bulk_delete():
    try:
        data = request.json
        user_ids = data.get('user_ids', [])
        
        if not user_ids:
            return jsonify({'success': False, 'message': 'No users selected'}), 400
        
        admin_id = session['user_id']
        if admin_id in user_ids:
            user_ids.remove(admin_id)
        
        count = User.bulk_delete(user_ids)
        return jsonify({'success': True, 'deleted_count': count})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/admin/users/<int:user_id>/deactivate', methods=['POST'])
@admin_required
def admin_deactivate_user(user_id):
    try:
        User.deactivate(user_id)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/admin/users/<int:user_id>/activate', methods=['POST'])
@admin_required
def admin_activate_user(user_id):
    try:
        User.activate(user_id)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/admin/users/<int:user_id>/upload-photo', methods=['POST'])
@admin_required
def admin_upload_user_photo(user_id):
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
        encoding_path, error = register_face_from_photo(
            photo_path,
            user_id,
            Config.FACE_RECOGNITION['encoding_dir']
        )
        
        if error:
            os.remove(photo_path)
            return jsonify({'success': False, 'message': f'Face registration failed: {error}'}), 400
        
        User.update(user_id, {
            'photo_path': photo_path,
            'face_encoding_path': encoding_path
        })
        
        return jsonify({'success': True, 'message': 'Photo uploaded successfully!'})
    
    except Exception as e:
        logger.error(f"Upload error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/admin/users/<int:user_id>/upload-id-doc', methods=['POST'])
@admin_required
def admin_upload_id_doc(user_id):
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
        
        User.update(user_id, {'id_document_path': doc_path})
        
        return jsonify({'success': True, 'message': 'ID document uploaded successfully!'})
    
    except Exception as e:
        logger.error(f"Upload ID doc error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/admin/logs')
@admin_required
def admin_logs():
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

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(Config.FACE_RECOGNITION['upload_dir'], filename)

@app.route('/id_documents/<filename>')
def id_document_file(filename):
    return send_from_directory(Config.FACE_RECOGNITION['id_doc_dir'], filename)

def init_app():
    create_database()
    init_pool()
    init_schema()
    
    os.makedirs(Config.FACE_RECOGNITION['upload_dir'], exist_ok=True)
    os.makedirs(Config.FACE_RECOGNITION['encoding_dir'], exist_ok=True)
    os.makedirs(Config.FACE_RECOGNITION['id_doc_dir'], exist_ok=True)
    
    if not User.get_by_username('admin'):
        User.create({
            'username': 'admin',
            'email': 'admin@system.local',
            'password': 'admin123',
            'full_name': 'System Administrator',
            'role': 'ADMIN'
        })
        logger.info("Default admin created: admin / admin123")
    
    logger.info("Application initialized")

if __name__ == '__main__':
    init_app()
    print("\n" + "=" * 60)
    print("FACE RECOGNITION - ADMIN PANEL")
    print("=" * 60)
    print(f"\nAdmin Panel: http://localhost:{Config.PORT}/admin/login")
    print(f"\nDEFAULT ADMIN: admin / admin123")
    print("=" * 60 + "\n")
    app.run(host=Config.HOST, port=Config.PORT, debug=Config.DEBUG)
