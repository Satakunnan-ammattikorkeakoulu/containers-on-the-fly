import random
import socket
from database import Session, Reservation
from settings_handler import settings_handler


def is_port_in_use(port: int) -> bool:
  '''
  Checks if a port is in use.
  Returns:
    True if port is in use, False otherwise
  '''
  with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    return s.connect_ex(('localhost', port)) == 0

def get_available_port():
  # Loop through all started containers and get the ports in use
  portsInUse = []
  with Session() as session:
    allActiveReservations = session.query(Reservation).filter( Reservation.status == "started" )
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
