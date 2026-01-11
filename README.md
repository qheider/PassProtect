# PassProtect MCP Server

A Model Context Protocol (MCP) server providing CRUD operations for MySQL database access.

## Features

- **Create**: Add new records to the passprotect table
- **Read**: Query records with filtering and limits
- **Update**: Modify existing records based on conditions
- **Delete**: Remove records based on conditions
- **Schema**: View table structure
- **Custom Query**: Execute custom SELECT queries

## Setup

### 1. Configure Database Connection

Edit the `.env` file with your MySQL credentials:

```env
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=quaziinfodb
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure MCP Client

Add this server to your MCP client configuration (e.g., Claude Desktop, Cline):

**For Claude Desktop** (`claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "passprotect": {
      "command": "C:/AI-Projects/Python-Projects/PassProtect/.venv/Scripts/python.exe",
      "args": ["C:/AI-Projects/Python-Projects/PassProtect/mcp_server.py"],
      "env": {
        "DB_HOST": "localhost",
        "DB_USER": "root",
        "DB_PASSWORD": "your_password",
        "DB_NAME": "quaziinfodb"
      }
    }
  }
}
```

**For Cline** (VS Code settings):
```json
{
  "mcp.servers": {
    "passprotect": {
      "command": "C:/AI-Projects/Python-Projects/PassProtect/.venv/Scripts/python.exe",
      "args": ["C:/AI-Projects/Python-Projects/PassProtect/mcp_server.py"],
      "env": {
        "DB_HOST": "localhost",
        "DB_USER": "root",
        "DB_PASSWORD": "your_password",
        "DB_NAME": "quaziinfodb"
      }
    }
  }
}
```

## Available Tools

### 1. create_record
Create a new record in the passprotect table.

**Example:**
```json
{
  "data": {
    "username": "john_doe",
    "password": "encrypted_password",
    "email": "john@example.com"
  }
}
```

### 2. read_records
Read records with optional filtering and limits.

**Example:**
```json
{
  "conditions": {
    "username": "john_doe"
  },
  "limit": 10
}
```

### 3. update_record
Update existing records based on conditions.

**Example:**
```json
{
  "data": {
    "password": "new_encrypted_password"
  },
  "conditions": {
    "id": 1
  }
}
```

### 4. delete_record
Delete records based on conditions.

**Example:**
```json
{
  "conditions": {
    "id": 1
  }
}
```

### 5. get_table_schema
Get the table structure and column information.

### 6. execute_custom_query
Execute custom SELECT queries.

**Example:**
```json
{
  "query": "SELECT username, email FROM passprotect WHERE created_at > '2024-01-01'"
}
```

## Security Notes

- The server only allows SELECT queries in custom query execution
- Update and delete operations require explicit conditions to prevent accidental full table operations
- Store database credentials securely in environment variables
- Never commit `.env` file to version control

## Testing

You can test the server by running it directly:

```bash
python mcp_server.py
```

Then interact with it through your MCP client (Claude Desktop, Cline, etc.)

## License

MIT
