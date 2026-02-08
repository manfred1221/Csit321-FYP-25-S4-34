# entity/staff_entity.py
# Entity Layer - Staff data model and database operations
# Uses users table for staff lookup (staff_id = user_id)

from database import get_db_cursor
from datetime import datetime


class StaffEntity:
    """
    Staff Entity - Handles staff operations using users table
    """

    @staticmethod
    def find_by_username(username):
        """
        Find staff by username from users table.
        Returns staff record with user info or None if not found.
        """
        try:
            with get_db_cursor() as cursor:
                cursor.execute("""
                    SELECT u.user_id, u.username, u.password_hash, r.role_name,
                           u.user_id as staff_id,
                           COALESCE(u.full_name, u.username) as full_name,
                           r.role_name as position,
                           true as is_active,
                           u.email as contact_number,
                           u.created_at
                    FROM users u
                    JOIN roles r ON u.role_id = r.role_id
                    WHERE u.username = %s AND u.role_id IN (4, 7, 8, 9)
                """, (username,))

                return cursor.fetchone()

        except Exception as e:
            print(f"StaffEntity.find_by_username error: {e}")
            raise

    @staticmethod
    def find_by_id(staff_id):
        """
        Find staff by staff_id (user_id) from users table.
        Returns staff record or None if not found.
        """
        try:
            with get_db_cursor() as cursor:
                cursor.execute("""
                    SELECT u.user_id as staff_id,
                           COALESCE(u.full_name, u.username) as full_name,
                           u.email as contact_number,
                           r.role_name as position,
                           u.created_at,
                           true as is_active,
                           u.username, u.email, u.user_id
                    FROM users u
                    JOIN roles r ON u.role_id = r.role_id
                    WHERE u.user_id = %s AND u.role_id IN (4, 7, 8, 9)
                """, (staff_id,))

                return cursor.fetchone()

        except Exception as e:
            print(f"StaffEntity.find_by_id error: {e}")
            raise

    @staticmethod
    def update(staff_id, update_fields):
        """
        Update staff information in users table.

        Args:
            staff_id: Staff ID (user_id)
            update_fields: Dictionary of fields to update

        Returns:
            Updated staff record or None if not found
        """
        try:
            with get_db_cursor(commit=True) as cursor:
                if 'full_name' in update_fields:
                    cursor.execute("""
                        UPDATE users
                        SET full_name = %s
                        WHERE user_id = %s
                    """, (update_fields['full_name'], staff_id))

                if 'contact_number' in update_fields:
                    cursor.execute("""
                        UPDATE users
                        SET email = %s
                        WHERE user_id = %s
                    """, (update_fields['contact_number'], staff_id))

                # Return updated record
                cursor.execute("""
                    SELECT u.user_id as staff_id,
                           COALESCE(u.full_name, u.username) as full_name,
                           u.email as contact_number,
                           r.role_name as position
                    FROM users u
                    JOIN roles r ON u.role_id = r.role_id
                    WHERE u.user_id = %s
                """, (staff_id,))

                return cursor.fetchone()
        except Exception as e:
            print(f"StaffEntity.update error: {e}")
            raise

    @staticmethod
    def soft_delete(staff_id):
        """
        Soft delete staff by setting status to inactive.

        Returns:
            Deleted staff record or None if not found
        """
        try:
            with get_db_cursor(commit=True) as cursor:
                # Get staff info before deactivating
                cursor.execute("""
                    SELECT u.user_id, COALESCE(u.full_name, u.username) as full_name
                    FROM users u
                    WHERE u.user_id = %s
                """, (staff_id,))

                staff_info = cursor.fetchone()

                if not staff_info:
                    return None

                # Set status to inactive
                cursor.execute("""
                    UPDATE users SET status = 'inactive'
                    WHERE user_id = %s
                """, (staff_id,))

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
                           COALESCE(u.full_name, u.username) as full_name,
                           r.role_name as position,
                           fe.embedding <-> %s::vector AS distance
                    FROM face_embeddings fe
                    JOIN users u ON fe.reference_id = u.user_id
                    JOIN roles r ON u.role_id = r.role_id
                    WHERE fe.user_type IN ('staff', 'internal_staff')
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
