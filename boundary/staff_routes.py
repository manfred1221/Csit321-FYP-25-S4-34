# boundary/staff_routes.py
# Boundary Layer - HTTP interface for staff operations

from flask import Blueprint, request, jsonify
from control.staff_controller import StaffController
from control.schedule_controller import ScheduleController
from control.attendance_controller import AttendanceController

# Create Blueprint
staff_bp = Blueprint("staff_bp", __name__)


# ----------------------------------------------------------------------
# UC-IS01: Login to System
# ----------------------------------------------------------------------
@staff_bp.route("/login", methods=["POST"])
def login():
    """
    Staff login endpoint.
    Delegates to StaffController for business logic.
    """
    try:
        data = request.get_json(silent=True) or {}
        username = data.get("username")
        password = data.get("password")
        
        # Delegate to controller
        result = StaffController.login(username, password)
        return jsonify(result), 200
        
    except ValueError as e:
        return jsonify({"error": str(e)}), 401
    except Exception as e:
        print(f"Login error: {e}")
        return jsonify({"error": "Login failed", "details": str(e)}), 500


# ----------------------------------------------------------------------
# UC-IS07: Logout
# ----------------------------------------------------------------------
@staff_bp.route("/logout", methods=["POST"])
def logout():
    """
    Staff logout endpoint.
    """
    try:
        result = StaffController.logout()
        return jsonify(result), 200
    except Exception as e:
        print(f"Logout error: {e}")
        return jsonify({"error": "Logout failed"}), 500


# ----------------------------------------------------------------------
# UC-IS02: Check Schedule
# ----------------------------------------------------------------------
@staff_bp.route("/<int:staff_id>/schedule", methods=["GET"])
def get_schedule(staff_id):
    """
    Get staff work schedule.
    Query parameters: start_date, end_date (optional)
    """
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        # Delegate to controller
        result = ScheduleController.get_staff_schedule(staff_id, start_date, end_date)
        return jsonify(result), 200
        
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        print(f"Get schedule error: {e}")
        return jsonify({"error": "Failed to retrieve schedule", "details": str(e)}), 500


# ----------------------------------------------------------------------
# UC-IS03: Automatic Attendance Recording
# ----------------------------------------------------------------------
@staff_bp.route("/attendance/record", methods=["POST"])
def record_attendance():
    """
    Record staff attendance (entry or exit).
    
    Body JSON:
    {
      "staff_id": 1,  // Optional if face_embedding provided
      "face_embedding": [0.1, 0.2, ...],  // Optional if staff_id provided
      "action": "entry" or "exit",
      "confidence": 0.98,
      "location": "Staff Entrance"
    }
    """
    try:
        data = request.get_json() or {}
        staff_id = data.get("staff_id")
        face_embedding = data.get("face_embedding")
        action = data.get("action")
        confidence = data.get("confidence", 0.0)
        location = data.get("location", "Unknown")
        
        # Validate action
        if not action or action not in ['entry', 'exit']:
            return jsonify({
                "error": "Invalid action",
                "valid_values": ["entry", "exit"]
            }), 400
        
        # Delegate to controller based on action
        if action == 'entry':
            result = AttendanceController.record_entry(
                staff_id, face_embedding, confidence, location
            )
            return jsonify(result), 201
        else:  # exit
            result = AttendanceController.record_exit(
                staff_id, face_embedding, confidence, location
            )
            return jsonify(result), 200
            
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        print(f"Record attendance error: {e}")
        return jsonify({"error": "Failed to record attendance", "details": str(e)}), 500


# ----------------------------------------------------------------------
# View Attendance History
# ----------------------------------------------------------------------
@staff_bp.route("/<int:staff_id>/attendance", methods=["GET"])
def get_attendance_history(staff_id):
    """
    Get staff attendance history.
    Query parameters: start_date, end_date (optional)
    """
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        # Delegate to controller
        result = AttendanceController.get_attendance_history(staff_id, start_date, end_date)
        return jsonify(result), 200
        
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        print(f"Get attendance history error: {e}")
        return jsonify({"error": "Failed to retrieve attendance", "details": str(e)}), 500


