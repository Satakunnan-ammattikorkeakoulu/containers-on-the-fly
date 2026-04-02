"""Docker utility daemon -- manages container lifecycle based on reservation state.

Polls the database every 10 seconds to start, stop, restart, and clean up
Docker containers for reservations. Runs as a long-lived process managed by
pm2, and coordinates between the database reservation state and the actual
Docker containers running on the host.
"""

from time import sleep
from datetime import timezone, datetime, timedelta
import sys
from os import linesep

from logger import log
from settings_handler import settings_handler
from database import Session, Reservation, ReservedContainerPort, Role, Computer, HardwareSpec, ReservedHardwareSpec
from helpers.auth import create_password
from sqlalchemy import select

from docker.containers import start_container, stop_container, restart_container, run_stop_script
from docker.monitoring import update_server_monitoring
from docker.notifications import send_container_started_email, send_container_error_email, send_admin_failure_alert, send_container_paused_email, send_container_resumed_email
from docker.ports import get_available_port
from docker.queries import (
    get_reservations_requiring_start, get_running_reservations,
    get_reservations_requiring_stop, get_reservations_requiring_restart,
    get_container_information, get_computer_id, get_running_reserved_docker_containers,
    get_containers_requiring_build, get_containers_requiring_image_removal, reset_stale_building_status,
    get_low_priority_running_reservations, get_paused_reservations,
    get_future_normal_reservations, get_all_active_reservations
)
from docker.image_builder import build_and_push_image, remove_image, update_all_image_sizes

# Runs the script forever
run: bool = True
# The ID of the computer from the database which this script should react to is saved here
computer_id: int = None


def time_now():
  """Return the current UTC datetime.

  Returns:
      datetime: Current time in UTC timezone.
  """
  return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Daemon main loop
# ---------------------------------------------------------------------------

def main():
  """Run the daemon's main polling loop.

  Continuously cycles through lifecycle checks every 10 seconds:
  pause low-priority containers for incoming normal reservations,
  stop finished containers, start new ones, resume paused low-priority
  containers, restart crashed or restart-requested containers. Server
  monitoring is updated every 30 seconds, and orphan container cleanup
  runs every 60 seconds.
  """
  while (run):
    for i in range(6):
      pause_low_priority_for_normal_reservations()
      stop_finished_servers()
      start_new_servers()
      resume_paused_containers()
      restart_crashed_servers()
      restart_servers_requiring_restart()
      process_image_builds()
      process_image_removals()

      # Update monitoring data every 3rd iteration (every 30 seconds)
      if i % 3 == 0:
        update_server_monitoring()

      sleep(10)
    # Run this larger cleanup below every 60 seconds (1 minute)
    stop_orphan_container_reservations()


# ---------------------------------------------------------------------------
# Lifecycle handlers (called from main loop)
# ---------------------------------------------------------------------------

def stop_finished_servers():
  """Stop containers whose reservations have ended.

  Queries for reservations past their end date with status "started" or
  "reserved" on this computer, then stops each corresponding Docker
  container.
  """
  global computer_id
  reservations = get_reservations_requiring_stop(computer_id)
  for reservation in reservations:
    if settings_handler.get_setting("docker.enabled") == True:
      stop_docker_container(reservation.reservationId)

def start_new_servers():
  """Start containers for reservations that are due to begin.

  Queries for reservations with status "reserved" whose start date has
  passed on this computer, then starts a Docker container for each one.
  """
  global computer_id
  reservations = get_reservations_requiring_start(computer_id)
  for reservation in reservations:
    if settings_handler.get_setting("docker.enabled") == True:
      start_docker_container(reservation.reservationId)

def restart_crashed_servers():
  """Restart containers that have exited unexpectedly.

  Queries for running reservations on this computer, inspects each
  container's Docker state, and restarts any that have exited.
  """
  global computer_id
  reservations = get_running_reservations(computer_id)
  for reservation in reservations:
    if settings_handler.get_setting("docker.enabled") == True:
      try:
        container_name, container_state = get_container_information(reservation.reservationId)
        if container_state.state.status == "exited":
          log.warning(f"Container exited unexpectedly for reservation {reservation.reservationId}, restarting")
          restart_docker_container(reservation.reservationId)
      except Exception as e:
        log.error(f"Error restarting crashed container for reservation {reservation.reservationId}: {e}")

