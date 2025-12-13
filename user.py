import bcrypt
import numpy as np
from datetime import date
from psycopg2.extras import RealDictCursor
<<<<<<< HEAD
from database import get_db_connection
from config import Config
from werkzeug.security import check_password_hash

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
    
=======
from database import get_db_connection  # ✅ use your database.py, not db.py

class User:
    @staticmethod
    def hash_password(password: str) -> str:
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        try:
            if not password_hash:
                return False
            if password_hash.startswith("$2b$") or password_hash.startswith("$2a$"):
                return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
            # fallback for testing only
            return password == password_hash
        except Exception:
            return False

>>>>>>> e00f4330b54b2a5a29c75eee08ba7b7e3007c292
    @staticmethod
    def create(data: dict) -> int:
        """
        Create a new user.
        Supabase schema supported:
          users(user_id, username, email, password_hash, role_id, created_at)
          residents(resident_id, full_name, unit_number, contact_number, user_id, registered_at)
          staff(staff_id, user_id, full_name, contact_number, position, ...)
          temp_staff(temp_id, user_id, full_name, company, contact_number, contract_start, contract_end, ...)
          roles(role_id, role_name)
        """
        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            if not data.get("username"):
                raise ValueError("username is required")
            if not data.get("email"):
                raise ValueError("email is required")
            if not data.get("password"):
                raise ValueError("password is required")

            # role mapping (adjust if your roles table differs)
            role_name = (data.get("role") or "Resident").strip()
            role_map = {
                "Admin": 1,
                "Resident": 2,
                "Visitor": 3,
                "Security_Officer": 4,
                "TEMP_WORKER": 6,
                "Internal_Staff": 8,
                "Staff": 8,
            }
            role_id = role_map.get(role_name, 2)
<<<<<<< HEAD
            
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
            if role_id in [2, 6]:  # Resident or Temp Worker
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
                if role_id == 6:
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
            
=======

            cursor.execute(
                """
                INSERT INTO users (username, email, password_hash, role_id)
                VALUES (%s, %s, %s, %s)
                RETURNING user_id;
                """,
                (data["username"], data["email"], User.hash_password(data["password"]), role_id),
            )
            row = cursor.fetchone()
            if not row:
                raise ValueError("Failed to create user")
            user_id = row["user_id"]

            # Create related record depending on role
            if role_id == 2:  # Resident
                cursor.execute(
                    """
                    INSERT INTO residents (full_name, unit_number, contact_number, user_id)
                    VALUES (%s, %s, %s, %s)
                    RETURNING resident_id;
                    """,
                    (
                        data.get("full_name") or data["username"],
                        data.get("unit_number") or "N/A",
                        data.get("phone") or "",
                        user_id,
                    ),
                )
                cursor.fetchone()

            elif role_id == 8:  # Internal staff
                cursor.execute(
                    """
                    INSERT INTO staff (user_id, full_name, contact_number, position, is_active)
                    VALUES (%s, %s, %s, %s, TRUE)
                    RETURNING staff_id;
                    """,
                    (
                        user_id,
                        data.get("full_name") or data["username"],
                        data.get("phone") or "",
                        data.get("position") or "",
                    ),
                )
                cursor.fetchone()

            elif role_id == 6:  # Temp worker
                # create temp_staff (exists in your schema)
                cursor.execute(
                    """
                    INSERT INTO temp_staff (full_name, company, contact_number, contract_start, contract_end,
                                           allowed_rate_min, allowed_rate_max, user_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING temp_id;
                    """,
                    (
                        data.get("full_name") or data["username"],
                        data.get("company") or "",
                        data.get("phone") or "",
                        data.get("contract_start"),
                        data.get("contract_end"),
                        data.get("allowed_rate_min"),
                        data.get("allowed_rate_max"),
                        user_id,
                    ),
                )
                cursor.fetchone()

                # also create temp_workers (exists in your schema)
                cursor.execute(
                    """
                    INSERT INTO temp_workers (user_id, work_start_date, work_end_date, work_schedule, work_details, id_document_path)
                    VALUES (%s, %s, %s, %s, %s, %s);
                    """,
                    (
                        user_id,
                        data.get("work_start_date"),
                        data.get("work_end_date"),
                        data.get("work_schedule") or "",
                        data.get("work_details") or "",
                        data.get("id_document_path"),
                    ),
                )

