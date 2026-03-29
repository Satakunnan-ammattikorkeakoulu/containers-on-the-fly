from database import Session, Computer, ContainerPort, User, Reservation, Container, ReservedContainer, ReservedHardwareSpec, HardwareSpec, UserRole, Role, ServerStatus, ServerLogs
from dateutil import parser
from dateutil.relativedelta import *
from datetime import timezone, timedelta
from helpers.server import api_response, orm_to_dict
import datetime
from endpoints.models.admin import ContainerEdit, ComputerEdit
from endpoints.models.reservation import ReservationFilters
from sqlalchemy.orm import joinedload
from logger import log
from helpers.auth import hash_password, is_correct_password
import base64
from endpoints.models.admin import UserEdit
from database import UserRole, Role
from helpers.tables.role import get_roles, get_role_by_id, add_role as add_role_helper, edit_role as edit_role_helper, remove_role as remove_role_helper
from sqlalchemy import func

def get_reservations(filters : ReservationFilters) -> object:
  '''
  Returns a list of all reservations.

  Args:
    filters (ReservationFilters): The filters to apply to the query.

  Returns:
    object: Response object with status, message and data.
  '''
  reservations = []
  status_counts = {"reserved": 0, "started": 0, "stopped": 0, "error": 0}

  # Limit listing to 90 days
  def time_now(): return datetime.datetime.now(datetime.timezone.utc)
  min_start_date = time_now() - timedelta(days=90)

  with Session() as session:
    # First get all reservations for counting
    count_query = session.query(Reservation)\
      .filter((Reservation.startDate > min_start_date) | (Reservation.endDate > time_now()) )
    
    # Count statuses
    for reservation in count_query:
      if reservation.status in status_counts:
        status_counts[reservation.status] += 1
    
    # Now get filtered reservations with all the joins
    query = session.query(Reservation)\
      .options(
        joinedload(Reservation.reservedHardwareSpecs),
        joinedload(Reservation.reservedContainer).joinedload(ReservedContainer.reservedContainerPorts),
        joinedload(Reservation.reservedContainer).joinedload(ReservedContainer.container),
        joinedload(Reservation.computer)
      )\
      .filter((Reservation.startDate > min_start_date) | (Reservation.endDate > time_now()) )
    if filters.filters["status"] != "":
      query = query.filter( Reservation.status == filters.filters["status"] )
    session.close()

  for reservation in query:
    res = orm_to_dict(reservation)
    res["userEmail"] = reservation.user.email
    res["computerName"] = reservation.computer.name
    res["reservedContainer"] = orm_to_dict(reservation.reservedContainer)
    res["reservedContainer"]["container"] = orm_to_dict(reservation.reservedContainer.container)
    
    # Add all reserved ports
    res["reservedContainer"]["reservedPorts"] = []
    # Only add ports if the reservation is started as the ports are unbound after the reservation is stopped
    if reservation.status == "started":
      for reserved_port in reservation.reservedContainer.reservedContainerPorts:
        port_obj = orm_to_dict(reserved_port)
        port_obj["localPort"] = reserved_port.containerPort.port
        port_obj["serviceName"] = reserved_port.containerPort.serviceName
        res["reservedContainer"]["reservedPorts"].append(port_obj)
    
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
    
  return api_response(True, "Reservations fetched.", { "reservations": reservations, "statusCounts": status_counts })

def save_container(containerEdit : ContainerEdit) -> object:
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
        return api_response(False, "Container not found.")
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
            old_port = session.query(ContainerPort).filter(ContainerPort.containerPortId == port["containerPortId"]).first()
            if old_port.port != port["port"] or old_port.serviceName != port["serviceName"]:
              old_port.port = port["port"]
              old_port.serviceName = port["serviceName"]
              old_port.updatedAt = datetime.datetime.now(datetime.timezone.utc)

        #for port in containerEdit.data.get("ports", []):
        #  container.containerPorts.append(ContainerPort(port=port["port"], serviceName=port["serviceName"]))
        session.commit()
  return api_response(True, "Container saved successfully")

def remove_container(containerId : int) -> object:
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
      return api_response(False, "Container not found.")
    else:
      container.removed = True
      container.public = False
      session.commit()
  
  return api_response(True, "Container removed successfully")

