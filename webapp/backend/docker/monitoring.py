"""Server monitoring and log collection for container servers.

Periodically collects system metrics (CPU, memory, disk, Docker container
counts, load averages, uptime, software version) and pm2 service logs,
then stores them in the database for display in the admin dashboard.
"""

import psutil
import subprocess
import time
from datetime import datetime, timezone
from database import ServerStatus, ServerLogs, Computer, Session
from settings_handler import settings_handler
from sqlalchemy import select
from logger import log


def read_version_file():
    """Read version information from the project's .version file.

    Parses the key-value format file located three directories above this
    module (project root).

    Returns:
        tuple: A 2-element tuple of (version, updated) where version is a
            string like "1.2.3" and updated is a timestamp string like
            "2025-07-21 15:12:10 UTC". Both are None if the file is
            missing or cannot be parsed.
    """
    try:
        import os
        # Look for .version file in project root (3 levels up from this script)
        version_file_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', '.version')

        if os.path.exists(version_file_path):
            with open(version_file_path, 'r') as f:
                content = f.read().strip()

            # Parse the version file content
            version_info = {}
            for line in content.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    version_info[key.strip()] = value.strip()

            return version_info.get('version'), version_info.get('updated')
        else:
            return None, None
    except Exception as e:
        log.warning(f"Error reading version file: {e}")
        return None, None


def update_server_monitoring():
    """Collect system metrics and update the ServerStatus record in the database.

    Gathers CPU usage, memory usage, disk usage, Docker container counts,
    system load averages, uptime, and software version, then writes them to
    the ServerStatus table for the current computer. Also triggers log
    collection via update_server_logs().
    """
    try:
        with Session() as session:
            computer = session.execute(
                select(Computer).where(
                    Computer.name == settings_handler.get_setting("docker.serverName")
                )
            ).scalar_one_or_none()

            if not computer:
                log.warning(f"Computer '{settings_handler.get_setting('docker.serverName')}' not found in database")
                return

            # Get or create status record
            status = session.execute(
                select(ServerStatus).where(
                    ServerStatus.computerId == computer.computerId
                )
            ).scalar_one_or_none()

            if not status:
                status = ServerStatus(computerId=computer.computerId)
                session.add(status)

            # Collect system metrics
            status.isOnline = True
            status.cpuUsagePercent = round(psutil.cpu_percent(interval=1), 1)
            status.cpuCores = psutil.cpu_count()

            # Memory metrics
            memory = psutil.virtual_memory()
            status.memoryTotalBytes = memory.total
            status.memoryUsedBytes = memory.used
            status.memoryUsagePercent = round(memory.percent, 1)

            # Root disk usage (/)
            try:
                disk = psutil.disk_usage('/')
                status.diskTotalBytes = disk.total
                status.diskUsedBytes = disk.used
                status.diskFreeBytes = disk.free
                status.diskUsagePercent = round((disk.used / disk.total) * 100, 1)
            except:
                pass  # Skip if can't access root disk

            # Docker status
            try:
                from python_on_whales import docker
                running_containers = docker.container.list()
                all_containers = docker.container.list(all=True)
                status.dockerContainersRunning = len(running_containers)
                status.dockerContainersTotal = len(all_containers)
            except:
                status.dockerContainersRunning = None
                status.dockerContainersTotal = None

            # System load
            try:
                load_avg = psutil.getloadavg()
                status.loadAvg1Min = round(load_avg[0], 2)
                status.loadAvg5Min = round(load_avg[1], 2)
                status.loadAvg15Min = round(load_avg[2], 2)
            except:
                pass  # getloadavg not available on all systems

            # System uptime
            try:
                status.systemUptimeSeconds = int(time.time() - psutil.boot_time())
            except:
                pass

            # Update software version information
            try:
                version, updated_str = read_version_file()
                if version:
                    status.softwareVersion = version

                    # Parse the updated timestamp if provided
                    if updated_str:
                        try:
                            # Parse UTC timestamp format: "2025-07-21 15:12:10 UTC"
                            updated_str = updated_str.replace(' UTC', '')
                            updated_dt = datetime.strptime(updated_str, '%Y-%m-%d %H:%M:%S')
                            status.versionUpdatedAt = updated_dt.replace(tzinfo=timezone.utc)
                        except:
                            pass
            except Exception as e:
                log.warning(f"Error updating version info: {e}")

            session.commit()

            # Update logs
            update_server_logs(computer.computerId, session)

    except Exception as e:
        log.error(f"Error updating server monitoring: {e}")


def update_server_logs(computer_id: int, session):
    """Collect pm2 service logs and store them in the database.

    Captures the last 300 lines of logs from the backend, frontend, and
    Docker utility pm2 processes, then upserts them into the ServerLogs
    table.

    Args:
        computer_id: Database ID of the computer whose logs are being collected.
        session: Active SQLAlchemy session to use for database operations.
    """
    try:
        # Backend logs
        try:
            backend_logs = subprocess.check_output(
                ["pm2", "logs", "backend", "--lines", "300", "--nostream"],
                text=True, stderr=subprocess.STDOUT, timeout=10
            )
            update_log_record(session, computer_id, "backend", backend_logs, 300)
        except:
            pass

        # Frontend logs
        try:
            frontend_logs = subprocess.check_output(
                ["pm2", "logs", "frontend", "--lines", "300", "--nostream"],
                text=True, stderr=subprocess.STDOUT, timeout=10
            )
            update_log_record(session, computer_id, "frontend", frontend_logs, 300)
        except:
            pass

        # Docker utility logs
        try:
            docker_logs = subprocess.check_output(
                ["pm2", "logs", "backendDockerUtil", "--lines", "300", "--nostream"],
                text=True, stderr=subprocess.STDOUT, timeout=10
            )
            update_log_record(session, computer_id, "docker_utility", docker_logs, 300)
        except:
            pass

    except Exception as e:
        log.error(f"Error updating server logs: {e}")


def update_log_record(session, computer_id: int, log_type: str, content: str, lines: int):
    """Upsert a log record in the ServerLogs table.

    Creates a new log record if one does not exist for the given computer
    and log type, or updates the existing record's content and line count.

    Args:
        session: Active SQLAlchemy session to use for database operations.
        computer_id: Database ID of the computer the logs belong to.
        log_type: Type of log, e.g. "backend", "frontend", or "docker_utility".
        content: Full log text content to store.
        lines: Number of log lines captured.
    """
    try:
        log_record = session.execute(
            select(ServerLogs).where(
                ServerLogs.computerId == computer_id,
                ServerLogs.logType == log_type
            )
        ).scalar_one_or_none()

        if not log_record:
            log_record = ServerLogs(
                computerId=computer_id,
                logType=log_type
            )
            session.add(log_record)

        log_record.logContent = content
        log_record.logLines = lines
        session.commit()

    except Exception as e:
        log.error(f"Error updating {log_type} logs: {e}")
