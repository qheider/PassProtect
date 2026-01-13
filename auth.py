"""
User Authentication Module for PassProtect
Handles user authentication against quaziinfodb
"""

from typing import Dict, List
from db_access import fetch_one, fetch_all
from password_utils import verify_password, PasswordVerificationError


class AuthenticationError(Exception):
    """Exception raised when authentication fails"""
    pass


def authenticate_user(username: str, password: str) -> Dict[str, any]:
    """
    Authenticate a user by username and password.
    
    Args:
        username: The username to authenticate (matches user.userName)
        password: The plain text password to verify
        
    Returns:
        Dictionary containing authenticated user data:
            - id: User ID
            - userName: Username
            - email: User email
            
    Raises:
        AuthenticationError: If authentication fails for any reason
        
    Example:
        try:
            user = authenticate_user("john_doe", "mypassword123")
            print(f"Authenticated: {user['userName']} ({user['email']})")
        except AuthenticationError as e:
            print(f"Login failed: {e}")
    """
    if not username or not password:
        raise AuthenticationError("Username and password are required")
    
    # Query user by userName
    sql = "SELECT id, userName, email, password, enabled, archived FROM user WHERE userName = %s"
    user_record = fetch_one(sql, (username,))
    
    # Check if user exists
    if not user_record:
        raise AuthenticationError("Invalid username or password")
    
    # Check if user is archived (BIT(1) field - archived = 1 means archived)
    if user_record.get('archived'):
        raise AuthenticationError("Account is archived")
    
    # Check if user is enabled (BIT(1) field - enabled = 0 means disabled)
    if not user_record.get('enabled'):
        raise AuthenticationError("Account is disabled")
    
    # Verify password against user.password field
    try:
        verify_password(password, user_record['password'])
    except PasswordVerificationError:
        raise AuthenticationError("Invalid username or password")
    
    # Return user object (without sensitive data)
    return {
        "id": user_record['id'],
        "userName": user_record['userName'],
        "email": user_record['email']
    }


def load_user_roles(user_id: int) -> List[str]:
    """
    Load all role names assigned to a user.
    
    Args:
        user_id: The ID of the user
        
    Returns:
        List of role names (strings). Empty list if no roles assigned.
        Only includes non-archived roles (role.archived = 0).
        
    Example:
        roles = load_user_roles(1)
        # Returns: ['admin', 'editor']
    """
    if not user_id:
        return []
    
    # JOIN role and users_roles tables, filter by archived = 0
    sql = """
        SELECT r.name 
        FROM role r
        INNER JOIN users_roles ur ON r.id = ur.role_id
        WHERE ur.user_id = %s AND r.archived = 0
    """
    
    results = fetch_all(sql, (user_id,))
    
    # Extract role names from results
    role_names = [row['name'] for row in results]
    
    return role_names