def restart_servers_requiring_restart():
  """Restart containers that have been flagged for restart by a user or admin.

  Queries for reservations with status "restart" on this computer whose
  end date has not yet passed, then restarts each corresponding Docker
  container.
  """
  global computer_id
  reservations = get_reservations_requiring_restart(computer_id)

  for reservation in reservations:
    if settings_handler.get_setting("docker.enabled") == True:
      try:
        restart_docker_container(reservation.reservationId)
      except Exception as e:
        log.error(f"Error restarting container for reservation {reservation.reservationId}: {e}")

def process_image_builds():
  """Build Docker images for containers with pending build requests.

  Queries for containers with buildStatus "pending" and builds them
  one at a time to avoid resource contention. Each build generates
  a Dockerfile from the base template plus custom commands, builds
  the image, and pushes it to the local registry.
  """
  containers = get_containers_requiring_build()
  for container in containers:
    log.info(f"Building image for container {container.containerId} ({container.imageName})")
    try:
      build_and_push_image(container.containerId)
    except Exception as e:
      log.error(f"Error building image for container {container.containerId} ({container.imageName}): {e}")

def process_image_removals():
  """Remove Docker images for containers that have been deleted by admins.

  Queries for containers with buildStatus "removing" and removes their
  Docker images one at a time.
  """
  containers = get_containers_requiring_image_removal()
  for container in containers:
    log.info(f"Removing image for deleted container {container.containerId} ({container.imageName})")
    try:
      remove_image(container.containerId)
    except Exception as e:
      log.error(f"Error removing image for container {container.containerId} ({container.imageName}): {e}")

