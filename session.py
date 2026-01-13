"""
Session Handler and Authentication Guard for PassProtect CLI
Provides session management and authentication verification
"""

import os
import json
from pathlib import Path
from typing import Dict, Optional
from jwt_utils import verify_token, TokenError


# Session file path
SESSION_DIR = Path.home() / ".passprotect"
SESSION_FILE = SESSION_DIR / "session.json"


class SessionError(Exception):
    """Exception raised for session-related errors"""
    pass


def load_session() -> Optional[str]:
    """
    Load JWT token from session file.
    
    Returns:
        JWT token string if session exists, None otherwise
        
    Raises:
        SessionError: If session file exists but cannot be read
    """
    if not SESSION_FILE.exists():
        return None
    
    try:
        with open(SESSION_FILE, 'r') as f:
            session_data = json.load(f)
            return session_data.get('token')
    except Exception as e:
        raise SessionError(f"Failed to load session: {e}")


def require_auth() -> Dict:
    """
    Authentication guard that verifies and returns JWT claims.
    
    This function MUST be called before any authenticated CLI operation.
    It loads the session token, verifies it, and returns the decoded claims.
    
    Returns:
        Dictionary containing decoded JWT claims:
            - sub: User ID
            - username: Username
            - roles: List of role names
            - iat: Issued at timestamp
            - exp: Expiration timestamp
            
    Raises:
        SessionError: If token is missing, invalid, or expired
        
    Example:
        try:
            claims = require_auth()
            print(f"Authenticated as: {claims['username']}")
            print(f"User ID: {claims['sub']}")
            print(f"Roles: {claims['roles']}")
        except SessionError as e:
            print(f"Authentication required: {e}")
            print("Please login using: python cli_login.py")
            exit(1)
    """
    # Load token from session file
    token = load_session()
    
    if not token:
        raise SessionError(
            "No active session found. Please login first.\n"
            "Run: python cli_login.py"
        )
    
    # Verify and decode token
    try:
        claims = verify_token(token)
        return claims
    except TokenError as e:
        raise SessionError(
            f"Session expired or invalid: {e}\n"
            "Please login again using: python cli_login.py"
        )


def clear_session():
    """
    Clear the current session by removing the session file.
    
    Used for logout functionality.
    """
    if SESSION_FILE.exists():
        SESSION_FILE.unlink()


def is_authenticated() -> bool:
    """
    Check if user is currently authenticated.
    
    Returns:
        True if valid session exists, False otherwise
    """
    try:
        require_auth()
        return True
    except SessionError:
        return False
