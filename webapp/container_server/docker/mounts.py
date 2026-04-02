"""Docker volume mount operations for container reservations.

Handles building Docker volume lists from role-based mount configurations,
creating host directories with correct permissions, substituting template
variables in mount paths, and executing user config scripts inside containers.
"""

import os
import shutil
import getpass
import subprocess
import re


def remove_special_characters(string):
    """Remove all non-alphanumeric characters (except whitespace) from a string."""
    return re.sub(r'[^a-zA-Z0-9\s]', '', string)
from logger import log


def substitute_mount_variables(path, user_email, user_id):
    """Substitute template variables in mount paths.

    Replaces {email} and {userid} placeholders in a path string with
    sanitized values derived from the user's email and database ID.

    Args:
        path: Path string that may contain {email} and/or {userid} variables.
        user_email: User's email address (special characters will be removed).
        user_id: User's database ID.

    Returns:
        str: The path with all template variables replaced, or the original
            path if it was None/empty.
    """
    if not path:
        return path

    # Sanitize email for filesystem use
    email_sanitized = remove_special_characters(user_email)

    substitutions = {
        '{email}': email_sanitized,
        '{userid}': str(user_id)
    }

    result = path
    for variable, value in substitutions.items():
        result = result.replace(variable, value)

    return result


def prepare_mount_directory(host_path):
    """Create a mount directory on the host with correct permissions and ACLs.

    Creates the directory if it does not exist, sets ownership to the current
    user with the "docker" group, applies 775 permissions, resets any existing
    ACLs, and grants the "containerfly" group read-write-execute access.

    Args:
        host_path: Absolute path on the host filesystem where the directory
            should be created. If None or empty, does nothing.
    """
    # Set mounting user and group
    mount_user = os.getenv('USER') or os.getenv('USERNAME') or getpass.getuser()
    mount_group = "docker"

    if not host_path:
        return

    # Create directory for mounting if it does not exist
    if not os.path.isdir(host_path):
        os.makedirs(host_path, exist_ok=True)
    # Set correct owner and group for the mount folder (keep docker group for mounting)
    shutil.chown(host_path, user=mount_user, group=mount_group)
    # Set correct file permissions for the mount folder
    os.chmod(host_path, 0o775)

    # Remove any existing ACLs to ensure default Unix behavior
    try:
        subprocess.run(['setfacl', '-b', host_path], check=True, capture_output=True)
    except Exception as e:
        log.warning(f"Resetting ACL permissions for mount folder {host_path} failed: {e}")

    # Give containerfly group write access to the directory
    try:
        subprocess.run(['setfacl', '-m', 'g:containerfly:rwx', host_path], check=True)
    except Exception as e:
        log.warning(f"Failed to set containerfly group permissions on {host_path}: {e}")


def build_volume_list(role_mounts, computer_id, user_email, user_id):
    """Build Docker volume list from role mounts, creating host directories as needed.

    Iterates over the role mount configurations, filters by computer ID,
    substitutes template variables in paths, creates host directories with
    appropriate permissions, and produces volume tuples suitable for
    python_on_whales docker.run().

    Args:
        role_mounts: List of mount dictionaries, each containing hostPath,
            containerPath, readOnly, and computerId.
        computer_id: Database ID of the computer to filter mounts for.
        user_email: User's email address for template variable substitution.
        user_id: User's database ID for template variable substitution.

    Returns:
        list: Volume tuples for docker.run(). Each tuple is either
            (host_path, container_path) for read-write mounts or
            (host_path, container_path, "ro") for read-only mounts.
    """
    volumes = []

    for mount in role_mounts:
        # Only include mounts for this specific computer
        if mount["computerId"] == computer_id:
            # Apply variable substitution to paths
            host_path = substitute_mount_variables(mount["hostPath"], user_email, user_id)
            container_path = substitute_mount_variables(mount["containerPath"], user_email, user_id)
            read_only = mount["readOnly"]

            if host_path:
                prepare_mount_directory(host_path)

            # Add the volume mount
            if read_only:
                volumes.append((host_path, container_path, "ro"))
            else:
                volumes.append((host_path, container_path))

    return volumes


def run_user_config_script(role_mounts, computer_id, user_email, user_id, container_name):
    """Look for config.bash in mounted persistent volumes and execute it inside the container.

    Searches through the role mounts for a read-write mount that contains
    a ``config/config.bash`` file on the host. If found, executes it inside
    the container as root with a 60-second timeout. Only the first matching
    config script is executed.

    Args:
        role_mounts: List of mount dictionaries with hostPath, containerPath,
            readOnly, and computerId.
        computer_id: Database ID of the computer to filter mounts for.
        user_email: User's email address for template variable substitution.
        user_id: User's database ID for template variable substitution.
        container_name: Name of the running Docker container to execute
            the script in.

    Returns:
        str: Non-critical error message if config.bash execution failed,
            or an empty string on success or if no config.bash was found.
    """
    from python_on_whales import docker

    try:
        for mount in role_mounts:
            if mount["computerId"] == computer_id and not mount["readOnly"]:
                container_path = substitute_mount_variables(mount["containerPath"], user_email, user_id)
                host_path = substitute_mount_variables(mount["hostPath"], user_email, user_id)
                config_path = f'{host_path}/config/config.bash'
                if os.path.exists(config_path):
                    docker.execute(container=container_name, command=["/bin/bash", "-c", f"timeout 60 {container_path}/config/config.bash"], user="root")
                    break  # Only run the first config.bash found
    except Exception as e:
        log.warning(f"Error running user config.bash in container {container_name} (non-critical): {e}")
        return "Something went wrong when running users config.bash, from a persistent mount path /config, check your script."

    return ""
