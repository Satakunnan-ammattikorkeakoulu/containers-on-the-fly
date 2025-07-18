from database import Session, Computer, ContainerPort, User, Reservation, Container, ReservedContainer, ReservedHardwareSpec, HardwareSpec
from dateutil import parser
from dateutil.relativedelta import *
from datetime import timezone, timedelta
from helpers.server import Response, ORMObjectToDict
import datetime
from endpoints.models.admin import ContainerEdit, ComputerEdit
from endpoints.models.reservation import ReservationFilters
from sqlalchemy.orm import joinedload
from logger import log
from helpers.auth import HashPassword, IsCorrectPassword
import base64
from endpoints.models.admin import UserEdit
from database import UserRole, Role

def getReservations(filters : ReservationFilters) -> object:
  '''
  Returns a list of all reservations.

  Args:
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
        joinedload(Reservation.reservedContainer).joinedload(ReservedContainer.container)
      )\
      .filter(Reservation.startDate > minStartDate )
    if filters.filters["status"] != "":
      query = query.filter( Reservation.status == filters.filters["status"] )
    session.close()

  for reservation in query:
    res = ORMObjectToDict(reservation)
    res["userEmail"] = reservation.user.email
    res["reservedContainer"] = ORMObjectToDict(reservation.reservedContainer)
    res["reservedContainer"]["container"] = ORMObjectToDict(reservation.reservedContainer.container)
    
    # Add all reserved ports
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
    
  return Response(True, "Reservations fetched.", { "reservations": reservations })

def saveContainer(containerEdit : ContainerEdit) -> object:
  '''
  Edits the given container.

  Parameters:
    containerId: id of the container to edit.
    data: New data for the container.
  
  Returns:
    object: Response object with status, message and data.

  '''

  with Session() as session:
    # If new, create a new container
    if containerEdit.containerId == -1:
      container = Container()
      container.public = containerEdit.data.get("public", False)
      container.name = containerEdit.data.get("name")
      container.imageName = containerEdit.data.get("imageName")
      container.description = containerEdit.data.get("description", "")
      # Add ports
      for port in containerEdit.data.get("ports", []):
        container.containerPorts.append(ContainerPort(port=port["port"], serviceName=port["serviceName"]))
      session.add(container)
      session.commit()
    # Otherwise, edit container
    else:
      container = session.query(Container).filter(Container.containerId == containerEdit.containerId).first()
      if container is None:
        return Response(False, "Container not found.")
      else:
        container.public = containerEdit.data.get("public", False)
        container.name = containerEdit.data.get("name")
        container.imageName = containerEdit.data.get("imageName")
        container.description = containerEdit.data.get("description", "")
        container.updatedAt = datetime.datetime.now(datetime.timezone.utc)
        # Remove all removable ports
        for port in containerEdit.data.get("removedPorts", []):
          session.query(ContainerPort).filter(ContainerPort.containerPortId == port).delete()
        # Add all new ports
        for port in containerEdit.data.get("ports", []):
          if "containerPortId" not in port:
            container.containerPorts.append(ContainerPort(port=port["port"], serviceName=port["serviceName"]))
        # Edit changed ports
        for port in containerEdit.data.get("ports", []):
          if "containerPortId" in port:
            oldPort = session.query(ContainerPort).filter(ContainerPort.containerPortId == port["containerPortId"]).first()
            if oldPort.port != port["port"] or oldPort.serviceName != port["serviceName"]:
              oldPort.port = port["port"]
              oldPort.serviceName = port["serviceName"]
              oldPort.updatedAt = datetime.datetime.now(datetime.timezone.utc)

        #for port in containerEdit.data.get("ports", []):
        #  container.containerPorts.append(ContainerPort(port=port["port"], serviceName=port["serviceName"]))
        session.commit()
  return Response(True, "Container saved successfully")

def removeContainer(containerId : int) -> object:
  '''
  Removes the given container.

  Parameters:
    containerId: id of the container to remove.
  
  Returns:
    object: Response object with status, message and data.
  '''

  with Session() as session:
    container = session.query(Container).filter(Container.containerId == containerId).first()
    if container is None:
      return Response(False, "Container not found.")
    else:
      container.removed = True
      container.public = False
      session.commit()
  
  return Response(True, "Container removed successfully")

def getUsers() -> object:
    '''
    Returns a list of all users.

    Returns:
        object: Response object with status, message and data.
    '''
    data = []

    with Session() as session:
        query = session.query(User)
        for user in query:
            addable = {}
            addable["userId"] = user.userId
            addable["email"] = user.email
            addable["roles"] = [role.name for role in user.roles]
            addable["createdAt"] = user.userCreatedAt  # Added createdAt field
            data.append(addable)

    return Response(True, "Users fetched successfully", {"users": data})

def getUser(userId: int) -> object:
    '''
    Returns a single user.

    Parameters:
        userId: id of the user to fetch.

    Returns:
        object: Response object with status, message and data.
    '''
    data = {}

    with Session() as session:
        user = session.query(User).filter(User.userId == userId).first()
        if user is None:
            return Response(False, "User not found")
        
        data = {
            "userId": user.userId,
            "email": user.email,
            "roles": [role.name for role in user.roles],  # Changed from role.role to role.name
            "createdAt": user.userCreatedAt
        }

    return Response(True, "User fetched successfully", {"user": data})

def saveUser(userId: int, data: dict) -> object:
    '''
    Saves user data.

    Parameters:
        userId: id of the user to save (-1 for new user)
        data: dictionary containing user data to save

    Returns:
        object: Response object with status and message
    '''
    with Session() as session:
        # Check if email already exists
        existing_user = session.query(User).filter(User.email == data["email"]).first()
        if existing_user is not None and (userId == -1 or existing_user.userId != userId):
            return Response(False, "A user with this email already exists")

        if userId == -1:
            # Create new user
            hash = HashPassword(data["password"])
            user = User(
                email=data["email"],
                password=base64.b64encode(hash["hashedPassword"]).decode('utf-8'),
                passwordSalt=base64.b64encode(hash["salt"]).decode('utf-8')
            )
            session.add(user)
            session.flush()  # This will populate the userId
            
        else:
            # Update existing user
            user = session.query(User).filter(User.userId == userId).first()
            if user is None:
                return Response(False, "User not found")
            
            user.email = data["email"]
            if "password" in data and data["password"]:
                hash = HashPassword(data["password"])
                user.password = base64.b64encode(hash["hashedPassword"]).decode('utf-8')
                user.passwordSalt = base64.b64encode(hash["salt"]).decode('utf-8')
        
        # Handle roles
        # First remove all existing roles
        user.roles = []
        session.flush()
        
        # Then add new roles by querying the Role table
        if "roles" in data:
            # Create a set of role names to ensure uniqueness
            role_names = set(data["roles"])
            for roleName in role_names:
                role = session.query(Role).filter(Role.name == roleName).first()
                if role and role not in user.roles:  # Check if role exists and isn't already assigned
                    user.roles.append(role)
        
        session.commit()
        return Response(True, "User saved successfully")

def getHardware() -> object:
  '''
  Returns a list of all hardware.

  Returns:
    object: Response object with status, message and data.
  '''

  data = []

  with Session() as session:
    query = session.query(HardwareSpec)
    for hardware in query:
      addable = {}
      addable = ORMObjectToDict(hardware)
      data.append(addable)
  
  return Response(True, "Data fetched.", { "hardware": data })

def getContainers() -> object:
  '''
  Returns a list of all containers which have not been removed.

  Returns:
    object: Response object with status, message and data.
  '''

  data = []

  with Session() as session:
    # Find all where Container.removed is not True
    query = session.query(Container).filter(Container.removed.isnot(True))
    for container in query:
      addable = {}
      addable = ORMObjectToDict(container)
      addable["ports"] = []
      for port in container.containerPorts:
        addable["ports"].append({
          "containerPortId": port.containerPortId,
          "port": port.port,
          "serviceName": port.serviceName,
        })
      data.append(addable)
  
  return Response(True, "Data fetched.", { "containers": data })

def getContainer(containerId : int) -> object:
  '''
  Returns the given container.

  Parameters:
    containerId: id of the container to fetch.

  Returns:
    object: Response object with status, message and data.
  '''

  addable = {}

  with Session() as session:
    query = session.query(Container).filter(Container.containerId == containerId).limit(1)
    for container in query:
      addable = {}
      addable = ORMObjectToDict(container)
      addable["ports"] = []
      for port in container.containerPorts:
        addable["ports"].append({
          "containerPortId": port.containerPortId,
          "port": port.port,
          "serviceName": port.serviceName,
        })
  
  return Response(True, "Data fetched.", { "data": addable })

def getComputers() -> object:
  '''
  Returns a list of all computers.

  Returns:
    object: Response object with status, message and data.
  '''

  data = []

  with Session() as session:
    query = session.query(Computer).filter(Computer.removed.isnot(True))
    for computer in query:
      addable = {}
      addable = ORMObjectToDict(computer)
      addable["hardwareSpecs"] = []
      for spec in computer.hardwareSpecs:
        addable["hardwareSpecs"].append(ORMObjectToDict(spec))
      data.append(addable)
  
  return Response(True, "Data fetched.", { "computers": data })

def getComputer(computerId : int) -> object:
  '''
  Returns a single computer.

  Parameters:
    computerId: id of the computer to fetch.

  Returns:
    object: Response object with status, message and data.
  '''

  data = {}

  with Session() as session:
    query = session.query(Computer).filter( Computer.computerId == computerId ).limit(1)
    for computer in query:
      addable = {}
      addable = ORMObjectToDict(computer)
      addable["hardware"] = {}
      addable["hardware"]["gpus"] = []
      for spec in computer.hardwareSpecs:
        if spec.type == "cpus":
          addable["hardware"]["cpu"] = ORMObjectToDict(spec)
        if spec.type == "ram":
          addable["hardware"]["ram"] = ORMObjectToDict(spec)
        if spec.type == "gpus":
          addable["hardware"]["gpu"] = ORMObjectToDict(spec)
        if spec.type == "gpu":
          addable["hardware"]["gpus"].append(ORMObjectToDict(spec))
        #print(ORMObjectToDict(spec))
        #addable["hardwareSpecs"].append(ORMObjectToDict(spec))
      data = addable

  return Response(True, "Data fetched.", { "data": data })

def saveComputer(computerEdit : ComputerEdit) -> object:
  '''
  Edits the given computer.

  Parameters:
    computerId: id of the computer to edit.
    data: New data for the computer.
  
  Returns:
    object: Response object with status, message and data.

  '''
  
  with Session() as session:
    # If new, create a new computer
    if computerEdit.computerId == -1:
      hardware = computerEdit.data.get("hardware")
      computer = Computer()
      computer.public = computerEdit.data.get("public", False)
      computer.name = computerEdit.data.get("name")
      computer.ip = computerEdit.data.get("ip")
      # Add hardware specs
      cpu = HardwareSpec(
        type = "cpus",
        format = "CPUs",
        maximumAmount = hardware.get("cpu").get("maximumAmount"),
        minimumAmount = hardware.get("cpu").get("minimumAmount"),
        maximumAmountForUser = hardware.get("cpu").get("maximumAmountForUser"),
        defaultAmountForUser = hardware.get("cpu").get("defaultAmountForUser"),
      )
      computer.hardwareSpecs.append(cpu)
      ram = HardwareSpec(
        type = "ram",
        format = "GB",
        maximumAmount = hardware.get("ram").get("maximumAmount"),
        minimumAmount = hardware.get("ram").get("minimumAmount"),
        maximumAmountForUser = hardware.get("ram").get("maximumAmountForUser"),
        defaultAmountForUser = hardware.get("ram").get("defaultAmountForUser"),
      )
      computer.hardwareSpecs.append(ram)
      gpus = HardwareSpec(
        type = "gpus",
        format = "GB",
        maximumAmount = len(hardware.get("gpus")),
        minimumAmount = 0,
        defaultAmountForUser = 0,
        maximumAmountForUser = hardware.get("gpu").get("maximumAmountForUser"),
      )
      computer.hardwareSpecs.append(gpus)
      # Add GPUs
      for gpu in hardware.get("gpus"):
        gpuSpec = HardwareSpec(
          type = "gpu",
          format = gpu.get("format", ""),
          maximumAmount = 1,
          minimumAmount = 0,
          defaultAmountForUser = 0,
          maximumAmountForUser = 1,
          internalId = gpu.get("internalId", ""))
        computer.hardwareSpecs.append(gpuSpec)
      session.add(computer)
      session.commit()
    # Otherwise, edit computer
    else:
      log.debug(computerEdit.data.get("hardware").get("gpus"))
      computer = session.query(Computer).filter(Computer.computerId == computerEdit.computerId).first()
      if computer is None:
        return Response(False, "Computer not found.")
      else:
        computer.public = computerEdit.data.get("public", False)
        computer.name = computerEdit.data.get("name")
        computer.ip = computerEdit.data.get("ip")
        computer.updatedAt = datetime.datetime.now(datetime.timezone.utc)
        # Update hardware specs
        for spec in computer.hardwareSpecs:
          if spec.type == "cpus":
            spec.maximumAmount = computerEdit.data.get("hardware").get("cpu").get("maximumAmount")
            spec.minimumAmount = computerEdit.data.get("hardware").get("cpu").get("minimumAmount")
            spec.maximumAmountForUser = computerEdit.data.get("hardware").get("cpu").get("maximumAmountForUser")
            spec.defaultAmountForUser = computerEdit.data.get("hardware").get("cpu").get("defaultAmountForUser")
          if spec.type == "ram":
            spec.maximumAmount = computerEdit.data.get("hardware").get("ram").get("maximumAmount")
            spec.minimumAmount = computerEdit.data.get("hardware").get("ram").get("minimumAmount")
            spec.maximumAmountForUser = computerEdit.data.get("hardware").get("ram").get("maximumAmountForUser")
            spec.defaultAmountForUser = computerEdit.data.get("hardware").get("ram").get("defaultAmountForUser")
          if spec.type == "gpus":
            spec.maximumAmount = len(computerEdit.data.get("hardware").get("gpus"))
            spec.maximumAmountForUser = computerEdit.data.get("hardware").get("gpu").get("maximumAmountForUser")
        # Remove all removable GPUs
        for spec in computerEdit.data.get("removedGPUs", []):
          session.query(HardwareSpec).filter(HardwareSpec.hardwareSpecId == spec).delete()
        # Add all new GPUs
        for gpu in computerEdit.data.get("hardware").get("gpus", []):
          if "hardwareSpecId" not in gpu:
            computer.hardwareSpecs.append(HardwareSpec(
              type = "gpu",
              format = gpu.get("format", ""),
              internalId = gpu.get("internalId", ""),
              maximumAmount = 1,
              minimumAmount = 0,
              defaultAmountForUser = 0,
              maximumAmountForUser = 1,
            ))
        # Edit changed GPUs
        for gpu in computerEdit.data.get("hardware").get("gpus", []):
          if "hardwareSpecId" in gpu:
            oldGPU = session.query(HardwareSpec).filter(HardwareSpec.hardwareSpecId == gpu["hardwareSpecId"]).first()
            if oldGPU.format != gpu["format"] or oldGPU.internalId != gpu["internalId"]:
              oldGPU.format = gpu["format"]
              oldGPU.internalId = gpu["internalId"]
              oldGPU.updatedAt = datetime.datetime.now(datetime.timezone.utc)

        #for port in containerEdit.data.get("ports", []):
        #  container.containerPorts.append(ContainerPort(port=port["port"], serviceName=port["serviceName"]))
        session.commit()
  return Response(True, "Computer saved successfully")

def removeComputer(computerId : int) -> object:
  '''
  Removes the given computer.

  Parameters:
    computerId: id of the computer to remove.
  
  Returns:
    object: Response object with status, message and data.
  '''

  with Session() as session:
    computer = session.query(Computer).filter(Computer.computerId == computerId).first()
    if computer is None:
      return Response(False, "Computer not found.")
    else:
      computer.removed = True
      computer.public = False
      session.commit()
  
  return Response(True, "Computer removed successfully")

def editReservation(reservationId : int, endDate : str) -> object:
  '''
  Edits the given reservation.

  Parameters:
    reservationId: id of the reservation to edit.
    endDate: New end date for the reservation.

  Returns:
    object: Response object with status, message and data.
  '''
  # Verify that the new end date is valid
  try:
    endDate = parser.parse(endDate)
  except:
    return Response(False, "Invalid end date.")

  with Session() as session:
    reservation = session.query(Reservation).filter(Reservation.reservationId == reservationId).first()
    if reservation is None:
      return Response(False, "Reservation not found.")
    else:
      reservation.endDate = endDate
      session.commit()

  return Response(True, "Reservation was edited succesfully.")