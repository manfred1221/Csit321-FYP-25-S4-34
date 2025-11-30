from flask import Blueprint, request, jsonify

# Blueprint for resident-managed visitors
visitor_bp = Blueprint("visitor", __name__)


@visitor_bp.route("/visitors", methods=["POST"])
def create_visitor_entry():
    """
    UC-R8 Create Visitor Entry (stub)
    Expects JSON with visitor details.
    """
    payload = request.get_json() or {}
    # TODO: insert into visitors table
    return jsonify({"message": "Visitor entry created (stub)", "payload": payload}), 201


@visitor_bp.route("/visitors", methods=["GET"])
def view_registered_visitors():
    """
    UC-R10 View Registered Visitors (stub)
    """
    # TODO: query visitors table for this resident
    demo_visitors = [
        {
            "visitor_id": 1,
            "full_name": "Mary Lee",
            "visiting_unit": "B-12-05",
            "check_in": "2025-11-12T11:06:13",
        }
    ]
    return jsonify(demo_visitors), 200
