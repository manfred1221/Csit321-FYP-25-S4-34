# db.py
# Compatibility wrapper so old code that imports from `db` still works.
import os
import psycopg2


def get_db_connection():

    dbname = os.getenv("DB_NAME", "CSIT321")
    user = os.getenv("DB_USER", "postgres")
    password = os.getenv("DB_PASSWORD", "joshua1102")
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")

    conn = psycopg2.connect(
        dbname=dbname,
        user=user,
        password=password,
        host=host,
        port=port,
    )
    return conn
