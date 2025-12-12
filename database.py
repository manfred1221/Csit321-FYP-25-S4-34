# database.py
import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager

DATABASE_URL = "postgresql://postgres.hacoojohokviouocuwxx:year3fyp123Ab@aws-1-ap-northeast-2.pooler.supabase.com:5432/postgres"

def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

@contextmanager
def get_db_cursor(commit=False):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        yield cursor
        if commit:
            conn.commit()
    except:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()