def pause_low_priority_for_normal_reservations():
  """Pause running low-priority containers to free resources for normal reservations.

  Checks if any normal reservation is ready to start but lacks resources
  because low-priority containers are using them. If so, stops the
  low-priority containers and sets their status to "paused".
  """
  global computer_id
  if settings_handler.get_setting("docker.enabled") != True:
    return

  try:
    # Find normal reservations ready to start
    with Session() as session:
      from sqlalchemy.orm import joinedload
      normal_pending = session.execute(
        select(Reservation)
        .options(
          joinedload(Reservation.reservedHardwareSpecs).joinedload(ReservedHardwareSpec.hardwareSpec)
        )
        .where(
          Reservation.status == "reserved",
          Reservation.isLowPriority == False,
          Reservation.computerId == computer_id,
          Reservation.startDate < time_now()
        )
      ).unique().scalars().all()

      if not normal_pending:
        return

      # Get computer's total hardware capacity
      computer = session.execute(
        select(Computer).options(joinedload(Computer.hardwareSpecs))
        .where(Computer.computerId == computer_id)
      ).unique().scalar_one_or_none()
      if not computer:
        return

      total_capacity = {}
      for spec in computer.hardwareSpecs:
        total_capacity[spec.hardwareSpecId] = spec.maximumAmount

      # Get all currently active non-low-priority reservations (started + reserved)
      non_lp_active = session.execute(
        select(Reservation)
        .options(joinedload(Reservation.reservedHardwareSpecs))
        .where(
          Reservation.computerId == computer_id,
          Reservation.isLowPriority == False,
          Reservation.status.in_(["started", "reserved"]),
          Reservation.endDate > time_now()
        )
      ).unique().scalars().all()

      # Calculate resources used by non-low-priority reservations
      non_lp_used = {}
      for res in non_lp_active:
        for spec in res.reservedHardwareSpecs:
          spec_id = spec.hardwareSpecId
          non_lp_used[spec_id] = non_lp_used.get(spec_id, 0) + spec.amount

      # Get running low-priority containers
      lp_running = session.execute(
        select(Reservation)
        .options(
          joinedload(Reservation.reservedHardwareSpecs).joinedload(ReservedHardwareSpec.hardwareSpec),
          joinedload(Reservation.reservedContainer),
          joinedload(Reservation.user),
          joinedload(Reservation.computer),
        )
        .where(
          Reservation.status == "started",
          Reservation.isLowPriority == True,
          Reservation.computerId == computer_id,
          Reservation.endDate > time_now()
        )
      ).unique().scalars().all()

      if not lp_running:
        return

      for normal_res in normal_pending:
        # What does this normal reservation need?
        needed = {}
        for spec in normal_res.reservedHardwareSpecs:
          needed[spec.hardwareSpecId] = spec.amount

        # Check if resources are already available (without touching low-priority)
        resources_ok = True
        for spec_id, amount in needed.items():
          available = total_capacity.get(spec_id, 0) - non_lp_used.get(spec_id, 0)
          if amount > available:
            resources_ok = False
            break

        if resources_ok:
          continue  # No preemption needed for this reservation

        # Need to pause low-priority containers to free resources
        # Build a deficit map: how much more resource is needed
        deficit = {}
        for spec_id, amount in needed.items():
          available = total_capacity.get(spec_id, 0) - non_lp_used.get(spec_id, 0)
          if amount > available:
            deficit[spec_id] = amount - available

        # Try to resolve deficit by pausing low-priority containers (newest first = LIFO)
        lp_sorted = sorted(lp_running, key=lambda r: r.createdAt, reverse=True)
        to_pause = []

        for lp_res in lp_sorted:
          if not deficit:
            break
          # Check if this low-priority container has overlapping resources
          lp_specs = {}
          for spec in lp_res.reservedHardwareSpecs:
            lp_specs[spec.hardwareSpecId] = spec.amount

          has_overlap = any(spec_id in lp_specs for spec_id in deficit)
          if not has_overlap:
            continue

          to_pause.append(lp_res)
          # Reduce deficit by resources freed from this container
          for spec_id in list(deficit.keys()):
            if spec_id in lp_specs:
              deficit[spec_id] -= lp_specs[spec_id]
              if deficit[spec_id] <= 0:
                del deficit[spec_id]

        # Pause the identified containers
        for lp_res in to_pause:
          try:
            container_docker_name = lp_res.reservedContainer.containerDockerName
            if container_docker_name:
              # Run stop script before pausing the container
              stop_script = lp_res.reservedContainer.stopScriptPath
              if stop_script:
                container_username = (lp_res.reservedContainer.container.containerUsername or "user") if lp_res.reservedContainer.container else "user"
                run_stop_script(container_docker_name, stop_script, container_username)
              stop_container(container_docker_name)
            lp_res.status = "paused"
            lp_res.reservedContainer.stoppedAt = time_now()
            lp_res.reservedContainer.containerStatus = "paused"
            session.commit()

            image_name = lp_res.reservedContainer.container.imageName if lp_res.reservedContainer.container else "unknown"
            computer_name = lp_res.computer.name if lp_res.computer else "unknown"
            log.info(f"Low-priority reservation {lp_res.reservationId} paused for normal reservation {normal_res.reservationId}")
            send_container_paused_email(lp_res.user.email, image_name, computer_name, lp_res.reservationId)

            # Remove from the running list so subsequent normal reservations don't try to pause it again
            if lp_res in lp_running:
              lp_running.remove(lp_res)

            # Update non_lp_used would not change (we paused an LP), but total available changes
            # Actually we need to recalculate for the next normal_res iteration

          except Exception as e:
            log.error(f"Error pausing low-priority reservation {lp_res.reservationId}: {e}")

  except Exception as e:
    log.error(f"Error in pause_low_priority_for_normal_reservations: {e}")


