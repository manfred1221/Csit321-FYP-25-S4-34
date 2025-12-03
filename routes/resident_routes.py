from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta

from db import get_db_connection

# Blueprint for all resident-facing APIs
resident_bp = Blueprint("resident_bp", __name__, url_prefix="/api/resident")


# ----------------------------------------------------------------------
# Small helpers
# ----------------------------------------------------------------------
def _get_resident_by_id(resident_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT r.resident_id,
               r.full_name,
               r.unit_number,
               r.contact_number,
               r.user_id,
               u.email
        FROM residents r
        LEFT JOIN users u ON r.user_id = u.user_id
        WHERE r.resident_id = %s
        """,
        (resident_id,),
    )
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row


def _get_resident_name(resident_id):
    resident = _get_resident_by_id(resident_id)
    return resident["full_name"] if resident else None


# ----------------------------------------------------------------------
# UC-R1: Register Face Data
# (DB integration will be completed after pgvector + face table exist)
# ----------------------------------------------------------------------
@resident_bp.route("/register-face", methods=["POST"])
def register_face():
    """
    Body JSON:
    {
      "resident_id": 1,
      "image_data": "dummy_base64_image"
    }

    For now:
    - validates the request
    - confirms that resident exists in DB
    - returns success without storing the image
      (face embeddings will be stored once pgvector table is ready)
    """
    data = request.get_json() or {}
    resident_id = data.get("resident_id")
    image_data = data.get("image_data")

    if not resident_id or not image_data:
        return jsonify(
            {
                "error": "Missing fields",
                "required": ["resident_id", "image_data"],
            }
        ), 400

    resident = _get_resident_by_id(resident_id)
    if not resident:
        return jsonify({"error": "Resident not found"}), 404

    return jsonify(
        {
            "message": "Face data received (stored on device / to be linked with pgvector later)",
            "resident_id": resident_id,
            "resident_name": resident["full_name"],
            "stored_image_sample": image_data[:20] + "...",
        }
    ), 201


# ----------------------------------------------------------------------
# UC-R2: View Personal Data
# GET /api/resident/<resident_id>
# ----------------------------------------------------------------------
@resident_bp.route("/<int:resident_id>", methods=["GET"])
def view_personal_data(resident_id):
    resident = _get_resident_by_id(resident_id)
    if not resident:
        return jsonify({"error": "Resident not found"}), 404

    return jsonify(
        {
            "resident_id": resident["resident_id"],
            "full_name": resident["full_name"],
            "unit_number": resident["unit_number"],
            "contact_number": resident["contact_number"],
            "email": resident["email"],
            "user_id": resident["user_id"],
        }
    ), 200


# ----------------------------------------------------------------------
# UC-R3: Update Personal Data
# PUT /api/resident/<resident_id>
# ----------------------------------------------------------------------
@resident_bp.route("/<int:resident_id>", methods=["PUT"])
def update_personal_data(resident_id):
    data = request.get_json() or {}

    allowed_fields = {"full_name", "unit_number", "contact_number"}
    updates = {k: v for k, v in data.items() if k in allowed_fields}

    if not updates:
        return jsonify({"error": "No valid fields to update"}), 400

    set_clauses = []
    values = []
    for idx, (field, value) in enumerate(updates.items(), start=1):
        set_clauses.append(f"{field} = %s")
        values.append(value)
    values.append(resident_id)

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        f"""
        UPDATE residents
        SET {", ".join(set_clauses)}
        WHERE resident_id = %s
        RETURNING resident_id
        """,
        tuple(values),
    )
    row = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()

    if not row:
        return jsonify({"error": "Resident not found"}), 404

    updated = _get_resident_by_id(resident_id)
    return jsonify(
        {
            "message": "Personal data updated",
            "resident": {
                "resident_id": updated["resident_id"],
                "full_name": updated["full_name"],
                "unit_number": updated["unit_number"],
                "contact_number": updated["contact_number"],
                "email": updated["email"],
            },
        }
    ), 200


# ----------------------------------------------------------------------
# UC-R4: Delete Personal Data
# For this system, deleting the user account will cascade.
# ----------------------------------------------------------------------
@resident_bp.route("/<int:resident_id>", methods=["DELETE"])
def delete_personal_data(resident_id):
    # Get user_id for this resident
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT user_id FROM residents WHERE resident_id = %s", (resident_id,)
    )
    row = cur.fetchone()

    if not row:
        cur.close()
        conn.close()
        return jsonify({"error": "Resident not found"}), 404

    user_id = row["user_id"]

    # Delete user, which cascades to residents (ON DELETE CASCADE)
    cur.execute("DELETE FROM users WHERE user_id = %s RETURNING user_id", (user_id,))
    deleted = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()

    if not deleted:
        return jsonify({"error": "User not deleted"}), 500

    return jsonify(
        {
            "message": "Resident account deleted",
            "resident_id": resident_id,
            "user_id": user_id,
        }
    ), 200


# ----------------------------------------------------------------------
# UC-R22: View Personal Access History
# Uses access_logs table
# ----------------------------------------------------------------------
@resident_bp.route("/<int:resident_id>/access-history", methods=["GET"])
def view_personal_access_history(resident_id):
    full_name = _get_resident_name(resident_id)
    if not full_name:
        return jsonify({"error": "Resident not found"}), 404

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT access_time,
               access_result,
               confidence,
               person_type,
               recognized_person
        FROM access_logs
        WHERE person_type = 'resident'
          AND recognized_person = %s
        ORDER BY access_time DESC
        LIMIT 50
        """,
        (full_name,),
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()

    records = [
        {
            "timestamp": r["access_time"].isoformat()
            if isinstance(r["access_time"], datetime)
            else r["access_time"],
            "door": None,  # door column not in current schema
            "result": r["access_result"],
            "confidence": r["confidence"],
        }
        for r in rows
    ]

    return jsonify({"resident_id": resident_id, "records": records}), 200


# ----------------------------------------------------------------------
# UC-R8 & UC-R13: Create Visitor Entry
# POST /api/resident/<resident_id>/visitors
# ----------------------------------------------------------------------
@resident_bp.route("/<int:resident_id>/visitors", methods=["POST"])
def create_visitor_entry(resident_id):
    data = request.get_json() or {}

    required = [
        "visitor_name",
        "contact_number",
        "visiting_unit",
        "start_time",
        "end_time",
    ]
    missing = [f for f in required if f not in data]
    if missing:
        return jsonify({"error": "Missing fields", "missing": missing}), 400

    try:
        start_time = datetime.fromisoformat(data["start_time"])
        end_time = datetime.fromisoformat(data["end_time"])
    except ValueError:
        return jsonify({"error": "Invalid datetime format"}), 400

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO visitors (full_name, contact_number, visiting_unit,
                              check_in, check_out, approved_by)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING visitor_id, full_name, contact_number,
                  visiting_unit, check_in, check_out, approved_by
        """,
        (
            data["visitor_name"],
            data["contact_number"],
            data["visiting_unit"],
            start_time,
            end_time,
            resident_id,
        ),
    )
    row = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()

    visitor = {
        "visitor_id": row["visitor_id"],
        "visitor_name": row["full_name"],
        "contact_number": row["contact_number"],
        "visiting_unit": row["visiting_unit"],
        "start_time": row["check_in"].isoformat()
        if isinstance(row["check_in"], datetime)
        else row["check_in"],
        "end_time": row["check_out"].isoformat()
        if isinstance(row["check_out"], datetime)
        else row["check_out"],
        "status": "APPROVED",
    }

    return jsonify(
        {
            "message": "Visitor created",
            "resident_id": resident_id,
            "visitor": visitor,
        }
    ), 201


# ----------------------------------------------------------------------
# UC-R10 & UC-R15: View Registered Visitors
# GET /api/resident/<resident_id>/visitors
# ----------------------------------------------------------------------
@resident_bp.route("/<int:resident_id>/visitors", methods=["GET"])
def view_registered_visitors(resident_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT visitor_id, full_name, contact_number,
               visiting_unit, check_in, check_out, approved_by
        FROM visitors
        WHERE approved_by = %s
        ORDER BY check_in NULLS LAST, visitor_id
        """,
        (resident_id,),
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()

    visitors = []
    now = datetime.now()
    for r in rows:
        check_in = r["check_in"]
        check_out = r["check_out"]

        if check_in is None:
            status = "PENDING"
        elif check_out is None or check_out > now:
            status = "ACTIVE"
        else:
            status = "EXPIRED"

        visitors.append(
            {
                "visitor_id": r["visitor_id"],
                "visitor_name": r["full_name"],
                "contact_number": r["contact_number"],
                "visiting_unit": r["visiting_unit"],
                "start_time": check_in.isoformat()
                if isinstance(check_in, datetime)
                else check_in,
                "end_time": check_out.isoformat()
                if isinstance(check_out, datetime)
                else check_out,
                "status": status,
            }
        )

    return jsonify({"resident_id": resident_id, "visitors": visitors}), 200


# ----------------------------------------------------------------------
# UC-R11 & UC-R16: Update Visitor Information
# PUT /api/resident/<resident_id>/visitors/<visitor_id>
# ----------------------------------------------------------------------
@resident_bp.route("/<int:resident_id>/visitors/<int:visitor_id>", methods=["PUT"])
def update_visitor_information(resident_id, visitor_id):
    data = request.get_json() or {}

    allowed_fields = {
        "visitor_name": "full_name",
        "contact_number": "contact_number",
        "visiting_unit": "visiting_unit",
        "start_time": "check_in",
        "end_time": "check_out",
    }

    updates = {}
    for key, column in allowed_fields.items():
        if key in data:
            if key in ("start_time", "end_time"):
                try:
                    updates[column] = datetime.fromisoformat(data[key])
                except ValueError:
                    return jsonify({"error": f"Invalid datetime for {key}"}), 400
            else:
                updates[column] = data[key]

    if not updates:
        return jsonify({"error": "No valid fields to update"}), 400

    set_clauses = []
    values = []
    for col, val in updates.items():
        set_clauses.append(f"{col} = %s")
        values.append(val)
    values.extend([resident_id, visitor_id])

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        f"""
        UPDATE visitors
        SET {", ".join(set_clauses)}
        WHERE approved_by = %s AND visitor_id = %s
        RETURNING visitor_id
        """,
        tuple(values),
    )
    row = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()

    if not row:
        return jsonify({"error": "Visitor not found for this resident"}), 404

    return jsonify(
        {
            "message": "Visitor information updated",
            "resident_id": resident_id,
            "visitor_id": visitor_id,
            "updated_fields": data,
        }
    ), 200


