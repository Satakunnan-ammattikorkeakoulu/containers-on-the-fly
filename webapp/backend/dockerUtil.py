from docker.dockerUtils import stopOrphanDockerContainer, getRunningReservedDockerContainers, getComputerId, getContainerInformation, getRunningReservations, getReservationsRequiringStart, getReservationsRequiringStop, stopDockerContainer, startDockerContainer, getReservationsRequiringRestart, restartDockerContainer
from time import sleep
from settings import settings
import datetime
from datetime import timezone, datetime, timedelta
import sys
from os import linesep

# Runs the script forever
run : bool = True
# The ID of the computer from the database which this script should react to is saved here
computerId : int = None

def timeNow():
  return datetime.now(timezone.utc)

def main():
  while (run):
    for _ in range(6):
      stopFinishedServers()
      startNewServers()
      restartCrashedServers()
      restartServersRequiringRestart()
      sleep(10)
    # Run this larger cleanup below every 60 seconds (1 minute)
    stopOrphanContainerReservations()

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
      print(reservation.reservedContainer.containerDockerName)
    
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
          # Container not marked as started in the database - stop it
          stopOrphanDockerContainer(container.name)
          print("Container Docker reservation not synchronized with database! Reservation ID: " + str(reservation.reservationId) + " and container name: " + container.name)
  except Exception as e:
    print("Error stopping (cleaning up) orphan containers:")
    print(e)

def stopFinishedServers():
  '''
  Gathers a list of reservations (containers) which reservation is due, status is "started"
  and stops them one by one.
  '''
  global computerId
  reservations = getReservationsRequiringStop(computerId)
  for reservation in reservations:
    if settings.docker["enabled"] == True:
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
    if settings.docker["enabled"] == True:
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
    if settings.docker["enabled"] == True:
      try:
        containerName, containerState = getContainerInformation(reservation.reservationId)
        #print(containerName, containerState)
        #print(containerState.state.status)
        if containerState.state.status == "exited":
          restartDockerContainer(reservation.reservationId)
      except Exception as e:
        print(f"Error restarting a container:")
        print(e)
        pass
      
      #print(timeNow(), ": Restarting Docker server for reservation with reservationId: ",  reservation.reservationId)
      #startDockerContainer(reservation.reservationId)

def restartServersRequiringRestart():
  '''
  Gathers a list of reservations (containers) requiring to be restarted in the current computer (state is 'restart')
  and starts them one by one.
  '''
  global computerId
  reservations = getReservationsRequiringRestart(computerId)

  for reservation in reservations:
    if settings.docker["enabled"] == True:
      try:
        restartDockerContainer(reservation.reservationId)
      except Exception as e:
        print(f"Error restarting a container:")
        print(e)
        pass
      
      #print(timeNow(), ": Restarting Docker server for reservation with reservationId: ",  reservation.reservationId)
      #startDockerContainer(reservation.reservationId)

if __name__ == "__main__":
  print("AI Server Docker utility started.")
  print("This software will run infinitely and start / stop servers for reservations." + linesep)

  # Check that docker support has been enabled
  if (settings.docker['enabled'] != True):
    print("!!! Docker support has not been enabled, so this script does nothing. Enable it with settings.json setting docker.enabled: true !!!" + linesep)

  # Get ID of the computer from the database based on the settings.json key docker.serverName.
  # Exit on any errors
  serverName = settings.docker["serverName"]
  if not serverName:
    print("!!! You need to specify the name of the server in settings.json file, in key docker.serverName. The name should be exactly the same as in database !!! Exiting." + linesep)
    sys.exit()
  computerId = getComputerId(serverName)
  if not computerId:
    print("!!! Could not find computer with this name from the database. settings.json should contain docker.serverName and the name should be exactly the same as the computer in the database. !!! Exiting." + linesep)
    sys.exit()

  main()