def get_users() -> object:
    '''
    Returns a list of all users and available roles.

    Returns:
        object: Response object with status, message and data.
    '''
    data = []
    role_user_counts = {}

    with Session() as session:
        query = session.query(User)
        for user in query:
            addable = {}
            addable["userId"] = user.userId
            addable["email"] = user.email
            addable["roles"] = [role.name for role in user.roles]
            addable["createdAt"] = user.userCreatedAt  # Added createdAt field
            addable["hasPassword"] = user.password is not None and user.password != ""
            data.append(addable)
            
            # Count users per role
            for role in user.roles:
                if role.name not in role_user_counts:
                    role_user_counts[role.name] = 0
                role_user_counts[role.name] += 1

    # Get available roles
    from helpers.tables.role import get_roles_with_mount_counts
    available_roles = get_roles_with_mount_counts()

    # Add user counts to each role
    for role in available_roles:
        role["userCount"] = role_user_counts.get(role["name"], 0)

    return api_response(True, "Users fetched successfully", {"users": data, "availableRoles": available_roles})

def get_user(userId: int) -> object:
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
            return api_response(False, "User not found")
        
        data = {
            "userId": user.userId,
            "email": user.email,
            "roles": [role.name for role in user.roles],  # Changed from role.role to role.name
            "createdAt": user.userCreatedAt
        }

    return api_response(True, "User fetched successfully", {"user": data})

def save_user(userId: int, data: dict) -> object:
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
            return api_response(False, "A user with this email already exists")

        if userId == -1:
            # Create new user
            hash = hash_password(data["password"])
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
                return api_response(False, "User not found")
            
            user.email = data["email"]
            
            # Check if we should clear the password
            if "clearPassword" in data and data["clearPassword"]:
                # Clear both password and salt
                user.password = ""
                user.passwordSalt = ""
            elif "password" in data and data["password"]:
                # Update password only if provided and not clearing
                hash = hash_password(data["password"])
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
            for role_name in role_names:
                role = session.query(Role).filter(Role.name == role_name).first()
                if role and role not in user.roles:  # Check if role exists and isn't already assigned
                    user.roles.append(role)
        
        session.commit()
        return api_response(True, "User saved successfully")

def get_hardware() -> object:
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
      addable = orm_to_dict(hardware)
      data.append(addable)
  
  return api_response(True, "Data fetched.", { "hardware": data })

def get_containers() -> object:
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
      addable = orm_to_dict(container)
      addable["ports"] = []
      for port in container.containerPorts:
        addable["ports"].append({
          "containerPortId": port.containerPortId,
          "port": port.port,
          "serviceName": port.serviceName,
        })
      data.append(addable)
  
  return api_response(True, "Data fetched.", { "containers": data })

def get_container(containerId : int) -> object:
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
      addable = orm_to_dict(container)
      addable["ports"] = []
      for port in container.containerPorts:
        addable["ports"].append({
          "containerPortId": port.containerPortId,
          "port": port.port,
          "serviceName": port.serviceName,
        })
  
  return api_response(True, "Data fetched.", { "data": addable })

def get_computers() -> object:
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
      addable = orm_to_dict(computer)
      addable["hardwareSpecs"] = []
      for spec in computer.hardwareSpecs:
        addable["hardwareSpecs"].append(orm_to_dict(spec))
      data.append(addable)
  
  return api_response(True, "Data fetched.", { "computers": data })

def get_computer(computerId : int) -> object:
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
      addable = orm_to_dict(computer)
      addable["hardware"] = {}
      addable["hardware"]["gpus"] = []
      for spec in computer.hardwareSpecs:
        if spec.type == "cpus":
          addable["hardware"]["cpu"] = orm_to_dict(spec)
        if spec.type == "ram":
          addable["hardware"]["ram"] = orm_to_dict(spec)
        if spec.type == "gpus":
          addable["hardware"]["gpu"] = orm_to_dict(spec)
        if spec.type == "gpu":
          addable["hardware"]["gpus"].append(orm_to_dict(spec))
        #print(orm_to_dict(spec))
        #addable["hardwareSpecs"].append(orm_to_dict(spec))
      data = addable

  return api_response(True, "Data fetched.", { "data": data })

