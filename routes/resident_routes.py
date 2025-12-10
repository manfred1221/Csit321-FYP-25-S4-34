from flask import Blueprint, request, jsonify
from datetime import datetime
from db import get_db_connection


resident_bp = Blueprint("resident_bp", __name__, url_prefix="/api/resident")


# ----------------------------------------------------------------------
# Utility helpers
# ----------------------------------------------------------------------
def parse_iso(dt_str):
    """Parse ISO datetime string safely; return None if invalid."""
    if not dt_str:
        return None
    try:
        # psycopg2 can accept ISO strings directly, but we parse to catch errors early
        return datetime.fromisoformat(dt_str)
    except ValueError:
        return None

# ----------------------------------------------------------------------
# UC-R1: Register Face Data  (DB-backed, embedding placeholder for now)
# ----------------------------------------------------------------------
@resident_bp.route("/register-face", methods=["POST"])
def register_face():
    """
    Body JSON:
    {
      "resident_id": 1,
      "image_data": "base64..."
    }

    For now we just create a row in face_embeddings with NULL embedding.
    Later your FaceNet service can update the embedding column using pgvector.
    """
    data = request.get_json() or {}
    resident_id = data.get("resident_id")
    image_data = data.get("image_data")  # not used yet, kept for future FaceNet

    if not resident_id or not image_data:
        return jsonify({
            "error": "Missing fields",
            "required": ["resident_id", "image_data"]
        }), 400

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Ensure resident exists
        cur.execute(
            "SELECT resident_id FROM residents WHERE resident_id = %s;",
            (resident_id,)
        )
        row = cur.fetchone()
        if not row:
            cur.close()
            conn.close()
            return jsonify({"error": "Resident not found"}), 404

        # Create a placeholder embedding row
        cur.execute(
            """
            INSERT INTO face_embeddings (user_type, reference_id, embedding)
            VALUES ('resident', %s, NULL)
            RETURNING embedding_id;
            """,
            (resident_id,)
        )
        embedding_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()

        return jsonify({
            "message": "Face data registered (placeholder, no embedding yet)",
            "resident_id": resident_id,
            "embedding_id": embedding_id
        }), 201

    except Exception as e:
        return jsonify({"error": "DB error while saving face data", "details": str(e)}), 500