# ----------------------------------------------------------------------
# UC-R12 & UC-R17: Delete / Cancel Visitor Access
# DELETE /api/resident/<resident_id>/visitors/<visitor_id>
# ----------------------------------------------------------------------
@resident_bp.route("/<int:resident_id>/visitors/<int:visitor_id>", methods=["DELETE"])
def delete_cancel_visitor_access(resident_id, visitor_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        DELETE FROM visitors
        WHERE approved_by = %s AND visitor_id = %s
        RETURNING visitor_id
        """,
        (resident_id, visitor_id),
    )
    row = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()

    if not row:
        return jsonify({"error": "Visitor not found for this resident"}), 404

    return jsonify(
        {
            "message": "Visitor access cancelled",
            "resident_id": resident_id,
            "visitor_id": visitor_id,
        }
    ), 200


# ----------------------------------------------------------------------
# UC-R9: Set Visitor Time Period
# PUT /api/resident/<resident_id>/visitors/<visitor_id>/time-window
# ----------------------------------------------------------------------
@resident_bp.route(
    "/<int:resident_id>/visitors/<int:visitor_id>/time-window", methods=["PUT"]
)
def set_visitor_time_period(resident_id, visitor_id):
    data = request.get_json() or {}
    required = ["start_time", "end_time"]
    missing = [f for f in required if f not in data]
    if missing:
        return jsonify({"error": "Missing fields", "missing": missing}), 400

    try:
        start_time = datetime.fromisoformat(data["start_time"])
        end_time = datetime.fromisoformat(data["end_time"])
    except ValueError:
        return jsonify({"error": "Invalid datetime format"}), 400

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE visitors
        SET check_in = %s,
            check_out = %s
        WHERE approved_by = %s AND visitor_id = %s
        RETURNING visitor_id
        """,
        (start_time, end_time, resident_id, visitor_id),
    )
    row = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()

    if not row:
        return jsonify({"error": "Visitor not found for this resident"}), 404

    return jsonify(
        {
            "message": "Visitor time window updated",
            "resident_id": resident_id,
            "visitor_id": visitor_id,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
        }
    ), 200


