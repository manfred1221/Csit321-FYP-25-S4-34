# database.py
<<<<<<< HEAD
# Infrastructure layer - Database connection management only

import os
=======
>>>>>>> e00f4330b54b2a5a29c75eee08ba7b7e3007c292
import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager

<<<<<<< HEAD
# Use the same URL as test_supabase_connection.py
# (you can also move it to an env var later)
DATABASE_URL = "postgresql://postgres.hacoojohokviouocuwxx:year3fyp123Ab@aws-1-ap-northeast-2.pooler.supabase.com:5432/postgres"



def get_db_connection():
    """
    Create a new database connection.
    Returns a psycopg2 connection object.
    """
    try:
        # For Supabase, passing the URL string is enough
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    except psycopg2.Error as e:
        print(f"Database connection error: {e}")
        raise


@contextmanager
def get_db_cursor(commit=False):
    """
    Context manager for database operations.
    Automatically handles connection and cursor cleanup.
    """
=======
DATABASE_URL = "postgresql://postgres.hacoojohokviouocuwxx:year3fyp123Ab@aws-1-ap-northeast-2.pooler.supabase.com:5432/postgres"

def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

@contextmanager
def get_db_cursor(commit=False):
>>>>>>> e00f4330b54b2a5a29c75eee08ba7b7e3007c292
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
<<<<<<< HEAD


def test_connection():
    """
    Test the database connection.
    Returns True if successful, False otherwise.
    """
    try:
        with get_db_cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        print("✅ Database connection successful!")
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False


if __name__ == "__main__":
    test_connection()
=======
>>>>>>> e00f4330b54b2a5a29c75eee08ba7b7e3007c292
