"""Port allocation utilities for Docker container reservations.

Manages finding available ports within the configured range for binding
container services to the host machine. Checks both database records of
active reservations and actual socket availability.
"""

import random
import socket
from database import Session, Reservation
from settings_handler import settings_handler
from sqlalchemy import select


def is_port_in_use(port: int) -> bool:
  """Check whether a port is currently in use on localhost.

  Attempts a TCP connection to the given port on localhost to determine
  if anything is listening.

  Args:
      port: TCP port number to check.

  Returns:
      bool: True if the port is in use, False otherwise.
  """
  with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    return s.connect_ex(('localhost', port)) == 0

def get_available_port():
  """Find an available port within the configured port range.

  Queries the database for all ports currently used by active (started)
  reservations, builds a list of available ports within the configured
  range (docker.port_range_start to docker.port_range_end), then
  randomly selects one that is not bound on the host.

  Returns:
      int: An available port number.

  Raises:
      IndexError: If no ports are available in the configured range
          (all are in use by active reservations).
  """
  # Loop through all started containers and get the ports in use
  portsInUse = []
  with Session() as session:
    allActiveReservations = session.execute(
      select(Reservation).where(Reservation.status == "started")
    ).scalars().all()
    for reservation in allActiveReservations:
      for usedPort in reservation.reservedContainer.reservedContainerPorts:
        portsInUse.append(usedPort.outsidePort)
    min = settings_handler.get_setting("docker.port_range_start")
    max = settings_handler.get_setting("docker.port_range_end")
    availablePorts = []
    for port in range(min, max):
      if port not in portsInUse:
        availablePorts.append(port)

  # Try to bind to a random available port 50 times
  i = 0
  retries = 50
  while i < retries:
    randPort = random.choice(availablePorts)
    if is_port_in_use(randPort) == False:
       return randPort
    i += 1

  print("ERROR: Did not find a random port to bind to after 50 attempts. Randomly giving one out.")
  return random.choice(availablePorts)
