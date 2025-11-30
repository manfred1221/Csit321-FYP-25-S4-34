from flask import Blueprint, request, jsonify

# Blueprint for all resident-facing APIs
resident_bp = Blueprint("resident_bp", __name__, url_prefix="/api/resident")


# ----------------------------------------------------------------------
# UC-R1: Register Face Data
# ----------------------------------------------------------------------
@resident_bp.route("/register-face", methods=["POST"])
def register_face():
    """
    Body JSON:
    {
      "resident_id": 1,
      "image_data": "dummy_base64_image"
    }
    """
    data = request.get_json() or {}
    resident_id = data.get("resident_id")
    image_data = data.get("image_data")

    if not resident_id or not image_data:
        return jsonify({
            "error": "Missing fields",
            "required": ["resident_id", "image_data"]
        }), 400

    # MOCK behaviour – pretend we saved it
    return jsonify({
        "message": "Face data registered (mock)",
        "resident_id": resident_id,
        "stored_image_sample": image_data[:20] + "..."
    }), 201


# ----------------------------------------------------------------------
# UC-R2: View Personal Data
# ----------------------------------------------------------------------
@resident_bp.route("/<int:resident_id>", methods=["GET"])
def view_personal_data(resident_id):
    # MOCK data – later this will come from DB
    dummy_resident = {
        "resident_id": resident_id,
        "full_name": "John Tan",
        "unit_number": "B-12-05",
        "contact_number": "98765432",
        "email": "john.tan@example.com"
    }
    return jsonify(dummy_resident), 200


# ----------------------------------------------------------------------
# UC-R3: Update Personal Data
# ----------------------------------------------------------------------
@resident_bp.route("/<int:resident_id>", methods=["PUT"])
def update_personal_data(resident_id):
    data = request.get_json() or {}

    # In real version you would validate allowed fields
    updated_fields = {k: v for k, v in data.items()}

    return jsonify({
        "message": "Personal data updated (mock)",
        "resident_id": resident_id,
        "updated_fields": updated_fields
    }), 200


# ----------------------------------------------------------------------
# UC-R4: Delete Personal Data
# ----------------------------------------------------------------------
@resident_bp.route("/<int:resident_id>", methods=["DELETE"])
def delete_personal_data(resident_id):
    return jsonify({
        "message": "Resident account deleted (mock)",
        "resident_id": resident_id
    }), 200


# ----------------------------------------------------------------------
# UC-R22: View Personal Access History
# ----------------------------------------------------------------------
@resident_bp.route("/<int:resident_id>/access-history", methods=["GET"])
def view_personal_access_history(resident_id):
    history = [
        {"timestamp": "2025-11-20T09:00:00", "door": "Lobby", "result": "GRANTED"},
        {"timestamp": "2025-11-20T21:30:00", "door": "Lobby", "result": "DENIED"},
    ]
    return jsonify({
        "resident_id": resident_id,
        "records": history
    }), 200


# ----------------------------------------------------------------------
# UC-R8 & UC-R13: Create Visitor Entry (with time window)
# POST /api/resident/<resident_id>/visitors
# ----------------------------------------------------------------------
@resident_bp.route("/<int:resident_id>/visitors", methods=["POST"])
def create_visitor_entry(resident_id):
    """
    Body JSON example:
    {
      "visitor_name": "Mary Lee",
      "contact_number": "98765432",
      "visiting_unit": "B-12-05",
      "start_time": "2025-11-21T10:00:00",
      "end_time": "2025-11-21T12:00:00"
    }
    """
    data = request.get_json() or {}

    required = ["visitor_name", "contact_number", "visiting_unit",
                "start_time", "end_time"]
    missing = [f for f in required if f not in data]
    if missing:
        return jsonify({"error": "Missing fields", "missing": missing}), 400

    visitor_id = 101  # mock id

    return jsonify({
        "message": "Visitor created (mock)",
        "resident_id": resident_id,
        "visitor_id": visitor_id,
        "visitor": data
    }), 201


# ----------------------------------------------------------------------
# UC-R10 & UC-R15: View Registered Visitors / Visitor List
# GET /api/resident/<resident_id>/visitors
# ----------------------------------------------------------------------
@resident_bp.route("/<int:resident_id>/visitors", methods=["GET"])
def view_registered_visitors(resident_id):
    visitors = [
        {
            "visitor_id": 101,
            "visitor_name": "Mary Lee",
            "status": "APPROVED",
            "start_time": "2025-11-21T10:00:00",
            "end_time": "2025-11-21T12:00:00",
        },
        {
            "visitor_id": 102,
            "visitor_name": "David Ong",
            "status": "PENDING",
            "start_time": "2025-11-22T15:00:00",
            "end_time": "2025-11-22T17:00:00",
        },
    ]
    return jsonify({
        "resident_id": resident_id,
        "visitors": visitors
    }), 200