# ----------------------------------------------------------------------
# UC-R2: View Personal Data
# ----------------------------------------------------------------------
@resident_bp.route("/<int:resident_id>", methods=["GET"])
def view_personal_data(resident_id):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT r.resident_id,
                   r.full_name,
                   r.unit_number,
                   r.contact_number,
                   r.registered_at,
                   u.email
            FROM residents r
            LEFT JOIN users u ON r.user_id = u.user_id
            WHERE r.resident_id = %s;
            """,
            (resident_id,)
        )
        row = cur.fetchone()
        cur.close()
        conn.close()

        if not row:
            return jsonify({"error": "Resident not found"}), 404

        resident = {
            "resident_id": row[0],
            "full_name": row[1],
            "unit_number": row[2],
            "contact_number": row[3],
            "registered_at": row[4].isoformat() if row[4] else None,
            "email": row[5],
        }
        return jsonify(resident), 200

    except Exception as e:
        return jsonify({"error": "DB error while reading resident", "details": str(e)}), 500


# ----------------------------------------------------------------------
# UC-R3: Update Personal Data
# ----------------------------------------------------------------------
@resident_bp.route("/<int:resident_id>", methods=["PUT"])
def update_personal_data(resident_id):
    data = request.get_json() or {}

    allowed_fields = {
        "full_name": "full_name",
        "contact_number": "contact_number",
        "unit_number": "unit_number",
    }

    sets = []
    params = []
    for json_key, col in allowed_fields.items():
        if json_key in data:
            sets.append(f"{col} = %s")
            params.append(data[json_key])

    if not sets:
        return jsonify({"error": "No updatable fields provided"}), 400

    params.append(resident_id)

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            f"""
            UPDATE residents
            SET {", ".join(sets)}
            WHERE resident_id = %s
            RETURNING resident_id;
            """,
            tuple(params)
        )
        row = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()

        if not row:
            return jsonify({"error": "Resident not found"}), 404

        return jsonify({
            "message": "Personal data updated",
            "resident_id": resident_id,
            "updated_fields": {k: v for k, v in data.items() if k in allowed_fields}
        }), 200

    except Exception as e:
        return jsonify({"error": "DB error while updating resident", "details": str(e)}), 500


# ----------------------------------------------------------------------
# UC-R4: Delete Personal Data
# ----------------------------------------------------------------------
@resident_bp.route("/<int:resident_id>", methods=["DELETE"])
def delete_personal_data(resident_id):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM residents WHERE resident_id = %s RETURNING resident_id;",
            (resident_id,)
        )
        row = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()

        if not row:
            return jsonify({"error": "Resident not found"}), 404

        return jsonify({
            "message": "Resident account deleted",
            "resident_id": resident_id
        }), 200

    except Exception as e:
        return jsonify({"error": "DB error while deleting resident", "details": str(e)}), 500


# ----------------------------------------------------------------------
# UC-R22: View Personal Access History
# ----------------------------------------------------------------------
@resident_bp.route("/<int:resident_id>/access-history", methods=["GET"])
def view_personal_access_history(resident_id):
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Look up resident name
        cur.execute(
            "SELECT full_name FROM residents WHERE resident_id = %s;",
            (resident_id,)
        )
        row = cur.fetchone()
        if not row:
            cur.close()
            conn.close()
            return jsonify({"error": "Resident not found"}), 404
        full_name = row[0]

        # Get access logs where recognized_person matches resident name
        cur.execute(
            """
            SELECT access_time,
                   person_type,
                   confidence,
                   access_result
            FROM access_logs
            WHERE person_type = 'resident' AND recognized_person = %s
            ORDER BY access_time DESC;
            """,
            (full_name,)
        )
        logs = cur.fetchall()
        cur.close()
        conn.close()

        records = [
            {
                "timestamp": r[0].isoformat() if r[0] else None,
                "person_type": r[1],
                "confidence": r[2],
                "result": r[3],
            }
            for r in logs
        ]

        return jsonify({
            "resident_id": resident_id,
            "full_name": full_name,
            "records": records
        }), 200

    except Exception as e:
        return jsonify({"error": "DB error while reading access history", "details": str(e)}), 500


# ----------------------------------------------------------------------
# UC-R8 & UC-R13: Create Visitor Entry
# ----------------------------------------------------------------------
@resident_bp.route("/<int:resident_id>/visitors", methods=["POST"])
def create_visitor_entry(resident_id):
    data = request.get_json() or {}

    required = ["visitor_name", "contact_number", "visiting_unit",
                "start_time", "end_time"]
    missing = [f for f in required if f not in data]
    if missing:
        return jsonify({"error": "Missing fields", "missing": missing}), 400

    start_ts = parse_iso(data["start_time"])
    end_ts = parse_iso(data["end_time"])
    if not start_ts or not end_ts:
        return jsonify({"error": "Invalid datetime format (use ISO 8601)"}), 400

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Ensure resident exists
        cur.execute(
            "SELECT resident_id FROM residents WHERE resident_id = %s;",
            (resident_id,)
        )
        if not cur.fetchone():
            cur.close()
            conn.close()
            return jsonify({"error": "Resident not found"}), 404

        cur.execute(
            """
            INSERT INTO visitors
                (full_name, contact_number, visiting_unit,
                 check_in, check_out, approved_by)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING visitor_id, full_name, contact_number, visiting_unit,
                      check_in, check_out, approved_by;
            """,
            (
                data["visitor_name"],
                data["contact_number"],
                data["visiting_unit"],
                start_ts,
                end_ts,
                resident_id,
            )
        )
        row = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()

        visitor = {
            "visitor_id": row[0],
            "visitor_name": row[1],
            "contact_number": row[2],
            "visiting_unit": row[3],
            "start_time": row[4].isoformat() if row[4] else None,
            "end_time": row[5].isoformat() if row[5] else None,
            "approved_by": row[6],
            "status": "APPROVED",  # logical status for frontend
        }

        return jsonify({
            "message": "Visitor created",
            "resident_id": resident_id,
            "visitor": visitor
        }), 201

    except Exception as e:
        return jsonify({"error": "DB error while creating visitor", "details": str(e)}), 500


# ----------------------------------------------------------------------
# UC-R10 & UC-R15: View Registered Visitors
# ----------------------------------------------------------------------
@resident_bp.route("/<int:resident_id>/visitors", methods=["GET"])
def view_registered_visitors(resident_id):
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            """
            SELECT visitor_id,
                   full_name,
                   contact_number,
                   visiting_unit,
                   check_in,
                   check_out
            FROM visitors
            WHERE approved_by = %s
            ORDER BY check_in DESC NULLS LAST, visitor_id DESC;
            """,
            (resident_id,)
        )
        rows = cur.fetchall()
        cur.close()
        conn.close()

        visitors = [
            {
                "visitor_id": r[0],
                "visitor_name": r[1],
                "contact_number": r[2],
                "visiting_unit": r[3],
                "start_time": r[4].isoformat() if r[4] else None,
                "end_time": r[5].isoformat() if r[5] else None,
                "status": "APPROVED" if r[4] else "PENDING",
            }
            for r in rows
        ]

        return jsonify({
            "resident_id": resident_id,
            "visitors": visitors
        }), 200

    except Exception as e:
        return jsonify({"error": "DB error while reading visitors", "details": str(e)}), 500


# ----------------------------------------------------------------------
# UC-R11 & UC-R16: Update Visitor Information
# ----------------------------------------------------------------------
@resident_bp.route("/<int:resident_id>/visitors/<int:visitor_id>", methods=["PUT"])
def update_visitor_information(resident_id, visitor_id):
    data = request.get_json() or {}

    field_map = {
        "visitor_name": "full_name",
        "contact_number": "contact_number",
        "visiting_unit": "visiting_unit",
        "start_time": "check_in",
        "end_time": "check_out",
    }

    sets = []
    params = []
    for json_key, col in field_map.items():
        if json_key in data:
            if json_key in ("start_time", "end_time"):
                ts = parse_iso(data[json_key])
                if not ts:
                    return jsonify({"error": f"Invalid datetime for {json_key}"}), 400
                params.append(ts)
            else:
                params.append(data[json_key])
            sets.append(f"{col} = %s")

    if not sets:
        return jsonify({"error": "No updatable fields provided"}), 400

    params.extend([resident_id, visitor_id])

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            f"""
            UPDATE visitors
            SET {", ".join(sets)}
            WHERE approved_by = %s AND visitor_id = %s
            RETURNING visitor_id;
            """,
            tuple(params)
        )
        row = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()

        if not row:
            return jsonify({"error": "Visitor not found for this resident"}), 404

        return jsonify({
            "message": "Visitor information updated",
            "resident_id": resident_id,
            "visitor_id": visitor_id,
            "updated_fields": {k: v for k, v in data.items() if k in field_map}
        }), 200

    except Exception as e:
        return jsonify({"error": "DB error while updating visitor", "details": str(e)}), 500


# ----------------------------------------------------------------------
# UC-R12 & UC-R17: Delete / Cancel Visitor Access
# ----------------------------------------------------------------------
@resident_bp.route("/<int:resident_id>/visitors/<int:visitor_id>", methods=["DELETE"])
def delete_cancel_visitor_access(resident_id, visitor_id):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            DELETE FROM visitors
            WHERE approved_by = %s AND visitor_id = %s
            RETURNING visitor_id;
            """,
            (resident_id, visitor_id)
        )
        row = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()

        if not row:
            return jsonify({"error": "Visitor not found for this resident"}), 404

        return jsonify({
            "message": "Visitor access cancelled",
            "resident_id": resident_id,
            "visitor_id": visitor_id
        }), 200

    except Exception as e:
        return jsonify({"error": "DB error while deleting visitor", "details": str(e)}), 500


