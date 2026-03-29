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
from docker.monitoring import updateServerMonitoring
from docker.notifications import send_container_started_email, send_container_error_email, send_admin_failure_alert
from docker.ports import get_available_port
from docker.queries import (
    getReservationsRequiringStart, getRunningReservations,
    getReservationsRequiringStop, getReservationsRequiringRestart,
    getContainerInformation, getComputerId, getRunningReservedDockerContainers
)

# Runs the script forever
run: bool = True
# The ID of the computer from the database which this script should react to is saved here
computerId: int = None


def timeNow():
  return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Daemon main loop
# ---------------------------------------------------------------------------

def main():
  while (run):
    for i in range(6):
      stopFinishedServers()
      startNewServers()
      restartCrashedServers()
      restartServersRequiringRestart()

      # Update monitoring data every 3rd iteration (every 30 seconds)
      if i % 3 == 0:
        updateServerMonitoring()

      sleep(10)
    # Run this larger cleanup below every 60 seconds (1 minute)
    stopOrphanContainerReservations()


# ---------------------------------------------------------------------------
# Lifecycle handlers (called from main loop)
# ---------------------------------------------------------------------------

def stopFinishedServers():
  '''
  Gathers a list of reservations (containers) which reservation is due, status is "started"
  and stops them one by one.
  '''
  global computerId
  reservations = getReservationsRequiringStop(computerId)
  for reservation in reservations:
    if settings_handler.getSetting("docker.enabled") == True:
      print(timeNow(), ": Stopping Docker server for reservation with reservationId: ",  reservation.reservationId)
      stopDockerContainer(reservation.reservationId)

def startNewServers():
  '''
  Gathers a list of reservations (containers) requiring to be started in the current computer (state is 'reserved')
  and starts them one by one.
  '''
  global computerId
  reservations = getReservationsRequiringStart(computerId)
  for reservation in reservations:
    if settings_handler.getSetting("docker.enabled") == True:
      print(timeNow(), ": Starting Docker server for reservation with reservationId: ",  reservation.reservationId)
      startDockerContainer(reservation.reservationId)

def restartCrashedServers():
  '''
  Gathers a list of crashed reservations (containers) requiring to be restarted in the current computer (state is 'error')
  and starts them one by one.
  '''
  global computerId
  reservations = getRunningReservations(computerId)
  for reservation in reservations:
    if settings_handler.getSetting("docker.enabled") == True:
      try:
        containerName, containerState = getContainerInformation(reservation.reservationId)
        if containerState.state.status == "exited":
          restartDockerContainer(reservation.reservationId)
      except Exception as e:
        print(f"Error restarting a crashed container:")
        print(e)

def restartServersRequiringRestart():
  '''
  Gathers a list of reservations (containers) requiring to be restarted in the current computer (state is 'restart')
  and starts them one by one.
  '''
  global computerId
  reservations = getReservationsRequiringRestart(computerId)

  for reservation in reservations:
    if settings_handler.getSetting("docker.enabled") == True:
      try:
        restartDockerContainer(reservation.reservationId)
      except Exception as e:
        print(f"Error restarting a container:")
        print(e)

def stopOrphanContainerReservations():
  '''
  Gathers a list of orphan (not bound to started server) reservations and stops & removes them.
  Basically, we verify for each container running in Docker that the reservation is also marked as started in database.
  Every reservation which is not started in the database will be stopped and removed.
  These orphan containers can occur when the script errors out, for ex, and the server was never removed.
  '''

  try:
    # Get all containers marked as started in the database
    reservations = getRunningReservations(computerId)
    for reservation in reservations:
      pass  # containerDockerId might be None

    # Get all Docker container reservations (container name starting with "reservation-"") really running on this computer
    docker_reservation_containers = getRunningReservedDockerContainers()
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
          stopOrphanDockerContainer(container.name)
  except Exception as e:
    print("Error stopping (cleaning up) orphan containers:")
    print(e)


# ---------------------------------------------------------------------------
# Orchestration functions (bridge between DB reservations and Docker operations)
# ---------------------------------------------------------------------------

