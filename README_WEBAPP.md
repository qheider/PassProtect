# PassProtect Web Application

A multi-page Flask web application for secure database management with AI-powered assistance.

## Features

- **User Authentication**: Secure JWT-based login system
- **Role-Based Access Control**: Different permissions for admin, user, and readonly roles
- **AI Chat Interface**: Natural language database queries using OpenAI
- **Dashboard**: Overview of system features and user information
- **Session Management**: 8-hour session timeout for security
- **Responsive Design**: Works on desktop, tablet, and mobile devices

## Pages

1. **Login Page** (`/login`) - Secure authentication
2. **Dashboard** (`/dashboard`) - Main landing page with system overview
3. **Chat Interface** (`/chat`) - AI-powered database assistant

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create or update `.env` file:

```env
# Database Configuration
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=quaziinfodb

# Security
JWT_SECRET=your_secret_key_here
FLASK_SECRET_KEY=your_flask_secret_key

# OpenAI
OPENAI_API_KEY=your_openai_api_key
```

### 3. Run the Web Application

```bash
python app.py
```

The application will be available at: `http://localhost:5000`

## Usage

1. **Login**: Navigate to `http://localhost:5000` and login with your credentials
2. **Dashboard**: View your account information and available operations
3. **Chat**: Click "Open Chat" to interact with the AI database assistant

## Chat Commands

The AI assistant can help you with:

- **Create records**: "Add a new password for Microsoft"
- **Read records**: "Show me all passwords", "What's the password for ZoneEdit?"
- **Update records**: "Update the username for Google"
- **View schema**: "Show me the table structure"
- **Custom queries**: Natural language database questions

## Security Features

- JWT token authentication
- Role-based access control
- Encrypted password storage
- User data isolation
- Session expiration (8 hours)
- CSRF protection via Flask

## API Endpoints

### Web Routes
- `GET /` - Redirect to dashboard or login
- `GET /login` - Login page
- `POST /login` - Authenticate user
- `GET /logout` - Clear session and logout
- `GET /dashboard` - Main dashboard (requires auth)
- `GET /chat` - Chat interface (requires auth)

### API Routes
- `POST /api/chat` - Process chat messages (requires auth)

## File Structure

```
PassProtect/
├── app.py                  # Flask application
├── passProtect.py         # CLI version
├── mcp_server.py          # MCP database server
├── auth.py                # Authentication logic
├── jwt_utils.py           # JWT token management
├── db_access.py           # Database operations
├── templates/             # HTML templates
│   ├── base.html
│   ├── login.html
│   ├── dashboard.html
│   └── chat.html
├── static/                # Static assets
│   ├── css/
│   │   └── style.css
│   └── js/
├── requirements.txt       # Python dependencies
└── README_WEBAPP.md      # This file
```

## Differences from CLI Version

| Feature | CLI (passProtect.py) | Web App (app.py) |
|---------|---------------------|------------------|
| Interface | Terminal | Browser |
| Authentication | Session file | Flask sessions |
| Conversation | Async loop | HTTP requests |
| Multi-user | Single user | Multiple concurrent users |
| Accessibility | Local only | Network accessible |

## Development

To run in development mode with auto-reload:

```bash
export FLASK_ENV=development  # Linux/Mac
set FLASK_ENV=development     # Windows CMD
$env:FLASK_ENV="development"  # Windows PowerShell

python app.py
```

## Production Deployment

For production, use a WSGI server like Gunicorn:

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

## Troubleshooting

**Issue**: "OPENAI_API_KEY not found"
- **Solution**: Add OPENAI_API_KEY to your `.env` file

**Issue**: Database connection failed
- **Solution**: Check DB credentials in `.env` file

**Issue**: Session expires immediately
- **Solution**: Set FLASK_SECRET_KEY in `.env` file

**Issue**: Chat not responding
- **Solution**: Check MCP server connection and OpenAI API status

## License

Same as PassProtect CLI application.
