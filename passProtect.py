"""
PassProtect AI Agent
An OpenAI-powered agent that uses MCP tools to perform CRUD operations on the PassProtect database
"""

import os
import json
import asyncio
import getpass
from typing import Any, Dict
from openai import OpenAI
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from dotenv import load_dotenv
from session import require_auth, SessionError
from auth import authenticate_user, load_user_roles, AuthenticationError
from jwt_utils import create_token, TokenError
from cli_login import save_session, update_last_login

# Load environment variables
load_dotenv()

# OpenAI configuration
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class PassProtectAgent:
    """AI Agent that uses MCP tools for database operations"""
    
    def __init__(self, user_context: Dict):
        """
        Initialize agent with immutable user identity.
        
        Args:
            user_context: Immutable user identity from JWT claims containing:
                - user_id: User ID
                - username: Username
                - roles: List of role names
        """
        self.session = None
        self.tools = []
        self.conversation_history = []
        self.client_context = None
        
        # Immutable identity context from JWT - CANNOT be modified
        self._user_id = user_context['user_id']
        self._username = user_context['username']
        self._roles = tuple(user_context['roles'])  # Tuple for immutability
    
    def _get_allowed_tools(self) -> set:
        """
        Determine which MCP tools are allowed based on user roles.
        
        Role permissions:
        - admin: full CRUD access (all tools)
        - user/generalUser: create, read, update
        - readonly: read only
        
        Returns:
            Set of allowed tool names
        """
        # Check roles in order of permissions (most permissive first)
        if 'admin' in self._roles:
            # Full CRUD access
            return {
                'create_record',
                'read_records',
                'update_record',
                'delete_record',
                'get_table_schema',
                'execute_custom_query',
                'read_password'
            }
        elif 'user' in self._roles or 'generalUser' in self._roles:
            # Create, read, update only
            return {
                'create_record',
                'read_records',
                'update_record',
                'get_table_schema',
                'read_password'
            }
        elif 'readonly' in self._roles:
            # Read only
            return {
                'read_records',
                'get_table_schema',
                'read_password'
            }
        else:
            # No recognized roles - no access
            return set()
        
    async def connect_to_mcp(self):
        """Connect to the MCP server and retrieve available tools"""
        # Get the Python executable path from the virtual environment
        python_path = os.path.join(os.path.dirname(__file__), ".venv", "Scripts", "python.exe")
        server_script = os.path.join(os.path.dirname(__file__), "mcp_server.py")
        
        server_params = StdioServerParameters(
            command=python_path,
            args=[server_script],
            env={
                "DB_HOST": os.getenv("DB_HOST", "localhost"),
                "DB_USER": os.getenv("DB_USER", "root"),
                "DB_PASSWORD": os.getenv("DB_PASSWORD", ""),
                "DB_NAME": os.getenv("DB_NAME", "quaziinfodb"),
                "USER_ID": str(self._user_id)  # Pass authenticated user ID to MCP server
            }
        )
        
        # Use context manager properly
        self.client_context = stdio_client(server_params)
        stdio_transport = await self.client_context.__aenter__()
        self.stdio, self.write = stdio_transport
        self.session = ClientSession(self.stdio, self.write)
        
        await self.session.__aenter__()
        
        # Initialize and get tools
        await self.session.initialize()
        response = await self.session.list_tools()
        
        # Get allowed tools based on user roles
        allowed_tools = self._get_allowed_tools()
        
        # Filter tools by role permissions
        filtered_tools = [tool for tool in response.tools if tool.name in allowed_tools]
        
        # Convert MCP tools to OpenAI function format
        self.tools = self._convert_tools_to_openai_format(filtered_tools)
        
        print(f"✓ Connected to MCP server")
        print(f"✓ Authenticated as: {self._username} (ID: {self._user_id})")
        print(f"✓ Roles: {', '.join(self._roles)}")
        print(f"✓ Available tools ({len(self.tools)}): {', '.join([t['function']['name'] for t in self.tools])}\n")
        
    def _convert_tools_to_openai_format(self, mcp_tools):
        """Convert MCP tool definitions to OpenAI function calling format"""
        openai_tools = []
        for tool in mcp_tools:
            openai_tools.append({
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.inputSchema
                }
            })
        return openai_tools
    
    async def call_mcp_tool(self, tool_name: str, arguments: dict) -> str:
        """Call an MCP tool and return the result"""
        result = await self.session.call_tool(tool_name, arguments)
        
        # Extract text content from result
        if result.content:
            return "\n".join([item.text for item in result.content if hasattr(item, 'text')])
        return "No response from tool"
    
    async def process_request(self, user_message: str) -> str:
        """Process user request using OpenAI agent with tool calling"""
        
        # Add user message to conversation history
        self.conversation_history.append({
            "role": "user",
            "content": user_message
        })
        
        # Call OpenAI with tools
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": f"""You are a helpful database assistant with access to CRUD operations on a PassProtect database.
                    
IMMUTABLE USER IDENTITY (DO NOT MODIFY):
- User ID: {self._user_id}
- Username: {self._username}
- Roles: {', '.join(self._roles)}

