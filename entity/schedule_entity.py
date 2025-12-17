# entity/schedule_entity.py
# Entity Layer - Schedule data model and database operations
# Uses ONLY temp_workers table

from database import get_db_cursor
from datetime import datetime, timedelta
import json


class ScheduleEntity:
    """
    Schedule Entity - Handles schedule operations using temp_workers table only
    """
    
    @staticmethod
    def get_schedules_by_staff(staff_id, start_date, end_date):
        """
        Get schedules for a staff member from temp_workers table.
        Generates daily schedule entries from work_start_date to work_end_date.
        
        Args:
            staff_id: Staff ID (user_id in temp_workers table)
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
        
        Returns:
            List of schedule records
        """
        try:
            with get_db_cursor() as cursor:
                # Get temp worker data
                cursor.execute("""
                    SELECT user_id, work_start_date, work_end_date, 
                           work_schedule, work_details
                    FROM temp_workers
                    WHERE user_id = %s
                """, (staff_id,))
                
                temp_worker = cursor.fetchone()
                
                if not temp_worker:
                    return []  # Staff not found
                
                # Get the work period
                work_start = temp_worker['work_start_date']
                work_end = temp_worker['work_end_date']
                work_details = temp_worker.get('work_details', 'Temporary work assignment')
                
                # Convert start_date and end_date strings to date objects
                query_start = datetime.strptime(start_date, '%Y-%m-%d').date()
                query_end = datetime.strptime(end_date, '%Y-%m-%d').date()
                
                # Find overlap between query range and work period
                schedule_start = max(work_start, query_start)
                schedule_end = min(work_end, query_end)
                
                generated_schedules = []
                
                if schedule_start <= schedule_end:
                    # Generate schedule for each day in the period
                    current_date = schedule_start
                    while current_date <= schedule_end:
                        generated_schedules.append({
                            'schedule_id': None,  # No schedule_id for temp workers
                            'staff_id': staff_id,
                            'shift_date': current_date,
                            'shift_start': '09:00:00',  # Default work hours
                            'shift_end': '17:00:00',
                            'task_description': work_details,
                            'created_at': work_start
                        })
                        current_date += timedelta(days=1)
                
                return generated_schedules
                
        except Exception as e:
            print(f"ScheduleEntity.get_schedules_by_staff error: {e}")
            raise
    
    @staticmethod
    def create_schedule(staff_id, shift_date, shift_start, shift_end, task_description=None):
        """
        Create/update schedule by modifying temp_worker record.
        Not implemented for temp_workers (they have fixed work periods).
        
        Returns:
            Error message
        """
        raise NotImplementedError("Cannot create individual schedules for temp workers. Modify temp_workers.work_start_date and work_end_date instead.")
    
    @staticmethod
    def update_schedule(schedule_id, update_fields):
        """
        Update schedule.
        Not implemented for temp_workers.
        
        Returns:
            Error message
        """
        raise NotImplementedError("Cannot update individual schedules for temp workers. Modify temp_workers table instead.")
    
    @staticmethod
    def delete_schedule(schedule_id):
        """
        Delete schedule.
        Not implemented for temp_workers.
        
        Returns:
            Error message
        """
        raise NotImplementedError("Cannot delete individual schedules for temp workers. Modify temp_workers table instead.")