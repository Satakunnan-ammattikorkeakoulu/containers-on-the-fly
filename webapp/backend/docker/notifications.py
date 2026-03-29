import os
from helpers.email import send_email
from settings_handler import get_setting


def generate_connection_text(image, ip, ports, password, include_email_details, non_critical_errors, end_date=None):
    '''
    Generates the connection details text for a started container.
    Used both in emails and in the UI.

    Parameters:
        image (string): The name of the image used to start the container.
        ip (string): The ip of the machine where the container is running.
        ports (list): The ports used by the container. Example format: [ { serviceName: "ssh", localPort: 22, outsidePort: 2283 } ]
        password (string): The password of the container user.
        include_email_details (bool): Whether to include email-specific details (contact info, noreply notice).
        non_critical_errors (string): Non-critical error messages to include.
        end_date (datetime): The date when the container will be stopped.
    '''

    linesep = os.linesep

    help_text = ""
    if include_email_details:
        contact_email = get_setting('email.contactEmail')
        if contact_email:
            help_text = f"If you need help, contact: {contact_email}{linesep}{linesep}"

    help_text_ssh = ""
    found_item = None
    for port in ports:
        if (port["serviceName"] == "SSH"):
            found_item = port
            help_text_ssh += f"Connecting with Visual Studio Code (SSH):{linesep}"
            help_text_ssh += f"user@{ip}:{port['outsidePort']}"
            help_text_ssh += linesep + linesep
            help_text_ssh += f"Connecting from the terminal (SSH):{linesep}"
            help_text_ssh += f"ssh user@{ip} -p {port['outsidePort']}"
            help_text_ssh += linesep + linesep
            help_text_ssh += f"Password for the SSH connection:" + linesep
            help_text_ssh += f"{password}"
            help_text_ssh += linesep
    if found_item is not None:
        ports.remove(found_item)

    help_text_other = ""
    if len(ports) > 0:
        help_text_other += f"{linesep}"
        for port in ports:
            help_text_other += f"Service {port['serviceName']} is available through: {ip}:{port['outsidePort']} {linesep}"
        help_text_other += f"{linesep}-----{linesep}"

    general_text = ""
    try:
        general_text = get_setting('instructions.email')
    except Exception:
        pass

    end_date_text = ""
    if end_date is not None:
        # Get timezone from database settings
        timezone_name = "UTC"  # Default timezone
        try:
            timezone_name = get_setting('general.timezone')
        except Exception:
            pass

        # convert end_date from UTC to configured timezone
        from dateutil import tz
        end_date.replace(tzinfo=None)
        end_date = end_date.astimezone(tz.gettz(timezone_name))
        end_date_text = f"Your reservation will end at ({timezone_name}): {end_date.strftime('%Y-%m-%d %H:%M:%S')}"

    start_message = ""
    if include_email_details:
        start_message = f"Container with image {image} is ready to use.{linesep}{linesep}-----{linesep}"

    no_reply = ""
    if include_email_details:
        no_reply = f"This is a noreply email account. Please do not reply to this email.{linesep}{linesep}"

    # Body text
    body = f"""
{start_message}
{help_text_ssh}
-----
{help_text_other}
IP address of the machine: {ip}

{general_text}

{no_reply}{help_text}{non_critical_errors}
"""

    return body


def send_container_started_email(user_email, image_name, computer_ip, ports, password, non_critical_errors, end_date):
    """Send email notification when a container starts successfully."""
    if not get_setting('email.sendEmail'):
        return

    body = generate_connection_text(
        image_name, computer_ip, ports, password,
        True, non_critical_errors, end_date
    )
    send_email(user_email, "AI Server is ready to use!", body)


def send_container_error_email(user_email, errors):
    """Send email notification when a container fails to start."""
    if not get_setting('email.sendEmail'):
        return

    linesep = os.linesep
    body = f"Your AI server reservation did not start as there was an error. {linesep}{linesep}"
    body += f"The error was: {linesep}{linesep}{errors}{linesep}{linesep}"
    body += "Please do not reply to this email, this email is sent from a noreply email address."
    send_email(user_email, "AI Server did not start", body)


def send_admin_failure_alert(user_email, reservation_id, image_name, server_name, errors):
    """Send container failure alerts to admin emails using existing helpers/email.py infrastructure."""
    try:
        alerts_enabled = get_setting('notifications.containerAlertsEnabled')
        if not alerts_enabled:
            return

        alert_emails = get_setting('notifications.alertEmails')
        if not alert_emails or len(alert_emails) == 0:
            print("Container failure alerts enabled but no alert emails configured")
            return

        # Create list of recipients, removing user's email to avoid duplicate notification
        recipients = set(alert_emails)
        if user_email in recipients:
            recipients.remove(user_email)

        if not recipients:
            print("Container failure alerts enabled but no additional recipients (user already notified)")
            return

        linesep = os.linesep
        admin_body = f"Container Failure Alert{linesep}{linesep}"
        admin_body += f"A container reservation failed to start for user: {user_email}{linesep}"
        admin_body += f"Reservation ID: {reservation_id}{linesep}"
        admin_body += f"Container Image: {image_name}{linesep}"
        admin_body += f"Server: {server_name}{linesep}"
        admin_body += f"Error: {errors}{linesep}{linesep}"
        admin_body += "This is an automated notification from the container management system."

        successful_sends = 0
        for admin_email in recipients:
            try:
                send_email(admin_email, "Container Failure Alert", admin_body)
                successful_sends += 1
            except Exception as email_error:
                print(f"Failed to send alert to {admin_email}: {email_error}")

        if successful_sends > 0:
            print(f"Container failure alerts sent to {successful_sends}/{len(recipients)} admin(s)")
        else:
            print(f"Failed to send container failure alerts to any of {len(recipients)} admin(s)")

    except Exception as e:
        print(f"Warning: Failed to send container failure alerts: {e}")
