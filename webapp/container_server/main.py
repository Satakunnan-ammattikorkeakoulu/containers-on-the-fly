"""Entry point for the container server daemon.

Starts the daemon that manages Docker container lifecycle by polling
the backend REST API for reservation state changes.
"""

from daemon import run_daemon

if __name__ == "__main__":
    run_daemon()
