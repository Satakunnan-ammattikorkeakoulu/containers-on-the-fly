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
def getAvailableHardware(date : str, duration : int, reducableSpecs : dict = None, isAdmin = False, ignoredReservationId : int = None, userId : int = None) -> object:
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

  # Get user's roles and their hardware limits
  user_role_limits = {}
  if userId:
    from database import RoleHardwareLimit, UserRole
    with Session() as session:
      # Get all roles for the user
      user_roles = session.query(UserRole).filter(UserRole.userId == userId).all()
      role_ids = [ur.roleId for ur in user_roles]
      
      # Get all hardware limits for user's roles
      if role_ids:
        role_limits = session.query(RoleHardwareLimit).filter(
          RoleHardwareLimit.roleId.in_(role_ids)
        ).all()
        
        # Build a dict of hardwareSpecId -> max limit across all roles
        for limit in role_limits:
          spec_id = limit.hardwareSpecId
          if spec_id not in user_role_limits or limit.maximumAmountForRole > user_role_limits[spec_id]:
            user_role_limits[spec_id] = limit.maximumAmountForRole

  # Set all user maximums to max for admins
  if (isAdmin == True):
    for computer in computers:
      for spec in computer["hardwareSpecs"]:
        spec["maximumAmountForUser"] = spec["maximumAmount"]
  else:
    # Apply role-based limits or default limits
    for computer in computers:
      for spec in computer["hardwareSpecs"]:
        # Check if there's a role-based limit for this hardware spec
        if spec["hardwareSpecId"] in user_role_limits:
          spec["maximumAmountForUser"] = min(user_role_limits[spec["hardwareSpecId"]], spec["maximumAmount"])
        # Otherwise, enforce GPU limit for non-admin users (max 1 GPU)
        elif spec["type"] == "gpu" and spec["maximumAmountForUser"] > 1:
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
    # Include SHM and RAM disk percentages
    res["shmSizePercent"] = reservation.reservedContainer.shmSizePercent if reservation.reservedContainer.shmSizePercent is not None else 50
    res["ramDiskSizePercent"] = reservation.reservedContainer.ramDiskSizePercent if reservation.reservedContainer.ramDiskSizePercent is not None else 0
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

