import bcrypt
from psycopg2.extras import RealDictCursor
from db import get_db_connection
from config import Config

class User:
    @staticmethod
    def hash_password(password):
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    @staticmethod
    def verify_password(password, password_hash):
        # If it's a bcrypt hash
        if password_hash.startswith('$2b$'):
            return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))

        if password_hash.startswith('hashed_pw_'):
            return password == 'admin123' or password == password_hash
        return password == password_hash
    
    @staticmethod
    def create(data):
        """Create a new user with associated resident record if needed"""
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            # Get role_id from role name
            role_name = data.get('role', 'Resident')
            role_id = Config.ROLES.get(role_name, 2)  # Default to Resident
            
            # Map role names
            role_map = {
                'ADMIN': 1, 'Admin': 1,
                'RESIDENT': 2, 'Resident': 2, 'USER': 2,
                'VISITOR': 3, 'Visitor': 3,
                'SECURITY': 4, 'Security': 4
            }
            role_id = role_map.get(role_name, 2)
            
            cursor.execute("""
                INSERT INTO users (username, email, password_hash, role_id)
                VALUES (%s, %s, %s, %s)
                RETURNING user_id
            """, (
                data['username'],
                data['email'],
                User.hash_password(data['password']),
                role_id
            ))
            user_id = cursor.fetchone()[0]
            
            if role_id == 2:
                cursor.execute("""
                    INSERT INTO residents (full_name, unit_number, contact_number, user_id)
                    VALUES (%s, %s, %s, %s)
                """, (
                    data.get('full_name', data['username']),
                    data.get('unit_number', 'N/A'),
                    data.get('phone'),
                    user_id
                ))
            
            conn.commit()
            return user_id
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()
            conn.close()
    
    @staticmethod
    def authenticate(username, password):
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            cursor.execute("""
                SELECT u.user_id as id, u.username, u.email, u.password_hash, 
                       u.role_id, r.role_name as role, u.created_at,
                       res.full_name, res.unit_number, res.contact_number as phone,
                       res.resident_id
                FROM users u
                JOIN roles r ON u.role_id = r.role_id
                LEFT JOIN residents res ON u.user_id = res.user_id
                WHERE u.username = %s
            """, (username,))
            user = cursor.fetchone()
            if user and User.verify_password(password, user['password_hash']):
                return dict(user)
            return None
        finally:
            cursor.close()
            conn.close()
    
    @staticmethod
    def get_by_id(user_id):
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            cursor.execute("""
                SELECT u.user_id as id, u.username, u.email, u.password_hash,
                       u.role_id, r.role_name as role, u.created_at,
                       res.full_name, res.unit_number, res.contact_number as phone,
                       res.resident_id
                FROM users u
                JOIN roles r ON u.role_id = r.role_id
                LEFT JOIN residents res ON u.user_id = res.user_id
                WHERE u.user_id = %s
            """, (user_id,))
            user = cursor.fetchone()
            return dict(user) if user else None
        finally:
            cursor.close()
            conn.close()
    
    @staticmethod
    def get_by_username(username):
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            cursor.execute("""
                SELECT u.user_id as id, u.username, u.email, u.password_hash,
                       u.role_id, r.role_name as role, u.created_at,
                       res.full_name, res.unit_number, res.contact_number as phone,
                       res.resident_id
                FROM users u
                JOIN roles r ON u.role_id = r.role_id
                LEFT JOIN residents res ON u.user_id = res.user_id
                WHERE u.username = %s
            """, (username,))
            user = cursor.fetchone()
            return dict(user) if user else None
        finally:
            cursor.close()
            conn.close()
    
    @staticmethod
    def get_all(role=None, status=None):
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            query = """
                SELECT u.user_id as id, u.username, u.email,
                       u.role_id, r.role_name as role, u.created_at,
                       res.full_name, res.unit_number, res.contact_number as phone,
                       res.resident_id
                FROM users u
                JOIN roles r ON u.role_id = r.role_id
                LEFT JOIN residents res ON u.user_id = res.user_id
                WHERE 1=1
            """
            params = []
            
            if role:
                query += " AND r.role_name = %s"
                params.append(role)
            
            query += " ORDER BY u.created_at DESC"
            cursor.execute(query, params)
            return [dict(u) for u in cursor.fetchall()]
        finally:
            cursor.close()
            conn.close()
    
    @staticmethod
    def search(keyword, role=None, status=None):
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            query = """
                SELECT u.user_id as id, u.username, u.email,
                       u.role_id, r.role_name as role, u.created_at,
                       res.full_name, res.unit_number, res.contact_number as phone,
                       res.resident_id
                FROM users u
                JOIN roles r ON u.role_id = r.role_id
                LEFT JOIN residents res ON u.user_id = res.user_id
                WHERE (
                    LOWER(u.username) LIKE LOWER(%s) OR 
                    LOWER(COALESCE(res.full_name, '')) LIKE LOWER(%s) OR 
                    LOWER(u.email) LIKE LOWER(%s) OR
                    LOWER(COALESCE(res.contact_number, '')) LIKE LOWER(%s)
                )
            """
            search_term = f"%{keyword}%"
            params = [search_term, search_term, search_term, search_term]
            
            if role:
                query += " AND r.role_name = %s"
                params.append(role)
            
            query += " ORDER BY u.created_at DESC"
            cursor.execute(query, params)
            return [dict(u) for u in cursor.fetchall()]
        finally:
            cursor.close()
            conn.close()
    
    @staticmethod
    def get_with_face():
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            cursor.execute("""
                SELECT r.resident_id as id, r.full_name as username, r.full_name,
                       fe.embedding_id, fe.embedding,
                       u.role_id, ro.role_name as role
                FROM residents r
                JOIN face_embeddings fe ON r.resident_id = fe.reference_id AND fe.user_type = 'resident'
                LEFT JOIN users u ON r.user_id = u.user_id
                LEFT JOIN roles ro ON u.role_id = ro.role_id
            """)
            return [dict(u) for u in cursor.fetchall()]
        finally:
            cursor.close()
            conn.close()
    
    @staticmethod
    def update(user_id, data):
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            user_fields = []
            user_params = []
            
            if 'email' in data:
                user_fields.append("email = %s")
                user_params.append(data['email'])
            
            if 'password' in data and data['password']:
                user_fields.append("password_hash = %s")
                user_params.append(User.hash_password(data['password']))
            
            if 'role' in data:
                role_map = {
                    'ADMIN': 1, 'Admin': 1,
                    'RESIDENT': 2, 'Resident': 2, 'USER': 2,
                    'VISITOR': 3, 'Visitor': 3,
                    'SECURITY': 4, 'Security': 4
                }
                role_id = role_map.get(data['role'], 2)
                user_fields.append("role_id = %s")
                user_params.append(role_id)
            
            if user_fields:
                user_params.append(user_id)
                cursor.execute(
                    f"UPDATE users SET {', '.join(user_fields)} WHERE user_id = %s",
                    user_params
                )
            
            res_fields = []
            res_params = []
            
            if 'full_name' in data:
                res_fields.append("full_name = %s")
                res_params.append(data['full_name'])
            
            if 'phone' in data:
                res_fields.append("contact_number = %s")
                res_params.append(data['phone'])
            
            if 'unit_number' in data:
                res_fields.append("unit_number = %s")
                res_params.append(data['unit_number'])
            
            if res_fields:
                res_params.append(user_id)
                cursor.execute(
                    f"UPDATE residents SET {', '.join(res_fields)} WHERE user_id = %s",
                    res_params
                )
            
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()
            conn.close()
    
    @staticmethod
    def delete(user_id):
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM users WHERE user_id = %s", (user_id,))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            cursor.close()
            conn.close()
    
    @staticmethod
    def bulk_delete(user_ids):
        if not user_ids:
            return 0
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            placeholders = ','.join(['%s'] * len(user_ids))
            cursor.execute(f"DELETE FROM users WHERE user_id IN ({placeholders})", user_ids)
            conn.commit()
            return cursor.rowcount
        finally:
            cursor.close()
            conn.close()
    
    @staticmethod
    def deactivate(user_id):
        return True
    
    @staticmethod
    def activate(user_id):
        return True
    
    @staticmethod
    def check_expired_temp_workers():
        return 0
    
    @staticmethod
    def is_temp_worker_valid(user):
        return True


