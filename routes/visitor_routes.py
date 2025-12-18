# routes/visitor_routes.py
# Visitor-related routes with real Supabase database connection

from flask import Blueprint, request, jsonify
from psycopg2.extras import RealDictCursor
from database import get_db_connection
from datetime import datetime

visitor_bp = Blueprint("visitor", __name__)


def _json_error(msg, status=400):
    """Helper to return JSON error response"""
    return jsonify({"error": msg}), status


def parse_iso(dt_str):
    """Parse ISO format datetime string"""
    if not dt_str:
        return None
    try:
        return datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
    except (ValueError, AttributeError):
        return None


# UC-R8 Create Visitor Entry (Real DB)
@visitor_bp.route("/visitors", methods=["POST"])
def create_visitor_entry():
    """
    Create a new visitor entry in the database.
    
    Request JSON:
      {
        "visitor_name": "John Visitor",
        "contact_number": "91234567",
        "visiting_unit": "B-12-05",
        "start_time": "2025-12-20T10:00:00",
        "end_time": "2025-12-20T18:00:00",
        "approved_by": 1  // resident_id who approved
      }
    """
    data = request.get_json(silent=True) or {}
    
    required = ["visitor_name", "contact_number", "visiting_unit", "start_time", "end_time"]
    missing = [f for f in required if f not in data]
    if missing:
        return _json_error(f"Missing required fields: {', '.join(missing)}", 400)
    
    # Parse datetime
    check_in = parse_iso(data["start_time"])
    check_out = parse_iso(data["end_time"])
    
    if not check_in or not check_out:
        return _json_error("Invalid datetime format. Use ISO 8601 format.", 400)
    
    approved_by = data.get("approved_by")  # resident_id
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Insert visitor
        cursor.execute("""
            INSERT INTO visitors (
                full_name,
                contact_number,
                visiting_unit,
                check_in,
                check_out,
                approved_by
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING visitor_id, full_name, contact_number, visiting_unit, 
                      check_in, check_out, approved_by
        """, (
            data["visitor_name"],
            data["contact_number"],
            data["visiting_unit"],
            check_in,
            check_out,
            approved_by
        ))
        
        visitor = cursor.fetchone()
        conn.commit()
        cursor.close()
        conn.close()
        
        # Format datetime for JSON response
        if visitor:
            visitor["check_in"] = visitor["check_in"].isoformat() if visitor.get("check_in") else None
            visitor["check_out"] = visitor["check_out"].isoformat() if visitor.get("check_out") else None
        
        return jsonify({
            "success": True,
            "message": "Visitor entry created successfully",
            "visitor": visitor
        }), 201
        
    except Exception as e:
        print(f"Error creating visitor: {e}")
        return _json_error("Database error while creating visitor entry", 500)


# UC-R10 View Registered Visitors (Real DB)
@visitor_bp.route("/visitors", methods=["GET"])
def view_registered_visitors():
    """
    Get all visitors, optionally filtered by resident_id.
    
    Query params:
      - resident_id: Filter visitors by who approved them
      - status: Filter by status (optional, if you add status field)
    """
    resident_id = request.args.get("resident_id", type=int)
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        if resident_id:
            # Get visitors for specific resident
            cursor.execute("""
                SELECT 
                    visitor_id,
                    full_name,
                    contact_number,
                    visiting_unit,
                    check_in,
                    check_out,
                    approved_by
                FROM visitors
                WHERE approved_by = %s
                ORDER BY check_in DESC
            """, (resident_id,))
        else:
            # Get all visitors
            cursor.execute("""
                SELECT 
                    v.visitor_id,
                    v.full_name,
                    v.contact_number,
                    v.visiting_unit,
                    v.check_in,
                    v.check_out,
                    v.approved_by,
                    r.full_name as resident_name
                FROM visitors v
                LEFT JOIN residents r ON v.approved_by = r.resident_id
                ORDER BY v.check_in DESC
            """)
        
        visitors = cursor.fetchall()
        cursor.close()
        conn.close()
        
        # Format datetime fields
        for visitor in visitors:
            visitor["check_in"] = visitor["check_in"].isoformat() if visitor.get("check_in") else None
            visitor["check_out"] = visitor["check_out"].isoformat() if visitor.get("check_out") else None
        
        return jsonify({
            "success": True,
            "count": len(visitors),
            "visitors": visitors
        }), 200
        
    except Exception as e:
        print(f"Error getting visitors: {e}")
        return _json_error("Database error while retrieving visitors", 500)


