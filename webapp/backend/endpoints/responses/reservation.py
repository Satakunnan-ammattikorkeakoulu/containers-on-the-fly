"""Response handlers for reservation management endpoints.

Provides business logic for creating, viewing, extending, cancelling, and
restarting container reservations. Includes hardware availability checking
with role-based limits, calendar timeline views, and connection detail
retrieval for active reservations.
"""

from database import Session, Computer, User, Reservation, Container, ReservedContainer, ReservedHardwareSpec, HardwareSpec, ServerStatus
from helpers.email_notifications import generate_connection_text
from helpers.server import api_response, orm_to_dict
from helpers.logger import log
from helpers.auth import is_admin
from helpers.tables.audit_log import (
    log_action, get_user_reservation_activity,
    get_user_unread_activity_count, mark_user_activity_seen,
    UNREAD_ACTIVITY_COUNT_CAP,
)
from dateutil import parser
from dateutil.relativedelta import *
import datetime
from datetime import timezone, timedelta
from endpoints.models.reservation import ReservationFilters, UserReservationRequest
from sqlalchemy import select, delete, func, cast, String
from sqlalchemy.orm import joinedload
from helpers.pagination import apply_pagination, get_total_count
from helpers.settings_handler import get_setting

def get_public_computers(user_id: int = None) -> object:
  """Return names and IP addresses of all non-removed computers visible to the user.

  Admins see all computers (including non-public ones). Regular users
  only see public computers.

  Args:
      user_id: The requesting user's ID. Used to check admin status.

  Returns:
      Response with a list of dicts, each containing ``name`` and ``ip``.
  """
  user_is_admin = is_admin(user_id) if user_id else False
  with Session() as session:
    query = select(Computer).where(Computer.removed.isnot(True))
    if not user_is_admin:
      query = query.where(Computer.public.is_(True))
    computers = session.execute(query).scalars().all()

    result = [{"name": c.name, "ip": c.ip} for c in computers]
    return api_response(True, "Computers retrieved", result)

