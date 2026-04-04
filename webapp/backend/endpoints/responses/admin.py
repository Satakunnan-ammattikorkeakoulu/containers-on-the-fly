"""Response handlers for admin management endpoints.

Provides business logic for administrative operations including reservation
management, container and computer (server) CRUD, user management, role and
permission management, server monitoring, and general application settings.
"""

from database import Session, Computer, ContainerPort, User, Reservation, Container, ReservedContainer, ReservedContainerPort, ReservedHardwareSpec, HardwareSpec, UserRole, Role, ServerStatus, ServerLogs, AuditLog, UserWhitelist, UserBlacklist
from dateutil import parser
from dateutil.relativedelta import *
from datetime import timezone, timedelta
from helpers.server import api_response, orm_to_dict
import datetime
from endpoints.models.admin import ContainerEdit, ComputerEdit
from endpoints.models.reservation import ReservationFilters, AdminReservationRequest, UserReservationRequest
from endpoints.models.admin import AdminUsersRequest
from sqlalchemy.orm import joinedload
from sqlalchemy import cast, String
from helpers.pagination import apply_pagination, get_total_count
from helpers.logger import log
from helpers.auth import hash_password, is_correct_password
from helpers.tables.audit_log import log_action, get_audit_logs as get_audit_logs_helper
import base64
from endpoints.models.admin import UserEdit
from database import UserRole, Role
from helpers.tables.role import get_roles, get_role_by_id, add_role as add_role_helper, edit_role as edit_role_helper, remove_role as remove_role_helper
from sqlalchemy import select, delete, update, func, case
import re

# Valid Linux username pattern
_VALID_USERNAME_RE = re.compile(r'^[a-z_][a-z0-9_-]{0,31}$')
_RESERVED_USERNAMES = {"root", "daemon", "bin", "sys", "nobody", "www-data", "mail", "sshd"}

# Valid Docker image name pattern (lowercase, digits, dots, hyphens, underscores, slashes)
_VALID_IMAGE_NAME_RE = re.compile(r'^[a-z0-9][a-z0-9._/\-]{0,127}$')

# Built-in SSH port — always present on every container
_SSH_SERVICE_NAME = "SSH"
_SSH_PORT = 22

def _ensure_ssh_port(session, container):
  """Ensure container has an SSH port 22 ContainerPort. Idempotent.

  If no ContainerPort with serviceName="SSH" and port=22 exists for this
  container, one is created. Safe to call on both new and existing containers.

  Args:
      session: Active SQLAlchemy session.
      container: Container ORM object to check/fix.
  """
  has_ssh = any(
    p.serviceName == _SSH_SERVICE_NAME and p.port == _SSH_PORT
    for p in container.containerPorts
  )
  if not has_ssh:
    container.containerPorts.append(
      ContainerPort(serviceName=_SSH_SERVICE_NAME, port=_SSH_PORT)
    )

def get_reservations(request: AdminReservationRequest) -> object:
  """Retrieve paginated reservations with server-side filtering and sorting.

  Fetches reservations from the last 90 days (or with future end dates),
  with pagination and filtering support. Also returns unfiltered status
  counts and time-based statistics for the dashboard cards.

  Args:
      request: Pagination, sorting, and filter parameters. Supported
          filter keys: status, reservationId.

  Returns:
      Response with paginated reservations, totalItems, statusCounts,
      and stats.
  """
  filters = request.filters
  status_filter = filters.get("status", "")
  user_filter = str(filters.get("user", "")).strip()
  reservation_id_filter = str(filters.get("reservationId", "")).strip()
  computer_id_filter = filters.get("computerId", "")
  container_id_filter = filters.get("containerId", "")
  date_from_filter = str(filters.get("dateFrom", "")).strip()
  date_to_filter = str(filters.get("dateTo", "")).strip()

  allowed_sort_keys = {
      "reservationId": Reservation.reservationId,
      "status": Reservation.status,
      "userEmail": User.email,
      "startDate": Reservation.startDate,
      "endDate": Reservation.endDate,
  }

  def time_now(): return datetime.datetime.now(datetime.timezone.utc)
  min_start_date = time_now() - timedelta(days=90)
  time_scope = (Reservation.startDate > min_start_date) | (Reservation.endDate > time_now())

  with Session() as session:
    # Status counts (unfiltered, 90-day scoped)
    status_counts = {"reserved": 0, "started": 0, "stopped": 0, "error": 0, "paused": 0}
    count_rows = session.execute(
        select(Reservation.status, func.count())
        .where(time_scope)
        .group_by(Reservation.status)
    ).all()
    for s, c in count_rows:
        if s == "restart_error":
            status_counts["error"] += c
        elif s in status_counts:
            status_counts[s] = c

    # Time-based stats (unfiltered, 90-day scoped)
    now = time_now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    stats_row = session.execute(
        select(
            func.count().label("total"),
            func.sum(case((Reservation.startDate >= today_start, 1), else_=0)).label("today"),
            func.sum(case((Reservation.startDate >= week_ago, 1), else_=0)).label("lastWeek"),
            func.sum(case((Reservation.startDate >= month_ago, 1), else_=0)).label("lastMonth"),
        )
        .where(time_scope)
    ).one()
    stats = {
        "total": stats_row.total or 0,
        "started": status_counts.get("started", 0),
        "stopped": status_counts.get("stopped", 0),
        "error": status_counts.get("error", 0),
        "today": int(stats_row.today or 0),
        "lastWeek": int(stats_row.lastWeek or 0),
        "lastMonth": int(stats_row.lastMonth or 0),
        "lastThreeMonths": stats_row.total or 0,
    }

    def _apply_reservation_filters(query):
        """Apply shared reservation filters to a query."""
        if status_filter:
            if status_filter == "error":
                query = query.where(Reservation.status.in_(["error", "restart_error"]))
            else:
                query = query.where(Reservation.status == status_filter)
        if user_filter:
            query = query.where(
                User.email.ilike(f"%{user_filter}%") | User.name.ilike(f"%{user_filter}%")
            )
        if reservation_id_filter:
            query = query.where(
                cast(Reservation.reservationId, String).like(f"%{reservation_id_filter}%")
            )
        if computer_id_filter:
            try:
                query = query.where(Reservation.computerId == int(computer_id_filter))
            except (ValueError, TypeError):
                pass
        if container_id_filter:
            query = query.join(ReservedContainer, Reservation.reservedContainerId == ReservedContainer.reservedContainerId)\
                .where(ReservedContainer.containerId == int(container_id_filter))
        if date_from_filter:
            try:
                query = query.where(Reservation.startDate >= parser.parse(date_from_filter))
            except (ValueError, TypeError):
                pass
        if date_to_filter:
            try:
                query = query.where(Reservation.startDate < parser.parse(date_to_filter) + timedelta(days=1))
            except (ValueError, TypeError):
                pass
        return query

    # Build filtered base query (for counting and pagination)
    base_filtered = select(Reservation).where(time_scope)
    # Need join to User for userEmail sorting — always join since it's lightweight
    base_filtered = base_filtered.join(User, Reservation.userId == User.userId)
    base_filtered = _apply_reservation_filters(base_filtered)

    # Total count of filtered results
    total_items = get_total_count(session, base_filtered)

    # Paginate IDs first (subquery pattern to avoid joinedload + LIMIT issues)
    # Rebuild ID query with same filters and joins to avoid cartesian product
    id_stmt = select(Reservation.reservationId).where(time_scope)\
        .join(User, Reservation.userId == User.userId)
    id_stmt = _apply_reservation_filters(id_stmt)
    id_stmt = apply_pagination(
        id_stmt, request.sortBy, request.page,
        request.itemsPerPage, allowed_sort_keys
    )
    paginated_ids = [row[0] for row in session.execute(id_stmt).all()]

    # Load full reservation objects for the paginated IDs
    reservations = []
    if paginated_ids:
        # Re-apply sort order to the full query
        full_stmt = select(Reservation)\
            .options(
                joinedload(Reservation.reservedHardwareSpecs),
                joinedload(Reservation.reservedContainer).joinedload(ReservedContainer.reservedContainerPorts),
                joinedload(Reservation.reservedContainer).joinedload(ReservedContainer.container),
                joinedload(Reservation.computer),
            )\
            .where(Reservation.reservationId.in_(paginated_ids))
        full_stmt = apply_pagination(full_stmt, request.sortBy, 1, -1, allowed_sort_keys)
        query = session.execute(full_stmt).unique().scalars().all()

        for reservation in query:
            res = orm_to_dict(reservation)
            res["userEmail"] = reservation.user.email
            res["userName"] = reservation.user.name
            res["computerName"] = reservation.computer.name
            res["reservedContainer"] = orm_to_dict(reservation.reservedContainer)
            container_dict = orm_to_dict(reservation.reservedContainer.container)
            # Strip buildLog from reservation listings to avoid large payloads
            container_dict.pop("buildLog", None)
            res["reservedContainer"]["container"] = container_dict

            res["reservedContainer"]["reservedPorts"] = []
            if reservation.status == "started":
                for reserved_port in reservation.reservedContainer.reservedContainerPorts:
                    port_obj = orm_to_dict(reserved_port)
                    port_obj["localPort"] = reserved_port.containerPort.port
                    port_obj["serviceName"] = reserved_port.containerPort.serviceName
                    res["reservedContainer"]["reservedPorts"].append(port_obj)

            res["reservedHardwareSpecs"] = []
            for spec in reservation.reservedHardwareSpecs:
                if spec.amount > 0:
                    if spec.hardwareSpec.type == "gpu":
                        format = f"{spec.hardwareSpec.format} (id: {spec.hardwareSpec.internalId})"
                    else:
                        format = spec.hardwareSpec.format
                    res["reservedHardwareSpecs"].append({
                        "type": spec.hardwareSpec.type,
                        "format": format,
                        "internalId": spec.hardwareSpec.internalId,
                        "amount": spec.amount,
                    })
            reservations.append(res)

  # Fetch available computers and containers for filter dropdowns
  with Session() as session:
    computers_list = session.execute(
        select(Computer.computerId, Computer.name).where(Computer.removed.isnot(True))
    ).all()
    containers_list = session.execute(
        select(Container.containerId, Container.name).where(Container.removed.isnot(True))
    ).all()

  return api_response(True, "Reservations fetched.", {
      "reservations": reservations,
      "totalItems": total_items,
      "statusCounts": status_counts,
      "stats": stats,
      "availableComputers": [{"id": c[0], "name": c[1]} for c in computers_list],
      "availableContainers": [{"id": c[0], "name": c[1]} for c in containers_list],
  })

