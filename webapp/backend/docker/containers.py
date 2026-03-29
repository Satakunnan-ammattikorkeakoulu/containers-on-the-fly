"""
Pure Docker container operations via python_on_whales.

This module handles the actual Docker API calls — start, stop, restart.
No database access, no email, no filesystem setup (that's in mounts.py).
"""

from python_on_whales import docker
from helpers.auth import create_password
from settings_handler import settings_handler
from python_on_whales.exceptions import NoSuchContainer
import traceback
from docker.mounts import build_volume_list, run_user_config_script


def start_container(pars):
    """
    Starts a Docker container with the given parameters.

    If the container cannot be started or there are any problems running this function,
    will try to stop the created container (if able to).

    Required parameters:
        name (string): Name of the container. Must be unique in Docker.
        image (string): Name of the image. Note: The image must be created in Docker before starting the container.
        username (string): Username of the container user. Note: The user must be created in the Docker image before starting the container.
        cpus (int): The amount of cpus dedicated for the container. Note: The amount of cpus must be available in the host machine.
        memory (string): The amount of RAM memory dedicated for the container. For example: "1g" or "8g"
        ports (list): The ports to be used. In format: [(local_port, container_port), (local_port2, container_port2)]. For example: [(2213, 22)] for SSH.
        dbUserId (string): User ID from the database who started the container
        reservation: Reservation dictionary containing computerId and user data (with email)
        roleMounts (list): List of mount dictionaries with hostPath, containerPath, readOnly, computerId
                          hostPath and containerPath support template variables:
                          - {email}: User's email with special characters removed (e.g., "test_foo_com")
                          - {userid}: User's database ID (e.g., "123")
    Optional parameters:
        gpus (string): The amount of gpus dedicated for the container in format "device=0,2,4" where "0", "2" and "4" are device nvidia / cuda IDs. Pass None if no gpus are needed.
        image_version (string) (default: "latest"): The image version to use.
        password (string) (default: random password): Password for the user of the container
        interactive (int) (default: True): Leave stdin open during the duration of the process to allow communication with the parent process. Currently only works with tty=True for interactive use on the terminal.
        remove (int) (default: True): If this is True, removes the container after it is stopped.
        shm_size (int): The size of the shared memory. For example: 1g
    Returns:
        namedtuple:
            (boolean) started: True if the container was started successfully,
            (string) container_name: The name of the container (if any),
            (string) password: The password of the container user (if any),
            (string) error_message: Error message(s) (if any),
            (string) non_critical_error: Non-critical error messages (if any)
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
            mount_path = "/home/user/ram_disk"
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
        docker.execute(container=container_name, command=["/bin/bash","-c", f"/bin/echo 'user:{pars['password']}' | /usr/sbin/chpasswd"], user="root")
    except Exception as e:
        print(f"Something went wrong starting container {container_name or 'unknown'}. Trying to stop the container. Error:")
        print(e)
        print("Stack trace:")
        print(traceback.format_exc())
        if container_name:  # Only try to stop if we have a name
            stop_container(container_name)
        return False, "", "", e, None

    non_critical_errors = run_user_config_script(pars["roleMounts"], computer_id, user_email, user_id, container_name)

    return True, container_name, pars["password"], "", non_critical_errors

def stop_container(container_name):
    '''
    Stops the container with the given name.
    Returns:
        (boolean) True if the container was stopped successfully, otherwise false (as it did not exist)
    '''
    no_errors = True
    try:
        docker.stop(container_name)
        print(f"Stopped container {container_name}")
    except NoSuchContainer as e:
        print(f"Error stopping container: {container_name}")
        no_errors = False

    try:
        docker.remove(container_name)
        print(f"Removed container {container_name}")
    except NoSuchContainer as e:
        print(f"Error removing container: {container_name}")
        no_errors = False

    return no_errors

def restart_container(container_name):
    '''
    Restarts the container with the given name.
    '''
    print("Starting to restart a container...")
    try:
        print(f"Restarting container: {container_name}")
        docker.restart(container_name)
    except Exception as e:
        print(f"Could not restart container: {container_name}")
        traceback.print_exc()