def resume_paused_containers():
  """Resume paused low-priority containers when resources become available.

  Checks if any paused low-priority reservations can be restarted based
  on current resource availability. Includes a 30-minute look-ahead to
  avoid start-stop thrashing. FIFO priority (oldest paused first).
  """
  global computer_id
  if settings_handler.get_setting("docker.enabled") != True:
    return

  try:
    paused = get_paused_reservations(computer_id)
    if not paused:
      return

    with Session() as session:
      from sqlalchemy.orm import joinedload

      # Get computer's total hardware capacity
      computer = session.execute(
        select(Computer).options(joinedload(Computer.hardwareSpecs))
        .where(Computer.computerId == computer_id)
      ).unique().scalar_one_or_none()
      if not computer:
        return

      total_capacity = {}
      for spec in computer.hardwareSpecs:
        total_capacity[spec.hardwareSpecId] = spec.maximumAmount

      # Get all currently active reservations (non-LP started/reserved + LP started)
      all_active = session.execute(
        select(Reservation)
        .options(joinedload(Reservation.reservedHardwareSpecs))
        .where(
          Reservation.computerId == computer_id,
          Reservation.status.in_(["started", "reserved"]),
          Reservation.endDate > time_now()
        )
      ).unique().scalars().all()

      # Calculate currently used resources
      used = {}
      for res in all_active:
        for spec in res.reservedHardwareSpecs:
          spec_id = spec.hardwareSpecId
          used[spec_id] = used.get(spec_id, 0) + spec.amount

      for paused_res in paused:
        # Re-fetch within this session to ensure we can modify
        res = session.execute(
          select(Reservation)
          .options(joinedload(Reservation.reservedHardwareSpecs).joinedload(ReservedHardwareSpec.hardwareSpec))
          .where(Reservation.reservationId == paused_res.reservationId)
        ).unique().scalar_one_or_none()
        if not res or res.status != "paused":
          continue

        # Check if resources are available
        needed = {}
        for spec in res.reservedHardwareSpecs:
          needed[spec.hardwareSpecId] = spec.amount

        resources_ok = True
        for spec_id, amount in needed.items():
          available = total_capacity.get(spec_id, 0) - used.get(spec_id, 0)
          if amount > available:
            resources_ok = False
            break

        if not resources_ok:
          continue

        # Look-ahead: check if a normal reservation would start within 30 minutes
        # that would immediately conflict and preempt this container again
        look_ahead_end = time_now() + timedelta(minutes=30)
        future_normals = get_future_normal_reservations(computer_id, time_now(), look_ahead_end)
        would_conflict = False
        for future_res in future_normals:
          # Check if the future normal reservation's resources overlap with this paused one
          for f_spec in future_res.reservedHardwareSpecs:
            if f_spec.hardwareSpecId in needed:
              # Would this future reservation cause a resource deficit?
              future_needed = f_spec.amount
              spec_available = total_capacity.get(f_spec.hardwareSpecId, 0) - used.get(f_spec.hardwareSpecId, 0)
              # If after resuming this LP container, the future normal wouldn't fit
              if future_needed > (spec_available - needed.get(f_spec.hardwareSpecId, 0)):
                would_conflict = True
                break
          if would_conflict:
            break

        if would_conflict:
          log.debug(f"Skipping resume of paused reservation {res.reservationId}: would conflict with upcoming normal reservation")
          continue

        # Resume: set back to "reserved" so start_new_servers() picks it up
        res.status = "reserved"
        session.commit()
        log.info(f"Resuming paused low-priority reservation {res.reservationId}")

        # Update used resources for subsequent iterations
        for spec_id, amount in needed.items():
          used[spec_id] = used.get(spec_id, 0) + amount

  except Exception as e:
    log.error(f"Error in resume_paused_containers: {e}")


def _are_resources_available_for_reservation(reservation):
  """Check if hardware resources are currently available for a reservation.

  Computes available resources on the computer by subtracting all active
  (started/reserved) reservations, then checks if the given reservation's
  needs fit within the remaining capacity.

  Args:
      reservation: Reservation ORM object to check resources for.

  Returns:
      bool: True if resources are available, False otherwise.
  """
  try:
    with Session() as session:
      from sqlalchemy.orm import joinedload

      computer = session.execute(
        select(Computer).options(joinedload(Computer.hardwareSpecs))
        .where(Computer.computerId == reservation.computerId)
      ).unique().scalar_one_or_none()
      if not computer:
        return False

      total_capacity = {}
      for spec in computer.hardwareSpecs:
        total_capacity[spec.hardwareSpecId] = spec.maximumAmount

      # Get all active reservations except this one
      all_active = session.execute(
        select(Reservation)
        .options(joinedload(Reservation.reservedHardwareSpecs))
        .where(
          Reservation.computerId == reservation.computerId,
          Reservation.status.in_(["started", "reserved"]),
          Reservation.reservationId != reservation.reservationId,
          Reservation.endDate > time_now()
        )
      ).unique().scalars().all()

      used = {}
      for res in all_active:
        for spec in res.reservedHardwareSpecs:
          spec_id = spec.hardwareSpecId
          used[spec_id] = used.get(spec_id, 0) + spec.amount

      for spec in reservation.reservedHardwareSpecs:
        available = total_capacity.get(spec.hardwareSpecId, 0) - used.get(spec.hardwareSpecId, 0)
        if spec.amount > available:
          return False

      return True
  except Exception as e:
    log.error(f"Error checking resource availability for reservation {reservation.reservationId}: {e}")
    return False


