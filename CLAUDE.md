# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is **Containers on the Fly** - a web-based Docker container reservation platform that allows users to reserve Docker containers with specific hardware resources and time slots. The system supports multiple container servers and includes comprehensive admin management tools.

## Architecture

The application follows a multi-component architecture:

- **Frontend**: Vue.js 3 + Vuetify 4 + Pinia (`webapp/frontend/`)
- **Backend**: Python 3 + FastAPI + SQLAlchemy ORM (`webapp/backend/`)
- **Database**: MariaDB with Alembic migrations
- **Container Server**: Docker container management daemon (`webapp/container_server/`)
- **Reverse Proxy**: Caddy with automatic HTTPS
- **Process Management**: pm2 for production deployment
- **Build System**: Make-based automation with comprehensive setup scripts

## Development Commands

### Core Development Workflow
```bash
# Start development servers
make start-dev-frontend          # Vue.js dev server with hot reload
make start-dev-backend           # FastAPI backend with auto-reload
make start-dev-container-server  # Container server daemon for container management

# Production deployment
make start-main-server           # Start/restart all main server services
make start-container-server      # Start/restart container server daemon

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
npm test               # Run unit + component tests (vitest)
npm run test:watch     # Tests in watch mode
npm run test:coverage  # Tests with coverage report
```

### Backend Commands
```bash
cd webapp/backend
python main.py         # Start FastAPI server
alembic upgrade head   # Apply database migrations

cd webapp/container_server
python main.py         # Start container server daemon
```

## Code Architecture Patterns

### Backend Structure (`webapp/backend/`)
- **Endpoints** (`endpoints/`): FastAPI route handlers
- **Responses** (`endpoints/responses/`): Business logic and response formatting
- **Helpers** (`helpers/`): Utility functions, settings, auth, and database table operations
- **Models** (`database.py`): SQLAlchemy ORM models
- **Routes** (`routes/`): API route registration

### Container Server Structure (`webapp/container_server/`)
- **Docker** (`docker/`): Container orchestration utilities (containers, ports, mounts, monitoring, image building, SSH host keys)
- **Helpers** (`helpers/`): Settings handler, logger, and utilities
- **API Client** (`api_client.py`): Communication with the main backend
- **Daemon** (`daemon.py`): Main daemon process for container lifecycle management

### Frontend Structure (`webapp/frontend/`)
- **Components** (`src/components/`): Reusable Vue components organized by feature
  - `admin/`: Admin interface components
  - `user/`: User interface components  
  - `global/`: Shared components
- **Pages** (`src/pages/`): Route-specific page components
- **Views** (`src/views/`): View wrappers for pages
- **Layouts** (`src/layouts/`): Page layout templates
- **Store** (`src/store/`): Pinia state management
- **Router** (`src/router/`): Vue Router configuration

### Authentication & Security
- Uses FastAPI's OAuth2PasswordBearer for authentication
- `force_authentication()` function for endpoint protection
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

- **Settings Handler**: `webapp/backend/helpers/settings_handler.py` - Unified interface for all settings
- **Settings Schema**: `webapp/backend/helpers/settings_schema.py` - Defines all settings with types, defaults, and validation
- **Two Types of Settings**:
  1. **File-based settings**: Infrastructure config (ports, IPs, paths) stored in `settings.json`
  2. **Database settings**: Runtime config (emails, features) stored in `SystemSetting` table

### Adding New Settings
When adding a new setting, you must:
1. Add it to `webapp/backend/helpers/settings_schema.py` with proper type and default value
2. For file-based settings:
   - Add to `user_config/settings_example`
   - Add to `user_config/templates/backend_settings.json` if needed by backend
   - Add to boolean/numeric lists in `scripts/apply_settings.py` if applicable
3. Access settings using: `settings_handler.get_setting("category.settingName")`

