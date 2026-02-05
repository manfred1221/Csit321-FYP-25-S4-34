import numpy as np
from datetime import datetime, date
from psycopg2.extras import RealDictCursor
from database import get_db_connection
from config import Config

class User:
    # @staticmethod
    # def hash_password(password):
    #     return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    # @staticmethod
    # def verify_password(password, password_hash):
    #     try:
    #         # If it's a bcrypt hash
    #         if password_hash.startswith('$2b$') or password_hash.startswith('$2a$'):
    #             return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
            
    #         # Fallback for legacy/test passwords
    #         if password_hash.startswith('hashed_pw_'):
    #             return password == 'admin123' or password == password_hash
            
    #         # Direct comparison for plaintext (temporary/testing)
    #         return password == password_hash
    #     except Exception as e:
    #         print(f"Password verification error: {e}")
    #         return False
    
    # Map role names
    role_map = {
        'ADMIN': 1, 'Admin': 1,
        'RESIDENT': 2, 'Resident': 2, 'USER': 2,
        # 'VISITOR': 3, 'Visitor': 3,
        'SECURITY': 4, 'Security': 4,
        'INTERNAL_STAFF': 9, 'Internal Staff': 9,
        # 'TEMP_WORKER': 6, 'TempWorker': 6
    }

    @staticmethod
    def create(data):
        """Create a new user with associated resident record if needed"""
        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            # IMPORTANT: Use RealDictCursor for all operations
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Get role_id from role name
            role_input = data.get('role', 'Resident')   
            role_id = User.role_map.get(role_input, 2)
            
            # Determine initial status
            status = data.get('status', 'active')
            access_level = data.get('access_level', 'standard')
            
            # Validate required fields
            if not data.get('username'):
                raise ValueError("Username is required")
            if not data.get('email'):
                raise ValueError("Email is required")
            if not data.get('password'):
                raise ValueError("Password is required")
            
            cursor.execute("""
                INSERT INTO users (username, email, password_hash, role_id, status, access_level)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING user_id
            """, (
                data['username'],
                data['email'],
                data['password'],
                role_id,
                status,
                access_level
            ))
            
            result = cursor.fetchone()
            if not result:
                raise ValueError("Failed to create user - no user_id returned")
            
            # Access as dictionary key with RealDictCursor
            user_id = result['user_id']
            
            if not user_id or user_id == 0:
                raise ValueError(f"Invalid user_id returned: {user_id}")
            
            # Create resident record for residents and temp workers
            if role_id in [2, 9]:  # Resident or Temp Worker
                cursor.execute("""
                    INSERT INTO residents (full_name, unit_number, contact_number, user_id)
                    VALUES (%s, %s, %s, %s)
                    RETURNING resident_id
                """, (
                    data.get('full_name', data['username']),
                    data.get('unit_number', 'N/A'),
                    data.get('phone', ''),
                    user_id
                ))
                
                res_result = cursor.fetchone()
                if not res_result:
                    raise ValueError("Failed to create resident record")
                
                resident_id = res_result['resident_id']
                
                # If temp worker, create temp worker record
                if role_id == 9:
                    cursor.execute("""
                        INSERT INTO temp_workers (
                            user_id, work_start_date, work_end_date, 
                            work_schedule, work_details, id_document_path
                        )
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (
                        user_id,
                        data.get('work_start_date'),
                        data.get('work_end_date'),
                        data.get('work_schedule', ''),
                        data.get('work_details', ''),
                        data.get('id_document_path')
                    ))
            
            conn.commit()
            return user_id
            
        except Exception as e:
            if conn:
                conn.rollback()
            import logging
            logging.error(f"User creation error: {type(e).__name__}: {str(e)}")
            raise e
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    # ============================================================================
    # user.py - REPLACE User.authenticate() method
    # Uses PLAIN TEXT password comparison (no hashing)
    # ============================================================================

    @staticmethod
    def authenticate(username, password):
        """
        Authenticate user with plain text password comparison.
        Returns user dict with role_id and role_name from roles table.
        """
        from psycopg2.extras import RealDictCursor
        import logging
        
        logger = logging.getLogger(__name__)
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Query with JOIN to get role_id and role_name
            cursor.execute("""
                SELECT 
                    u.user_id,
                    u.username,
                    u.password_hash,        -- Actually stores plain text password
                    u.email,
                    u.full_name,
                    u.contact_number,
                    u.status,
                    u.access_level,
                    u.role_id,              -- ⭐ The role ID number
                    r.role_name,            -- ⭐ The role name string
                    u.created_at
                FROM users u
                LEFT JOIN roles r ON u.role_id = r.role_id
                WHERE u.username = %s
            """, (username,))
            
            user = cursor.fetchone()
            
            if not user:
                logger.info(f"❌ User not found: {username}")
                cursor.close()
                conn.close()
                return None
            
            # Get stored password (plain text in your case)
            db_password = user.get('password_hash')
            
            # Debug log
            logger.info(f"[DEBUG] authenticate called with username='{username}'")
            logger.info(f"[DEBUG] Found user: role_id={user.get('role_id')}, role_name={user.get('role_name')}")
            
            # Check if user is active
            if user.get('status') != 'active':
                logger.info(f"❌ User inactive: {username}")
                cursor.close()
                conn.close()
                return None
            
            # Plain text password comparison
            if password != db_password:
                logger.info(f"❌ Incorrect password for: {username}")
                logger.info(f"[DEBUG] Password mismatch: provided != stored")
                cursor.close()
                conn.close()
                return None
            
            # Check if user is a resident and get resident_id
            resident_id = None
            if user.get('role_id') == 2:  # Resident role
                cursor.execute("""
                    SELECT resident_id FROM residents WHERE user_id = %s
                """, (user['user_id'],))
                resident_row = cursor.fetchone()
                if resident_row:
                    resident_id = resident_row['resident_id']
                    logger.info(f"[DEBUG] Found resident_id: {resident_id}")
            
            # Build result dictionary
            result = {
                'id': user['user_id'],
                'username': user['username'],
                'email': user.get('email'),
                'full_name': user.get('full_name'),
                'phone': user.get('contact_number'),
                'status': user.get('status'),
                'role': user.get('role_name'),       # Role name string
                'role_id': user.get('role_id'),      # ⭐ Role ID number
                'resident_id': resident_id,
                'access_level': user.get('access_level')
            }
            
            logger.info(f"✅ Authentication successful: {username}")
            logger.info(f"   → user_id={result['id']}")
            logger.info(f"   → role_id={result['role_id']}")
            logger.info(f"   → role_name={result['role']}")
            logger.info(f"   → resident_id={result['resident_id']}")
            
            cursor.close()
            conn.close()
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Authentication error for {username}: {e}")
            import traceback
            traceback.print_exc()
            return None
        
    @staticmethod
    def get_by_id(user_id):
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            cursor.execute("""
                SELECT u.user_id as id, u.username, u.email, u.password_hash,
                       u.role_id, r.role_name as role, u.created_at,
                       res.full_name, res.unit_number, res.contact_number as phone,
                       res.resident_id,
                       tw.work_start_date, tw.work_end_date, tw.work_schedule, 
                       tw.work_details, tw.id_document_path
                FROM users u
                JOIN roles r ON u.role_id = r.role_id
                LEFT JOIN residents res ON u.user_id = res.user_id
                LEFT JOIN temp_workers tw ON u.user_id = tw.user_id
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
                       res.resident_id,
                       tw.work_start_date, tw.work_end_date,
                       CASE WHEN fe.embedding_id IS NOT NULL THEN 1 ELSE 0 END as has_face
                FROM users u
                JOIN roles r ON u.role_id = r.role_id
                LEFT JOIN residents res ON u.user_id = res.user_id
                LEFT JOIN temp_workers tw ON u.user_id = tw.user_id
                LEFT JOIN face_embeddings fe ON res.resident_id = fe.reference_id AND fe.user_type = 'resident'
                WHERE 1=1
            """
            params = []
            
            if role:
                query += " AND r.role_name = %s"
                params.append(role)
            
            if status:
                query += " AND LOWER(u.status) = LOWER(%s)"
                params.append(status)
            
            query += " ORDER BY u.created_at DESC"
            cursor.execute(query, params)
            
            users = []
            for u in cursor.fetchall():
                user_dict = dict(u)
                user_dict['face_encoding_path'] = user_dict.get('has_face', 0) == 1
                users.append(user_dict)
            return users
        finally:
            cursor.close()
            conn.close()
    
    @staticmethod
    def get_all(role=None, status=None):
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            query = """
                SELECT u.user_id as id, u.username, u.email, u.status,  -- ✅ ADDED THIS (u.status)
                       u.role_id, r.role_name as role, u.created_at,
                       res.full_name, res.unit_number, res.contact_number as phone,
                       res.resident_id,
                       tw.work_start_date, tw.work_end_date,
                       CASE WHEN fe.embedding_id IS NOT NULL THEN 1 ELSE 0 END as has_face
                FROM users u
                JOIN roles r ON u.role_id = r.role_id
                LEFT JOIN residents res ON u.user_id = res.user_id
                LEFT JOIN temp_workers tw ON u.user_id = tw.user_id
                LEFT JOIN face_embeddings fe ON res.resident_id = fe.reference_id AND fe.user_type = 'resident'
                WHERE 1=1
            """
            params = []
            
            if role:
                query += " AND r.role_name = %s"
                params.append(role)
            
            if status:
                query += " AND LOWER(u.status) = LOWER(%s)"
                params.append(status)
            
            query += " ORDER BY u.created_at DESC"
            cursor.execute(query, params)
            
            users = []
            for u in cursor.fetchall():
                user_dict = dict(u)
                user_dict['face_encoding_path'] = user_dict.get('has_face', 0) == 1
                users.append(user_dict)
            return users
        finally:
            cursor.close()
            conn.close()
    
    @staticmethod
    def search(keyword, role=None, status=None):
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            query = """
                SELECT u.user_id as id, u.username, u.email, u.status,  -- ✅ ADDED THIS (u.status)
                       u.role_id, r.role_name as role, u.created_at,
                       res.full_name, res.unit_number, res.contact_number as phone,
                       res.resident_id,
                       tw.work_start_date, tw.work_end_date,
                       CASE WHEN fe.embedding_id IS NOT NULL THEN 1 ELSE 0 END as has_face
                FROM users u
                JOIN roles r ON u.role_id = r.role_id
                LEFT JOIN residents res ON u.user_id = res.user_id
                LEFT JOIN temp_workers tw ON u.user_id = tw.user_id
                LEFT JOIN face_embeddings fe ON res.resident_id = fe.reference_id AND fe.user_type = 'resident'
                WHERE (
                    LOWER(u.username) LIKE LOWER(%s) OR 
                    LOWER(COALESCE(res.full_name, '')) LIKE LOWER(%s) OR 
                    LOWER(u.email) LIKE LOWER(%s) OR
                    LOWER(COALESCE(res.contact_number, '')) LIKE LOWER(%s) OR
                    LOWER(COALESCE(res.unit_number, '')) LIKE LOWER(%s)
                )
            """
            search_term = f"%{keyword}%"
            params = [search_term, search_term, search_term, search_term, search_term]
            
            if role:
                query += " AND r.role_name = %s"
                params.append(role)
            
            if status:
                query += " AND LOWER(u.status) = LOWER(%s)"
                params.append(status)
            
            query += " ORDER BY u.created_at DESC"
            cursor.execute(query, params)
            
            users = []
            for u in cursor.fetchall():
                user_dict = dict(u)
                user_dict['face_encoding_path'] = user_dict.get('has_face', 0) == 1
                users.append(user_dict)
            return users
        finally:
            cursor.close()
            conn.close()
    
    @staticmethod
    def get_with_face():
        """Get all users with face embeddings - properly convert embeddings to numpy arrays"""
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
                WHERE LOWER(u.status) = 'active'
            """)
            users = []
            for row in cursor.fetchall():
                user_dict = dict(row)
                # Convert embedding from string/list to numpy array
                embedding = user_dict.get('embedding')
                if embedding is not None:
                    if isinstance(embedding, str):
                        # If it's a string, parse it
                        embedding = np.array(eval(embedding))
                    elif isinstance(embedding, list):
                        # If it's already a list, convert to numpy array
                        embedding = np.array(embedding)
                    elif not isinstance(embedding, np.ndarray):
                        # If it's some other type, try to convert
                        embedding = np.array(embedding)
                    user_dict['embedding'] = embedding
                users.append(user_dict)
            return users
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
                user_params.append(data['password'])
                        
            if 'role' in data:
                role_id = User.role_map.get(data['role'])
                if role_id:
                    user_fields.append("role_id = %s")
                    user_params.append(role_id)
            
            if 'status' in data:
                user_fields.append("status = %s")
                user_params.append(data['status'])
            
            if 'access_level' in data:
                user_fields.append("access_level = %s")
                user_params.append(data['access_level'])
            
            if user_fields:
                user_params.append(user_id)
                cursor.execute(
                    f"UPDATE users SET {', '.join(user_fields)} WHERE user_id = %s",
                    user_params
                )
            
            # Update resident fields
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
            
            # Update temp worker fields if applicable
            tw_fields = []
            tw_params = []
            
            if 'work_start_date' in data:
                tw_fields.append("work_start_date = %s")
                tw_params.append(data['work_start_date'] if data['work_start_date'] else None)
            
            if 'work_end_date' in data:
                tw_fields.append("work_end_date = %s")
                tw_params.append(data['work_end_date'] if data['work_end_date'] else None)
            
            if 'work_schedule' in data:
                tw_fields.append("work_schedule = %s")
                tw_params.append(data['work_schedule'])
            
            if 'work_details' in data:
                tw_fields.append("work_details = %s")
                tw_params.append(data['work_details'])
            
            if 'id_document_path' in data:
                tw_fields.append("id_document_path = %s")
                tw_params.append(data['id_document_path'])
            
            if tw_fields:
                # Check if temp_worker record exists
                cursor.execute("SELECT 1 FROM temp_workers WHERE user_id = %s", (user_id,))
                if cursor.fetchone():
                    tw_params.append(user_id)
                    cursor.execute(
                        f"UPDATE temp_workers SET {', '.join(tw_fields)} WHERE user_id = %s",
                        tw_params
                    )
                else:
                    # Create new temp_worker record
                    cursor.execute("SELECT resident_id FROM residents WHERE user_id = %s", (user_id,))
                    res = cursor.fetchone()
                    if res:
                        cursor.execute("""
                            INSERT INTO temp_workers (user_id, work_start_date, work_end_date, work_schedule, work_details, id_document_path)
                            VALUES (%s, %s, %s, %s, %s, %s)
                        """, (
                            user_id,
                            data.get('work_start_date'),
                            data.get('work_end_date'),
                            data.get('work_schedule'),
                            data.get('work_details'),
                            data.get('id_document_path')
                        ))
            
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
            # Delete in order due to foreign key constraints
            cursor.execute("DELETE FROM temp_workers WHERE user_id = %s", (user_id,))
            cursor.execute("DELETE FROM face_embeddings WHERE reference_id IN (SELECT resident_id FROM residents WHERE user_id = %s) AND user_type = 'resident'", (user_id,))
            cursor.execute("DELETE FROM residents WHERE user_id = %s", (user_id,))
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
            
            # Delete in order due to foreign key constraints
            cursor.execute(f"DELETE FROM temp_workers WHERE user_id IN ({placeholders})", user_ids)
            cursor.execute(f"""
                DELETE FROM face_embeddings 
                WHERE reference_id IN (SELECT resident_id FROM residents WHERE user_id IN ({placeholders})) 
                AND user_type = 'resident'
            """, user_ids)
            cursor.execute(f"DELETE FROM residents WHERE user_id IN ({placeholders})", user_ids)
            cursor.execute(f"DELETE FROM users WHERE user_id IN ({placeholders})", user_ids)
            
            conn.commit()
            return cursor.rowcount
        finally:
            cursor.close()
            conn.close()
    
    @staticmethod
    def deactivate(user_id):
        """Temporarily deactivate a user account"""
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE users SET status = 'inactive' WHERE user_id = %s",
                (user_id,)
            )
            conn.commit()
            return cursor.rowcount > 0
        finally:
            cursor.close()
            conn.close()
    
    @staticmethod
    def activate(user_id):
        """Reactivate a user account"""
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE users SET status = 'active' WHERE user_id = %s",
                (user_id,)
            )
            conn.commit()
            return cursor.rowcount > 0
        finally:
            cursor.close()
            conn.close()
    
    @staticmethod
    def check_expired_temp_workers():
        """
        Check and deactivate expired temporary workers.
        Should be called periodically (e.g., daily cron job or on app startup)
        Returns the count of deactivated workers
        """
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            # Find and deactivate expired temp workers
            cursor.execute("""
                UPDATE users 
                SET status = 'inactive'
                WHERE user_id IN (
                    SELECT u.user_id 
                    FROM users u
                    JOIN temp_workers tw ON u.user_id = tw.user_id
                    WHERE tw.work_end_date < CURRENT_DATE
                    AND LOWER(u.status) = 'active'
                )
            """)
            count = cursor.rowcount
            conn.commit()
            return count
        finally:
            cursor.close()
            conn.close()
    
    @staticmethod
    def is_temp_worker_valid(user):
        """
        Check if a temporary worker's access is still valid
        based on their work_start_date and work_end_date
        """
        if not user:
            return False
        
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            user_id = user.get('id') or user.get('user_id')
            cursor.execute("""
                SELECT work_start_date, work_end_date
                FROM temp_workers
                WHERE user_id = %s
            """, (user_id,))
            
            tw = cursor.fetchone()
            if not tw:
                return True  # Not a temp worker, so valid
            
            today = date.today()
            
            # Check if work period is valid
            start_date = tw.get('work_start_date')
            end_date = tw.get('work_end_date')
            
            if start_date and today < start_date:
                return False  # Work hasn't started yet
            
            if end_date and today > end_date:
                return False  # Work period has ended
            
            return True
        finally:
            cursor.close()
            conn.close()
    
    @staticmethod
    def get_expiring_temp_workers(days=7):
        """Get temp workers whose access will expire within the specified days"""
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            cursor.execute("""
                SELECT u.user_id as id, u.username, u.email, u.status,
                       res.full_name, res.contact_number as phone,
                       tw.work_start_date, tw.work_end_date, tw.work_schedule, tw.work_details
                FROM users u
                JOIN temp_workers tw ON u.user_id = tw.user_id
                LEFT JOIN residents res ON u.user_id = res.user_id
                WHERE tw.work_end_date BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '%s days'
                AND LOWER(u.status) = 'active'
                ORDER BY tw.work_end_date ASC
            """, (days,))
            return [dict(u) for u in cursor.fetchall()]
        finally:
            cursor.close()
            conn.close()


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
