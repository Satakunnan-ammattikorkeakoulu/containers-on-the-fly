"""In-memory fixed-window rate limiter.

Provides a simple rate limiting engine that tracks request counts per key
within fixed time windows. Uses time.monotonic() for clock-adjustment immunity.

Cleanup of expired entries is handled lazily — stale buckets are purged
at most once every 5 minutes during normal request processing.

Usage:
    from helpers.rate_limiter import is_rate_limited

    limited, retry_after = is_rate_limited("login:192.168.1.1", max_requests=10)
    if limited:
        # reject with 429, tell client to retry after `retry_after` seconds
"""

import math
import time
from dataclasses import dataclass, field


@dataclass
class _WindowCounter:
    """Tracks request count within a fixed time window."""

    count: int = 0
    window_start: float = 0.0


# Key → counter mapping. Keys are constructed by callers,
# e.g. "login:192.168.1.1" or "general:10.0.0.5".
# In async single-worker FastAPI, dict access is safe without locks
# because the event loop is single-threaded — no preemptive context
# switches mid-operation.
_buckets: dict[str, _WindowCounter] = {}

# Monotonic timestamp of the last cleanup run.
_last_cleanup: float = 0.0

# How often (seconds) to scan for stale entries.
_CLEANUP_INTERVAL = 300  # 5 minutes

# Entries older than this (seconds) are removed during cleanup.
_STALE_THRESHOLD = 120  # 2× the default 60s window


def is_rate_limited(key: str, max_requests: int,
                    window_seconds: int = 60) -> tuple[bool, int]:
    """Check whether a key has exceeded its rate limit, and increment its counter.

    Args:
        key: Unique identifier for the rate limit bucket
            (e.g. "login:192.168.1.1").
        max_requests: Maximum allowed requests within the window.
        window_seconds: Duration of the fixed time window in seconds.

    Returns:
        A tuple of (limited, retry_after) where limited is True if the
        request should be rejected, and retry_after is the number of
        seconds until the current window resets (only meaningful when
        limited is True).
    """
    now = time.monotonic()
    _maybe_cleanup(now)

    bucket = _buckets.get(key)

    if bucket is None or (now - bucket.window_start) >= window_seconds:
        # First request or window expired — start a new window.
        _buckets[key] = _WindowCounter(count=1, window_start=now)
        return False, 0

    bucket.count += 1

    if bucket.count > max_requests:
        retry_after = math.ceil(
            bucket.window_start + window_seconds - now
        )
        return True, max(retry_after, 1)

    return False, 0


def _maybe_cleanup(now: float) -> None:
    """Remove stale bucket entries if enough time has passed since the last cleanup.

    Args:
        now: Current monotonic timestamp.
    """
    global _last_cleanup

    if _last_cleanup == 0.0:
        _last_cleanup = now
        return

    if (now - _last_cleanup) < _CLEANUP_INTERVAL:
        return

    _last_cleanup = now
    stale_keys = [
        key for key, bucket in _buckets.items()
        if (now - bucket.window_start) > _STALE_THRESHOLD
    ]
    for key in stale_keys:
        del _buckets[key]


def reset() -> None:
    """Clear all rate limit state. Intended for testing."""
    global _last_cleanup
    _buckets.clear()
    _last_cleanup = 0.0
