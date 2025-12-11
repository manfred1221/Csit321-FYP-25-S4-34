import psycopg2

# Session pooler connection
DATABASE_URL = "postgresql://postgres.hacoojohokviouocuwxx:year3fyp123Ab@aws-1-ap-northeast-2.pooler.supabase.com:5432/postgres"

try:
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    cur.execute("SELECT COUNT(*) FROM users")
    count = cur.fetchone()[0]
    print(f"✅ Connected! Found {count} users in database")
    
    cur.close()
    conn.close()
except Exception as e:
    print(f"❌ Error: {e}")