from python_on_whales import docker
from database import Session, Reservation, Computer
import datetime
from datetime import timezone


def timeNow():
  return datetime.datetime.now(datetime.timezone.utc)


def getReservationsRequiringStart(computerId: int):
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


def getRunningReservations(computerId: int):
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


def getReservationsRequiringStop(computerId: int):
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


def getReservationsRequiringRestart(computerId: int):
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
