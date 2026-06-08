# Contributing to Containers on the Fly

## Commit Message Format

Format all commit messages using conventional commits: `type(scope): description`

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

## Documentation Standards

### Python Backend

Uses Google-style docstrings:

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

- All functions have docstrings describing purpose, parameters, and return values
- Module-level docstrings describe each file's purpose
- Pydantic models have field descriptions for complex types

### Vue Frontend

- Component files have a comment block at the top of `<script>` explaining the component's purpose
- Complex computed properties and methods have brief JSDoc-style comments

### JavaScript Utilities

Use JSDoc-style comments:

```js
/**
 * Convert a UTC timestamp to the user's local timezone.
 * @param {string} timestamp - ISO 8601 timestamp
 * @returns {string} Formatted local time string
 */
```
