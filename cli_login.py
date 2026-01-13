"""
CLI Login Command for PassProtect
Provides command-line authentication interface
"""

import os
import json
import getpass
from pathlib import Path
from datetime import datetime
from auth import authenticate_user, load_user_roles, AuthenticationError
from jwt_utils import create_token, TokenError
from db_access import execute


# Session file path
SESSION_DIR = Path.home() / ".passprotect"
SESSION_FILE = SESSION_DIR / "session.json"


def update_last_login(user_id: int):
    """
    Update the lastLogin field for a user.
    
    Args:
        user_id: The ID of the user to update
    """
    sql = "UPDATE user SET lastLogin = %s WHERE id = %s"
    current_time = datetime.now()
    execute(sql, (current_time, user_id))


def save_session(token: str):
    """
    Save the JWT token to session file with secure permissions.
    
    Args:
        token: JWT token to save
    """
    # Create directory if it doesn't exist
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    
    # Save token to file
    session_data = {
        "token": token,
        "created_at": datetime.now().isoformat()
    }
    
    with open(SESSION_FILE, 'w') as f:
        json.dump(session_data, f, indent=2)
    
    # Set file permissions to 600 (read/write for owner only)
    os.chmod(SESSION_FILE, 0o600)


def login():
    """
    CLI login command.
    
    Prompts for username and password, authenticates the user,
    loads roles, generates JWT token, and saves session.
    """
    try:
        # Prompt for credentials
        username = input("Username: ").strip()
        password = getpass.getpass("Password: ")
        
        if not username or not password:
            print("Error: Username and password are required")
            return
        
        # Authenticate user
        user = authenticate_user(username, password)
        
        # Load user roles
        roles = load_user_roles(user['id'])
        
        # Generate JWT token
        token = create_token(
            user_id=user['id'],
            username=user['userName'],
            roles=roles
        )
        
        # Update lastLogin timestamp
        update_last_login(user['id'])
        
        # Save session
        save_session(token)
        
        # Print success message
        print(f"✓ Login successful. Welcome, {user['userName']}!")
        
    except AuthenticationError as e:
        print(f"Authentication failed: {e}")
    except TokenError as e:
        print(f"Token generation failed: {e}")
    except Exception as e:
        print(f"Login failed: {e}")


if __name__ == "__main__":
    login()