def save_container(containerEdit : ContainerEdit, actor_user_id: int = None) -> object:
  """Create or update a container definition.

  For new containers (containerId == -1), creates a new Container record
  with the given name, image, description, and ports. For existing
  containers, updates the fields and handles port additions, removals,
  and edits. Validates that the image name is unique across containers.

  Args:
      containerEdit: ContainerEdit model containing containerId and a
          data dict with name, imageName, description, public flag,
          ports, and removedPorts.

  Returns:
      Response indicating success or failure with an appropriate message.
  """

  with Session() as session:
    # Check for duplicate image name
    new_image_name = containerEdit.data.get("imageName")
    existing = session.execute(
      select(Container).where(Container.imageName == new_image_name)
    ).scalar_one_or_none()
    if existing and existing.containerId != containerEdit.containerId:
      return api_response(False, "A container with this image name already exists.")
    if new_image_name and not _VALID_IMAGE_NAME_RE.match(new_image_name):
      return api_response(False, "Invalid image name. Use only lowercase letters, digits, dots, hyphens, underscores, and forward slashes.")

    new_managed_externally = containerEdit.data.get("managedExternally", True)
    new_dockerfile_commands = containerEdit.data.get("dockerfileCommands", None)
    new_base_image = containerEdit.data.get("baseImage", None)
    new_username = containerEdit.data.get("containerUsername", None)
    new_password_command = containerEdit.data.get("passwordCommand", None)
    new_ssh_key_commands = containerEdit.data.get("sshKeyDeployCommands", None)
    new_cmd = containerEdit.data.get("containerCmd", None)

    # For externally managed containers, clear image builder fields
    if new_managed_externally:
      new_dockerfile_commands = None
      new_base_image = None
      new_username = None
      new_password_command = None
      new_ssh_key_commands = None
      new_cmd = None

    # Type-check string fields
    for field_name, field_val in [("dockerfileCommands", new_dockerfile_commands), ("baseImage", new_base_image),
                                   ("containerUsername", new_username), ("passwordCommand", new_password_command),
                                   ("sshKeyDeployCommands", new_ssh_key_commands), ("containerCmd", new_cmd)]:
      if field_val is not None and not isinstance(field_val, str):
        return api_response(False, f"{field_name} must be a string.")

    # Normalize empty strings to None
    if new_dockerfile_commands is not None and not new_dockerfile_commands.strip():
      new_dockerfile_commands = None
    if new_base_image is not None and not new_base_image.strip():
      new_base_image = None
    if new_password_command is not None and not new_password_command.strip():
      new_password_command = None
    if new_ssh_key_commands is not None and not new_ssh_key_commands.strip():
      new_ssh_key_commands = None
    if new_cmd is not None and not new_cmd.strip():
      new_cmd = None

    # Validate username
    if new_username is not None and new_username.strip():
      new_username = new_username.strip()
      if not _VALID_USERNAME_RE.match(new_username):
        return api_response(False, "Invalid username. Must be 1-32 lowercase letters, digits, hyphens, or underscores, starting with a letter or underscore.")
      if new_username in _RESERVED_USERNAMES:
        return api_response(False, f"Username '{new_username}' is reserved and cannot be used.")
    else:
      new_username = None  # Will default to "user" at runtime

    # Validate ports (integers 1-65535, no duplicates, port 22 reserved for SSH)
    new_ports = containerEdit.data.get("ports", [])
    port_numbers = [_SSH_PORT]  # SSH is always reserved
    for port in new_ports:
      try:
        port_num = int(port.get("port", 0))
      except (ValueError, TypeError):
        return api_response(False, "Port must be an integer.")
      if port_num < 1 or port_num > 65535:
        return api_response(False, f"Port {port_num} is out of range. Must be between 1 and 65535.")
      if port_num == _SSH_PORT:
        return api_response(False, "Port 22 is reserved for SSH and is always included automatically.")
      if port_num in port_numbers:
        return api_response(False, f"Duplicate port {port_num}. Each port can only be used once.")
      port_numbers.append(port_num)

    # If new, create a new container
    if containerEdit.containerId == -1:
      container = Container()
      container.public = containerEdit.data.get("public", False)
      container.name = containerEdit.data.get("name")
      container.imageName = new_image_name
      container.description = containerEdit.data.get("description", "")
      container.managedExternally = new_managed_externally
      container.dockerfileCommands = new_dockerfile_commands
      container.baseImage = new_base_image
      container.containerUsername = new_username
      container.passwordCommand = new_password_command
      container.sshKeyDeployCommands = new_ssh_key_commands
      container.containerCmd = new_cmd
      # Queue build if using Image Builder
      if not new_managed_externally and new_dockerfile_commands:
        container.buildStatus = "pending"
        container.buildLog = ""
      # Add ports
      for port in containerEdit.data.get("ports", []):
        container.containerPorts.append(ContainerPort(port=port["port"], serviceName=port["serviceName"]))
      session.add(container)
      _ensure_ssh_port(session, container)
      session.commit()
      saved_container_id = container.containerId
    # Otherwise, edit container
    else:
      container = session.execute(select(Container).where(Container.containerId == containerEdit.containerId)).scalar_one_or_none()
      if container is None:
        return api_response(False, "Container not found.")
      else:
        # Check if Dockerfile-related fields changed — if so, queue a rebuild
        dockerfile_changed = (new_dockerfile_commands != container.dockerfileCommands)
        base_image_changed = (new_base_image != container.baseImage)
        username_changed = (new_username != container.containerUsername)
        cmd_changed = (new_cmd != container.containerCmd)

        container.public = containerEdit.data.get("public", False)
        container.name = containerEdit.data.get("name")
        container.imageName = new_image_name
        container.description = containerEdit.data.get("description", "")
        container.managedExternally = new_managed_externally
        container.dockerfileCommands = new_dockerfile_commands
        container.baseImage = new_base_image
        container.containerUsername = new_username
        container.passwordCommand = new_password_command
        container.sshKeyDeployCommands = new_ssh_key_commands
        container.containerCmd = new_cmd
        container.updatedAt = datetime.datetime.now(datetime.timezone.utc)

        # Queue rebuild if using Image Builder and Dockerfile-related fields changed
        if not new_managed_externally and new_dockerfile_commands and (dockerfile_changed or base_image_changed or username_changed or cmd_changed):
          container.buildStatus = "pending"
          container.buildLog = ""
        # If switching to externally managed, clear build status
        if new_managed_externally:
          container.buildStatus = None
          container.buildLog = None
        # Remove all removable ports (protect built-in SSH port from deletion)
        for port_id in containerEdit.data.get("removedPorts", []):
          port_to_remove = session.execute(
            select(ContainerPort).where(ContainerPort.containerPortId == port_id)
          ).scalar_one_or_none()
          if port_to_remove and not (port_to_remove.serviceName == _SSH_SERVICE_NAME and port_to_remove.port == _SSH_PORT):
            # Block removal if any active reservation references this port
            active_ref_count = session.execute(
              select(func.count()).select_from(ReservedContainerPort).join(
                ReservedContainer, ReservedContainerPort.reservedContainerId == ReservedContainer.reservedContainerId
              ).join(
                Reservation, Reservation.reservedContainerId == ReservedContainer.reservedContainerId
              ).where(
                ReservedContainerPort.containerPortForeign == port_id,
                Reservation.status.in_(["reserved", "started", "restart", "restart_error"])
              )
            ).scalar() or 0
            if active_ref_count > 0:
              return api_response(
                False,
                f"Cannot remove port {port_to_remove.port} ({port_to_remove.serviceName}): "
                f"it is used by {active_ref_count} active reservation(s). "
                f"Cancel or wait for those reservations to end first."
              )
            # Clean up historical ReservedContainerPort records before deleting the port
            session.execute(
              delete(ReservedContainerPort).where(ReservedContainerPort.containerPortForeign == port_id)
            )
            session.execute(delete(ContainerPort).where(ContainerPort.containerPortId == port_id))
        # Add all new ports
        for port in containerEdit.data.get("ports", []):
          if "containerPortId" not in port:
            container.containerPorts.append(ContainerPort(port=port["port"], serviceName=port["serviceName"]))
        # Edit changed ports
        for port in containerEdit.data.get("ports", []):
          if "containerPortId" in port:
            old_port = session.execute(select(ContainerPort).where(ContainerPort.containerPortId == port["containerPortId"])).scalar_one_or_none()
            if old_port.port != port["port"] or old_port.serviceName != port["serviceName"]:
              old_port.port = port["port"]
              old_port.serviceName = port["serviceName"]
              old_port.updatedAt = datetime.datetime.now(datetime.timezone.utc)

        #for port in containerEdit.data.get("ports", []):
        #  container.containerPorts.append(ContainerPort(port=port["port"], serviceName=port["serviceName"]))
        _ensure_ssh_port(session, container)
        session.commit()
        saved_container_id = container.containerId
  is_new = containerEdit.containerId == -1
  log_action(
      actor_user_id,
      "CONTAINER_CREATE" if is_new else "CONTAINER_UPDATE",
      "container", saved_container_id,
      {"name": containerEdit.data.get("name"), "imageName": containerEdit.data.get("imageName")}
  )
  return api_response(True, "Container saved successfully", {"containerId": saved_container_id})