def startDockerContainer(reservationId: str):
  with Session() as session:
    reservation = session.query(Reservation).filter( Reservation.reservationId == reservationId ).first()
    if reservation == None: return False
    sshPassword = create_password()

    imageName = reservation.reservedContainer.container.imageName
    hwSpecs = {}
    gpuSpecs = {}
    for spec in reservation.reservedHardwareSpecs:
      if spec.hardwareSpec.type == "gpu":
        gpuSpecs[spec.hardwareSpec.internalId] = { "amount": spec.amount }
      else:
        hwSpecs[spec.hardwareSpec.type] = { "amount": spec.amount }

    timeNowParsed = timeNow().strftime('%m_%d_%Y_%H_%M_%S')

    containerName = f"reservation-{reservation.reservationId}-{imageName.replace(':', '').replace('/', '')}-{timeNowParsed}"
    reservation.reservedContainer.containerDockerName = containerName

    ports = []

    # Set bindable ports for the reservation container
    for port in reservation.reservedContainer.container.containerPorts:
      outsidePort = get_available_port()
      ports.append({
        "containerPortId" : port.containerPortId,
        "serviceName": port.serviceName,
        "localPort": port.port,
        "outsidePort": outsidePort
      })

    # Create the GPUs string to be passed to Docker
    gpusString = ""
    # Loop through all hwSpecs and find the reserved GPU internal IDs (Nvidia / cuda IDs), if any
    if len(gpuSpecs) > 0:
      gpusString = "device="
      for gpu in gpuSpecs:
        gpusString = gpusString + gpu + ","
      # Remove the trailing , from gpuSpecs, if it exists
      if gpusString[-1] == ",": gpusString = gpusString[:-1]


    # Create the port string to be passed to Docker
    portsForContainer = []
    for port in ports:
      portsForContainer.append( (port["outsidePort"], port["localPort"]) )

    details = {
      "name": containerName,
      "image": imageName,
      "username": "user",
      "cpus": int(hwSpecs['cpus']["amount"]),
      "gpus": gpusString if gpusString else None,  # Convert empty string to None
      "memory": f"{hwSpecs['ram']['amount']}g",
      "shm_size_percent": reservation.reservedContainer.shmSizePercent if reservation.reservedContainer.shmSizePercent is not None else 50,
      "ram_disk_percent": reservation.reservedContainer.ramDiskSizePercent if reservation.reservedContainer.ramDiskSizePercent is not None else 0,
      "ports": portsForContainer,
      "password": sshPassword,
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
      reservation.reservedContainer.startedAt = timeNow()
      send_container_started_email(
        reservation.user.email, imageName, reservation.computer.ip,
        ports, sshPassword, non_critical_errors, reservation.endDate
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
        imageName, reservation.computer.name, errors
      )

      print("Container was not started. Logged the error to ReservedContainer.")

def stopDockerContainer(reservationId: str):
  try:
    with Session() as session:
      reservation = session.query(Reservation).filter( Reservation.reservationId == reservationId ).first()
      if reservation == None: return False

      if (reservation.status == "started"):
        stop_container(reservation.reservedContainer.containerDockerName)
      reservation.status = "stopped"
      reservation.reservedContainer.stoppedAt = timeNow()
      session.commit()
  except Exception as e:
    print("Error stopping server:")
    print(e)

def stopOrphanDockerContainer(containerName):
  if not containerName: return
  try:
    stop_container(containerName)
  except Exception as e:
    print("Error stopping orphan container:")
    print(e)

def restartDockerContainer(reservationId: str):
  try:
    with Session() as session:
      reservation = session.query(Reservation).filter( Reservation.reservationId == reservationId ).first()
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
  global computerId

  print("AI Server Docker utility started.")
  print("This software will run infinitely and start / stop servers for reservations." + linesep)

  # Check that docker support has been enabled
  if (settings_handler.getSetting("docker.enabled") != True):
    print("!!! Docker support has not been enabled, so this script does nothing. Enable it with settings.json setting docker.enabled: true !!!" + linesep)

  # Get ID of the computer from the database based on the settings.json key docker.serverName.
  # Exit on any errors
  serverName = settings_handler.getSetting("docker.serverName")
  if not serverName:
    print("!!! You need to specify the name of the server in settings.json file, in key docker.serverName. The name should be exactly the same as in database !!! Exiting." + linesep)
    sys.exit()
  computerId = getComputerId(serverName)
  if not computerId:
    print("!!! Could not find computer with this name from the database. settings.json should contain docker.serverName and the name should be exactly the same as the computer in the database. !!! Exiting." + linesep)
    sys.exit()

  main()


if __name__ == "__main__":
  run()
