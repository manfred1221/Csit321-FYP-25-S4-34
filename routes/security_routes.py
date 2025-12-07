"""
Security Officer Routes
Handles all API endpoints for security officer functionality
"""

from flask import Blueprint, request, jsonify
from models import db, User, Resident, Visitor, AccessLog, Alert
from datetime import datetime, timedelta
from sqlalchemy import func, and_, or_

security_bp = Blueprint("security_bp", __name__)


# SEC-1: Get Dashboard Statistics
@security_bp.route("/statistics", methods=["GET"])
def get_statistics():
    """
    Get real-time statistics for security dashboard
    Returns: total residents, active visitors, today's access count, alerts
    """
    today = datetime.now().date()
    
    total_residents = Resident.query.filter_by(is_active=True).count()
    
    active_visitors = Visitor.query.filter(
        Visitor.status == 'APPROVED',
        Visitor.start_time <= datetime.now(),
        Visitor.end_time >= datetime.now()
    ).count()
    
    today_access = AccessLog.query.filter(
        func.date(AccessLog.access_time) == today
    ).count()
    
    alerts_today = Alert.query.filter(
        func.date(Alert.created_at) == today,
        Alert.status == 'UNREAD'
    ).count()
    
    return jsonify({
        "total_residents": total_residents,
        "active_visitors": active_visitors,
        "today_access_count": today_access,
        "alerts_today": alerts_today
    }), 200


# SEC-2: Get Recent Access Activity
@security_bp.route("/recent-access", methods=["GET"])
def get_recent_access():
    """
    Get most recent access logs
    Query params: limit (default 10)
    """
    limit = request.args.get('limit', 10, type=int)
    
    logs = AccessLog.query.order_by(AccessLog.access_time.desc()).limit(limit).all()
    
    result = []
    for log in logs:
        person_name = "Unknown"
        person_type = "UNKNOWN"
        unit = "N/A"
        
        # Get person details
        if log.user_id:
            user = User.query.get(log.user_id)
            if user:
                person_name = user.full_name
                person_type = "RESIDENT"
                resident = Resident.query.filter_by(user_id=user.user_id).first()
                if resident:
                    unit = f"{resident.block}-{resident.unit_number}"
        
        elif log.visitor_id:
            visitor = Visitor.query.get(log.visitor_id)
            if visitor:
                person_name = visitor.visitor_name
                person_type = "VISITOR"
                unit = visitor.visiting_unit or "N/A"
        
        result.append({
            "log_id": log.log_id,
            "access_time": log.access_time.isoformat() if log.access_time else None,
            "person_name": person_name,
            "person_type": person_type,
            "unit": unit,
            "access_point": log.access_point,
            "access_result": log.access_result,
            "recognition_confidence": log.recognition_confidence
        })
    
    return jsonify(result), 200


# SEC-3: Get Current Visitors in Building
@security_bp.route("/current-visitors", methods=["GET"])
def get_current_visitors():
    """
    Get list of visitors currently in the building
    Based on approved visitors with active time slots who have entered
    """
    now = datetime.now()
    
    # Get approved visitors with active time slots
    visitors = Visitor.query.filter(
        Visitor.status == 'APPROVED',
        Visitor.start_time <= now,
        Visitor.end_time >= now
    ).all()
    
    result = []
    for visitor in visitors:
        # Check if they've actually entered (has GRANTED access log)
        entry_log = AccessLog.query.filter_by(
            visitor_id=visitor.visitor_id,
            access_result='GRANTED'
        ).order_by(AccessLog.access_time.desc()).first()
        
        if entry_log:
            result.append({
                "visitor_id": visitor.visitor_id,
                "visitor_name": visitor.visitor_name,
                "visiting_unit": visitor.visiting_unit or "N/A",
                "entry_time": entry_log.access_time.isoformat(),
                "expected_exit": visitor.end_time.isoformat() if visitor.end_time else None,
                "status": "IN_BUILDING"
            })
    
    return jsonify(result), 200