def get_container_remove_info(container_id: int) -> object:
  """Get information for the container removal confirmation dialog.

  Returns active reservation count, image management mode, and image name
  so the frontend can show an informative confirmation dialog.

  Args:
      container_id: Database ID of the container to check.

  Returns:
      Response with activeReservations, managedExternally, and imageName.
  """
  with Session() as session:
    container = session.execute(
      select(Container).where(Container.containerId == container_id)
    ).scalar_one_or_none()
    if container is None:
      return api_response(False, "Container not found.")

    # Count active reservations (reserved or started) using this container
    from database import Reservation, ReservedContainer
    active_count = session.execute(
      select(func.count()).select_from(Reservation).join(
        ReservedContainer, Reservation.reservedContainerId == ReservedContainer.reservedContainerId
      ).where(
        ReservedContainer.containerId == container_id,
        Reservation.status.in_(["reserved", "started"])
      )
    ).scalar() or 0

    return api_response(True, "Remove info fetched.", {
      "activeReservations": active_count,
      "managedExternally": container.managedExternally if container.managedExternally is not None else True,
      "imageName": container.imageName,
    })

def remove_container(containerId : int, actor_user_id: int = None) -> object:
  """Soft-delete a container by marking it as removed and non-public.

  For containers managed by the Image Builder, queues the Docker image
  for removal by setting buildStatus to "removing". The daemon will
  clean up the image on its next polling cycle.

  Args:
      containerId: The ID of the container to remove.
      actor_user_id: The userId of the admin performing the action.

  Returns:
      Response indicating success or failure with an appropriate message.
  """

  with Session() as session:
    container = session.execute(select(Container).where(Container.containerId == containerId)).scalar_one_or_none()
    if container is None:
      return api_response(False, "Container not found.")
    else:
      container_name = container.name
      container_image = container.imageName
      container.removed = True
      container.public = False
      # Queue image removal for non-externally managed containers
      if container.managedExternally == False:
        container.buildStatus = "removing"
      session.commit()

  log_action(actor_user_id, "CONTAINER_DELETE", "container", containerId,
             {"name": container_name, "imageName": container_image})
  return api_response(True, "Container removed successfully")

def rebuild_container_image(container_id: int, actor_user_id: int = None) -> object:
  """Queue a container image for rebuild by setting buildStatus to "pending".

  The Docker utility daemon will pick this up on its next polling cycle
  and perform the actual build. Refuses if the container has no Dockerfile
  commands or if a build is already in progress.

  Args:
      container_id: Database ID of the container to rebuild.
      actor_user_id: The userId of the admin performing the action.

  Returns:
      Response indicating success or failure with an appropriate message.
  """
  with Session() as session:
    container = session.execute(
      select(Container).where(Container.containerId == container_id)
    ).scalar_one_or_none()
    if container is None:
      return api_response(False, "Container not found.")
    if not container.dockerfileCommands:
      return api_response(False, "This container has no Dockerfile commands. Cannot build.")
    if container.buildStatus == "building":
      return api_response(False, "A build is already in progress for this container.")
    container.buildStatus = "pending"
    container.buildLog = ""
    session.commit()
  log_action(actor_user_id, "CONTAINER_REBUILD", "container", container_id)
  return api_response(True, "Image build queued. The Docker utility will build it shortly.")

def get_container_defaults(username: str = "user") -> object:
  """Get default values for container creation fields.

  Returns the default Dockerfile body, CMD, password command, and SSH key
  deploy commands. Used by the frontend to pre-fill the container creation
  form and for the "Reset to Defaults" button.

  Args:
      username: Linux username to interpolate into the defaults.

  Returns:
      Response with default field values.
  """
  # Validate username before interpolating into Dockerfile template
  if not _VALID_USERNAME_RE.match(username):
    return api_response(False, "Invalid username.")
  if username in _RESERVED_USERNAMES:
    return api_response(False, f"Username '{username}' is reserved.")

  from helpers.container_defaults import get_default_dockerfile_body, DEFAULT_CMD, DEFAULT_PASSWORD_COMMAND, DEFAULT_SSH_KEY_DEPLOY_COMMANDS

  return api_response(True, "Defaults fetched.", {
    "dockerfileBody": get_default_dockerfile_body(username),
    "containerCmd": DEFAULT_CMD,
    "passwordCommand": DEFAULT_PASSWORD_COMMAND,
    "sshKeyDeployCommands": DEFAULT_SSH_KEY_DEPLOY_COMMANDS,
    "containerUsername": username,
  })