This identity is fixed and comes from authenticated JWT claims. You cannot change or override these values.

ACCESS CONTROL:
You only have access to the tools that are registered based on your roles.
The tools available to you are already filtered - do not attempt to use tools you don't have access to.
                    
Your job is to:
1. Understand user requests for database operations
2. Use the appropriate tools to perform those operations
3. Provide clear, friendly responses about what was done

When users ask to:
- Add/create/insert records → use create_record
- View/read/get/list records → use read_records
- Update/modify records → use update_record
- Delete/remove records → use delete_record
- See table structure → use get_table_schema
- Run custom queries → use execute_custom_query

Always confirm what you're about to do before executing destructive operations (update/delete)."""
                }
            ] + self.conversation_history,
            tools=self.tools,
            tool_choice="auto"
        )
        
        assistant_message = response.choices[0].message
        
        # Check if the model wants to call a tool
        if assistant_message.tool_calls:
            # Add assistant's response to history
            self.conversation_history.append({
                "role": "assistant",
                "content": assistant_message.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    }
                    for tc in assistant_message.tool_calls
                ]
            })
            
            # Execute each tool call
            for tool_call in assistant_message.tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                
                print(f"🔧 Calling tool: {function_name}")
                print(f"   Arguments: {json.dumps(function_args, indent=2)}")
                
                # Call the MCP tool
                tool_result = await self.call_mcp_tool(function_name, function_args)
                
                # Add tool result to conversation
                self.conversation_history.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": tool_result
                })
            
            # Get final response from the model after tool execution
            final_response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful database assistant. Summarize the results of the operations in a clear, user-friendly way."
                    }
                ] + self.conversation_history
            )
            
            final_message = final_response.choices[0].message.content
            self.conversation_history.append({
                "role": "assistant",
                "content": final_message
            })
            
            return final_message
        else:
            # No tool call needed, return the direct response
            self.conversation_history.append({
                "role": "assistant",
                "content": assistant_message.content
            })
            return assistant_message.content
    
    async def interactive_mode(self):
        """Run the agent in interactive mode"""
        print("=" * 60)
        print("PassProtect AI Agent")
        print("=" * 60)
        print("\nConnecting to database...")
        
        await self.connect_to_mcp()
        
        print("Agent ready! You can ask me to:")
        print("  • Create new records")
        print("  • Read/search records")
        print("  • Update existing records")
        print("  • Delete records")
        print("  • View table schema")
        print("\nType 'exit' or 'quit' to stop.\n")
        
        while True:
            try:
                user_input = input("You: ").strip()
                
                if not user_input:
                    continue
                    
                if user_input.lower() in ['exit', 'quit', 'bye']:
                    print("\n👋 Goodbye!")
                    break
                
                print("\n🤖 Agent:", end=" ")
                response = await self.process_request(user_input)
                print(response)
                print()
                
            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"\n❌ Error: {str(e)}\n")
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.session:
            await self.session.__aexit__(None, None, None)
        if self.client_context:
            await self.client_context.__aexit__(None, None, None)


def perform_login():
    """
    Perform interactive login when authentication is required.
    Returns the JWT claims if successful, None otherwise.
    """
    print("\n" + "="*60)
    print("Authentication Required")
    print("="*60)
    print("Please login to continue:\n")
    
    try:
        # Prompt for credentials
        username = input("Username: ").strip()
        password = getpass.getpass("Password: ")
        
        if not username or not password:
            print("❌ Error: Username and password are required")
            return None
        
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
        
        print(f"✓ Login successful. Welcome, {user['userName']}!\n")
        
        # Return claims for immediate use
        return {
            'sub': str(user['id']),
            'username': user['userName'],
            'roles': roles
        }
        
    except AuthenticationError as e:
        print(f"❌ Authentication failed: {e}")
        return None
    except TokenError as e:
        print(f"❌ Token generation failed: {e}")
        return None
    except Exception as e:
        print(f"❌ Login failed: {e}")
        return None


async def main():
    """Main entry point"""
    # STEP 1: Check authentication, prompt for login if needed
    claims = None
    try:
        claims = require_auth()
    except SessionError as e:
        # Authentication failed, prompt for login
        claims = perform_login()
        
        if not claims:
            print("\n❌ Authentication failed. Exiting.\n")
            exit(1)
    
    # STEP 2: Build immutable user context from JWT claims
    user_context = {
        'user_id': int(claims['sub']),  # Convert string back to int
        'username': claims['username'],
        'roles': claims['roles']
    }
    
    # STEP 3: Initialize agent with immutable identity
    agent = PassProtectAgent(user_context)
    
    try:
        await agent.interactive_mode()
    finally:
        await agent.cleanup()


if __name__ == "__main__":
    # Check for OpenAI API key
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ Error: OPENAI_API_KEY not found in environment variables")
        print("Please add it to your .env file:")
        print("OPENAI_API_KEY=your_api_key_here")
        exit(1)
    
    asyncio.run(main())
