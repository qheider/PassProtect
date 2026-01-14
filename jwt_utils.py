"""
JWT Utility Module for PassProtect
Provides JWT token creation and verification
"""

import os
import jwt
from datetime import datetime, timedelta
from typing import Dict, List
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# JWT configuration
JWT_SECRET = os.getenv('JWT_SECRET')
JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION_HOURS = 8


class TokenError(Exception):
    """Exception raised for JWT token errors"""
    pass


def create_token(user_id: int, username: str, roles: List[str]) -> str:
    """
    Create a JWT token for an authenticated user.
    
    Args:
        user_id: User ID (stored in 'sub' claim)
        username: Username from user.userName
        roles: List of role names
        
    Returns:
        Encoded JWT token string
        
    Raises:
        TokenError: If JWT_SECRET is not configured
        
    Example:
        token = create_token(1, "john_doe", ["admin", "editor"])
    """
    if not JWT_SECRET:
        raise TokenError("JWT_SECRET environment variable not configured")
    
    # Calculate expiration time (8 hours from now)
    now = datetime.utcnow()
    expiration = now + timedelta(hours=JWT_EXPIRATION_HOURS)
    
    # Build token payload
    payload = {
        'sub': str(user_id),         # Subject: user ID (must be string)
        'username': username,         # Username from user.userName
        'roles': roles,              # Array of role names
        'iat': now,                  # Issued at
        'exp': expiration            # Expiration (8 hours)
    }
    
    # Create and return the token
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token


def verify_token(token: str) -> Dict:
    """
    Verify and decode a JWT token.
    
    Args:
        token: JWT token string to verify
        
    Returns:
        Dictionary containing the decoded token payload with:
            - sub: User ID
            - username: Username
            - roles: List of role names
            - iat: Issued at timestamp
            - exp: Expiration timestamp
            
    Raises:
        TokenError: If token is expired, invalid, or JWT_SECRET not configured
        
    Example:
        try:
            payload = verify_token(token)
            print(f"User: {payload['username']}")
            print(f"Roles: {payload['roles']}")
        except TokenError as e:
            print(f"Invalid token: {e}")
    """
    if not JWT_SECRET:
        raise TokenError("JWT_SECRET environment variable not configured")
    
    try:
        # Decode and verify the token
        payload = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM]
        )
        return payload
        
    except jwt.ExpiredSignatureError:
        raise TokenError("Token has expired")
    except jwt.InvalidTokenError as e:
        raise TokenError(f"Invalid token: {str(e)}")
    except Exception as e:
        raise TokenError(f"Token verification failed: {str(e)}")
