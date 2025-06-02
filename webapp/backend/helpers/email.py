import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from settings import settings

def send_email(to, mail_subject, mail_body):

    if "sendEmail" not in settings.email or settings.email["sendEmail"] is False:
        return

    if "emailAddress" not in settings.email or "smtpPassword" not in settings.email or "smtpAddress" not in settings.email or "smtpPort" not in settings.email:
        print("Email settings are not set in the settings file. Email not sent.")
        return

    username = settings.email["emailAddress"]
    mail_from = settings.email["emailAddress"]
    password = settings.email["smtpPassword"]
    smtpAddress = settings.email["smtpAddress"]
    smtpPort = settings.email["smtpPort"]

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
    except (smtplib.SMTPConnectError, smtplib.SMTPAuthenticationError) as e:
        print(f"Something went wrong sending email: {e}")