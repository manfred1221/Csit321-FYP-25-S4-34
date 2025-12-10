# entity/schedule_entity.py
# Entity Layer - Schedule data model and database operations

from database import get_db_cursor
from datetime import datetime


class ScheduleEntity:
    """
    Schedule Entity - Handles all schedule-related database operations
    """
    
    @staticmethod
    def get_schedules_by_staff(staff_id, start_date, end_date):
        """
        Get schedules for a staff member within a date range.
        
        Args:
            staff_id: Staff ID
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
        
        Returns:
            List of schedule records
        """
        try:
            with get_db_cursor() as cursor:
                cursor.execute("""
                    SELECT schedule_id, staff_id, shift_date, shift_start, 
                           shift_end, task_description, created_at
                    FROM staff_schedules
                    WHERE staff_id = %s 
                      AND shift_date BETWEEN %s AND %s
                    ORDER BY shift_date, shift_start
                """, (staff_id, start_date, end_date))
                
                return cursor.fetchall()
        except Exception as e:
            print(f"ScheduleEntity.get_schedules_by_staff error: {e}")
            raise
    
    @staticmethod
    def create_schedule(staff_id, shift_date, shift_start, shift_end, task_description=None):
        """
        Create a new schedule entry.
        
        Returns:
            Created schedule record
        """
        try:
            with get_db_cursor(commit=True) as cursor:
                cursor.execute("""
                    INSERT INTO staff_schedules 
                    (staff_id, shift_date, shift_start, shift_end, task_description)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING schedule_id, staff_id, shift_date, shift_start, 
                              shift_end, task_description
                """, (staff_id, shift_date, shift_start, shift_end, task_description))
                
                return cursor.fetchone()
        except Exception as e:
            print(f"ScheduleEntity.create_schedule error: {e}")
            raise
    
    @staticmethod
    def update_schedule(schedule_id, update_fields):
        """
        Update a schedule entry.
        
        Args:
            schedule_id: Schedule ID to update
            update_fields: Dictionary of fields to update
        
        Returns:
            Updated schedule record or None
        """
        try:
            with get_db_cursor(commit=True) as cursor:
                set_clause = ", ".join([f"{field} = %s" for field in update_fields.keys()])
                values = list(update_fields.values()) + [schedule_id]
                
                cursor.execute(f"""
                    UPDATE staff_schedules 
                    SET {set_clause}
                    WHERE schedule_id = %s
                    RETURNING schedule_id, staff_id, shift_date, shift_start, 
                              shift_end, task_description
                """, values)
                
                return cursor.fetchone()
        except Exception as e:
            print(f"ScheduleEntity.update_schedule error: {e}")
            raise
    
    @staticmethod
    def delete_schedule(schedule_id):
        """
        Delete a schedule entry.
        
        Returns:
            Deleted schedule record or None
        """
        try:
            with get_db_cursor(commit=True) as cursor:
                cursor.execute("""
                    DELETE FROM staff_schedules
                    WHERE schedule_id = %s
                    RETURNING schedule_id, staff_id
                """, (schedule_id,))
                
                return cursor.fetchone()
        except Exception as e:
            print(f"ScheduleEntity.delete_schedule error: {e}")
            raise
