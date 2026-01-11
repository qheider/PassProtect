"""
PassProtect AI Agent
An OpenAI-powered agent that uses MCP tools to perform CRUD operations on the PassProtect database
"""

import os
import json
import asyncio
from typing import Any
from openai import OpenAI
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# OpenAI configuration
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class PassProtectAgent:
    """AI Agent that uses MCP tools for database operations"""
    
    def __init__(self):
        self.session = None
        self.tools = []
        self.conversation_history = []
        self.client_context = None
        
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
                "DB_NAME": os.getenv("DB_NAME", "quaziinfodb")
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
        
        # Convert MCP tools to OpenAI function format
        self.tools = self._convert_tools_to_openai_format(response.tools)
        
        print(f"✓ Connected to MCP server")
        print(f"✓ Available tools: {', '.join([t['function']['name'] for t in self.tools])}\n")
        
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
                    "content": """You are a helpful database assistant with access to CRUD operations on a PassProtect database.
                    
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


async def main():
    """Main entry point"""
    agent = PassProtectAgent()
    
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