def save_computer(computerEdit : ComputerEdit) -> object:
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
        gpu_spec = HardwareSpec(
          type = "gpu",
          format = gpu.get("format", ""),
          maximumAmount = 1,
          minimumAmount = 0,
          defaultAmountForUser = 0,
          maximumAmountForUser = 1,
          internalId = gpu.get("internalId", ""))
        computer.hardwareSpecs.append(gpu_spec)
      session.add(computer)
      session.commit()
    # Otherwise, edit computer
    else:
      log.debug(computerEdit.data.get("hardware").get("gpus"))
      computer = session.query(Computer).filter(Computer.computerId == computerEdit.computerId).first()
      if computer is None:
        return api_response(False, "Computer not found.")
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
          session.query(ReservedHardwareSpec).filter(ReservedHardwareSpec.hardwareSpecId == spec).delete()
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
            old_gpu = session.query(HardwareSpec).filter(HardwareSpec.hardwareSpecId == gpu["hardwareSpecId"]).first()
            if old_gpu.format != gpu["format"] or old_gpu.internalId != gpu["internalId"]:
              old_gpu.format = gpu["format"]
              old_gpu.internalId = gpu["internalId"]
              old_gpu.updatedAt = datetime.datetime.now(datetime.timezone.utc)

        #for port in containerEdit.data.get("ports", []):
        #  container.containerPorts.append(ContainerPort(port=port["port"], serviceName=port["serviceName"]))
        session.commit()
  return api_response(True, "Computer saved successfully")

def remove_computer(computerId : int) -> object:
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
      return api_response(False, "Computer not found.")
    else:
      computer.removed = True
      computer.public = False
      session.commit()
  
  return api_response(True, "Computer removed successfully")

def edit_reservation(reservationId : int, end_date_str : str) -> object:
  '''
  Edits the given reservation.

  Parameters:
    reservationId: id of the reservation to edit.
    end_date_str: New end date for the reservation.

  Returns:
    object: Response object with status, message and data.
  '''
  # Verify that the new end date is valid
  try:
    parsed_end_date = parser.parse(end_date_str)
  except:
    return api_response(False, "Invalid end date.")

  with Session() as session:
    reservation = session.query(Reservation).filter(Reservation.reservationId == reservationId).first()
    if reservation is None:
      return api_response(False, "Reservation not found.")
    else:
      reservation.endDate = parsed_end_date
      session.commit()

  return api_response(True, "Reservation was edited succesfully.")

def get_all_roles() -> object:
    '''
    Returns a list of all roles with mount counts.
    Returns:
        object: Response object with status, message and data.
    '''
    from helpers.tables.role import get_roles_with_mount_counts
    data = get_roles_with_mount_counts()
    
    return api_response(True, "Roles fetched successfully.", {"roles": data})

def add_role(name: str) -> object:
    '''
    Adds a new role.
    Parameters:
        name: The name of the role
    Returns:
        object: Response object with status and message
    '''
    success, message, role_dict = add_role_helper(name)
    if not success:
        return api_response(False, message)
    return api_response(True, message, role_dict)

def edit_role(roleId: int, name: str) -> object:
    '''
    Edits an existing role.
    Parameters:
        roleId: The ID of the role to edit
        name: The new name for the role
    Returns:
        object: Response object with status and message
    '''
    success, message, role_dict = edit_role_helper(roleId, name)
    if not success:
        return api_response(False, message)
    return api_response(True, message, role_dict)

def remove_role(roleId: int) -> object:
    '''
    Removes a role.
    Parameters:
        roleId: The ID of the role to remove
    Returns:
        object: Response object with status and message
    '''
    success, message = remove_role_helper(roleId)
    if not success:
        return api_response(False, message)
    return api_response(True, message)

def get_role_mounts(roleId: int) -> object:
    '''
    Gets all mounts for a specific role.
    
    Parameters:
        roleId: The ID of the role to get mounts for
        
    Returns:
        object: Response object with status, message and data containing mounts
    '''
    try:
        from helpers.tables.role import get_role_mounts as get_role_mounts_helper
        mounts = get_role_mounts_helper(roleId)
        return api_response(True, "Role mounts retrieved successfully", {"mounts": mounts})
    except Exception as e:
        return api_response(False, f"Error retrieving role mounts: {str(e)}")

