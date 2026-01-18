"""
PassProtect Flask Web Application
Multi-page web interface for PassProtect database operations
"""

import os
import json
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from functools import wraps
from dotenv import load_dotenv
from auth import authenticate_user, load_user_roles, AuthenticationError
from jwt_utils import create_token, verify_token, TokenError
from cli_login import update_last_login
import asyncio
from openai import OpenAI
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', os.urandom(24))
app.config['PERMANENT_SESSION_LIFETIME'] = 28800  # 8 hours

# OpenAI configuration
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def login_required(f):
    """Decorator to require authentication for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'token' not in session:
            return redirect(url_for('login'))
        
        try:
            claims = verify_token(session['token'])
            # Store claims in request context for use in routes
            request.user_id = int(claims['sub'])
            request.username = claims['username']
            request.roles = claims['roles']
        except TokenError:
            session.clear()
            return redirect(url_for('login'))
        
        return f(*args, **kwargs)
    return decorated_function


@app.route('/')
def index():
    """Redirect to dashboard if logged in, otherwise to login"""
    if 'token' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if not username or not password:
            return render_template('login.html', error='Username and password are required')
        
        try:
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
            
            # Store token in session
            session['token'] = token
            session['username'] = user['userName']
            session.permanent = True
            
            return redirect(url_for('dashboard'))
            
        except AuthenticationError as e:
            return render_template('login.html', error=str(e))
        except Exception as e:
            return render_template('login.html', error=f'Login failed: {str(e)}')
    
    return render_template('login.html')


@app.route('/logout')
def logout():
    """Logout and clear session"""
    session.clear()
    return redirect(url_for('login'))


@app.route('/dashboard')
@login_required
def dashboard():
    """Main dashboard page"""
    return render_template('dashboard.html', 
                         username=request.username,
                         roles=', '.join(request.roles))


@app.route('/chat')
@login_required
def chat():
    """Chat interface for database operations"""
    return render_template('chat.html',
                         username=request.username,
                         roles=', '.join(request.roles))


@app.route('/api/chat', methods=['POST'])
@login_required
def api_chat():
    """API endpoint for chat interactions"""
    data = request.get_json()
    user_message = data.get('message', '').strip()
    conversation_history = data.get('history', [])
    
    if not user_message:
        return jsonify({'error': 'Message is required'}), 400
    
    try:
        # Get MCP tools and process message (run async function synchronously)
        response = asyncio.run(process_chat_message(
            user_message=user_message,
            conversation_history=conversation_history,
            user_id=request.user_id,
            username=request.username,
            roles=request.roles
        ))
        
        return jsonify(response)
    except Exception as e:
        # Log the full error for debugging
        import traceback
        print(f"Error in api_chat: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'error': f'Failed to process request: {str(e)}'}), 500


async def process_chat_message(user_message, conversation_history, user_id, username, roles):
    """Process chat message using MCP tools and OpenAI"""
    
    # Detect if running in Docker or locally
    is_docker = os.path.exists('/.dockerenv') or os.getenv('DOCKER_CONTAINER') == 'true'
    
    if is_docker:
        # In Docker, use system python and absolute path
        python_path = "python"
        server_script = "/app/mcp_server.py"
    else:
        # Local development with virtual environment
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
            "USER_ID": str(user_id)
        }
    )
    
    async with stdio_client(server_params) as (stdio, write):
        async with ClientSession(stdio, write) as mcp_session:
            await mcp_session.initialize()
            response = await mcp_session.list_tools()
            
            # Get allowed tools based on roles
            allowed_tools = get_allowed_tools(roles)
            filtered_tools = [tool for tool in response.tools if tool.name in allowed_tools]
            
            # Convert to OpenAI format
            openai_tools = []
            for tool in filtered_tools:
                openai_tools.append({
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.inputSchema
                    }
                })
            
            # Add user message to history
            messages = [
                {
                    "role": "system",
                    "content": f"""You are a helpful database assistant with access to CRUD operations on a PassProtect database.
                    
