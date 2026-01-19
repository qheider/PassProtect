"""
Database Access Layer for PassProtect
Provides low-level database operations with parameterized queries
"""

import os
import mysql.connector
from mysql.connector import Error
from typing import Optional, List, Dict, Any, Tuple
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', ''),
    'database': os.getenv('DB_NAME', 'quaziinfodb')
}


def _get_connection():
    """
    Create and return a database connection.
    
    Returns:
        mysql.connector.connection: Database connection object
        
    Raises:
        Exception: If connection fails
    """
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        return connection
    except Error as e:
        raise Exception(f"Database connection failed: {e}")


def fetch_one(sql: str, params: Optional[Tuple] = None) -> Optional[Dict[str, Any]]:
    """
    Execute a SELECT query and return a single row.
    
    Args:
        sql: SQL query string with placeholders (%s)
        params: Tuple of parameters for the query
        
    Returns:
        Dictionary containing the row data, or None if no results
        
    Raises:
        Exception: If query execution fails
        
    Example:
        result = fetch_one("SELECT * FROM user WHERE id = %s", (1,))
    """
    connection = None
    try:
        connection = _get_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(sql, params or ())
        result = cursor.fetchone()
        return result
    except Error as e:
        raise Exception(f"Query execution failed: {e}")
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()


def fetch_all(sql: str, params: Optional[Tuple] = None) -> List[Dict[str, Any]]:
    """
    Execute a SELECT query and return all matching rows.
    
    Args:
        sql: SQL query string with placeholders (%s)
        params: Tuple of parameters for the query
        
    Returns:
        List of dictionaries containing row data
        
    Raises:
        Exception: If query execution fails
        
    Example:
        results = fetch_all("SELECT * FROM user WHERE enabled = %s", (1,))
    """
    connection = None
    try:
        connection = _get_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(sql, params or ())
        results = cursor.fetchall()
        return results
    except Error as e:
        raise Exception(f"Query execution failed: {e}")
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()


def execute(sql: str, params: Optional[Tuple] = None) -> Dict[str, Any]:
    """
    Execute an INSERT, UPDATE, or DELETE query.
    
    Args:
        sql: SQL query string with placeholders (%s)
        params: Tuple of parameters for the query
        
    Returns:
        Dictionary with execution results:
            - affected_rows: Number of rows affected
            - last_insert_id: ID of last inserted row (for INSERT)
            
    Raises:
        Exception: If query execution fails
        
    Example:
        result = execute("INSERT INTO user (userName, email, password) VALUES (%s, %s, %s)", 
                        ('john', 'john@example.com', 'hashed_password'))
    """
    connection = None
    try:
        connection = _get_connection()
        cursor = connection.cursor()
        cursor.execute(sql, params or ())
        connection.commit()
        
        return {
            "affected_rows": cursor.rowcount,
            "last_insert_id": cursor.lastrowid
        }
    except Error as e:
        if connection:
            connection.rollback()
        raise Exception(f"Query execution failed: {e}")
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()


def register_new_user(username: str, email: str, password: str) -> int:
    """
    Register a new user in the database.
    
    Args:
        username: Username for the new user
        email: Email address for the new user
        password: Plain text password (will be hashed)
        
    Returns:
        The user ID of the newly created user
        
    Raises:
        Exception: If username or email already exists, or if registration fails
    """
    import bcrypt
    from datetime import datetime
    
    # Check if username already exists
    existing_user = fetch_one("SELECT id FROM user WHERE userName = %s", (username,))
    if existing_user:
        raise Exception(f"Username '{username}' is already taken")
    
    # Check if email already exists
    existing_email = fetch_one("SELECT id FROM user WHERE email = %s", (email,))
    if existing_email:
        raise Exception(f"Email '{email}' is already registered")
    
    # Hash the password
    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    # Insert new user
    sql = """
        INSERT INTO user (userName, email, password, enabled, archived, date_created, date_updated, created_by_user_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """
    
    now = datetime.now()
    params = (username, email, password_hash, 1, 0, now, now, None)
    
    result = execute(sql, params)
    user_id = result['last_insert_id']
    
    # Assign default role (generalUser with id=5)
    role_sql = """
        INSERT INTO users_roles (users_ID, roles_ID)
        VALUES (%s, %s)
    """
    execute(role_sql, (user_id, 5))
    
    return user_id
