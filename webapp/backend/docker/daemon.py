"""Docker utility daemon -- manages container lifecycle based on reservation state.

Polls the database every 10 seconds to start, stop, restart, and clean up
Docker containers for reservations. Runs as a long-lived process managed by
pm2, and coordinates between the database reservation state and the actual
Docker containers running on the host.
"""

from time import sleep
from datetime import timezone, datetime, timedelta
import sys
from os import linesep

from logger import log
from settings_handler import settings_handler
from database import Session, Reservation, ReservedContainerPort, Role
from helpers.auth import create_password
from sqlalchemy import select

from docker.containers import start_container, stop_container, restart_container
from docker.monitoring import update_server_monitoring
from docker.notifications import send_container_started_email, send_container_error_email, send_admin_failure_alert
from docker.ports import get_available_port
from docker.queries import (
    get_reservations_requiring_start, get_running_reservations,
    get_reservations_requiring_stop, get_reservations_requiring_restart,
    get_container_information, get_computer_id, get_running_reserved_docker_containers,
    get_containers_requiring_build, get_containers_requiring_image_removal, reset_stale_building_status
)
from docker.image_builder import build_and_push_image, remove_image, update_all_image_sizes

# Runs the script forever
run: bool = True
# The ID of the computer from the database which this script should react to is saved here
computer_id: int = None


def time_now():
  """Return the current UTC datetime.

  Returns:
      datetime: Current time in UTC timezone.
  """
  return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Daemon main loop
# ---------------------------------------------------------------------------

def main():
  """Run the daemon's main polling loop.

  Continuously cycles through lifecycle checks every 10 seconds:
  stop finished containers, start new ones, restart crashed or
  restart-requested containers. Server monitoring is updated every
  30 seconds, and orphan container cleanup runs every 60 seconds.
  """
  while (run):
    for i in range(6):
      stop_finished_servers()
      start_new_servers()
      restart_crashed_servers()
      restart_servers_requiring_restart()
      process_image_builds()
      process_image_removals()

      # Update monitoring data every 3rd iteration (every 30 seconds)
      if i % 3 == 0:
        update_server_monitoring()

      sleep(10)
    # Run this larger cleanup below every 60 seconds (1 minute)
    stop_orphan_container_reservations()


# ---------------------------------------------------------------------------
# Lifecycle handlers (called from main loop)
# ---------------------------------------------------------------------------

def stop_finished_servers():
  """Stop containers whose reservations have ended.

  Queries for reservations past their end date with status "started" or
  "reserved" on this computer, then stops each corresponding Docker
  container.
  """
  global computer_id
  reservations = get_reservations_requiring_stop(computer_id)
  for reservation in reservations:
    if settings_handler.get_setting("docker.enabled") == True:
      stop_docker_container(reservation.reservationId)

def start_new_servers():
  """Start containers for reservations that are due to begin.

  Queries for reservations with status "reserved" whose start date has
  passed on this computer, then starts a Docker container for each one.
  """
  global computer_id
  reservations = get_reservations_requiring_start(computer_id)
  for reservation in reservations:
    if settings_handler.get_setting("docker.enabled") == True:
      start_docker_container(reservation.reservationId)

def restart_crashed_servers():
  """Restart containers that have exited unexpectedly.

  Queries for running reservations on this computer, inspects each
  container's Docker state, and restarts any that have exited.
  """
  global computer_id
  reservations = get_running_reservations(computer_id)
  for reservation in reservations:
    if settings_handler.get_setting("docker.enabled") == True:
      try:
        container_name, container_state = get_container_information(reservation.reservationId)
        if container_state.state.status == "exited":
          log.warning(f"Container exited unexpectedly for reservation {reservation.reservationId}, restarting")
          restart_docker_container(reservation.reservationId)
      except Exception as e:
        log.error(f"Error restarting crashed container for reservation {reservation.reservationId}: {e}")

def restart_servers_requiring_restart():
  """Restart containers that have been flagged for restart by a user or admin.

  Queries for reservations with status "restart" on this computer whose
  end date has not yet passed, then restarts each corresponding Docker
  container.
  """
  global computer_id
  reservations = get_reservations_requiring_restart(computer_id)

  for reservation in reservations:
    if settings_handler.get_setting("docker.enabled") == True:
      try:
        restart_docker_container(reservation.reservationId)
      except Exception as e:
        log.error(f"Error restarting container for reservation {reservation.reservationId}: {e}")

