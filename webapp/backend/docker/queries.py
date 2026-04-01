"""Database queries for the Docker utility daemon.

Provides query functions to retrieve reservations in various lifecycle
states (needing start, stop, restart) and to look up container and
computer information. Used exclusively by the daemon module.
"""

from python_on_whales import docker
from database import Session, Reservation, Computer, Container, ReservedHardwareSpec, HardwareSpec
from sqlalchemy import select
from sqlalchemy.orm import joinedload
import datetime
from datetime import timezone
from logger import log


def time_now():
  """Return the current UTC datetime.

  Returns:
      datetime: Current time in UTC timezone.
  """
  return datetime.datetime.now(datetime.timezone.utc)


def get_reservations_requiring_start(computer_id: int):
  """Get all reservations that need to be started on the given computer.

  Queries for reservations with status "reserved" whose start date has
  already passed.

  Args:
      computer_id: Database ID of the computer to query.

  Returns:
      list: Reservation ORM objects that should have their containers started.
  """
  with Session() as session:
    reservations = session.execute(
      select(Reservation).where(
        Reservation.status == "reserved",
        Reservation.computerId == computer_id,
        Reservation.startDate < time_now()
      )
    ).scalars().all()
    return reservations


def get_running_reservations(computer_id: int):
  """Get all currently running reservations on the given computer.

  Queries for reservations with status "started" whose start date has
  passed and end date has not yet been reached. Eager-loads the
  reservedContainer relationship.

  Args:
      computer_id: Database ID of the computer to query.

  Returns:
      list: Reservation ORM objects that are currently running.
  """
  with Session() as session:
    reservations = session.execute(
      select(Reservation).options(
        joinedload(Reservation.reservedContainer)
      ).where(
        Reservation.status == "started",
        Reservation.startDate < time_now(),
        Reservation.computerId == computer_id,
        Reservation.endDate > time_now()
      )
    ).scalars().all()
    return reservations


def get_reservations_requiring_stop(computer_id: int):
  """Get all reservations that need to be stopped on the given computer.

  Queries for reservations with status "started" or "reserved" whose
  end date has already passed.

  Args:
      computer_id: Database ID of the computer to query.

  Returns:
      list: Reservation ORM objects whose containers should be stopped.
  """
  with Session() as session:
    reservations = session.execute(
      select(Reservation).where(
        Reservation.computerId == computer_id,
        Reservation.status.in_(["started", "reserved", "restart_error", "paused"]),
        Reservation.endDate < time_now()
      )
    ).scalars().all()
    return reservations


def get_reservations_requiring_restart(computer_id: int):
  """Get all reservations flagged for restart on the given computer.

  Queries for reservations with status "restart" whose end date has
  not yet been reached.

  Args:
      computer_id: Database ID of the computer to query.

  Returns:
      list: Reservation ORM objects whose containers should be restarted.
  """
  with Session() as session:
    reservations = session.execute(
      select(Reservation).where(
        Reservation.status == "restart",
        Reservation.computerId == computer_id,
        Reservation.endDate > time_now()
      )
    ).scalars().all()
    return reservations


def get_container_information(reservation_id: str):
  """Get the Docker container name and inspection data for a reservation.

  Looks up the reservation in the database, retrieves the associated
  Docker container name, and calls docker inspect to get full container
  state information.

  Args:
      reservation_id: Database ID of the reservation to inspect.

  Returns:
      tuple: A 2-element tuple of (container_name, container_inspect)
          where container_name is a string and container_inspect is a
          python_on_whales Container object with a .state attribute
          containing status, running, paused, exit_code, started_at, etc.
          Returns (None, {}) if the reservation is not found or on error.
  """
  try:
    with Session() as session:
      reservation = session.execute(
        select(Reservation).where(Reservation.reservationId == reservation_id)
      ).scalar_one_or_none()
      if reservation == None:
        return None, {}
      container_state = docker.container.inspect(reservation.reservedContainer.containerDockerName)
      return reservation.reservedContainer.containerDockerName, container_state
  except Exception as e:
    log.error(f"Error getting container information for reservation {reservation_id}: {e}")
    return None, {}


def get_computer_id(computer_name: str):
  """Get the database ID of a computer by its name.

  Args:
      computer_name: Name of the computer as stored in the database.

  Returns:
      int or None: The computer's database ID, or None if no computer
          with that name exists or an exception occurs.
  """
  try:
    with Session() as session:
      computer = session.execute(
        select(Computer).where(Computer.name == computer_name)
      ).scalar_one_or_none()
      if computer == None:
        return None
      return computer.computerId
  except Exception as e:
    log.error(f"Error getting computer ID for name '{computer_name}': {e}")
    return None


