"""Email notification templates for container lifecycle events.

Generates human-readable connection instructions for started containers
and sends email notifications for container start, error, pause, resume,
and failure events. Called by daemon response handlers when container
state changes.
"""

import os
from helpers.email_sender import send_email
from helpers.settings_handler import get_setting
from helpers.logger import log


def _render_port_url(port_type, ip, outside_port):
    """Render a connection URL based on the port type.

    Args:
        port_type: Port type string ("HTTP", "HTTPS", "VNC", or None/other for plain TCP).
        ip: IP address of the host machine.
        outside_port: External port number.

    Returns:
        str: Formatted URL or address string.
    """
    if port_type == "HTTP":
        return f"http://{ip}:{outside_port}"
    elif port_type == "HTTPS":
        return f"https://{ip}:{outside_port}"
    elif port_type == "VNC":
        return f"vnc://{ip}:{outside_port}"
    else:
        return f"{ip}:{outside_port}"


def generate_connection_text(image, ip, ports, password, include_email_details,
                             non_critical_errors, end_date=None, username="user",
                             ssh_methods=None, primary_connection_port_id=None):
    """Generate connection details text for a started container.

    Builds a formatted text block containing SSH connection instructions,
    other service endpoints, the container password, and optionally
    email-specific details such as contact information and no-reply
    notices. Used both in notification emails and in the UI.

    Args:
        image: Name of the Docker image used to start the container.
        ip: IP address of the host machine running the container.
        ports: List of port dictionaries, each containing serviceName,
            localPort, outsidePort, and optionally portType keys. The
            SSH port entry is extracted and formatted specially.
        password: Password for the container's user account.
        include_email_details: Whether to include email-specific text
            such as contact info and no-reply notice.
        non_critical_errors: Non-critical error messages to append to
            the output text.
        end_date: Optional datetime when the reservation ends. Converted
            to the configured timezone for display.
        username: Container username for SSH connection strings.
        ssh_methods: Optional list of SSH connection method dicts. If None,
            fetched from system settings.
        primary_connection_port_id: Optional ContainerPort ID of the primary
            connection method. None means SSH is primary.

    Returns:
        str: Formatted connection details text.

    Note:
        This function mutates the ports list by removing the SSH port
        entry if found.
    """

    linesep = os.linesep

    # Load SSH methods from settings if not provided
    if ssh_methods is None:
        try:
            ssh_methods = get_setting('connection.sshMethods')
        except Exception:
            ssh_methods = None
    if not isinstance(ssh_methods, list) or len(ssh_methods) == 0:
        ssh_methods = [
            {"id": "vscode", "name": "VS Code", "template": "{username}@{ip}:{port}", "helpText": "Open the Remote SSH extension and connect to"},
            {"id": "terminal", "name": "Terminal", "template": "ssh {username}@{ip} -p {port}", "helpText": "Run this command in your terminal"}
        ]

    help_text = ""
    if include_email_details:
        contact_email = get_setting('email.contactEmail')
        if contact_email:
            help_text = f"If you need help, contact: {contact_email}{linesep}{linesep}"

    # Find and extract SSH port
    help_text_ssh = ""
    found_item = None
    for port in ports:
        if port.get("portType") == "SSH":
            found_item = port
            for method in ssh_methods:
                rendered = method["template"].replace("{username}", username).replace("{ip}", ip).replace("{port}", str(port['outsidePort']))
                help_text_ssh += f"{method['name']}{linesep}"
                help_text_ssh += f"{method['helpText']}{linesep}"
                help_text_ssh += f"{rendered}"
                help_text_ssh += linesep + linesep
            help_text_ssh += f"Password for the SSH connection:{linesep}"
            help_text_ssh += f"{password}"
            help_text_ssh += linesep
    if found_item is not None:
        ports.remove(found_item)

    # Find primary non-SSH port if set
    help_text_primary = ""
    if primary_connection_port_id is not None:
        for port in list(ports):
            if port.get("containerPortId") == primary_connection_port_id:
                url = _render_port_url(port.get("portType"), ip, port["outsidePort"])
                help_text_primary += f"Primary service — {port['serviceName']}:{linesep}"
                help_text_primary += f"{url}{linesep}{linesep}"
                ports.remove(port)
                break

    # Render remaining other ports
    help_text_other = ""
    if len(ports) > 0:
        help_text_other += f"{linesep}"
        for port in ports:
            url = _render_port_url(port.get("portType"), ip, port["outsidePort"])
            help_text_other += f"Service {port['serviceName']} (local port {port['localPort']}): {url}{linesep}"
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

    # Add separator before instructions if there are any
    general_text_block = ""
    if general_text:
        general_text_block = f"-----{linesep}{linesep}{general_text}"

    # Build body — primary service first (if non-SSH), then SSH, then other services
    body = f"""
{start_message}
{help_text_primary}{help_text_ssh}
-----
{help_text_other}
Address of the machine: {ip}

{general_text_block}

{no_reply}{help_text}{non_critical_errors}
"""

    return body


