#! /usr/bin/python3
from python_on_whales import docker
from helpers.auth import create_password
from helpers.Utils import removeSpecialCharacters
from datetime import datetime
from settings import settings
from python_on_whales.exceptions import NoSuchContainer
import os
import shutil
import traceback
import getpass
from database import Session, Role
import subprocess

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

        # can this lead to oum? we need to test so if weird shit is happening, look in to this:
        # we add that as half of the ram size, if this seems to work, remove this shm_size from docker.settings.
        mem_value = int(float((pars["memory"][:-1])))
        unit = pars["memory"][-1]
        shm_value = f"{mem_value // 2}{unit}"
        pars["shm_size"] = shm_value

        container_name = None
        container_name = pars['name']

        #print(pars["gpus"])
        gpus = None
        if pars["gpus"] != None:
            gpus = f'"{pars["gpus"]}"'

        # Add volumes and mounts
        volumes = []
        
        # Set mounting user and group
        # For the user we will use the current user running this script
        # "docker" is the group
        mountUser = os.getenv('USER') or os.getenv('USERNAME') or getpass.getuser()
        mountGroup = "docker"

        # Get user info for variable substitution
        user_email = pars["reservation"]["user"]["email"]
        user_id = pars["dbUserId"]

        # Unified mount processing with variable substitution
        computer_id = pars["reservation"]["computerId"]
        for mount in pars["roleMounts"]:
            # Only include mounts for this specific computer
            if mount["computerId"] == computer_id:
                # Apply variable substitution to paths
                host_path = substitute_mount_variables(mount["hostPath"], user_email, user_id)
                container_path = substitute_mount_variables(mount["containerPath"], user_email, user_id)
                read_only = mount["readOnly"]
                
                if host_path:
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
                
                # Add the volume mount
                if read_only:
                    volumes.append((host_path, container_path, "ro"))
                else:
                    volumes.append((host_path, container_path))

        full_image_name = f"{settings.docker['registryAddress']}/{pars['image']}:{pars['image_version']}"

        # RAM disk
        mount_path = "/home/user/ram_disk"
        ram_disk_size = "1073741824" # 1G in bytes, if I understanded correctly, this need to be in bytes, not 1GB etc
        tmpfs_config = f"type=tmpfs,destination={mount_path},tmpfs-size={ram_disk_size}" 
        ram_mounts = [tmpfs_config]
        
        # Start the container
        cont = docker.run(
            full_image_name,
            volumes = volumes,
            mounts = [ram_mounts], # added this for ramdisk
            gpus=gpus,
            name = container_name,
            memory = pars['memory'],
            kernel_memory = pars['memory'],
            shm_size = pars['shm_size'],
            cpus = pars['cpus'],
            publish = pars['ports'],
            detach = True,
            interactive = pars['interactive'],
            
            # Do not automatically remove the container as it will stop.
            # Removing a container will be handled manually in the stop_container() function.
            # If it would be removed, restarting or crashing a container would fully destroy it immediately.
            remove = False,
            # Looks every time if there is newer image in local registery
            pull='always',

            #user="1002:130"
        )
        #print("The running container: ", cont)
        #print("=== Stop printing running container")
        docker.execute(container=container_name, command=["/bin/bash","-c", f"/bin/echo 'user:{pars['password']}' | /usr/sbin/chpasswd"], user="root")
    except Exception as e:
        print(f"Something went wrong starting container {container_name or 'unknown'}. Trying to stop the container. Error:")
        print(e)
        print("Stack trace:")
        print(traceback.format_exc())
        if container_name:  # Only try to stop if we have a name
            stop_container(container_name)
        return False, "", "", e, None

    try:
        non_critical_errors = ""
        #This will check if the user has config.bash in config folder. If yes, then this config.bash will be executed, before container is given to user
        # Note: Since we removed localMountFolderPath, config.bash should be placed in role-mounted paths with {email} variable
        # For example, if a role mount maps /data/users/{email} to /home/user/persistent, 
        # then config.bash should be at /data/users/{email_sanitized}/config/config.bash
        
        # Look for config.bash in any mounted persistent volume
        for mount in pars["roleMounts"]:
            if mount["computerId"] == computer_id and not mount["readOnly"]:
                container_path = substitute_mount_variables(mount["containerPath"], user_email, user_id)
                host_path = substitute_mount_variables(mount["hostPath"], user_email, user_id)
                config_path = f'{host_path}/config/config.bash'
                if os.path.exists(config_path):
                    docker.execute(container=container_name, command=["/bin/bash","-c", f"timeout 60 {container_path}/config/config.bash"], user="root")
                    break  # Only run the first config.bash found
    except Exception as e:
        print(f"Something went wrong when running users config.bash in  {container_name}. This is not critical, most likely user error")
        print(e)
        non_critical_errors = "Something went wrong when running users config.bash, from a persistent mount path /config, check your script."

    return True, container_name, pars["password"], "", non_critical_errors

