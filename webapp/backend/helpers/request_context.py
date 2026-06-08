"""Request context utilities using contextvars.

Stores per-request data (e.g. client IP) that can be read anywhere
in the call stack without passing the Request object around.
"""

from contextvars import ContextVar

_client_ip: ContextVar[str | None] = ContextVar('client_ip', default=None)


def set_client_ip(ip: str | None):
    """Set the client IP for the current request context."""
    _client_ip.set(ip)


def get_client_ip() -> str | None:
    """Get the client IP for the current request context."""
    return _client_ip.get()
