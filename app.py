"""
PassProtect Flask Web Application
Multi-page web interface for PassProtect database operations
"""

import os
import json
import re
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

# Ollama configuration (using OpenAI SDK with custom base_url)
openai_client = OpenAI(
    api_key="ollama",  # Ollama doesn't require a real API key
    base_url=f"http://{os.getenv('OLLAMA_HOST')}/v1"
)


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


@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration page"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        # Validation
        if not username or not email or not password:
            return render_template('register.html', error='All fields are required')
        
        if password != confirm_password:
            return render_template('register.html', error='Passwords do not match')
        
        if len(password) < 8:
            return render_template('register.html', error='Password must be at least 8 characters long')
        
        try:
            # Register user
            from db_access import register_new_user
            user_id = register_new_user(username, email, password)
            
            return render_template('register.html', success=f'Registration successful! You can now login with username: {username}')
            
        except Exception as e:
            return render_template('register.html', error=str(e))
    
    return render_template('register.html')


@app.route('/logout')
def logout():
    """Logout and clear session"""
    session.clear()
    return redirect(url_for('login'))


@app.route('/dashboard')
@login_required
def dashboard():
    """Main dashboard page"""
    # Fetch recent searches
    recent_searches = asyncio.run(fetch_recent_searches(request.user_id, limit=5))
    
    return render_template('dashboard.html', 
                         username=request.username,
                         roles=', '.join(request.roles),
                         recent_searches=recent_searches)


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


async def fetch_record_for_update(user_id, company_name):
    """Fetch a record for update form pre-filling"""
    try:
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
            async with ClientSession(stdio, write) as session:
                await session.initialize()
                result = await session.call_tool("read_password", {"company": company_name})
                result_text = "\n".join([content.text for content in result.content])
                
                if 'Password for' in result_text and '{' in result_text:
                    json_start = result_text.index('{')
                    json_end = result_text.rindex('}') + 1
                    json_str = result_text[json_start:json_end]
                    return json.loads(json_str)
                return None
    except Exception as e:
        print(f"Error fetching record: {e}")
        return None


async def fetch_recent_searches(user_id, limit=10):
    """Fetch recent search history from MCP"""
    try:
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
            async with ClientSession(stdio, write) as session:
                await session.initialize()
                result = await session.call_tool("get_recent_searches", {"limit": limit})
                result_text = "\n".join([content.text for content in result.content])
                
                if 'Recent searches' in result_text and '[' in result_text:
                    json_start = result_text.index('[')
                    json_end = result_text.rindex(']') + 1
                    json_str = result_text[json_start:json_end]
                    return json.loads(json_str)
                
                return []
    except Exception as e:
        print(f"Error fetching recent searches: {e}")
        return []


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
6. When users ask to CREATE/ADD a new password WITHOUT providing all details, simply acknowledge and let the UI form handle it
7. When users ask to UPDATE/MODIFY a password WITHOUT providing all details, acknowledge and let the UI form handle it
8. DO NOT ask for details when user wants to create or update - the form will collect them

AVAILABLE TOOLS AND WHEN TO USE THEM:
- Get/retrieve/show password for SPECIFIC company → ALWAYS use read_password tool (supports case-insensitive and partial matching)
- List/browse multiple passwords → use read_records with no conditions or specific filters
- Add/create/insert new password WITH complete data provided → use create_record tool
- Add/create/insert new password WITHOUT complete data → acknowledge request (form UI will collect data)
- Update/modify existing password WITH complete data provided → use update_record
- Update/modify existing password WITHOUT complete data → acknowledge request (form UI will collect data)
- Delete/remove records → use delete_record (admin only)
- See table structure → use get_table_schema
- Run custom queries → use execute_custom_query (admin only)

CRITICAL TOOL SELECTION:
- "get password for Gmail" → Use read_password with company: "Gmail"
- "show me Netflix password" → Use read_password with company: "Netflix"
- "what's my gemini-cli password" → Use read_password with company: "gemini-cli"
- "list all my passwords" → Use read_records with no conditions
- "show records with id 5" → Use read_records with conditions: {{"id": 5}}
- "Create a new password record with the following details: Company Name: X, Password: Y, Username: Z" → Use create_record tool with exact column names

CREATING NEW RECORDS:
When user provides data in format like:
"Create a new password record with the following details:
- Company Name: [name]
- Password: [password]
- Username: [username]
- Note: [note]"

You MUST use create_record tool with this exact format:
{{
  "data": {{
    "companyName": "[name]",
    "companyPassword": "[password]",
    "companyUserName": "[username]",
    "note": "[note]",
    "created_by_user_id": {user_id}
  }}
}}

