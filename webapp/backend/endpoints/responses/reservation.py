from database import Session, Computer, User, Reservation, Container, ReservedContainer, ReservedHardwareSpec, HardwareSpec
from docker.docker_functionality import get_email_container_started, restart_container
from helpers.server import Response, ORMObjectToDict
from helpers.auth import IsAdmin
from dateutil import parser
from dateutil.relativedelta import *
import datetime
from datetime import timezone, timedelta
from docker.dockerUtils import stop_container
from endpoints.models.reservation import ReservationFilters
from sqlalchemy.orm import joinedload

# TODO: Should be able to send a computer here and get the available hardware specs for it.
# TODO: Should also be able to only fail there is not enough resources any computer. Right now it fails if any of the computers are out of resources for the given time period.
def getAvailableHardware(date : str, duration : int, reducableSpecs : dict = None, isAdmin = False, ignoredReservationId : int = None) -> object:
  '''
  Returns a list of all available hardware specs for the given date and duration.
  
  Args:
    date (str): The date when the reservation starts.
    duration (int): The duration of the reservation in hours.
    reducableSpecs (dict): If reducableSpecs is given, it will reduce the available hardware specs by the given amount.
      Example: { "1": 1, "2": 0, ... }
      Where the key is the hardwareSpecId and the value is the amount to reduce.
    
  Returns:
    object: Response object with status, message and data.

    If status is True, data will contain a list of all available hardware specs for the given date and duration.
    If status is False, message will contain the error message. The error is usually that there are not enough resources for the given date and duration.
  '''
  date = parser.parse(date)
  endDate = date+relativedelta(hours=+duration)

  # Fetch all required data first
  with Session() as session:
    reservations = session.query(Reservation)\
      .options(
        joinedload(Reservation.reservedHardwareSpecs)
      )\
      .filter(
        Reservation.startDate < endDate,
        Reservation.endDate > date,
        (Reservation.status == "reserved") | (Reservation.status == "started")
      )
    allComputers = session.query(Computer).filter(Computer.removed.isnot(True), Computer.public.is_(True))
    allContainers = session.query(Container)
    session.close()

  #print("Ignored reservation ID: ", ignoredReservationId)

  # All reserved hardware specs for the given time period will be listed here
  # This loop will go through all reservations and add the reserved hardware specs to this list for the given time period
  removableHardwareSpecs = {}
  for res in reservations:
    if res.reservationId == ignoredReservationId: continue
    for spec in res.reservedHardwareSpecs:
      hardwareSpecId = spec.hardwareSpec.hardwareSpecId
      amount = spec.amount
      
      if hardwareSpecId not in removableHardwareSpecs:
        removableHardwareSpecs[hardwareSpecId] = amount
      else:
        removableHardwareSpecs[hardwareSpecId] += amount

  # Reduce the available hardware specs by the given reducable specs, if any
  if reducableSpecs != None:
    for key, val in reducableSpecs.items():
      intKey = int(key)
      if val == 0: continue
      if intKey not in removableHardwareSpecs:
        removableHardwareSpecs[intKey] = val
      else:
        removableHardwareSpecs[intKey] += val

  #print("removableHardwareSpecs: ", removableHardwareSpecs)

  computers = []

  for computer in allComputers:
    compDict = ORMObjectToDict(computer)
    compDict["hardwareSpecs"] = []
    for spec in computer.hardwareSpecs:
      compDict["hardwareSpecs"].append(ORMObjectToDict(spec))
    computers.append(compDict)

  containers = []
  for container in allContainers:
    containers.append(ORMObjectToDict(container))

  # Set all user maximums to max for admins
  if (isAdmin == True):
    for computer in computers:
      for spec in computer["hardwareSpecs"]:
        spec["maximumAmountForUser"] = spec["maximumAmount"]
  else:
    # Enforce GPU limit for non-admin users (max 1 GPU)
    for computer in computers:
      for spec in computer["hardwareSpecs"]:
        if spec["type"] == "gpu" and spec["maximumAmountForUser"] > 1:
          spec["maximumAmountForUser"] = 1

  for computer in computers:
    for spec in computer["hardwareSpecs"]:
      if spec["hardwareSpecId"] in removableHardwareSpecs:
        spec["maximumAmount"] -= removableHardwareSpecs[spec["hardwareSpecId"]]
        
        # Prevent any resource going below 0
        if (spec["maximumAmount"] < 0):
          spec["maximumAmount"] = 0

        #print(f"Reducing " + str(removableHardwareSpecs[spec["hardwareSpecId"]]) + " from max: " + str(spec["maximumAmount"]))
        if spec["maximumAmountForUser"] > spec["maximumAmount"]:
          spec["maximumAmountForUser"] = spec["maximumAmount"]
        #print("Reducing spec: ", spec["type"], " ", removableHardwareSpecs[spec["type"]], " max: " , spec["maximumAmount"], "maxForUser: ", spec["maximumAmountForUser"])
        if spec["maximumAmount"] < spec["minimumAmount"]:
          print("Spec: ", spec["type"], " ", spec["maximumAmount"], " is below minimum amount: ", spec["minimumAmount"])
          #print("minimumAmount: ", spec["minimumAmount"])
          #print("maximumAmount: ", spec["maximumAmount"])
          #print("maximumAmountForUser: ", spec["maximumAmountForUser"])
          specMessage = ""
          specMax = spec['maximumAmount']
          if specMax < 0: specMax = 0
          if spec["type"] == "ram":
            specMessage = f"Available: {specMax} {spec['format']} {spec['type']}."
          else:
            specMessage = f"Available: {specMax} {spec['type']}."
          return Response(False, f"Not enough resources to make a reservation: {spec['type']}. {specMessage}")

  return Response(True, "Hardware resources fetched.", { "computers": computers, "containers": containers })