# TODO: Should be able to send a computer here and get the available hardware specs for it.
# TODO: Should also be able to only fail there is not enough resources any computer. Right now it fails if any of the computers are out of resources for the given time period.
def get_available_hardware(date : str, duration : int, reducable_specs : dict = None, is_admin = False, ignored_reservation_id : int = None, user_id : int = None, target_computer_id : int = None) -> object:
  """Calculate available hardware resources for a given time slot.

  Fetches all public computers and their hardware specs, subtracts
  resources already reserved during the requested time period, and
  applies role-based or default user limits. Admin users receive
  full maximum amounts without restrictions.

  Each returned computer dict has a ``fullyBooked`` flag indicating
  whether at least one of its specs has insufficient capacity for the
  requested time slot. The listing path returns success as long as at
  least one computer has capacity; the validation path returns success
  as long as the target computer has capacity.

  Args:
      date: The reservation start date as an ISO-format string.
      duration: The reservation duration in hours.
      reducable_specs: Optional dict of {hardwareSpecId: amount} to
          additionally subtract from availability (used when checking
          extension feasibility).
      is_admin: Whether the requesting user has admin privileges.
      ignored_reservation_id: A reservation ID to exclude from
          conflict checking (used when editing an existing reservation).
      user_id: The requesting user's ID, used to look up role-based
          hardware limits.
      target_computer_id: When set together with ``reducable_specs``,
          over-allocation errors are only raised for specs that belong
          to this computer; other computers' availability is ignored.
          Callers that know exactly which computer they intend to
          reserve against should pass this so that an unrelated
          computer being fully booked cannot fail their request.

  Returns:
      Response with computers list (each with adjusted hardwareSpecs
      and a ``fullyBooked`` flag) and containers list on success, or an
      error message if resources are insufficient for the requested
      time period.
  """
  date = parser.parse(date)
  end_date = date+relativedelta(hours=+duration)

  # Fetch all required data and process inside session scope
  with Session() as session:
    reservations = session.execute(
      select(Reservation)
      .options(
        joinedload(Reservation.reservedHardwareSpecs).joinedload(ReservedHardwareSpec.hardwareSpec)
      )
      .where(
        Reservation.startDate < end_date,
        Reservation.endDate > date,
        Reservation.isLowPriority == False,
        (Reservation.status == "reserved") | (Reservation.status == "started")
      )
    ).unique().scalars().all()
    computer_query = (
      select(Computer)
      .options(joinedload(Computer.hardwareSpecs), joinedload(Computer.status))
      .where(Computer.removed.isnot(True))
    )
    if not is_admin:
      computer_query = computer_query.where(Computer.public.is_(True))
    all_computers = session.execute(computer_query).unique().scalars().all()
    all_containers = session.execute(
      select(Container).options(joinedload(Container.containerPorts))
    ).unique().scalars().all()

    # All reserved hardware specs for the given time period will be listed here
    removable_hardware_specs = {}
    for res in reservations:
      if res.reservationId == ignored_reservation_id: continue
      for spec in res.reservedHardwareSpecs:
        hardware_spec_id = spec.hardwareSpec.hardwareSpecId
        amount = spec.amount

        if hardware_spec_id not in removable_hardware_specs:
          removable_hardware_specs[hardware_spec_id] = amount
        else:
          removable_hardware_specs[hardware_spec_id] += amount

    # Reduce the available hardware specs by the given reducable specs, if any
    if reducable_specs != None:
      for key, val in reducable_specs.items():
        int_key = int(key)
        if val == 0: continue
        if int_key not in removable_hardware_specs:
          removable_hardware_specs[int_key] = val
        else:
          removable_hardware_specs[int_key] += val

    threshold_minutes = int(get_setting("docker.serverOnlineThresholdMinutes"))
    now_utc = datetime.datetime.now(timezone.utc)

    computers = []

    for computer in all_computers:
      comp_dict = orm_to_dict(computer)
      comp_dict["hardwareSpecs"] = []
      for spec in computer.hardwareSpecs:
        comp_dict["hardwareSpecs"].append(orm_to_dict(spec))

      status = computer.status
      raw_last_ping = status.lastUpdatedAt if status else None
      if raw_last_ping is not None:
        # DateTime(timezone=True) may come back naive from MariaDB; normalize
        # to tz-aware UTC only for the age comparison. The ISO string we
        # return mirrors get_server_monitoring, which emits raw .isoformat()
        # so the frontend's "append Z" convention continues to work.
        aware_last_ping = raw_last_ping if raw_last_ping.tzinfo is not None else raw_last_ping.replace(tzinfo=timezone.utc)
        age_seconds = (now_utc - aware_last_ping).total_seconds()
        comp_dict["lastPingAt"] = raw_last_ping.isoformat()
        comp_dict["isOnline"] = age_seconds < threshold_minutes * 60
      else:
        comp_dict["lastPingAt"] = None
        comp_dict["isOnline"] = False

      computers.append(comp_dict)

    containers = []
    for container in all_containers:
      container_dict = orm_to_dict(container)
      # Strip build-related fields not needed by regular users
      container_dict.pop("dockerfileCommands", None)
      container_dict.pop("buildLog", None)
      container_dict["containerPorts"] = [
        {
          "containerPortId": p.containerPortId,
          "serviceName": p.serviceName,
          "port": p.port,
          "portType": p.portType,
        }
        for p in container.containerPorts
      ]
      containers.append(container_dict)

    # Get user's roles and their hardware limits (in the same session)
    user_role_limits = {}
    user_role_limits_low = {}
    if user_id:
      from database import RoleHardwareLimit, UserRole
      user_roles = session.execute(select(UserRole).where(UserRole.userId == user_id)).scalars().all()
      role_ids = [ur.roleId for ur in user_roles]

      if role_ids:
        role_limits = session.execute(select(RoleHardwareLimit).where(
          RoleHardwareLimit.roleId.in_(role_ids)
        )).scalars().all()

        # Build a dict of hardwareSpecId -> max limit across all roles
        for limit in role_limits:
          spec_id = limit.hardwareSpecId
          if limit.maximumAmountForRole is not None:
            if spec_id not in user_role_limits or limit.maximumAmountForRole > user_role_limits[spec_id]:
              user_role_limits[spec_id] = limit.maximumAmountForRole

          # Low-priority falls back to the normal override on rows where it is NULL
          low_value = limit.maximumAmountForRoleLowPriority if limit.maximumAmountForRoleLowPriority is not None else limit.maximumAmountForRole
          if low_value is not None:
            if spec_id not in user_role_limits_low or low_value > user_role_limits_low[spec_id]:
              user_role_limits_low[spec_id] = low_value

  # Set all user maximums to max for admins
  if (is_admin == True):
    for computer in computers:
      for spec in computer["hardwareSpecs"]:
        spec["maximumAmountForUser"] = spec["maximumAmount"]
        spec["maximumAmountForUserLowPriority"] = spec["maximumAmount"]
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

        # Low-priority max: role override (with fallback) if present, otherwise the HardwareSpec column
        if spec["hardwareSpecId"] in user_role_limits_low:
          spec["maximumAmountForUserLowPriority"] = min(user_role_limits_low[spec["hardwareSpecId"]], spec["maximumAmount"])
        # No GPU-1-cap for low-priority — low-priority is meant to allow more, not less

  all_fully_booked = len(computers) > 0
  for computer in computers:
    computer_fully_booked = False
    is_target = (target_computer_id is None) or (computer["computerId"] == target_computer_id)

    for spec in computer["hardwareSpecs"]:
      # Expose the reserved-by-normal-reservations amount so the reserve page
      # can show a "currently reserved" hint when low-priority is toggled on.
      spec["reservedAmount"] = removable_hardware_specs.get(spec["hardwareSpecId"], 0)

      if spec["hardwareSpecId"] in removable_hardware_specs:
        spec["maximumAmount"] -= removable_hardware_specs[spec["hardwareSpecId"]]

        # Two semantically different callers share this function:
        #   - Listing mode (reducable_specs is None): the leftover represents
        #     what is still bookable; a slot smaller than minimumAmount is not
        #     useful to anyone, so flag the computer as fully booked.
        #   - Validation mode (reducable_specs was passed): the leftover is
        #     "what remains after the user's request lands", so the request
        #     fits iff the leftover is >= 0. Comparing against minimumAmount
        #     here would forbid users from taking the last slice of a resource.
        if reducable_specs is not None:
          over_allocated = spec["maximumAmount"] < 0
        else:
          over_allocated = spec["maximumAmount"] < spec["minimumAmount"]

        if over_allocated:
          computer_fully_booked = True
          # In validation mode, surface this as a hard error — but only if it
          # belongs to the target computer the caller actually cares about.
          # Other computers' state should not poison a request that targets a
          # specific machine.
          if reducable_specs is not None and is_target:
            log.warning(f"Spec {spec['type']} on computer {computer['computerId']} is over-allocated ({spec['maximumAmount']})")
            spec_max = spec['maximumAmount']
            if spec_max < 0: spec_max = 0
            if spec["type"] == "ram":
              spec_message = f"Available: {spec_max} {spec['format']} {spec['type']}."
            else:
              spec_message = f"Available: {spec_max} {spec['type']}."
            return api_response(False, f"Not enough resources to make a reservation: {spec['type']}. {spec_message}")

        # Clamp leftover and cap user max only after the over-allocation check
        if spec["maximumAmount"] < 0:
          spec["maximumAmount"] = 0
        if spec["maximumAmountForUser"] > spec["maximumAmount"]:
          spec["maximumAmountForUser"] = spec["maximumAmount"]
        # Low-priority max is intentionally NOT clamped here — low-priority
        # reservations are allowed to exceed current remaining availability.

    computer["fullyBooked"] = computer_fully_booked
    if not computer_fully_booked:
      all_fully_booked = False

  # Listing mode only: surface a global error when every public computer is
  # unbookable for the requested slot. If at least one computer has capacity,
  # return success and let the frontend disable the fully-booked cards.
  if reducable_specs is None and all_fully_booked:
    return api_response(False, "No public computer has enough resources for the requested time slot.")

  return api_response(True, "Hardware resources fetched.", {
    "computers": computers,
    "containers": containers,
    "onlineThresholdMinutes": threshold_minutes,
  })