def get_container_build_status(container_id: int) -> object:
  """Get the current build status and log for a container image.

  Args:
      container_id: Database ID of the container to check.

  Returns:
      Response with buildStatus and buildLog fields.
  """
  with Session() as session:
    container = session.execute(
      select(Container).where(Container.containerId == container_id)
    ).scalar_one_or_none()
    if container is None:
      return api_response(False, "Container not found.")
    return api_response(True, "Build status fetched.", {
      "buildStatus": container.buildStatus,
      "buildLog": container.buildLog or ""
    })

def get_users(request: AdminUsersRequest) -> object:
    """Retrieve paginated users with server-side filtering and sorting.

    Returns a page of users matching the given filters, along with the
    total count of matching users and available roles with user counts
    (always unfiltered so the role dropdown shows accurate totals).

    Args:
        request: Pagination, sorting, and filter parameters. Supported
            filter keys: role, email, userId.

    Returns:
        Response with paginated users list, totalItems count, and
        availableRoles list.
    """
    filters = request.filters
    role_filter = filters.get("role", "")
    name_filter = filters.get("name", "")
    email_filter = filters.get("email", "")
    user_id_filter = filters.get("userId", "")

    allowed_sort_keys = {
        "userId": User.userId,
        "email": User.email,
        "name": User.name,
        "createdAt": User.userCreatedAt,
        "hasPassword": User.password,
    }

    with Session() as session:
        # Build base filtered query (exclude anonymized users)
        base_stmt = select(User).where(User.removed.isnot(True))
        if role_filter:
            base_stmt = base_stmt.join(UserRole, User.userId == UserRole.userId)\
                .join(Role, UserRole.roleId == Role.roleId)\
                .where(Role.name == role_filter)
        if name_filter:
            base_stmt = base_stmt.where(User.name.ilike(f"%{name_filter}%"))
        if email_filter:
            base_stmt = base_stmt.where(User.email.ilike(f"%{email_filter}%"))
        if user_id_filter:
            base_stmt = base_stmt.where(cast(User.userId, String).like(f"%{user_id_filter}%"))

        # Get total count of filtered results
        total_items = get_total_count(session, base_stmt)

        # Apply sorting and pagination
        paginated_stmt = apply_pagination(
            base_stmt, request.sortBy, request.page,
            request.itemsPerPage, allowed_sort_keys
        )

        # Fetch paginated users with their roles eager-loaded
        paginated_stmt = paginated_stmt.options(joinedload(User.roles))
        users = session.execute(paginated_stmt).unique().scalars().all()

        data = []
        for user in users:
            data.append({
                "userId": user.userId,
                "email": user.email,
                "name": user.name,
                "roles": [role.name for role in user.roles],
                "createdAt": user.userCreatedAt,
                "hasPassword": user.password is not None and user.password != "",
            })

    # Get available roles with user counts (always unfiltered)
    role_user_counts = {}
    with Session() as session:
        role_counts = session.execute(
            select(Role.name, func.count(UserRole.userId))
            .outerjoin(UserRole, Role.roleId == UserRole.roleId)
            .group_by(Role.name)
        ).all()
        for role_name, count in role_counts:
            role_user_counts[role_name] = count

    from helpers.tables.role import get_roles_with_mount_counts
    available_roles = get_roles_with_mount_counts()
    for role in available_roles:
        role["userCount"] = role_user_counts.get(role["name"], 0)

    return api_response(True, "Users fetched successfully", {
        "users": data,
        "totalItems": total_items,
        "availableRoles": available_roles,
    })

def get_user(userId: int) -> object:
    """Retrieve a single user by ID.

    Args:
        userId: The ID of the user to fetch.

    Returns:
        Response with user details (userId, email, roles, createdAt),
        or an error if the user is not found.
    """
    data = {}

    with Session() as session:
        user = session.execute(
            select(User).options(joinedload(User.roles)).where(User.userId == userId)
        ).unique().scalar_one_or_none()
        if user is None or user.removed is True:
            return api_response(False, "User not found")

        data = {
            "userId": user.userId,
            "email": user.email,
            "name": user.name,
            "roles": [role.name for role in user.roles],
            "createdAt": user.userCreatedAt
        }

    return api_response(True, "User fetched successfully", {"user": data})

def save_user(userId: int, data: dict, actor_user_id: int = None) -> object:
    """Create or update a user account.

    For new users (userId == -1), creates a new User with hashed password.
    For existing users, updates email and optionally password or clears it.
    Also handles role assignment by replacing existing roles with the
    provided list. Validates email uniqueness across all users.

    Args:
        userId: The ID of the user to update, or -1 to create a new user.
        data: Dictionary containing email, password (optional),
            clearPassword (optional bool), and roles (list of role names).
        actor_user_id: The userId of the admin performing the action.

    Returns:
        Response indicating success or failure with an appropriate message.
    """
    with Session() as session:
        # Check if email already exists
        existing_user = session.execute(select(User).where(User.email == data["email"])).scalar_one_or_none()
        if existing_user is not None and (userId == -1 or existing_user.userId != userId):
            return api_response(False, "A user with this email already exists")

        if userId == -1:
            # Create new user
            hash = hash_password(data["password"])
            raw_name = data.get("name")
            user = User(
                email=data["email"],
                name=raw_name[:200] if raw_name else raw_name,
                password=base64.b64encode(hash["hashedPassword"]).decode('utf-8'),
                passwordSalt=base64.b64encode(hash["salt"]).decode('utf-8')
            )
            session.add(user)
            session.flush()  # This will populate the userId
            
        else:
            # Update existing user
            user = session.execute(select(User).where(User.userId == userId)).scalar_one_or_none()
            if user is None:
                return api_response(False, "User not found")
            if user.removed is True:
                return api_response(False, "Cannot edit an anonymized user.")

            user.email = data["email"]
            new_name = data.get("name", user.name)
            user.name = new_name[:200] if new_name else new_name

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
                role = session.execute(select(Role).where(Role.name == role_name)).scalar_one_or_none()
                if role and role not in user.roles:  # Check if role exists and isn't already assigned
                    user.roles.append(role)
        
        session.commit()
        is_new = userId == -1
        audit_details = {"email": data.get("email"), "roles": data.get("roles", [])}
        if not is_new:
            if data.get("clearPassword"):
                audit_details["passwordCleared"] = True
            elif data.get("password"):
                audit_details["passwordChanged"] = True
        log_action(actor_user_id, "USER_CREATE" if is_new else "USER_UPDATE",
                   "user", user.userId, audit_details)
        return api_response(True, "User saved successfully")

def get_hardware() -> object:
  """Retrieve all hardware specification records.

  Returns:
      Response with a list of all HardwareSpec entries as dicts.
  """

  data = []

  with Session() as session:
    query = session.execute(select(HardwareSpec)).scalars().all()
    for hardware in query:
      addable = {}
      addable = orm_to_dict(hardware)
      data.append(addable)
  
  return api_response(True, "Data fetched.", { "hardware": data })

def get_containers() -> object:
  """Retrieve all active (non-removed) container definitions with their ports.

  Returns:
      Response with a list of container dicts, each including a ports
      list with containerPortId, port number, and serviceName.
  """

  data = []

  with Session() as session:
    # Find all where Container.removed is not True
    query = session.execute(select(Container).where(Container.removed.isnot(True))).scalars().all()
    for container in query:
      addable = {}
      addable = orm_to_dict(container)
      # Strip buildLog from listing to avoid large payloads
      addable.pop("buildLog", None)
      addable["ports"] = []
      for port in container.containerPorts:
        if port.serviceName == _SSH_SERVICE_NAME and port.port == _SSH_PORT:
          continue
        addable["ports"].append({
          "containerPortId": port.containerPortId,
          "port": port.port,
          "serviceName": port.serviceName,
        })
      data.append(addable)
  
  return api_response(True, "Data fetched.", { "containers": data })

