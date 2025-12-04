from psycopg2.extras import RealDictCursor
from database import get_conn, return_conn

class AccessLog:
    @staticmethod
    def create(user_id, status, confidence=None, access_point='Main Gate', access_type='entry'):
        conn = get_conn()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO access_logs (user_id, status, confidence, access_point, access_type)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
            """, (user_id, status, confidence, access_point, access_type))
            log_id = cursor.fetchone()[0]
            conn.commit()
            return log_id
        finally:
            cursor.close()
            return_conn(conn)
    
    @staticmethod
    def get_recent(limit=100):
        conn = get_conn()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            cursor.execute("""
                SELECT l.*, u.username, u.full_name, u.role
                FROM access_logs l
                LEFT JOIN users u ON l.user_id = u.id
                ORDER BY l.created_at DESC
                LIMIT %s
            """, (limit,))
            return [dict(l) for l in cursor.fetchall()]
        finally:
            cursor.close()
            return_conn(conn)
    
    @staticmethod
    def filter_logs(user_id=None, date_from=None, date_to=None, status=None, access_type=None, limit=500):
        conn = get_conn()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            query = """
                SELECT l.*, u.username, u.full_name, u.role
                FROM access_logs l
                LEFT JOIN users u ON l.user_id = u.id
                WHERE 1=1
            """
            params = []
            
            if user_id:
                query += " AND l.user_id = %s"
                params.append(user_id)
            
            if date_from:
                query += " AND DATE(l.created_at) >= %s"
                params.append(date_from)
            
            if date_to:
                query += " AND DATE(l.created_at) <= %s"
                params.append(date_to)
            
            if status:
                query += " AND l.status = %s"
                params.append(status)
            
            if access_type:
                query += " AND l.access_type = %s"
                params.append(access_type)
            
            query += " ORDER BY l.created_at DESC LIMIT %s"
            params.append(limit)
            
            cursor.execute(query, params)
            return [dict(l) for l in cursor.fetchall()]
        finally:
            cursor.close()
            return_conn(conn)
    
    @staticmethod
    def get_by_user(user_id, limit=100):
        conn = get_conn()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            cursor.execute("""
                SELECT l.*, u.username, u.full_name, u.role
                FROM access_logs l
                LEFT JOIN users u ON l.user_id = u.id
                WHERE l.user_id = %s
                ORDER BY l.created_at DESC
                LIMIT %s
            """, (user_id, limit))
            return [dict(l) for l in cursor.fetchall()]
        finally:
            cursor.close()
            return_conn(conn)
    
    @staticmethod
    def get_by_date_range(date_from, date_to, limit=500):
        conn = get_conn()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            cursor.execute("""
                SELECT l.*, u.username, u.full_name, u.role
                FROM access_logs l
                LEFT JOIN users u ON l.user_id = u.id
                WHERE DATE(l.created_at) >= %s AND DATE(l.created_at) <= %s
                ORDER BY l.created_at DESC
                LIMIT %s
            """, (date_from, date_to, limit))
            return [dict(l) for l in cursor.fetchall()]
        finally:
            cursor.close()
            return_conn(conn)
    
    @staticmethod
    def get_today():
        conn = get_conn()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            cursor.execute("""
                SELECT l.*, u.username, u.full_name
                FROM access_logs l
                LEFT JOIN users u ON l.user_id = u.id
                WHERE DATE(l.created_at) = CURRENT_DATE
                ORDER BY l.created_at DESC
            """)
            return [dict(l) for l in cursor.fetchall()]
        finally:
            cursor.close()
            return_conn(conn)
    
    @staticmethod
    def get_stats(days=30):
        conn = get_conn()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE status = 'granted') as granted,
                    COUNT(*) FILTER (WHERE status = 'denied') as denied,
                    COUNT(DISTINCT user_id) as unique_users
                FROM access_logs
                WHERE created_at >= CURRENT_TIMESTAMP - INTERVAL '%s days'
            """, (days,))
            return dict(cursor.fetchone())
        finally:
            cursor.close()
            return_conn(conn)
    
    @staticmethod
    def get_all_users_for_filter():
        conn = get_conn()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            cursor.execute("""
                SELECT DISTINCT u.id, u.username, u.full_name
                FROM access_logs l
                JOIN users u ON l.user_id = u.id
                ORDER BY u.full_name
            """)
            return [dict(u) for u in cursor.fetchall()]
        finally:
            cursor.close()
            return_conn(conn)