def get_own_reservations(userId: int, request: UserReservationRequest) -> object:
  """Retrieve paginated reservations belonging to a specific user.

  Fetches reservations from the last 90 days (or with future end dates),
  with server-side pagination, sorting, and filtering. Returns unfiltered
  status counts and the user's active reservation count for limit
  enforcement.

  Args:
      userId: The ID of the user whose reservations to fetch.
      request: Pagination, sorting, and filter parameters. Supported
          filter keys: status, dateFrom, dateTo, reservationType
          ("normal" or "lowPriority").

  Returns:
      Response with paginated reservations, totalItems, statusCounts,
      and activeReservationCount.
  """
  filters = request.filters
  status_filter = filters.get("status", "")
  date_from_filter = str(filters.get("dateFrom", "")).strip()
  date_to_filter = str(filters.get("dateTo", "")).strip()
  reservation_type_filter = str(filters.get("reservationType", "")).strip()

  allowed_sort_keys = {
      "reservationId": Reservation.reservationId,
      "status": Reservation.status,
      "startDate": Reservation.startDate,
      "endDate": Reservation.endDate,
  }

  def _apply_date_filter(query):
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

  def _apply_status_filter(query):
      if status_filter:
          if status_filter == "error":
              query = query.where(Reservation.status.in_(["error", "restart_error"]))
          else:
              query = query.where(Reservation.status == status_filter)
      return query

  def _apply_reservation_type_filter(query):
      if reservation_type_filter == "normal":
          query = query.where(Reservation.isLowPriority == False)
      elif reservation_type_filter == "lowPriority":
          query = query.where(Reservation.isLowPriority == True)
      return query

  def _apply_user_reservation_filters(query):
      """Apply shared filters for user reservation queries."""
      query = _apply_status_filter(query)
      query = _apply_date_filter(query)
      query = _apply_reservation_type_filter(query)
      return query

  with Session() as session:
    # Status counts (scoped to date + reservation-type filters, but NOT status filter —
    # so the dropdown shows counts for each status within the other active filters).
    status_counts = {"reserved": 0, "started": 0, "stopping": 0, "stopped": 0, "error": 0, "paused": 0}
    status_query = select(Reservation.status, func.count()).where(Reservation.userId == userId)
    status_query = _apply_date_filter(status_query)
    status_query = _apply_reservation_type_filter(status_query)
    count_rows = session.execute(status_query.group_by(Reservation.status)).all()
    for s, c in count_rows:
        if s == "restart_error":
            status_counts["error"] += c
        elif s in status_counts:
            status_counts[s] = c

    # Reservation-type counts (scoped to date + status filters, but NOT reservation-type).
    reservation_type_counts = {"normal": 0, "lowPriority": 0}
    type_query = select(Reservation.isLowPriority, func.count()).where(Reservation.userId == userId)
    type_query = _apply_date_filter(type_query)
    type_query = _apply_status_filter(type_query)
    for is_low, c in session.execute(type_query.group_by(Reservation.isLowPriority)).all():
        if is_low:
            reservation_type_counts["lowPriority"] = c
        else:
            reservation_type_counts["normal"] = c

    # Active reservation count (no date scope — for limit enforcement)
    active_count = session.execute(
        select(func.count())
        .select_from(Reservation)
        .where(
            Reservation.userId == userId,
            Reservation.status.in_(["reserved", "started", "paused"]),
        )
    ).scalar()

    # Unread activity count (events newer than the user's last activity-view).
    # Used by the frontend to render a badge next to the "Activity" link.
    user_row = session.execute(
        select(User.activityLastSeenAt).where(User.userId == userId)
    ).first()
    user_last_seen = user_row[0] if user_row else None
    unread_activity_count = get_user_unread_activity_count(
        session, userId, user_last_seen
    )
    unread_activity_capped = unread_activity_count > UNREAD_ACTIVITY_COUNT_CAP
    if unread_activity_capped:
        unread_activity_count = UNREAD_ACTIVITY_COUNT_CAP

    # Build filtered base query
    base_filtered = select(Reservation).where(Reservation.userId == userId)
    base_filtered = _apply_user_reservation_filters(base_filtered)

    # Total count of filtered results
    total_items = get_total_count(session, base_filtered)

    # Paginate IDs first (subquery pattern to avoid joinedload + LIMIT issues)
    id_stmt = select(Reservation.reservationId).where(Reservation.userId == userId)
    id_stmt = _apply_user_reservation_filters(id_stmt)
    id_stmt = apply_pagination(
        id_stmt, request.sortBy, request.page,
        request.itemsPerPage, allowed_sort_keys
    )
    paginated_ids = [row[0] for row in session.execute(id_stmt).all()]

    # Load full reservation objects for the paginated IDs
    reservations = []
    if paginated_ids:
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
            res["computerName"] = reservation.computer.name
            res["reservedContainer"] = orm_to_dict(reservation.reservedContainer)
            container_dict = orm_to_dict(reservation.reservedContainer.container)
            # Strip build-related fields not needed by regular users
            container_dict.pop("dockerfileCommands", None)
            container_dict.pop("buildLog", None)
            res["reservedContainer"]["container"] = container_dict
            res["reservedContainer"]["reservedPorts"] = []
            res["shmSizePercent"] = reservation.reservedContainer.shmSizePercent if reservation.reservedContainer.shmSizePercent is not None else 50
            res["ramDiskSizePercent"] = reservation.reservedContainer.ramDiskSizePercent if reservation.reservedContainer.ramDiskSizePercent is not None else 0
            # Paused LP reservations keep their port allocations so they can
            # resume on the same outside ports; expose them to the UI too.
            if reservation.status in ("started", "paused"):
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

  return api_response(True, "Reservations fetched.", {
      "reservations": reservations,
      "totalItems": total_items,
      "statusCounts": status_counts,
      "reservationTypeCounts": reservation_type_counts,
      "activeReservationCount": active_count,
      "unreadActivityCount": unread_activity_count,
      "unreadActivityCapped": unread_activity_capped,
  })

def get_own_activity(userId: int, request) -> object:
  """Retrieve paginated audit log entries for the user's own reservations.

  Returns chronological reservation events (create, cancel, extend,
  restart, paused, resumed, started, error, auto-stopped) for the
  authenticated user. Events initiated by the system (daemon) are
  included alongside events initiated by the user or an admin.

  Args:
      userId: The ID of the user whose activity to fetch.
      request: Pagination, sorting, and filter parameters. Supported
          filter keys: action, dateFrom, dateTo.

  Returns:
      Response with paginated logs, totalItems, retentionDays,
      reservationSummaries, and activityLastSeenAt.
  """
  return get_user_reservation_activity(userId, request)

def mark_own_activity_seen(userId: int) -> object:
  """Mark the user's activity feed as seen up to the current moment.

  Updates ``User.activityLastSeenAt`` to NOW() and returns the previous
  value so the caller can highlight rows newer than that snapshot.

  Args:
      userId: The ID of the requesting user.

  Returns:
      Response containing ``previousLastSeenAt`` (ISO string or None).
  """
  return mark_user_activity_seen(userId)

