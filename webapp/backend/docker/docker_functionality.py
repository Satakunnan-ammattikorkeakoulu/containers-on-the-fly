#! /usr/bin/python3
from python_on_whales import docker
from helpers.auth import create_password
from datetime import datetime
from settings import settings
from python_on_whales.exceptions import NoSuchContainer
import os
import shutil

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
        localMountFolderPath (string): The folder to mount in the local filesystem. For example: /home/user/docker_mounts
    Optional parameters:
        gpus (string): The amount of gpus dedicated for the container in format "device=0,2,4" where "0", "2" and "4" are device nvidia / cuda IDs. Pass None if no gpus are needed.
        image_version (string) (default: "latest"): The image version to use.
        password (string) (default: random password): Password for the user of the container
        interactive (int) (default: True): Leave stdin open during the duration of the process to allow communication with the parent process. Currently only works with tty=True for interactive use on the terminal.
        remove (int) (default: True): If this is True, removes the container after it is stopped.
        shm_size (int): The size of the shared memory. For example: 1g
    Returns:
        tuple:
            (boolean) True if the container was started successfully,
            (string) The name of the container,
            (string) The password of the container user
    """

    try:
        # Verify all that all the required parameters are present.
        if "name" not in pars: raise Exception("Missing parameter: name")
        if "image" not in pars: raise Exception("Missing parameter: image")
        if "username" not in pars: raise Exception("Missing parameter: username")
        if "cpus" not in pars: raise Exception("Missing parameter: cpus")
        if "memory" not in pars: raise Exception("Missing parameter: memory")
        if "ports" not in pars: raise Exception("Missing parameter: ports")
        if "localMountFolderPath" not in pars: raise Exception("Missing parameter: localMountFolderPath")

        if "gpus" not in pars: pars["gpus"] = None
        if pars["gpus"] == 0: pars["gpus"] = None
        if pars["gpus"] == "": pars["gpus"] = None
        if "image_version" not in pars: pars["image_version"] = "latest"
        if "interactive" not in pars: pars["interactive"] = True
        if "remove" not in pars: pars["remove"] = True
        if "shm_size" not in pars: pars["shm_size"] = "1g"
        if "password" not in pars: pars["password"] = create_password()

        container_name = pars['name']

        #print(pars["gpus"])

        gpus = None
        if pars["gpus"] != None:
            gpus = f'"{pars["gpus"]}"'

        # Create directory for mounting if it does not exist
        if not os.path.isdir(pars["localMountFolderPath"]):
            os.makedirs(pars["localMountFolderPath"], exist_ok=True)
        # Set correct owner and group for the mount folder
        shutil.chown(pars["localMountFolderPath"], user=settings.docker['mountUser'], group=settings.docker['mountGroup'])
        # Set correct file permissions for the mount folder
        os.chmod(pars["localMountFolderPath"], 0o777)

        # Add volumes and mounts
        volumes = [(pars['localMountFolderPath'], f"/home/{pars['username']}/persistent")]
        if "extraMounts" in settings.docker and len(settings.docker["extraMounts"]) > 0:
            for mount in settings.docker["extraMounts"]:
                if mount["readOnly"]:
                    volumes.append((mount["mountLocation"], f"/home/{pars['username']}/{mount['containerFolderName']}", "ro"))
                else:
                    volumes.append((mount["mountLocation"], f"/home/{pars['username']}/{mount['containerFolderName']}"))

        #testing ram disk
        mount_path = "/home/user/ram_disk"
        ram_disk_size = "1073741824" # 1G in bytes, if I understanded correctly, this need to be in bytes, not 1GB etc
        tmpfs_config = f"type=tmpfs,destination={mount_path},tmpfs-size={ram_disk_size}" 
        ram_mounts = [tmpfs_config]

        cont = docker.run(
            f"{pars['image']}:{pars['image_version']}",
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
            remove = False

            #user=user
        )
        #print("The running container: ", cont)
        #print("=== Stop printing running container")
        docker.execute(container=container_name, command=["/bin/bash","-c", f"/bin/echo 'user:{pars['password']}' | /usr/sbin/chpasswd"], user="root")
    except Exception as e:
        print(f"Something went wrong starting container {container_name}. Trying to stop the container. Error:")
        print(e)
        stop_container(container_name)
        return False, e, None

    try:
        non_critical_errors = ""
        #This will check if the user has config.bash in config folder. If yes, then this config.bash will be executed, before container is given to user
        if os.path.exists(f'{pars["localMountFolderPath"]}/config/config.bash'):
            docker.execute(container=container_name, command=["/bin/bash","-c", "/home/user/persistent/config/config.bash"], user="root")
    except Exception as e:
        print(f"Something went wrong when running users config.bash in  {container_name}. This is not critical, most likely user error")
        print(e)
        non_critical_errors = "Something went wrong when running users config.bash, from /home/persistent/config, check your script."

    return True, container_name, pars["password"], non_critical_errors

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
        helpText = f"If you need help, contact: {settings.email['helpEmailAddress']}"

    helpTextSSH = ""
    foundItem = None
    for port in ports:
        if (port["serviceName"] == "SSH"):
            foundItem = port
            helpTextSSH = f"Connecting from Unix terminal: ssh user@{ip} -p {port['outsidePort']}"
            helpTextSSH += linesep
            helpTextSSH += f"    Password: {password}"
            helpTextSSH += linesep + linesep
    if foundItem is not None:
        ports.remove(foundItem)

    helpTextOther = ""
    for port in ports:
        helpTextOther += f"Service {port['serviceName']} is also available through: {ip}:{port['outsidePort']} {linesep}{linesep}"

    generalText = ""
    if "generalText" in settings.docker:
        generalText = settings.docker["generalText"]

    webAddress = ""
    if "clientUrl" in settings.app and includeEmailDetails:
        webAddress = f"You can access your reservations through: "
        webAddress += settings.app['clientUrl']
    
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
        startMessage = f"Container with image {image} is ready to use.{linesep}"

    noReply = ""
    if includeEmailDetails:
        noReply = "This is a noreply email account. Please do not reply to this email."

    # Body text
    body = f"""
    {startMessage}
    {generalText}{linesep}
    IP of the machine is {ip}.{linesep}
    {helpTextSSH}
    {helpTextOther}
    NOTE! only files and folders from ~/persistent folder are
    saved after container stops, so save trained networks, 
    checkpoint files, logs, your datasets etc to that folder.

    Every started container has datasets folder, this folder is READ only, 
    you cannot modify files inside that folder. If you need to modify dataset, 
    then copy it to some other directory.

    {noReply}

    {webAddress}
    
    {helpText}

    {non_critical_errors}
    """

    return body