def getOwnReservations(userId : int, filters : ReservationFilters) -> object:
  '''
  Returns a list of all reservations owned by the given user.

  Args:
    userId (int): The userId of the user.
    filters (ReservationFilters): The filters to apply to the query.

  Returns:
    object: Response object with status, message and data.
  '''
  reservations = []

  # Limit listing to 90 days
  def timeNow(): return datetime.datetime.now(datetime.timezone.utc)
  minStartDate = timeNow() - timedelta(days=90)

  with Session() as session:
    query = session.query(Reservation)\
      .options(
        joinedload(Reservation.reservedHardwareSpecs),
        joinedload(Reservation.reservedContainer).joinedload(ReservedContainer.reservedContainerPorts),
        joinedload(Reservation.reservedContainer).joinedload(ReservedContainer.container),
        joinedload(Reservation.computer)
      ).\
      filter(
        Reservation.userId == userId,
        (Reservation.startDate > minStartDate) | (Reservation.endDate > timeNow()))
    if filters.filters["status"] != "":
      query = query.filter( Reservation.status == filters.filters["status"] )
    session.close()
  
  for reservation in query:
    res = ORMObjectToDict(reservation)
    res["computerName"] = reservation.computer.name
    res["reservedContainer"] = ORMObjectToDict(reservation.reservedContainer)
    res["reservedContainer"]["container"] = ORMObjectToDict(reservation.reservedContainer.container)
    res["reservedContainer"]["reservedPorts"] = []
    # Only add ports if the reservation is started as the ports are unbound after the reservation is stopped
    if reservation.status == "started":
      for reservedPort in reservation.reservedContainer.reservedContainerPorts:
        portObj = ORMObjectToDict(reservedPort)
        portObj["localPort"] = reservedPort.containerPort.port
        portObj["serviceName"] = reservedPort.containerPort.serviceName
        res["reservedContainer"]["reservedPorts"].append(portObj)
    # Add all reserved hardware specs
    res["reservedHardwareSpecs"] = []
    for spec in reservation.reservedHardwareSpecs:
      # Add only specs over 0
      if spec.amount > 0:
          # Add also internalId for GPUs
          if spec.hardwareSpec.type == "gpu":
            format = f"{spec.hardwareSpec.format} (id: {spec.hardwareSpec.internalId})"
          else:
            format = spec.hardwareSpec.format

          res["reservedHardwareSpecs"].append({
            "type": spec.hardwareSpec.type,
            "format": format,
            "internalId": spec.hardwareSpec.format,
            "amount": spec.amount
          })
    reservations.append(res)
  
  return Response(True, "Hardware resources fetched.", { "reservations": reservations })

def getOwnReservationDetails(reservationId : int, userId : int) -> object:
  with Session() as session:
    # Check that the reservation exists and is owned by the current user (admins can view any reservation)
    if IsAdmin(userId):
      reservation = session.query(Reservation).filter( Reservation.reservationId == reservationId ).first()
    else:
      reservation = session.query(Reservation).filter( Reservation.reservationId == reservationId, Reservation.userId == userId ).first()
    if (reservation == None):
      return Response(False, "Reservation not found.")

    portsForEmail = []

    # Set bindable ports for the reservation container
    for port in reservation.reservedContainer.reservedContainerPorts:
      serviceName = port.containerPort.serviceName
      outsidePort = port.outsidePort
      localPort = port.containerPort.port
      portsForEmail.append({ "serviceName": serviceName, "localPort": localPort, "outsidePort": outsidePort })

    connectionText = get_email_container_started(
      reservation.reservedContainer.container.imageName,
      reservation.computer.ip,
      portsForEmail,
      reservation.reservedContainer.sshPassword,
      False,
      reservation.endDate
      )

    connectionText = connectionText.replace("\n", "<br>")

  return Response(True, "Details fetched.", { "connectionText": connectionText } )