def get_own_reservation_details(reservationId : int, userId : int) -> object:
  """Retrieve connection details for a specific reservation.

  Returns structured connection information including SSH credentials,
  port mappings, container metadata, and formatted connection text.
  Admin users can view details for any reservation; regular users
  can only view their own.

  Args:
      reservationId: The ID of the reservation.
      userId: The ID of the requesting user (used for ownership check).

  Returns:
      Response with connectionText (HTML-formatted) and connectionDetails
      dict containing IP, SSH password/port, other service ports,
      end date, instructions, and container info.
  """
  with Session() as session:
    # Check that the reservation exists and is owned by the current user (admins can view any reservation)
    if is_admin(userId):
      reservation = session.execute(select(Reservation).where( Reservation.reservationId == reservationId )).scalar_one_or_none()
    else:
      reservation = session.execute(select(Reservation).where( Reservation.reservationId == reservationId, Reservation.userId == userId )).scalar_one_or_none()
    if (reservation == None):
      return api_response(False, "Reservation not found.")

    ports_for_email = []

    # Set bindable ports for the reservation container
    for port in reservation.reservedContainer.reservedContainerPorts:
      service_name = port.containerPort.serviceName
      outside_port = port.outsidePort
      local_port = port.containerPort.port
      port_type = port.containerPort.portType
      container_port_id = port.containerPort.containerPortId
      ports_for_email.append({
        "serviceName": service_name, "localPort": local_port,
        "outsidePort": outside_port, "portType": port_type,
        "containerPortId": container_port_id
      })

    container_username = reservation.reservedContainer.container.containerUsername or "user"
    container = reservation.reservedContainer.container

    # Pass a copy of ports list — generate_connection_text mutates it by removing the SSH entry
    connection_text = generate_connection_text(
      container.imageName,
      reservation.computer.ip,
      list(ports_for_email),
      reservation.reservedContainer.sshPassword,
      False,
      "",
      reservation.endDate,
      container_username
      )

    connection_text = connection_text.replace("\n", "<br>")

    # Build structured connection details for the frontend
    ssh_port = None
    ssh_password = reservation.reservedContainer.sshPassword
    other_ports = []
    for port in ports_for_email:
      if port["portType"] == "SSH":
        ssh_port = port["outsidePort"]
      else:
        other_ports.append({
          "serviceName": port["serviceName"],
          "outsidePort": port["outsidePort"],
          "localPort": port["localPort"],
          "portType": port["portType"],
          "containerPortId": port["containerPortId"],
        })

    # Resolve effective primary port: use configured value, or fallback for
    # old containers that have no favorite set.
    # If SSH was already detected by portType, no fallback needed — the frontend
    # shows SSH as primary automatically. Otherwise pick the best port:
    # local port 22 → service named "SSH" → first port available.
    effective_primary_port_id = container.primaryConnectionPortId
    if effective_primary_port_id is None and not ssh_port and ports_for_email:
      port_on_22 = next((p for p in ports_for_email if p["localPort"] == 22), None)
      port_named_ssh = next((p for p in ports_for_email if p["serviceName"].upper() == "SSH"), None)
      fallback_port = port_on_22 or port_named_ssh or ports_for_email[0]
      effective_primary_port_id = fallback_port["containerPortId"]

    instructions = ""
    try:
      instructions = get_setting('instructions.email') or ""
    except Exception:
      pass

    # Fetch system-wide SSH connection methods
    ssh_methods = None
    try:
      ssh_methods = get_setting('connection.sshMethods')
    except Exception:
      pass

    connection_details = {
      "ip": reservation.computer.ip,
      "computerName": reservation.computer.name,
      "sshPassword": ssh_password,
      "sshPort": ssh_port,
      "sshMethods": ssh_methods,
      "otherPorts": other_ports,
      "primaryConnectionPortId": effective_primary_port_id,
      "endDate": reservation.endDate.isoformat() if reservation.endDate else None,
      "instructions": instructions,
      "containerName": container.name,
      "containerDescription": container.description,
      "containerImage": container.imageName,
      "username": container_username,
      "hasSshPublicKey": bool(reservation.user.sshPublicKey),
    }

  return api_response(True, "Details fetched.", { "connectionText": connection_text, "connectionDetails": connection_details } )

def get_current_reservations() -> object:
  """Retrieve all currently active or recently ended reservations.

  Fetches reservations with status 'reserved' or 'started' that ended
  within the last 5 days. Used for the reservation calendar to show
  ongoing and very recent reservations with their hardware specs.

  Returns:
      Response with a list of reservation summary dicts including
      reservationId, dates, computer info, and hardware specs.
  """
  reservations = []

  def time_now(): return datetime.datetime.now(datetime.timezone.utc)
  min_end_date = time_now() - timedelta(days=5)

  with Session() as session:
    query = session.execute(
      select(Reservation)
      .options(joinedload(Reservation.reservedHardwareSpecs))
      .where(
        Reservation.status.in_(["reserved", "started", "paused"]),
        (Reservation.endDate > min_end_date),
      )
    ).unique().scalars().all()
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
        "isLowPriority": reservation.isLowPriority,
        "lowPriorityLevel": reservation.lowPriorityLevel,
      }
      reservations.append(res)

  return api_response(True, "Current reservations fetched.", { "reservations": reservations })

