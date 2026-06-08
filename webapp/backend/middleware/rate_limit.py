"""FastAPI middleware that enforces per-IP and per-endpoint rate limits.

Applies different rate limits based on the request path and authentication
status. Daemon endpoints get a separate generous bucket, login and password
change endpoints have stricter per-IP/per-user limits, and all other
endpoints share a general per-IP limit.

Rate limit state is stored in-memory via helpers.rate_limiter.
"""

import asyncio
import logging

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from helpers.rate_limiter import is_rate_limited

log = logging.getLogger("global_logger")

# ---------------------------------------------------------------------------
# Rate limit configuration
# ---------------------------------------------------------------------------
GENERAL_UNAUTH_LIMIT = 60       # per IP per window (no auth token)
GENERAL_AUTH_LIMIT = 200         # per IP per window (with auth token)
LOGIN_LIMIT = 10                 # per IP per window
PASSWORD_CHANGE_LIMIT = 10       # per user per window
CREATE_PASSWORD_LIMIT = 10       # per user per window
DAEMON_LIMIT = 300               # per IP per window for /api/daemon/*
RATE_LIMIT_WINDOW = 60           # window duration in seconds


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Enforce request rate limits before requests reach route handlers."""

    async def dispatch(self, request: Request, call_next):
        """Check rate limits and either forward the request or return 429.

        Args:
            request: The incoming HTTP request.
            call_next: Callback to pass the request to the next middleware
                or route handler.

        Returns:
            The response from the downstream handler, or a 429 JSON
            response if a rate limit was exceeded.
        """
        # 1. Skip CORS preflight requests.
        if request.method == "OPTIONS":
            return await call_next(request)

        # 2. Determine client IP.
        client_ip = request.client.host if request.client else "unknown"

        # 3. Normalize request path for matching.
        path = request.url.path.rstrip("/").lower()
        method = request.method.upper()

        # 4. Extract bearer token (used later for auth detection).
        token = None
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]

        # 5. Endpoint-specific limits (checked first, most restrictive).

        # 5a. Daemon endpoints — separate generous bucket, replaces general limit.
        if path.startswith("/api/daemon"):
            limited, retry_after = is_rate_limited(
                f"daemon:{client_ip}", DAEMON_LIMIT, RATE_LIMIT_WINDOW,
            )
            if limited:
                log.warning("Rate limit exceeded for daemon endpoint: %s", client_ip)
                return _rate_limit_response(retry_after)
            # Daemon paths skip the general limit entirely.
            return await call_next(request)

        # 5b. Login endpoint.
        if path == "/api/user/login" and method == "POST":
            limited, retry_after = is_rate_limited(
                f"login:{client_ip}", LOGIN_LIMIT, RATE_LIMIT_WINDOW,
            )
            if limited:
                log.warning("Rate limit exceeded for login: %s", client_ip)
                return _rate_limit_response(retry_after)

        # 5c. Password change endpoint (per-user limit).
        if path == "/api/user/change_password" and method == "POST":
            if token:
                user_id = await _extract_user_id(token)
                if user_id is not None:
                    limited, retry_after = is_rate_limited(
                        f"password_change:user:{user_id}",
                        PASSWORD_CHANGE_LIMIT,
                        RATE_LIMIT_WINDOW,
                    )
                    if limited:
                        log.warning(
                            "Rate limit exceeded for password change: user %s",
                            user_id,
                        )
                        return _rate_limit_response(retry_after)

        # 5d. Create password endpoint (per-user limit).
        if path == "/api/user/create_password" and method == "POST":
            if token:
                user_id = await _extract_user_id(token)
                if user_id is not None:
                    limited, retry_after = is_rate_limited(
                        f"create_password:user:{user_id}",
                        CREATE_PASSWORD_LIMIT,
                        RATE_LIMIT_WINDOW,
                    )
                    if limited:
                        log.warning(
                            "Rate limit exceeded for create password: user %s",
                            user_id,
                        )
                        return _rate_limit_response(retry_after)

        # 6. General per-IP limit.
        is_authenticated = token is not None and len(token) > 0
        general_limit = GENERAL_AUTH_LIMIT if is_authenticated else GENERAL_UNAUTH_LIMIT
        limited, retry_after = is_rate_limited(
            f"general:{client_ip}", general_limit, RATE_LIMIT_WINDOW,
        )
        if limited:
            log.warning("Rate limit exceeded (general): %s", client_ip)
            return _rate_limit_response(retry_after)

        # 7. All checks passed — forward to the route handler.
        return await call_next(request)


async def _extract_user_id(token: str) -> int | None:
    """Validate a bearer token and return the associated user ID.

    Runs the synchronous check_token() in a thread executor to avoid
    blocking the async event loop.

    Args:
        token: The bearer token from the Authorization header.

    Returns:
        The user ID if the token is valid, or None if invalid/expired.
    """
    from helpers.auth import check_token

    loop = asyncio.get_running_loop()
    auth_result = await loop.run_in_executor(None, check_token, token)
    if auth_result["status"]:
        return auth_result["data"]["userId"]
    return None


def _rate_limit_response(retry_after: int) -> JSONResponse:
    """Build a 429 response matching the application's API response format.

    Args:
        retry_after: Number of seconds until the rate limit window resets.

    Returns:
        A JSONResponse with status 429, a descriptive message, and a
        Retry-After header.
    """
    return JSONResponse(
        status_code=429,
        content={
            "status": False,
            "message": f"Rate limit exceeded. Try again in {retry_after} seconds.",
        },
        headers={"Retry-After": str(retry_after)},
    )
