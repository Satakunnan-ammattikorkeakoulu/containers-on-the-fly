"""Email sending utilities.

Provides SMTP-based email sending with support for both SSL/TLS (port 465)
and STARTTLS connections. All SMTP configuration is read from system settings.
"""

import smtplib
import socket
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from settings_handler import get_setting

def send_email(to, mail_subject, mail_body):
    """Send a plain-text email using the configured SMTP server.

    Does nothing if email sending is disabled in settings or if required
    SMTP settings are incomplete. Uses SSL/TLS for port 465 and STARTTLS
    for other ports (typically 587). Errors are printed to stdout rather
    than raised.

    Args:
        to: Recipient email address.
        mail_subject: The email subject line.
        mail_body: The plain-text body of the email.
    """

    # Check if email sending is enabled
    if not get_setting('email.sendEmail'):
        return

    # Get SMTP settings from database
    smtp_server = get_setting('email.smtpServer')
    smtp_port = get_setting('email.smtpPort')
    smtp_username = get_setting('email.smtpUsername')
    smtp_password = get_setting('email.smtpPassword')
    from_email = get_setting('email.fromEmail')

    # Check if all required settings are configured
    if not all([smtp_server, smtp_port, smtp_username, smtp_password, from_email]):
        print("Email settings are incomplete in the database. Email not sent.")
        return

    username = smtp_username
    mail_from = from_email
    password = smtp_password
    smtp_address = smtp_server
    smtp_port_num = smtp_port

    mimemsg = MIMEMultipart()
    mimemsg['From'] = mail_from
    mimemsg['To'] = to
    mimemsg['Subject'] = mail_subject
    mimemsg.attach(MIMEText(mail_body, 'plain'))
    try:
        # Use SSL/TLS for port 465, STARTTLS for other ports (typically 587)
        if smtp_port_num == 465:
            connection = smtplib.SMTP_SSL(host = smtp_address, port = smtp_port_num)
        else:
            connection = smtplib.SMTP(host = smtp_address, port = smtp_port_num)
            connection.starttls()
        connection.login(username,password)
        connection.send_message(mimemsg)
        connection.quit()
    except (smtplib.SMTPConnectError, smtplib.SMTPAuthenticationError, socket.gaierror, socket.error, Exception) as e:
        print(f"Something went wrong sending email: {e}")
        return