# ----------------------------------------------------------------------
# UC-R14: Upload Visitor Facial Image
# (will connect to face embeddings later)
# ----------------------------------------------------------------------
@resident_bp.route(
    "/<int:resident_id>/visitors/<int:visitor_id>/face-image", methods=["POST"]
)
def upload_visitor_facial_image(resident_id, visitor_id):
    data = request.get_json() or {}
    image_data = data.get("image_data")

    if not image_data:
        return jsonify({"error": "Missing field", "required": ["image_data"]}), 400

    # TODO: when face_embeddings table is ready, store the embedding here.
    return jsonify(
        {
            "message": "Visitor facial image received (to be linked with recognition pipeline)",
            "resident_id": resident_id,
            "visitor_id": visitor_id,
            "stored_image_sample": image_data[:20] + "...",
        }
    ), 201


# ----------------------------------------------------------------------
# UC-R23: View Visitor Access History
# GET /api/resident/<resident_id>/visitors/<visitor_id>/access-history
# ----------------------------------------------------------------------
@resident_bp.route(
    "/<int:resident_id>/visitors/<int:visitor_id>/access-history", methods=["GET"]
)
def view_visitor_access_history(resident_id, visitor_id):
    # find visitor name
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT full_name
        FROM visitors
        WHERE visitor_id = %s AND approved_by = %s
        """,
        (visitor_id, resident_id),
    )
    row = cur.fetchone()
    if not row:
        cur.close()
        conn.close()
        return jsonify({"error": "Visitor not found for this resident"}), 404

    visitor_name = row["full_name"]

    cur.execute(
        """
        SELECT access_time,
               access_result,
               confidence,
               recognized_person
        FROM access_logs
        WHERE person_type = 'visitor'
          AND recognized_person = %s
        ORDER BY access_time DESC
        LIMIT 50
        """,
        (visitor_name,),
    )
    logs = cur.fetchall()
    cur.close()
    conn.close()

    records = [
        {
            "timestamp": l["access_time"].isoformat()
            if isinstance(l["access_time"], datetime)
            else l["access_time"],
            "result": l["access_result"],
            "confidence": l["confidence"],
        }
        for l in logs
    ]

    return jsonify(
        {
            "resident_id": resident_id,
            "visitor_id": visitor_id,
            "visitor_name": visitor_name,
            "records": records,
        }
    ), 200


# ----------------------------------------------------------------------
# UC-R19: Temporarily Disable Face Access
# (no dedicated DB structure yet, kept as mock)
# ----------------------------------------------------------------------
@resident_bp.route("/<int:resident_id>/face-access/disable", methods=["POST"])
def temporarily_disable_face_access(resident_id):
    return jsonify(
        {
            "message": "Face access disabled temporarily (demo only)",
            "resident_id": resident_id,
            "status": "DISABLED",
        }
    ), 200


# ----------------------------------------------------------------------
# UC-R20: Receive Unauthorized Access Alert
# (requires an alerts table – mock for now)
# ----------------------------------------------------------------------
@resident_bp.route("/<int:resident_id>/alerts", methods=["GET"])
def receive_unauthorized_access_alert(resident_id):
    recent_time = (datetime.now() - timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%S")

    alerts = [
        {
            "alert_id": 1,
            "timestamp": recent_time,
            "description": "Multiple failed face attempts at lobby door",
            "status": "UNREAD",
        },
        {
            "alert_id": 2,
            "timestamp": (datetime.now() - timedelta(days=1)).strftime(
                "%Y-%m-%dT21:30:00"
            ),
            "description": "Unauthorized access attempt at parking gate",
            "status": "READ",
        },
    ]
    return jsonify({"resident_id": resident_id, "alerts": alerts}), 200


# ----------------------------------------------------------------------
# UC-R21: Offline Recognition Mode
# (edge device feature – mock logic)
# ----------------------------------------------------------------------
@resident_bp.route("/offline/recognize", methods=["POST"])
def offline_recognition_mode():
    data = request.get_json() or {}
    device_id = data.get("device_id")
    image_data = data.get("image_data")

    if not device_id or not image_data:
        return jsonify(
            {
                "error": "Missing fields",
                "required": ["device_id", "image_data"],
            }
        ), 400

    # TODO: connect to offline recognition pipeline later.
    return jsonify(
        {
            "message": "Offline recognition successful (demo)",
            "device_id": device_id,
            "matched_resident_id": 1,
            "confidence": 0.95,
            "name": "John Tan",
        }
    ), 200
from db import get_db_connection   # make sure this import is near the top

@resident_bp.route("/test-db", methods=["GET"])
def test_db():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT NOW();")
        row = cur.fetchone()
        cur.close()
        conn.close()

        # row can be a dict (RealDictCursor) or a tuple – handle both safely
        if isinstance(row, dict):
            server_time = row.get("now") or next(iter(row.values()))
        else:
            server_time = row[0]  # tuple/list

        return jsonify({
            "db_connection": "OK",
            "server_time": str(server_time)
        }), 200

    except Exception as e:
        # print full traceback to your terminal so we can debug if needed
        import traceback
        traceback.print_exc()

        return jsonify({
            "db_error": repr(e)
        }), 500