def process_image_builds():
  """Build Docker images for containers with pending build requests.

  Queries for containers with buildStatus "pending" and builds them
  one at a time to avoid resource contention. Each build generates
  a Dockerfile from the base template plus custom commands, builds
  the image, and pushes it to the local registry.
  """
  containers = get_containers_requiring_build()
  for container in containers:
    log.info(f"Building image for container {container.containerId} ({container.imageName})")
    try:
      build_and_push_image(container.containerId)
    except Exception as e:
      log.error(f"Error building image for container {container.containerId} ({container.imageName}): {e}")

def process_image_removals():
  """Remove Docker images for containers that have been deleted by admins.

  Queries for containers with buildStatus "removing" and removes their
  Docker images one at a time.
  """
  containers = get_containers_requiring_image_removal()
  for container in containers:
    log.info(f"Removing image for deleted container {container.containerId} ({container.imageName})")
    try:
      remove_image(container.containerId)
    except Exception as e:
      log.error(f"Error removing image for container {container.containerId} ({container.imageName}): {e}")

def stop_orphan_container_reservations():
  """Clean up Docker containers that have no matching active reservation.

  Compares containers physically running in Docker (with names starting
  with "reservation-") against reservations marked as "started" in the
  database. Any container running for more than 30 minutes without a
  matching database record is considered orphaned and is stopped and
  removed. Orphan containers can occur when the daemon encounters an
  error and fails to clean up properly.
  """

  try:
    # Get all containers marked as started in the database
    reservations = get_running_reservations(computer_id)
    for reservation in reservations:
      pass  # containerDockerId might be None

    # Get all Docker container reservations (container name starting with "reservation-"") really running on this computer
    docker_reservation_containers = get_running_reserved_docker_containers()
    for container in docker_reservation_containers:
      time_running = datetime.now(timezone.utc) - container.state.started_at
      # If the container has been running for over 30 minutes, check that it is really marked as running in the database
      if time_running > timedelta(minutes=30):
        is_running = False
        for reservation in reservations:
          if reservation.reservedContainer.containerDockerName == container.name: is_running = True
        if is_running:
          pass
        else:
          log.warning(f"Orphan container detected (not in database): container name {container.name}, stopping it")
          stop_orphan_docker_container(container.name)
  except Exception as e:
    log.error(f"Error stopping (cleaning up) orphan containers: {e}")


# ---------------------------------------------------------------------------
# Orchestration functions (bridge between DB reservations and Docker operations)
# ---------------------------------------------------------------------------

