#!/usr/bin/env python3
"""Test script để debug login"""

from db import get_db_connection
from psycopg2.extras import RealDictCursor

def test_login():
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    # Test 1: Kiểm tra user admin_user có tồn tại không
    print("=" * 50)
    print("TEST 1: Kiểm tra user admin_user")
    print("=" * 50)
    
    cursor.execute("SELECT * FROM users WHERE username = 'admin_user'")
    user = cursor.fetchone()
    
    if user:
        print(f"✓ User tồn tại!")
        print(f"  - user_id: {user['user_id']}")
        print(f"  - username: {user['username']}")
        print(f"  - email: {user['email']}")
        print(f"  - password_hash: {user['password_hash']}")
        print(f"  - role_id: {user['role_id']}")
    else:
        print("✗ User KHÔNG tồn tại!")
        return
    
    # Test 2: Kiểm tra role
    print("\n" + "=" * 50)
    print("TEST 2: Kiểm tra role")
    print("=" * 50)
    
    cursor.execute("""
        SELECT u.*, r.role_name 
        FROM users u 
        JOIN roles r ON u.role_id = r.role_id 
        WHERE u.username = 'admin_user'
    """)
    user_with_role = cursor.fetchone()
    
    if user_with_role:
        print(f"✓ Role: {user_with_role['role_name']}")
        print(f"  - Là Admin? {user_with_role['role_name'] == 'Admin'}")
    
    # Test 3: So sánh password
    print("\n" + "=" * 50)
    print("TEST 3: So sánh password")
    print("=" * 50)
    
    test_password = "hashed_pw_123"
    stored_password = user['password_hash']
    
    print(f"  - Password nhập: '{test_password}'")
    print(f"  - Password DB: '{stored_password}'")
    print(f"  - Khớp? {test_password == stored_password}")
    
    # Test 4: Test full authenticate query
    print("\n" + "=" * 50)
    print("TEST 4: Full authenticate query")
    print("=" * 50)
    
    cursor.execute("""
        SELECT u.user_id as id, u.username, u.email, u.password_hash, 
               u.role_id, r.role_name as role, u.created_at,
               res.full_name, res.unit_number, res.contact_number as phone,
               res.resident_id
        FROM users u
        JOIN roles r ON u.role_id = r.role_id
        LEFT JOIN residents res ON u.user_id = res.user_id
        WHERE u.username = 'admin_user'
    """)
    full_user = cursor.fetchone()
    
    if full_user:
        print(f"✓ Query thành công!")
        print(f"  - id: {full_user['id']}")
        print(f"  - username: {full_user['username']}")
        print(f"  - role: {full_user['role']}")
        print(f"  - password_hash: {full_user['password_hash']}")
    else:
        print("✗ Query THẤT BẠI!")
    
    cursor.close()
    conn.close()
    
    print("\n" + "=" * 50)
    print("KẾT LUẬN")
    print("=" * 50)
    print(f"Đăng nhập với:")
    print(f"  Username: admin_user")
    print(f"  Password: {stored_password}")

if __name__ == "__main__":
    test_login()