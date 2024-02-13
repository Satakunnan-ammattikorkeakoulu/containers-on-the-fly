from docker.dockerUtils import getComputerId, getContainerInformation, getRunningReservations, getReservationsRequiringStart, getReservationsRequiringStop, stopDockerContainer, startDockerContainer, getReservationsRequiringRestart, restartDockerContainer
from time import sleep
from settings import settings
import datetime
from datetime import timezone
import sys
from os import linesep

# Runs the script forever
run : bool = True
# The ID of the computer from the database which this script should react to is saved here
computerId : int = None

def timeNow():
  return datetime.datetime.now(datetime.timezone.utc)

def main():
  while (run):
    stopFinishedServers()
    startNewServers()
    restartCrashedServers()
    restartServersRequiringRestart()
    sleep(10)

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