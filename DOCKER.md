# PassProtect Docker Setup

## Quick Start

Run the entire application with a single command:

```bash
docker-compose up
```

The application will be available at:
- **Local**: http://localhost:5000
- **Network**: http://0.0.0.0:5000

## Prerequisites

- Docker Desktop installed
- Docker Compose installed
- `.env` file with required configuration

## Environment Variables

Make sure your `.env` file contains:

```env
# Database Configuration
DB_HOST=10.0.0.47
DB_USER=quazisr
DB_PASSWORD=your_password
DB_NAME=quaziinfodb

# OpenAI Configuration
OPENAI_API_KEY=your_openai_key

# JWT Configuration
JWT_SECRET=your_jwt_secret

# Flask Configuration (optional)
FLASK_SECRET_KEY=your_flask_secret
```

## Docker Commands

### Build and start the container
```bash
docker-compose up --build
```

### Run in detached mode (background)
```bash
docker-compose up -d
```

### Stop the container
```bash
docker-compose down
```

### View logs
```bash
docker-compose logs -f
```

### Rebuild the image
```bash
docker-compose build --no-cache
```

### Remove all containers and volumes
```bash
docker-compose down -v
```

## Container Details

- **Image**: Python 3.11-slim
- **Port**: 5000 (mapped to host:5000)
- **Volumes**: 
  - Code mounted at `/app` (for development)
  - Session data persisted in `passprotect-sessions` volume
- **Network**: Custom bridge network `passprotect-network`

## Features

- ✅ Automatic container restart
- ✅ Health checks
- ✅ Session persistence
- ✅ Hot reload in development mode
- ✅ Environment variable configuration

## Production Deployment

For production, modify `docker-compose.yml`:

1. Remove the code volume mount:
   ```yaml
   volumes:
     # - .:/app  # Comment this out
     - passprotect-sessions:/root/.passprotect
   ```

2. Set production environment:
   ```yaml
   environment:
     - FLASK_ENV=production
   ```

3. Use a production WSGI server (add to Dockerfile):
   ```dockerfile
   CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
   ```

## Troubleshooting

### Port already in use
```bash
# Change port in docker-compose.yml
ports:
  - "8080:5000"  # Use port 8080 instead
```

### Database connection issues
- Ensure the database host (10.0.0.47) is accessible from Docker
- Check firewall rules
- Verify credentials in .env file

### Permission issues
```bash
# Fix permissions
chmod 600 .env
```

## Architecture

```
┌─────────────────────────────────┐
│   Docker Container              │
│                                 │
│   ┌─────────────────────────┐  │
│   │   Flask App (Port 5000) │  │
│   │   - Authentication      │  │
│   │   - MCP Server          │  │
│   │   - OpenAI Integration  │  │
│   └──────────┬──────────────┘  │
│              │                  │
└──────────────┼──────────────────┘
               │
               ▼
    MySQL Database (10.0.0.47)
```