def create_reservation(userId : int, date: str, duration: int, computerId: int, containerId: int, hardwareSpecs, adminReserveUserEmail: str = None, description: str = None, shmSizePercent: int = 50, ramDiskSizePercent: int = 0, isLowPriority: bool = False, lowPriorityLevel: int = 1, startScriptPath: str = "", stopScriptPath: str = ""):
  """Create a new container reservation with hardware resource allocation.

  Validates all inputs including duration limits, resource availability,
  user permissions, role-based hardware limits, and active reservation
  caps. Admins can reserve on behalf of other users via email address.

  Args:
      userId: The ID of the user creating the reservation.
      date: The reservation start date as an ISO-format string.
      duration: The reservation duration in hours.
      computerId: The ID of the target computer/server.
      containerId: The ID of the container image to use.
      hardwareSpecs: Dict of {hardwareSpecId: amount} for requested
          hardware resources (CPUs, RAM, GPUs).
      adminReserveUserEmail: Optional email to reserve on behalf of
          another user (admin only).
      description: Optional short description (max 40 characters).
      shmSizePercent: Shared memory size as percentage of allocated
          RAM (10-90, default 50).
      ramDiskSizePercent: RAM disk size as percentage of allocated
          RAM (0-60, default 0).
      isLowPriority: Whether this is a low-priority reservation that
          can be paused when normal reservations need resources.
      lowPriorityLevel: Sub-priority for LP reservations (1 = Standard,
          2 = Background, 3 = Idle). Higher numbers yield to lower
          numbers within the LP class. Forced to 1 when isLowPriority
          is False.
      startScriptPath: Absolute path to a start script inside the
          container (overrides user profile default if set).
      stopScriptPath: Absolute path to a stop script inside the
          container (overrides user profile default if set).

  Returns:
      Response indicating success with informByEmail flag, or an error
      message describing validation failure.
  """
  # Normalize: lowPriorityLevel is only meaningful when isLowPriority is True.
  if not isLowPriority:
    lowPriorityLevel = 1
  if not isinstance(lowPriorityLevel, int) or lowPriorityLevel < 1 or lowPriorityLevel > 3:
    return api_response(False, "Low-priority level must be 1, 2, or 3.")
  # Validate description length if provided
  if description and len(description) > 40:
    return api_response(False, "Description must be 40 characters or less.")
  
  # Validate SHM size percentage (minimum 10%, maximum 90%)
  if shmSizePercent < 10:
    return api_response(False, "SHM size must be at least 10% of allocated memory.")
  if shmSizePercent > 90:
    return api_response(False, "SHM size cannot exceed 90% of allocated memory.")
  
  # Validate RAM disk size percentage (minimum 0%, maximum 60%)
  if ramDiskSizePercent < 0:
    return api_response(False, "RAM disk size cannot be negative.")
  if ramDiskSizePercent > 60:
    return api_response(False, "RAM disk size cannot exceed 60% of allocated memory.")

  date = parser.parse(date)
  end_date = date+relativedelta(hours=+duration)

  # Phase 1: Validation session — resolve user, check limits, validate inputs
  is_user_admin = False
  resolved_user_id = userId

  with Session() as session:
    # Check that user exists
    user = session.execute(select(User).where( User.userId == userId )).scalar_one_or_none()
    if (user == None):
      return api_response(False, "User not found.")
    is_user_admin = is_admin(user.email)

    # Check that computer and container exists
    computer = session.execute(select(Computer).where( Computer.computerId == computerId )).scalar_one_or_none()
    if (computer == None):
      return api_response(False, "Computer not found.")
    container = session.execute(select(Container).where( Container.containerId == containerId )).scalar_one_or_none()
    if (container == None):
      return api_response(False, "Container not found.")

    # Verify user can access this container
    if container.public == False and not is_user_admin:
      return api_response(False, "Access denied to private container.")

    # Get user's role-based reservation limits
    from database import RoleReservationLimit, UserRole
    user_roles = session.execute(select(UserRole).where(UserRole.userId == user.userId)).scalars().all()
    role_ids = [ur.roleId for ur in user_roles]

    # Get all reservation limits for user's roles
    role_limits = session.execute(select(RoleReservationLimit).where(
        RoleReservationLimit.roleId.in_(role_ids)
    )).scalars().all() if role_ids else []

    # Apply defaults based on whether user is admin
    default_min_duration = 1  # 1 hour for all users
    default_max_duration = 1440 if is_user_admin else 48  # 60 days for admin, 48 hours for others
    default_max_active = 99 if is_user_admin else 1

    # Find the most permissive limits across all roles
    min_duration = default_min_duration
    max_duration = default_max_duration
    max_active_reservations = default_max_active

    for limit in role_limits:
        # For min duration, take the lowest value (most permissive)
        if limit.minDuration is not None:
            min_duration = min(min_duration, limit.minDuration)

        # For max duration, take the highest value (most permissive). Low-priority
        # reservations use lowPriorityMaxDuration if set, otherwise fall back to
        # the normal maxDuration on the same row.
        if isLowPriority:
            effective_max = limit.lowPriorityMaxDuration if limit.lowPriorityMaxDuration is not None else limit.maxDuration
        else:
            effective_max = limit.maxDuration
        if effective_max is not None:
            max_duration = max(max_duration, effective_max)

        # For max active reservations, take the highest value (most permissive)
        if limit.maxActiveReservations is not None:
            max_active_reservations = max(max_active_reservations, limit.maxActiveReservations)

    # Enforce the per-role "allow low-priority" gate. Admins bypass.
    # Only explicit RoleReservationLimit rows contribute opinions — if every
    # role the user has is silent (no row), LP is allowed (default-on posture
    # for fresh installs). If ANY role explicitly allows, LP is allowed
    # (most-permissive, so a trusted role can re-enable). If every explicit
    # opinion is False, LP is denied.
    if isLowPriority and not is_user_admin:
        lp_opinions = [limit.allowLowPriority for limit in role_limits]
        allow_lp = True if not lp_opinions else any(lp_opinions)
        if not allow_lp:
            return api_response(False, "Low-priority reservations are not enabled for your role.")

    # Check active reservations limit
    user_active_reservations = session.execute(
      select(func.count()).select_from(Reservation).where(
        (Reservation.userId == userId),
        Reservation.status.in_(["reserved", "started", "paused"])
      )
    ).scalar_one()
    if user_active_reservations >= max_active_reservations:
      return api_response(False, f"You can only have {max_active_reservations} active reservation(s) at a time.")

    # Validate duration against limits
    if duration < min_duration:
        return api_response(False, f"Minimum duration is {min_duration} hours.")
    if duration > max_duration:
        return api_response(False, f"Maximum duration is {max_duration} hours.")

    # If adminReserveUserEmail is given, check that the user exists
    if adminReserveUserEmail != None and adminReserveUserEmail != "" and is_user_admin == True:
      another_user = session.execute(select(User).where( User.email == adminReserveUserEmail )).scalar_one_or_none()
      if (another_user == None):
        return api_response(False, "User for which you tried to reserve for did not exist. Check the email address: " + adminReserveUserEmail)
      resolved_user_id = another_user.userId
    else:
      resolved_user_id = user.userId

  # Phase 2: Check hardware availability outside session to avoid nested sessions
  if not isLowPriority:
    available_hardware_response = get_available_hardware(date.isoformat(), duration, hardwareSpecs, is_user_admin, None, resolved_user_id, target_computer_id=computerId)
    if (available_hardware_response["status"] == False):
      return api_response(False, available_hardware_response["message"])

  # Phase 3: Creation session — build and persist the reservation
  with Session() as session:
    user = session.execute(select(User).where( User.userId == resolved_user_id )).scalar_one_or_none()

    # Create the base reservation
    reservation_data = {
      "reservedContainerId": containerId,
      "startDate": date,
      "endDate": end_date,
      "userId": resolved_user_id,
      "computerId": computerId,
      "status": "reserved",
      "isLowPriority": isLowPriority,
      "lowPriorityLevel": lowPriorityLevel,
    }

    # Only add description if it's provided and not empty
    if description and description.strip():
      reservation_data["description"] = description.strip()

    reservation = Reservation(**reservation_data)

    # Get user's role-based hardware limits
    user_role_limits = {}
    user_role_limits_low = {}
    from database import RoleHardwareLimit, UserRole
    user_roles = session.execute(select(UserRole).where(UserRole.userId == resolved_user_id)).scalars().all()
    role_ids = [ur.roleId for ur in user_roles]

    if role_ids and not is_user_admin:
      role_limits = session.execute(select(RoleHardwareLimit).where(
        RoleHardwareLimit.roleId.in_(role_ids)
      )).scalars().all()

      # Build a dict of hardwareSpecId -> max limit across all roles
      for limit in role_limits:
        spec_id = limit.hardwareSpecId
        if limit.maximumAmountForRole is not None:
          if spec_id not in user_role_limits or limit.maximumAmountForRole > user_role_limits[spec_id]:
            user_role_limits[spec_id] = limit.maximumAmountForRole

        # Low-priority falls back to the normal override on rows where it is NULL
        low_value = limit.maximumAmountForRoleLowPriority if limit.maximumAmountForRoleLowPriority is not None else limit.maximumAmountForRole
        if low_value is not None:
          if spec_id not in user_role_limits_low or low_value > user_role_limits_low[spec_id]:
            user_role_limits_low[spec_id] = low_value

    # Select which role-limit dict applies to this reservation based on priority
    effective_role_limits = user_role_limits_low if isLowPriority else user_role_limits

    # Add GPU count validation
    total_gpus_requested = 0
    for key, val in hardwareSpecs.items():
      hardware_spec = session.execute(select(HardwareSpec).where( HardwareSpec.hardwareSpecId == key )).scalar_one_or_none()
      if hardware_spec and hardware_spec.type == "gpu" and val > 0:
        total_gpus_requested += val

    # Validate total GPU count for non-admins (max 1 GPU per reservation)
    if not is_user_admin and total_gpus_requested > 1:
      # Check if any role allows more than 1 GPU
      gpu_limit_from_roles = 1
      for key, val in hardwareSpecs.items():
        hardware_spec = session.execute(select(HardwareSpec).where( HardwareSpec.hardwareSpecId == key )).scalar_one_or_none()
        if hardware_spec and hardware_spec.type == "gpu" and key in effective_role_limits:
          gpu_limit_from_roles = max(gpu_limit_from_roles, effective_role_limits[key])

      if total_gpus_requested > gpu_limit_from_roles:
        return api_response(False, f"You can only reserve {gpu_limit_from_roles} GPU(s) at a time.")

    # Enhanced hardware specification validation
    reserved_specs_summary = []
    for key, val in hardwareSpecs.items():
      # Validate hardware spec exists
      hardware_spec = session.execute(select(HardwareSpec).where( HardwareSpec.hardwareSpecId == key )).scalar_one_or_none()
      if not hardware_spec:
        return api_response(False, f"Invalid hardware specification ID: {key}")

      # Validate amount bounds
      if val < 0:
        return api_response(False, f"Invalid negative amount for {hardware_spec.type}")
      if val > hardware_spec.maximumAmount:
        return api_response(False, f"Requested amount exceeds available resources for {hardware_spec.type}: {val} > {hardware_spec.maximumAmount}")

      # Check that the amount does not exceed user limits for the given hardware
      # Skipped for admins
      if is_user_admin == False:
        # Use role-based limit if available, otherwise use default computer limit.
        # For low-priority reservations, use the low-priority cap/override.
        if isLowPriority:
          effective_limit = hardware_spec.maximumAmountForUserLowPriority
          if int(key) in user_role_limits_low:
            effective_limit = min(user_role_limits_low[int(key)], hardware_spec.maximumAmount)
        else:
          effective_limit = hardware_spec.maximumAmountForUser
          if int(key) in user_role_limits:
            effective_limit = min(user_role_limits[int(key)], hardware_spec.maximumAmount)

        if val > effective_limit:
          return api_response(False, f"Trying to utilize hardware specs above the user maximum amount for {hardware_spec.type} {hardware_spec.format}: {val} > {effective_limit}")

      # Only add resources over 0
      if val > 0:
        reserved_specs_summary.append({"type": hardware_spec.type, "format": hardware_spec.format, "amount": val})
        reservation.reservedHardwareSpecs.append(
          ReservedHardwareSpec(
            hardwareSpecId = key,
            amount = val,
          )
      )
    # Clear script paths if the corresponding feature is disabled
    effective_start_script = startScriptPath if get_setting('features.startScriptsEnabled') else None
    effective_stop_script = stopScriptPath if get_setting('features.stopScriptsEnabled') else None

    # Create the ReservedContainer
    reservation.reservedContainer = ReservedContainer(
      containerId = containerId,
      shmSizePercent = shmSizePercent,
      ramDiskSizePercent = ramDiskSizePercent,
      startScriptPath = effective_start_script or None,
      stopScriptPath = effective_stop_script or None,
    )
    user.reservations.append(reservation)
    session.add(reservation)
    session.commit()

    created_reservation_id = reservation.reservationId
    inform_by_email = get_setting('email.sendEmail')

    log_action(userId, "RESERVATION_CREATE", "reservation", created_reservation_id,
               {"computerName": computer.name, "containerName": container.name,
                "containerImage": container.imageName, "duration": duration,
                "description": description, "hardwareSpecs": reserved_specs_summary,
                "shmSizePercent": shmSizePercent, "ramDiskSizePercent": ramDiskSizePercent,
                "isLowPriority": isLowPriority, "lowPriorityLevel": lowPriorityLevel})
    return api_response(True, "Reservation created succesfully!", { "informByEmail": inform_by_email })