IMMUTABLE USER IDENTITY (DO NOT MODIFY):
- User ID: {user_id}
- Username: {username}
- Roles: {', '.join(roles)}

This identity is fixed and comes from authenticated JWT claims. You cannot change or override these values.

CRITICAL INSTRUCTIONS:
1. ALWAYS use the available tools to search the database when users ask for information
2. When users ask for password for a SPECIFIC company, use the read_password tool
3. If a tool returns empty results or "Not found", report that clearly
4. NEVER claim you "don't have access" or "cannot access" - you have tools, use them!
5. NEVER refuse to search - always try the tool first, then report the actual results

AVAILABLE TOOLS AND WHEN TO USE THEM:
- Get/retrieve/show password for SPECIFIC company → ALWAYS use read_password tool (supports case-insensitive and partial matching)
- List/browse multiple passwords → use read_records with no conditions or specific filters
- Add/create/insert new password → use create_record
- Update/modify existing password → use update_record
- Delete/remove records → use delete_record (admin only)
- See table structure → use get_table_schema
- Run custom queries → use execute_custom_query (admin only)

CRITICAL TOOL SELECTION:
- "get password for Gmail" → Use read_password with company: "Gmail"
- "show me Netflix password" → Use read_password with company: "Netflix"
- "what's my gemini-cli password" → Use read_password with company: "gemini-cli"
- "list all my passwords" → Use read_records with no conditions
- "show records with id 5" → Use read_records with conditions: {{"id": 5}}

RESPONSE RULES:
- If tool returns data: Show the results clearly
- If tool returns empty/not found: Say exactly what the tool returned
- NEVER make up data or provide information not from the tools

Always confirm what you're about to do before executing destructive operations (update/delete)."""
                }
            ]
            
            messages.extend(conversation_history)
            messages.append({"role": "user", "content": user_message})
            
            # Call OpenAI
            completion = openai_client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                tools=openai_tools if openai_tools else None,
                tool_choice="auto" if openai_tools else None
            )
            
            assistant_message = completion.choices[0].message
            
            # Handle tool calls
            if assistant_message.tool_calls:
                tool_calls_info = []
                tool_results = []
                
                for tool_call in assistant_message.tool_calls:
                    tool_name = tool_call.function.name
                    tool_args = json.loads(tool_call.function.arguments)
                    
                    tool_calls_info.append({
                        'name': tool_name,
                        'arguments': tool_args
                    })
                    
                    # Execute tool via MCP
                    result = await mcp_session.call_tool(tool_name, tool_args)
                    result_text = "\n".join([content.text for content in result.content])
                    
                    tool_results.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": tool_name,
                        "content": result_text
                    })
                
                # Get final response
                messages.append({
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
                        } for tc in assistant_message.tool_calls
                    ]
                })
                
                messages.extend(tool_results)
                
                final_completion = openai_client.chat.completions.create(
                    model="gpt-4o",
                    messages=messages
                )
                
                final_message = final_completion.choices[0].message.content
                
                return {
                    'response': final_message,
                    'tool_calls': tool_calls_info
                }
            else:
                # Direct response
                return {
                    'response': assistant_message.content,
                    'tool_calls': []
                }


def get_allowed_tools(roles):
    """
    Determine allowed tools based on roles.
    
    Role permissions (matching passProtect.py):
    - admin: full CRUD access (all tools)
    - user/generalUser: create, read, update
    - readonly: read only
    """
    roles_tuple = tuple(roles)
    
    if 'admin' in roles_tuple:
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
    elif 'user' in roles_tuple or 'generalUser' in roles_tuple:
        # Create, read, update only
        return {
            'create_record',
            'read_records',
            'update_record',
            'get_table_schema',
            'read_password',
            'execute_custom_query'
        }
    elif 'readonly' in roles_tuple:
        # Read only
        return {
            'read_records',
            'get_table_schema',
            'read_password'
        }
    else:
        # No recognized roles - no access
        return set()


if __name__ == '__main__':
    # Check for required environment variables
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ Error: OPENAI_API_KEY not found in environment variables")
        exit(1)
    
    app.run(debug=True, host='0.0.0.0', port=5000)