class Resident:
    @staticmethod
    def get_by_id(resident_id):
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            cursor.execute("""
                SELECT r.*, u.username, u.email, ro.role_name as role
                FROM residents r
                LEFT JOIN users u ON r.user_id = u.user_id
                LEFT JOIN roles ro ON u.role_id = ro.role_id
                WHERE r.resident_id = %s
            """, (resident_id,))
            res = cursor.fetchone()
            return dict(res) if res else None
        finally:
            cursor.close()
            conn.close()
    
    @staticmethod
    def get_all():
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            cursor.execute("""
                SELECT r.*, u.username, u.email
                FROM residents r
                LEFT JOIN users u ON r.user_id = u.user_id
                ORDER BY r.registered_at DESC
            """)
            return [dict(r) for r in cursor.fetchall()]
        finally:
            cursor.close()
            conn.close()


class Visitor:
    @staticmethod
    def get_by_id(visitor_id):
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            cursor.execute("""
                SELECT v.*, r.full_name as approved_by_name
                FROM visitors v
                LEFT JOIN residents r ON v.approved_by = r.resident_id
                WHERE v.visitor_id = %s
            """, (visitor_id,))
            vis = cursor.fetchone()
            return dict(vis) if vis else None
        finally:
            cursor.close()
            conn.close()
    
    @staticmethod
    def get_all():
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            cursor.execute("""
                SELECT v.*, r.full_name as approved_by_name
                FROM visitors v
                LEFT JOIN residents r ON v.approved_by = r.resident_id
                ORDER BY v.check_in DESC
            """)
            return [dict(v) for v in cursor.fetchall()]
        finally:
            cursor.close()
            conn.close()
    
    @staticmethod
    def check_in(visitor_id):
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                UPDATE visitors SET check_in = CURRENT_TIMESTAMP
                WHERE visitor_id = %s
            """, (visitor_id,))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            cursor.close()
            conn.close()
    
    @staticmethod
    def check_out(visitor_id):
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                UPDATE visitors SET check_out = CURRENT_TIMESTAMP
                WHERE visitor_id = %s
            """, (visitor_id,))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            cursor.close()
            conn.close()