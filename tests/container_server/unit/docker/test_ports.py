"""Tests for container server docker/ports.py."""

import pytest
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
        result = get_available_port()
        assert 20000 <= result["port"] < 20100
        assert result["stolen"] is False

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
        result = get_available_port()
        assert 20000 <= result["port"] < 20010
        assert result["stolen"] is False

    @patch("docker.ports.secrets.choice", return_value=20050)
    @patch("docker.ports.is_port_in_use", return_value=True)
    @patch("docker.ports.settings_handler")
    def test_falls_back_after_50_attempts(self, mock_settings, mock_in_use, mock_choice):
        mock_settings.get_setting.side_effect = lambda k: {
            "docker.port_range_start": 20000,
            "docker.port_range_end": 20100,
        }[k]
        result = get_available_port()
        # After 50 failed attempts in the first pass, the last-resort
        # random-choice fallback returns the mocked value.
        assert result["port"] == 20050
        assert result["stolen"] is False
        assert mock_in_use.call_count == 50

    @patch("docker.ports.is_port_in_use", return_value=False)
    @patch("docker.ports.settings_handler")
    def test_excludes_specified_ports(self, mock_settings, mock_in_use):
        mock_settings.get_setting.side_effect = lambda k: {
            "docker.port_range_start": 20000,
            "docker.port_range_end": 20003,
        }[k]
        # Range is 20000, 20001, 20002. Exclude two — only 20002 remains.
        result = get_available_port(exclude={20000, 20001})
        assert result["port"] == 20002
        assert result["stolen"] is False

    @patch("docker.ports.is_port_in_use", return_value=False)
    @patch("docker.ports.settings_handler")
    def test_raises_when_all_ports_excluded(self, mock_settings, mock_in_use):
        mock_settings.get_setting.side_effect = lambda k: {
            "docker.port_range_start": 20000,
            "docker.port_range_end": 20003,
        }[k]
        with pytest.raises(RuntimeError, match="No ports left"):
            get_available_port(exclude={20000, 20001, 20002})

    @patch("docker.ports.is_port_in_use", return_value=False)
    @patch("docker.ports.settings_handler")
    def test_soft_exclude_avoided_when_room_available(self, mock_settings, mock_in_use):
        mock_settings.get_setting.side_effect = lambda k: {
            "docker.port_range_start": 20000,
            "docker.port_range_end": 20003,
        }[k]
        # Range is 20000, 20001, 20002. Soft-exclude 20001 and 20002 —
        # only 20000 remains and should be returned without stealing.
        result = get_available_port(soft_exclude={20001, 20002})
        assert result["port"] == 20000
        assert result["stolen"] is False

    @patch("docker.ports.is_port_in_use", return_value=False)
    @patch("docker.ports.settings_handler")
    def test_soft_exclude_steal_when_range_exhausted(self, mock_settings, mock_in_use):
        mock_settings.get_setting.side_effect = lambda k: {
            "docker.port_range_start": 20000,
            "docker.port_range_end": 20003,
        }[k]
        # Hard-exclude covers 20000 and 20001. Soft-exclude covers 20002.
        # First pass finds nothing; second pass must steal 20002.
        result = get_available_port(exclude={20000, 20001}, soft_exclude={20002})
        assert result["port"] == 20002
        assert result["stolen"] is True

    @patch("docker.ports.is_port_in_use", return_value=False)
    @patch("docker.ports.settings_handler")
    def test_soft_exclude_not_stolen_when_ignored_port_is_outside_held(self, mock_settings, mock_in_use):
        mock_settings.get_setting.side_effect = lambda k: {
            "docker.port_range_start": 20000,
            "docker.port_range_end": 20004,
        }[k]
        # Range: 20000..20003. Soft-exclude 20000. First pass can pick
        # from {20001, 20002, 20003} — no steal.
        result = get_available_port(soft_exclude={20000})
        assert result["port"] in {20001, 20002, 20003}
        assert result["stolen"] is False

    @patch("docker.ports.is_port_in_use", return_value=False)
    @patch("docker.ports.settings_handler")
    def test_hard_exclude_wins_over_soft_exclude(self, mock_settings, mock_in_use):
        mock_settings.get_setting.side_effect = lambda k: {
            "docker.port_range_start": 20000,
            "docker.port_range_end": 20003,
        }[k]
        # Hard-exclude covers every port in the range — must raise, not
        # steal from soft_exclude.
        with pytest.raises(RuntimeError, match="No ports left"):
            get_available_port(
                exclude={20000, 20001, 20002},
                soft_exclude={20000, 20001},
            )
