from python_on_whales import docker
from database import Session, Reservation, Computer, ReservedContainerPort, Role
from helpers.auth import create_password
from helpers.server import ORMObjectToDict
#from dateutil import parser
#from dateutil.relativedelta import *
from helpers.email import send_email
from datetime import timezone
import datetime
from helpers.auth import create_password
from settings import settings
from docker.docker_functionality import get_email_container_started, start_container, stop_container, restart_container
import random
import socket
import os

def is_port_in_use(port: int) -> bool:
  '''
  Checks if a port is in use.
  Returns:
    True if port is in use, False otherwise
  '''
  with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    return s.connect_ex(('localhost', port)) == 0

def get_available_port():
  # Loop through all started containers and get the ports in use
  portsInUse = []
  with Session() as session:
    allActiveReservations = session.query(Reservation).filter( Reservation.status == "started" )
    for reservation in allActiveReservations:
      for usedPort in reservation.reservedContainer.reservedContainerPorts:
        #print("Used port:", usedPort.outsidePort)
        portsInUse.append(usedPort.outsidePort)
    min = settings.docker["port_range_start"]
    max = settings.docker["port_range_end"]
    availablePorts = []
    for port in range(min, max):
      if port not in portsInUse:
        availablePorts.append(port)
  
  # Try to bind to a random available port 50 times
  i = 0
  retries = 50
  while i < retries:
    randPort = random.choice(availablePorts)
    if is_port_in_use(randPort) == False:
       return randPort
    i += 1

  print("ERROR: Did not find a random port to bind to after 50 attempts. Randomly giving one out.")
  return random.choice(availablePorts)

import re
def removeSpecialCharacters(string):
  pattern = re.compile(r'[^a-zA-Z0-9\s]')
  return re.sub(pattern, '', string)

def timeNow():
  return datetime.datetime.now(datetime.timezone.utc)

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
      #print(f"{spec.hardwareSpec.type}: {spec.amount} {spec.hardwareSpec.format}")

    timeNowParsed = timeNow().strftime('%m_%d_%Y_%H_%M_%S')

    containerName = f"reservation-{reservation.reservationId}-{imageName.replace(':', '').replace('/', '')}-{timeNowParsed}"
    reservation.reservedContainer.containerDockerName = containerName

    ports = []

    # Set bindable ports for the reservation container
    for port in reservation.reservedContainer.container.containerPorts:
      #print(port.port)
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
      "gpus": gpusString,
      "memory": f"{hwSpecs['ram']['amount']}g",
      "shm_size": settings.docker["shm_size"],
      "ports": portsForContainer,
      "password": sshPassword,
      "dbUserId": reservation.userId,
      "reservation": reservation  # Add this line to include the reservation parameter
    }

    if settings.docker.get("userMountLocation"):
      userEmailParsed = removeSpecialCharacters(reservation.user.email)
      userMountLocation = f'{settings.docker["userMountLocation"]}/{userEmailParsed}'
      details["localMountFolderPath"] = userMountLocation

    # Add role-based mounts
    details["roleMounts"] = []
    
    # Always add mounts from "Everyone" role (roleId = 0)
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

    # Convert reservation to dictionary
    details["reservation"] = {
        "computerId": reservation.computerId
    }

    cont_was_started = False
    #print(details)
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
      # Send the email
      if (settings.docker["sendEmail"] == True):
        body =  get_email_container_started(
          imageName,
          reservation.computer.ip,
          ports,
          sshPassword,
          True,
          non_critical_errors,
          reservation.endDate
          )
        send_email(reservation.user.email, "AI Server is ready to use!", body)
      
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

      # Send email about the error
      if (settings.docker["sendEmail"] == True):
        body = f"Your AI server reservation did not start as there was an error. {os.linesep}{os.linesep}"
        body += f"The error was: {os.linesep}{os.linesep}{errors}{os.linesep}{os.linesep}"
        body += "Please do not reply to this email, this email is sent from a noreply email address."
        send_email(reservation.user.email, "AI Server did not start", body)

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

