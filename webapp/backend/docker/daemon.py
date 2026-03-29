"""
Docker utility daemon — manages container lifecycle based on reservation state.

Polls the database every 10 seconds to start, stop, restart, and clean up
Docker containers for reservations.
"""

from time import sleep
from datetime import timezone, datetime, timedelta
import sys
from os import linesep

from settings_handler import settings_handler
from database import Session, Reservation, ReservedContainerPort, Role
from helpers.auth import create_password

from docker.containers import start_container, stop_container, restart_container
from docker.monitoring import update_server_monitoring
from docker.notifications import send_container_started_email, send_container_error_email, send_admin_failure_alert
from docker.ports import get_available_port
from docker.queries import (
    get_reservations_requiring_start, get_running_reservations,
    get_reservations_requiring_stop, get_reservations_requiring_restart,
    get_container_information, get_computer_id, get_running_reserved_docker_containers
)

# Runs the script forever
run: bool = True
# The ID of the computer from the database which this script should react to is saved here
computer_id: int = None


def time_now():
  return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Daemon main loop
# ---------------------------------------------------------------------------

def main():
  while (run):
    for i in range(6):
      stop_finished_servers()
      start_new_servers()
      restart_crashed_servers()
      restart_servers_requiring_restart()

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
  '''
  Gathers a list of reservations (containers) which reservation is due, status is "started"
  and stops them one by one.
  '''
  global computer_id
  reservations = get_reservations_requiring_stop(computer_id)
  for reservation in reservations:
    if settings_handler.get_setting("docker.enabled") == True:
      print(time_now(), ": Stopping Docker server for reservation with reservationId: ",  reservation.reservationId)
      stop_docker_container(reservation.reservationId)

def start_new_servers():
  '''
  Gathers a list of reservations (containers) requiring to be started in the current computer (state is 'reserved')
  and starts them one by one.
  '''
  global computer_id
  reservations = get_reservations_requiring_start(computer_id)
  for reservation in reservations:
    if settings_handler.get_setting("docker.enabled") == True:
      print(time_now(), ": Starting Docker server for reservation with reservationId: ",  reservation.reservationId)
      start_docker_container(reservation.reservationId)

def restart_crashed_servers():
  '''
  Gathers a list of crashed reservations (containers) requiring to be restarted in the current computer (state is 'error')
  and starts them one by one.
  '''
  global computer_id
  reservations = get_running_reservations(computer_id)
  for reservation in reservations:
    if settings_handler.get_setting("docker.enabled") == True:
      try:
        container_name, container_state = get_container_information(reservation.reservationId)
        if container_state.state.status == "exited":
          restart_docker_container(reservation.reservationId)
      except Exception as e:
        print(f"Error restarting a crashed container:")
        print(e)

def restart_servers_requiring_restart():
  '''
  Gathers a list of reservations (containers) requiring to be restarted in the current computer (state is 'restart')
  and starts them one by one.
  '''
  global computer_id
  reservations = get_reservations_requiring_restart(computer_id)

  for reservation in reservations:
    if settings_handler.get_setting("docker.enabled") == True:
      try:
        restart_docker_container(reservation.reservationId)
      except Exception as e:
        print(f"Error restarting a container:")
        print(e)

def stop_orphan_container_reservations():
  '''
  Gathers a list of orphan (not bound to started server) reservations and stops & removes them.
  Basically, we verify for each container running in Docker that the reservation is also marked as started in database.
  Every reservation which is not started in the database will be stopped and removed.
  These orphan containers can occur when the script errors out, for ex, and the server was never removed.
  '''

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
          print("Container Docker reservation not synchronized with database! Reservation ID: " + str(reservation.reservationId) + " and container name: " + container.name)
          stop_orphan_docker_container(container.name)
  except Exception as e:
    print("Error stopping (cleaning up) orphan containers:")
    print(e)


# ---------------------------------------------------------------------------
# Orchestration functions (bridge between DB reservations and Docker operations)
# ---------------------------------------------------------------------------

def start_docker_container(reservation_id: str):
  with Session() as session:
    reservation = session.query(Reservation).filter( Reservation.reservationId == reservation_id ).first()
    if reservation == None: return False
    ssh_password = create_password()

    image_name = reservation.reservedContainer.container.imageName
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
      "username": "user",
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
      }
    }

    # Add role-based mounts (now the unified mounting system)
    details["roleMounts"] = []

    # Always add mounts from "Everyone" role
    with Session() as mount_session:
        everyone_role = mount_session.query(Role).filter(Role.name == "everyone").first()
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
    print("Starting container..")
    cont_was_started, cont_name, cont_password, errors, non_critical_errors = start_container(details)
    print("Container started!")
    print("Result: " + str(cont_was_started))

    if cont_was_started == True:
      print(f"Container with Docker name {cont_name} was started succesfully.")
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
      send_container_started_email(
        reservation.user.email, image_name, reservation.computer.ip,
        ports, ssh_password, non_critical_errors, reservation.endDate
      )

      session.commit()
    else:
      # Set error message to database
      print("Error starting container!")
      print("Critical errors:")
      if errors:
        print(errors)
      print("Non-critical errors:")
      if non_critical_errors:
        print(non_critical_errors)
      reservation.status = "error"
      reservation.reservedContainer.containerDockerErrorMessage = str(errors)
      session.commit()

      send_container_error_email(reservation.user.email, errors)
      send_admin_failure_alert(
        reservation.user.email, reservation.reservationId,
        image_name, reservation.computer.name, errors
      )

      print("Container was not started. Logged the error to ReservedContainer.")

def stop_docker_container(reservation_id: str):
  try:
    with Session() as session:
      reservation = session.query(Reservation).filter( Reservation.reservationId == reservation_id ).first()
      if reservation == None: return False

      if (reservation.status == "started"):
        stop_container(reservation.reservedContainer.containerDockerName)
      reservation.status = "stopped"
      reservation.reservedContainer.stoppedAt = time_now()
      session.commit()
  except Exception as e:
    print("Error stopping server:")
    print(e)

def stop_orphan_docker_container(container_name):
  if not container_name: return
  try:
    stop_container(container_name)
  except Exception as e:
    print("Error stopping orphan container:")
    print(e)

def restart_docker_container(reservation_id: str):
  try:
    with Session() as session:
      reservation = session.query(Reservation).filter( Reservation.reservationId == reservation_id ).first()
      if reservation == None: return False

      restart_container(reservation.reservedContainer.containerDockerName)
      reservation.status = "started"
      session.commit()
  except Exception as e:
    print("Error restarting server:")
    print(e)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run():
  """Initialize and start the daemon. Called from docker_util.py shim."""
  global computer_id

  print("AI Server Docker utility started.")
  print("This software will run infinitely and start / stop servers for reservations." + linesep)

  # Check that docker support has been enabled
  if (settings_handler.get_setting("docker.enabled") != True):
    print("!!! Docker support has not been enabled, so this script does nothing. Enable it with settings.json setting docker.enabled: true !!!" + linesep)

  # Get ID of the computer from the database based on the settings.json key docker.serverName.
  # Exit on any errors
  server_name = settings_handler.get_setting("docker.serverName")
  if not server_name:
    print("!!! You need to specify the name of the server in settings.json file, in key docker.serverName. The name should be exactly the same as in database !!! Exiting." + linesep)
    sys.exit()
  computer_id = get_computer_id(server_name)
  if not computer_id:
    print("!!! Could not find computer with this name from the database. settings.json should contain docker.serverName and the name should be exactly the same as the computer in the database. !!! Exiting." + linesep)
    sys.exit()

  main()


if __name__ == "__main__":
  run()