def stop_orphan_container_reservations():
  """Clean up Docker containers that have no matching active reservation.

  Compares containers physically running in Docker (with names starting
  with "reservation-") against reservations marked as "started" in the
  database. Any container running for more than 30 minutes without a
  matching database record is considered orphaned and is stopped and
  removed. Orphan containers can occur when the daemon encounters an
  error and fails to clean up properly.
  """

  try:
    # Get all containers marked as started in the database
    reservations = get_running_reservations(computer_id)
    for reservation in reservations:
      pass  # containerDockerId might be None

    # Get all Docker container reservations (container name starting with "reservation-"") really running on this computer
    docker_reservation_containers = get_running_reserved_docker_containers()
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
          log.warning(f"Orphan container detected (not in database): container name {container.name}, stopping it")
          stop_orphan_docker_container(container.name)
  except Exception as e:
    log.error(f"Error stopping (cleaning up) orphan containers: {e}")


# ---------------------------------------------------------------------------
# Orchestration functions (bridge between DB reservations and Docker operations)
# ---------------------------------------------------------------------------

def start_docker_container(reservation_id: str):
  """Build configuration and start a Docker container for a reservation.

  Reads the reservation from the database, assembles all container
  parameters (image, hardware specs, ports, mounts, GPU assignment),
  calls the Docker start_container function, and updates the
  reservation status accordingly. Sends email notifications on both
  success and failure.

  Args:
      reservation_id: Database ID of the reservation to start.
  """
  with Session() as session:
    reservation = session.execute(
      select(Reservation).where(Reservation.reservationId == reservation_id)
    ).scalar_one_or_none()
    if reservation == None: return False

    # Guard: if low-priority reservation, verify resources are actually available right now
    if reservation.isLowPriority:
      if not _are_resources_available_for_reservation(reservation):
        reservation.status = "paused"
        session.commit()
        log.info(f"Low-priority reservation {reservation_id} paused: insufficient resources")
        return
    ssh_password = create_password()

    # Guard: if the container has Dockerfile commands but hasn't been built successfully, block start
    container_obj = reservation.reservedContainer.container
    if container_obj.dockerfileCommands and container_obj.buildStatus != "success":
      log.warning(f"Container image for {container_obj.imageName} not built successfully (status: {container_obj.buildStatus}), marking reservation {reservation_id} as error")
      reservation.status = "error"
      reservation.reservedContainer.containerDockerErrorMessage = "Container image has not been built successfully. Please ask an admin to build the image first."
      reservation.reservedContainer.containerStatus = "error"
      session.commit()
      return

    image_name = container_obj.imageName
    hw_specs = {}
    gpu_specs = {}
    for spec in reservation.reservedHardwareSpecs:
      if spec.hardwareSpec.type == "gpu":
        gpu_specs[spec.hardwareSpec.internalId] = { "amount": spec.amount }
      else:
        hw_specs[spec.hardwareSpec.type] = { "amount": spec.amount }

    time_now_parsed = time_now().strftime('%m_%d_%Y_%H_%M_%S')

    container_name = f"reservation-{reservation.reservationId}-{image_name.replace(':', '').replace('/', '')}-{time_now_parsed}"
    reservation.reservedContainer.containerDockerName = container_name

    ports = []

    # Set bindable ports for the reservation container
    for port in reservation.reservedContainer.container.containerPorts:
      outside_port = get_available_port()
      ports.append({
        "containerPortId" : port.containerPortId,
        "serviceName": port.serviceName,
        "localPort": port.port,
        "outsidePort": outside_port
      })

    # Create the GPUs string to be passed to Docker
    gpus_string = ""
    # Loop through all hw_specs and find the reserved GPU internal IDs (Nvidia / cuda IDs), if any
    if len(gpu_specs) > 0:
      gpus_string = "device="
      for gpu in gpu_specs:
        gpus_string = gpus_string + gpu + ","
      # Remove the trailing , from gpu_specs, if it exists
      if gpus_string[-1] == ",": gpus_string = gpus_string[:-1]


    # Create the port string to be passed to Docker
    ports_for_container = []
    for port in ports:
      ports_for_container.append( (port["outsidePort"], port["localPort"]) )

    details = {
      "name": container_name,
      "image": image_name,
      "username": container_obj.containerUsername or "user",
      "cpus": int(hw_specs['cpus']["amount"]),
      "gpus": gpus_string if gpus_string else None,  # Convert empty string to None
      "memory": f"{hw_specs['ram']['amount']}g",
      "shm_size_percent": reservation.reservedContainer.shmSizePercent if reservation.reservedContainer.shmSizePercent is not None else 50,
      "ram_disk_percent": reservation.reservedContainer.ramDiskSizePercent if reservation.reservedContainer.ramDiskSizePercent is not None else 0,
      "ports": ports_for_container,
      "password": ssh_password,
      "dbUserId": reservation.userId,
      "reservation": {
        "computerId": reservation.computerId,
        "user": {
          "email": reservation.user.email
        }
      },
      "sshPublicKey": reservation.user.sshPublicKey,
      "passwordCommand": container_obj.passwordCommand,
      "sshKeyDeployCommands": container_obj.sshKeyDeployCommands,
      "startScriptPath": reservation.reservedContainer.startScriptPath,
      "stopScriptPath": reservation.reservedContainer.stopScriptPath,
    }

    # Add role-based mounts (now the unified mounting system)
    details["roleMounts"] = []

    # Always add mounts from "Everyone" role
    with Session() as mount_session:
        everyone_role = mount_session.execute(
            select(Role).where(Role.name == "everyone")
        ).scalar_one_or_none()
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
    cont_was_started, cont_name, cont_password, errors, non_critical_errors, container_docker_id = start_container(details)

    if cont_was_started == True:
      log.info(f"Container started for reservation {reservation_id}, user={reservation.userId}, image={image_name}, docker_name={cont_name}, docker_id={container_docker_id}")
      # Set bound ports
      for port in ports:
        reservation.reservedContainer.reservedContainerPorts.append(ReservedContainerPort(
          outsidePort = port["outsidePort"],
          containerPortForeign = port["containerPortId"]
        ))

      # Set basic reservation status
      reservation.status = "started"
      reservation.reservedContainer.sshPassword = cont_password
      reservation.reservedContainer.startedAt = time_now()
      reservation.reservedContainer.containerDockerId = container_docker_id
      reservation.reservedContainer.containerStatus = "running"
      send_container_started_email(
        reservation.user.email, image_name, reservation.computer.ip,
        ports, ssh_password, non_critical_errors, reservation.endDate,
        container_obj.containerUsername or "user"
      )

      session.commit()
    else:
      # Set error message to database
      log.error(f"Failed to start container for reservation {reservation_id}, user={reservation.userId}, image={image_name}: {errors}")
      reservation.status = "error"
      reservation.reservedContainer.containerDockerErrorMessage = str(errors)
      reservation.reservedContainer.containerStatus = "error"
      session.commit()

      send_container_error_email(reservation.user.email, errors)
      send_admin_failure_alert(
        reservation.user.email, reservation.reservationId,
        image_name, reservation.computer.name, errors
      )

