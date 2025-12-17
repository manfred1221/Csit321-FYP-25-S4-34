# entity/staff_entity.py
# Entity Layer - Staff data model and database operations
# Uses ONLY temp_workers table (no staff table)

from database import get_db_cursor
from datetime import datetime


class StaffEntity:
    """
    Staff Entity - Handles staff operations using temp_workers table only
    """
    
    @staticmethod
    def find_by_username(username):
        """
        Find staff by username from temp_workers table.
        Returns staff record with user info or None if not found.
        """
        try:
            with get_db_cursor() as cursor:
                cursor.execute("""
                    SELECT u.user_id, u.username, u.password_hash, r.role_name,
                           tw.user_id as staff_id, 
                           u.username as full_name,
                           'Temporary Worker' as position,
                           true as is_active,
                           u.email as contact_number,
                           tw.work_start_date as created_at
                    FROM users u
                    JOIN roles r ON u.role_id = r.role_id
                    JOIN temp_workers tw ON tw.user_id = u.user_id
                    WHERE u.username = %s
                """, (username,))
                
                return cursor.fetchone()
                
        except Exception as e:
            print(f"StaffEntity.find_by_username error: {e}")
            raise
    
    @staticmethod
    def find_by_id(staff_id):
        """
        Find staff by staff_id (user_id) from temp_workers table.
        Returns staff record or None if not found.
        """
        try:
            with get_db_cursor() as cursor:
                cursor.execute("""
                    SELECT tw.user_id as staff_id, 
                           u.username as full_name,
                           u.email as contact_number,
                           'Temporary Worker' as position,
                           tw.work_start_date as created_at,
                           true as is_active,
                           u.username, u.email, u.user_id
                    FROM temp_workers tw
                    JOIN users u ON tw.user_id = u.user_id
                    WHERE tw.user_id = %s
                """, (staff_id,))
                
                return cursor.fetchone()
                
        except Exception as e:
            print(f"StaffEntity.find_by_id error: {e}")
            raise
    
    @staticmethod
    def update(staff_id, update_fields):
        """
        Update staff information in temp_workers table.
        Currently only supports updating work_details.
        
        Args:
            staff_id: Staff ID (user_id)
            update_fields: Dictionary of fields to update
        
        Returns:
            Updated staff record or None if not found
        """
        try:
            with get_db_cursor(commit=True) as cursor:
                # For temp_workers, we can update work_details
                if 'full_name' in update_fields:
                    # Update username in users table
                    cursor.execute("""
                        UPDATE users 
                        SET username = %s
                        WHERE user_id = %s
                        RETURNING user_id
                    """, (update_fields['full_name'], staff_id))
                
                if 'contact_number' in update_fields:
                    # Update email in users table
                    cursor.execute("""
                        UPDATE users 
                        SET email = %s
                        WHERE user_id = %s
                    """, (update_fields['contact_number'], staff_id))
                
                # Return updated record
                cursor.execute("""
                    SELECT tw.user_id as staff_id, 
                           u.username as full_name,
                           u.email as contact_number,
                           'Temporary Worker' as position
                    FROM temp_workers tw
                    JOIN users u ON tw.user_id = u.user_id
                    WHERE tw.user_id = %s
                """, (staff_id,))
                
                return cursor.fetchone()
        except Exception as e:
            print(f"StaffEntity.update error: {e}")
            raise
    
    @staticmethod
    def soft_delete(staff_id):
        """
        Soft delete staff by removing from temp_workers table.
        
        Returns:
            Deleted staff record or None if not found
        """
        try:
            with get_db_cursor(commit=True) as cursor:
                # Get staff info before deleting
                cursor.execute("""
                    SELECT u.user_id, u.username as full_name
                    FROM temp_workers tw
                    JOIN users u ON tw.user_id = u.user_id
                    WHERE tw.user_id = %s
                """, (staff_id,))
                
                staff_info = cursor.fetchone()
                
                if not staff_info:
                    return None
                
                # Delete from temp_workers
                cursor.execute("""
                    DELETE FROM temp_workers
                    WHERE user_id = %s
                """, (staff_id,))
                
                # Log the deletion
                cursor.execute("""
                    INSERT INTO access_logs 
                    (recognized_person, person_type, access_result, confidence)
                    VALUES (%s, %s, %s, %s)
                """, (f"Staff deleted: {staff_info['full_name']}", 
                      'unknown', 'denied', 1.0))
                
                return {'staff_id': staff_id, 'full_name': staff_info['full_name']}
        except Exception as e:
            print(f"StaffEntity.soft_delete error: {e}")
            raise
    
    @staticmethod
    def find_by_face_embedding(embedding_str, threshold=0.3):
        """
        Find staff by face embedding using pgvector similarity.
        
        Args:
            embedding_str: Vector string representation
            threshold: Distance threshold for matching (default 0.3)
        
        Returns:
            Matching staff record with distance or None
        """
        try:
            with get_db_cursor() as cursor:
                cursor.execute("""
                    SELECT fe.reference_id as staff_id, 
                           u.username as full_name, 
                           'Temporary Worker' as position,
                           fe.embedding <-> %s::vector AS distance
                    FROM face_embeddings fe
                    JOIN temp_workers tw ON fe.reference_id = tw.user_id
                    JOIN users u ON tw.user_id = u.user_id
                    WHERE fe.user_type = 'staff'
                    ORDER BY distance
                    LIMIT 1
                """, (embedding_str,))
                
                match = cursor.fetchone()
                
                # Check if distance is within threshold
                if match and match['distance'] <= threshold:
                    return match
                
                return None
        except Exception as e:
            print(f"StaffEntity.find_by_face_embedding error: {e}")
            raise