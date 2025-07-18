from fastapi import APIRouter, Depends, Request
from helpers.server import ForceAuthentication, Response
from fastapi.security import OAuth2PasswordBearer
from endpoints.responses import admin as functionality
from endpoints.models.admin import ContainerEdit, ComputerEdit, UserEdit
from endpoints.models.reservation import ReservationFilters
from database import Session, Computer, ContainerPort, User, Reservation, Container, ReservedContainer, ReservedHardwareSpec, HardwareSpec, UserRole
from sqlalchemy import desc
import datetime
from pydantic import BaseModel

router = APIRouter(
    prefix="/api/admin",
    tags=["Admin"],
    responses={404: {"description": "Not found"}},
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/user/login")

@router.post("/reservations")
async def getReservations(filters : ReservationFilters, token: str = Depends(oauth2_scheme)):
  ForceAuthentication(token, "admin")
  return functionality.getReservations(filters)

@router.get("/users")
async def getUsers(token: str = Depends(oauth2_scheme)):
  ForceAuthentication(token, "admin")
  return functionality.getUsers()

@router.get("/hardware")
async def getHardware(token: str = Depends(oauth2_scheme)):
  ForceAuthentication(token, "admin")
  return functionality.getHardware()

@router.get("/containers")
async def getContainers(token: str = Depends(oauth2_scheme)):
  ForceAuthentication(token, "admin")
  return functionality.getContainers()

@router.get("/computers")
async def getComputers(token: str = Depends(oauth2_scheme)):
  ForceAuthentication(token, "admin")
  return functionality.getComputers()

@router.get("/computer")
async def getComputer(computerId : int, token: str = Depends(oauth2_scheme)):
  ForceAuthentication(token, "admin")
  return functionality.getComputer(computerId)

@router.post("/save_computer")
async def saveComputer(computerEdit : ComputerEdit, token: str = Depends(oauth2_scheme)):
  ForceAuthentication(token, "admin")
  return functionality.saveComputer(computerEdit)

@router.post("/remove_computer")
async def removeComputer(computerId : int, token: str = Depends(oauth2_scheme)):
  ForceAuthentication(token, "admin")
  return functionality.removeComputer(computerId)

@router.get("/container")
async def getContainer(containerId : int, token: str = Depends(oauth2_scheme)):
  ForceAuthentication(token, "admin")
  return functionality.getContainer(containerId)

@router.post("/save_container")
async def saveContainer(containerEdit : ContainerEdit, token: str = Depends(oauth2_scheme)):
  ForceAuthentication(token, "admin")
  return functionality.saveContainer(containerEdit)

@router.post("/remove_container")
async def removeContainer(containerId : int, token: str = Depends(oauth2_scheme)):
  ForceAuthentication(token, "admin")
  return functionality.removeContainer(containerId)

@router.post("/edit_reservation")
async def editReservation(reservationId : int, endDate : str, token: str = Depends(oauth2_scheme)):
  ForceAuthentication(token, "admin")
  return functionality.editReservation(reservationId, endDate)

@router.get("/user")
async def getUser(userId: int, token: str = Depends(oauth2_scheme)):
    ForceAuthentication(token, "admin")
    return functionality.getUser(userId)

@router.post("/save_user")
async def saveUser(userEdit: UserEdit, token: str = Depends(oauth2_scheme)):
    ForceAuthentication(token, "admin")
    return functionality.saveUser(userEdit.userId, userEdit.data)