def stop_docker_container(reservation_id: str):
  """Stop a Docker container and update the reservation to "stopped".

  Looks up the reservation in the database, stops the corresponding
  Docker container, and records the stop timestamp.

  Args:
      reservation_id: Database ID of the reservation whose container
          should be stopped.
  """
  try:
    with Session() as session:
      reservation = session.execute(
        select(Reservation).where(Reservation.reservationId == reservation_id)
      ).scalar_one_or_none()
      if reservation == None: return False

      container_docker_name = reservation.reservedContainer.containerDockerName
      if reservation.status in ("started", "restart_error"):
        # Run stop script before stopping the container
        stop_script = reservation.reservedContainer.stopScriptPath
        if stop_script and container_docker_name:
          container_username = (reservation.reservedContainer.container.containerUsername or "user") if reservation.reservedContainer.container else "user"
          run_stop_script(container_docker_name, stop_script, container_username)
        stop_container(container_docker_name)
      # Paused containers are already stopped in Docker, just finalize the status
      reservation.status = "stopped"
      reservation.reservedContainer.stoppedAt = time_now()
      reservation.reservedContainer.containerStatus = "stopped"
      session.commit()
      container_docker_id = reservation.reservedContainer.containerDockerId
      log.info(f"Container stopped for reservation {reservation_id}, user={reservation.userId}, docker_name={container_docker_name}, docker_id={container_docker_id}")
  except Exception as e:
    log.error(f"Error stopping container for reservation {reservation_id}: {e}")

