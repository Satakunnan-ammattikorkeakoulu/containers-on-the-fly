import smtplib
import socket
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from settings_handler import getSetting

def send_email(to, mail_subject, mail_body):

    # Check if email sending is enabled
    if not getSetting('email.sendEmail'):
        return

    # Get SMTP settings from database
    smtp_server = getSetting('email.smtpServer')
    smtp_port = getSetting('email.smtpPort')
    smtp_username = getSetting('email.smtpUsername')
    smtp_password = getSetting('email.smtpPassword')
    from_email = getSetting('email.fromEmail')

    # Check if all required settings are configured
    if not all([smtp_server, smtp_port, smtp_username, smtp_password, from_email]):
        print("Email settings are incomplete in the database. Email not sent.")
        return

    username = smtp_username
    mail_from = from_email
    password = smtp_password
    smtpAddress = smtp_server
    smtpPort = smtp_port

    mimemsg = MIMEMultipart()
    mimemsg['From'] = mail_from
    mimemsg['To'] = to
    mimemsg['Subject'] = mail_subject
    mimemsg.attach(MIMEText(mail_body, 'plain'))
    try:
        connection = smtplib.SMTP(host = smtpAddress, port = smtpPort)
        connection.starttls()
        connection.login(username,password)
        connection.send_message(mimemsg)
        connection.quit()
    except (smtplib.SMTPConnectError, smtplib.SMTPAuthenticationError, socket.gaierror, socket.error, Exception) as e:
        print(f"Something went wrong sending email: {e}")
        return