# db.py
# Compatibility wrapper so old code that imports from `db` still works.
import os
import psycopg2

# db.py
# Compatibility wrapper so old code that imports from `db` still works.

from database import get_db_connection, get_db_cursor, test_connection
