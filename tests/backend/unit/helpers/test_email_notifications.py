"""Tests for helpers/email_notifications.py."""

from unittest.mock import patch, MagicMock
from helpers.email_notifications import (
    generate_connection_text,
    send_container_started_email,
    send_container_error_email,
    send_container_paused_email,
    send_admin_failure_alert,
)


class TestGenerateConnectionText:

    def _make_ports(self):
        return [
            {"serviceName": "SSH", "localPort": 22, "outsidePort": 2001, "portType": "SSH"},
            {"serviceName": "Jupyter", "localPort": 8888, "outsidePort": 2002, "portType": None},
        ]

    @patch("helpers.email_notifications.get_setting", return_value=None)
    def test_ssh_port_formatted(self, mock_setting):
        ports = self._make_ports()
        text = generate_connection_text("ubuntu", "10.0.0.1", ports, "pass123", False, "")
        assert "ssh user@10.0.0.1 -p 2001" in text
        assert "pass123" in text

    @patch("helpers.email_notifications.get_setting", return_value=None)
    def test_non_ssh_ports_listed(self, mock_setting):
        ports = self._make_ports()
        text = generate_connection_text("ubuntu", "10.0.0.1", ports, "pass", False, "")
        assert "Jupyter" in text
        assert "2002" in text

    @patch("helpers.email_notifications.get_setting", return_value=None)
    def test_password_included(self, mock_setting):
        ports = [{"serviceName": "SSH", "localPort": 22, "outsidePort": 2001, "portType": "SSH"}]
        text = generate_connection_text("ubuntu", "10.0.0.1", ports, "s3cret", False, "")
        assert "s3cret" in text

    @patch("helpers.email_notifications.get_setting", return_value="admin@test.com")
    def test_email_details_included(self, mock_setting):
        ports = [{"serviceName": "SSH", "localPort": 22, "outsidePort": 2001, "portType": "SSH"}]
        text = generate_connection_text("ubuntu", "10.0.0.1", ports, "pass", True, "")
        assert "ready to use" in text
        assert "noreply" in text

    @patch("helpers.email_notifications.get_setting", return_value=None)
    def test_email_details_excluded(self, mock_setting):
        ports = [{"serviceName": "SSH", "localPort": 22, "outsidePort": 2001, "portType": "SSH"}]
        text = generate_connection_text("ubuntu", "10.0.0.1", ports, "pass", False, "")
        assert "noreply" not in text

    @patch("helpers.email_notifications.get_setting", return_value=None)
    def test_non_critical_errors_appended(self, mock_setting):
        ports = [{"serviceName": "SSH", "localPort": 22, "outsidePort": 2001, "portType": "SSH"}]
        text = generate_connection_text("ubuntu", "10.0.0.1", ports, "pass", False, "Warning: something")
        assert "Warning: something" in text

    @patch("helpers.email_notifications.get_setting", return_value=None)
    def test_custom_username(self, mock_setting):
        ports = [{"serviceName": "SSH", "localPort": 22, "outsidePort": 2001, "portType": "SSH"}]
        text = generate_connection_text("ubuntu", "10.0.0.1", ports, "pass", False, "", username="student")
        assert "student@10.0.0.1" in text

    @patch("helpers.email_notifications.get_setting", return_value=None)
    def test_ip_address_shown(self, mock_setting):
        ports = []
        text = generate_connection_text("ubuntu", "192.168.1.1", ports, "pass", False, "")
        assert "192.168.1.1" in text


class TestSendContainerStartedEmail:

    @patch("helpers.email_notifications.send_email")
    @patch("helpers.email_notifications.get_setting")
    def test_sends_when_enabled(self, mock_setting, mock_send):
        mock_setting.return_value = True
        ports = [{"serviceName": "SSH", "localPort": 22, "outsidePort": 2001, "portType": "SSH"}]
        send_container_started_email("user@test.com", "ubuntu", "10.0.0.1", ports, "pass", "", None)
        mock_send.assert_called_once()
        assert mock_send.call_args[0][0] == "user@test.com"

    @patch("helpers.email_notifications.send_email")
    @patch("helpers.email_notifications.get_setting", return_value=False)
    def test_skips_when_disabled(self, mock_setting, mock_send):
        send_container_started_email("user@test.com", "ubuntu", "10.0.0.1", [], "pass", "", None)
        mock_send.assert_not_called()


class TestSendContainerErrorEmail:

    @patch("helpers.email_notifications.send_email")
    @patch("helpers.email_notifications.get_setting", return_value=True)
    def test_sends_error_body(self, mock_setting, mock_send):
        send_container_error_email("user@test.com", "GPU not available")
        mock_send.assert_called_once()
        body = mock_send.call_args[0][2]
        assert "GPU not available" in body

    @patch("helpers.email_notifications.send_email")
    @patch("helpers.email_notifications.get_setting", return_value=False)
    def test_skips_when_disabled(self, mock_setting, mock_send):
        send_container_error_email("user@test.com", "error")
        mock_send.assert_not_called()


class TestSendContainerPausedEmail:

    @patch("helpers.email_notifications.send_email")
    @patch("helpers.email_notifications.get_setting", return_value=True)
    def test_sends_pause_notification(self, mock_setting, mock_send):
        send_container_paused_email("user@test.com", "ubuntu", "server1", 42)
        mock_send.assert_called_once()
        body = mock_send.call_args[0][2]
        assert "paused" in body
        assert "42" in body

    @patch("helpers.email_notifications.send_email")
    @patch("helpers.email_notifications.get_setting", return_value=False)
    def test_skips_when_disabled(self, mock_setting, mock_send):
        send_container_paused_email("user@test.com", "ubuntu", "server1", 42)
        mock_send.assert_not_called()


class TestSendAdminFailureAlert:

    @patch("helpers.email_notifications.send_email")
    @patch("helpers.email_notifications.get_setting")
    def test_sends_to_admins_excluding_user(self, mock_setting, mock_send):
        def setting_side_effect(key):
            return {
                "notifications.containerAlertsEnabled": True,
                "notifications.alertEmails": ["admin1@test.com", "admin2@test.com", "user@test.com"],
            }.get(key)
        mock_setting.side_effect = setting_side_effect

        send_admin_failure_alert("user@test.com", 1, "ubuntu", "srv1", "GPU error")
        # Should send to admin1 and admin2, not user
        assert mock_send.call_count == 2

    @patch("helpers.email_notifications.send_email")
    @patch("helpers.email_notifications.get_setting")
    def test_skips_when_alerts_disabled(self, mock_setting, mock_send):
        mock_setting.return_value = False
        send_admin_failure_alert("user@test.com", 1, "ubuntu", "srv1", "error")
        mock_send.assert_not_called()

    @patch("helpers.email_notifications.send_email")
    @patch("helpers.email_notifications.get_setting")
    def test_skips_when_no_alert_emails(self, mock_setting, mock_send):
        def setting_side_effect(key):
            return {
                "notifications.containerAlertsEnabled": True,
                "notifications.alertEmails": [],
            }.get(key)
        mock_setting.side_effect = setting_side_effect

        send_admin_failure_alert("user@test.com", 1, "ubuntu", "srv1", "error")
        mock_send.assert_not_called()
