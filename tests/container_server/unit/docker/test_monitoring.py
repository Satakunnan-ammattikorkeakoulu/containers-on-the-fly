"""Tests for container server docker/monitoring.py."""

import os
from unittest.mock import patch
from docker.monitoring import read_version_file


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