def getCurrentReservations() -> object:
  reservations = []

  def timeNow(): return datetime.datetime.now(datetime.timezone.utc)
  minEndDate = timeNow() - timedelta(days=5)

  with Session() as session:
    query = session.query(Reservation)\
      .options(joinedload(Reservation.reservedHardwareSpecs))\
      .filter(
        ((Reservation.status == "reserved") | (Reservation.status == "started")),
        (Reservation.endDate > minEndDate),
      )
    session.close()
  for reservation in query:
    specs = []
    for spec in reservation.reservedHardwareSpecs:
      specs.append({
        "type": spec.hardwareSpec.type,
        "format": spec.hardwareSpec.format,
        "amount": spec.amount,
      })
    res = {
      "reservationId": reservation.reservationId,
      "startDate": reservation.startDate,
      "endDate": reservation.endDate,
      "computerId": reservation.computerId,
      "computerName": reservation.computer.name,
      "hardwareSpecs": specs,
    }
    reservations.append(res)
  
  return Response(True, "Current reservations fetched.", { "reservations": reservations })

def createReservation(userId : int, date: str, duration: int, computerId: int, containerId: int, hardwareSpecs, adminReserveUserEmail: str = None, description: str = None):
  # Validate description length if provided
  if description and len(description) > 50:
    return Response(False, "Description must be 50 characters or less.")
  
  # Make sure that there are enough resources for the reservation
  getAvailableHardwareResponse = getAvailableHardware(date, duration, hardwareSpecs)
  if (getAvailableHardwareResponse["status"] == False):
    return Response(False, getAvailableHardwareResponse["message"])

  date = parser.parse(date)
  endDate = date+relativedelta(hours=+duration)

  with Session() as session:
    # Check that user exists
    user = session.query(User).filter( User.userId == userId ).first()
    if (user == None):
      return Response(False, "User not found.")
    isAdmin = IsAdmin(user.email)

    # Check that computer and container exists
    computer = session.query(Computer).filter( Computer.computerId == computerId ).first()
    if (computer == None):
      return Response(False, "Computer not found.")
    container = session.query(Container).filter( Container.containerId == containerId ).first()
    if (container == None):
      return Response(False, "Container not found.")
    
    # Verify user can access this container
    if container.public == False and not isAdmin:
      return Response(False, "Access denied to private container.")

    # Make sure that user can only have one queued / started server at once (admins can have unlimited)
    userActiveReservations = session.query(Reservation).filter(
      (Reservation.userId == userId),
      ( (Reservation.status == "reserved") | (Reservation.status == "started") )
    ).count()
    if userActiveReservations > 0 and isAdmin == False:
      return Response(False, "You can only have one queued or started reservation.")

    # Check that the duration is between minimum and maximum lengths
    try:
        from settings_handler import getSetting
        min_duration = getSetting('reservation.minimumDuration')
        max_duration = getSetting('reservation.maximumDuration')
    except Exception:
        # Fallback to default values if database is unavailable
        min_duration = 5
        max_duration = 72
    
    if (duration < min_duration):
      return Response(False, f"Minimum duration is {min_duration} hours.")
    if (duration > max_duration) and isAdmin == False:
      return Response(False, f"Maximum duration is {max_duration} hours.")

    userId = user.userId

    # If adminReserveUserEmail is given, check that the user exists
    if adminReserveUserEmail != None and adminReserveUserEmail != "" and isAdmin == True:
      anotherUser = session.query(User).filter( User.email == adminReserveUserEmail ).first()
      if (anotherUser == None):
        return Response(False, "User for which you tried to reserve for did not exist. Check the email address: " + adminReserveUserEmail)
      user = anotherUser

    # Create the base reservation
    reservation_data = {
      "reservedContainerId": containerId,
      "startDate": date,
      "endDate": endDate,
      "userId": user.userId,
      "computerId": computerId,
      "status": "reserved",
    }
    
    # Only add description if it's provided and not empty
    if description and description.strip():
      reservation_data["description"] = description.strip()

    reservation = Reservation(**reservation_data)

    # Add GPU count validation
    total_gpus_requested = 0
    for key, val in hardwareSpecs.items():
      hardwareSpec = session.query(HardwareSpec).filter( HardwareSpec.hardwareSpecId == key ).first()
      if hardwareSpec and hardwareSpec.type == "gpu" and val > 0:
        total_gpus_requested += val
    
    # Validate total GPU count for non-admins (max 1 GPU per reservation)
    if not isAdmin and total_gpus_requested > 1:
      return Response(False, "You can only reserve 1 GPU at a time.")
    
    # Enhanced hardware specification validation
    for key, val in hardwareSpecs.items():
      # Validate hardware spec exists
      hardwareSpec = session.query(HardwareSpec).filter( HardwareSpec.hardwareSpecId == key ).first()
      if not hardwareSpec:
        return Response(False, f"Invalid hardware specification ID: {key}")
      
      # Validate amount bounds
      if val < 0:
        return Response(False, f"Invalid negative amount for {hardwareSpec.type}")
      if val > hardwareSpec.maximumAmount:
        return Response(False, f"Requested amount exceeds available resources for {hardwareSpec.type}: {val} > {hardwareSpec.maximumAmount}")
      
      # Check that the amount does not exceed user limits for the given hardware
      # Skipped for admins
      if val > hardwareSpec.maximumAmountForUser and isAdmin == False:
        return Response(False, f"Trying to utilize hardware specs above the user maximum amount for {hardwareSpec.type} {hardwareSpec.format}: {val} > {hardwareSpec.maximumAmountForUser}")
      
      # Only add resources over 0
      if val > 0:
        reservation.reservedHardwareSpecs.append(
          ReservedHardwareSpec(
            hardwareSpecId = key,
            amount = val,
          )
      )
    # Create the ReservedContainer
    reservation.reservedContainer = ReservedContainer(
      containerId = containerId,
    )
    #print(ORMObjectToDict(reservation))
    #print(ORMObjectToDict(reservation.reservedContainer))
    user.reservations.append(reservation)
    session.add(reservation)
    session.commit()

    from settings_handler import getSetting
    informByEmail = getSetting('email.sendEmail')

    return Response(True, "Reservation created succesfully!", { "informByEmail": informByEmail })