def save_role_mounts(roleId: int, mounts: list) -> object:
    '''
    Saves role mounts, replacing existing ones.
    
    Parameters:
        roleId: The ID of the role
        mounts: List of mount dictionaries
        
    Returns:
        object: Response object with status and message
    '''
    try:
        from helpers.tables.role import save_role_mounts as save_role_mounts_helper
        success, message = save_role_mounts_helper(roleId, mounts)
        return api_response(success, message)
    except Exception as e:
        return api_response(False, f"Error saving role mounts: {str(e)}")

def get_role_hardware_limits(roleId: int) -> object:
    '''
    Retrieves hardware limits for a specific role.
    
    Parameters:
        roleId: The ID of the role
        
    Returns:
        object: Response object with hardware limits data
    '''
    try:
        from helpers.tables.role import get_role_hardware_limits as get_role_hardware_limits_helper
        limits = get_role_hardware_limits_helper(roleId)
        return api_response(True, "Role hardware limits retrieved successfully", {"hardwareLimits": limits})
    except Exception as e:
        return api_response(False, f"Error retrieving role hardware limits: {str(e)}")

def save_role_hardware_limits(roleId: int, hardwareLimits: list) -> object:
    '''
    Saves role hardware limits, replacing existing ones.
    
    Parameters:
        roleId: The ID of the role
        hardwareLimits: List of hardware limit dictionaries
        
    Returns:
        object: Response object with status and message
    '''
    try:
        from helpers.tables.role import save_role_hardware_limits as save_role_hardware_limits_helper
        success, message = save_role_hardware_limits_helper(roleId, hardwareLimits)
        return api_response(success, message)
    except Exception as e:
        return api_response(False, f"Error saving role hardware limits: {str(e)}")

def get_role_reservation_limits(roleId: int) -> object:
    '''
    Retrieves reservation limits for a specific role.
    
    Parameters:
        roleId: The ID of the role
        
    Returns:
        object: Response object with reservation limits data
    '''
    try:
        from helpers.tables.role import get_role_reservation_limits as get_role_reservation_limits_helper
        limits = get_role_reservation_limits_helper(roleId)
        return api_response(True, "Role reservation limits retrieved successfully", {"reservationLimits": limits})
    except Exception as e:
        return api_response(False, f"Error retrieving role reservation limits: {str(e)}")

def save_role_reservation_limits(roleId: int, reservationLimits: dict) -> object:
    '''
    Saves role reservation limits, replacing existing ones.
    
    Parameters:
        roleId: The ID of the role
        reservationLimits: Dictionary containing minDuration, maxDuration, and maxActiveReservations
        
    Returns:
        object: Response object indicating success or failure
    '''
    try:
        from helpers.tables.role import save_role_reservation_limits as save_role_reservation_limits_helper
        success, message = save_role_reservation_limits_helper(roleId, reservationLimits)
        return api_response(success, message)
    except Exception as e:
        return api_response(False, f"Error saving role reservation limits: {str(e)}")

