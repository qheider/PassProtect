"""
Password Utility Module for PassProtect
Provides secure password verification using bcrypt
"""

import bcrypt


class PasswordVerificationError(Exception):
    """Exception raised when password verification fails"""
    pass


def verify_password(plain_password: str, password_hash: str) -> bool:
    """
    Verify a plain text password against a bcrypt hash.
    
    Args:
        plain_password: The plain text password to verify
        password_hash: The bcrypt hash stored in user.password field
        
    Returns:
        True if password matches the hash
        
    Raises:
        PasswordVerificationError: If verification fails or hash is invalid
        
    Example:
        try:
            verify_password("mypassword", stored_hash)
            print("Password verified")
        except PasswordVerificationError:
            print("Invalid password")
    """
    try:
        # Convert password to bytes if it's a string
        if isinstance(plain_password, str):
            plain_password_bytes = plain_password.encode('utf-8')
        else:
            plain_password_bytes = plain_password
            
        # Convert hash to bytes if it's a string
        if isinstance(password_hash, str):
            password_hash_bytes = password_hash.encode('utf-8')
        else:
            password_hash_bytes = password_hash
        
        # Verify the password
        if bcrypt.checkpw(plain_password_bytes, password_hash_bytes):
            return True
        else:
            raise PasswordVerificationError("Password verification failed")
            
    except ValueError as e:
        raise PasswordVerificationError(f"Invalid password hash format: {e}")
    except Exception as e:
        raise PasswordVerificationError(f"Password verification error: {e}")