def createReservation(userId : int, date: str, duration: int, computerId: int, containerId: int, hardwareSpecs, adminReserveUserEmail: str = None, description: str = None, shmSizePercent: int = 50, ramDiskSizePercent: int = 0):
  # Validate description length if provided
  if description and len(description) > 50:
    return Response(False, "Description must be 50 characters or less.")
  
  # Validate SHM size percentage (minimum 10%, maximum 90%)
  if shmSizePercent < 10:
    return Response(False, "SHM size must be at least 10% of allocated memory.")
  if shmSizePercent > 90:
    return Response(False, "SHM size cannot exceed 90% of allocated memory.")
  
  # Validate RAM disk size percentage (minimum 0%, maximum 60%)
  if ramDiskSizePercent < 0:
    return Response(False, "RAM disk size cannot be negative.")
  if ramDiskSizePercent > 60:
    return Response(False, "RAM disk size cannot exceed 60% of allocated memory.")

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

    # Get user's role-based reservation limits
    from database import RoleReservationLimit, UserRole
    user_roles = session.query(UserRole).filter(UserRole.userId == user.userId).all()
    role_ids = [ur.roleId for ur in user_roles]
    
    # Get all reservation limits for user's roles
    role_limits = session.query(RoleReservationLimit).filter(
        RoleReservationLimit.roleId.in_(role_ids)
    ).all() if role_ids else []
    
    # Apply defaults based on whether user is admin
    default_min_duration = 1  # 1 hour for all users
    default_max_duration = 1440 if isAdmin else 48  # 60 days for admin, 48 hours for others
    default_max_active = 99 if isAdmin else 1
    
    # Find the most permissive limits across all roles
    min_duration = default_min_duration
    max_duration = default_max_duration
    max_active_reservations = default_max_active
    
    for limit in role_limits:
        # For min duration, take the lowest value (most permissive)
        if limit.minDuration is not None:
            min_duration = min(min_duration, limit.minDuration)
        
        # For max duration, take the highest value (most permissive)
        if limit.maxDuration is not None:
            max_duration = max(max_duration, limit.maxDuration)
            
        # For max active reservations, take the highest value (most permissive)
        if limit.maxActiveReservations is not None:
            max_active_reservations = max(max_active_reservations, limit.maxActiveReservations)
    
    # Check active reservations limit
    userActiveReservations = session.query(Reservation).filter(
      (Reservation.userId == userId),
      ( (Reservation.status == "reserved") | (Reservation.status == "started") )
    ).count()
    if userActiveReservations >= max_active_reservations:
      return Response(False, f"You can only have {max_active_reservations} active reservation(s) at a time.")
    
    # Validate duration against limits
    if duration < min_duration:
        return Response(False, f"Minimum duration is {min_duration} hours.")
    if duration > max_duration:
        return Response(False, f"Maximum duration is {max_duration} hours.")

    # If adminReserveUserEmail is given, check that the user exists
    if adminReserveUserEmail != None and adminReserveUserEmail != "" and isAdmin == True:
      anotherUser = session.query(User).filter( User.email == adminReserveUserEmail ).first()
      if (anotherUser == None):
        return Response(False, "User for which you tried to reserve for did not exist. Check the email address: " + adminReserveUserEmail)
      user = anotherUser

    # Make sure that there are enough resources for the reservation
    getAvailableHardwareResponse = getAvailableHardware(date.isoformat(), duration, hardwareSpecs, isAdmin, None, user.userId)
    if (getAvailableHardwareResponse["status"] == False):
      return Response(False, getAvailableHardwareResponse["message"])

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

    # Get user's role-based hardware limits
    user_role_limits = {}
    from database import RoleHardwareLimit, UserRole
    user_roles = session.query(UserRole).filter(UserRole.userId == user.userId).all()
    role_ids = [ur.roleId for ur in user_roles]
    
    if role_ids and not isAdmin:
      role_limits = session.query(RoleHardwareLimit).filter(
        RoleHardwareLimit.roleId.in_(role_ids)
      ).all()
      
      # Build a dict of hardwareSpecId -> max limit across all roles
      for limit in role_limits:
        spec_id = limit.hardwareSpecId
        if spec_id not in user_role_limits or limit.maximumAmountForRole > user_role_limits[spec_id]:
          user_role_limits[spec_id] = limit.maximumAmountForRole

    # Add GPU count validation
    total_gpus_requested = 0
    for key, val in hardwareSpecs.items():
      hardwareSpec = session.query(HardwareSpec).filter( HardwareSpec.hardwareSpecId == key ).first()
      if hardwareSpec and hardwareSpec.type == "gpu" and val > 0:
        total_gpus_requested += val
    
    # Validate total GPU count for non-admins (max 1 GPU per reservation)
    if not isAdmin and total_gpus_requested > 1:
      # Check if any role allows more than 1 GPU
      gpu_limit_from_roles = 1
      for key, val in hardwareSpecs.items():
        hardwareSpec = session.query(HardwareSpec).filter( HardwareSpec.hardwareSpecId == key ).first()
        if hardwareSpec and hardwareSpec.type == "gpu" and key in user_role_limits:
          gpu_limit_from_roles = max(gpu_limit_from_roles, user_role_limits[key])
      
      if total_gpus_requested > gpu_limit_from_roles:
        return Response(False, f"You can only reserve {gpu_limit_from_roles} GPU(s) at a time.")
    
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
      if isAdmin == False:
        # Use role-based limit if available, otherwise use default computer limit
        effective_limit = hardwareSpec.maximumAmountForUser
        if int(key) in user_role_limits:
          effective_limit = min(user_role_limits[int(key)], hardwareSpec.maximumAmount)
        
        if val > effective_limit:
          return Response(False, f"Trying to utilize hardware specs above the user maximum amount for {hardwareSpec.type} {hardwareSpec.format}: {val} > {effective_limit}")
      
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
      shmSizePercent = shmSizePercent,
      ramDiskSizePercent = ramDiskSizePercent,
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

    reservation = session.query(Reservation)\
      .options(joinedload(Reservation.reservedHardwareSpecs).joinedload(ReservedHardwareSpec.hardwareSpec))\
      .filter( Reservation.reservationId == reservationId ).first()
    if reservation is None: return Response(False, "No reservation found.")
    
    if reservation.status != "started":
      return Response(False, "Reservation is not started, so cannot extend it.")
    
    # Check that the duration is between minimum and maximum lengths
    if duration < 0 or duration > 24:
      return Response(False, "Duration must be between 0 and 24 hours.")

    # First check if specific GPUs are still available during the extension period
    endTimeString = reservation.endDate.strftime("%Y-%m-%d %H:%M:%S")
    extendedEndDate = reservation.endDate + relativedelta(hours=+duration)
    
    # Check for GPU conflicts specifically
    for spec in reservation.reservedHardwareSpecs:
      if spec.hardwareSpec.type == "gpu" and spec.amount > 0:
        # Check if this specific GPU is reserved by another reservation during the extension period
        conflictingReservation = session.query(Reservation)\
          .join(ReservedHardwareSpec)\
          .filter(
            ReservedHardwareSpec.hardwareSpecId == spec.hardwareSpecId,
            ReservedHardwareSpec.amount > 0,
            Reservation.reservationId != reservationId,
            Reservation.startDate < extendedEndDate,
            Reservation.endDate > reservation.endDate,
            (Reservation.status == "reserved") | (Reservation.status == "started")
          ).first()
        
        if conflictingReservation:
          return Response(False, f"Cannot extend reservation: GPU {spec.hardwareSpec.format} (ID: {spec.hardwareSpec.internalId}) is already reserved by another user during the requested extension period.")

    # Check that there are enough resources for the reservation extension
    # Reducable specs comes from the current reservation
    reducableSpecs = {}
    for spec in reservation.reservedHardwareSpecs:
      reducableSpecs[spec.hardwareSpecId] = spec.amount
    getAvailableHardwareResponse = getAvailableHardware(endTimeString, duration, reducableSpecs, False, reservation.reservationId, reservation.userId)
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
    
    reservation = reservation.first()
    if reservation is None: 
      session.close()
      return Response(False, "No reservation found.")

    if (reservation.status == "started"):
      reservation.status = "restart"
      session.commit()
      session.close()
      return Response(True, "Container will be restarted.")
    else:
      session.close()
      return Response(False, "Reservation is not currently started, so cannot restart the container.")

