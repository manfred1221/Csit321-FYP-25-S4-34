from psycopg2.extras import RealDictCursor
from db import get_db_connection

class AccessLog:
    @staticmethod
    def create(recognized_person, access_result, confidence=None, person_type='unknown', embedding_id=None):
        """
        Create a new access log entry
        
        Args:
            recognized_person: Name of recognized person (or None/Unknown)
            access_result: 'granted' or 'denied'
            confidence: Recognition confidence (0.0 - 1.0)
            person_type: 'resident', 'visitor', or 'unknown'
            embedding_id: Reference to face_embeddings table
        """
        conn = get_db_connection()
        cursor = conn.cursor()
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
            log_id = cursor.fetchone()[0]
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
                SELECT l.log_id as id, l.access_time as created_at, 
                       l.recognized_person, l.person_type, 
                       l.confidence, l.access_result as status,
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
    def filter_logs(user_id=None, date_from=None, date_to=None, status=None, person_type=None, limit=500):
        """Filter access logs with various criteria"""
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            query = """
                SELECT l.log_id as id, l.access_time as created_at,
                       l.recognized_person, l.person_type,
                       l.confidence, l.access_result as status,
                       l.embedding_id
                FROM access_logs l
                WHERE 1=1
            """
            params = []
            
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
            
            if user_id:
                # Filter by recognized person name (join with residents)
                query = """
                    SELECT l.log_id as id, l.access_time as created_at,
                           l.recognized_person, l.person_type,
                           l.confidence, l.access_result as status,
                           l.embedding_id, r.full_name, r.resident_id
                    FROM access_logs l
                    LEFT JOIN face_embeddings fe ON l.embedding_id = fe.embedding_id
                    LEFT JOIN residents r ON fe.reference_id = r.resident_id
                    WHERE r.resident_id = %s
                """
                params = [user_id]
                
                if date_from:
                    query += " AND DATE(l.access_time) >= %s"
                    params.append(date_from)
                
                if date_to:
                    query += " AND DATE(l.access_time) <= %s"
                    params.append(date_to)
                
                if status:
                    query += " AND l.access_result = %s"
                    params.append(status)
            
            query += " ORDER BY l.access_time DESC LIMIT %s"
            params.append(limit)
            
            cursor.execute(query, params)
            return [dict(l) for l in cursor.fetchall()]
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
        """Get all unique users for filter dropdown"""
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            cursor.execute("""
                SELECT DISTINCT r.resident_id as id, r.full_name as username, r.full_name
                FROM access_logs l
                JOIN face_embeddings fe ON l.embedding_id = fe.embedding_id
                JOIN residents r ON fe.reference_id = r.resident_id
                WHERE l.access_result = 'granted'
                ORDER BY r.full_name
            """)
            return [dict(u) for u in cursor.fetchall()]
        finally:
            cursor.close()
            conn.close()