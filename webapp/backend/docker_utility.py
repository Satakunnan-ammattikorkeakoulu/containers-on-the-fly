"""
Entry point shim for the Docker utility daemon.

Started by pm2 as "backendDockerUtil" (see Makefile start-docker-utility target).
All logic lives in docker/daemon.py.
"""

if __name__ == "__main__":
    from docker.daemon import run
    run()