# Get single visitor by ID
@visitor_bp.route("/visitors/<int:visitor_id>", methods=["GET"])
def get_visitor_by_id(visitor_id):
    """Get details of a specific visitor"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT 
                v.visitor_id,
                v.full_name,
                v.contact_number,
                v.visiting_unit,
                v.check_in,
                v.check_out,
                v.approved_by,
                r.full_name as resident_name,
                r.unit_number as resident_unit
            FROM visitors v
            LEFT JOIN residents r ON v.approved_by = r.resident_id
            WHERE v.visitor_id = %s
        """, (visitor_id,))
        
        visitor = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not visitor:
            return _json_error("Visitor not found", 404)
        
        # Format datetime
        visitor["check_in"] = visitor["check_in"].isoformat() if visitor.get("check_in") else None
        visitor["check_out"] = visitor["check_out"].isoformat() if visitor.get("check_out") else None
        
        return jsonify({
            "success": True,
            "visitor": visitor
        }), 200
        
    except Exception as e:
        print(f"Error getting visitor: {e}")
        return _json_error("Database error while retrieving visitor", 500)


# Update visitor
@visitor_bp.route("/visitors/<int:visitor_id>", methods=["PUT"])
def update_visitor(visitor_id):
    """Update visitor information"""
    data = request.get_json(silent=True) or {}
    
    allowed_fields = {
        "visitor_name": "full_name",
        "full_name": "full_name",
        "contact_number": "contact_number",
        "visiting_unit": "visiting_unit",
        "start_time": "check_in",
        "end_time": "check_out"
    }
    
    sets = []
    params = []
    
    for json_key, db_col in allowed_fields.items():
        if json_key in data:
            if json_key in ("start_time", "end_time"):
                ts = parse_iso(data[json_key])
                if not ts:
                    return _json_error(f"Invalid datetime format for {json_key}", 400)
                params.append(ts)
            else:
                params.append(data[json_key])
            sets.append(f"{db_col} = %s")
    
    if not sets:
        return _json_error("No fields to update", 400)
    
    params.append(visitor_id)
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(f"""
            UPDATE visitors
            SET {", ".join(sets)}
            WHERE visitor_id = %s
            RETURNING visitor_id
        """, tuple(params))
        
        result = cursor.fetchone()
        conn.commit()
        cursor.close()
        conn.close()
        
        if not result:
            return _json_error("Visitor not found", 404)
        
        return jsonify({
            "success": True,
            "message": "Visitor updated successfully",
            "visitor_id": visitor_id
        }), 200
        
    except Exception as e:
        print(f"Error updating visitor: {e}")
        return _json_error("Database error while updating visitor", 500)


# Delete visitor
@visitor_bp.route("/visitors/<int:visitor_id>", methods=["DELETE"])
def delete_visitor(visitor_id):
    """Delete/cancel a visitor entry"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            DELETE FROM visitors
            WHERE visitor_id = %s
            RETURNING visitor_id
        """, (visitor_id,))
        
        result = cursor.fetchone()
        conn.commit()
        cursor.close()
        conn.close()
        
        if not result:
            return _json_error("Visitor not found", 404)
        
        return jsonify({
            "success": True,
            "message": "Visitor entry deleted successfully",
            "visitor_id": visitor_id
        }), 200
        
    except Exception as e:
        print(f"Error deleting visitor: {e}")
        return _json_error("Database error while deleting visitor", 500)


# Test database connection
@visitor_bp.route("/test-db", methods=["GET"])
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
        return _json_error(f"Database connection failed: {str(e)}", 500)