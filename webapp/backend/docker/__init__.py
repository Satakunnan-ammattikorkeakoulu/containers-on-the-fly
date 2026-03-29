"""
Docker container management module.

External code (e.g. API endpoints) should import from this package directly,
not from sub-modules. This facade provides a stable public API.
"""

# Container lifecycle operations
from docker.containers import start_container, stop_container, restart_container

# Connection details / email text generation
from docker.notifications import generate_connection_text

# Backward-compatible alias used by endpoints
get_email_container_started = generate_connection_text
