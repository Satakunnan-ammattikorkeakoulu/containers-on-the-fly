"""Port allocation utilities for Docker container reservations.

Manages finding available ports within the configured range for binding
container services to the host machine. Uses socket probing to check
actual port availability.
"""

import random
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


def get_available_port():
    """Find an available port within the configured port range.

    Builds a list of all ports in the configured range and randomly
    selects one that is not bound on the host.

    Returns:
        int: An available port number.
    """
    min_port = settings_handler.get_setting("docker.port_range_start")
    max_port = settings_handler.get_setting("docker.port_range_end")
    available_ports = list(range(min_port, max_port))

    # Try to bind to a random available port 50 times
    for _ in range(50):
        rand_port = random.choice(available_ports)
        if not is_port_in_use(rand_port):
            return rand_port

    log.warning("Did not find an available port after 50 attempts. Randomly assigning one.")
    return random.choice(available_ports)
