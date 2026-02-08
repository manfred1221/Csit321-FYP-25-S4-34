from flask import Blueprint, request, jsonify
from datetime import datetime
from psycopg2.extras import RealDictCursor
from database import get_db_connection

import numpy as np

# ✅ Remote ML embedding (Cloud Run)
from ml_client import get_embedding as get_remote_embedding

resident_bp = Blueprint("resident_bp", __name__, url_prefix="/api/resident")


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------
def parse_iso(dt_str):
    if not dt_str:
        return None
    try:
        return datetime.fromisoformat(dt_str)
    except ValueError:
        return None


def _get_resident_id_by_user_id(user_id: int):
    """
    If your frontend/login stores user_id, but your resident features need resident_id,
    this resolves it using the residents table.
    """
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT resident_id FROM residents WHERE user_id = %s", (user_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row["resident_id"] if row else None


def _json_error(msg, status=400, details=None):
    payload = {"error": msg}
    if details is not None:
        payload["details"] = str(details)
    return jsonify(payload), status


def _normalize_embedding(emb_list):
    """
    Normalize embedding to unit length for stable cosine similarity.
    Store as list[float] for pgvector.
    """
    v = np.array(emb_list, dtype=np.float32)
    norm = float(np.linalg.norm(v))
    if norm == 0.0:
        return v.tolist()
    return (v / norm).tolist()


# ----------------------------------------------------------------------
# UC-R1: Register Face Data (REMOTE embedding)
# ----------------------------------------------------------------------
@resident_bp.route("/register-face", methods=["POST"])
def register_face():
    data = request.get_json(silent=True) or {}
    resident_id = data.get("resident_id")
    image_data = data.get("image_data")

    if not resident_id or not image_data:
        return _json_error("Missing fields", 400, {"required": ["resident_id", "image_data"]})

    # ✅ Generate embedding from Cloud Run ML (expects base64 or dataURL)
    emb = get_remote_embedding(image_data)
    if emb is None:
        return _json_error("No face detected. Please center your face and try again.", 400)

    embedding = _normalize_embedding(emb)

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Ensure resident exists
        cur.execute("SELECT resident_id FROM residents WHERE resident_id = %s;", (resident_id,))
        if not cur.fetchone():
            cur.close()
            conn.close()
            return _json_error("Resident not found", 404)

        # Keep only ONE embedding per resident (recommended)
        cur.execute(
            """
            DELETE FROM face_embeddings
            WHERE user_type = 'resident' AND reference_id = %s;
            """,
            (resident_id,)
        )

        # Insert new embedding (pgvector accepts python list)
        cur.execute(
            """
            INSERT INTO face_embeddings (user_type, reference_id, embedding, created_at)
            VALUES ('resident', %s, %s, NOW())
            RETURNING embedding_id;
            """,
            (resident_id, embedding)
        )

        embedding_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()

        return jsonify({
            "success": True,
            "message": "Face embedding registered successfully",
            "resident_id": resident_id,
            "embedding_id": embedding_id
        }), 201

    except Exception as e:
        return _json_error("DB error while saving face embedding", 500, e)


