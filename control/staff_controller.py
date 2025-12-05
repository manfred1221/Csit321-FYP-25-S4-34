# control/staff_controller.py
# Control Layer - Business logic for staff operations

from entity.staff_entity import StaffEntity
from datetime import datetime


class StaffController:
    """
    Staff Controller - Handles business logic for staff operations
    """
    
    @staticmethod
    def login(username, password):
        """
        Authenticate staff user.
        
        Args:
            username: Staff username
            password: Staff password
        
        Returns:
            dict: Success response with staff info and token
            
        Raises:
            ValueError: If credentials are invalid or staff is inactive
        """
        # Validate input
        if not username or not password:
            raise ValueError("Username and password are required")
        
        # Find staff by username
        staff = StaffEntity.find_by_username(username)
        
        if not staff:
            raise ValueError("Invalid username or password")
        
        # Check if staff is active
        if not staff['is_active']:
            raise ValueError("Staff account is inactive")
        
        # Verify password (simple comparison for now - use bcrypt in production)
        if staff['password_hash'] != password:
            raise ValueError("Invalid username or password")
        
        # Generate token (mock - implement JWT in production)
        token = f"staff-token-{staff['staff_id']}"
        
        # Return success response
        return {
            "user_id": staff["user_id"],
            "staff_id": staff["staff_id"],
            "username": staff["username"],
            "full_name": staff["full_name"],
            "position": staff["position"],
            "role": staff["role_name"],
            "token": token,
            "message": "Login successful"
        }
    
    @staticmethod
    def get_profile(staff_id):
        """
        Get staff profile information.
        
        Args:
            staff_id: Staff ID
        
        Returns:
            dict: Staff profile data
            
        Raises:
            ValueError: If staff not found
        """
        staff = StaffEntity.find_by_id(staff_id)
        
        if not staff:
            raise ValueError("Staff not found")
        
        # Format the response
        profile = dict(staff)
        if profile.get('registered_at'):
            profile['registered_at'] = profile['registered_at'].isoformat()
        
        return profile
    
    @staticmethod
    def update_profile(staff_id, update_data):
        """
        Update staff profile information.
        
        Args:
            staff_id: Staff ID
            update_data: Dictionary of fields to update
        
        Returns:
            dict: Updated staff information
            
        Raises:
            ValueError: If no valid fields or staff not found
        """
        # Allowed fields to update
        allowed_fields = ['full_name', 'contact_number', 'position']
        update_fields = {k: v for k, v in update_data.items() if k in allowed_fields}
        
        if not update_fields:
            raise ValueError("No valid fields to update")
        
        # Update staff
        updated_staff = StaffEntity.update(staff_id, update_fields)
        
        if not updated_staff:
            raise ValueError("Staff not found or inactive")
        
        return {
            "message": "Personal information updated successfully",
            "staff": dict(updated_staff)
        }
    
    @staticmethod
    def delete_account(staff_id):
        """
        Delete staff account (soft delete).
        
        Args:
            staff_id: Staff ID
        
        Returns:
            dict: Deletion confirmation
            
        Raises:
            ValueError: If staff not found
        """
        deleted_staff = StaffEntity.soft_delete(staff_id)
        
        if not deleted_staff:
            raise ValueError("Staff not found or already deleted")
        
        return {
            "message": "Staff data deleted successfully",
            "staff_id": staff_id,
            "full_name": deleted_staff['full_name']
        }
    
    @staticmethod
    def logout():
        """
        Logout staff user.
        In stateless JWT, frontend discards token.
        
        Returns:
            dict: Logout confirmation
        """
        return {"message": "Logout successful"}