def updateRunningContainerStatus(reservationId: str):
  print("IMPLEMENT")
  with Session() as session:
    reservation = session.query(Reservation).filter( Reservation.reservationId == reservationId ).first()
    print(ORMObjectToDict(reservation))
    print(ORMObjectToDict(reservation.reservedContainer))
    reservation.reservedContainer.containerStatus = "Container status here..."
    session.commit()

def getReservationsRequiringStart(computerId : int):
  '''
  Returns all reservations requiring start in the given computer.
  Parameters:
    computerId: ID of the computer.
  
  Returns:
    List of reservations requiring start in the given computer.
  '''
  with Session() as session:
    reservations = session.query(Reservation).filter(
      Reservation.status == "reserved",
      Reservation.computerId == computerId,
      Reservation.startDate < timeNow()
    )
    return reservations

def getRunningReservations(computerId : int):
  '''
  Returns all running reservations in the given computer.
  Parameters:
    computerId: ID of the computer.
  
  Returns:
    List of running reservations in the given computer.
  '''
  with Session() as session:
    reservations = session.query(Reservation).filter(
      Reservation.status == "started",
      Reservation.startDate < timeNow(),
      Reservation.computerId == computerId,
      Reservation.endDate > timeNow()
    )
    return reservations

def getReservationsRequiringStop(computerId : int):
  '''
  Returns all reservations requiring stop in the given computer.
  Parameters:
    computerId: ID of the computer.
  
  Returns:
    List of reservations requiring stop in the given computer.
  '''
  with Session() as session:
    reservations = session.query(Reservation).filter(
      Reservation.computerId == computerId,
      Reservation.status.in_(["started", "reserved"]),
      Reservation.endDate < timeNow()
    )
    return reservations

def getReservationsRequiringRestart(computerId : int):
  '''
  Returns all reservations requiring restart in the given computer.
  Parameters:
    computerId: ID of the computer.
  
  Returns:
    List of reservations requiring restart in the given computer.
  '''
  with Session() as session:
    reservations = session.query(Reservation).filter(
      Reservation.status == "restart",
      Reservation.computerId == computerId,
      Reservation.endDate > timeNow()
    )
    return reservations

def getContainerInformation(reservationId: str):
  '''
    Returns:
      On error or if cannot find the container:
        None, {}
      Otherwise (example, first is container name / ID and second is the python_on_whales.components.container.models.ContainerState object):
        "yolov7_12_12_12_2023",
        python_on_whales.components.container.models.ContainerState object {
          containerName = 'yolov7_12_12_12_2023',
          status='running',
          running=True,
          paused=False,
          restarting=False,
          oom_killed=False,
          dead=False,
          pid=1042809,
          exit_code=0,
          error='',
          started_at=datetime.datetime(2023, 5, 22, 17, 47, 42, 381981),
          tzinfo=datetime.timezone.utc),
          finished_at=datetime.datetime(1, 1, 1, 0, 0, tzinfo=datetime.timezone.utc),
          health=None
        }
  '''
  try:
    with Session() as session:
      reservation = session.query(Reservation).filter( Reservation.reservationId == reservationId ).first()
      if reservation == None:
        return None, {}
      containerState = docker.container.inspect(reservation.reservedContainer.containerDockerName)
      return reservation.reservedContainer.containerDockerName, containerState
  except Exception as e:
    print(f"Something went wrong getting container information for reservation {reservationId}. Error:")
    print(e)
    return None, {}

def getComputerId(computerName: str):
  '''
  Gets the ID of the computer in the database with the given name.

  Parameters:
    computerName: Name of the computer (in the database)
  
  Returns:
    ID of the computer, or None if it was not found or we encounter any exception.
  '''
  try:
    with Session() as session:
      computer = session.query(Computer).filter( Computer.name == computerName ).first()
      if computer == None:
        return None
      return computer.computerId
  except Exception as e:
    print(f"Something went wrong getting computer ID for name: {computerName}. Error:")
    print(e)
    return None

def getRunningReservedDockerContainers():
  '''
  Finds all Docker containers with name starting with "reservation-".
  Basically all reservations that are physically running on this computer.
  '''
  running_containers = docker.ps()

  # Filter containers whose names start with "reservation-"
  reservation_containers = [
  container for container in running_containers
    if container.name.startswith("reservation-")
  ]

  return reservation_containers