# ----------------------------------------------------------------------
# UC-R11 & UC-R16: Update Visitor Information / Details
# PUT /api/resident/<resident_id>/visitors/<visitor_id>
# ----------------------------------------------------------------------
@resident_bp.route("/<int:resident_id>/visitors/<int:visitor_id>", methods=["PUT"])
def update_visitor_information(resident_id, visitor_id):
    data = request.get_json() or {}
    return jsonify({
        "message": "Visitor information updated (mock)",
        "resident_id": resident_id,
        "visitor_id": visitor_id,
        "updated_fields": data
    }), 200


# ----------------------------------------------------------------------
# UC-R12 & UC-R17: Delete / Cancel Visitor Access
# DELETE /api/resident/<resident_id>/visitors/<visitor_id>
# ----------------------------------------------------------------------
@resident_bp.route("/<int:resident_id>/visitors/<int:visitor_id>", methods=["DELETE"])
def delete_cancel_visitor_access(resident_id, visitor_id):
    return jsonify({
        "message": "Visitor access cancelled (mock)",
        "resident_id": resident_id,
        "visitor_id": visitor_id
    }), 200


# ----------------------------------------------------------------------
# UC-R9: Set Visitor Time Period
# PUT /api/resident/<resident_id>/visitors/<visitor_id>/time-window
# ----------------------------------------------------------------------
@resident_bp.route(
    "/<int:resident_id>/visitors/<int:visitor_id>/time-window",
    methods=["PUT"]
)
def set_visitor_time_period(resident_id, visitor_id):
    data = request.get_json() or {}
    required = ["start_time", "end_time"]
    missing = [f for f in required if f not in data]
    if missing:
        return jsonify({"error": "Missing fields", "missing": missing}), 400

    return jsonify({
        "message": "Visitor time window updated (mock)",
        "resident_id": resident_id,
        "visitor_id": visitor_id,
        "start_time": data["start_time"],
        "end_time": data["end_time"]
    }), 200


# ----------------------------------------------------------------------
# UC-R14: Upload Visitor Facial Image
# POST /api/resident/<resident_id>/visitors/<visitor_id>/face-image
# ----------------------------------------------------------------------
@resident_bp.route(
    "/<int:resident_id>/visitors/<int:visitor_id>/face-image",
    methods=["POST"]
)
def upload_visitor_facial_image(resident_id, visitor_id):
    data = request.get_json() or {}
    image_data = data.get("image_data")

    if not image_data:
        return jsonify({
            "error": "Missing field",
            "required": ["image_data"]
        }), 400

    return jsonify({
        "message": "Visitor facial image stored (mock)",
        "resident_id": resident_id,
        "visitor_id": visitor_id,
        "stored_image_sample": image_data[:20] + "..."
    }), 201


# ----------------------------------------------------------------------
# UC-R23: View Visitor Access History
# GET /api/resident/<resident_id>/visitors/<visitor_id>/access-history
# ----------------------------------------------------------------------
@resident_bp.route(
    "/<int:resident_id>/visitors/<int:visitor_id>/access-history",
    methods=["GET"]
)
def view_visitor_access_history(resident_id, visitor_id):
    logs = [
        {"timestamp": "2025-11-21T10:05:00", "door": "Lobby", "result": "GRANTED"},
        {"timestamp": "2025-11-21T10:20:00", "door": "Lift Lobby", "result": "GRANTED"},
    ]
    return jsonify({
        "resident_id": resident_id,
        "visitor_id": visitor_id,
        "records": logs
    }), 200


# ----------------------------------------------------------------------
# UC-R19: Temporarily Disable Face Access
# POST /api/resident/<resident_id>/face-access/disable
# ----------------------------------------------------------------------
@resident_bp.route("/<int:resident_id>/face-access/disable", methods=["POST"])
def temporarily_disable_face_access(resident_id):
    return jsonify({
        "message": "Face access disabled temporarily (mock)",
        "resident_id": resident_id,
        "status": "DISABLED"
    }), 200


# ----------------------------------------------------------------------
# UC-R20: Receive Unauthorized Access Alert
# GET /api/resident/<resident_id>/alerts
# ----------------------------------------------------------------------
@resident_bp.route("/<int:resident_id>/alerts", methods=["GET"])
def receive_unauthorized_access_alert(resident_id):
    alerts = [
        {
            "alert_id": 1,
            "timestamp": "2025-11-20T21:30:00",
            "description": "Multiple failed face attempts at lobby door",
            "status": "UNREAD"
        }
    ]
    return jsonify({
        "resident_id": resident_id,
        "alerts": alerts
    }), 200


# ----------------------------------------------------------------------
# UC-R21: Offline Recognition Mode
# POST /api/resident/offline/recognize
# ----------------------------------------------------------------------
@resident_bp.route("/offline/recognize", methods=["POST"])
def offline_recognition_mode():
    """
    Body JSON:
    {
      "device_id": "gate-1",
      "image_data": "dummy_base64_image"
    }
    """
    data = request.get_json() or {}
    device_id = data.get("device_id")
    image_data = data.get("image_data")

    if not device_id or not image_data:
        return jsonify({
            "error": "Missing fields",
            "required": ["device_id", "image_data"]
        }), 400

    # MOCK: always recognise as resident 1
    return jsonify({
        "message": "Offline recognition successful (mock)",
        "device_id": device_id,
        "matched_resident_id": 1
    }), 200