# ----------------------------------------------------------------------
# UC-IS05: View Personal Profile
# ----------------------------------------------------------------------
@staff_bp.route("/<int:staff_id>/profile", methods=["GET"])
def get_profile(staff_id):
    """
    Get staff personal profile.
    """
    try:
        # Delegate to controller
        result = StaffController.get_profile(staff_id)
        return jsonify(result), 200
        
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        print(f"Get profile error: {e}")
        return jsonify({"error": "Failed to retrieve profile", "details": str(e)}), 500


# ----------------------------------------------------------------------
# UC-IS04: Update Personal Information
# ----------------------------------------------------------------------
@staff_bp.route("/<int:staff_id>/profile", methods=["PUT"])
def update_profile(staff_id):
    """
    Update staff personal information.
    
    Body JSON:
    {
      "full_name": "John Smith Jr.",
      "contact_number": "012-9876543",
      "position": "Senior Security Guard"
    }
    """
    try:
        data = request.get_json() or {}
        
        # Delegate to controller
        result = StaffController.update_profile(staff_id, data)
        return jsonify(result), 200
        
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        print(f"Update profile error: {e}")
        return jsonify({"error": "Failed to update profile", "details": str(e)}), 500


# ----------------------------------------------------------------------
# UC-IS06: Delete Personal Information
# ----------------------------------------------------------------------
@staff_bp.route("/<int:staff_id>", methods=["DELETE"])
def delete_account(staff_id):
    """
    Delete staff account (soft delete).
    """
    try:
        # Delegate to controller
        result = StaffController.delete_account(staff_id)
        return jsonify(result), 200
        
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        print(f"Delete account error: {e}")
        return jsonify({"error": "Failed to delete account", "details": str(e)}), 500


# ----------------------------------------------------------------------
# UC-IS08: Enroll Face Data
# ----------------------------------------------------------------------
@staff_bp.route("/enroll-face", methods=["POST"])
def enroll_face():
    """
    Staff face enrollment endpoint.
    Accepts staff_id and image_data (base64), stores face embedding in database.
    Currently stores placeholder (NULL embedding) - will integrate FaceNet later.
    
    Body JSON:
    {
      "staff_id": 1,
      "image_data": "data:image/jpeg;base64,/9j/4AAQ..."
    }
    """
    try:
        from database import get_db_connection
        from datetime import datetime
        
        data = request.get_json(silent=True) or {}
        staff_id = data.get("staff_id")
        image_data = data.get("image_data")

        if not staff_id or not image_data:
            return jsonify({
                "error": "Missing fields",
                "required": ["staff_id", "image_data"]
            }), 400

        conn = get_db_connection()
        cur = conn.cursor()

        # Verify staff exists
        cur.execute("SELECT staff_id, full_name FROM staff WHERE staff_id = %s;", (staff_id,))
        staff_row = cur.fetchone()
        if not staff_row:
            cur.close()
            conn.close()
            return jsonify({"error": "Staff member not found"}), 404

        # Generate filename for the image
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        image_filename = f"staff_{staff_id}_{timestamp}.jpg"

        # TODO: In the future, process image_data with FaceNet here
        # and generate the actual embedding vector instead of NULL
        
        # Insert face embedding record
        cur.execute(
            """
            INSERT INTO face_embeddings (user_type, reference_id, embedding, image_filename)
            VALUES ('staff', %s, NULL, %s)
            RETURNING embedding_id;
            """,
            (staff_id, image_filename)
        )
        embedding_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()

        return jsonify({
            "success": True,
            "message": "Face enrolled successfully",
            "staff_id": staff_id,
            "embedding_id": embedding_id,
            "image_filename": image_filename
        }), 201

    except Exception as e:
        print(f"Enroll face error: {e}")
        return jsonify({"error": "Failed to enroll face", "details": str(e)}), 500


# ----------------------------------------------------------------------
# Additional Endpoints (Optional)
# ----------------------------------------------------------------------

@staff_bp.route("/<int:staff_id>/total-hours", methods=["GET"])
def get_total_hours(staff_id):
    """
    Calculate total hours worked in a period.
    Query parameters: start_date (required), end_date (required)
    """
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        if not start_date or not end_date:
            return jsonify({
                "error": "Missing required parameters",
                "required": ["start_date", "end_date"]
            }), 400
        
        # Delegate to controller
        result = AttendanceController.get_total_hours_worked(staff_id, start_date, end_date)
        return jsonify(result), 200
        
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        print(f"Get total hours error: {e}")
        return jsonify({"error": "Failed to calculate total hours", "details": str(e)}), 500