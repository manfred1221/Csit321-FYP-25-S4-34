# entity/schedule_entity.py
# Entity Layer - Schedule data model and database operations

from database import get_db_cursor
from datetime import datetime, timedelta
import json


class ScheduleEntity:
    """
    Schedule Entity - Handles schedule operations
    """

    @staticmethod
    def get_schedules_by_staff(staff_id, start_date, end_date):
        """
        Get schedules for a staff member.
        Checks staff_schedules table first, then falls back to temp_workers.

        Args:
            staff_id: Staff ID (user_id)
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)

        Returns:
            List of schedule records
        """
        print(f"[ScheduleEntity] Querying staff_schedules for staff_id={staff_id}, start={start_date}, end={end_date}")

        # First check staff_schedules table (admin-assigned schedules)
        try:
            with get_db_cursor() as cursor:
                cursor.execute("""
                    SELECT schedule_id, staff_id, shift_date,
                           shift_start, shift_end,
                           task_description, created_at
                    FROM staff_schedules
                    WHERE staff_id = %s
                    AND shift_date >= %s AND shift_date <= %s
                    ORDER BY shift_date, shift_start
                """, (staff_id, start_date, end_date))

                staff_schedule_rows = cursor.fetchall()
                print(f"[ScheduleEntity] staff_schedules returned {len(staff_schedule_rows)} rows")

                if staff_schedule_rows:
                    schedules = []
                    for row in staff_schedule_rows:
                        schedules.append({
                            'schedule_id': row['schedule_id'],
                            'staff_id': row['staff_id'],
                            'shift_date': row['shift_date'] if not isinstance(row['shift_date'], datetime) else row['shift_date'].date(),
                            'shift_start': str(row['shift_start']) if row['shift_start'] else '09:00:00',
                            'shift_end': str(row['shift_end']) if row['shift_end'] else '17:00:00',
                            'task_description': row.get('task_description') or 'Work shift',
                            'created_at': row.get('created_at')
                        })
                    return schedules
                else:
                    # Also check without date filter to see if ANY schedules exist
                    cursor.execute("""
                        SELECT schedule_id, staff_id, shift_date
                        FROM staff_schedules
                        WHERE staff_id = %s
                        ORDER BY shift_date DESC
                        LIMIT 5
                    """, (staff_id,))
                    all_rows = cursor.fetchall()
                    if all_rows:
                        print(f"[ScheduleEntity] Found {len(all_rows)} schedules for staff_id={staff_id} but NOT matching date range:")
                        for r in all_rows:
                            print(f"  - schedule_id={r['schedule_id']}, shift_date={r['shift_date']}")
                    else:
                        print(f"[ScheduleEntity] NO schedules at all for staff_id={staff_id} in staff_schedules table")
        except Exception as e:
            print(f"ScheduleEntity: staff_schedules query error: {e}")

        # Fallback: try temp_workers table (separate connection in case schema differs)
        try:
            with get_db_cursor() as cursor:
                cursor.execute("""
                    SELECT user_id, work_start_date, work_end_date,
                           work_schedule, work_details
                    FROM temp_workers
                    WHERE user_id = %s
                """, (staff_id,))

                temp_worker = cursor.fetchone()

                if not temp_worker:
                    return []

                work_start = temp_worker['work_start_date']
                work_end = temp_worker['work_end_date']

                if isinstance(work_start, datetime):
                    work_start = work_start.date()
                if isinstance(work_end, datetime):
                    work_end = work_end.date()

                work_details = temp_worker.get('work_details', 'Temporary work assignment')

                query_start = datetime.strptime(start_date, '%Y-%m-%d').date()
                query_end = datetime.strptime(end_date, '%Y-%m-%d').date()

                schedule_start = max(work_start, query_start)
                schedule_end = min(work_end, query_end)

                generated_schedules = []

                if schedule_start <= schedule_end:
                    current_date = schedule_start
                    while current_date <= schedule_end:
                        generated_schedules.append({
                            'schedule_id': None,
                            'staff_id': staff_id,
                            'shift_date': current_date,
                            'shift_start': '09:00:00',
                            'shift_end': '17:00:00',
                            'task_description': work_details,
                            'created_at': work_start
                        })
                        current_date += timedelta(days=1)

                return generated_schedules

        except Exception as e:
            print(f"ScheduleEntity: temp_workers fallback error: {e}")

        return []

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