def cancelReservation(userId : int, reservationId: str):
  # Check that user owns the given reservation and it can be found
  # Admins can cancel any reservation
  # print("Starting to cancel reservation: " + reservationId)
  with Session() as session:
    reservation = None
    if IsAdmin(userId) == False:
      reservation = session.query(Reservation).filter( Reservation.reservationId == reservationId, Reservation.userId == userId ).first()
    else:
      reservation = session.query(Reservation).filter( Reservation.reservationId == reservationId ).first()
    if reservation is None: return Response(False, "No reservation found.")

    reservation.endDate = datetime.datetime.now(datetime.timezone.utc)
    session.commit()

  return Response(True, "Reservation cancelled.")

def extendReservation(userId : int, reservationId: str, duration: int):
  # Check that user owns the given reservation and it can be found
  # Admins can extend any reservation

  with Session() as session:
    if IsAdmin(userId) == False:
      reservationCheck = session.query(Reservation).filter( Reservation.reservationId == reservationId, Reservation.userId == userId ).first()
      if reservationCheck is None: return Response(False, "No reservation found for this user.")

    reservation = session.query(Reservation).filter( Reservation.reservationId == reservationId ).first()
    if reservation is None: return Response(False, "No reservation found.")
    
    if reservation.status != "started":
      return Response(False, "Reservation is not started, so cannot extend it.")
    
    # Check that the duration is between minimum and maximum lengths
    if duration < 0 or duration > 24:
      return Response(False, "Duration must be between 0 and 24 hours.")

    # Check that there are enough resources for the reservation extension
    # Reducable specs comes from the current reservation
    reducableSpecs = {}
    for spec in reservation.reservedHardwareSpecs:
      reducableSpecs[spec.hardwareSpecId] = spec.amount
    endTimeString = reservation.endDate.strftime("%Y-%m-%d %H:%M:%S")
    getAvailableHardwareResponse = getAvailableHardware(endTimeString, duration, reducableSpecs, False, reservation.reservationId)
    if getAvailableHardwareResponse["status"]:
      # Extend the reservation
      reservation.endDate = reservation.endDate + relativedelta(hours=+duration)
      session.commit()
      return Response(True, "Reservation was extended by " + str(duration) + " hours.")
    else:
      print(getAvailableHardwareResponse["message"])
      return Response(False, "Cannot extend reservation due to lack of resources. Try with less hours.")

  return Response(False, "Error.")

def restartContainer(userId : int, reservationId: str):
  reservation = None
  # Check that user owns the given container reservation and it can be found
  # Admins can restart any container
  with Session() as session:
    reservation = session.query(Reservation)\
      .options(joinedload(Reservation.reservedContainer))\
      .filter( Reservation.reservationId == reservationId )
    if IsAdmin(userId) == False:
      reservation = reservation.filter(Reservation.userId == userId )
    session.close()
  
  reservation = reservation.first()
  if reservation is None: return Response(False, "No reservation found.")

  if (reservation.status == "started"):
    reservation.status = "restart"
    session.commit()
    return Response(True, "Container will be restarted.")
  else:
    return Response(False, "Reservation is not currently started, so cannot restart the container.")
