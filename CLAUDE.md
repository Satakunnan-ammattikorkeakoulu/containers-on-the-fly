# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is **Containers on the Fly** - a web-based Docker container reservation platform that allows users to reserve Docker containers with specific hardware resources and time slots. The system supports multiple container servers and includes comprehensive admin management tools.

## Architecture

The application follows a multi-component architecture:

- **Frontend**: Vue.js 2 + Vuetify UI framework (`webapp/frontend/`)
- **Backend**: Python 3 + FastAPI + SQLAlchemy ORM (`webapp/backend/`)
- **Database**: MariaDB with Alembic migrations
- **Container Management**: Docker + custom Python utility (`dockerUtil.py`)
- **Reverse Proxy**: Caddy with automatic HTTPS
- **Process Management**: pm2 for production deployment
- **Build System**: Make-based automation with comprehensive setup scripts

## Development Commands

### Core Development Workflow
```bash
# Start development servers
make start-dev-frontend          # Vue.js dev server with hot reload
make start-dev-backend           # FastAPI backend with auto-reload
make start-dev-docker-utility    # Docker utility for container management

# Production deployment
make start-main-server           # Start/restart all main server services
make start-docker-utility        # Start/restart Docker utility

# Configuration management
make apply-settings              # Apply user_config/settings to templates
make logs                        # View pm2 logs
make status                      # Check pm2 service status
make stop-servers               # Stop all pm2 services
```

### Database Operations
```bash
# Database management
make init-database                    # Initialize/update database schema
make migrate-database                 # Apply pending migrations
make create-migration MESSAGE="..."   # Create new migration
```

### Frontend Commands
```bash
cd webapp/frontend
npm run serve          # Development server
npm run build          # Production build
npm run lint           # ESLint
npm run production     # Production mode serve
```

### Backend Commands
```bash
cd webapp/backend
python main.py         # Start FastAPI server
python dockerUtil.py   # Start Docker container utility
alembic upgrade head   # Apply database migrations
```

## Code Architecture Patterns

### Backend Structure
- **Endpoints** (`endpoints/`): FastAPI route handlers
- **Responses** (`endpoints/responses/`): Business logic and response formatting
- **Helpers** (`helpers/`): Utility functions and database table operations
- **Models** (`database.py`): SQLAlchemy ORM models
- **Docker Management** (`docker/`): Container orchestration utilities

### Frontend Structure
- **Components** (`src/components/`): Reusable Vue components organized by feature
  - `admin/`: Admin interface components
  - `user/`: User interface components  
  - `global/`: Shared components
- **Pages** (`src/pages/`): Route-specific page components
- **Layouts** (`src/layouts/`): Page layout templates
- **Store** (`src/store/`): Vuex state management
- **Router** (`src/router/`): Vue Router configuration

### Authentication & Security
- Uses FastAPI's OAuth2PasswordBearer for authentication
- `ForceAuthentication()` decorator for endpoint protection
- Role-based access control with admin/user separation
- Session management with token validation

### Database Patterns
- SQLAlchemy ORM with MariaDB backend
- Alembic for schema migrations
- Connection pooling configured for scalability
- UTF8MB4 character set with proper collation
- InnoDB engine for transaction support

## Configuration Management

### Settings System
- Main configuration: `user_config/settings` (copied from `user_config/settings_example`)
- Template processing: `scripts/apply_settings.py` processes templates in `user_config/templates/`
- Backend settings: Generated as `webapp/backend/settings.json`
- Frontend settings: Generated as `webapp/frontend/public/settings.js`

### Multi-Server Architecture
- **Main Server**: Web interface, database, Docker registry
- **Container Servers**: Remote Docker hosts for container execution
- Firewall rules managed via `scripts/apply_firewall_rules.bash`
- Container port ranges configurable (default: 2000-3000)

## Important Development Guidelines

### Database Migrations
```bash
# Create migration after model changes
make create-migration MESSAGE="Add new table"

# Apply migrations (may require stopping container servers)
make migrate-database
```

### Security Considerations
- All admin endpoints must use proper role checking
- Input validation and sanitization required
- Use SQLAlchemy properly to prevent SQL injection
- Session management with secure token handling

### Dependencies
- **Backend**: FastAPI, SQLAlchemy, PyMySQL, ldap3, python-on-whales, alembic
- **Frontend**: Vue.js 2, Vuetify, Vue Router, Vuex, axios, dayjs
- **Process Management**: pm2, Caddy reverse proxy
- **Database**: MariaDB with connection pooling

### Container Development
- Docker images stored in local registry (port 5000)
- Example Dockerfile: `DockerfileContainerExample`
- Build and push pattern:
  ```bash
  docker build -t REGISTRY_IP:5000/IMAGE_NAME:latest -f DockerfileContainerExample .
  docker push REGISTRY_IP:5000/IMAGE_NAME:latest
  ```

## Testing & Quality

This project does not include automated tests. Manual testing workflows:
1. Test main server setup: `make start-main-server`
2. Test Docker utility: `make start-docker-utility`
3. Test database operations: `make init-database`
4. Frontend linting: `cd webapp/frontend && npm run lint`
5. Manual testing via web interface and container reservations

## Deployment & Infrastructure

### Ubuntu 24.04 Deployment
- Automated setup scripts for main server and container servers
- Make-based deployment with interactive configuration
- UFW firewall configuration included
- pm2 process management with startup scripts
- Caddy reverse proxy with automatic HTTPS via Let's Encrypt

### Common Port Usage
- 80/443: HTTP/HTTPS web interface
- 5000: Docker registry
- 2000-3000: Default container port range (configurable)
- 22: SSH (firewall managed)