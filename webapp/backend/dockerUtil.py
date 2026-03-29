"""
Entry point shim for the Docker utility daemon.

This file is referenced by pm2 (Makefile line 468) as "backendDockerUtil".
All logic lives in docker/daemon.py.
"""

if __name__ == "__main__":
    from docker.daemon import run
    run()