def stop_orphan_docker_container(container_name):
  """Stop an orphan Docker container that has no active reservation.

  Args:
      container_name: Name of the Docker container to stop and remove.
  """
  if not container_name: return
  try:
    stop_container(container_name)
    log.info(f"Orphan container stopped: {container_name}")
  except Exception as e:
    log.error(f"Error stopping orphan container {container_name}: {e}")

def restart_docker_container(reservation_id: str):
  """Restart a Docker container and reset the reservation status to "started".

  If the restart fails, sets the reservation status to "restart_error"
  so the user can see the failure and manually retry.

  Args:
      reservation_id: Database ID of the reservation whose container
          should be restarted.
  """
  with Session() as session:
    reservation = session.execute(
      select(Reservation).where(Reservation.reservationId == reservation_id)
    ).scalar_one_or_none()
    if reservation == None: return False

    container_docker_name = reservation.reservedContainer.containerDockerName
    try:
      restart_container(container_docker_name)
      reservation.status = "started"
      reservation.reservedContainer.containerStatus = "running"
      reservation.reservedContainer.containerDockerErrorMessage = ""
      container_docker_id = reservation.reservedContainer.containerDockerId
      log.info(f"Container restarted for reservation {reservation_id}, user={reservation.userId}, docker_name={container_docker_name}, docker_id={container_docker_id}")
    except Exception as e:
      log.error(f"Error restarting container for reservation {reservation_id}, user={reservation.userId}, docker_name={container_docker_name}: {e}")
      reservation.status = "restart_error"
      reservation.reservedContainer.containerStatus = "restart_error"
      reservation.reservedContainer.containerDockerErrorMessage = f"Container failed to restart: {e}"

    session.commit()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run():
  """Initialize the daemon and start the main loop.

  Reads the server name from settings, resolves it to a database computer
  ID, and enters the infinite main polling loop. Exits if Docker is not
  enabled or if the server name cannot be found in the database. Called
  from the docker_utility.py entry-point shim.
  """
  global computer_id

  log.info("AI Server Docker utility started.")
  log.info("This software will run infinitely and start / stop servers for reservations.")

  # Check that docker support has been enabled
  if (settings_handler.get_setting("docker.enabled") != True):
    log.warning("Docker support has not been enabled. Enable it with settings.json setting docker.enabled: true")

  # Get ID of the computer from the database based on the settings.json key docker.serverName.
  # Exit on any errors
  server_name = settings_handler.get_setting("docker.serverName")
  if not server_name:
    log.critical("docker.serverName not specified in settings.json. The name should be exactly the same as in database. Exiting.")
    sys.exit()
  computer_id = get_computer_id(server_name)
  if not computer_id:
    log.critical(f"Could not find computer with name '{server_name}' from the database. Exiting.")
    sys.exit()

  # Reset any image builds that were interrupted by a previous shutdown
  reset_stale_building_status()

  # Update image sizes for all containers on startup
  update_all_image_sizes()

  # Ensure persistent SSH host keys exist for this server
  from docker.ssh_host_keys import ensure_host_keys
  host_keys_path = settings_handler.get_setting("docker.sshHostKeysPath")
  ensure_host_keys(host_keys_path)

  main()


if __name__ == "__main__":
  run()
