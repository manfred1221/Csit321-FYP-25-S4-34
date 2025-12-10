# database.py
# Infrastructure layer - Database connection management only

import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager

# Database configuration
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'CSIT321',
    'user': 'postgres',
    'password': 'Jb150611'  # CHANGE THIS to your actual PostgreSQL password
}


def get_db_connection():
    """
    Create a new database connection.
    Returns a psycopg2 connection object.
    """
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except psycopg2.Error as e:
        print(f"Database connection error: {e}")
        raise


@contextmanager
def get_db_cursor(commit=False):
    """
    Context manager for database operations.
    Automatically handles connection and cursor cleanup.
    
    Args:
        commit (bool): Whether to commit the transaction (for INSERT/UPDATE/DELETE)
    """
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        yield cursor
        if commit:
            conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cursor.close()
        conn.close()


def test_connection():
    """
    Test the database connection.
    Returns True if successful, False otherwise.
    """
    try:
        with get_db_cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            print("✅ Database connection successful!")
            return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False


if __name__ == "__main__":
    test_connection()
