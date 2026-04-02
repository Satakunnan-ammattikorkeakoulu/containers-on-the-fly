"""Pure Docker container operations via python_on_whales.

This module handles the actual Docker API calls -- start, stop, restart.
No database access, no email, no filesystem setup (that's in mounts.py).
"""

from python_on_whales import docker
from helpers.utils import create_password
from helpers.settings_handler import settings_handler
from python_on_whales.exceptions import NoSuchContainer
import traceback
import shlex
from helpers.logger import log
from docker.mounts import build_volume_list, run_user_config_script
from docker.image_builder import DEFAULT_PASSWORD_COMMAND, DEFAULT_SSH_KEY_DEPLOY_COMMANDS
from docker.ssh_host_keys import inject_host_keys


def start_container(pars):
    """Start a Docker container with the given parameters.

    Builds the full Docker run configuration from the provided parameter
    dictionary, starts the container, sets the user password, optionally
    deploys an SSH public key, and runs any user config scripts found in
    mounted volumes. If the container cannot be started, attempts to clean
    up by stopping any partially-created container.

    Args:
        pars: Dictionary of container parameters. Required keys:
            name (str): Unique container name in Docker.
            image (str): Docker image name (must exist in the registry).
            username (str): Username inside the container.
            cpus (int): Number of CPUs to dedicate.
            memory (str): RAM allocation, e.g. "1g" or "8g".
            ports (list): Port mappings as [(host_port, container_port), ...].
            dbUserId (str): Database user ID of the reservation owner.
            reservation (dict): Reservation info with computerId and user data.
            roleMounts (list): Mount configs with hostPath, containerPath,
                readOnly, and computerId. Paths support {email} and {userid}
                template variables.
            Optional keys:
            gpus (str): GPU device string, e.g. "device=0,2,4", or None.
            image_version (str): Image tag, defaults to "latest".
            password (str): Container user password, defaults to random.
            interactive (bool): Keep stdin open, defaults to True.
            remove (bool): Remove container on stop, defaults to True.
            shm_size_percent (int): Shared memory as percentage of RAM (10-90).
            ram_disk_percent (int): RAM disk as percentage of RAM, 0 to disable.
            sshPublicKey (str): SSH public key to deploy into the container.

    Returns:
        tuple: A 6-element tuple of (started, container_name, password,
            error_message, non_critical_errors, container_id) where
            started is a bool indicating success, container_name and
            password are strings, error_message is a string or Exception
            (empty on success), non_critical_errors is a string or None,
            and container_id is the Docker container ID or None on failure.
    """
    try:
        # Verify parameters first
        if "name" not in pars: raise Exception("Missing parameter: name")
        if "image" not in pars: raise Exception("Missing parameter: image")
        if "username" not in pars: raise Exception("Missing parameter: username")
        if "cpus" not in pars: raise Exception("Missing parameter: cpus")
        if "memory" not in pars: raise Exception("Missing parameter: memory")
        if "ports" not in pars: raise Exception("Missing parameter: ports")
        if "dbUserId" not in pars: raise Exception("Missing parameter: dbUserId")
        if "reservation" not in pars: raise Exception("Missing parameter: reservation")
        if "roleMounts" not in pars: raise Exception("Missing parameter: roleMounts")

        if "gpus" not in pars: pars["gpus"] = None
        if pars["gpus"] == 0: pars["gpus"] = None
        if pars["gpus"] == "": pars["gpus"] = None
        if "image_version" not in pars: pars["image_version"] = "latest"
        if "interactive" not in pars: pars["interactive"] = True
        if "remove" not in pars: pars["remove"] = True

        # Create random password for the user if it was not passed
        if "password" not in pars: pars["password"] = create_password()

        # Calculate SHM size based on percentage
        mem_value = int(float((pars["memory"][:-1])))
        unit = pars["memory"][-1]

        # Convert memory to MB for more precise calculation
        if unit.lower() == 'g':
            mem_mb = mem_value * 1024
        elif unit.lower() == 'm':
            mem_mb = mem_value
        else:
            mem_mb = mem_value * 1024  # Default to GB

        # Use provided percentage or default to 50%
        shm_percent = pars.get("shm_size_percent", 50)
        # Enforce minimum 10% and maximum 90%
        shm_percent = max(10, min(90, shm_percent))
        shm_mb = int(mem_mb * shm_percent / 100)
        pars["shm_size"] = f"{shm_mb}m"

        container_name = None
        container_name = pars['name']

        gpus = None
        # Check if gpus parameter exists and is not empty
        if pars.get("gpus") and pars["gpus"] != "":
            # Check if GPU debug mode is enabled
            try:
                debug_skip_gpu = settings_handler.get_setting("docker.debugSkipGpuDedication")
            except Exception as e:
                debug_skip_gpu = False

            if debug_skip_gpu:
                gpus = None
            else:
                gpus = f'"{pars["gpus"]}"'

        # Get user info for variable substitution
        user_email = pars["reservation"]["user"]["email"]
        user_id = pars["dbUserId"]
        computer_id = pars["reservation"]["computerId"]

        # Build volumes from role mounts (creates host directories and sets permissions)
        volumes = build_volume_list(pars["roleMounts"], computer_id, user_email, user_id)

        full_image_name = f"{settings_handler.get_setting('docker.registryAddress')}/{pars['image']}:{pars['image_version']}"

        # RAM disk configuration
        ram_mounts = []
        ram_disk_percent = pars.get("ram_disk_percent", 0)

        if ram_disk_percent > 0:
            username = pars.get("username", "user")
            mount_path = f"/home/{username}/ram_disk"
            # Calculate RAM disk size in bytes based on percentage
            # Use the same memory value we calculated for SHM
            ram_disk_mb = int(mem_mb * ram_disk_percent / 100)
            ram_disk_bytes = ram_disk_mb * 1024 * 1024  # Convert MB to bytes
            tmpfs_config = f"type=tmpfs,destination={mount_path},tmpfs-size={ram_disk_bytes}"
            ram_mounts.append(tmpfs_config)

        # Start the container
        # Build the base parameters
        run_params = {
            'volumes': volumes,
            'name': container_name,
            'memory': pars['memory'],
            'shm_size': pars['shm_size'],
            'cpus': pars['cpus'],
            'publish': pars['ports'],
            'detach': True,
            'interactive': pars['interactive'],
            # Do not automatically remove the container as it will stop.
            # Removing a container will be handled manually in the stop_container() function.
            # If it would be removed, restarting or crashing a container would fully destroy it immediately.
            'remove': False,
            # Looks every time if there is newer image in local registery
            'pull': 'always',
        }

        # Only add gpus parameter if we actually have GPUs to dedicate
        if gpus is not None:
            run_params['gpus'] = gpus

        # Add tmpfs mounts if RAM disk is configured
        if ram_mounts:
            # mounts expects a list of lists where each inner list contains mount config parts
            run_params['mounts'] = [[mount] for mount in ram_mounts]

        cont = docker.run(full_image_name, **run_params)

        # Set password using customizable command template
        password_cmd_template = pars.get("passwordCommand") or DEFAULT_PASSWORD_COMMAND
        password_cmd = password_cmd_template.replace("{username}", pars.get("username", "user")).replace("{password}", pars["password"])
        docker.execute(container=container_name, command=["/bin/bash", "-c", password_cmd], user="root")

        # Inject persistent SSH host keys to prevent known_hosts conflicts on port reuse
        host_keys_path = settings_handler.get_setting("docker.sshHostKeysPath")
        inject_host_keys(container_name, host_keys_path)

    except Exception as e:
        log.error(f"Failed to start container {container_name or 'unknown'}: {e}\n{traceback.format_exc()}")
        if container_name:  # Only try to stop if we have a name
            log.info(f"Cleaning up partially-created container {container_name}")
            stop_container(container_name)
        return False, "", "", e, None, None

    # Deploy SSH public key if provided (non-critical — don't fail the container)
    if pars.get("sshPublicKey"):
        try:
            ssh_key = pars["sshPublicKey"]
            ssh_cmd_template = pars.get("sshKeyDeployCommands") or DEFAULT_SSH_KEY_DEPLOY_COMMANDS
            ssh_cmd = ssh_cmd_template.replace("{username}", pars.get("username", "user")).replace("{ssh_key}", ssh_key)
            docker.execute(
                container=container_name,
                command=["/bin/bash", "-c", ssh_cmd],
                user="root"
            )
        except Exception as e:
            log.warning(f"Non-critical error deploying SSH public key to container {container_name}: {e}")

    non_critical_errors = run_user_config_script(pars["roleMounts"], computer_id, user_email, user_id, container_name)

    # Execute user's start script if configured (non-critical)
    start_script = pars.get("startScriptPath")
    if start_script:
        try:
            log.info(f"Running start script '{start_script}' in container {container_name}")
            docker.execute(
                container=container_name,
                command=["/bin/bash", "-c", f"timeout 40 {shlex.quote(start_script)}"],
                user=pars.get("username", "user")
            )
        except Exception as e:
            log.warning(f"Non-critical error running start script in container {container_name}: {e}")

    return True, container_name, pars["password"], "", non_critical_errors, cont.id