def get_server_monitoring(computer_id: int) -> object:
    '''
    Returns monitoring data (metrics and logs) for a specific server.
    
    Args:
        computer_id (int): The ID of the computer/server.
        
    Returns:
        object: Response object with server monitoring data.
    '''
    with Session() as session:
        # Check if computer exists
        computer = session.query(Computer).filter(Computer.computerId == computer_id).first()
        if not computer:
            return api_response(False, "Server not found")
        
        # Get server status/metrics
        status = session.query(ServerStatus).filter(
            ServerStatus.computerId == computer_id
        ).first()
        
        # Get server logs
        logs = session.query(ServerLogs).filter(
            ServerLogs.computerId == computer_id
        ).all()
        
        # Build response
        monitoring_data = {
            "computer": {
                "id": computer.computerId,
                "name": computer.name,
                "ip": computer.ip
            },
            "isOnline": status.isOnline if status else False,
            "metrics": None,
            "logs": {}
        }
        
        # Add metrics if available
        if status:
            # Convert uptime seconds to days/hours/minutes
            uptime_days = 0
            uptime_hours = 0 
            uptime_minutes = 0
            
            if status.systemUptimeSeconds:
                uptime_days = status.systemUptimeSeconds // 86400
                uptime_hours = (status.systemUptimeSeconds % 86400) // 3600
                uptime_minutes = (status.systemUptimeSeconds % 3600) // 60
            
            monitoring_data["metrics"] = {
                "cpu": {
                    "usage": status.cpuUsagePercent,
                    "cores": status.cpuCores
                },
                "memory": {
                    "total": status.memoryTotalBytes,
                    "used": status.memoryUsedBytes,
                    "percentage": status.memoryUsagePercent
                },
                "disk": {
                    "total": status.diskTotalBytes,
                    "used": status.diskUsedBytes,
                    "free": status.diskFreeBytes,
                    "percentage": status.diskUsagePercent
                },
                "docker": {
                    "running": status.dockerContainersRunning,
                    "total": status.dockerContainersTotal
                },
                "load": {
                    "avg1": status.loadAvg1Min,
                    "avg5": status.loadAvg5Min,
                    "avg15": status.loadAvg15Min
                },
                "uptime": {
                    "days": uptime_days,
                    "hours": uptime_hours,
                    "minutes": uptime_minutes,
                    "seconds": status.systemUptimeSeconds
                },
                "lastUpdated": status.lastUpdatedAt.isoformat() if status.lastUpdatedAt else None
            }
            
            # Add software version information
            monitoring_data["version"] = {
                "software": status.softwareVersion,
                "updated": status.versionUpdatedAt.isoformat() if status.versionUpdatedAt else None
            }
        
        # Add logs
        for log in logs:
            monitoring_data["logs"][log.logType] = {
                "content": log.logContent or "",
                "lines": log.logLines or 0,
                "lastUpdated": log.lastUpdatedAt.isoformat() if log.lastUpdatedAt else None
            }
        
        return api_response(True, "Server monitoring data retrieved", monitoring_data)

def get_servers_for_monitoring() -> object:
    '''
    Returns a list of all servers/computers available for monitoring.
    
    Returns:
        object: Response object with servers list.
    '''
    with Session() as session:
        computers = session.query(Computer).filter(
            (Computer.removed == False) | (Computer.removed.is_(None))
        ).all()
        
        servers_list = []
        for computer in computers:
            servers_list.append({
                "id": computer.computerId,
                "name": computer.name,
                "address": computer.ip,
                "public": computer.public
            })
        
        return api_response(True, "Servers retrieved successfully", {"servers": servers_list})

