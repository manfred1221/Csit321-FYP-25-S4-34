import os
from dotenv import load_dotenv
from db import get_db_connection

# Load environment variables from control/.env
env_path = os.path.join(os.path.dirname(__file__), 'control', '.env')
load_dotenv(env_path)


    # Use the project's database connection function
conn = get_db_connection()
cur = conn.cursor()

# Test connection by querying users table
cur.execute("SELECT COUNT(*) FROM users")
count = cur.fetchone()[0]

cur.close()
conn.close()