Example:
```python
# In settings_schema.py
"docker.debugSkipGpuDedication": SettingSetting(
    SettingSource.FILE, SettingType.BOOLEAN, default=False,
    description="Skip GPU dedication for testing"
)

# In code
debug_mode = settings_handler.get_setting("docker.debugSkipGpuDedication")

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

### Python Naming Convention (PEP 8)
- **Files**: `snake_case.py` (e.g., `hardware_spec.py`, not `HardwareSpec.py`)
- **Functions, methods, variables, parameters**: `snake_case` (e.g., `get_roles()`, `computer_id`)
- **Classes**: `PascalCase` (e.g., `Reservation`, `UnifiedSettings`)
- **Exception — database layer stays camelCase**: SQLAlchemy column attributes (e.g., `userId`, `computerId`), relationship names (e.g., `reservedContainer`), `__tablename__` values, API response JSON field names, Pydantic request model fields, and settings keys (e.g., `docker.serverName`) all remain camelCase because they are part of the API contract with the frontend.

### AI Workflow Rules

- **Never stage or commit**: Do NOT run `git add`, `git commit`, or any git command that stages or commits changes. The user will always do this manually.
- **Plan before implementing**: When asked for a plan or design, present the plan and wait for approval before writing any code. Do not implement unless explicitly asked.
- **UI changes — change only what was requested**: When modifying frontend components, only change the elements explicitly requested. Do not move, resize, restyle, or reorganize other elements in the same component or page. If an adjacent change seems beneficial, mention it and wait for approval.
- **Respect existing structure**: When adding new items to arrays, config objects, endpoint lists (like `AppUrls.js`), database models, or Pinia store, study the existing entries first and replicate their exact pattern (spacing, naming, ordering conventions).

### Function Return Values
- **2 values**: Tuples are fine (e.g., `return success, message`)
- **3+ values**: Always return a dictionary instead of a tuple. Dictionary keys are self-documenting and easier to extend without breaking callers. Example: `return {"started": True, "containerName": name, "error": ""}` instead of `return True, name, ""`

### Common Pitfalls

- **Session management**: Always use `with Session() as session:` context manager. Do NOT call `session.close()` inside a `with` block (it is redundant). Access ORM objects only within the session scope.
- **Authentication patterns**: The codebase uses two auth patterns: `force_authentication(token)` raises HTTPException if not authenticated, and `force_authentication(token, "admin")` additionally checks for admin role. For admin endpoints always pass `"admin"` as the second argument.
- **Response wrapper**: Always return via `Response(status, message, data)` from `helpers.server`. Never return raw dicts from endpoint response functions.
- **Frontend date handling**: Always use Day.js via `helpers/time.js` utilities (`DisplayTime` and `TimestampToLocalTimeZone`). Never use raw `Date()` or `moment`.
- **Pydantic models for POST bodies**: POST endpoints that accept JSON bodies must define a Pydantic model in `endpoints/models/`. GET endpoints use query parameters directly.
- **AppUrls.js**: All API URLs must be registered in `src/AppUrls.js`. Never hardcode API paths in components.

### Documentation Standards

**Python Backend:**
- All functions should have docstrings describing purpose, parameters, and return values
- Use **Google-style docstrings** for all Python code:
  ```python
  def reserve_container(user_id, container_id, hours):
      """Reserve a container for the specified user.

      Args:
          user_id: The ID of the user making the reservation.
          container_id: The target container's database ID.
          hours: Duration of the reservation in hours.

      Returns:
          Response with the created reservation details.

      Raises:
          HTTPException: If the container is already reserved.
      """
  ```
- Endpoint response functions should document what the endpoint does and its expected inputs
- No inline type annotations are required, but Pydantic models must have field descriptions for complex types
- Module-level docstrings should describe the file's purpose at the top of each `.py` file
- Alembic migration files should have a module-level docstring describing what the migration does

**Vue Frontend:**
- Component files should have a comment block at the top of `<script>` explaining the component's purpose if it is not obvious from the filename
- Complex computed properties and methods should have brief JSDoc-style comments
- No documentation is required for simple template bindings or obvious Vuetify component usage

**JavaScript Utilities:**
- Use JSDoc-style comments for exported functions:
  ```js
  /**
   * Convert a UTC timestamp to the user's local timezone.
   * @param {string} timestamp - ISO 8601 timestamp
   * @returns {string} Formatted local time string
   */
  ```

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

### Test Coverage for New Features
After implementing a new feature or significant change, evaluate whether new tests would be beneficial and suggest this to the user. Consider adding tests when:
- A new API endpoint was added or an existing endpoint's behavior changed
- New business logic was introduced (validation, data transformation, access control)
- A new database column or model was added that affects queries or responses
- Frontend store state or actions were modified

Do NOT suggest tests for trivial changes (config edits, copy/label updates, documentation).

### Automated Code Review (Post-Implementation)

After completing a feature or task (not after every individual edit), automatically run review skills and tests **in the background** against unstaged changes:

1. Run `/code-review`, `/security-review`, and `/test` **in parallel as background agents**
2. Code review and security review should review the **unstaged git diff** (`git diff`) to see what changed
3. `/test` runs the offline test suites (backend + frontend) to catch regressions
4. Wait for all to finish, then present a combined summary:
   - Code convention issues (if any)
   - Security issues (if any)
   - Test results (pass/fail count)
   - "No issues found" if clean

**When to trigger:** After finishing implementation work, before the user commits. Do NOT trigger on trivial changes (typo fixes, single-line config edits, documentation-only changes).

**Skills available:**
- `/code-review` — Checks naming conventions, auth patterns, Response() usage, session management, Vuetify patterns, and ESLint compliance
- `/security-review` — Checks authentication on endpoints, role authorization, input validation, ORM usage, and Docker security
- `/test` — Runs backend (pytest) and frontend (vitest) test suites, reports pass/fail summary

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
- **Backend**: FastAPI, SQLAlchemy, PyMySQL, ldap3, python-ldap, alembic, pydantic
- **Container Server**: python-on-whales, requests, psutil
- **Frontend**: Vue.js 3, Vuetify 4, Vue Router, Pinia, axios, dayjs
- **Testing**: pytest, httpx, vitest, @vue/test-utils, Playwright, Bruno CLI
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

### Running Tests
```bash
# All automated tests (backend + container server + frontend)
make test-all