def get_general_settings() -> object:
    '''
    Returns all general admin settings with default values if not set.
    
    Returns:
        object: Response object with all settings organized by section.
    '''
    try:
        from settings_handler import get_setting, get_multiple_settings
        from helpers.tables.user_access_control import get_blacklisted_emails, get_whitelisted_emails
        
        # Define all settings with their defaults
        setting_keys = [
            'general.applicationName',
            'general.timezone',
            'instructions.login',
            'instructions.reservation', 
            'instructions.email',
            'instructions.usernameFieldLabel',
            'instructions.passwordFieldLabel',
            'access.blacklistEnabled',
            'access.whitelistEnabled',
            'email.smtpServer',
            'email.smtpPort',
            'email.smtpUsername',
            'email.smtpPassword',
            'email.fromEmail',
            'email.contactEmail',
            'email.sendEmail',
            'notifications.containerAlertsEnabled',
            'notifications.alertEmails',
            'auth.loginType',
            'auth.sessionTimeoutMinutes',
            'auth.ldap.url',
            'auth.ldap.usernameFormat',
            'auth.ldap.passwordFormat',
            'auth.ldap.domain',
            'auth.ldap.searchMethod',
            'auth.ldap.accountField',
            'auth.ldap.emailField'
        ]
        
        # Get all settings
        settings_dict = get_multiple_settings(setting_keys)
        
        # Get email lists
        blacklisted_emails = get_blacklisted_emails()
        whitelisted_emails = get_whitelisted_emails()
        
        # Get alert emails from JSON setting
        alert_emails = settings_dict.get('notifications.alertEmails', [])
        if isinstance(alert_emails, str):
            import json
            try:
                alert_emails = json.loads(alert_emails)
            except:
                alert_emails = []
        
        # Build response with defaults
        response_data = {
            "general": {
                "applicationName": settings_dict.get('general.applicationName', 'Containers on the Fly'),
                "timezone": settings_dict.get('general.timezone', 'UTC'),
                "loginPageInfo": settings_dict.get('instructions.login', ''),
                "reservationPageInstructions": settings_dict.get('instructions.reservation', ''),
                "emailInstructions": settings_dict.get('instructions.email', ''),
                "usernameFieldLabel": settings_dict.get('instructions.usernameFieldLabel', 'Username'),
                "passwordFieldLabel": settings_dict.get('instructions.passwordFieldLabel', 'Password')
            },
            "access": {
                "blacklistEnabled": settings_dict.get('access.blacklistEnabled', False),
                "whitelistEnabled": settings_dict.get('access.whitelistEnabled', False),
                "blacklistedEmails": blacklisted_emails,
                "whitelistedEmails": whitelisted_emails
            },
            "email": {
                "smtpServer": settings_dict.get('email.smtpServer', ''),
                "smtpPort": settings_dict.get('email.smtpPort', 587),
                "smtpUsername": settings_dict.get('email.smtpUsername', ''),
                "smtpPassword": settings_dict.get('email.smtpPassword', ''),
                "fromEmail": settings_dict.get('email.fromEmail', ''),
                "contactEmail": settings_dict.get('email.contactEmail', '')
            },
            "emailEnable": {
                "sendEmail": settings_dict.get('email.sendEmail', False)
            },
            "notifications": {
                "containerAlertsEnabled": settings_dict.get('notifications.containerAlertsEnabled', False),
                "alertEmails": alert_emails
            },
            "auth": {
                "loginType": settings_dict.get('auth.loginType', 'password'),
                "sessionTimeoutMinutes": settings_dict.get('auth.sessionTimeoutMinutes', 1440),
                "ldap": {
                    "url": settings_dict.get('auth.ldap.url', ''),
                    "usernameFormat": settings_dict.get('auth.ldap.usernameFormat', ''),
                    "passwordFormat": settings_dict.get('auth.ldap.passwordFormat', ''),
                    "domain": settings_dict.get('auth.ldap.domain', ''),
                    "searchMethod": settings_dict.get('auth.ldap.searchMethod', ''),
                    "accountField": settings_dict.get('auth.ldap.accountField', ''),
                    "emailField": settings_dict.get('auth.ldap.emailField', '')
                }
            }
        }
        
        return api_response(True, "Settings retrieved successfully", response_data)
        
    except Exception as e:
        return api_response(False, f"Error retrieving settings: {str(e)}")