def get_container(containerId : int) -> object:
  """Retrieve a single container definition by ID, including its ports.

  Args:
      containerId: The ID of the container to fetch.

  Returns:
      Response with the container dict including its ports list.
  """

  addable = {}

  with Session() as session:
    query = session.execute(select(Container).where(Container.containerId == containerId).limit(1)).scalars().all()
    for container in query:
      addable = {}
      addable = orm_to_dict(container)
      addable["ports"] = []
      for port in container.containerPorts:
        if port.serviceName == _SSH_SERVICE_NAME and port.port == _SSH_PORT:
          continue
        addable["ports"].append({
          "containerPortId": port.containerPortId,
          "port": port.port,
          "serviceName": port.serviceName,
        })
  
  return api_response(True, "Data fetched.", { "data": addable })

def get_computers() -> object:
  """Retrieve all active (non-removed) computers with their hardware specs.

  Returns:
      Response with a list of computer dicts, each including a
      hardwareSpecs list of associated hardware specifications.
  """

  data = []

  with Session() as session:
    query = session.execute(select(Computer).where(Computer.removed.isnot(True))).scalars().all()
    for computer in query:
      addable = {}
      addable = orm_to_dict(computer)
      addable["hardwareSpecs"] = []
      for spec in computer.hardwareSpecs:
        addable["hardwareSpecs"].append(orm_to_dict(spec))
      data.append(addable)
  
  return api_response(True, "Data fetched.", { "computers": data })

def get_computer(computerId : int) -> object:
  """Retrieve a single computer by ID with structured hardware details.

  Returns hardware organized into cpu, ram, gpu (aggregate), and gpus
  (individual GPU list) sections.

  Args:
      computerId: The ID of the computer to fetch.

  Returns:
      Response with the computer dict including nested hardware details.
  """

  data = {}

  with Session() as session:
    query = session.execute(select(Computer).where( Computer.computerId == computerId ).limit(1)).scalars().all()
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

def save_computer(computerEdit : ComputerEdit, actor_user_id: int = None) -> object:
  """Create or update a computer (server) and its hardware specifications.

  For new computers (computerId == -1), creates a Computer record with
  CPU, RAM, and GPU hardware specs. For existing computers, updates the
  fields, modifies hardware spec limits, and handles GPU additions,
  removals, and edits.

  Args:
      computerEdit: ComputerEdit model containing computerId and a data
          dict with name, ip, public flag, hardware (cpu, ram, gpu, gpus),
          and removedGPUs list.

  Returns:
      Response indicating success or failure with an appropriate message.
  """
  
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
      saved_computer_id = computer.computerId
    # Otherwise, edit computer
    else:
      log.debug(computerEdit.data.get("hardware").get("gpus"))
      computer = session.execute(select(Computer).where(Computer.computerId == computerEdit.computerId)).scalar_one_or_none()
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
          session.execute(delete(ReservedHardwareSpec).where(ReservedHardwareSpec.hardwareSpecId == spec))
          session.execute(delete(HardwareSpec).where(HardwareSpec.hardwareSpecId == spec))
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
            old_gpu = session.execute(select(HardwareSpec).where(HardwareSpec.hardwareSpecId == gpu["hardwareSpecId"])).scalar_one_or_none()
            if old_gpu.format != gpu["format"] or old_gpu.internalId != gpu["internalId"]:
              old_gpu.format = gpu["format"]
              old_gpu.internalId = gpu["internalId"]
              old_gpu.updatedAt = datetime.datetime.now(datetime.timezone.utc)

        #for port in containerEdit.data.get("ports", []):
        #  container.containerPorts.append(ContainerPort(port=port["port"], serviceName=port["serviceName"]))
        session.commit()
        saved_computer_id = computer.computerId
  is_new = computerEdit.computerId == -1
  log_action(
      actor_user_id,
      "COMPUTER_CREATE" if is_new else "COMPUTER_UPDATE",
      "computer", saved_computer_id,
      {"name": computerEdit.data.get("name"), "ip": computerEdit.data.get("ip")}
  )
  return api_response(True, "Computer saved successfully")

def remove_computer(computerId : int, actor_user_id: int = None) -> object:
  """Soft-delete a computer by marking it as removed and non-public.

  Args:
      computerId: The ID of the computer to remove.
      actor_user_id: The userId of the admin performing the action.

  Returns:
      Response indicating success or failure with an appropriate message.
  """

  with Session() as session:
    computer = session.execute(select(Computer).where(Computer.computerId == computerId)).scalar_one_or_none()
    if computer is None:
      return api_response(False, "Computer not found.")
    else:
      computer_name = computer.name
      computer.removed = True
      computer.public = False
      session.commit()

  log_action(actor_user_id, "COMPUTER_DELETE", "computer", computerId, {"name": computer_name})
  return api_response(True, "Computer removed successfully")

def edit_reservation(reservationId : int, end_date_str : str, actor_user_id: int = None) -> object:
  """Update a reservation's end date.

  Parses the provided date string and sets it as the new end date
  for the specified reservation.

  Args:
      reservationId: The ID of the reservation to edit.
      end_date_str: The new end date as an ISO-format string.
      actor_user_id: The userId of the admin performing the action.

  Returns:
      Response indicating success or failure with an appropriate message.
  """
  # Verify that the new end date is valid
  try:
    parsed_end_date = parser.parse(end_date_str)
  except:
    return api_response(False, "Invalid end date.")

  with Session() as session:
    reservation = session.execute(select(Reservation).where(Reservation.reservationId == reservationId)).scalar_one_or_none()
    if reservation is None:
      return api_response(False, "Reservation not found.")
    else:
      old_end_date = reservation.endDate.isoformat() if reservation.endDate else None
      reservation.endDate = parsed_end_date
      session.commit()

  log_action(actor_user_id, "RESERVATION_ADMIN_EDIT", "reservation", reservationId,
             {"oldEndDate": old_end_date, "newEndDate": end_date_str})
  return api_response(True, "Reservation was edited succesfully.")

def get_all_roles() -> object:
    """Retrieve all roles with their associated mount counts.

    Returns:
        Response with a list of role dicts including mount count per role.
    """
    from helpers.tables.role import get_roles_with_mount_counts
    data = get_roles_with_mount_counts()
    
    return api_response(True, "Roles fetched successfully.", {"roles": data})

def add_role(name: str, actor_user_id: int = None) -> object:
    """Create a new role with the given name.

    Args:
        name: The name for the new role.
        actor_user_id: The userId of the admin performing the action.

    Returns:
        Response with the created role data, or an error if creation fails.
    """
    success, message, role_dict = add_role_helper(name)
    if not success:
        return api_response(False, message)
    log_action(actor_user_id, "ROLE_CREATE", "role", role_dict.get("roleId"), {"name": name})
    return api_response(True, message, role_dict)

def edit_role(roleId: int, name: str, actor_user_id: int = None) -> object:
    """Rename an existing role.

    Args:
        roleId: The ID of the role to edit.
        name: The new name for the role.
        actor_user_id: The userId of the admin performing the action.

    Returns:
        Response with the updated role data, or an error if the edit fails.
    """
    success, message, role_dict = edit_role_helper(roleId, name)
    if not success:
        return api_response(False, message)
    log_action(actor_user_id, "ROLE_UPDATE", "role", roleId, {"newName": name})
    return api_response(True, message, role_dict)