def get_running_reserved_docker_containers():
  """Find all Docker containers whose name starts with "reservation-".

  Lists all currently running Docker containers on this host and filters
  for those created by the reservation system (identified by the
  "reservation-" name prefix).

  Returns:
      list: python_on_whales Container objects for running reservation
          containers.
  """
  running_containers = docker.ps()

  # Filter containers whose names start with "reservation-"
  reservation_containers = [
  container for container in running_containers
    if container.name.startswith("reservation-")
  ]

  return reservation_containers


def get_containers_requiring_build():
  """Get all container definitions that have a pending image build.

  Queries for Container records where buildStatus is "pending",
  indicating the admin has saved Dockerfile commands and the image
  needs to be built.

  Returns:
      list: Container ORM objects that need their images built.
  """
  with Session() as session:
    containers = session.execute(
      select(Container).where(Container.buildStatus == "pending")
    ).scalars().all()
    return containers


def get_containers_requiring_image_removal():
  """Get all container definitions that need their Docker image removed.

  Queries for Container records where buildStatus is "removing",
  indicating the admin removed the container and the image should
  be cleaned up from Docker.

  Returns:
      list: Container ORM objects that need their images removed.
  """
  with Session() as session:
    containers = session.execute(
      select(Container).where(Container.buildStatus == "removing")
    ).scalars().all()
    return containers


def get_low_priority_running_reservations(computer_id: int):
  """Get all running low-priority reservations on the given computer.

  Args:
      computer_id: Database ID of the computer to query.

  Returns:
      list: Reservation ORM objects for running low-priority containers.
  """
  with Session() as session:
    reservations = session.execute(
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
    return reservations


def get_paused_reservations(computer_id: int):
  """Get all paused reservations waiting to resume on the given computer.

  Ordered by createdAt ascending (FIFO) so the oldest paused reservation
  gets priority when resources free up.

  Args:
      computer_id: Database ID of the computer to query.

  Returns:
      list: Reservation ORM objects for paused low-priority containers.
  """
  with Session() as session:
    reservations = session.execute(
      select(Reservation)
      .options(
        joinedload(Reservation.reservedHardwareSpecs).joinedload(ReservedHardwareSpec.hardwareSpec),
        joinedload(Reservation.reservedContainer),
        joinedload(Reservation.user),
        joinedload(Reservation.computer),
      )
      .where(
        Reservation.status == "paused",
        Reservation.computerId == computer_id,
        Reservation.endDate > time_now()
      )
      .order_by(Reservation.createdAt.asc())
    ).unique().scalars().all()
    return reservations


def get_future_normal_reservations(computer_id: int, start_time, end_time):
  """Get non-low-priority reservations overlapping a future time window.

  Used for look-ahead conflict checking to prevent thrashing when
  deciding whether to resume a paused low-priority container.

  Args:
      computer_id: Database ID of the computer to query.
      start_time: Start of the time window to check.
      end_time: End of the time window to check.

  Returns:
      list: Reservation ORM objects for normal reservations in the window.
  """
  with Session() as session:
    reservations = session.execute(
      select(Reservation)
      .options(
        joinedload(Reservation.reservedHardwareSpecs).joinedload(ReservedHardwareSpec.hardwareSpec)
      )
      .where(
        Reservation.computerId == computer_id,
        Reservation.isLowPriority == False,
        Reservation.status.in_(["reserved", "started"]),
        Reservation.startDate < end_time,
        Reservation.endDate > start_time
      )
    ).unique().scalars().all()
    return reservations


def get_all_active_reservations(computer_id: int):
  """Get all active reservations (started or reserved) on the given computer.

  Used to calculate current resource usage for preemption decisions.

  Args:
      computer_id: Database ID of the computer to query.

  Returns:
      list: Reservation ORM objects for all active reservations.
  """
  with Session() as session:
    reservations = session.execute(
      select(Reservation)
      .options(
        joinedload(Reservation.reservedHardwareSpecs).joinedload(ReservedHardwareSpec.hardwareSpec)
      )
      .where(
        Reservation.computerId == computer_id,
        Reservation.status.in_(["started", "reserved"]),
        Reservation.endDate > time_now()
      )
    ).unique().scalars().all()
    return reservations


def reset_stale_building_status():
  """Reset any containers stuck in "building" status back to "pending".

  This handles the case where the daemon was restarted while a build
  was in progress. Called once at daemon startup.

  Returns:
      int: Number of containers that were reset.
  """
  with Session() as session:
    containers = session.execute(
      select(Container).where(Container.buildStatus == "building")
    ).scalars().all()
    count = len(containers)
    for container in containers:
      container.buildStatus = "pending"
    if count > 0:
      session.commit()
      log.info(f"Reset {count} stale 'building' status(es) to 'pending'")
    return count
