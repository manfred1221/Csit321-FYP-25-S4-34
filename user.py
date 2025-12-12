import bcrypt
import numpy as np
from datetime import date
from psycopg2.extras import RealDictCursor
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

    @staticmethod
    def get_by_id(user_id: int):
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            cursor.execute(
                """
                SELECT u.user_id,
                       u.username,
                       u.email,
                       u.role_id,
                       r.role_name
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
            q = """
                SELECT u.user_id,
                       u.username,
                       u.email,
                       r.role_name
                FROM users u
                JOIN roles r ON u.role_id = r.role_id
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
            # update users table
            user_fields = []
            user_params = []

            if "email" in data:
                user_fields.append("email = %s")
                user_params.append(data["email"])

            if "password" in data and data["password"]:
                user_fields.append("password_hash = %s")
                user_params.append(User.hash_password(data["password"]))

            if "role" in data:
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
    def get_all():
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            cursor.execute("""
                SELECT r.*, u.username, u.email, ro.role_name as role
                FROM residents r
                LEFT JOIN users u ON r.user_id = u.user_id
                LEFT JOIN roles ro ON u.role_id = ro.role_id
                ORDER BY r.registered_at DESC
            """)
            return [dict(r) for r in cursor.fetchall()]
        finally:
            cursor.close()
            conn.close()