UPDATING EXISTING RECORDS:
When user provides update data in format like:
"Update the password record for company \"[name]\" (ID: [id]) with the following changes:
- Password: [new_password]
- Username: [new_username]
- Note: [new_note]"

You MUST use update_record tool with this exact format:
{{
  "data": {{
    "companyPassword": "[new_password]",
    "companyUserName": "[new_username]",
    "note": "[new_note]"
  }},
  "conditions": {{
    "id": [id]
  }}
}}
Only include fields that are being updated (don't include fields that aren't mentioned).

RESPONSE RULES:
- If tool returns data: Show the results clearly
- If tool returns empty/not found: Say exactly what the tool returned
- NEVER make up data or provide information not from the tools
- After creating a record, confirm what was created

Always confirm what you're about to do before executing destructive operations (update/delete)."""
                }
            ]
            
            messages.extend(conversation_history)
            messages.append({"role": "user", "content": user_message})
            
            # Call OpenAI
            completion = openai_client.chat.completions.create(
                model=os.getenv("OLLAMA_MODEL", "gpt-oss:20b"),
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
                    model=os.getenv("OLLAMA_MODEL", "gpt-oss:20b"),
                    messages=messages
                )
                
                final_message = final_completion.choices[0].message.content
                
                # Extract password data if read_password was called
                password_data = None
                for tool_call, result in zip(tool_calls_info, tool_results):
                    if tool_call['name'] == 'read_password':
                        # Parse the JSON response from tool result
                        try:
                            result_text = result['content']
                            if 'Password for' in result_text and '{' in result_text:
                                # Extract JSON from result
                                json_start = result_text.index('{')
                                json_end = result_text.rindex('}') + 1
                                json_str = result_text[json_start:json_end]
                                password_data = json.loads(json_str)
                        except Exception:
                            pass  # If parsing fails, just use text response
                
                return {
                    'response': final_message,
                    'tool_calls': tool_calls_info,
                    'password_data': password_data
                }
            else:
                # Direct response - check if this is a create/update record request
                show_form = False
                show_update_form = False
                record_data = None
                response_text = assistant_message.content
                
                # Detect if user is asking to create a new record
                create_keywords = ['create', 'add', 'new record', 'new password', 'save password', 'store password']
                update_keywords = ['update', 'modify', 'change', 'edit']
                user_message_lower = user_message.lower()
                
                if any(keyword in user_message_lower for keyword in create_keywords):
                    # Check if they're NOT providing data already
                    has_data = any(indicator in user_message_lower for indicator in ['company:', 'password:', 'name:', '- company', '- password'])
                    
                    if not has_data:
                        show_form = True
                        response_text = "I'll help you create a new password record. Please fill in the form below with the details."
                
                elif any(keyword in user_message_lower for keyword in update_keywords):
                    # Check if they're asking to update without providing details
                    has_data = any(indicator in user_message_lower for indicator in ['password:', '- password', '- username', 'with the following'])
                    
                    if not has_data:
                        # Extract company name from the message
                        # Try multiple patterns to find company name
                        company_name = None
                        
                        # Pattern 1: "update [company]" or "update a record [company]"
                        match = re.search(r'(?:update|modify|change|edit)(?:\s+(?:a\s+)?record)?(?:\s+for)?\s+(.+?)(?:\s*$)', user_message_lower)
                        if match:
                            potential_name = match.group(1).strip()
                            # Clean up common filler words
                            potential_name = re.sub(r'^(?:for|company|the|a|an)\s+', '', potential_name)
                            if potential_name and len(potential_name) > 1:
                                company_name = potential_name
                        
                        # Pattern 2: Just a company name after update discussion
                        if not company_name and len(user_message.strip().split()) <= 3:
                            # If message is short (1-3 words) after update context, treat as company name
                            company_name = user_message.strip()
                        
                        if company_name:
                            # Fetch the record using a separate async call
                            record_data = await fetch_record_for_update(user_id, company_name)
                            
                            if record_data:
                                show_update_form = True
                                response_text = f"I found the record for {company_name}. Please update the fields you want to change in the form below."
                            else:
                                response_text = f"I couldn't find a record for '{company_name}'. Please check the company name and try again."
                        else:
                            response_text = "Please specify which company's record you want to update."
                
                return {
                    'response': response_text,
                    'tool_calls': [],
                    'show_form': show_form,
                    'show_update_form': show_update_form,
                    'record_data': record_data
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
