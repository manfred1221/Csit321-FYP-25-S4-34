# entity/attendance_entity.py
# Entity Layer - Attendance data model and database operations

from database import get_db_cursor
from datetime import datetime


class AttendanceEntity:
    """
    Attendance Entity - Handles all attendance-related database operations
    """
    
    @staticmethod
    def create_entry(staff_id, entry_time, verification_method, confidence, location):
        """
        Create a new attendance entry record.
        
        Returns:
            Created attendance record
        """
        try:
            with get_db_cursor(commit=True) as cursor:
                cursor.execute("""
                    INSERT INTO staff_attendance 
                    (staff_id, entry_time, verification_method, entry_confidence, location)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING attendance_id, staff_id, entry_time, verification_method, 
                              entry_confidence, location
                """, (staff_id, entry_time, verification_method, confidence, location))
                
                return cursor.fetchone()
        except Exception as e:
            print(f"AttendanceEntity.create_entry error: {e}")
            raise
    
    @staticmethod
    def find_open_entry(staff_id):
        """
        Find the most recent entry without an exit time for a staff member.
        
        Returns:
            Open attendance record or None
        """
        try:
            with get_db_cursor() as cursor:
                cursor.execute("""
                    SELECT attendance_id, staff_id, entry_time, location
                    FROM staff_attendance
                    WHERE staff_id = %s AND exit_time IS NULL
                    ORDER BY entry_time DESC
                    LIMIT 1
                """, (staff_id,))
                
                return cursor.fetchone()
        except Exception as e:
            print(f"AttendanceEntity.find_open_entry error: {e}")
            raise
    
    @staticmethod
    def update_exit(attendance_id, exit_time, confidence):
        """
        Update attendance record with exit time.
        
        Returns:
            Updated attendance record
        """
        try:
            with get_db_cursor(commit=True) as cursor:
                cursor.execute("""
                    UPDATE staff_attendance
                    SET exit_time = %s, exit_confidence = %s
                    WHERE attendance_id = %s
                    RETURNING attendance_id, staff_id, entry_time, exit_time, 
                              entry_confidence, exit_confidence, location
                """, (exit_time, confidence, attendance_id))
                
                return cursor.fetchone()
        except Exception as e:
            print(f"AttendanceEntity.update_exit error: {e}")
            raise
    
    @staticmethod
    def get_attendance_history(staff_id, start_date=None, end_date=None, limit=50):
        """
        Get attendance history for a staff member.
        
        Args:
            staff_id: Staff ID
            start_date: Optional start date filter (YYYY-MM-DD)
            end_date: Optional end date filter (YYYY-MM-DD)
            limit: Maximum number of records to return
        
        Returns:
            List of attendance records
        """
        try:
            with get_db_cursor() as cursor:
                query = """
                    SELECT attendance_id, staff_id, entry_time, exit_time, 
                           verification_method, entry_confidence, exit_confidence, location
                    FROM staff_attendance
                    WHERE staff_id = %s
                """
                params = [staff_id]
                
                if start_date:
                    query += " AND entry_time >= %s"
                    params.append(start_date)
                
                if end_date:
                    query += " AND entry_time <= %s"
                    params.append(end_date + ' 23:59:59')
                
                query += " ORDER BY entry_time DESC LIMIT %s"
                params.append(limit)
                
                cursor.execute(query, params)
                return cursor.fetchall()
        except Exception as e:
            print(f"AttendanceEntity.get_attendance_history error: {e}")
            raise
    
    @staticmethod
    def get_total_hours(staff_id, start_date, end_date):
        """
        Calculate total work hours for a staff member in a date range.
        
        Returns:
            Total hours worked
        """
        try:
            with get_db_cursor() as cursor:
                cursor.execute("""
                    SELECT SUM(EXTRACT(EPOCH FROM (exit_time - entry_time))/3600) as total_hours
                    FROM staff_attendance
                    WHERE staff_id = %s 
                      AND entry_time >= %s 
                      AND entry_time <= %s
                      AND exit_time IS NOT NULL
                """, (staff_id, start_date, end_date + ' 23:59:59'))
                
                result = cursor.fetchone()
                return result['total_hours'] if result['total_hours'] else 0.0
        except Exception as e:
            print(f"AttendanceEntity.get_total_hours error: {e}")
            raise