# SEC-4: Get All Access Logs with Filters
@security_bp.route("/access-logs", methods=["GET"])
def get_access_logs():
    """
    Get access logs with filtering and pagination
    Query params: date, type, result, location, search, page, per_page
    """
    date_filter = request.args.get('date')
    type_filter = request.args.get('type')
    result_filter = request.args.get('result')
    location_filter = request.args.get('location')
    search_query = request.args.get('search')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    
    query = AccessLog.query
    
    # Apply date filter
    if date_filter:
        try:
            filter_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
            query = query.filter(func.date(AccessLog.access_time) == filter_date)
        except ValueError:
            pass
    
    # Apply result filter
    if result_filter:
        query = query.filter(AccessLog.access_result == result_filter)
    
    # Apply location filter
    if location_filter:
        query = query.filter(AccessLog.access_point == location_filter)
    
    # Order by most recent
    query = query.order_by(AccessLog.access_time.desc())
    
    # Get all logs before pagination to apply additional filters
    all_logs = query.all()
    
    # Apply search and type filters (need to query related tables)
    filtered_logs = []
    for log in all_logs:
        person_name = "Unknown"
        person_type = "UNKNOWN"
        unit = "N/A"
        
        if log.user_id:
            user = User.query.get(log.user_id)
            if user:
                person_name = user.full_name
                person_type = "RESIDENT"
                resident = Resident.query.filter_by(user_id=user.user_id).first()
                if resident:
                    unit = f"{resident.block}-{resident.unit_number}"
        
        elif log.visitor_id:
            visitor = Visitor.query.get(log.visitor_id)
            if visitor:
                person_name = visitor.visitor_name
                person_type = "VISITOR"
                unit = visitor.visiting_unit or "N/A"
        
        # Apply search filter
        if search_query and search_query.lower() not in person_name.lower():
            continue
        
        # Apply type filter
        if type_filter and person_type != type_filter:
            continue
        
        filtered_logs.append({
            "log_id": log.log_id,
            "access_time": log.access_time.isoformat() if log.access_time else None,
            "person_name": person_name,
            "person_type": person_type,
            "unit": unit,
            "access_point": log.access_point,
            "access_result": log.access_result,
            "recognition_confidence": log.recognition_confidence
        })
    
    # Manual pagination
    total = len(filtered_logs)
    start = (page - 1) * per_page
    end = start + per_page
    paginated_logs = filtered_logs[start:end]
    
    return jsonify({
        "logs": paginated_logs,
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": (total + per_page - 1) // per_page  # ceiling division
    }), 200


# SEC-5: Get All Residents
@security_bp.route("/residents", methods=["GET"])
def get_all_residents():
    """
    Get directory of all active residents
    Query params: search
    """
    search = request.args.get('search', '')
    
    query = Resident.query.join(User).filter(Resident.is_active == True)
    
    if search:
        query = query.filter(
            or_(
                User.full_name.ilike(f'%{search}%'),
                Resident.unit_number.ilike(f'%{search}%')
            )
        )
    
    residents = query.all()
    
    result = []
    for resident in residents:
        if resident.user:
            result.append({
                "resident_id": resident.resident_id,
                "full_name": resident.user.full_name,
                "unit": f"{resident.block}-{resident.unit_number}",
                "contact": resident.user.contact_number,
                "email": resident.user.email,
                "face_registered": resident.face_registered
            })
    
    return jsonify(result), 200


# SEC-6: Get All Visitors
@security_bp.route("/visitors", methods=["GET"])
def get_all_visitors():
    """
    Get list of all visitors
    Query params: status, date
    """
    status_filter = request.args.get('status')
    date_filter = request.args.get('date')
    
    query = Visitor.query
    
    if status_filter:
        query = query.filter(Visitor.status == status_filter)
    
    if date_filter:
        try:
            filter_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
            query = query.filter(func.date(Visitor.start_time) == filter_date)
        except ValueError:
            pass
    
    visitors = query.order_by(Visitor.created_at.desc()).all()
    
    result = []
    for visitor in visitors:
        result.append({
            "visitor_id": visitor.visitor_id,
            "visitor_name": visitor.visitor_name,
            "contact_number": visitor.contact_number,
            "visiting_unit": visitor.visiting_unit,
            "status": visitor.status,
            "start_time": visitor.start_time.isoformat() if visitor.start_time else None,
            "end_time": visitor.end_time.isoformat() if visitor.end_time else None
        })
    
    return jsonify(result), 200


# SEC-7: Export Today's Report
@security_bp.route("/export-report", methods=["GET"])
def export_report():
    """
    Export today's access logs for reporting
    Returns data in format suitable for CSV export
    """
    today = datetime.now().date()
    
    logs = AccessLog.query.filter(
        func.date(AccessLog.access_time) == today
    ).order_by(AccessLog.access_time.desc()).all()
    
    result = []
    for log in logs:
        person_name = "Unknown"
        person_type = "UNKNOWN"
        
        if log.user_id:
            user = User.query.get(log.user_id)
            if user:
                person_name = user.full_name
                person_type = "RESIDENT"
        elif log.visitor_id:
            visitor = Visitor.query.get(log.visitor_id)
            if visitor:
                person_name = visitor.visitor_name
                person_type = "VISITOR"
        
        result.append({
            "access_time": log.access_time.isoformat() if log.access_time else "",
            "person_name": person_name,
            "person_type": person_type,
            "access_point": log.access_point,
            "access_result": log.access_result
        })
    
    return jsonify(result), 200


# SEC-8: Get Alerts
@security_bp.route("/alerts", methods=["GET"])
def get_alerts():
    """
    Get security alerts
    Query params: status (UNREAD/READ)
    """
    status_filter = request.args.get('status', 'UNREAD')
    
    query = Alert.query
    
    if status_filter:
        query = query.filter(Alert.status == status_filter)
    
    alerts = query.order_by(Alert.created_at.desc()).limit(50).all()
    
    result = []
    for alert in alerts:
        result.append({
            "alert_id": alert.alert_id,
            "alert_type": alert.alert_type,
            "description": alert.description,
            "status": alert.status,
            "created_at": alert.created_at.isoformat() if alert.created_at else None
        })
    
    return jsonify(result), 200