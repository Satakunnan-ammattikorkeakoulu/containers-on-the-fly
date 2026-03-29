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

### Backend Settings Architecture
The backend uses a unified settings system that handles both file-based and database settings:

- **Settings Handler**: `webapp/backend/settings_handler.py` - Unified interface for all settings
- **Settings Schema**: `webapp/backend/settings_schema.py` - Defines all settings with types, defaults, and validation
- **Two Types of Settings**:
  1. **File-based settings**: Infrastructure config (ports, IPs, paths) stored in `settings.json`
  2. **Database settings**: Runtime config (emails, features) stored in `SystemSetting` table

### Adding New Settings
When adding a new setting, you must:
1. Add it to `webapp/backend/settings_schema.py` with proper type and default value
2. For file-based settings:
   - Add to `user_config/settings_example`
   - Add to `user_config/templates/backend_settings.json` if needed by backend
   - Add to boolean/numeric lists in `scripts/apply_settings.py` if applicable
3. Access settings using: `settings_handler.getSetting("category.settingName")`

Example:
```python
# In settings_schema.py
"docker.debugSkipGpuDedication": SettingSetting(
    SettingSource.FILE, SettingType.BOOLEAN, default=False,
    description="Skip GPU dedication for testing"
)

# In code
debug_mode = settings_handler.getSetting("docker.debugSkipGpuDedication")

### Multi-Server Architecture
- **Main Server**: Web interface, database, Docker registry
- **Container Servers**: Remote Docker hosts for container execution
- Firewall rules managed via `scripts/apply_firewall_rules.bash`
- Container port ranges configurable (default: 2000-3000)

## Commit Message Format

Use conventional commits: `type(scope): description`

**Types**: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`, `perf`, `ci`, `build`

**Rules**:
- Write subjects in imperative mood ("Add", "Fix", "Update")
- Keep messages short — focus on the main changes, not every detail
- No marketing text ("improved UX", "for better maintainability")
- No preamble ("This commit introduces...")
- If there are multiple major changes across areas, group with headers

**Example**:
```
Frontend
feat(teachers): Add new page for teachers to manage their games
chore(nav): Update the header to include a new link for the games

Backend
feat(teachers): Add a new route for teacher to fetch game statistics
fix: Fix group removal logic to not break on empty usernames
```

## Important Development Guidelines

### AI Workflow Rules

- **Plan before implementing**: When asked for a plan or design, present the plan and wait for approval before writing any code. Do not implement unless explicitly asked.
- **UI changes — change only what was requested**: When modifying frontend components, only change the elements explicitly requested. Do not move, resize, restyle, or reorganize other elements in the same component or page. If an adjacent change seems beneficial, mention it and wait for approval.
- **Respect existing structure**: When adding new items to arrays, config objects, endpoint lists (like `AppUrls.js`), database models, or Vuex store modules, study the existing entries first and replicate their exact pattern (spacing, naming, ordering conventions).

### Common Pitfalls

- **Session management**: Always use `with Session() as session:` context manager. Do NOT call `session.close()` inside a `with` block (it is redundant). Access ORM objects only within the session scope.
- **Authentication patterns**: The codebase uses two auth patterns: `ForceAuthentication(token)` raises HTTPException if not authenticated, and `ForceAuthentication(token, "admin")` additionally checks for admin role. For admin endpoints always pass `"admin"` as the second argument.
- **Response wrapper**: Always return via `Response(status, message, data)` from `helpers.server`. Never return raw dicts from endpoint response functions.
- **Frontend date handling**: Always use Day.js via `helpers/time.js` utilities (`DisplayTime` and `TimestampToLocalTimeZone`). Never use raw `Date()` or `moment`.
- **Pydantic models for POST bodies**: POST endpoints that accept JSON bodies must define a Pydantic model in `endpoints/models/`. GET endpoints use query parameters directly.
- **AppUrls.js**: All API URLs must be registered in `src/AppUrls.js`. Never hardcode API paths in components.

### Documentation Standards

**Python Backend:**
- All new functions should have docstrings describing purpose, parameters, and return values
- Endpoint response functions should document what the endpoint does and its expected inputs
- No inline type annotations are required, but Pydantic models must have field descriptions for complex types

**Vue Frontend:**
- Component files should have a comment block at the top of `<script>` explaining the component's purpose if it is not obvious from the filename
- Complex computed properties and methods should have brief JSDoc-style comments
- No documentation is required for simple template bindings or obvious Vuetify component usage

### Version Management
The project maintains a `.version` file in the root directory to track releases:
- Format: `version: X.Y.Z` and `updated: YYYY-MM-DD HH:MM:SS UTC`
- **When to update**: After making significant changes, ask if the version should be updated
- **Version increment rules**:
  - Patch version (Z): Increment by 0.0.1 for bug fixes and minor changes
  - Can exceed 9 (e.g., 1.0.26 is valid) but max is 99
  - When reaching 100, roll over to next minor version (1.0.100 → 1.1.0)
  - Minor version (Y): For new features or significant improvements
  - Major version (X): For breaking changes or major releases

### Post-Development Workflow
After making code changes, especially to frontend/backend configuration or business logic:
```bash
pm2 restart all    # Restart all services to apply changes
```

### Automated Code Review (Post-Implementation)

After completing a feature or task (not after every individual edit), automatically run both review skills **in the background** against unstaged changes:

1. Run `/code-review` and `/security-review` **in parallel as background agents**
2. Each agent should review the **unstaged git diff** (`git diff`) to see what changed
3. Wait for both to finish, then present a combined summary:
   - Code convention issues (if any)
   - Security issues (if any)
   - "No issues found" if clean

**When to trigger:** After finishing implementation work, before the user commits. Do NOT trigger on trivial changes (typo fixes, single-line config edits, documentation-only changes).

**Skills available:**
- `/code-review` — Checks naming conventions, auth patterns, Response() usage, session management, Vuetify patterns, and ESLint compliance
- `/security-review` — Checks authentication on endpoints, role authorization, input validation, ORM usage, and Docker security

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
- iptables (iptables-persistent) firewall configuration included
- pm2 process management with startup scripts
- Caddy reverse proxy with automatic HTTPS via Let's Encrypt

### Common Port Usage
- 80/443: HTTP/HTTPS web interface
- 5000: Docker registry
- 2000-3000: Default container port range (configurable)
- 22: SSH (firewall managed)