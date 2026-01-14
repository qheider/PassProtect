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