def remove_role(roleId: int, actor_user_id: int = None) -> object:
    """Delete a role by ID.

    Args:
        roleId: The ID of the role to remove.
        actor_user_id: The userId of the admin performing the action.

    Returns:
        Response indicating success or failure with an appropriate message.
    """
    success, message = remove_role_helper(roleId)
    if not success:
        return api_response(False, message)
    log_action(actor_user_id, "ROLE_DELETE", "role", roleId)
    return api_response(True, message)

def get_role_mounts(roleId: int) -> object:
    """Retrieve all volume mount configurations for a specific role.

    Args:
        roleId: The ID of the role to get mounts for.

    Returns:
        Response with a list of mount dicts for the role.
    """
    try:
        from helpers.tables.role import get_role_mounts as get_role_mounts_helper
        mounts = get_role_mounts_helper(roleId)
        return api_response(True, "Role mounts retrieved successfully", {"mounts": mounts})
    except Exception as e:
        return api_response(False, f"Error retrieving role mounts: {str(e)}")

def save_role_mounts(roleId: int, mounts: list, actor_user_id: int = None) -> object:
    """Replace all volume mount configurations for a role.

    Deletes existing mounts and saves the provided list as the new
    mount configuration for the specified role.

    Args:
        roleId: The ID of the role.
        mounts: List of mount dicts, each containing host path,
            container path, and read-only flag.
        actor_user_id: The userId of the admin performing the action.

    Returns:
        Response indicating success or failure with an appropriate message.
    """
    try:
        from helpers.tables.role import save_role_mounts as save_role_mounts_helper
        success, message = save_role_mounts_helper(roleId, mounts)
        if success:
            log_action(actor_user_id, "ROLE_MOUNTS_UPDATE", "role", roleId,
                       {"mountCount": len(mounts)})
        return api_response(success, message)
    except Exception as e:
        return api_response(False, f"Error saving role mounts: {str(e)}")

def get_role_hardware_limits(roleId: int) -> object:
    """Retrieve hardware resource limits for a specific role.

    Args:
        roleId: The ID of the role.

    Returns:
        Response with a list of hardware limit dicts for the role.
    """
    try:
        from helpers.tables.role import get_role_hardware_limits as get_role_hardware_limits_helper
        limits = get_role_hardware_limits_helper(roleId)
        return api_response(True, "Role hardware limits retrieved successfully", {"hardwareLimits": limits})
    except Exception as e:
        return api_response(False, f"Error retrieving role hardware limits: {str(e)}")

def save_role_hardware_limits(roleId: int, hardwareLimits: list, actor_user_id: int = None) -> object:
    """Replace all hardware resource limits for a role.

    Deletes existing limits and saves the provided list as the new
    hardware limit configuration for the specified role.

    Args:
        roleId: The ID of the role.
        hardwareLimits: List of hardware limit dicts, each containing
            hardwareSpecId and maximumAmountForRole.
        actor_user_id: The userId of the admin performing the action.

    Returns:
        Response indicating success or failure with an appropriate message.
    """
    try:
        from helpers.tables.role import save_role_hardware_limits as save_role_hardware_limits_helper
        success, message = save_role_hardware_limits_helper(roleId, hardwareLimits)
        if success:
            log_action(actor_user_id, "ROLE_HARDWARE_LIMITS_UPDATE", "role", roleId)
        return api_response(success, message)
    except Exception as e:
        return api_response(False, f"Error saving role hardware limits: {str(e)}")

def get_role_reservation_limits(roleId: int) -> object:
    """Retrieve reservation limits for a specific role.

    Args:
        roleId: The ID of the role.

    Returns:
        Response with reservation limits (minDuration, maxDuration,
        maxActiveReservations) for the role.
    """
    try:
        from helpers.tables.role import get_role_reservation_limits as get_role_reservation_limits_helper
        limits = get_role_reservation_limits_helper(roleId)
        return api_response(True, "Role reservation limits retrieved successfully", {"reservationLimits": limits})
    except Exception as e:
        return api_response(False, f"Error retrieving role reservation limits: {str(e)}")

def save_role_reservation_limits(roleId: int, reservationLimits: dict, actor_user_id: int = None) -> object:
    """Replace reservation limits for a role.

    Args:
        roleId: The ID of the role.
        reservationLimits: Dictionary containing minDuration (hours),
            maxDuration (hours), and maxActiveReservations.
        actor_user_id: The userId of the admin performing the action.

    Returns:
        Response indicating success or failure with an appropriate message.
    """
    try:
        from helpers.tables.role import save_role_reservation_limits as save_role_reservation_limits_helper
        success, message = save_role_reservation_limits_helper(roleId, reservationLimits)
        if success:
            log_action(actor_user_id, "ROLE_RESERVATION_LIMITS_UPDATE", "role", roleId)
        return api_response(success, message)
    except Exception as e:
        return api_response(False, f"Error saving role reservation limits: {str(e)}")

def get_server_monitoring(computer_id: int) -> object:
    """Retrieve monitoring data for a specific server.

    Returns system metrics (CPU, memory, disk, Docker, load averages,
    uptime) and logs for the specified server. Includes online status
    and software version information.

    Args:
        computer_id: The ID of the computer/server to monitor.

    Returns:
        Response with computer info, online status, metrics dict,
        version info, and logs dict keyed by log type.
    """
    with Session() as session:
        # Check if computer exists
        computer = session.execute(select(Computer).where(Computer.computerId == computer_id)).scalar_one_or_none()
        if not computer:
            return api_response(False, "Server not found")

        # Get server status/metrics
        status = session.execute(select(ServerStatus).where(
            ServerStatus.computerId == computer_id
        )).scalar_one_or_none()

        # Get server logs
        logs = session.execute(select(ServerLogs).where(
            ServerLogs.computerId == computer_id
        )).scalars().all()
        
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
    """Retrieve all non-removed servers for the monitoring dashboard.

    Returns:
        Response with a list of server dicts containing id, name,
        address (IP), and public visibility flag.
    """
    with Session() as session:
        computers = session.execute(select(Computer).where(
            (Computer.removed == False) | (Computer.removed.is_(None))
        )).scalars().all()
        
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
    """Retrieve all admin-configurable application settings.

    Fetches settings from the database organized by section: general
    (app name, timezone, instructions), access control (blacklist/whitelist),
    email (SMTP configuration), notifications (alert settings), and
    authentication (login type, session timeout, LDAP configuration).
    Returns default values for any settings not yet configured.

    Returns:
        Response with settings organized by section, including
        blacklisted and whitelisted email lists.
    """
    try:
        from helpers.settings_handler import get_setting, get_multiple_settings
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
            'auth.ldap.emailField',
            'auth.ldap.nameField',
            'analytics.rybbitUrl',
            'analytics.rybbitSiteId',
            'analytics.googleAnalyticsId',
            'legal.enabled',
            'legal.organizationName',
            'legal.contactEmail',
            'legal.privacyPolicyContent',
            'legal.termsOfServiceContent',
            'legal.lastUpdated'
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
                    "emailField": settings_dict.get('auth.ldap.emailField', ''),
                    "nameField": settings_dict.get('auth.ldap.nameField', '')
                }
            },
            "analytics": {
                "rybbitUrl": settings_dict.get('analytics.rybbitUrl', ''),
                "rybbitSiteId": settings_dict.get('analytics.rybbitSiteId', ''),
                "googleAnalyticsId": settings_dict.get('analytics.googleAnalyticsId', '')
            },
            "legal": {
                "enabled": settings_dict.get('legal.enabled', False),
                "organizationName": settings_dict.get('legal.organizationName', ''),
                "contactEmail": settings_dict.get('legal.contactEmail', ''),
                "privacyPolicyContent": settings_dict.get('legal.privacyPolicyContent', ''),
                "termsOfServiceContent": settings_dict.get('legal.termsOfServiceContent', ''),
                "lastUpdated": settings_dict.get('legal.lastUpdated', '')
            }
        }
        
        return api_response(True, "Settings retrieved successfully", response_data)
        
    except Exception as e:
        return api_response(False, f"Error retrieving settings: {str(e)}")

