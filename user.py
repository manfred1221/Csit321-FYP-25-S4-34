import bcrypt
from psycopg2.extras import RealDictCursor
from database import get_conn, return_conn
from datetime import date

class User:
    @staticmethod
    def hash_password(password):
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    @staticmethod
    def verify_password(password, password_hash):
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
    
    @staticmethod
    def create(data):
        conn = get_conn()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO users (username, email, password_hash, full_name, phone, role, 
                    access_level, id_document_path, work_start_date, work_end_date, 
                    work_schedule, work_details)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                data['username'],
                data['email'],
                User.hash_password(data['password']),
                data['full_name'],
                data.get('phone'),
                data.get('role', 'USER'),
                data.get('access_level', 'standard'),
                data.get('id_document_path'),
                data.get('work_start_date'),
                data.get('work_end_date'),
                data.get('work_schedule'),
                data.get('work_details')
            ))
            user_id = cursor.fetchone()[0]
            conn.commit()
            return user_id
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()
            return_conn(conn)
    
    @staticmethod
    def authenticate(username, password):
        conn = get_conn()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            cursor.execute("SELECT * FROM users WHERE username = %s AND status = 'active'", (username,))
            user = cursor.fetchone()
            if user and User.verify_password(password, user['password_hash']):
                return dict(user)
            return None
        finally:
            cursor.close()
            return_conn(conn)
    
    @staticmethod
    def get_by_id(user_id):
        conn = get_conn()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
            user = cursor.fetchone()
            return dict(user) if user else None
        finally:
            cursor.close()
            return_conn(conn)
    
    @staticmethod
    def get_by_username(username):
        conn = get_conn()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
            user = cursor.fetchone()
            return dict(user) if user else None
        finally:
            cursor.close()
            return_conn(conn)
    
    @staticmethod
    def get_all(role=None, status=None):
        conn = get_conn()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            query = "SELECT * FROM users WHERE 1=1"
            params = []
            if role:
                query += " AND role = %s"
                params.append(role)
            if status:
                query += " AND status = %s"
                params.append(status)
            query += " ORDER BY created_at DESC"
            cursor.execute(query, params)
            return [dict(u) for u in cursor.fetchall()]
        finally:
            cursor.close()
            return_conn(conn)
    
    @staticmethod
    def search(keyword, role=None, status=None):
        conn = get_conn()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            query = """
                SELECT * FROM users 
                WHERE (
                    LOWER(username) LIKE LOWER(%s) OR 
                    LOWER(full_name) LIKE LOWER(%s) OR 
                    LOWER(email) LIKE LOWER(%s) OR
                    LOWER(phone) LIKE LOWER(%s)
                )
            """
            search_term = f"%{keyword}%"
            params = [search_term, search_term, search_term, search_term]
            
            if role:
                query += " AND role = %s"
                params.append(role)
            if status:
                query += " AND status = %s"
                params.append(status)
            
            query += " ORDER BY created_at DESC"
            cursor.execute(query, params)
            return [dict(u) for u in cursor.fetchall()]
        finally:
            cursor.close()
            return_conn(conn)
    
    @staticmethod
    def get_with_face():
        conn = get_conn()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            cursor.execute("""
                SELECT id, username, full_name, face_encoding_path, role, work_end_date
                FROM users 
                WHERE status = 'active' AND face_encoding_path IS NOT NULL
            """)
            return [dict(u) for u in cursor.fetchall()]
        finally:
            cursor.close()
            return_conn(conn)
    
    @staticmethod
    def update(user_id, data):
        conn = get_conn()
        cursor = conn.cursor()
        try:
            fields = []
            params = []
            allowed_fields = ['email', 'full_name', 'phone', 'role', 'status', 
                            'access_level', 'photo_path', 'face_encoding_path',
                            'id_document_path', 'work_start_date', 'work_end_date',
                            'work_schedule', 'work_details']
            
            for key in allowed_fields:
                if key in data:
                    fields.append(f"{key} = %s")
                    params.append(data[key])
            
            if 'password' in data and data['password']:
                fields.append("password_hash = %s")
                params.append(User.hash_password(data['password']))
            
            if not fields:
                return False
            
            params.append(user_id)
            cursor.execute(f"UPDATE users SET {', '.join(fields)} WHERE id = %s", params)
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()
            return_conn(conn)
    
    @staticmethod
    def delete(user_id):
        conn = get_conn()
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            cursor.close()
            return_conn(conn)
    
    @staticmethod
    def bulk_delete(user_ids):
        if not user_ids:
            return 0
        conn = get_conn()
        cursor = conn.cursor()
        try:
            placeholders = ','.join(['%s'] * len(user_ids))
            cursor.execute(f"DELETE FROM users WHERE id IN ({placeholders})", user_ids)
            conn.commit()
            return cursor.rowcount
        finally:
            cursor.close()
            return_conn(conn)
    
    @staticmethod
    def deactivate(user_id):
        return User.update(user_id, {'status': 'inactive'})
    
    @staticmethod
    def activate(user_id):
        return User.update(user_id, {'status': 'active'})
    
    @staticmethod
    def check_expired_temp_workers():
        conn = get_conn()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'users' AND column_name = 'work_end_date'
            """)
            if not cursor.fetchone():
                return 0
            
            cursor.execute("""
                UPDATE users 
                SET status = 'inactive' 
                WHERE role = 'TEMP_WORKER' 
                AND work_end_date < CURRENT_DATE 
                AND status = 'active'
            """)
            count = cursor.rowcount
            conn.commit()
            return count
        except:
            conn.rollback()
            return 0
        finally:
            cursor.close()
            return_conn(conn)
    
    @staticmethod
    def is_temp_worker_valid(user):
        if user.get('role') != 'TEMP_WORKER':
            return True
        
        today = date.today()
        start_date = user.get('work_start_date')
        end_date = user.get('work_end_date')
        
        if start_date and today < start_date:
            return False
        if end_date and today > end_date:
            return False
        return True
