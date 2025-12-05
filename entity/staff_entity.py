# entity/staff_entity.py
# Entity Layer - Staff data model and database operations

from database import get_db_cursor
from datetime import datetime


class StaffEntity:
    """
    Staff Entity - Handles all staff-related database operations
    """
    
    @staticmethod
    def find_by_username(username):
        """
        Find staff by username.
        Returns staff record with user info or None if not found.
        """
        try:
            with get_db_cursor() as cursor:
                cursor.execute("""
                    SELECT u.user_id, u.username, u.password_hash, r.role_name,
                           s.staff_id, s.full_name, s.position, s.is_active,
                           s.contact_number, s.registered_at
                    FROM users u
                    JOIN roles r ON u.role_id = r.role_id
                    LEFT JOIN staff s ON s.user_id = u.user_id
                    WHERE u.username = %s AND r.role_name = 'STAFF'
                """, (username,))
                
                return cursor.fetchone()
        except Exception as e:
            print(f"StaffEntity.find_by_username error: {e}")
            raise
    
    @staticmethod
    def find_by_id(staff_id):
        """
        Find staff by staff_id.
        Returns staff record or None if not found.
        """
        try:
            with get_db_cursor() as cursor:
                cursor.execute("""
                    SELECT s.staff_id, s.full_name, s.contact_number, s.position,
                           s.registered_at, s.is_active, u.username, u.email, u.user_id
                    FROM staff s
                    LEFT JOIN users u ON s.user_id = u.user_id
                    WHERE s.staff_id = %s
                """, (staff_id,))
                
                return cursor.fetchone()
        except Exception as e:
            print(f"StaffEntity.find_by_id error: {e}")
            raise
    
    @staticmethod
    def update(staff_id, update_fields):
        """
        Update staff information.
        
        Args:
            staff_id: Staff ID to update
            update_fields: Dictionary of fields to update
        
        Returns:
            Updated staff record or None if not found
        """
        try:
            with get_db_cursor(commit=True) as cursor:
                # Build dynamic UPDATE query
                set_clause = ", ".join([f"{field} = %s" for field in update_fields.keys()])
                values = list(update_fields.values()) + [staff_id]
                
                cursor.execute(f"""
                    UPDATE staff 
                    SET {set_clause}
                    WHERE staff_id = %s AND is_active = true
                    RETURNING staff_id, full_name, contact_number, position
                """, values)
                
                return cursor.fetchone()
        except Exception as e:
            print(f"StaffEntity.update error: {e}")
            raise
    
    @staticmethod
    def soft_delete(staff_id):
        """
        Soft delete staff (mark as inactive).
        
        Returns:
            Deleted staff record or None if not found
        """
        try:
            with get_db_cursor(commit=True) as cursor:
                cursor.execute("""
                    UPDATE staff
                    SET is_active = false
                    WHERE staff_id = %s AND is_active = true
                    RETURNING staff_id, full_name
                """, (staff_id,))
                
                deleted_staff = cursor.fetchone()
                
                if deleted_staff:
                    # Log the deletion
                    cursor.execute("""
                        INSERT INTO access_logs 
                        (recognized_person, person_type, access_result, confidence)
                        VALUES (%s, %s, %s, %s)
                    """, (f"Staff deleted: {deleted_staff['full_name']}", 
                          'unknown', 'denied', 1.0))
                
                return deleted_staff
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
                    SELECT fe.reference_id as staff_id, s.full_name, s.position,
                           fe.embedding <-> %s::vector AS distance
                    FROM face_embeddings fe
                    JOIN staff s ON fe.reference_id = s.staff_id
                    WHERE fe.user_type = 'staff' AND s.is_active = true
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