def save_general_settings(section: str, settings: dict, actor_user_id: int = None) -> object:
    """Save admin settings for a specific configuration section.

    Persists settings to the database for the given section. Supported
    sections: general, access, email, contact, emailEnable, notifications,
    auth (including nested LDAP settings), auditLog, analytics, and legal.

    Args:
        section: The settings section name to save.
        settings: Dictionary of key-value pairs for the section.
        actor_user_id: The userId of the admin performing the action.

    Returns:
        Response indicating success or failure with an appropriate message.
    """
    try:
        from helpers.settings_handler import set_setting
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
                if 'nameField' in ldap_settings:
                    set_setting('auth.ldap.nameField', ldap_settings['nameField'])

        elif section == "auditLog":
            if 'retentionDays' in settings:
                set_setting('auditLog.retentionDays', settings['retentionDays'])
                # When set to -1 (disabled), purge all existing audit log entries
                if settings['retentionDays'] == -1:
                    from helpers.tables.audit_log import purge_all_logs
                    purge_all_logs()

        elif section == "analytics":
            if 'rybbitUrl' in settings:
                set_setting('analytics.rybbitUrl', settings['rybbitUrl'])
            if 'rybbitSiteId' in settings:
                set_setting('analytics.rybbitSiteId', settings['rybbitSiteId'])
            if 'googleAnalyticsId' in settings:
                set_setting('analytics.googleAnalyticsId', settings['googleAnalyticsId'])

        elif section == "legal":
            if 'enabled' in settings:
                set_setting('legal.enabled', settings['enabled'])
            if 'organizationName' in settings:
                set_setting('legal.organizationName', settings['organizationName'])
            if 'contactEmail' in settings:
                set_setting('legal.contactEmail', settings['contactEmail'])
            if 'privacyPolicyContent' in settings:
                set_setting('legal.privacyPolicyContent', settings['privacyPolicyContent'])
            if 'termsOfServiceContent' in settings:
                set_setting('legal.termsOfServiceContent', settings['termsOfServiceContent'])
            from datetime import datetime, timezone
            set_setting('legal.lastUpdated', datetime.now(timezone.utc).isoformat())

        else:
            return api_response(False, f"Unknown section: {section}")

        # Build audit details, excluding sensitive values
        safe_keys = list(settings.keys())
        audit_details = {"section": section, "keys": safe_keys}
        if section == "email" and "smtpPassword" in settings:
            audit_details["smtpPasswordChanged"] = True
        log_action(actor_user_id, "SETTINGS_UPDATE", "settings", None, audit_details)
        return api_response(True, f"Settings for {section} saved successfully")

    except Exception as e:
        return api_response(False, f"Error saving settings: {str(e)}")

def send_test_email(email: str) -> object:
    """Send a test email to verify SMTP configuration.

    Uses the currently saved SMTP settings to send a test message.
    Supports both SSL/TLS (port 465) and STARTTLS (other ports).

    Args:
        email: The recipient email address.

    Returns:
        Response indicating whether the email was sent successfully
        or describing the error that occurred.
    """
    try:
        from helpers.settings_handler import get_setting
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

def test_ad_connection(username: str, password: str) -> object:
    """Test AD/LDAP connection and return all attributes for the matched user.

    Uses the currently saved LDAP settings to bind and search. Returns all
    attributes from the LDAP response so the admin can verify the configuration.
    Does not create users, check whitelists, or modify any database state.

    Args:
        username: The LDAP username to test with.
        password: The LDAP password to test with.

    Returns:
        Response with full LDAP attributes on success, or error message on failure.
    """
    try:
        import ldap
        from helpers.settings_handler import get_setting

        # Get LDAP settings from database
        ldap_url = get_setting('auth.ldap.url')
        username_format = get_setting('auth.ldap.usernameFormat')
        password_format = get_setting('auth.ldap.passwordFormat')
        ldap_domain = get_setting('auth.ldap.domain')
        search_method = get_setting('auth.ldap.searchMethod')
        account_field = get_setting('auth.ldap.accountField')
        email_field = get_setting('auth.ldap.emailField')

        # Check if LDAP is properly configured
        if not all([ldap_url, username_format, password_format, ldap_domain, search_method, account_field, email_field]):
            return api_response(False, "LDAP is not properly configured. Please fill in all LDAP settings and save before testing.")

        # Disable certificate checks (mirrors get_ldap_user behavior)
        ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER)
        conn = ldap.initialize(ldap_url)
        conn.set_option(ldap.OPT_NETWORK_TIMEOUT, 6)
        conn.set_option(ldap.OPT_TIMEOUT, 6)
        conn.set_option(ldap.OPT_REFERRALS, ldap.OPT_OFF)

        # Bind with provided credentials
        bind_dn = username_format.replace("{username}", username)
        bind_pw = password_format.replace("{password}", password)
        conn.simple_bind_s(bind_dn, bind_pw)

        # Search for the user, requesting ALL attributes
        search_filter = search_method.replace("{username}", username)
        result = conn.search_s(ldap_domain, ldap.SCOPE_SUBTREE, search_filter)

        conn.unbind_s()

        if not result or not result[0] or not result[0][1]:
            return api_response(False, "LDAP bind succeeded but no user entry was found matching the search filter.")

        # Decode all attributes from bytes to strings for JSON serialization
        dn = result[0][0]
        raw_attrs = result[0][1]
        decoded_attrs = {}
        for key, values in raw_attrs.items():
            decoded_values = []
            for v in values:
                try:
                    decoded_values.append(v.decode('utf-8'))
                except (UnicodeDecodeError, AttributeError):
                    decoded_values.append(base64.b64encode(v).decode('ascii'))
            if len(decoded_values) == 1:
                decoded_attrs[key] = decoded_values[0]
            else:
                decoded_attrs[key] = decoded_values

        response_data = {
            "dn": dn,
            "attributes": decoded_attrs
        }

        return api_response(True, "LDAP connection test successful", response_data)

    except ldap.INVALID_CREDENTIALS:
        return api_response(False, "Invalid credentials: The username or password was rejected by the LDAP server.")
    except ldap.SERVER_DOWN:
        return api_response(False, "Server unreachable: Failed to connect to the LDAP server. Check the URL and ensure the server is running.")
    except Exception as e:
        return api_response(False, f"LDAP connection test failed: {str(e)}")

def get_audit_logs(request) -> object:
    """Retrieve paginated audit log entries with optional filtering.

    Delegates to the audit_log helper which handles query building,
    filtering, pagination, and response formatting.

    Args:
        request: AuditLogRequest with pagination, sorting, and filter params.

    Returns:
        Response with paginated logs, totalItems, and retentionDays.
    """
    return get_audit_logs_helper(request)