def stop_container(container_name):
    '''
    Stops the container with the given name.
    Returns:
        (boolean) True if the container was stopped successfully, otherwise false (as it did not exist)
    '''
    noErrors = True
    try:
        docker.stop(container_name)
        print(f"Stopped container {container_name}")
    except NoSuchContainer as e:
        print(f"Error stopping container: {container_name}")
        noErrors = False
    
    try:
        docker.remove(container_name)
        print(f"Removed container {container_name}")
    except NoSuchContainer as e:
        print(f"Error removing container: {container_name}")
        noErrors = False
    
    return noErrors

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
        pass

def get_email_container_started(image, ip, ports, password, includeEmailDetails, non_critical_errors, endDate = None):
    '''
    Gets the email body to send when a container is started.
    Required Parameters:
        email (string): The email address to send the email to.
        image (string): The name of the image used to start the container.
        ip (string): The ip of the machine where the container is running.
        ports (list): The ports used by the container. Example format: [ { serviceName: "ssh", localPort: 22, outsidePort: 2283 } ]
        password (string): The password of the container user.
        endDate (datetime): The date when the container will be stopped.
    '''

    import os
    linesep = os.linesep

    helpText = ""
    if "helpEmailAddress" in settings.email and includeEmailDetails:
        helpText = f"If you need help, contact: {settings.email['helpEmailAddress']}{linesep}{linesep}"

    helpTextSSH = ""
    foundItem = None
    for port in ports:
        if (port["serviceName"] == "SSH"):
            foundItem = port
            helpTextSSH += f"Connecting with Visual Studio Code (SSH):{linesep}"
            helpTextSSH += f"user@{ip}:{port['outsidePort']}"
            helpTextSSH += linesep + linesep
            helpTextSSH += f"Connecting from the terminal (SSH):{linesep}"
            helpTextSSH += f"ssh user@{ip} -p {port['outsidePort']}"
            helpTextSSH += linesep + linesep
            helpTextSSH += f"Password for the SSH connection:" + linesep
            helpTextSSH += f"{password}"
            helpTextSSH += linesep
    if foundItem is not None:
        ports.remove(foundItem)

    helpTextOther = ""
    if len(ports) > 0:
        helpTextOther += f"{linesep}"
        for port in ports:
            helpTextOther += f"Service {port['serviceName']} is available through: {ip}:{port['outsidePort']} {linesep}"
        helpTextOther += f"{linesep}-----{linesep}"


    generalText = ""
    try:
        from helpers.tables.SystemSetting import getSetting
        generalText = getSetting('instructions.email', '')
    except Exception:
        pass

    webAddress = ""
    if "clientUrl" in settings.app and includeEmailDetails:
        webAddress = f"You can access your reservations through: {settings.app['clientUrl']}{linesep}{linesep}"
    
    endDateText = ""
    # TODO: Get endDate in user timezone and after that add in the email
    if endDate is not None:
        # convert endDate from UTC to Europe_Helsinki timezone
        from dateutil import tz
        endDate.replace(tzinfo=None)
        endDate = endDate.astimezone(tz.gettz('Europe_Helsinki'))
        endDateText = f"Your reservation will end at (Europe_Helsinki): {endDate.strftime('%Y-%m-%d %H:%M:%S')}"

    startMessage = ""
    if includeEmailDetails:
        startMessage = f"Container with image {image} is ready to use.{linesep}{linesep}-----{linesep}"

    noReply = ""
    if includeEmailDetails:
        noReply = f"This is a noreply email account. Please do not reply to this email.{linesep}{linesep}"

    # Body text
    body = f"""
{startMessage}
{helpTextSSH}
-----
{helpTextOther}
IP address of the machine: {ip}

{generalText}

Every server contains the same two folders in home folder: persistent and datasets.

persistent: Files and folders in the persistent folder are saved after container stops, so save trained networks, your code, checkpoint files, logs, your datasets etc. to that folder.

datasets: This folder is read-only. This folder contains existing datasets and scripts which you can utilize.

{noReply}{webAddress}{helpText}{non_critical_errors}
"""

    return body