def cancel_reservation(userId : int, reservationId: int):
  """Cancel a reservation by setting its end date to now.

  The reservation's end date is set to the current UTC time, which
  triggers the container server daemon to stop the container. Regular users
  can only cancel their own reservations; admins can cancel any.

  Args:
      userId: The ID of the requesting user.
      reservationId: The ID of the reservation to cancel.

  Returns:
      Response indicating success or failure with an appropriate message.
  """
  # Check that user owns the given reservation and it can be found
  # Admins can cancel any reservation
  # print("Starting to cancel reservation: " + reservationId)
  with Session() as session:
    query = select(Reservation).where(Reservation.reservationId == reservationId)
    if not is_admin(userId):
      query = query.where(Reservation.userId == userId)
    query = query.options(
      joinedload(Reservation.computer),
      joinedload(Reservation.reservedContainer).joinedload(ReservedContainer.container),
    )
    reservation = session.execute(query).scalar_one_or_none()
    if reservation is None: return api_response(False, "No reservation found.")
    if reservation.status in ("stopped", "stopping", "error"):
      return api_response(False, "Reservation cannot be cancelled in its current state.")

    owner_id = reservation.userId
    computer_name = reservation.computer.name if reservation.computer else None
    container_name = reservation.reservedContainer.container.name if reservation.reservedContainer and reservation.reservedContainer.container else None
    container_image = reservation.reservedContainer.container.imageName if reservation.reservedContainer and reservation.reservedContainer.container else None

    now = datetime.datetime.now(datetime.timezone.utc)
    reservation.endDate = now
    # If the container was never started, go directly to stopped
    if reservation.status == "reserved":
      reservation.status = "stopped"
    else:
      reservation.status = "stopping"
    start_date = reservation.startDate.replace(tzinfo=datetime.timezone.utc) if reservation.startDate.tzinfo is None else reservation.startDate
    if start_date > now:
      reservation.startDate = now
    session.commit()

  cancelled_by = "admin" if userId != owner_id else "user"
  log_action(userId, "RESERVATION_CANCEL", "reservation", int(reservationId),
             {"cancelledBy": cancelled_by, "computerName": computer_name,
              "containerName": container_name, "containerImage": container_image})
  return api_response(True, "Reservation cancelled.")