def getAvailabilityTimeline(startDate: str, endDate: str, isAdmin = False) -> object:
  '''
  Returns availability timeline data for all servers between the given dates.
  This creates continuous availability events showing remaining resources for each server.
  
  Args:
    startDate (str): Start date for the timeline
    endDate (str): End date for the timeline  
    isAdmin (bool): Whether the user is an admin
    
  Returns:
    object: Response object with timeline events for each server
  '''
  try:
    start_date = parser.parse(startDate)
    end_date = parser.parse(endDate)
  except:
    return Response(False, "Invalid date format.")
  
  # Fetch all computers and reservations in the time range
  with Session() as session:
    computers = session.query(Computer)\
      .options(joinedload(Computer.hardwareSpecs))\
      .filter(Computer.removed.isnot(True), Computer.public.is_(True))\
      .all()
    
    reservations = session.query(Reservation)\
      .options(
        joinedload(Reservation.reservedHardwareSpecs).joinedload(ReservedHardwareSpec.hardwareSpec),
        joinedload(Reservation.computer)
      )\
      .filter(
        Reservation.startDate < end_date,
        Reservation.endDate > start_date,
        (Reservation.status == "reserved") | (Reservation.status == "started")
      ).all()
    
    # Process all data before closing session
    timeline_events = []
    
    for computer in computers:
      # Get all time points where availability changes for this computer (reservation start/end times)
      time_points = set([start_date, end_date])
      for res in reservations:
        if res.computer.computerId == computer.computerId:
          if res.startDate > start_date:
            time_points.add(res.startDate)
          if res.endDate < end_date:
            time_points.add(res.endDate)
          if res.startDate < start_date and res.endDate > start_date:
            time_points.add(start_date)
          if res.startDate < end_date and res.endDate > end_date:
            time_points.add(end_date)
      
      time_points = sorted(list(time_points))
      
      # If there are no reservations for this computer, we still want to show full availability
      # So we'll have at least one period from start_date to end_date
      if len(time_points) == 2:  # Only start_date and end_date
        time_points = [start_date, end_date]
      
      # Create availability periods between time points
      for i in range(len(time_points) - 1):
        period_start = time_points[i]
        period_end = time_points[i + 1]
        
        # Calculate available resources for this period
        available_specs = {}
        # Group specs by type, consolidating GPUs without internalId
        spec_groups = {}
        
        for spec in computer.hardwareSpecs:
          # For GPUs, only include those without internalId (consolidated view)
          if spec.type == 'gpu' and spec.internalId is not None:
            continue
            
          if spec.type not in spec_groups:
            spec_groups[spec.type] = {
              'type': spec.type,
              'format': spec.format,
              'available': 0,
              'maximum': 0,
              'hardwareSpecIds': []
            }
          
          spec_groups[spec.type]['available'] += spec.maximumAmount
          spec_groups[spec.type]['maximum'] += spec.maximumAmount
          spec_groups[spec.type]['hardwareSpecIds'].append(spec.hardwareSpecId)
        
        # Convert groups back to available_specs format
        for group_key, group_data in spec_groups.items():
          # Use the first hardwareSpecId as the key for this group
          primary_spec_id = group_data['hardwareSpecIds'][0]
          available_specs[primary_spec_id] = {
            'type': group_data['type'],
            'format': group_data['format'],
            'available': group_data['available'],
            'maximum': group_data['maximum'],
            'relatedSpecIds': group_data['hardwareSpecIds']
          }
        
        # Subtract resources used by overlapping reservations
        for res in reservations:
          if (res.computer.computerId == computer.computerId and 
              res.startDate < period_end and res.endDate > period_start):
            for reserved_spec in res.reservedHardwareSpecs:
              spec_id = reserved_spec.hardwareSpecId
              
              # Find which group this spec_id belongs to
              for group_spec_id, group_data in available_specs.items():
                if spec_id in group_data.get('relatedSpecIds', [group_spec_id]):
                  available_specs[group_spec_id]['available'] -= reserved_spec.amount
                  if available_specs[group_spec_id]['available'] < 0:
                    available_specs[group_spec_id]['available'] = 0
                  break
        
        # Create display text for available resources (no server name in resource text)
        resource_text = ""
        total_capacity = 0
        available_capacity = 0
        
        for spec_data in available_specs.values():
          if spec_data['type'] == 'gpu':
            resource_text += f"GPU: {int(spec_data['available'])}/{int(spec_data['maximum'])}<br>"
          elif spec_data['type'] == 'cpu':
            resource_text += f"CPU: {int(spec_data['available'])}/{int(spec_data['maximum'])}<br>"
          elif spec_data['type'] == 'ram':
            resource_text += f"RAM: {int(spec_data['available'])}/{int(spec_data['maximum'])} {spec_data['format']}<br>"
          else:
            resource_text += f"{spec_data['type'].upper()}: {int(spec_data['available'])}/{int(spec_data['maximum'])}<br>"
          
          total_capacity += spec_data['maximum']
          available_capacity += spec_data['available']
        
        # Determine availability level for color coding
        availability_ratio = available_capacity / max(total_capacity, 1)
        if availability_ratio > 0.75:
          availability_level = 'high'
        elif availability_ratio > 0.25:
          availability_level = 'medium'
        else:
          availability_level = 'low'
        
        # Generate consistent color for server based on server name hash
        import hashlib
        server_hash = int(hashlib.md5(computer.name.encode()).hexdigest(), 16)
        server_colors = ['#1976D2', '#388E3C', '#F57C00', '#7B1FA2', '#D32F2F', '#0097A7', '#5D4037', '#455A64', '#E64A19', '#303F9F']
        server_color = server_colors[server_hash % len(server_colors)]
        
        timeline_events.append({
          'name': f"{computer.name} - {availability_level.title()} Availability",
          'start': period_start.isoformat(),
          'end': period_end.isoformat(),
          'color': server_color,
          'timed': True,
          'type': 'availability',
          'computerId': computer.computerId,
          'computerName': computer.name,
          'availabilityLevel': availability_level,
          'availabilityRatio': availability_ratio,
          'resourceText': resource_text.rstrip('<br>'),
          'availableSpecs': available_specs
        })
    
    session.close()
  
  return Response(True, "Availability timeline fetched.", {'events': timeline_events})