>>>>>>> e00f4330b54b2a5a29c75eee08ba7b7e3007c292
            conn.commit()
            return int(user_id)

        except Exception:
            if conn:
                conn.rollback()
            raise
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    @staticmethod
<<<<<<< HEAD
    def authenticate(username, password):
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            print(f"[DEBUG] authenticate called with username='{username}', password='{password}'")

            cursor.execute("""
                SELECT user_id, username, password_hash
                FROM users
                WHERE username = %s
                LIMIT 1
            """, (username,))

            row = cursor.fetchone()
            cursor.close()
            conn.close()

            if not row:
                print("[DEBUG] User not found")
                return None

            user_id, db_username, db_password = row

            # ❗ PLAIN TEXT CHECK — NO HASHING
            if password != db_password:
                print("[DEBUG] Incorrect password (plain-text check failed)")
                return None

            # Successful login
            return {
                'id': user_id,
                'username': db_username,
                'role': 'Admin'
            }

        except Exception as e:
            print("[AUTHENTICATION ERROR]", e)
            return None
    
=======
    def authenticate(username: str, password: str):
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            cursor.execute(
                """
                SELECT u.user_id,
                       u.username,
                       u.email,
                       u.password_hash,
                       u.role_id,
                       r.role_name
                FROM users u
                JOIN roles r ON u.role_id = r.role_id
                WHERE u.username = %s
                LIMIT 1;
                """,
                (username,),
            )
            u = cursor.fetchone()
            if not u:
                return None

            if not User.verify_password(password, u["password_hash"]):
                return None

            # attach profile info from role tables
            role_name = u["role_name"]

            profile = {"full_name": None, "phone": None, "unit_number": None, "resident_id": None}

            if role_name.lower() == "resident":
                cursor.execute(
                    """
                    SELECT resident_id, full_name, contact_number, unit_number
                    FROM residents
                    WHERE user_id = %s
                    LIMIT 1;
                    """,
                    (u["user_id"],),
                )
                rrow = cursor.fetchone()
                if rrow:
                    profile.update({
                        "resident_id": rrow["resident_id"],
                        "full_name": rrow["full_name"],
                        "phone": rrow["contact_number"],
                        "unit_number": rrow["unit_number"],
                    })

            elif role_name.lower() in ["internal_staff", "staff"]:
                cursor.execute(
                    """
                    SELECT staff_id, full_name, contact_number
                    FROM staff
                    WHERE user_id = %s
                    LIMIT 1;
                    """,
                    (u["user_id"],),
                )
                srow = cursor.fetchone()
                if srow:
                    profile.update({
                        "full_name": srow["full_name"],
                        "phone": srow["contact_number"],
                    })

            elif role_name.lower() in ["temp_worker", "temp staff", "temp_staff"]:
                cursor.execute(
                    """
                    SELECT full_name, contact_number
                    FROM temp_staff
                    WHERE user_id = %s
                    LIMIT 1;
                    """,
                    (u["user_id"],),
                )
                trow = cursor.fetchone()
                if trow:
                    profile.update({
                        "full_name": trow["full_name"],
                        "phone": trow["contact_number"],
                    })

            user = {
                "user_id": u["user_id"],
                "id": u["user_id"],  # keep compatibility with your app.py
                "username": u["username"],
                "email": u["email"],
                "role_id": u["role_id"],
                "role": u["role_name"],
                **profile
            }
            return user

        finally:
            cursor.close()
            conn.close()