def update_reservation_description(userId: int, reservationId: int, description: str):
  """Updates the description of a reservation owned by the user.
  Only allowed for reservations with status 'reserved' or 'started'.
  Admins can update any reservation's description.

  Args:
    userId (int): The ID of the user making the request
    reservationId (str): The ID of the reservation to update
    description (str): The new description (already validated/sanitized by the endpoint)

  Returns:
    object: Response indicating success or failure
  """
  with Session() as session:
    reservation = None
    if is_admin(userId) == False:
      reservation = session.execute(select(Reservation).where( Reservation.reservationId == reservationId, Reservation.userId == userId )).scalar_one_or_none()
    else:
      reservation = session.execute(select(Reservation).where( Reservation.reservationId == reservationId )).scalar_one_or_none()
    if reservation is None: return api_response(False, "No reservation found.")

    if reservation.status not in ("reserved", "started", "paused"):
      return api_response(False, "Cannot edit description: reservation is not active.")

    reservation.description = description if description else None
    session.commit()

  log_action(userId, "RESERVATION_UPDATE_DESCRIPTION", "reservation", int(reservationId))
  return api_response(True, "Description updated.")

def extend_reservation(userId : int, reservationId: int, duration: int):
  """Extend a running reservation by a specified number of hours.

  Checks GPU availability during the extension period to prevent
  conflicts, then verifies general resource availability. Only started
  reservations can be extended. Duration must be between 0 and 24 hours.
  Regular users can only extend their own reservations; admins can
  extend any.

  Args:
      userId: The ID of the requesting user.
      reservationId: The ID of the reservation to extend.
      duration: Number of hours to extend the reservation.

  Returns:
      Response indicating success with the extension amount, or an
      error message if extension is not possible.
  """
  # Phase 1: Read session — validate ownership, status, GPU conflicts, collect data
  # Admins can extend any reservation

  with Session() as session:
    if is_admin(userId) == False:
      reservation_check = session.execute(select(Reservation).where( Reservation.reservationId == reservationId, Reservation.userId == userId )).scalar_one_or_none()
      if reservation_check is None: return api_response(False, "No reservation found for this user.")

    reservation = session.execute(
      select(Reservation)
      .options(joinedload(Reservation.reservedHardwareSpecs).joinedload(ReservedHardwareSpec.hardwareSpec))
      .where( Reservation.reservationId == reservationId )
    ).unique().scalar_one_or_none()
    if reservation is None: return api_response(False, "No reservation found.")

    if reservation.status not in ("started", "paused"):
      return api_response(False, "Reservation is not active, so cannot extend it.")

    # Check that the duration is between minimum and maximum lengths
    if duration < 0 or duration > 24:
      return api_response(False, "Duration must be between 0 and 24 hours.")

    # First check if specific GPUs are still available during the extension period
    end_time_string = reservation.endDate.strftime("%Y-%m-%d %H:%M:%S")
    extended_end_date = reservation.endDate + relativedelta(hours=+duration)

    # Check for GPU conflicts specifically
    for spec in reservation.reservedHardwareSpecs:
      if spec.hardwareSpec.type == "gpu" and spec.amount > 0:
        # Check if this specific GPU is reserved by another reservation during the extension period
        conflicting_reservation = session.execute(
          select(Reservation)
          .join(ReservedHardwareSpec)
          .where(
            ReservedHardwareSpec.hardwareSpecId == spec.hardwareSpecId,
            ReservedHardwareSpec.amount > 0,
            Reservation.reservationId != reservationId,
            Reservation.startDate < extended_end_date,
            Reservation.endDate > reservation.endDate,
            (Reservation.status == "reserved") | (Reservation.status == "started")
          )
        ).scalar_one_or_none()

        if conflicting_reservation:
          return api_response(False, f"Cannot extend reservation: GPU {spec.hardwareSpec.format} (ID: {spec.hardwareSpec.internalId}) is already reserved by another user during the requested extension period.")

    # Collect data needed for availability check and update
    reducable_specs = {}
    for spec in reservation.reservedHardwareSpecs:
      reducable_specs[spec.hardwareSpecId] = spec.amount
    res_id = reservation.reservationId
    res_user_id = reservation.userId
    res_computer_id = reservation.computerId
    res_is_low_priority = reservation.isLowPriority

  # Phase 2: Check resource availability outside session to avoid nested sessions.
  # Low-priority extensions skip the availability check entirely, mirroring creation.
  if not res_is_low_priority:
    available_hardware_response = get_available_hardware(end_time_string, duration, reducable_specs, False, res_id, res_user_id, target_computer_id=res_computer_id)
    if not available_hardware_response["status"]:
      log.debug(available_hardware_response["message"])
      return api_response(False, "Cannot extend reservation due to lack of resources. Try with less hours.")

  # Phase 3: Update session — apply the extension
  with Session() as session:
    reservation = session.execute(
      select(Reservation)
      .options(
        joinedload(Reservation.computer),
        joinedload(Reservation.reservedContainer).joinedload(ReservedContainer.container),
      )
      .where(Reservation.reservationId == res_id)
    ).unique().scalar_one_or_none()
    if reservation is None:
      return api_response(False, "No reservation found.")
    computer_name = reservation.computer.name if reservation.computer else None
    container_name = reservation.reservedContainer.container.name if reservation.reservedContainer and reservation.reservedContainer.container else None
    container_image = reservation.reservedContainer.container.imageName if reservation.reservedContainer and reservation.reservedContainer.container else None
    reservation.endDate = reservation.endDate + relativedelta(hours=+duration)
    session.commit()
    log_action(userId, "RESERVATION_EXTEND", "reservation", int(reservationId),
               {"duration": duration, "computerName": computer_name,
                "containerName": container_name, "containerImage": container_image})
    return api_response(True, "Reservation was extended by " + str(duration) + " hours.")

