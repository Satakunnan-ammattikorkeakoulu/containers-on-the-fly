"""Tests for container server docker/monitoring.py."""

import os
from unittest.mock import patch, MagicMock
from docker.monitoring import read_version_file, collect_server_metrics, collect_server_logs


class TestReadVersionFile:

    @patch("docker.monitoring.os.path.exists", return_value=True)
    @patch("builtins.open")
    def test_reads_valid_version_file(self, mock_open, mock_exists):
        mock_open.return_value.__enter__ = lambda s: s
        mock_open.return_value.__exit__ = lambda s, *a: None
        mock_open.return_value.read.return_value = "version: 1.2.3\nupdated: 2024-01-01 12:00:00 UTC"
        version, updated = read_version_file()
        assert version == "1.2.3"
        assert updated == "2024-01-01 12:00:00 UTC"

    @patch("docker.monitoring.os.path.exists", return_value=False)
    def test_returns_none_for_missing_file(self, mock_exists):
        version, updated = read_version_file()
        assert version is None
        assert updated is None

    @patch("docker.monitoring.os.path.exists", return_value=True)
    @patch("builtins.open")
    def test_handles_partial_content(self, mock_open, mock_exists):
        mock_open.return_value.__enter__ = lambda s: s
        mock_open.return_value.__exit__ = lambda s, *a: None
        mock_open.return_value.read.return_value = "version: 2.0.0"
        version, updated = read_version_file()
        assert version == "2.0.0"
        assert updated is None

    @patch("docker.monitoring.os.path.exists", return_value=True)
    @patch("builtins.open")
    def test_handles_empty_file(self, mock_open, mock_exists):
        mock_open.return_value.__enter__ = lambda s: s
        mock_open.return_value.__exit__ = lambda s, *a: None
        mock_open.return_value.read.return_value = ""
        version, updated = read_version_file()
        assert version is None
        assert updated is None

    @patch("docker.monitoring.os.path.exists", return_value=True)
    @patch("builtins.open", side_effect=PermissionError("denied"))
    def test_handles_read_error(self, mock_open, mock_exists):
        version, updated = read_version_file()
        assert version is None
        assert updated is None


class TestCollectServerMetrics:

    @patch("docker.monitoring.read_version_file", return_value=(None, None))
    @patch("docker.monitoring.time")
    @patch("docker.monitoring.psutil")
    def test_returns_cpu_and_memory_metrics(self, mock_psutil, mock_time, mock_version):
        mock_psutil.cpu_percent.return_value = 42.5
        mock_psutil.cpu_count.return_value = 8
        mem = MagicMock(total=16_000_000_000, used=8_000_000_000, percent=50.0)
        mock_psutil.virtual_memory.return_value = mem
        disk = MagicMock(total=500_000_000_000, used=250_000_000_000, free=250_000_000_000)
        mock_psutil.disk_usage.return_value = disk
        mock_psutil.getloadavg.return_value = (1.5, 1.2, 0.9)
        mock_psutil.boot_time.return_value = 0
        mock_time.time.return_value = 86400

        result = collect_server_metrics()
        assert result["cpuUsagePercent"] == 42.5
        assert result["cpuCores"] == 8
        assert result["memoryTotalBytes"] == 16_000_000_000
        assert result["memoryUsedBytes"] == 8_000_000_000
        assert result["diskTotalBytes"] == 500_000_000_000
        assert result["loadAvg1Min"] == 1.5
        assert result["systemUptimeSeconds"] == 86400

    @patch("docker.monitoring.read_version_file", return_value=("1.2.3", "2025-01-15 10:30:00 UTC"))
    @patch("docker.monitoring.time")
    @patch("docker.monitoring.psutil")
    def test_includes_version_info(self, mock_psutil, mock_time, mock_version):
        mock_psutil.cpu_percent.return_value = 10.0
        mock_psutil.cpu_count.return_value = 4
        mock_psutil.virtual_memory.return_value = MagicMock(total=8_000_000_000, used=4_000_000_000, percent=50.0)
        mock_psutil.disk_usage.return_value = MagicMock(total=100, used=50, free=50)
        mock_psutil.getloadavg.return_value = (0.5, 0.5, 0.5)
        mock_psutil.boot_time.return_value = 0
        mock_time.time.return_value = 100

        result = collect_server_metrics()
        assert result["softwareVersion"] == "1.2.3"
        assert "versionUpdatedAt" in result

    @patch("docker.monitoring.read_version_file", return_value=(None, None))
    @patch("docker.monitoring.psutil")
    def test_handles_docker_exception(self, mock_psutil, mock_version):
        mock_psutil.cpu_percent.return_value = 10.0
        mock_psutil.cpu_count.return_value = 4
        mock_psutil.virtual_memory.return_value = MagicMock(total=8_000_000_000, used=4_000_000_000, percent=50.0)
        mock_psutil.disk_usage.return_value = MagicMock(total=100, used=50, free=50)
        mock_psutil.getloadavg.return_value = (0.5, 0.5, 0.5)
        mock_psutil.boot_time.return_value = 0
        # docker import raises inside collect_server_metrics -> caught by try/except
        result = collect_server_metrics()
        assert "cpuUsagePercent" in result


class TestCollectServerLogs:

    @patch("docker.monitoring.subprocess.check_output")
    def test_returns_log_types(self, mock_output):
        mock_output.return_value = "some log output\n"
        result = collect_server_logs()
        assert result is not None
        assert "backend" in result
        assert "frontend" in result
        assert "docker_utility" in result
        assert result["backend"]["content"] == "some log output\n"
        assert result["backend"]["lines"] == 300

    @patch("docker.monitoring.subprocess.check_output", side_effect=Exception("pm2 not found"))
    def test_returns_none_on_total_failure(self, mock_output):
        result = collect_server_logs()
        assert result is None

    @patch("docker.monitoring.subprocess.check_output")
    def test_handles_partial_failure(self, mock_output):
        def side_effect(cmd, **kwargs):
            if "backend" in cmd:
                return "backend logs"
            raise Exception("not found")
        mock_output.side_effect = side_effect
        result = collect_server_logs()
        assert result is not None
        assert "backend" in result
        assert "frontend" not in result
