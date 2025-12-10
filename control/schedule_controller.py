# control/schedule_controller.py
# Control Layer - Business logic for schedule operations

from entity.schedule_entity import ScheduleEntity
from entity.staff_entity import StaffEntity
from datetime import datetime, timedelta


class ScheduleController:
    """
    Schedule Controller - Handles business logic for schedule operations
    """
    
    @staticmethod
    def get_staff_schedule(staff_id, start_date=None, end_date=None):
        """
        Get schedule for a staff member.
        
        Args:
            staff_id: Staff ID
            start_date: Optional start date (YYYY-MM-DD), defaults to today
            end_date: Optional end date (YYYY-MM-DD), defaults to 7 days from start
        
        Returns:
            dict: Staff info and schedule list
            
        Raises:
            ValueError: If staff not found
        """
        # Verify staff exists and is active
        staff = StaffEntity.find_by_id(staff_id)
        
        if not staff or not staff['is_active']:
            raise ValueError("Staff not found or inactive")
        
        # Set default dates if not provided
        if not start_date:
            start_date = datetime.now().strftime('%Y-%m-%d')
        
        if not end_date:
            end_date_obj = datetime.strptime(start_date, '%Y-%m-%d') + timedelta(days=7)
            end_date = end_date_obj.strftime('%Y-%m-%d')
        
        # Get schedules
        schedules = ScheduleEntity.get_schedules_by_staff(staff_id, start_date, end_date)
        
        # Format schedule data
        schedule_list = []
        for schedule in schedules:
            schedule_list.append({
                "schedule_id": schedule['schedule_id'],
                "shift_date": schedule['shift_date'].strftime('%Y-%m-%d'),
                "shift_start": str(schedule['shift_start']),
                "shift_end": str(schedule['shift_end']),
                "task_description": schedule['task_description']
            })
        
        return {
            "staff_id": staff['staff_id'],
            "full_name": staff['full_name'],
            "position": staff['position'],
            "schedules": schedule_list,
            "period": {
                "start_date": start_date,
                "end_date": end_date
            }
        }
    
    @staticmethod
    def create_schedule(staff_id, shift_date, shift_start, shift_end, task_description=None):
        """
        Create a new schedule entry.
        
        Args:
            staff_id: Staff ID
            shift_date: Shift date (YYYY-MM-DD)
            shift_start: Shift start time (HH:MM:SS)
            shift_end: Shift end time (HH:MM:SS)
            task_description: Optional task description
        
        Returns:
            dict: Created schedule
            
        Raises:
            ValueError: If validation fails or staff not found
        """
        # Verify staff exists
        staff = StaffEntity.find_by_id(staff_id)
        if not staff or not staff['is_active']:
            raise ValueError("Staff not found or inactive")
        
        # Validate required fields
        if not all([shift_date, shift_start, shift_end]):
            raise ValueError("shift_date, shift_start, and shift_end are required")
        
        # Create schedule
        schedule = ScheduleEntity.create_schedule(
            staff_id, shift_date, shift_start, shift_end, task_description
        )
        
        return {
            "message": "Schedule created successfully",
            "schedule": dict(schedule)
        }
    
    @staticmethod
    def update_schedule(schedule_id, update_data):
        """
        Update a schedule entry.
        
        Args:
            schedule_id: Schedule ID
            update_data: Dictionary of fields to update
        
        Returns:
            dict: Updated schedule
            
        Raises:
            ValueError: If schedule not found or no valid fields
        """
        # Allowed fields to update
        allowed_fields = ['shift_date', 'shift_start', 'shift_end', 'task_description']
        update_fields = {k: v for k, v in update_data.items() if k in allowed_fields}
        
        if not update_fields:
            raise ValueError("No valid fields to update")
        
        # Update schedule
        schedule = ScheduleEntity.update_schedule(schedule_id, update_fields)
        
        if not schedule:
            raise ValueError("Schedule not found")
        
        return {
            "message": "Schedule updated successfully",
            "schedule": dict(schedule)
        }
    
    @staticmethod
    def delete_schedule(schedule_id):
        """
        Delete a schedule entry.
        
        Args:
            schedule_id: Schedule ID
        
        Returns:
            dict: Deletion confirmation
            
        Raises:
            ValueError: If schedule not found
        """
        deleted = ScheduleEntity.delete_schedule(schedule_id)
        
        if not deleted:
            raise ValueError("Schedule not found")
        
        return {
            "message": "Schedule deleted successfully",
            "schedule_id": schedule_id
        }
