---
name: security-review
description: Review code changes for security vulnerabilities specific to this project
---

Review all unstaged changes (`git diff`) for security issues. Check each area below and report findings as a numbered list with PASS/WARN/FAIL per item.

## Authentication & Authorization

1. **Endpoint protection**: Every endpoint in `endpoints/*.py` (except `/api/app/config`) must call `ForceAuthentication(token)` or `ForceAuthentication(token, "admin")` before any business logic. Check that no new endpoints skip authentication.
2. **Admin role enforcement**: All endpoints under `/api/admin/` must use `ForceAuthentication(token, "admin")`. Check that no admin endpoint uses plain `ForceAuthentication(token)` without the role parameter.
3. **User data isolation**: Endpoints returning user-specific data must filter by the authenticated user's ID. Check that users cannot access other users' reservations or data by manipulating IDs.
4. **Token handling**: Login tokens are generated via `CreateLoginToken()`. Check that tokens are not logged, exposed in responses beyond login, or stored insecurely.

## Input Validation

5. **Pydantic validation**: POST request bodies use Pydantic models with appropriate type constraints. Check for overly permissive types (e.g., `Dict[str, Any]` without further validation in the response handler).
6. **Query parameter validation**: GET endpoint parameters have type annotations and are validated before use. Check for missing bounds on numeric parameters (IDs, durations, page sizes).
7. **String sanitization**: User-supplied strings (descriptions, names, emails) are length-limited and stripped of dangerous characters before database storage or HTML rendering.

## Database Security

8. **ORM-only queries**: All database access uses SQLAlchemy ORM methods (`session.query()`, `session.add()`, `filter()`). Check for any raw SQL via `session.execute(text(...))` or string concatenation in queries.
9. **Session scope**: Database sessions are properly scoped with `with Session() as session:`. Check that sessions are not leaked or left open.

## Docker & Infrastructure Security

10. **Container isolation**: Container operations in `docker/containers.py` validate parameters before passing to `python_on_whales`. Check that user input does not flow unsanitized into container names, mount paths, or command strings.
11. **Port exposure**: Container port assignments come from the managed port range (default 2000-3000). Check that no code opens arbitrary ports or bypasses the port management system in `docker/ports.py`.
12. **Mount path validation**: Role-based mounts in `docker/mounts.py` use template variables (`{email}`, `{userid}`). Check that user input cannot inject path traversal sequences (`../`) into mount paths.

## Information Disclosure

13. **Error messages**: Error responses use generic messages. Check that stack traces, internal paths, database details, or configuration values are not leaked to the client.
14. **Sensitive data in responses**: Check that password hashes, salts, login tokens (beyond the owner's own token), and internal IDs are not included in API responses.

Present results as a checklist. For any WARN or FAIL items, show the specific file, line number, and a concrete description of the vulnerability with a suggested fix.

Do NOT report style issues, naming conventions, or non-security concerns. Stay focused on security only.