def restart_container(userId : int, reservationId: int):
  """Request a restart for a reservation's running container.

  Sets the reservation status to 'restart', which the container server daemon
  picks up to perform the actual container restart. Only started
  reservations can be restarted. Regular users can only restart their
  own containers; admins can restart any.

  Args:
      userId: The ID of the requesting user.
      reservationId: The ID of the reservation whose container to restart.

  Returns:
      Response indicating the restart was queued, or an error message
      if the reservation is not found or not currently started.
  """
  reservation = None
  # Check that user owns the given container reservation and it can be found
  # Admins can restart any container
  with Session() as session:
    stmt = select(Reservation)\
      .options(
        joinedload(Reservation.reservedContainer).joinedload(ReservedContainer.container),
        joinedload(Reservation.computer),
      )\
      .where( Reservation.reservationId == reservationId )
    if is_admin(userId) == False:
      stmt = stmt.where(Reservation.userId == userId )

    reservation = session.execute(stmt).unique().scalar_one_or_none()
    if reservation is None:
      return api_response(False, "No reservation found.")

    computer_name = reservation.computer.name if reservation.computer else None
    container_name = reservation.reservedContainer.container.name if reservation.reservedContainer and reservation.reservedContainer.container else None
    container_image = reservation.reservedContainer.container.imageName if reservation.reservedContainer and reservation.reservedContainer.container else None
    audit_details = {"computerName": computer_name, "containerName": container_name, "containerImage": container_image}

    if reservation.status == "paused":
      reservation.status = "reserved"
      session.commit()
      log_action(userId, "RESERVATION_RESTART", "reservation", int(reservationId), audit_details)
      return api_response(True, "Container will be restarted when resources are available.")
    elif reservation.status in ("started", "restart_error"):
      reservation.status = "restart"
      session.commit()
      log_action(userId, "RESERVATION_RESTART", "reservation", int(reservationId), audit_details)
      return api_response(True, "Container will be restarted.")
    else:
      return api_response(False, "Reservation is not currently active, so cannot restart the container.")

def get_availability_timeline(startDate: str, endDate: str, is_admin = False) -> object:
  """Generate resource availability timeline for all public servers.

  Creates continuous time-period events between the given dates for
  each server, showing remaining hardware resources (CPU, RAM, GPU)
  after subtracting active and upcoming reservations. Each period is
  color-coded by availability level (high/medium/low) with a
  consistent server-specific color.

  Args:
      startDate: Start date for the timeline as an ISO-format string.
      endDate: End date for the timeline as an ISO-format string.
      is_admin: Whether the requesting user has admin privileges.

  Returns:
      Response with a list of timeline event dicts, each containing
      period start/end, server info, availability level, resource
      text, and available spec details.
  """
  try:
    start_date = parser.parse(startDate)
    end_date = parser.parse(endDate)
  except:
    return api_response(False, "Invalid date format.")
  
  # Fetch all computers and reservations in the time range
  with Session() as session:
    computer_query = select(Computer).options(joinedload(Computer.hardwareSpecs)).where(Computer.removed.isnot(True))
    if not is_admin:
      computer_query = computer_query.where(Computer.public.is_(True))
    computers = session.execute(computer_query).unique().scalars().all()

    reservations = session.execute(
      select(Reservation)
      .options(
        joinedload(Reservation.reservedHardwareSpecs).joinedload(ReservedHardwareSpec.hardwareSpec),
        joinedload(Reservation.computer)
      )
      .where(
        Reservation.startDate < end_date,
        Reservation.endDate > start_date,
        Reservation.isLowPriority == False,
        (Reservation.status == "reserved") | (Reservation.status == "started")
      )
    ).unique().scalars().all()
    
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
              
              # Special handling for GPU reservations: individual GPU specs (with internalId) 
              # are reserved but not displayed. We need to subtract these from the 
              # consolidated GPU group (without internalId) that is displayed.
              if reserved_spec.hardwareSpec.type == 'gpu' and reserved_spec.hardwareSpec.internalId is not None:
                # Find the consolidated GPU group (type='gpus' without internalId)
                for group_spec_id, group_data in available_specs.items():
                  if group_data['type'] == 'gpus':  # Note: 'gpus' plural, not 'gpu'
                    group_data['available'] -= reserved_spec.amount
                    if group_data['available'] < 0:
                      group_data['available'] = 0
                    break
              else:
                # Normal handling for non-GPU specs or consolidated GPU specs
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
    
  return api_response(True, "Availability timeline fetched.", {'events': timeline_events})

def get_all_reservations_for_calendar(startDate: str, endDate: str) -> object:
  """Retrieve all reservations within a date range for calendar display.

  Fetches reservations of all statuses (reserved, started, stopped,
  error) that overlap with the given date range, including their
  hardware specs and computer assignments.

  Args:
      startDate: Start date for the query as an ISO-format string.
      endDate: End date for the query as an ISO-format string.

  Returns:
      Response with a list of reservation summary dicts containing
      reservationId, dates, computerName, hardwareSpecs, and status.
  """
  try:
    start_date = parser.parse(startDate)
    end_date = parser.parse(endDate)
  except:
    return api_response(False, "Invalid date format.")
  
  reservations = []

  with Session() as session:
    query = session.execute(
      select(Reservation)
      .options(
        joinedload(Reservation.reservedHardwareSpecs).joinedload(ReservedHardwareSpec.hardwareSpec),
        joinedload(Reservation.computer)
      )
      .where(
        Reservation.startDate < end_date,
        Reservation.endDate > start_date
      )
    ).unique().scalars().all()

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
        "status": reservation.status,
        "isLowPriority": reservation.isLowPriority,
        "lowPriorityLevel": reservation.lowPriorityLevel,
      })
    
  return api_response(True, "All reservations fetched.", {"reservations": reservations})