# ----------------------------------------------------------------------
# UC-R2: View Personal Data
# ----------------------------------------------------------------------
@resident_bp.route("/<int:resident_id>", methods=["GET"])
def view_personal_data(resident_id):
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute(
            """
            SELECT r.resident_id,
                   r.full_name,
                   r.unit_number,
                   r.contact_number,
                   r.registered_at,
                   u.email,
                   r.user_id
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
            return _json_error("Resident not found", 404)

        if row.get("registered_at"):
            row["registered_at"] = row["registered_at"].isoformat()

        # Return fields at top level (apiCall already wraps in {success, data})
        row["success"] = True
        return jsonify(row), 200

    except Exception as e:
        return _json_error("DB error while reading resident", 500, e)


# ----------------------------------------------------------------------
# Extra: /me profile endpoint (frontend can call using user_id)
# Example: /api/resident/me?user_id=123
# ----------------------------------------------------------------------
@resident_bp.route("/me", methods=["GET"])
def view_me():
    user_id = request.args.get("user_id", type=int)
    if not user_id:
        return _json_error("Missing user_id query param", 400)

    resident_id = _get_resident_id_by_user_id(user_id)
    if not resident_id:
        return _json_error("Resident not found for this user_id", 404)

    return view_personal_data(resident_id)


# ----------------------------------------------------------------------
# UC-R3: Update Personal Data
# ----------------------------------------------------------------------
@resident_bp.route("/<int:resident_id>", methods=["PUT"])
def update_personal_data(resident_id):
    data = request.get_json(silent=True) or {}

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
        return _json_error("No updatable fields provided", 400)

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
            return _json_error("Resident not found", 404)

        return jsonify({
            "success": True,
            "message": "Personal data updated",
            "resident_id": resident_id,
            "updated_fields": {k: v for k, v in data.items() if k in allowed_fields}
        }), 200

    except Exception as e:
        return _json_error("DB error while updating resident", 500, e)


# ----------------------------------------------------------------------
# UC-R4: Delete Personal Data
# ----------------------------------------------------------------------
@resident_bp.route("/<int:resident_id>", methods=["DELETE"])
def delete_personal_data(resident_id):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM residents WHERE resident_id = %s RETURNING resident_id;", (resident_id,))
        row = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()

        if not row:
            return _json_error("Resident not found", 404)

        return jsonify({"success": True, "message": "Resident account deleted", "resident_id": resident_id}), 200

    except Exception as e:
        return _json_error("DB error while deleting resident", 500, e)


# ----------------------------------------------------------------------
# UC-R22: View Personal Access History
# ----------------------------------------------------------------------
@resident_bp.route("/<int:resident_id>/access-history", methods=["GET"])
def view_personal_access_history(resident_id):
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("SELECT full_name FROM residents WHERE resident_id = %s;", (resident_id,))
        r = cur.fetchone()
        if not r:
            cur.close()
            conn.close()
            return _json_error("Resident not found", 404)

        full_name = r["full_name"]

        # Get visitor names registered by this resident
        cur.execute(
            "SELECT full_name FROM visitors WHERE approved_by = %s;",
            (resident_id,)
        )
        visitor_names = [row["full_name"] for row in cur.fetchall()]

        # Show resident's own access + their visitors' access
        if visitor_names:
            cur.execute(
                """
                SELECT access_time AS timestamp,
                       recognized_person,
                       person_type,
                       confidence,
                       UPPER(access_result) AS result
                FROM access_logs
                WHERE (person_type = 'resident' AND recognized_person = %s)
                   OR (person_type = 'visitor' AND recognized_person = ANY(%s))
                ORDER BY access_time DESC;
                """,
                (full_name, visitor_names)
            )
        else:
            cur.execute(
                """
                SELECT access_time AS timestamp,
                       recognized_person,
                       person_type,
                       confidence,
                       UPPER(access_result) AS result
                FROM access_logs
                WHERE person_type = 'resident' AND recognized_person = %s
                ORDER BY access_time DESC;
                """,
                (full_name,)
            )
        logs = cur.fetchall()
        cur.close()
        conn.close()

        for item in logs:
            if item.get("timestamp"):
                item["timestamp"] = item["timestamp"].isoformat()

        return jsonify({
            "success": True,
            "resident_id": resident_id,
            "full_name": full_name,
            "records": logs
        }), 200

    except Exception as e:
        return _json_error("DB error while reading access history", 500, e)


# ----------------------------------------------------------------------
# Extra: /me access-history endpoint (frontend can call using user_id)
# Example: /api/resident/me/access-history?user_id=123
# ----------------------------------------------------------------------
@resident_bp.route("/me/access-history", methods=["GET"])
def view_my_access_history():
    user_id = request.args.get("user_id", type=int)
    if not user_id:
        return _json_error("Missing user_id query param", 400)

    resident_id = _get_resident_id_by_user_id(user_id)
    if not resident_id:
        return _json_error("Resident not found for this user_id", 404)

    return view_personal_access_history(resident_id)


# ----------------------------------------------------------------------
# Visitors CRUD
# ----------------------------------------------------------------------
@resident_bp.route("/<int:resident_id>/visitors", methods=["POST"])
def create_visitor_entry(resident_id):
    data = request.get_json(silent=True) or {}
    required = ["visitor_name", "contact_number", "visiting_unit", "start_time", "end_time"]
    missing = [f for f in required if f not in data]
    if missing:
        return _json_error("Missing fields", 400, {"missing": missing})

    start_ts = parse_iso(data["start_time"])
    end_ts = parse_iso(data["end_time"])
    if not start_ts or not end_ts:
        return _json_error("Invalid datetime format (use ISO 8601)", 400)

    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("SELECT resident_id FROM residents WHERE resident_id = %s;", (resident_id,))
        if not cur.fetchone():
            cur.close()
            conn.close()
            return _json_error("Resident not found", 404)

        cur.execute(
            """
            INSERT INTO visitors (full_name, contact_number, visiting_unit, check_in, check_out, approved_by)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING visitor_id, full_name, contact_number, visiting_unit, check_in, check_out, approved_by;
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

        row["check_in"] = row["check_in"].isoformat() if row.get("check_in") else None
        row["check_out"] = row["check_out"].isoformat() if row.get("check_out") else None

        return jsonify({"success": True, "message": "Visitor created", "visitor": row}), 201

    except Exception as e:
        return _json_error("DB error while creating visitor", 500, e)


@resident_bp.route("/<int:resident_id>/visitors", methods=["GET"])
def view_registered_visitors(resident_id):
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute(
            """
            SELECT visitor_id,
                   full_name AS visitor_name,
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

        from datetime import datetime as dt
        now = dt.now()
        for r in rows:
            ci = r.get("check_in")
            co = r.get("check_out")
            r["start_time"] = ci.isoformat() if ci else None
            r["end_time"] = co.isoformat() if co else None
            # Compute status from check_in/check_out times
            if co and co < now:
                r["status"] = "EXPIRED"
            elif ci and ci <= now and (not co or co >= now):
                r["status"] = "APPROVED"
            elif ci and ci > now:
                r["status"] = "PENDING"
            else:
                r["status"] = "PENDING"

        return jsonify({"success": True, "resident_id": resident_id, "visitors": rows}), 200

    except Exception as e:
        return _json_error("DB error while reading visitors", 500, e)


@resident_bp.route("/me/visitors", methods=["GET"])
def view_my_visitors():
    user_id = request.args.get("user_id", type=int)
    if not user_id:
        return _json_error("Missing user_id query param", 400)

    resident_id = _get_resident_id_by_user_id(user_id)
    if not resident_id:
        return _json_error("Resident not found for this user_id", 404)

    return view_registered_visitors(resident_id)


@resident_bp.route("/<int:resident_id>/visitors/<int:visitor_id>", methods=["PUT"])
def update_visitor_information(resident_id, visitor_id):
    data = request.get_json(silent=True) or {}

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
                    return _json_error(f"Invalid datetime for {json_key}", 400)
                params.append(ts)
            else:
                params.append(data[json_key])
            sets.append(f"{col} = %s")

    if not sets:
        return _json_error("No updatable fields provided", 400)

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
            return _json_error("Visitor not found for this resident", 404)

        return jsonify({"success": True, "message": "Visitor updated", "visitor_id": visitor_id}), 200

    except Exception as e:
        return _json_error("DB error while updating visitor", 500, e)


# ----------------------------------------------------------------------
# UC-R: Upload Visitor Face Image (create embedding for gate recognition)
# ----------------------------------------------------------------------
@resident_bp.route("/<int:resident_id>/visitors/<int:visitor_id>/face-image", methods=["POST"])
def upload_visitor_face(resident_id, visitor_id):
    import logging
    logger = logging.getLogger(__name__)

    data = request.get_json(silent=True) or {}
    image_data = data.get("image_data")

    if not image_data:
        return _json_error("Missing image_data", 400)

    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # Verify visitor belongs to this resident
        cur.execute(
            "SELECT visitor_id, full_name FROM visitors WHERE visitor_id = %s AND approved_by = %s;",
            (visitor_id, resident_id)
        )
        visitor = cur.fetchone()
        if not visitor:
            cur.close()
            conn.close()
            return _json_error("Visitor not found for this resident", 404)

        logger.info(f"Visitor found: {visitor['full_name']}, generating embedding...")

        # Generate embedding from Cloud Run ML service
        try:
            emb = get_remote_embedding(image_data)
        except Exception as ml_err:
            logger.error(f"ML service error: {ml_err}")
            cur.close()
            conn.close()
            return _json_error(f"ML service error: {ml_err}", 502)

        if emb is None:
            cur.close()
            conn.close()
            return _json_error("No face detected. Please center the face and try again.", 400)

        logger.info(f"Embedding generated, length={len(emb)}")
        embedding = _normalize_embedding(emb)

        # Keep only ONE embedding per visitor
        cur.execute(
            "DELETE FROM face_embeddings WHERE user_type = 'visitor' AND reference_id = %s;",
            (visitor_id,)
        )

        # Insert new embedding
        cur.execute(
            """
            INSERT INTO face_embeddings (user_type, reference_id, embedding, created_at)
            VALUES ('visitor', %s, %s, NOW())
            RETURNING embedding_id;
            """,
            (visitor_id, embedding)
        )
        embedding_id = cur.fetchone()["embedding_id"]
        conn.commit()
        cur.close()
        conn.close()

        logger.info(f"Visitor face saved: visitor_id={visitor_id}, embedding_id={embedding_id}")
        return jsonify({
            "success": True,
            "message": "Visitor face registered successfully",
            "visitor_id": visitor_id,
            "embedding_id": embedding_id
        }), 201

    except Exception as e:
        logger.error(f"Error in upload_visitor_face: {type(e).__name__}: {e}")
        if conn:
            conn.rollback()
            conn.close()
        return _json_error(f"Error saving visitor face: {type(e).__name__}: {e}", 500)


# ----------------------------------------------------------------------
# UC-R: View Visitor Access History
# ----------------------------------------------------------------------
@resident_bp.route("/<int:resident_id>/visitors/<int:visitor_id>/access-history", methods=["GET"])
def view_visitor_access_history(resident_id, visitor_id):
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # Verify visitor belongs to this resident
        cur.execute(
            "SELECT visitor_id, full_name FROM visitors WHERE visitor_id = %s AND approved_by = %s;",
            (visitor_id, resident_id)
        )
        visitor = cur.fetchone()
        if not visitor:
            cur.close()
            conn.close()
            return _json_error("Visitor not found for this resident", 404)

        visitor_name = visitor["full_name"]

        # Query access logs for this visitor
        cur.execute(
            """
            SELECT access_time AS timestamp,
                   'Main Gate' AS door,
                   confidence,
                   UPPER(access_result) AS result
            FROM access_logs
            WHERE person_type = 'visitor' AND recognized_person = %s
            ORDER BY access_time DESC;
            """,
            (visitor_name,)
        )
        logs = cur.fetchall()
        cur.close()
        conn.close()

        for item in logs:
            if item.get("timestamp"):
                item["timestamp"] = item["timestamp"].isoformat()

        return jsonify({
            "success": True,
            "visitor_id": visitor_id,
            "visitor_name": visitor_name,
            "records": logs
        }), 200

    except Exception as e:
        return _json_error("DB error while reading visitor access history", 500, e)


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
            return _json_error("Visitor not found for this resident", 404)

        return jsonify({"success": True, "message": "Visitor cancelled", "visitor_id": visitor_id}), 200

    except Exception as e:
        return _json_error("DB error while deleting visitor", 500, e)


# ----------------------------------------------------------------------
# Alerts (still mock unless you have an alerts table)
# ----------------------------------------------------------------------
@resident_bp.route("/<int:resident_id>/alerts", methods=["GET"])
def receive_unauthorized_access_alert(resident_id):
    recent_time = datetime.now().isoformat(timespec="seconds")
    return jsonify({
        "success": True,
        "resident_id": resident_id,
        "alerts": [
            {
                "alert_id": 1,
                "timestamp": recent_time,
                "description": "Multiple failed face attempts at lobby door",
                "status": "UNREAD"
            }
        ]
    }), 200


# ----------------------------------------------------------------------
# Test DB
# ----------------------------------------------------------------------
@resident_bp.route("/test-db", methods=["GET"])
def test_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT NOW();")
    result = cur.fetchone()
    cur.close()
    conn.close()

    return jsonify({"success": True, "db_connection": "OK", "server_time": str(result[0])}), 200
