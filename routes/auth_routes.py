# routes/auth_routes.py

from flask import Blueprint, request, jsonify

auth_bp = Blueprint("auth", __name__)

# -----------------------------
# Mock data - replace with real DB later
# -----------------------------
mock_users = {
    "john_resident": {
        "user_id": 2,
        "username": "john_resident",
        "password": "password123",   # mock only
        "resident_id": 1,
        "role": "RESIDENT"
    },
    "alice_resident": {
        "user_id": 4,
        "username": "alice_resident",
        "password": "password123",
        "resident_id": 2,
        "role": "RESIDENT"
    },
}


# UC-R6 Login
@auth_bp.route("/login", methods=["POST"])
def login():
    """
    Request JSON:
      {
        "username": "john_resident",
        "password": "password123"
      }

    Success response (mock token):
      {
        "user_id": 2,
        "resident_id": 1,
        "username": "john_resident",
        "role": "RESIDENT",
        "token": "fake-token-123"
      }
    """
    data = request.get_json(silent=True) or {}

    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400

    user = mock_users.get(username)

    if not user or user["password"] != password:
        return jsonify({"error": "Invalid username or password"}), 401

    # In future generate JWT here
    token = "fake-token-123"

    return jsonify(
        {
            "user_id": user["user_id"],
            "resident_id": user["resident_id"],
            "username": user["username"],
            "role": user["role"],
            "token": token,
            "message": "Login successful (mock)",
        }
    ), 200


# UC-R7 Logout
@auth_bp.route("/logout", methods=["POST"])
def logout():
    """
    Mock logout.

    In a stateless JWT setup, frontend just discards the token.
    Later you can implement token blacklist if needed.
    """
    return jsonify({"message": "Logout successful (mock)"}), 200
