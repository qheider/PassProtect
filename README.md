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

## AI Agent (passProtect.py)

PassProtect includes an OpenAI-powered AI agent that provides a natural language interface to the MCP server's database operations. The agent understands conversational requests and automatically selects and executes the appropriate database tools.

### Architecture

```
User → passProtect.py (OpenAI Agent) → MCP Server → MySQL Database
```

The AI agent acts as an intelligent client that:
1. Connects to the MCP server as a client
2. Retrieves available tools from the server
3. Processes natural language requests from users
4. Converts user intent into appropriate tool calls
5. Executes database operations via the MCP server
6. Returns user-friendly responses

### How the Agent Works

#### Agent Initialization

The `PassProtectAgent` class handles the complete agent lifecycle:

1. **OpenAI Client Setup**: Creates an OpenAI client using the API key from environment variables
2. **MCP Connection**: Connects to the MCP server using `stdio_client` and `ClientSession`
3. **Tool Discovery**: Retrieves available tools from the MCP server via `list_tools()`
4. **Tool Conversion**: Converts MCP tool definitions to OpenAI function calling format using `_convert_tools_to_openai_format()`

#### Tool Integration

The agent seamlessly integrates with all MCP server tools:

- `create_record` - Create new database records
- `read_records` - Query and retrieve records
- `update_record` - Modify existing records
- `delete_record` - Remove records
- `get_table_schema` - View table structure
- `execute_custom_query` - Run custom SELECT queries

Each tool is automatically converted to OpenAI's function calling format, enabling the GPT model to understand when and how to use them.

#### Request Processing Flow

1. **User Input**: User sends a natural language request (e.g., "Add a new user with username john")
2. **OpenAI Analysis**: Request is sent to OpenAI GPT-4o with available tools
3. **Tool Selection**: OpenAI determines which tool(s) to call based on the request
4. **Tool Execution**: Agent executes the selected MCP tool via `call_mcp_tool()` method
5. **Result Processing**: Tool results are sent back to OpenAI for interpretation
6. **User Response**: Agent returns a user-friendly natural language response

### Setup Instructions

#### Prerequisites

- Python 3.9 or higher
- OpenAI API key
- Python virtual environment
- All dependencies from `requirements.txt`

#### Environment Variables

Add the following to your `.env` file:

```env
OPENAI_API_KEY=your_openai_api_key_here
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=quaziinfodb
```

#### Installing Dependencies

```bash
pip install -r requirements.txt
```

The agent requires the following additional packages:
- `openai` - OpenAI Python SDK
- `mcp` - Model Context Protocol library
- `python-dotenv` - Environment variable management

#### Running the Agent

Start the interactive agent:

```bash
python passProtect.py
```

The agent will:
1. Load environment variables
2. Connect to the MCP server
3. Initialize available tools
4. Start interactive mode

### Usage Examples

Once started, the agent provides an interactive conversational interface:

```
You: Add a new user with username testuser, password secure123, and email test@example.com

🤖 Agent: I've successfully created a new record with the following details:
- Username: testuser
- Password: secure123
- Email: test@example.com
The record has been added to the database.
```

```
You: Show me all users

🤖 Agent: Here are all the users in the database:

1. Username: testuser
   Email: test@example.com
   ID: 1

2. Username: admin
   Email: admin@example.com
   ID: 2

Total: 2 users found
```

```
You: Update the password for user testuser to newpass456

🤖 Agent: I've successfully updated the password for user 'testuser' to 'newpass456'. The record has been modified in the database.
```

```
You: Delete the user with username testuser

🤖 Agent: I've successfully deleted the user with username 'testuser' from the database. The record has been removed.
```

### Key Features

- **Natural Language Understanding**: Interprets conversational requests without requiring specific command syntax
- **Automatic Tool Selection**: Intelligently chooses the right database operation based on user intent
- **Conversation History**: Maintains context across multiple interactions
- **Error Handling**: Provides clear, user-friendly error messages
- **Interactive Mode**: Continuous conversation with the ability to exit anytime
- **Smart Responses**: The agent provides context-aware responses and can ask clarifying questions when needed
- **Tool Visibility**: Shows which tools are being called and with what arguments

### Technical Details

#### Technology Stack

- **AI Model**: OpenAI GPT-4o with function calling capabilities
- **Communication Protocol**: MCP (Model Context Protocol) via stdio transport
- **Async Operations**: Built on Python's `asyncio` for efficient I/O handling
- **Resource Management**: Proper cleanup of connections using context managers

#### Architecture Components

1. **PassProtectAgent Class**: Main agent orchestrator
   - Manages MCP client session
   - Handles OpenAI API interactions
   - Processes tool calls and responses

2. **MCP Client Session**: Bidirectional communication with the server
   - Stdio transport for process communication
   - Async message handling
   - Tool discovery and invocation

3. **Conversation Manager**: Maintains dialogue state
   - Tracks user messages and agent responses
   - Preserves tool call history
   - Enables contextual follow-up questions

4. **Tool Adapter**: Bridges MCP and OpenAI formats
   - Converts MCP tool schemas to OpenAI function definitions
   - Translates tool results back to conversation format

## Security Notes

- The server only allows SELECT queries in custom query execution
- Update and delete operations require explicit conditions to prevent accidental full table operations
- Store database credentials securely in environment variables
- Never commit `.env` file to version control
- **AI Agent Security**: Keep your `OPENAI_API_KEY` secure and never commit it to version control

## Testing

You can test the server by running it directly:

```bash
python mcp_server.py
```

Then interact with it through your MCP client (Claude Desktop, Cline, etc.)

## License

MIT