def stop_container(container_name):
    """Stop and remove a Docker container by name.

    Attempts to stop the container first, then remove it. Either step
    may fail independently if the container does not exist.

    Args:
        container_name: Name of the Docker container to stop.

    Returns:
        bool: True if both stop and remove succeeded, False if either
            failed due to the container not existing.
    """
    no_errors = True
    try:
        docker.stop(container_name, time=60)
    except NoSuchContainer as e:
        log.error(f"Could not stop container (not found): {container_name}")
        no_errors = False

    try:
        docker.remove(container_name)
    except NoSuchContainer as e:
        log.error(f"Could not remove container (not found): {container_name}")
        no_errors = False

    return no_errors

def run_stop_script(container_name, stop_script_path, container_username="user"):
    """Execute a stop script inside a running container before stopping it.

    Non-critical — logs a warning on failure but does not raise. The script
    runs with a 40-second timeout to prevent blocking container shutdown.

    Args:
        container_name: Name of the running Docker container.
        stop_script_path: Absolute path to the stop script inside the container.
        container_username: Username to run the script as (default "user").
    """
    if not stop_script_path:
        return
    try:
        log.info(f"Running stop script '{stop_script_path}' in container {container_name}")
        docker.execute(
            container=container_name,
            command=["/bin/bash", "-c", f"timeout 40 {shlex.quote(stop_script_path)}"],
            user=container_username
        )
    except Exception as e:
        log.warning(f"Non-critical error running stop script in container {container_name}: {e}")

def restart_container(container_name):
    """Restart a Docker container by name.

    Args:
        container_name: Name of the Docker container to restart.

    Raises:
        Exception: If the container cannot be restarted (logged via traceback).
    """
    try:
        docker.restart(container_name, time=60)
    except Exception as e:
        log.error(f"Could not restart container {container_name}: {e}\n{traceback.format_exc()}")
        raise