# Backend only
make test-backend                # All backend tests (unit + integration)
make test-backend-unit           # Unit tests only (no DB)
make test-backend-integration    # Integration tests (SQLite in-memory)
make test-backend-coverage       # With HTML coverage report

# Container server only
make test-container-server       # All container server tests
make test-container-server-unit  # Unit tests only
make test-container-server-coverage  # With HTML coverage report

# Frontend only
make test-frontend               # Unit + component tests (vitest)
make test-frontend-watch         # Watch mode

# E2E (requires running app stack)
make test-e2e                    # Playwright tests
make test-e2e-ui                 # Playwright with UI

# API (requires running app)
make test-api                    # Bruno CLI tests
```

### Test Structure
```
tests/
├── scripts/
│   ├── setup_test_users.py      # Create temp admin + user accounts
│   ├── teardown_test_users.py   # Delete temp accounts + cleanup files
│   └── generate_bruno_env.py    # Generate Bruno test environment from credentials
├── backend/
│   ├── conftest.py              # Shared fixtures, SQLite in-memory DB setup
│   ├── test_settings.json       # Test-specific settings
│   ├── unit/                    # Pure function tests (no DB)
│   │   ├── helpers/             # auth, utils, server, email, pagination,
│   │   │                        # container_defaults, email_notifications
│   │   ├── test_settings_schema.py
│   │   └── test_validate_script_path.py
│   └── integration/             # API endpoint tests with test DB
│       ├── test_user_endpoints.py
│       ├── test_reservation_endpoints.py
│       ├── test_admin_endpoints.py
│       ├── test_daemon_endpoints.py
│       └── test_app_endpoints.py
├── container_server/
│   ├── conftest.py              # Path setup, settings patch, docker/psutil mocks
│   ├── test_settings.json       # Test-specific settings
│   └── unit/
│       ├── helpers/             # utils, settings_handler
│       ├── docker/              # ports, mounts, image_builder, ssh_host_keys, monitoring
│       └── test_api_client.py   # DaemonApiClient tests
├── frontend/
│   ├── setup.js                 # Vitest setup (mocks axios)
│   ├── unit/                    # Store, helpers, URL builder tests
│   └── component/               # Vue component tests (shallowMount)
├── e2e/
│   ├── playwright.config.js
│   ├── auth.setup.js            # Login once, save session for parallel tests
│   ├── fixtures/auth.js         # Login helpers (reads .test_credentials.json)
│   └── tests/                   # Auth, reservation, admin, navigation specs
├── api/                         # Bruno API tests (56 .bru files)
└── docker-compose.test.yml      # Full stack for E2E testing
```

### Test Architecture Notes
- **Backend unit tests** use no database — they test pure functions in `helpers/` and `settings_schema.py`
- **Backend integration tests** use SQLite in-memory via `StaticPool` — the `conftest.py` patches `settings_handler` and `database.engine` at import time to avoid MySQL dependencies
- **Container server tests** use a separate `conftest.py` that adds `webapp/container_server` to `sys.path`, patches `settings_handler` with test settings, and mocks `python_on_whales` and `psutil`. No database is needed — all Docker/system calls are mocked
- **Frontend tests** run via vitest with jsdom. Test files live outside `webapp/frontend/` so `test.alias` in `vite.config.js` maps package imports to the frontend's `node_modules`
- **Component tests** use `shallowMount` with Vuetify stubs (Vuetify 4 auto-import sub-paths are not compatible with alias-based resolution in the test environment)
- **E2E tests** require the full app stack running (use `docker-compose.test.yml` or manual startup, then `make seed-data` to seed test data)

### E2E & API Test User Management
E2E (Playwright) and API (Bruno) tests use **temporary test accounts** created automatically before tests and deleted afterward — they never use real user accounts. The flow is:

1. `tests/scripts/setup_test_users.py` creates a temp admin + normal user with random passwords via direct DB access
2. Credentials are written to `tests/.test_credentials.json`
3. For Bruno, `tests/scripts/generate_bruno_env.py` generates `tests/api/environments/test.bru` from the credentials
4. Tests run (Playwright reads credentials from JSON; Bruno uses the `test` environment)
5. `tests/scripts/teardown_test_users.py` deletes the users and removes credential files

The `make test-e2e` and `make test-api` targets handle this full lifecycle automatically — teardown always runs even if tests fail. For manual use: `make test-e2e-setup` and `make test-e2e-teardown`.

Playwright uses an **auth setup project** to avoid login race conditions: `auth.setup.js` logs in once per role, saves browser state, and all parallel test workers reuse the saved session without hitting the login endpoint again.

### Installing Test Dependencies
```bash
# Backend
pip install -r tests/backend/requirements-test.txt

# Container server
pip install -r tests/container_server/requirements-test.txt

# Frontend (already in devDependencies after npm install)
cd webapp/frontend && npm install

# E2E
cd tests/e2e && npm install && npx playwright install

# Bruno CLI
cd tests/api && npm install
```

### Manual Testing
1. Test main server setup: `make start-main-server`
2. Test container server: `make start-container-server`
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