def save_general_settings(section: str, settings: dict) -> object:
    '''
    Saves general admin settings for a specific section.
    
    Args:
        section: The section to save (general, access, email, notifications, auth)
        settings: Dictionary of settings to save
        
    Returns:
        object: Response object indicating success/failure
    '''
    try:
        from settings_handler import set_setting
        from helpers.tables.user_access_control import set_blacklisted_emails, set_whitelisted_emails
        
        if section == "general":
            # Save general application settings
            if 'applicationName' in settings:
                set_setting('general.applicationName', settings['applicationName'])
            if 'timezone' in settings:
                set_setting('general.timezone', settings['timezone'])
            
            # Save instruction settings using new naming scheme
            if 'loginPageInfo' in settings:
                set_setting('instructions.login', settings['loginPageInfo'])
            if 'reservationPageInstructions' in settings:
                set_setting('instructions.reservation', settings['reservationPageInstructions'])
            if 'emailInstructions' in settings:
                set_setting('instructions.email', settings['emailInstructions'])
            if 'usernameFieldLabel' in settings:
                set_setting('instructions.usernameFieldLabel', settings['usernameFieldLabel'])
            if 'passwordFieldLabel' in settings:
                set_setting('instructions.passwordFieldLabel', settings['passwordFieldLabel'])
                
        elif section == "access":
            # Save access control settings
            if 'blacklistEnabled' in settings:
                set_setting('access.blacklistEnabled', settings['blacklistEnabled'])
            if 'whitelistEnabled' in settings:
                set_setting('access.whitelistEnabled', settings['whitelistEnabled'])
            if 'blacklistedEmails' in settings:
                set_blacklisted_emails(settings['blacklistedEmails'])
            if 'whitelistedEmails' in settings:
                set_whitelisted_emails(settings['whitelistedEmails'])
                
        elif section == "email":
            # Save email configuration
            if 'smtpServer' in settings:
                set_setting('email.smtpServer', settings['smtpServer'])
            if 'smtpPort' in settings:
                set_setting('email.smtpPort', settings['smtpPort'])
            if 'smtpUsername' in settings:
                set_setting('email.smtpUsername', settings['smtpUsername'])
            if 'smtpPassword' in settings:
                set_setting('email.smtpPassword', settings['smtpPassword'])
            if 'fromEmail' in settings:
                set_setting('email.fromEmail', settings['fromEmail'])
                
        elif section == "contact":
            # Save contact email separately
            if 'contactEmail' in settings:
                set_setting('email.contactEmail', settings['contactEmail'])
                
        elif section == "emailEnable":
            # Save email enable setting
            if 'sendEmail' in settings:
                set_setting('email.sendEmail', settings['sendEmail'])
                
        elif section == "notifications":
            # Save notification settings
            if 'containerAlertsEnabled' in settings:
                set_setting('notifications.containerAlertsEnabled', settings['containerAlertsEnabled'])
            if 'alertEmails' in settings:
                set_setting('notifications.alertEmails', settings['alertEmails'])
        
        elif section == "auth":
            # Save authentication settings
            if 'loginType' in settings:
                set_setting('auth.loginType', settings['loginType'])
            if 'sessionTimeoutMinutes' in settings:
                timeout = 1440 if not settings['sessionTimeoutMinutes'] else settings['sessionTimeoutMinutes']
                set_setting('auth.sessionTimeoutMinutes', timeout)
                
            # Save LDAP settings if they exist
            if 'ldap' in settings and isinstance(settings['ldap'], dict):
                ldap_settings = settings['ldap']
                if 'url' in ldap_settings:
                    set_setting('auth.ldap.url', ldap_settings['url'])
                if 'usernameFormat' in ldap_settings:
                    set_setting('auth.ldap.usernameFormat', ldap_settings['usernameFormat'])
                if 'passwordFormat' in ldap_settings:
                    set_setting('auth.ldap.passwordFormat', ldap_settings['passwordFormat'])
                if 'domain' in ldap_settings:
                    set_setting('auth.ldap.domain', ldap_settings['domain'])
                if 'searchMethod' in ldap_settings:
                    set_setting('auth.ldap.searchMethod', ldap_settings['searchMethod'])
                if 'accountField' in ldap_settings:
                    set_setting('auth.ldap.accountField', ldap_settings['accountField'])
                if 'emailField' in ldap_settings:
                    set_setting('auth.ldap.emailField', ldap_settings['emailField'])
                
        else:
            return api_response(False, f"Unknown section: {section}")
            
        return api_response(True, f"Settings for {section} saved successfully")
        
    except Exception as e:
        return api_response(False, f"Error saving settings: {str(e)}")

def send_test_email(email: str) -> object:
    '''
    Sends a test email to verify SMTP configuration.
    
    Args:
        email: Email address to send test to
        
    Returns:
        object: Response object indicating success/failure
    '''
    try:
        from settings_handler import get_setting
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        
        # Get SMTP settings
        smtp_server = get_setting('email.smtpServer')
        smtp_port = get_setting('email.smtpPort')
        smtp_username = get_setting('email.smtpUsername')
        smtp_password = get_setting('email.smtpPassword')
        from_email = get_setting('email.fromEmail')
        
        if not all([smtp_server, smtp_port, smtp_username, smtp_password, from_email]):
            return api_response(False, "SMTP configuration is incomplete. Please configure all SMTP settings first.")
        
        # Create message
        msg = MIMEMultipart()
        msg['From'] = from_email
        msg['To'] = email
        msg['Subject'] = "Test Email from Container Reservation System"
        
        body = """
        This is a test email from your Container Reservation System.
        
        If you receive this email, your SMTP configuration is working correctly.
        
        This email was sent from the admin general settings page.
        """
        
        msg.attach(MIMEText(body, 'plain'))
        
        # Send email
        # Use SSL/TLS for port 465, STARTTLS for other ports (typically 587)
        if smtp_port == 465:
            server = smtplib.SMTP_SSL(smtp_server, smtp_port)
        else:
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
        server.login(smtp_username, smtp_password)
        server.send_message(msg)
        server.quit()
        
        return api_response(True, f"Test email sent successfully to {email}")
        
    except Exception as e:
        return api_response(False, f"Failed to send test email: {str(e)}")