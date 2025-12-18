# routes/auth_routes.py
# REAL DATABASE VERSION - Queries Supabase users + residents tables

from flask import Blueprint, request, jsonify
from psycopg2.extras import RealDictCursor
from database import get_db_connection

auth_bp = Blueprint("auth", __name__)


# UC-R6 Login - REAL DATABASE
@auth_bp.route("/login", methods=["POST"])
def login():
    """
    Resident login with real Supabase database.
    
    Database Structure:
    - users table: user_id, username, password_hash, role_id, email, status
    - residents table: resident_id, user_id, full_name, unit_number, contact_number
    - roles table: role_id, role_name (role_id=2 is "Resident")
    
    Request JSON:
      {
        "username": "john_resident",
        "password": "password123"
      }

    Success response (200):
      {
        "user_id": 2,
        "resident_id": 1,
        "username": "john_resident",
        "role": "Resident",
        "full_name": "John Tan",
        "email": "john@condo.com",
        "unit_number": "B-12-05",
        "contact_number": "91234567",
        "token": "mock-jwt-token-2",
        "message": "Login successful"
      }
    """
    data = request.get_json(silent=True) or {}

    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Step 1: Query users table with role information
        cursor.execute("""
            SELECT 
                u.user_id,
                u.username,
                u.email,
                u.password_hash,
                u.role_id,
                u.status,
                r.role_name
            FROM users u
            JOIN roles r ON u.role_id = r.role_id
            WHERE u.username = %s
        """, (username,))
        
        user = cursor.fetchone()
        
        if not user:
            cursor.close()
            conn.close()
            return jsonify({"error": "Invalid username or password"}), 401
        
        # Step 2: Verify password (TODO: use bcrypt in production)
        if user['password_hash'] != password:
            cursor.close()
            conn.close()
            return jsonify({"error": "Invalid username or password"}), 401
        
        # Step 3: Check if user is active
        if user['status'] != 'active':
            cursor.close()
            conn.close()
            return jsonify({"error": "Account is not active"}), 401
        
        # Step 4: Check if user is a resident (role_id = 2)
        if user['role_id'] != 2:
            cursor.close()
            conn.close()
            return jsonify({"error": "Invalid user type. Please use the correct login portal."}), 401
        
        # Step 5: Get resident details from residents table using user_id
        cursor.execute("""
            SELECT 
                resident_id,
                full_name,
                unit_number,
                contact_number,
                registered_at
            FROM residents
            WHERE user_id = %s
        """, (user['user_id'],))
        
        resident = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        if not resident:
            return jsonify({"error": "Resident profile not found. Please contact administrator."}), 404
        
        # Step 6: Generate token (TODO: use JWT in production)
        token = f"mock-jwt-token-{user['user_id']}"
        
        # Step 7: Return complete user + resident data
        return jsonify({
            "user_id": user['user_id'],
            "resident_id": resident['resident_id'],  # THIS IS THE KEY FIELD!
            "username": user['username'],
            "role": user['role_name'],
            "full_name": resident['full_name'] or user['username'],
            "email": user['email'] or f"{username}@condo.com",
            "unit_number": resident['unit_number'] or "N/A",
            "contact_number": resident['contact_number'] or "N/A",
            "token": token,
            "message": "Login successful",
        }), 200
        
    except Exception as e:
        print(f"Login error: {e}")
        return jsonify({"error": "Database error occurred during login"}), 500


# UC-R7 Logout
@auth_bp.route("/logout", methods=["POST"])
def logout():
    """Resident logout"""
    return jsonify({"message": "Logout successful"}), 200


# Test database connection
@auth_bp.route("/test-db", methods=["GET"])
def test_db():
    """Test if database connection is working"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT NOW();")
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        return jsonify({
            "success": True,
            "message": "Database connection OK",
            "server_time": str(result[0])
        }), 200
        
    except Exception as e:
        return jsonify({"error": f"Database connection failed: {str(e)}"}), 500