# ----------------------------------------------------------------------
# UC-R9: Set Visitor Time Period (just updates check_in/check_out)
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

    start_ts = parse_iso(data["start_time"])
    end_ts = parse_iso(data["end_time"])
    if not start_ts or not end_ts:
        return jsonify({"error": "Invalid datetime format (use ISO 8601)"}), 400

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE visitors
            SET check_in = %s,
                check_out = %s
            WHERE approved_by = %s AND visitor_id = %s
            RETURNING visitor_id;
            """,
            (start_ts, end_ts, resident_id, visitor_id)
        )
        row = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()

        if not row:
            return jsonify({"error": "Visitor not found for this resident"}), 404

        return jsonify({
            "message": "Visitor time window updated",
            "resident_id": resident_id,
            "visitor_id": visitor_id,
            "start_time": data["start_time"],
            "end_time": data["end_time"]
        }), 200

    except Exception as e:
        return jsonify({"error": "DB error while updating time window", "details": str(e)}), 500


# ----------------------------------------------------------------------
# UC-R14: Upload Visitor Facial Image  (placeholder face_embeddings row)
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

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Ensure visitor belongs to this resident
        cur.execute(
            """
            SELECT visitor_id, full_name
            FROM visitors
            WHERE approved_by = %s AND visitor_id = %s;
            """,
            (resident_id, visitor_id)
        )
        row = cur.fetchone()
        if not row:
            cur.close()
            conn.close()
            return jsonify({"error": "Visitor not found for this resident"}), 404

        # Insert placeholder embedding row for visitor
        cur.execute(
            """
            INSERT INTO face_embeddings (user_type, reference_id, embedding)
            VALUES ('visitor', %s, NULL)
            RETURNING embedding_id;
            """,
            (visitor_id,)
        )
        embedding_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()

        return jsonify({
            "message": "Visitor facial image stored (placeholder, no embedding yet)",
            "resident_id": resident_id,
            "visitor_id": visitor_id,
            "embedding_id": embedding_id
        }), 201

    except Exception as e:
        return jsonify({"error": "DB error while saving visitor face", "details": str(e)}), 500


# ----------------------------------------------------------------------
# UC-R23: View Visitor Access History
# ----------------------------------------------------------------------
@resident_bp.route(
    "/<int:resident_id>/visitors/<int:visitor_id>/access-history",
    methods=["GET"]
)
def view_visitor_access_history(resident_id, visitor_id):
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Get visitor name (and make sure they belong to this resident)
        cur.execute(
            """
            SELECT full_name
            FROM visitors
            WHERE approved_by = %s AND visitor_id = %s;
            """,
            (resident_id, visitor_id)
        )
        row = cur.fetchone()
        if not row:
            cur.close()
            conn.close()
            return jsonify({"error": "Visitor not found for this resident"}), 404
        full_name = row[0]

        cur.execute(
            """
            SELECT access_time,
                   person_type,
                   confidence,
                   access_result
            FROM access_logs
            WHERE person_type = 'visitor' AND recognized_person = %s
            ORDER BY access_time DESC;
            """,
            (full_name,)
        )
        logs = cur.fetchall()
        cur.close()
        conn.close()

        records = [
            {
                "timestamp": r[0].isoformat() if r[0] else None,
                "person_type": r[1],
                "confidence": r[2],
                "result": r[3],
            }
            for r in logs
        ]

        return jsonify({
            "resident_id": resident_id,
            "visitor_id": visitor_id,
            "visitor_name": full_name,
            "records": records
        }), 200

    except Exception as e:
        return jsonify({"error": "DB error while reading visitor history", "details": str(e)}), 500


# ----------------------------------------------------------------------
# UC-R19 / UC-R20 / UC-R21
# Keep these mock for now (no DB columns / tables defined yet)
# ----------------------------------------------------------------------
@resident_bp.route("/<int:resident_id>/face-access/disable", methods=["POST"])
def temporarily_disable_face_access(resident_id):
    return jsonify({
        "message": "Face access disabled temporarily (mock)",
        "resident_id": resident_id,
        "status": "DISABLED"
    }), 200


@resident_bp.route("/<int:resident_id>/alerts", methods=["GET"])
def receive_unauthorized_access_alert(resident_id):
    # Still mock until you have an alerts table
    recent_time = (datetime.now()).isoformat(timespec="seconds")
    alerts = [
        {
            "alert_id": 1,
            "timestamp": recent_time,
            "description": "Multiple failed face attempts at lobby door",
            "status": "UNREAD"
        }
    ]
    return jsonify({
        "resident_id": resident_id,
        "alerts": alerts
    }), 200


@resident_bp.route("/offline/recognize", methods=["POST"])
def offline_recognition_mode():
    # You said this can stay mock for now
    data = request.get_json() or {}
    device_id = data.get("device_id")
    image_data = data.get("image_data")

    if not device_id or not image_data:
        return jsonify({
            "error": "Missing fields",
            "required": ["device_id", "image_data"]
        }), 400

    return jsonify({
        "message": "Offline recognition successful (mock)",
        "device_id": device_id,
        "matched_resident_id": 1,
        "confidence": 0.95,
        "name": "John Tan"
    }), 200
@resident_bp.route("/test-db", methods=["GET"])
def test_db():
    # Simple version with no try/except so we see real errors
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT NOW();")
    result = cur.fetchone()
    cur.close()
    conn.close()

    return jsonify({
        "db_connection": "OK",
        "server_time": str(result[0])
    }), 200