>>>>>>> e00f4330b54b2a5a29c75eee08ba7b7e3007c292
    @staticmethod
    def get_by_id(user_id: int):
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
<<<<<<< HEAD
            cursor.execute("""
                SELECT u.user_id as id, u.username, u.email, u.password_hash,
                       u.role_id, r.role_name as role, u.created_at,
                       res.full_name, res.unit_number, res.contact_number as phone,
                       res.resident_id,
                       tw.work_start_date, tw.work_end_date, tw.work_schedule, 
                       tw.work_details, tw.id_document_path
=======
            cursor.execute(
                """
                SELECT u.user_id,
                       u.username,
                       u.email,
                       u.role_id,
                       r.role_name
>>>>>>> e00f4330b54b2a5a29c75eee08ba7b7e3007c292
                FROM users u
                JOIN roles r ON u.role_id = r.role_id
                WHERE u.user_id = %s
                LIMIT 1;
                """,
                (user_id,),
            )
            u = cursor.fetchone()
            if not u:
                return None

            # same profile attach logic as authenticate()
            role_name = u["role_name"]
            profile = {"full_name": None, "phone": None, "unit_number": None, "resident_id": None}

            if role_name.lower() == "resident":
                cursor.execute(
                    """
                    SELECT resident_id, full_name, contact_number, unit_number
                    FROM residents
                    WHERE user_id = %s
                    LIMIT 1;
                    """,
                    (u["user_id"],),
                )
                rrow = cursor.fetchone()
                if rrow:
                    profile.update({
                        "resident_id": rrow["resident_id"],
                        "full_name": rrow["full_name"],
                        "phone": rrow["contact_number"],
                        "unit_number": rrow["unit_number"],
                    })

            elif role_name.lower() in ["internal_staff", "staff"]:
                cursor.execute(
                    """
                    SELECT full_name, contact_number
                    FROM staff
                    WHERE user_id = %s
                    LIMIT 1;
                    """,
                    (u["user_id"],),
                )
                srow = cursor.fetchone()
                if srow:
                    profile.update({
                        "full_name": srow["full_name"],
                        "phone": srow["contact_number"],
                    })

            elif role_name.lower() in ["temp_worker", "temp staff", "temp_staff"]:
                cursor.execute(
                    """
                    SELECT full_name, contact_number
                    FROM temp_staff
                    WHERE user_id = %s
                    LIMIT 1;
                    """,
                    (u["user_id"],),
                )
                trow = cursor.fetchone()
                if trow:
                    profile.update({
                        "full_name": trow["full_name"],
                        "phone": trow["contact_number"],
                    })

            return {
                "user_id": u["user_id"],
                "id": u["user_id"],
                "username": u["username"],
                "email": u["email"],
                "role_id": u["role_id"],
                "role": u["role_name"],
                **profile
            }

        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def get_all(role=None):
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
<<<<<<< HEAD
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
=======
            q = """
                SELECT u.user_id,
                       u.username,
                       u.email,
                       r.role_name
                FROM users u
                JOIN roles r ON u.role_id = r.role_id
>>>>>>> e00f4330b54b2a5a29c75eee08ba7b7e3007c292
                WHERE 1=1
            """
            params = []
            if role:
                q += " AND r.role_name = %s"
                params.append(role)
            q += " ORDER BY u.created_at DESC"

            cursor.execute(q, params)
            rows = cursor.fetchall()

            # return a consistent shape
            out = []
            for row in rows:
                out.append({
                    "user_id": row["user_id"],
                    "id": row["user_id"],
                    "username": row["username"],
                    "email": row["email"],
                    "role": row["role_name"],
                })
            return out
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def update(user_id: int, data: dict):
        """
        Updates:
          - users.email, users.password_hash, users.role_id
          - residents.full_name/contact_number/unit_number (if resident exists)
          - staff.full_name/contact_number/position (if staff exists)
          - temp_staff fields (if temp_staff exists)
          - temp_workers fields (if temp_workers exists)
        """
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
<<<<<<< HEAD
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
=======
            # update users table
>>>>>>> e00f4330b54b2a5a29c75eee08ba7b7e3007c292
            user_fields = []
            user_params = []

            if "email" in data:
                user_fields.append("email = %s")
                user_params.append(data["email"])

            if "password" in data and data["password"]:
                user_fields.append("password_hash = %s")
<<<<<<< HEAD
                user_params.append(data['password'])
                        
            if 'role' in data:
=======
                user_params.append(User.hash_password(data["password"]))

            if "role" in data:
>>>>>>> e00f4330b54b2a5a29c75eee08ba7b7e3007c292
                role_map = {
                    "Admin": 1,
                    "Resident": 2,
                    "Visitor": 3,
                    "Security_Officer": 4,
                    "TEMP_WORKER": 6,
                    "Internal_Staff": 8,
                    "Staff": 8,
                }
                role_id = role_map.get(data["role"], 2)
                user_fields.append("role_id = %s")
                user_params.append(role_id)

            if user_fields:
                user_params.append(user_id)
                cursor.execute(
                    f"UPDATE users SET {', '.join(user_fields)} WHERE user_id = %s",
                    user_params
                )

            # residents update (if exists)
            res_fields = []
            res_params = []
            if "full_name" in data:
                res_fields.append("full_name = %s")
                res_params.append(data["full_name"])
            if "phone" in data:
                res_fields.append("contact_number = %s")
                res_params.append(data["phone"])
            if "unit_number" in data:
                res_fields.append("unit_number = %s")
                res_params.append(data["unit_number"])

            if res_fields:
                cursor.execute("SELECT 1 FROM residents WHERE user_id = %s", (user_id,))
                if cursor.fetchone():
                    res_params.append(user_id)
                    cursor.execute(
                        f"UPDATE residents SET {', '.join(res_fields)} WHERE user_id = %s",
                        res_params
                    )

            # staff update (if exists)
            staff_fields = []
            staff_params = []
            if "full_name" in data:
                staff_fields.append("full_name = %s")
                staff_params.append(data["full_name"])
            if "phone" in data:
                staff_fields.append("contact_number = %s")
                staff_params.append(data["phone"])
            if "position" in data:
                staff_fields.append("position = %s")
                staff_params.append(data["position"])

            if staff_fields:
                cursor.execute("SELECT 1 FROM staff WHERE user_id = %s", (user_id,))
                if cursor.fetchone():
                    staff_params.append(user_id)
                    cursor.execute(
                        f"UPDATE staff SET {', '.join(staff_fields)} WHERE user_id = %s",
                        staff_params
                    )

            # temp_workers update (if exists)
            tw_fields = []
            tw_params = []
            if "work_start_date" in data:
                tw_fields.append("work_start_date = %s")
                tw_params.append(data["work_start_date"])
            if "work_end_date" in data:
                tw_fields.append("work_end_date = %s")
                tw_params.append(data["work_end_date"])
            if "work_schedule" in data:
                tw_fields.append("work_schedule = %s")
                tw_params.append(data["work_schedule"])
            if "work_details" in data:
                tw_fields.append("work_details = %s")
                tw_params.append(data["work_details"])
            if "id_document_path" in data:
                tw_fields.append("id_document_path = %s")
                tw_params.append(data["id_document_path"])

            if tw_fields:
                cursor.execute("SELECT 1 FROM temp_workers WHERE user_id = %s", (user_id,))
                if cursor.fetchone():
                    tw_params.append(user_id)
                    cursor.execute(
                        f"UPDATE temp_workers SET {', '.join(tw_fields)} WHERE user_id = %s",
                        tw_params
                    )
<<<<<<< HEAD
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
=======
>>>>>>> e00f4330b54b2a5a29c75eee08ba7b7e3007c292

            conn.commit()
            return True
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
            conn.close()

class Resident:
    @staticmethod
<<<<<<< HEAD
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
=======
>>>>>>> e00f4330b54b2a5a29c75eee08ba7b7e3007c292
    def get_all():
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            cursor.execute("""
<<<<<<< HEAD
                SELECT r.*, u.username, u.email
=======
                SELECT r.*, u.username, u.email, ro.role_name as role
>>>>>>> e00f4330b54b2a5a29c75eee08ba7b7e3007c292
                FROM residents r
                LEFT JOIN users u ON r.user_id = u.user_id
                LEFT JOIN roles ro ON u.role_id = ro.role_id
                ORDER BY r.registered_at DESC
            """)
            return [dict(r) for r in cursor.fetchall()]
        finally:
            cursor.close()
            conn.close()
