"""Database queries for the Docker utility daemon.

Provides query functions to retrieve reservations in various lifecycle
states (needing start, stop, restart) and to look up container and
computer information. Used exclusively by the daemon module.
"""

from python_on_whales import docker
from database import Session, Reservation, Computer
from sqlalchemy import select
from sqlalchemy.orm import joinedload
import datetime
from datetime import timezone


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
        Reservation.status.in_(["started", "reserved"]),
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
    print(f"Something went wrong getting container information for reservation {reservation_id}. Error:")
    print(e)
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
    print(f"Something went wrong getting computer ID for name: {computer_name}. Error:")
    print(e)
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
