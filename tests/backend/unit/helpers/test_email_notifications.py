"""Tests for helpers/email_notifications.py."""

from unittest.mock import patch, MagicMock
from helpers.email_notifications import (
    generate_connection_text,
    send_container_started_email,
    send_container_error_email,
    send_container_resume_failed_email,
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

    @staticmethod
    def _started_settings(key):
        """Return appropriate values for each setting key used by send_container_started_email."""
        return {
            "email.sendEmail": True,
            "email.enableContainerStarted": True,
            "email.subjectContainerStarted": "Server is ready to use!",
            "email.bodyIntroContainerStarted": "",
            "email.lowPriorityNotice": "Note: low-priority test notice.",
        }.get(key, None)

    @patch("helpers.email_notifications.send_email")
    @patch("helpers.email_notifications.get_setting")
    def test_sends_when_enabled(self, mock_setting, mock_send):
        mock_setting.side_effect = self._started_settings
        ports = [{"serviceName": "SSH", "localPort": 22, "outsidePort": 2001, "portType": "SSH"}]
        send_container_started_email("user@test.com", "ubuntu", "10.0.0.1", ports, "pass", "", None)
        mock_send.assert_called_once()
        assert mock_send.call_args[0][0] == "user@test.com"

    @patch("helpers.email_notifications.send_email")
    @patch("helpers.email_notifications.get_setting", return_value=False)
    def test_skips_when_disabled(self, mock_setting, mock_send):
        send_container_started_email("user@test.com", "ubuntu", "10.0.0.1", [], "pass", "", None)
        mock_send.assert_not_called()

    @patch("helpers.email_notifications.send_email")
    @patch("helpers.email_notifications.get_setting")
    def test_low_priority_notice_included(self, mock_setting, mock_send):
        mock_setting.side_effect = self._started_settings
        ports = [{"serviceName": "SSH", "localPort": 22, "outsidePort": 2001, "portType": "SSH"}]
        send_container_started_email("user@test.com", "ubuntu", "10.0.0.1", ports, "pass", "", None,
                                     is_low_priority=True)
        mock_send.assert_called_once()
        body = mock_send.call_args[0][2]
        assert "low-priority test notice" in body

    @patch("helpers.email_notifications.send_email")
    @patch("helpers.email_notifications.get_setting")
    def test_low_priority_notice_omitted_for_normal(self, mock_setting, mock_send):
        mock_setting.side_effect = self._started_settings
        ports = [{"serviceName": "SSH", "localPort": 22, "outsidePort": 2001, "portType": "SSH"}]
        send_container_started_email("user@test.com", "ubuntu", "10.0.0.1", ports, "pass", "", None)
        mock_send.assert_called_once()
        body = mock_send.call_args[0][2]
        assert "low-priority test notice" not in body


class TestSendContainerErrorEmail:

    @staticmethod
    def _error_settings(key):
        """Return appropriate values for each setting key used by send_container_error_email."""
        return {
            "email.sendEmail": True,
            "email.enableContainerError": True,
            "email.subjectContainerError": "Server did not start",
            "email.bodyIntroContainerError": "",
        }.get(key, None)

    @patch("helpers.email_notifications.send_email")
    @patch("helpers.email_notifications.get_setting")
    def test_sends_error_body(self, mock_setting, mock_send):
        mock_setting.side_effect = self._error_settings
        send_container_error_email("user@test.com", "GPU not available")
        mock_send.assert_called_once()
        body = mock_send.call_args[0][2]
        assert "GPU not available" in body

    @patch("helpers.email_notifications.send_email")
    @patch("helpers.email_notifications.get_setting", return_value=False)
    def test_skips_when_disabled(self, mock_setting, mock_send):
        send_container_error_email("user@test.com", "error")
        mock_send.assert_not_called()


class TestSendContainerResumeFailedEmail:

    @staticmethod
    def _resume_failed_settings(key):
        """Return appropriate values for each setting key used by send_container_resume_failed_email."""
        return {
            "email.sendEmail": True,
            "email.enableContainerResumeFailed": True,
            "email.subjectContainerResumeFailed": "Low-priority container failed to resume",
            "email.bodyIntroContainerResumeFailed": "",
        }.get(key, None)

    @patch("helpers.email_notifications.send_email")
    @patch("helpers.email_notifications.get_setting")
    def test_sends_resume_failure_body(self, mock_setting, mock_send):
        mock_setting.side_effect = self._resume_failed_settings
        send_container_resume_failed_email("user@test.com", "ubuntu", "server1", 42, "OOM killed")
        mock_send.assert_called_once()
        subject = mock_send.call_args[0][1]
        body = mock_send.call_args[0][2]
        assert subject == "Low-priority container failed to resume"
        assert "ubuntu" in body
        assert "server1" in body
        assert "42" in body
        assert "OOM killed" in body
        # Should explain it won't be retried automatically
        assert "NOT be retried" in body or "not be retried" in body
        # Should explain data preservation
        assert "preserved" in body

    @patch("helpers.email_notifications.send_email")
    @patch("helpers.email_notifications.get_setting", return_value=False)
    def test_skips_when_disabled(self, mock_setting, mock_send):
        send_container_resume_failed_email("user@test.com", "ubuntu", "server1", 42, "error")
        mock_send.assert_not_called()


class TestSendContainerPausedEmail:

    @staticmethod
    def _paused_settings(key):
        """Return appropriate values for each setting key used by send_container_paused_email."""
        return {
            "email.sendEmail": True,
            "email.enableContainerPaused": True,
            "email.subjectContainerPaused": "Low-priority container paused",
            "email.bodyIntroContainerPaused": "",
        }.get(key, None)

    @patch("helpers.email_notifications.send_email")
    @patch("helpers.email_notifications.get_setting")
    def test_sends_pause_notification(self, mock_setting, mock_send):
        mock_setting.side_effect = self._paused_settings
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