def getAllReservationsForCalendar(startDate: str, endDate: str) -> object:
  '''
  Returns all reservations within a date range for calendar display.
  This includes all reservations regardless of status (reserved, started, stopped, etc.)
  
  Args:
    startDate (str): Start date for the query
    endDate (str): End date for the query
    
  Returns:
    object: Response object with all reservations in the date range
  '''
  try:
    start_date = parser.parse(startDate)
    end_date = parser.parse(endDate)
  except:
    return Response(False, "Invalid date format.")
  
  reservations = []

  with Session() as session:
    query = session.query(Reservation)\
      .options(
        joinedload(Reservation.reservedHardwareSpecs).joinedload(ReservedHardwareSpec.hardwareSpec),
        joinedload(Reservation.computer)
      )\
      .filter(
        Reservation.startDate < end_date,
        Reservation.endDate > start_date
      )
    
    for reservation in query:
      specs = []
      for spec in reservation.reservedHardwareSpecs:
        if spec.amount > 0:
          # Add also internalId for GPUs
          if spec.hardwareSpec.type == "gpu":
            format = f"{spec.hardwareSpec.format} (id: {spec.hardwareSpec.internalId})"
          else:
            format = spec.hardwareSpec.format

          specs.append({
            "type": spec.hardwareSpec.type,
            "format": format,
            "amount": spec.amount
          })
      
      reservations.append({
        "reservationId": reservation.reservationId,
        "startDate": reservation.startDate.isoformat(),
        "endDate": reservation.endDate.isoformat(),
        "computerName": reservation.computer.name,
        "hardwareSpecs": specs,
        "status": reservation.status
      })
    
    session.close()
  
  return Response(True, "All reservations fetched.", {"reservations": reservations})
