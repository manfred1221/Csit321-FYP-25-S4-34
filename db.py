# db.py
import os
import psycopg2
from psycopg2.extras import RealDictCursor


def get_db_connection():

    # dbname = os.getenv("DB_NAME", "csit321_db")
    # user = os.getenv("DB_USER", "postgres")
    # password = os.getenv("DB_PASSWORD", "manfred@12")
    # host = os.getenv("DB_HOST", "localhost")
    # port = os.getenv("DB_PORT", "5432")

    dbname = os.getenv("DB_NAME", "CSIT321: Face Recognition")
    user = os.getenv("DB_USER", "postgres")
    password = os.getenv("DB_PASSWORD", "joshua1102")
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")

    # dbname = os.getenv("DB_NAME", "postgres")
    # user = os.getenv("DB_USER", "postgres.hacoojohokviouocuwxx")
    # password = os.getenv("DB_PASSWORD", "year3fyp123Ab")
    # host = os.getenv("DB_HOST", "aws-1-ap-northeast-2.pooler.supabase.com")
    # port = os.getenv("DB_PORT", "5432")



    conn = psycopg2.connect(
        dbname=dbname,
        user=user,
        password=password,
        host=host,
        port=port,
    )
    return conn
