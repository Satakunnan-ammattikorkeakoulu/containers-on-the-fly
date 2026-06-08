"""Port allocation utilities for Docker container reservations.

Manages finding available ports within the configured range for binding
container services to the host machine. Uses socket probing to check
actual port availability.
"""

import secrets
import socket
from helpers.settings_handler import settings_handler
from helpers.logger import log


def is_port_in_use(port: int) -> bool:
    """Check whether a port is currently in use on localhost.

    Args:
        port: TCP port number to check.

    Returns:
        bool: True if the port is in use, False otherwise.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0


def get_available_port(
    exclude: set[int] | None = None,
    soft_exclude: set[int] | None = None,
) -> dict:
    """Find an available port within the configured port range.

    Two-pass allocation: the first pass avoids both ``exclude`` and
    ``soft_exclude``. If that pass finds no usable port, a second pass
    drops ``soft_exclude`` and may return a port from it — this is the
    "steal" fallback used when paused low-priority reservations are
    holding ports that the computer can no longer afford to set aside.

    Args:
        exclude: Hard exclude. Ports already claimed by the current
            allocation batch (or otherwise unavailable). Never returned.
        soft_exclude: Soft exclude. Ports held for paused low-priority
            reservations. Avoided when possible; only returned (with
            ``stolen=True``) if the configured range is otherwise
            exhausted.

    Returns:
        dict: ``{"port": int, "stolen": bool}``. ``stolen`` is True iff
        the returned port was in the original ``soft_exclude`` set.

    Raises:
        RuntimeError: If no ports remain in the configured range after
            applying ``exclude`` (the second pass also fails).
    """
    exclude = exclude or set()
    soft_exclude = soft_exclude or set()
    min_port = settings_handler.get_setting("docker.port_range_start")
    max_port = settings_handler.get_setting("docker.port_range_end")

    # Validate port range boundaries
    if not isinstance(min_port, int) or not isinstance(max_port, int):
        raise RuntimeError(f"Port range settings must be integers, got {type(min_port)} and {type(max_port)}")
    if min_port < 1024:
        raise RuntimeError(f"Port range start ({min_port}) must be >= 1024 to avoid privileged ports")
    if max_port > 65535:
        raise RuntimeError(f"Port range end ({max_port}) must be <= 65535")
    if min_port >= max_port:
        raise RuntimeError(f"Port range start ({min_port}) must be less than end ({max_port})")

    def _try_pass(excluded: set[int]) -> int | None:
        candidates = [p for p in range(min_port, max_port) if p not in excluded]
        if not candidates:
            return None
        for _ in range(50):
            rand_port = secrets.choice(candidates)
            if not is_port_in_use(rand_port):
                return rand_port
        return None

    # First pass: respect both excludes
    port = _try_pass(exclude | soft_exclude)
    if port is not None:
        return {"port": port, "stolen": False}

    # Second pass: ignore the soft exclude (steal a held port if needed)
    if soft_exclude:
        port = _try_pass(exclude)
        if port is not None:
            return {"port": port, "stolen": port in soft_exclude}

    # Last resort: pick any non-hard-excluded port even if probing said it
    # was busy — preserves the previous behavior of always returning a port
    # rather than raising in a transient OS-busy scenario.
    fallback_candidates = [p for p in range(min_port, max_port) if p not in exclude]
    if not fallback_candidates:
        raise RuntimeError(
            f"No ports left in range {min_port}-{max_port} after "
            f"excluding {len(exclude)} already-assigned ports."
        )
    log.warning("Did not find an available port after 50 attempts in either pass. Randomly assigning one.")
    chosen = secrets.choice(fallback_candidates)
    return {"port": chosen, "stolen": chosen in soft_exclude}
