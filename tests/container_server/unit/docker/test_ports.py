"""Tests for container server docker/ports.py."""

from unittest.mock import patch, MagicMock
from docker.ports import is_port_in_use, get_available_port


class TestIsPortInUse:

    @patch("docker.ports.socket.socket")
    def test_port_in_use_returns_true(self, mock_socket_cls):
        mock_sock = MagicMock()
        mock_sock.connect_ex.return_value = 0
        mock_socket_cls.return_value.__enter__ = MagicMock(return_value=mock_sock)
        mock_socket_cls.return_value.__exit__ = MagicMock(return_value=False)
        assert is_port_in_use(8080) is True

    @patch("docker.ports.socket.socket")
    def test_port_not_in_use_returns_false(self, mock_socket_cls):
        mock_sock = MagicMock()
        mock_sock.connect_ex.return_value = 1
        mock_socket_cls.return_value.__enter__ = MagicMock(return_value=mock_sock)
        mock_socket_cls.return_value.__exit__ = MagicMock(return_value=False)
        assert is_port_in_use(8080) is False


class TestGetAvailablePort:

    @patch("docker.ports.is_port_in_use", return_value=False)
    @patch("docker.ports.settings_handler")
    def test_returns_port_in_range(self, mock_settings, mock_in_use):
        mock_settings.get_setting.side_effect = lambda k: {
            "docker.port_range_start": 20000,
            "docker.port_range_end": 20100,
        }[k]
        port = get_available_port()
        assert 20000 <= port < 20100

    @patch("docker.ports.is_port_in_use")
    @patch("docker.ports.settings_handler")
    def test_retries_when_ports_in_use(self, mock_settings, mock_in_use):
        mock_settings.get_setting.side_effect = lambda k: {
            "docker.port_range_start": 20000,
            "docker.port_range_end": 20010,
        }[k]
        # All ports busy except the last attempt
        call_count = [0]
        def side_effect(port):
            call_count[0] += 1
            return call_count[0] < 5
        mock_in_use.side_effect = side_effect
        port = get_available_port()
        assert 20000 <= port < 20010

    @patch("docker.ports.random.choice", return_value=20050)
    @patch("docker.ports.is_port_in_use", return_value=True)
    @patch("docker.ports.settings_handler")
    def test_falls_back_after_50_attempts(self, mock_settings, mock_in_use, mock_choice):
        mock_settings.get_setting.side_effect = lambda k: {
            "docker.port_range_start": 20000,
            "docker.port_range_end": 20100,
        }[k]
        port = get_available_port()
        # After 50 failed attempts, falls back to random choice
        assert port == 20050
        assert mock_in_use.call_count == 50
