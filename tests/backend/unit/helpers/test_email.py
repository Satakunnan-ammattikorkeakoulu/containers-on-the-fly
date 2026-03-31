"""Tests for helpers/email.py — with mocked SMTP and settings."""

from unittest.mock import patch, MagicMock
from helpers.email import send_email


class TestSendEmail:

    @patch("helpers.email.get_setting")
    def test_does_not_send_when_disabled(self, mock_get_setting):
        mock_get_setting.return_value = False
        # Should return immediately without attempting SMTP
        send_email("test@example.com", "Subject", "Body")
        # get_setting should only be called once (for email.sendEmail)
        mock_get_setting.assert_called_once_with("email.sendEmail")

    @patch("helpers.email.get_setting")
    def test_does_not_send_with_incomplete_settings(self, mock_get_setting):
        def side_effect(key):
            values = {
                "email.sendEmail": True,
                "email.smtpServer": "",  # Missing
                "email.smtpPort": 587,
                "email.smtpUsername": "user",
                "email.smtpPassword": "pass",
                "email.fromEmail": "from@example.com",
            }
            return values.get(key)

        mock_get_setting.side_effect = side_effect
        # Should print warning and return without crashing
        send_email("test@example.com", "Subject", "Body")

    @patch("helpers.email.smtplib")
    @patch("helpers.email.get_setting")
    def test_sends_email_with_starttls(self, mock_get_setting, mock_smtplib):
        def side_effect(key):
            values = {
                "email.sendEmail": True,
                "email.smtpServer": "smtp.example.com",
                "email.smtpPort": 587,
                "email.smtpUsername": "user",
                "email.smtpPassword": "pass",
                "email.fromEmail": "from@example.com",
            }
            return values.get(key)

        mock_get_setting.side_effect = side_effect
        mock_smtp = MagicMock()
        mock_smtplib.SMTP.return_value = mock_smtp

        send_email("test@example.com", "Test Subject", "Test Body")

        mock_smtplib.SMTP.assert_called_once_with(host="smtp.example.com", port=587)
        mock_smtp.starttls.assert_called_once()
        mock_smtp.login.assert_called_once_with("user", "pass")
        mock_smtp.send_message.assert_called_once()
        mock_smtp.quit.assert_called_once()

    @patch("helpers.email.smtplib")
    @patch("helpers.email.get_setting")
    def test_sends_email_with_ssl_on_port_465(self, mock_get_setting, mock_smtplib):
        def side_effect(key):
            values = {
                "email.sendEmail": True,
                "email.smtpServer": "smtp.example.com",
                "email.smtpPort": 465,
                "email.smtpUsername": "user",
                "email.smtpPassword": "pass",
                "email.fromEmail": "from@example.com",
            }
            return values.get(key)

        mock_get_setting.side_effect = side_effect
        mock_smtp = MagicMock()
        mock_smtplib.SMTP_SSL.return_value = mock_smtp

        send_email("test@example.com", "Test Subject", "Test Body")

        mock_smtplib.SMTP_SSL.assert_called_once_with(host="smtp.example.com", port=465)
        mock_smtp.login.assert_called_once()
        mock_smtp.send_message.assert_called_once()
