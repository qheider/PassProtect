"""
MCP Server for PassProtect MySQL Database CRUD Operations
Provides tools for Create, Read, Update, Delete operations on quaziinfodb.passprotect table
"""

import os
import json
from typing import Any
import mysql.connector
from mysql.connector import Error
from mcp.server import Server
from mcp.types import Tool, TextContent
import asyncio

# Database configuration from environment variables
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', ''),
    'database': os.getenv('DB_NAME', 'quaziinfodb')
}

# Authenticated user context from environment
AUTHENTICATED_USER_ID = os.getenv('USER_ID')

app = Server("passprotect-mcp-server")


def get_db_connection():
    """Create and return a database connection"""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        return connection
    except Error as e:
        raise Exception(f"Database connection failed: {e}")


def execute_query(query: str, params: tuple = None, fetch: bool = False):
    """Execute a database query with error handling"""
    connection = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(query, params or ())
        
        if fetch:
            result = cursor.fetchall()
            return result
        else:
            connection.commit()
            return {
                "success": True,
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


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List all available CRUD tools"""
    return [
        Tool(
            name="create_record",
            description="Create a new record in the passprotect table. Provide field names and values as JSON.",
            inputSchema={
                "type": "object",
                "properties": {
                    "data": {
                        "type": "object",
                        "description": "Field names and values to insert (e.g., {'username': 'john', 'password': 'secret123'})"
                    }
                },
                "required": ["data"]
            }
        ),
        Tool(
            name="read_records",
            description="Read/list multiple records from the passprotect table belonging to the authenticated user. **DO NOT use this to retrieve passwords by company name - use read_password instead.** Use read_records only for: listing all user's passwords, filtering by specific field values (id, etc.), or browsing multiple records. Automatically filters by authenticated user - only returns records created by the current user.",
            inputSchema={
                "type": "object",
                "properties": {
                    "conditions": {
                        "type": "object",
                        "description": "Additional filter conditions as key-value pairs (e.g., {'id': 1}). The user ID filter is automatically applied.",
                        "default": {}
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of records to return",
                        "default": 100
                    }
                }
            }
        ),
        Tool(
            name="update_record",
            description="Update existing record(s) in the passprotect table based on conditions.",
            inputSchema={
                "type": "object",
                "properties": {
                    "data": {
                        "type": "object",
                        "description": "Fields to update with new values (e.g., {'password': 'newpass123'})"
                    },
                    "conditions": {
                        "type": "object",
                        "description": "Conditions to match records (e.g., {'id': 1})"
                    }
                },
                "required": ["data", "conditions"]
            }
        ),
        Tool(
            name="delete_record",
            description="Delete record(s) from the passprotect table based on conditions.",
            inputSchema={
                "type": "object",
                "properties": {
                    "conditions": {
                        "type": "object",
                        "description": "Conditions to match records to delete (e.g., {'id': 1})"
                    }
                },
                "required": ["conditions"]
            }
        ),
        Tool(
            name="get_table_schema",
            description="Get the schema/structure of the passprotect table including column names and types.",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="execute_custom_query",
            description="Execute a custom SQL SELECT query on the passprotect table. Use with caution.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Custom SQL SELECT query to execute"
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="read_password",
            description="**PRIMARY TOOL for retrieving passwords by company name.** Use this when user asks for password, credentials, login info for any company/service. Supports case-insensitive and partial matching. Only returns passwords belonging to the authenticated user. Example queries: 'get password for Gmail', 'show me Netflix password', 'what's my GitHub login'.",
            inputSchema={
                "type": "object",
                "properties": {
                    "company": {
                        "type": "string",
                        "description": "The company/service name to retrieve the password for (case-insensitive, partial match supported)"
                    }
                },
                "required": ["company"]
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Handle tool calls for CRUD operations"""
    
    try:
        if name == "create_record":
            data = arguments.get("data", {})
            if not data:
                return [TextContent(type="text", text="Error: No data provided")]
            
            # Add default value for 'archived' field if not provided
            if 'archived' not in data:
                data['archived'] = 0
            
            columns = ", ".join(data.keys())
            placeholders = ", ".join(["%s"] * len(data))
            query = f"INSERT INTO passprotect ({columns}) VALUES ({placeholders})"
            
            result = execute_query(query, tuple(data.values()))
            return [TextContent(
                type="text",
                text=f"Record created successfully. Insert ID: {result['last_insert_id']}, Affected rows: {result['affected_rows']}"
            )]
        
        elif name == "read_records":
            # Security: Ensure user can only read their own records
            if not AUTHENTICATED_USER_ID:
                return [TextContent(type="text", text="Error: User authentication context not found")]
            
            conditions = arguments.get("conditions", {})
            limit = arguments.get("limit", 100)
            
            query = "SELECT * FROM passprotect WHERE created_by_user_id = %s"
            params = [AUTHENTICATED_USER_ID]
            
            if conditions:
                where_clauses = [f"{key} = %s" for key in conditions.keys()]
                query += " AND " + " AND ".join(where_clauses)
                params.extend(list(conditions.values()))
            
            query += f" LIMIT {limit}"
            
            results = execute_query(query, tuple(params), fetch=True)
            
            if not results:
                return [TextContent(type="text", text="No records found. You don't have any saved passwords yet.")]
            
            return [TextContent(
                type="text",
                text=f"Found {len(results)} record(s):\n{json.dumps(results, indent=2, default=str)}"
            )]
        
        elif name == "update_record":
            # Security: Ensure user can only update their own records
            if not AUTHENTICATED_USER_ID:
                return [TextContent(type="text", text="Error: User authentication context not found")]
            
            data = arguments.get("data", {})
            conditions = arguments.get("conditions", {})
            
            if not data:
                return [TextContent(type="text", text="Error: No data provided for update")]
            if not conditions:
                return [TextContent(type="text", text="Error: No conditions provided. Update requires conditions to prevent accidental full table update.")]
            
            set_clauses = [f"{key} = %s" for key in data.keys()]
            where_clauses = [f"{key} = %s" for key in conditions.keys()]
            
            # Add user ID constraint to prevent updating other users' records
            query = f"UPDATE passprotect SET {', '.join(set_clauses)} WHERE created_by_user_id = %s AND {' AND '.join(where_clauses)}"
            params = list(data.values()) + [AUTHENTICATED_USER_ID] + list(conditions.values())
            
            result = execute_query(query, tuple(params))
            
            if result['affected_rows'] == 0:
                return [TextContent(type="text", text="No records were updated. The record may not exist or you don't have permission to update it.")]
            
            return [TextContent(
                type="text",
                text=f"Update successful. Affected rows: {result['affected_rows']}"
            )]
        
        elif name == "delete_record":
            # Security: Ensure user can only delete their own records
            if not AUTHENTICATED_USER_ID:
                return [TextContent(type="text", text="Error: User authentication context not found")]
            
            conditions = arguments.get("conditions", {})
            
            if not conditions:
                return [TextContent(type="text", text="Error: No conditions provided. Delete requires conditions to prevent accidental full table deletion.")]
            
            where_clauses = [f"{key} = %s" for key in conditions.keys()]
            
            # Add user ID constraint to prevent deleting other users' records
            query = f"DELETE FROM passprotect WHERE created_by_user_id = %s AND {' AND '.join(where_clauses)}"
            params = [AUTHENTICATED_USER_ID] + list(conditions.values())
            
            result = execute_query(query, tuple(params))
            
            if result['affected_rows'] == 0:
                return [TextContent(type="text", text="No records were deleted. The record may not exist or you don't have permission to delete it.")]
            
            return [TextContent(
                type="text",
                text=f"Delete successful. Affected rows: {result['affected_rows']}"
            )]
        
        elif name == "get_table_schema":
            query = "DESCRIBE passprotect"
            results = execute_query(query, fetch=True)
            return [TextContent(
                type="text",
                text=f"Table schema:\n{json.dumps(results, indent=2, default=str)}"
            )]
        
        elif name == "execute_custom_query":
            query = arguments.get("query", "")
            if not query:
                return [TextContent(type="text", text="Error: No query provided")]
            
            # Security check: only allow SELECT queries
            if not query.strip().upper().startswith("SELECT"):
                return [TextContent(type="text", text="Error: Only SELECT queries are allowed")]
            
            results = execute_query(query, fetch=True)
            return [TextContent(
                type="text",
                text=f"Query results:\n{json.dumps(results, indent=2, default=str)}"
            )]
        
        elif name == "read_password":
            # Security: user_id comes from context (environment), NOT from arguments
            if not AUTHENTICATED_USER_ID:
                return [TextContent(type="text", text="Error: User authentication context not found")]
            
            company = arguments.get("company", "")
            if not company:
                return [TextContent(type="text", text="Error: Company name is required")]
            
            # Parameterized query with created_by_user_id AND companyName
            # Use LOWER() for case-insensitive comparison
            # This ensures users can ONLY access their own passwords
            query = "SELECT id, companyName, companyPassword, companyUserName, note FROM passprotect WHERE created_by_user_id = %s AND LOWER(companyName) = LOWER(%s) AND archived = 0"
            results = execute_query(query, (AUTHENTICATED_USER_ID, company), fetch=True)
            
            if not results:
                # Try partial match as fallback
                query_partial = "SELECT id, companyName, companyPassword, companyUserName, note FROM passprotect WHERE created_by_user_id = %s AND LOWER(companyName) LIKE LOWER(%s) AND archived = 0"
                results = execute_query(query_partial, (AUTHENTICATED_USER_ID, f"%{company}%"), fetch=True)
                
                if not results:
                    return [TextContent(type="text", text=f"Not found: No password for company '{company}'")]
            
            # Return the password record (or multiple if found)
            if len(results) == 1:
                record = results[0]
                return [TextContent(
                    type="text",
                    text=f"Password for {record['companyName']}:\n{json.dumps(record, indent=2, default=str)}"
                )]
            else:
                # Multiple matches found
                return [TextContent(
                    type="text",
                    text=f"Found {len(results)} matching passwords:\n{json.dumps(results, indent=2, default=str)}"
                )]
        
        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]
    
    except Exception as e:
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def main():
    """Run the MCP server"""
    from mcp.server.stdio import stdio_server
    
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
