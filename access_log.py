from psycopg2.extras import RealDictCursor
from db import get_db_connection

class AccessLog:
    @staticmethod
    def create(recognized_person, access_result, confidence=None, person_type='unknown', embedding_id=None):
        """
        Create a new access log entry with proper user type categorization

        Args:
            recognized_person: Name of recognized person (or None/Unknown)
            access_result: 'granted' or 'denied'
            confidence: Recognition confidence (0.0 - 1.0)
            person_type: User type - 'resident', 'visitor', 'security_officer', 'internal_staff', 'temp_staff', 'ADMIN', or 'unknown'
            embedding_id: Reference to face_embeddings table
        """
        # Normalize person_type to match database constraints
        valid_types = ['resident', 'visitor', 'security_officer', 'internal_staff', 'temp_staff', 'ADMIN', 'unknown']

        if person_type not in valid_types:
            # Handle edge cases - map similar types
            type_mapping = {
                'RESIDENT': 'resident',
                'VISITOR': 'visitor',
                'SECURITY_OFFICER': 'security_officer',
                'INTERNAL_STAFF': 'internal_staff',
                'Internal_Staff': 'internal_staff',
                'TEMP_STAFF': 'temp_staff',
                'Temp_Staff': 'temp_staff',
                'TEMP_WORKER': 'temp_staff',
                'temp_worker': 'temp_staff',
                'admin': 'ADMIN'
            }
            person_type = type_mapping.get(person_type, 'unknown')

        conn = get_db_connection()
        # Use RealDictCursor for consistency
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            cursor.execute("""
                INSERT INTO access_logs (recognized_person, person_type, confidence, access_result, embedding_id)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING log_id
            """, (
                recognized_person or 'Unknown',
                person_type,
                confidence,
                access_result,
                embedding_id
            ))
            result = cursor.fetchone()
            log_id = result['log_id'] if result else None
            conn.commit()
            return log_id
        finally:
            cursor.close()
            conn.close()
    
    @staticmethod
    def get_recent(limit=100):
        """Get recent access logs"""
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            cursor.execute("""
                SELECT l.log_id, l.access_time,
                       l.recognized_person, l.person_type as user_type,
                       l.confidence, l.access_result,
                       l.embedding_id
                FROM access_logs l
                ORDER BY l.access_time DESC
                LIMIT %s
            """, (limit,))
            return [dict(l) for l in cursor.fetchall()]
        finally:
            cursor.close()
            conn.close()
    
    @staticmethod
    def filter_logs(username=None, date_from=None, date_to=None, status=None, person_type=None, limit=500):
        """Filter access logs with various criteria and include user details"""
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            # Enhanced query that joins with face_embeddings, residents, and users to get full details
            query = """
                SELECT l.log_id as id, l.access_time as created_at,
                       l.recognized_person, l.person_type,
                       l.confidence, l.access_result as status,
                       l.embedding_id,
                       COALESCE(r.full_name, l.recognized_person) as full_name,
                       COALESCE(u.username, r.full_name, l.recognized_person) as username,
                       ro.role_name as role,
                       'entry' as access_type,
                       'Main Gate' as access_point
                FROM access_logs l
                LEFT JOIN face_embeddings fe ON l.embedding_id = fe.embedding_id
                LEFT JOIN residents r ON (fe.reference_id = r.resident_id AND fe.user_type = 'resident')
                LEFT JOIN users u ON r.user_id = u.user_id
                LEFT JOIN roles ro ON u.role_id = ro.role_id
                WHERE 1=1
            """
            params = []

            if username:
                query += " AND (u.username ILIKE %s OR r.full_name ILIKE %s OR l.recognized_person ILIKE %s)"
                search_pattern = f"%{username}%"
                params.extend([search_pattern, search_pattern, search_pattern])

            if date_from:
                query += " AND DATE(l.access_time) >= %s"
                params.append(date_from)

            if date_to:
                query += " AND DATE(l.access_time) <= %s"
                params.append(date_to)

            if status:
                query += " AND l.access_result = %s"
                params.append(status)

            if person_type:
                query += " AND l.person_type = %s"
                params.append(person_type)

            query += " ORDER BY l.access_time DESC LIMIT %s"
            params.append(limit)

            cursor.execute(query, params)
            logs = [dict(l) for l in cursor.fetchall()]

            # Post-process to handle person_type as role when role is missing
            for log in logs:
                if not log.get('role') and log.get('person_type'):
                    # Map person_type to a display role
                    type_to_role = {
                        'ADMIN': 'Admin',
                        'resident': 'Resident',
                        'visitor': 'Visitor',
                        'security_officer': 'Security Officer',
                        'internal_staff': 'Internal Staff',
                        'temp_staff': 'Temp Worker'
                    }
                    log['role'] = type_to_role.get(log['person_type'], log['person_type'])

            return logs
        finally:
            cursor.close()
            conn.close()
    
    @staticmethod
    def get_by_date_range(date_from, date_to, limit=500):
        """Get access logs within date range"""
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            cursor.execute("""
                SELECT l.log_id as id, l.access_time as created_at,
                       l.recognized_person, l.person_type,
                       l.confidence, l.access_result as status,
                       l.embedding_id
                FROM access_logs l
                WHERE DATE(l.access_time) >= %s AND DATE(l.access_time) <= %s
                ORDER BY l.access_time DESC
                LIMIT %s
            """, (date_from, date_to, limit))
            return [dict(l) for l in cursor.fetchall()]
        finally:
            cursor.close()
            conn.close()
    
    @staticmethod
    def get_today():
        """Get today's access logs"""
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            cursor.execute("""
                SELECT l.log_id as id, l.access_time as created_at,
                       l.recognized_person, l.person_type,
                       l.confidence, l.access_result as status,
                       l.embedding_id
                FROM access_logs l
                WHERE DATE(l.access_time) = CURRENT_DATE
                ORDER BY l.access_time DESC
            """)
            return [dict(l) for l in cursor.fetchall()]
        finally:
            cursor.close()
            conn.close()
    
    @staticmethod
    def get_stats(days=30):
        """Get access statistics for the past N days"""
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE access_result = 'granted') as granted,
                    COUNT(*) FILTER (WHERE access_result = 'denied') as denied,
                    COUNT(DISTINCT recognized_person) FILTER (WHERE recognized_person != 'Unknown') as unique_users
                FROM access_logs
                WHERE access_time >= CURRENT_TIMESTAMP - INTERVAL '%s days'
            """, (days,))
            return dict(cursor.fetchone())
        finally:
            cursor.close()
            conn.close()
    
    @staticmethod
    def get_all_users_for_filter():
        """Get all distinct users (residents, staff, etc.) who appear in access logs"""
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            cursor.execute("""
                SELECT DISTINCT
                    l.recognized_person as username,
                    l.person_type,
                    CASE
                        WHEN l.person_type = 'resident' THEN 'Resident'
                        WHEN l.person_type = 'internal_staff' THEN 'Staff'
                        WHEN l.person_type = 'temp_staff' THEN 'Temp Worker'
                        WHEN l.person_type = 'security_officer' THEN 'Security Officer'
                        WHEN l.person_type = 'visitor' THEN 'Visitor'
                        WHEN l.person_type = 'ADMIN' THEN 'Admin'
                        ELSE l.person_type
                    END as type_label
                FROM access_logs l
                WHERE l.recognized_person IS NOT NULL
                  AND l.recognized_person != 'Unknown'
                  AND l.recognized_person != ''
                ORDER BY l.person_type, l.recognized_person
            """)
            return [dict(u) for u in cursor.fetchall()]
        finally:
            cursor.close()
            conn.close()