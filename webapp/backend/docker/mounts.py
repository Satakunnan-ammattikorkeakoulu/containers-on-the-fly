import os
import shutil
import getpass
import subprocess
from helpers.utils import removeSpecialCharacters


def substitute_mount_variables(path, user_email, user_id):
    """Substitute template variables in mount paths"""
    if not path:
        return path

    # Sanitize email for filesystem use
    email_sanitized = removeSpecialCharacters(user_email)

    substitutions = {
        '{email}': email_sanitized,
        '{userid}': str(user_id)
    }

    result = path
    for variable, value in substitutions.items():
        result = result.replace(variable, value)

    return result


def prepare_mount_directory(host_path):
    """Create mount directory on host with correct permissions and ACLs"""
    # Set mounting user and group
    mountUser = os.getenv('USER') or os.getenv('USERNAME') or getpass.getuser()
    mountGroup = "docker"

    if not host_path:
        return

    # Create directory for mounting if it does not exist
    if not os.path.isdir(host_path):
        os.makedirs(host_path, exist_ok=True)
    # Set correct owner and group for the mount folder (keep docker group for mounting)
    shutil.chown(host_path, user=mountUser, group=mountGroup)
    # Set correct file permissions for the mount folder
    os.chmod(host_path, 0o775)

    # Remove any existing ACLs to ensure default Unix behavior
    try:
        subprocess.run(['setfacl', '-b', host_path], check=True, capture_output=True)
    except Exception as e:
        print("Resetting ACL permissions for a mount folder failed:")
        print(e)

    # Give containerfly group write access to the directory
    try:
        subprocess.run(['setfacl', '-m', 'g:containerfly:rwx', host_path], check=True)
    except Exception as e:
        print(f"Failed to set containerfly group permissions on {host_path}:")
        print(e)


def build_volume_list(role_mounts, computer_id, user_email, user_id):
    """
    Build Docker volume list from role mounts, creating host directories as needed.

    Returns:
        list: Volume tuples for python_on_whales docker.run()
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
    """
    Look for config.bash in mounted persistent volumes and execute it in the container.

    Returns:
        str: Non-critical error message if config.bash execution failed, empty string otherwise
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
        print(f"Something went wrong when running users config.bash in  {container_name}. This is not critical, most likely user error")
        print(e)
        return "Something went wrong when running users config.bash, from a persistent mount path /config, check your script."

    return ""
