# control/attendance_controller.py
# Control Layer - Business logic for attendance operations

from entity.attendance_entity import AttendanceEntity
from entity.staff_entity import StaffEntity
from datetime import datetime


class AttendanceController:
    """
    Attendance Controller - Handles business logic for attendance operations
    """
    
    @staticmethod
    def record_entry(staff_id=None, face_embedding=None, confidence=0.0, location="Unknown"):
        """
        Record staff entry/check-in.
        
        Args:
            staff_id: Staff ID (optional if face_embedding provided)
            face_embedding: Face embedding vector (optional if staff_id provided)
            confidence: Recognition confidence score
            location: Entry location
        
        Returns:
            dict: Entry record confirmation
            
        Raises:
            ValueError: If validation fails or staff not found
        """
        # If face embedding provided, find matching staff
        if face_embedding and not staff_id:
            if not isinstance(face_embedding, list) or len(face_embedding) != 128:
                raise ValueError("Invalid embedding format. Must be list of 128 floats")
            
            # Find staff by face embedding
            embedding_str = str(face_embedding)
            match = StaffEntity.find_by_face_embedding(embedding_str, threshold=0.3)
            
            if not match:
                raise ValueError("No matching staff found")
            
            staff_id = match['staff_id']
            confidence = 1.0 - float(match['distance'])  # Convert distance to confidence
        
        if not staff_id:
            raise ValueError("staff_id or face_embedding required")
        
        # Verify staff exists and is active
        staff = StaffEntity.find_by_id(staff_id)
        if not staff or not staff['is_active']:
            raise ValueError("Staff not found or inactive")
        
        # Record entry
        current_time = datetime.now()
        attendance = AttendanceEntity.create_entry(
            staff_id, current_time, 'face_recognition', confidence, location
        )
        
        return {
            "message": "Entry recorded successfully",
            "staff_id": staff_id,
            "full_name": staff['full_name'],
            "attendance_id": attendance['attendance_id'],
            "entry_time": attendance['entry_time'].isoformat(),
            "confidence": confidence,
            "location": location
        }
    
    @staticmethod
    def record_exit(staff_id=None, face_embedding=None, confidence=0.0, location="Unknown"):
        """
        Record staff exit/check-out.
        
        Args:
            staff_id: Staff ID (optional if face_embedding provided)
            face_embedding: Face embedding vector (optional if staff_id provided)
            confidence: Recognition confidence score
            location: Exit location
        
        Returns:
            dict: Exit record confirmation with duration
            
        Raises:
            ValueError: If validation fails, staff not found, or no open entry
        """
        # If face embedding provided, find matching staff
        if face_embedding and not staff_id:
            if not isinstance(face_embedding, list) or len(face_embedding) != 128:
                raise ValueError("Invalid embedding format. Must be list of 128 floats")
            
            embedding_str = str(face_embedding)
            match = StaffEntity.find_by_face_embedding(embedding_str, threshold=0.3)
            
            if not match:
                raise ValueError("No matching staff found")
            
            staff_id = match['staff_id']
            confidence = 1.0 - float(match['distance'])
        
        if not staff_id:
            raise ValueError("staff_id or face_embedding required")
        
        # Verify staff exists
        staff = StaffEntity.find_by_id(staff_id)
        if not staff:
            raise ValueError("Staff not found")
        
        # Find open entry
        open_entry = AttendanceEntity.find_open_entry(staff_id)
        if not open_entry:
            raise ValueError("No matching entry found. Staff must check in before checking out")
        
        # Record exit
        current_time = datetime.now()
        attendance = AttendanceEntity.update_exit(
            open_entry['attendance_id'], current_time, confidence
        )
        
        # Calculate duration
        duration = attendance['exit_time'] - attendance['entry_time']
        hours = duration.total_seconds() / 3600
        
        return {
            "message": "Exit recorded successfully",
            "staff_id": staff_id,
            "full_name": staff['full_name'],
            "attendance_id": attendance['attendance_id'],
            "entry_time": attendance['entry_time'].isoformat(),
            "exit_time": attendance['exit_time'].isoformat(),
            "duration_hours": round(hours, 2),
            "confidence": confidence,
            "location": location
        }
    
    @staticmethod
    def get_attendance_history(staff_id, start_date=None, end_date=None):
        """
        Get attendance history for a staff member.
        
        Args:
            staff_id: Staff ID
            start_date: Optional start date (YYYY-MM-DD)
            end_date: Optional end date (YYYY-MM-DD)
        
        Returns:
            dict: Attendance history records
            
        Raises:
            ValueError: If staff not found
        """
        # Verify staff exists
        staff = StaffEntity.find_by_id(staff_id)
        if not staff:
            raise ValueError("Staff not found")
        
        # Get attendance records
        records = AttendanceEntity.get_attendance_history(staff_id, start_date, end_date)
        
        # Format records
        attendance_list = []
        for record in records:
            duration = None
            if record['exit_time']:
                duration = (record['exit_time'] - record['entry_time']).total_seconds() / 3600
            
            attendance_list.append({
                "attendance_id": record['attendance_id'],
                "entry_time": record['entry_time'].isoformat(),
                "exit_time": record['exit_time'].isoformat() if record['exit_time'] else None,
                "duration_hours": round(duration, 2) if duration else None,
                "verification_method": record['verification_method'],
                "confidence": record['entry_confidence'],
                "location": record['location']
            })
        
        return {
            "staff_id": staff_id,
            "full_name": staff['full_name'],
            "records": attendance_list
        }
    
    @staticmethod
    def get_total_hours_worked(staff_id, start_date, end_date):
        """
        Calculate total hours worked in a period.
        
        Args:
            staff_id: Staff ID
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
        
        Returns:
            dict: Total hours calculation
            
        Raises:
            ValueError: If staff not found or dates invalid
        """
        # Verify staff exists
        staff = StaffEntity.find_by_id(staff_id)
        if not staff:
            raise ValueError("Staff not found")
        
        if not start_date or not end_date:
            raise ValueError("start_date and end_date are required")
        
        # Calculate total hours
        total_hours = AttendanceEntity.get_total_hours(staff_id, start_date, end_date)
        
        return {
            "staff_id": staff_id,
            "full_name": staff['full_name'],
            "period": {
                "start_date": start_date,
                "end_date": end_date
            },
            "total_hours": round(total_hours, 2)
        }