def start_docker_container(reservation_id: str):
  """Build configuration and start a Docker container for a reservation.

  Reads the reservation from the database, assembles all container
  parameters (image, hardware specs, ports, mounts, GPU assignment),
  calls the Docker start_container function, and updates the
  reservation status accordingly. Sends email notifications on both
  success and failure.

  Args:
      reservation_id: Database ID of the reservation to start.
  """
  with Session() as session:
    reservation = session.execute(
      select(Reservation).where(Reservation.reservationId == reservation_id)
    ).scalar_one_or_none()
    if reservation == None: return False
    ssh_password = create_password()

    # Guard: if the container has Dockerfile commands but hasn't been built successfully, block start
    container_obj = reservation.reservedContainer.container
    if container_obj.dockerfileCommands and container_obj.buildStatus != "success":
      log.warning(f"Container image for {container_obj.imageName} not built successfully (status: {container_obj.buildStatus}), marking reservation {reservation_id} as error")
      reservation.status = "error"
      reservation.reservedContainer.containerDockerErrorMessage = "Container image has not been built successfully. Please ask an admin to build the image first."
      reservation.reservedContainer.containerStatus = "error"
      session.commit()
      return

    image_name = container_obj.imageName
    hw_specs = {}
    gpu_specs = {}
    for spec in reservation.reservedHardwareSpecs:
      if spec.hardwareSpec.type == "gpu":
        gpu_specs[spec.hardwareSpec.internalId] = { "amount": spec.amount }
      else:
        hw_specs[spec.hardwareSpec.type] = { "amount": spec.amount }

    time_now_parsed = time_now().strftime('%m_%d_%Y_%H_%M_%S')

    container_name = f"reservation-{reservation.reservationId}-{image_name.replace(':', '').replace('/', '')}-{time_now_parsed}"
    reservation.reservedContainer.containerDockerName = container_name

    ports = []

    # Set bindable ports for the reservation container
    for port in reservation.reservedContainer.container.containerPorts:
      outside_port = get_available_port()
      ports.append({
        "containerPortId" : port.containerPortId,
        "serviceName": port.serviceName,
        "localPort": port.port,
        "outsidePort": outside_port
      })

    # Create the GPUs string to be passed to Docker
    gpus_string = ""
    # Loop through all hw_specs and find the reserved GPU internal IDs (Nvidia / cuda IDs), if any
    if len(gpu_specs) > 0:
      gpus_string = "device="
      for gpu in gpu_specs:
        gpus_string = gpus_string + gpu + ","
      # Remove the trailing , from gpu_specs, if it exists
      if gpus_string[-1] == ",": gpus_string = gpus_string[:-1]


    # Create the port string to be passed to Docker
    ports_for_container = []
    for port in ports:
      ports_for_container.append( (port["outsidePort"], port["localPort"]) )

    details = {
      "name": container_name,
      "image": image_name,
      "username": container_obj.containerUsername or "user",
      "cpus": int(hw_specs['cpus']["amount"]),
      "gpus": gpus_string if gpus_string else None,  # Convert empty string to None
      "memory": f"{hw_specs['ram']['amount']}g",
      "shm_size_percent": reservation.reservedContainer.shmSizePercent if reservation.reservedContainer.shmSizePercent is not None else 50,
      "ram_disk_percent": reservation.reservedContainer.ramDiskSizePercent if reservation.reservedContainer.ramDiskSizePercent is not None else 0,
      "ports": ports_for_container,
      "password": ssh_password,
      "dbUserId": reservation.userId,
      "reservation": {
        "computerId": reservation.computerId,
        "user": {
          "email": reservation.user.email
        }
      },
      "sshPublicKey": reservation.user.sshPublicKey,
      "passwordCommand": container_obj.passwordCommand,
      "sshKeyDeployCommands": container_obj.sshKeyDeployCommands,
    }

    # Add role-based mounts (now the unified mounting system)
    details["roleMounts"] = []

    # Always add mounts from "Everyone" role
    with Session() as mount_session:
        everyone_role = mount_session.execute(
            select(Role).where(Role.name == "everyone")
        ).scalar_one_or_none()
        if everyone_role:
            for mount in everyone_role.mounts:
                if mount.computerId == reservation.computerId:
                    details["roleMounts"].append({
                        "hostPath": mount.hostPath,
                        "containerPath": mount.containerPath,
                        "readOnly": mount.readOnly,
                        "computerId": mount.computerId
                    })

    # Add mounts from user's assigned roles
    for role in reservation.user.roles:
        for mount in role.mounts:
            # Only add mounts for the current computer
            if mount.computerId == reservation.computerId:
                # Check if this mount is already added (avoid duplicates from Everyone role)
                mount_exists = any(
                    existing["hostPath"] == mount.hostPath and
                    existing["containerPath"] == mount.containerPath
                    for existing in details["roleMounts"]
                )
                if not mount_exists:
                    details["roleMounts"].append({
                        "hostPath": mount.hostPath,
                        "containerPath": mount.containerPath,
                        "readOnly": mount.readOnly,
                        "computerId": mount.computerId
                    })

    cont_was_started = False
    cont_was_started, cont_name, cont_password, errors, non_critical_errors, container_docker_id = start_container(details)

    if cont_was_started == True:
      log.info(f"Container started for reservation {reservation_id}, user={reservation.userId}, image={image_name}, docker_name={cont_name}, docker_id={container_docker_id}")
      # Set bound ports
      for port in ports:
        reservation.reservedContainer.reservedContainerPorts.append(ReservedContainerPort(
          outsidePort = port["outsidePort"],
          containerPortForeign = port["containerPortId"]
        ))

      # Set basic reservation status
      reservation.status = "started"
      reservation.reservedContainer.sshPassword = cont_password
      reservation.reservedContainer.startedAt = time_now()
      reservation.reservedContainer.containerDockerId = container_docker_id
      reservation.reservedContainer.containerStatus = "running"
      send_container_started_email(
        reservation.user.email, image_name, reservation.computer.ip,
        ports, ssh_password, non_critical_errors, reservation.endDate,
        container_obj.containerUsername or "user"
      )

      session.commit()
    else:
      # Set error message to database
      log.error(f"Failed to start container for reservation {reservation_id}, user={reservation.userId}, image={image_name}: {errors}")
      reservation.status = "error"
      reservation.reservedContainer.containerDockerErrorMessage = str(errors)
      reservation.reservedContainer.containerStatus = "error"
      session.commit()

      send_container_error_email(reservation.user.email, errors)
      send_admin_failure_alert(
        reservation.user.email, reservation.reservationId,
        image_name, reservation.computer.name, errors
      )

