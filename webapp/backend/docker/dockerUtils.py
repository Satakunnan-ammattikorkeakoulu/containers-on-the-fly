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
from helpers.Utils import removeSpecialCharacters

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
      from helpers.tables.SystemSetting import getSetting
      if getSetting('email.sendEmail', False):
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
      from helpers.tables.SystemSetting import getSetting
      if getSetting('email.sendEmail', False):
        body = f"Your AI server reservation did not start as there was an error. {os.linesep}{os.linesep}"
        body += f"The error was: {os.linesep}{os.linesep}{errors}{os.linesep}{os.linesep}"
        body += "Please do not reply to this email, this email is sent from a noreply email address."
        send_email(reservation.user.email, "AI Server did not start", body)

        # Send container failure alerts to admin emails if enabled
        try:
          from helpers.tables.SystemSetting import getSetting
          import smtplib
          from email.mime.multipart import MIMEMultipart
          from email.mime.text import MIMEText
          
          alerts_enabled = getSetting('notifications.containerAlertsEnabled', False, 'boolean')
          
          if alerts_enabled:
            alert_emails = getSetting('notifications.alertEmails', [], 'json')
            
            if alert_emails and len(alert_emails) > 0:
              # Get SMTP settings from database
              smtp_server = getSetting('email.smtpServer', '')
              smtp_port = getSetting('email.smtpPort', 587)
              smtp_username = getSetting('email.smtpUsername', '')
              smtp_password = getSetting('email.smtpPassword', '')
              from_email = getSetting('email.fromEmail', '')
              
              # Check if SMTP is configured
              if not all([smtp_server, smtp_port, smtp_username, smtp_password, from_email]):
                print("Container failure alerts enabled but SMTP configuration is incomplete")
              else:
                # Create list of recipients (avoiding duplicates)
                recipients = set(alert_emails)  # Use set to avoid duplicates
                
                # Remove user's email if it's in the alert list to prevent duplicate
                if reservation.user.email in recipients:
                  recipients.remove(reservation.user.email)
                
                # Send alert email to admin recipients
                if recipients:  # Only send if there are remaining recipients
                  admin_body = f"Container Failure Alert{os.linesep}{os.linesep}"
                  admin_body += f"A container reservation failed to start for user: {reservation.user.email}{os.linesep}"
                  admin_body += f"Reservation ID: {reservation.id}{os.linesep}"
                  admin_body += f"Container Image: {reservation.reservedContainer.containerImage.imageName}{os.linesep}"
                  admin_body += f"Server: {reservation.reservedContainer.computer.name}{os.linesep}"
                  admin_body += f"Error: {errors}{os.linesep}{os.linesep}"
                  admin_body += "This is an automated notification from the container management system."
                  
                  # Send to all admin recipients using database-based SMTP settings
                  successful_sends = 0
                  for admin_email in recipients:
                    try:
                      # Create message
                      msg = MIMEMultipart()
                      msg['From'] = from_email
                      msg['To'] = admin_email
                      msg['Subject'] = "Container Failure Alert"
                      msg.attach(MIMEText(admin_body, 'plain'))
                      
                      # Send email
                      with smtplib.SMTP(smtp_server, smtp_port) as server:
                        server.starttls()
                        server.login(smtp_username, smtp_password)
                        server.send_message(msg)
                        successful_sends += 1
                        
                    except Exception as email_error:
                      print(f"Failed to send alert to {admin_email}: {email_error}")
                  
                  if successful_sends > 0:
                    print(f"Container failure alerts sent to {successful_sends}/{len(recipients)} admin(s)")
                  else:
                    print(f"Failed to send container failure alerts to any of {len(recipients)} admin(s)")
                else:
                  print("Container failure alerts enabled but no additional recipients (user already notified)")
            else:
              print("Container failure alerts enabled but no alert emails configured")
        except Exception as e:
          print(f"Warning: Failed to send container failure alerts: {e}")

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