def get_analytics(request) -> object:
    """Retrieve usage analytics data aggregated from audit logs and reservations.

    Runs five aggregation queries over the requested time range to produce
    chart-ready datasets: daily activity trends, reservation status breakdown,
    action type counts, top users by activity, and reservations per server.

    Args:
        request: AnalyticsRequest with a ``days`` field (0 = all time).

    Returns:
        Response with dailyActivity, reservationStatuses, actionCounts,
        topUsers, reservationsByComputer, and retentionDays.
    """
    from helpers.settings_handler import settings_handler

    now = datetime.datetime.now(timezone.utc)

    # Parse date range filters
    parsed_from = None
    parsed_to = None
    if request.dateFrom:
        try:
            parsed_from = parser.parse(request.dateFrom)
        except (ValueError, TypeError):
            return api_response(False, "Invalid dateFrom value.")
    if request.dateTo:
        try:
            parsed_to = parser.parse(request.dateTo)
        except (ValueError, TypeError):
            return api_response(False, "Invalid dateTo value.")

    def _apply_audit_date_filter(stmt, date_col):
        """Apply dateFrom/dateTo filters to a statement."""
        result = stmt
        if parsed_from:
            result = result.where(date_col >= parsed_from)
        if parsed_to:
            result = result.where(date_col < parsed_to + timedelta(days=1))
        return result

    reservation_actions = ["RESERVATION_CREATE", "RESERVATION_CANCEL",
                           "RESERVATION_EXTEND", "RESERVATION_RESTART"]
    login_actions = ["LOGIN", "LOGIN_FAILED"]

    with Session() as session:
        # --- Query 1: Daily activity (line chart) ---
        daily_stmt = select(
            func.date(AuditLog.createdAt).label("day"),
            func.sum(case(
                (AuditLog.action.in_(reservation_actions), 1),
                else_=0
            )).label("reservations"),
            func.sum(case(
                (AuditLog.action.in_(login_actions), 1),
                else_=0
            )).label("logins"),
        )
        daily_stmt = _apply_audit_date_filter(daily_stmt, AuditLog.createdAt)
        daily_stmt = daily_stmt.group_by(func.date(AuditLog.createdAt)).order_by(func.date(AuditLog.createdAt))
        daily_rows = session.execute(daily_stmt).all()

        # Build a dict of existing days for gap-filling
        daily_map = {}
        for row in daily_rows:
            day_str = str(row.day)
            daily_map[day_str] = {
                "day": day_str,
                "reservations": int(row.reservations or 0),
                "logins": int(row.logins or 0),
            }

        # Fill in zero-value days for gaps in the range
        daily_activity = []
        if parsed_from:
            start_date = parsed_from.date()
        elif daily_rows:
            start_date = daily_rows[0].day
        else:
            start_date = now.date()

        if parsed_to:
            end_date = parsed_to.date()
        else:
            end_date = now.date()

        current = start_date
        while current <= end_date:
            day_str = str(current)
            if day_str in daily_map:
                daily_activity.append(daily_map[day_str])
            else:
                daily_activity.append({"day": day_str, "reservations": 0, "logins": 0})
            current += timedelta(days=1)

        # --- Query 2: Reservation status breakdown (doughnut chart) ---
        status_stmt = select(Reservation.status, func.count().label("count"))
        status_stmt = _apply_audit_date_filter(status_stmt, Reservation.createdAt)
        status_stmt = status_stmt.group_by(Reservation.status)
        status_rows = session.execute(status_stmt).all()

        reservation_statuses = {}
        for row in status_rows:
            reservation_statuses[row.status] = row.count

        # --- Query 3: Action type counts (bar chart) ---
        action_stmt = select(
            AuditLog.action,
            func.count().label("count")
        )
        action_stmt = _apply_audit_date_filter(action_stmt, AuditLog.createdAt)
        action_stmt = action_stmt.group_by(AuditLog.action).order_by(func.count().desc())
        action_rows = session.execute(action_stmt).all()

        action_counts = [{"action": row.action, "count": row.count} for row in action_rows]

        # --- Query 4: Top 10 users by activity (bar chart) ---
        users_stmt = select(
            User.email,
            User.name,
            func.count().label("count")
        ).select_from(AuditLog).join(User, AuditLog.userId == User.userId)
        users_stmt = _apply_audit_date_filter(users_stmt, AuditLog.createdAt)
        users_stmt = users_stmt.group_by(AuditLog.userId, User.email, User.name).order_by(func.count().desc()).limit(10)
        user_rows = session.execute(users_stmt).all()

        top_users = [{"email": row.email, "name": row.name, "count": row.count} for row in user_rows]

        # --- Query 5: Reservations by computer/server (bar chart) ---
        computer_stmt = select(
            Computer.name.label("computerName"),
            func.count().label("count")
        ).select_from(Reservation).join(Computer, Reservation.computerId == Computer.computerId)
        computer_stmt = _apply_audit_date_filter(computer_stmt, Reservation.createdAt)
        computer_stmt = computer_stmt.group_by(Reservation.computerId, Computer.name).order_by(func.count().desc())
        computer_rows = session.execute(computer_stmt).all()

        reservations_by_computer = [{"computerName": row.computerName, "count": row.count} for row in computer_rows]

    retention_days = settings_handler.get_setting("auditLog.retentionDays")

    return api_response(True, "Analytics data fetched.", {
        "dailyActivity": daily_activity,
        "reservationStatuses": reservation_statuses,
        "actionCounts": action_counts,
        "topUsers": top_users,
        "reservationsByComputer": reservations_by_computer,
        "retentionDays": retention_days,
    })

def get_user_anonymize_info(user_id: int) -> object:
    """Get information for the user anonymization confirmation dialog.

    Returns the user's email, name, active reservation count, audit log
    entry count, and whether the user has an admin role so the frontend
    can show an informative confirmation dialog before anonymizing.

    Args:
        user_id: Database ID of the user to check.

    Returns:
        Response with email, name, activeReservations, auditLogEntries,
        and isAdmin, or an error if the user is not found.
    """
    with Session() as session:
        user = session.execute(
            select(User).options(joinedload(User.roles)).where(User.userId == user_id)
        ).unique().scalar_one_or_none()
        if user is None:
            return api_response(False, "User not found.")
        if user.removed is True:
            return api_response(False, "User is already anonymized.")

        active_count = session.execute(
            select(func.count()).select_from(Reservation).where(
                Reservation.userId == user_id,
                Reservation.status.in_(["reserved", "started"])
            )
        ).scalar() or 0

        audit_count = session.execute(
            select(func.count()).select_from(AuditLog).where(
                AuditLog.userId == user_id
            )
        ).scalar() or 0

        is_admin = any(role.name == "admin" for role in user.roles)

        return api_response(True, "Anonymize info fetched.", {
            "email": user.email,
            "name": user.name,
            "activeReservations": active_count,
            "auditLogEntries": audit_count,
            "isAdmin": is_admin,
        })

def anonymize_user(user_id: int, actor_user_id: int = None) -> object:
    """Anonymize a user's personal data (GDPR soft-deletion).

    Replaces all personally identifiable information with anonymous
    placeholders while preserving referential integrity. Clears private
    data from related tables (reservations, containers, audit logs).

    Args:
        user_id: The ID of the user to anonymize.
        actor_user_id: The userId of the admin performing the action.

    Returns:
        Response indicating success or failure with an appropriate message.
    """
    if user_id == actor_user_id:
        return api_response(False, "Cannot anonymize your own account.")

    with Session() as session:
        user = session.execute(
            select(User).where(User.userId == user_id)
        ).scalar_one_or_none()
        if user is None:
            return api_response(False, "User not found.")
        if user.removed is True:
            return api_response(False, "User is already anonymized.")

        original_email = user.email

        # Anonymize user record
        user.removed = True
        user.email = f"deleted_user_{user_id}@removed.local"
        user.name = None
        user.password = None
        user.passwordSalt = None
        user.loginToken = None
        user.loginTokenCreatedAt = None
        user.sshPublicKey = None
        user.startScriptPath = None
        user.stopScriptPath = None

        # Clear reservation descriptions
        session.execute(
            update(Reservation).where(Reservation.userId == user_id)
            .values(description=None)
        )

        # Clear SSH passwords on reserved containers linked to this user's reservations
        user_reserved_container_ids = select(Reservation.reservedContainerId).where(
            Reservation.userId == user_id
        )
        session.execute(
            update(ReservedContainer).where(
                ReservedContainer.reservedContainerId.in_(user_reserved_container_ids)
            ).values(sshPassword=None)
        )

        # Scrub audit log entries (clear PII but keep the action record)
        session.execute(
            update(AuditLog).where(AuditLog.userId == user_id)
            .values(ipAddress=None, details=None)
        )

        # Delete role assignments
        session.execute(
            delete(UserRole).where(UserRole.userId == user_id)
        )

        # Remove from whitelist and blacklist
        session.execute(
            delete(UserWhitelist).where(UserWhitelist.email == original_email)
        )
        session.execute(
            delete(UserBlacklist).where(UserBlacklist.email == original_email)
        )

        session.commit()

    log_action(actor_user_id, "USER_ANONYMIZE", "user", user_id,
               {"userId": user_id})
    return api_response(True, "User removed and data anonymized successfully.")