def stop_docker_container(reservation_id: str):
  """Stop a Docker container and update the reservation to "stopped".

  Looks up the reservation in the database, stops the corresponding
  Docker container, and records the stop timestamp.

  Args:
      reservation_id: Database ID of the reservation whose container
          should be stopped.
  """
  try:
    with Session() as session:
      reservation = session.execute(
        select(Reservation).where(Reservation.reservationId == reservation_id)
      ).scalar_one_or_none()
      if reservation == None: return False

      container_docker_name = reservation.reservedContainer.containerDockerName
      if reservation.status in ("started", "restart_error"):
        stop_container(container_docker_name)
      reservation.status = "stopped"
      reservation.reservedContainer.stoppedAt = time_now()
      reservation.reservedContainer.containerStatus = "stopped"
      session.commit()
      container_docker_id = reservation.reservedContainer.containerDockerId
      log.info(f"Container stopped for reservation {reservation_id}, user={reservation.userId}, docker_name={container_docker_name}, docker_id={container_docker_id}")
  except Exception as e:
    log.error(f"Error stopping container for reservation {reservation_id}: {e}")

def stop_orphan_docker_container(container_name):
  """Stop an orphan Docker container that has no active reservation.

  Args:
      container_name: Name of the Docker container to stop and remove.
  """
  if not container_name: return
  try:
    stop_container(container_name)
    log.info(f"Orphan container stopped: {container_name}")
  except Exception as e:
    log.error(f"Error stopping orphan container {container_name}: {e}")

def restart_docker_container(reservation_id: str):
  """Restart a Docker container and reset the reservation status to "started".

  If the restart fails, sets the reservation status to "restart_error"
  so the user can see the failure and manually retry.

  Args:
      reservation_id: Database ID of the reservation whose container
          should be restarted.
  """
  with Session() as session:
    reservation = session.execute(
      select(Reservation).where(Reservation.reservationId == reservation_id)
    ).scalar_one_or_none()
    if reservation == None: return False

    container_docker_name = reservation.reservedContainer.containerDockerName
    try:
      restart_container(container_docker_name)
      reservation.status = "started"
      reservation.reservedContainer.containerStatus = "running"
      reservation.reservedContainer.containerDockerErrorMessage = ""
      container_docker_id = reservation.reservedContainer.containerDockerId
      log.info(f"Container restarted for reservation {reservation_id}, user={reservation.userId}, docker_name={container_docker_name}, docker_id={container_docker_id}")
    except Exception as e:
      log.error(f"Error restarting container for reservation {reservation_id}, user={reservation.userId}, docker_name={container_docker_name}: {e}")
      reservation.status = "restart_error"
      reservation.reservedContainer.containerStatus = "restart_error"
      reservation.reservedContainer.containerDockerErrorMessage = f"Container failed to restart: {e}"

    session.commit()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run():
  """Initialize the daemon and start the main loop.

  Reads the server name from settings, resolves it to a database computer
  ID, and enters the infinite main polling loop. Exits if Docker is not
  enabled or if the server name cannot be found in the database. Called
  from the docker_utility.py entry-point shim.
  """
  global computer_id

  log.info("AI Server Docker utility started.")
  log.info("This software will run infinitely and start / stop servers for reservations.")

  # Check that docker support has been enabled
  if (settings_handler.get_setting("docker.enabled") != True):
    log.warning("Docker support has not been enabled. Enable it with settings.json setting docker.enabled: true")

  # Get ID of the computer from the database based on the settings.json key docker.serverName.
  # Exit on any errors
  server_name = settings_handler.get_setting("docker.serverName")
  if not server_name:
    log.critical("docker.serverName not specified in settings.json. The name should be exactly the same as in database. Exiting.")
    sys.exit()
  computer_id = get_computer_id(server_name)
  if not computer_id:
    log.critical(f"Could not find computer with name '{server_name}' from the database. Exiting.")
    sys.exit()

  # Reset any image builds that were interrupted by a previous shutdown
  reset_stale_building_status()

  # Update image sizes for all containers on startup
  update_all_image_sizes()

  # Ensure persistent SSH host keys exist for this server
  from docker.ssh_host_keys import ensure_host_keys
  host_keys_path = settings_handler.get_setting("docker.sshHostKeysPath")
  ensure_host_keys(host_keys_path)

  main()


if __name__ == "__main__":
  run()
