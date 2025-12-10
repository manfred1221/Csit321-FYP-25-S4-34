# backend_staff.py
# Main Flask Application - Internal Staff Backend

from flask import Flask
from flask_cors import CORS
from database import test_connection
from boundary.staff_routes import staff_bp

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Register blueprints
app.register_blueprint(staff_bp, url_prefix="/api/staff")


@app.route("/")
def home():
    """
    Health check endpoint.
    """
    return {
        "message": "Internal Staff Backend Running",
        "status": "healthy",
        "architecture": "BCE (Boundary-Control-Entity)"
    }, 200


@app.route("/api/health")
def health_check():
    """
    Check backend and database health.
    """
    db_status = "connected" if test_connection() else "disconnected"
    return {
        "backend": "running",
        "database": db_status,
        "architecture": "BCE"
    }, 200


if __name__ == "__main__":
    print("=" * 60)
    print("Internal Staff Backend - BCE Architecture")
    print("Condo Facial Recognition Access System")
    print("=" * 60)
    
    # Test database connection on startup
    print("\n🔍 Testing database connection...")
    if test_connection():
        print("✅ Database connection successful!\n")
    else:
        print("❌ Database connection failed!")
        print("⚠️  Please check your database.py configuration\n")
    
    print("🏗️  Architecture: BCE (Boundary-Control-Entity)")
    print("   📱 Boundary Layer: boundary/staff_routes.py")
    print("   🎯 Control Layer: control/staff_controller.py, etc.")
    print("   💾 Entity Layer: entity/staff_entity.py, etc.")
    
    print("\n🚀 Starting Flask server on http://localhost:5003")
    print("\n📋 Available Endpoints:")
    print("   POST   /api/staff/login                    - UC-IS01 Login")
    print("   POST   /api/staff/logout                   - Logout")
    print("   GET    /api/staff/<id>/schedule            - UC-IS02 Check Schedule")
    print("   POST   /api/staff/attendance/record        - UC-IS03 Record Attendance")
    print("   GET    /api/staff/<id>/attendance          - View Attendance History")
    print("   GET    /api/staff/<id>/profile             - UC-IS05 View Profile")
    print("   PUT    /api/staff/<id>/profile             - UC-IS04 Update Profile")
    print("   DELETE /api/staff/<id>                     - UC-IS06 Delete Account")
    print("   GET    /api/staff/<id>/total-hours         - Calculate Total Hours")
    print("=" * 60 + "\n")
    
    app.run(debug=True, port=5003, host='0.0.0.0')