def send_container_started_email(user_email, image_name, computer_ip, ports, password,
                                 non_critical_errors, end_date, username="user",
                                 ssh_methods=None, primary_connection_port_id=None):
    """Send an email notification when a container starts successfully.

    Generates connection details text and emails it to the user. Does
    nothing if email sending is disabled in settings.

    Args:
        user_email: Recipient email address.
        image_name: Name of the Docker image that was started.
        computer_ip: IP address of the host machine.
        ports: List of port dictionaries with serviceName, localPort,
            outsidePort, and optionally portType.
        password: SSH password for the container.
        non_critical_errors: Any non-critical error messages to include.
        end_date: Datetime when the reservation ends.
        username: Container username for SSH connection strings.
        ssh_methods: Optional list of SSH method dicts from system settings.
        primary_connection_port_id: Optional primary ContainerPort ID.
    """
    if not get_setting('email.sendEmail'):
        return

    body = generate_connection_text(
        image_name, computer_ip, ports, password,
        True, non_critical_errors, end_date, username,
        ssh_methods=ssh_methods,
        primary_connection_port_id=primary_connection_port_id
    )
    send_email(user_email, "AI Server is ready to use!", body)


def send_container_error_email(user_email, errors):
    """Send an email notification when a container fails to start.

    Notifies the user that their reservation encountered an error and
    includes the error details. Does nothing if email sending is disabled.

    Args:
        user_email: Recipient email address.
        errors: Error message or exception describing what went wrong.
    """
    if not get_setting('email.sendEmail'):
        return

    linesep = os.linesep
    body = f"Your AI server reservation did not start as there was an error. {linesep}{linesep}"
    body += f"The error was: {linesep}{linesep}{errors}{linesep}{linesep}"
    body += "Please do not reply to this email, this email is sent from a noreply email address."
    send_email(user_email, "AI Server did not start", body)


def send_container_paused_email(user_email, image_name, computer_name, reservation_id):
    """Send an email notification when a low-priority container is paused.

    Notifies the user that their container was paused to free resources
    for a higher-priority reservation, and that it will restart
    automatically when resources become available.

    Args:
        user_email: Recipient email address.
        image_name: Name of the Docker image that was paused.
        computer_name: Name of the server where the container ran.
        reservation_id: Database ID of the paused reservation.
    """
    if not get_setting('email.sendEmail'):
        return

    linesep = os.linesep
    body = f"Your low-priority container (reservation #{reservation_id}) has been paused.{linesep}{linesep}"
    body += f"Container image: {image_name}{linesep}"
    body += f"Server: {computer_name}{linesep}{linesep}"
    body += f"The container was paused because resources are needed by a higher-priority reservation.{linesep}"
    body += f"It will restart automatically when resources become available.{linesep}{linesep}"
    body += f"Data on mounted volumes is preserved. No action is needed from you.{linesep}{linesep}"
    body += "Please do not reply to this email, this email is sent from a noreply email address."
    send_email(user_email, "Low-priority container paused", body)


def send_container_resumed_email(user_email, image_name, computer_ip, ports, password,
                                 end_date, username="user",
                                 ssh_methods=None, primary_connection_port_id=None):
    """Send an email notification when a paused low-priority container resumes.

    Notifies the user that their container has been restarted with new
    connection details (ports and password may have changed).

    Args:
        user_email: Recipient email address.
        image_name: Name of the Docker image that was resumed.
        computer_ip: IP address of the host machine.
        ports: List of port dictionaries with serviceName, localPort,
            outsidePort, and optionally portType.
        password: New SSH password for the container.
        end_date: Datetime when the reservation ends.
        username: Container username for SSH connection strings.
        ssh_methods: Optional list of SSH method dicts from system settings.
        primary_connection_port_id: Optional primary ContainerPort ID.
    """
    if not get_setting('email.sendEmail'):
        return

    body = generate_connection_text(
        image_name, computer_ip, ports, password,
        True, "Your low-priority container has been resumed.", end_date, username,
        ssh_methods=ssh_methods,
        primary_connection_port_id=primary_connection_port_id
    )
    send_email(user_email, "Low-priority container resumed", body)


def send_admin_failure_alert(user_email, reservation_id, image_name, server_name, errors):
    """Send container failure alerts to configured admin email addresses.

    Sends a detailed failure notification to all admin alert recipients
    configured in settings, excluding the affected user (who receives
    their own notification separately). Does nothing if container alerts
    are disabled or no alert emails are configured.

    Args:
        user_email: Email of the user whose container failed (excluded
            from admin recipients to avoid duplicate notifications).
        reservation_id: Database ID of the failed reservation.
        image_name: Docker image that failed to start.
        server_name: Name of the server where the failure occurred.
        errors: Error message or exception describing the failure.
    """
    try:
        alerts_enabled = get_setting('notifications.containerAlertsEnabled')
        if not alerts_enabled:
            return

        alert_emails = get_setting('notifications.alertEmails')
        if not alert_emails or len(alert_emails) == 0:
            log.warning("Container failure alerts enabled but no alert emails configured")
            return

        # Create list of recipients, removing user's email to avoid duplicate notification
        recipients = set(alert_emails)
        if user_email in recipients:
            recipients.remove(user_email)

        if not recipients:
            log.info("Container failure alerts: no additional recipients (user already notified)")
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
                log.error(f"Failed to send alert to {admin_email}: {email_error}")

        if successful_sends > 0:
            log.info(f"Container failure alerts sent to {successful_sends}/{len(recipients)} admin(s)")
        else:
            log.error(f"Failed to send container failure alerts to any of {len(recipients)} admin(s)")

    except Exception as e:
        log.error(f"Failed to send container failure alerts: {e}")
