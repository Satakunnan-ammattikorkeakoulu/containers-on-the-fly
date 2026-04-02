"""Server monitoring and log collection for container servers.

Collects system metrics (CPU, memory, disk, Docker container counts,
load averages, uptime, software version) and pm2 service logs, returning
them as dictionaries for submission to the backend API.
"""

import os
import psutil
import subprocess
import time
from datetime import datetime, timezone
from helpers.logger import log


def read_version_file():
    """Read version information from the project's .version file.

    Returns:
        tuple: (version, updated) strings, or (None, None) if unavailable.
    """
    try:
        version_file_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', '.version')
        if os.path.exists(version_file_path):
            with open(version_file_path, 'r') as f:
                content = f.read().strip()
            version_info = {}
            for line in content.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    version_info[key.strip()] = value.strip()
            return version_info.get('version'), version_info.get('updated')
        return None, None
    except Exception as e:
        log.warning(f"Error reading version file: {e}")
        return None, None


def collect_server_metrics() -> dict:
    """Collect system metrics and return as a dictionary.

    Gathers CPU usage, memory usage, disk usage, Docker container counts,
    system load averages, uptime, and software version.

    Returns:
        Dict with all metric fields matching the MonitoringRequest model.
    """
    metrics = {}

    try:
        metrics["cpuUsagePercent"] = round(psutil.cpu_percent(interval=1), 1)
        metrics["cpuCores"] = psutil.cpu_count()

        memory = psutil.virtual_memory()
        metrics["memoryTotalBytes"] = memory.total
        metrics["memoryUsedBytes"] = memory.used
        metrics["memoryUsagePercent"] = round(memory.percent, 1)

        try:
            disk = psutil.disk_usage('/')
            metrics["diskTotalBytes"] = disk.total
            metrics["diskUsedBytes"] = disk.used
            metrics["diskFreeBytes"] = disk.free
            metrics["diskUsagePercent"] = round((disk.used / disk.total) * 100, 1)
        except Exception:
            pass

        try:
            from python_on_whales import docker
            running_containers = docker.container.list()
            all_containers = docker.container.list(all=True)
            metrics["dockerContainersRunning"] = len(running_containers)
            metrics["dockerContainersTotal"] = len(all_containers)
        except Exception:
            pass

        try:
            load_avg = psutil.getloadavg()
            metrics["loadAvg1Min"] = round(load_avg[0], 2)
            metrics["loadAvg5Min"] = round(load_avg[1], 2)
            metrics["loadAvg15Min"] = round(load_avg[2], 2)
        except Exception:
            pass

        try:
            metrics["systemUptimeSeconds"] = int(time.time() - psutil.boot_time())
        except Exception:
            pass

        try:
            version, updated_str = read_version_file()
            if version:
                metrics["softwareVersion"] = version
                if updated_str:
                    try:
                        updated_str = updated_str.replace(' UTC', '')
                        updated_dt = datetime.strptime(updated_str, '%Y-%m-%d %H:%M:%S')
                        metrics["versionUpdatedAt"] = updated_dt.replace(tzinfo=timezone.utc).isoformat()
                    except Exception:
                        pass
        except Exception:
            pass

    except Exception as e:
        log.error(f"Error collecting server metrics: {e}")

    return metrics


def collect_server_logs() -> dict:
    """Collect pm2 service logs and return as a dictionary.

    Captures the last 300 lines of logs from the backend, frontend, and
    container server pm2 processes.

    Returns:
        Dict mapping log type to {content, lines} dicts, or None on error.
    """
    logs = {}

    try:
        for pm2_name, log_type in [("backend", "backend"), ("frontend", "frontend"), ("backendDockerUtil", "docker_utility")]:
            try:
                output = subprocess.check_output(
                    ["pm2", "logs", pm2_name, "--lines", "300", "--nostream"],
                    text=True, stderr=subprocess.STDOUT, timeout=10
                )
                logs[log_type] = {"content": output, "lines": 300}
            except Exception:
                pass
    except Exception as e:
        log.error(f"Error collecting server logs: {e}")

    return logs if logs else None
