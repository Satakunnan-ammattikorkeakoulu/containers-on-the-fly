"""API router configuration and application startup initialization.

Registers all endpoint routers (user, reservation, admin, app) onto a
single FastAPI APIRouter. Also runs one-time startup logic when the module
is imported: ensures required roles exist ("everyone", "admin") and
optionally seeds test data in development mode.
"""

from fastapi import APIRouter
from endpoints import user, reservation, admin, app
from settings_handler import settings_handler
from helpers.auth import hash_password
from database import ContainerPort, Session, User, Role, Computer, HardwareSpec, Container
from sqlalchemy import select
import base64
import sqlalchemy as sa

router = APIRouter()
router.include_router(user.router)
router.include_router(reservation.router)
router.include_router(admin.router)
router.include_router(app.router)


# Run code here when server starts

if settings_handler.get_setting("app.production") == True:
  print("Running server in production mode")
else:
  print("Running server in development mode")

# Add everyone role if it does not exist
with Session() as session:
  everyoneRole = session.execute(select(Role).where(Role.name == "everyone")).scalar_one_or_none()
  if everyoneRole is None:
    print("Creating role everyone")
    session.add(Role(
      name = "everyone"
    ))
    session.commit()

# Add admin role if it does not exist
with Session() as session:
  adminRole = session.execute(select(Role).where(Role.name == "admin")).scalar_one_or_none()
  if adminRole is None:
    print("Creating role admin")
    session.add(Role(
      name = "admin"
    ))
    session.commit()

if settings_handler.get_setting("app.addTestDataInDevelopment"):
  with Session() as session:
    # Admin user
    adminUser = session.execute(select(User).where(User.email == "admin@foo.com")).scalar_one_or_none()
    if adminUser is None:
      print("Creating test data: admin user with email admin@foo.com")
      hash = hash_password("test")
      adminUser = User(
        email = "admin@foo.com",
        password = base64.b64encode(hash["hashedPassword"]).decode('utf-8'),
        passwordSalt = base64.b64encode(hash["salt"]).decode('utf-8')
      )
      adminRole = session.execute(select(Role).where(Role.name == "admin")).scalar_one_or_none()
      adminUser.roles.append(adminRole)
      session.add(adminUser)
      session.commit()

    # Normal User
    normalUser = session.execute(select(User).where(User.email == "user@foo.com")).scalar_one_or_none()
    if normalUser is None:
      print("Creating test data: normal user with email user@foo.com")
      hash = hash_password("test")
      normalUser = User(
        email = "user@foo.com",
        password = base64.b64encode(hash["hashedPassword"]).decode('utf-8'),
        passwordSalt = base64.b64encode(hash["salt"]).decode('utf-8')
      )
      session.add(normalUser)
      session.commit()

    # Computer
    computer = session.execute(select(Computer).where(Computer.name == "server1")).scalar_one_or_none()
    if computer is None:
      print("Creating test data: computer named server1")
      computer = Computer( name = "server1", ip = settings_handler.get_setting("app.serverIp"), public = True )
      session.add(computer)
      session.commit()

    # Hardware Specs for computer
    computer = session.execute(select(Computer).where(Computer.name == "server1")).scalar_one_or_none()
    if len(computer.hardwareSpecs) == 0:
      print("Creating test data: hardware specs for a computer")
      computer.hardwareSpecs.append(HardwareSpec(
        type = "gpus",
        maximumAmount = 0,
        # Only this will have effect on GPUS to set how many can be reserved, individual GPUs are then individually set as described below
        maximumAmountForUser = 1,
        defaultAmountForUser = 0,
        minimumAmount = 0,
        format = "GPUs",
      ))
      '''computer.hardwareSpecs.append(HardwareSpec(
        type = "gpu",
        maximumAmount = 1,        # Keep as 1
        maximumAmountForUser = 1, # Keep as 1
        defaultAmountForUser = 0, # Keep as 0
        minimumAmount = 0,        # Keep as 0
        internalId = "0", # Nvidia / cuda ID of the device
        format = "NVIDIA RTX A5000 24GB",
      ))
      computer.hardwareSpecs.append(HardwareSpec(
        type = "gpu",
        maximumAmount = 1,        # Keep as 1
        maximumAmountForUser = 1, # Keep as 1
        defaultAmountForUser = 0, # Keep as 0
        minimumAmount = 0,        # Keep as 0
        internalId = "1", # Nvidia / cuda ID of the device
        format = "NVIDIA RTX A5000 24GB",
      ))'''
      computer.hardwareSpecs.append(HardwareSpec(
        type = "ram",
        maximumAmount = 10,
        maximumAmountForUser = 10,
        defaultAmountForUser = 1,
        minimumAmount = 1,
        format = "GB",
      ))
      computer.hardwareSpecs.append(HardwareSpec(
        type = "cpus",
        maximumAmount = 5,
        maximumAmountForUser = 5,
        defaultAmountForUser = 1,
        minimumAmount = 1,
        format = "CPUs",
      ))
      session.commit()

    # Container
    container = session.execute(select(Container).where(Container.imageName == "ubuntu-base")).scalar_one_or_none()
    if container is None:
      print("Creating test data: container with imageName ubuntu-base")
      container = Container(
        public = True,
        imageName = "ubuntu-base",
        name = "Ubuntu Base Image",
        description = "Ubuntu Base Image"
      )
      container.containerPorts.append(ContainerPort(
        serviceName = "SSH",
        port = 22
      ))
      session.add(container)
      session.commit()
