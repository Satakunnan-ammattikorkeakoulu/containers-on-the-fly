from fastapi import APIRouter, Depends
from helpers.server import Response, ForceAuthentication
from helpers.auth import CheckToken, IsAdmin, get_authenticated_user_id
from fastapi.security import OAuth2PasswordBearer
from endpoints.responses import reservation as functionality
from endpoints.models.reservation import ReservationFilters
import json
import re

router = APIRouter(
    prefix="/api/reservation",
    tags=["Reservation"],
    responses={404: {"description": "Not found"}},
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/user/login")

@router.get("/get_available_hardware")
async def getAvailableHardware(date : str, duration: int, token: str = Depends(oauth2_scheme)):
  userId = get_authenticated_user_id(token)
  return functionality.getAvailableHardware(date, duration, None, IsAdmin(userId), None, userId)

@router.get("/get_availability_timeline")
async def getAvailabilityTimeline(startDate: str, endDate: str, token: str = Depends(oauth2_scheme)):
  userId = get_authenticated_user_id(token)
  return functionality.getAvailabilityTimeline(startDate, endDate, IsAdmin(userId))

@router.get("/get_all_reservations_for_calendar")
async def getAllReservationsForCalendar(startDate: str, endDate: str, token: str = Depends(oauth2_scheme)):
  ForceAuthentication(token)
  return functionality.getAllReservationsForCalendar(startDate, endDate)

@router.post("/get_own_reservations")
async def getOwnReservations(filters : ReservationFilters, token: str = Depends(oauth2_scheme)):
  userId = get_authenticated_user_id(token)
  return functionality.getOwnReservations(userId, filters)

@router.get("/get_own_reservation_details")
async def getOwnReservations(reservationId: int, token: str = Depends(oauth2_scheme)):
  userId = get_authenticated_user_id(token)
  return functionality.getOwnReservationDetails(reservationId, userId)

@router.post("/create_reservation")
async def CreateReservation(date: str, duration: int, computerId: int, containerId: int, hardwareSpecs, adminReserveUserEmail, description: str = "", shmSizePercent: int = 50, ramDiskSizePercent: int = 0, token: str = Depends(oauth2_scheme)):
  ForceAuthentication(token)
  
  # Validate date parameter
  if not date or not isinstance(date, str) or len(date) > 50:
    return Response(False, "Invalid date parameter.")
  
  # Validate duration
  if not isinstance(duration, int) or duration <= 0 or duration > 8760:  # Max 1 year
    return Response(False, "Invalid duration parameter.")
  
  # Validate computer and container IDs
  if not isinstance(computerId, int) or computerId <= 0:
    return Response(False, "Invalid computer ID.")
  if not isinstance(containerId, int) or containerId <= 0:
    return Response(False, "Invalid container ID.")
  
  # Validate and sanitize email
  if adminReserveUserEmail:
    adminReserveUserEmail = str(adminReserveUserEmail).strip()
    if len(adminReserveUserEmail) > 255:
      return Response(False, "Admin email address too long.")
    # Basic email validation
    if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', adminReserveUserEmail):
      return Response(False, "Invalid admin email format.")
  
  # Validate and sanitize description
  if description:
    description = str(description).strip()
    if len(description) > 50:
      return Response(False, "Description too long (max 50 characters).")
    # Remove potentially harmful characters
    description = re.sub(r'[<>"\']', '', description)
  
  # Validate SHM size percentage
  if not isinstance(shmSizePercent, int) or shmSizePercent < 0 or shmSizePercent > 90:
    return Response(False, "SHM size percentage must be between 0 and 90.")
  
  # Validate RAM disk size percentage
  if not isinstance(ramDiskSizePercent, int) or ramDiskSizePercent < 0 or ramDiskSizePercent > 60:
    return Response(False, "RAM disk size percentage must be between 0 and 60.")
  
  # Validate hardwareSpecs JSON
  try:
    hardwareSpecs = json.loads(hardwareSpecs)
    if not isinstance(hardwareSpecs, dict):
      return Response(False, "Hardware specs must be a valid JSON object.")
    
    # Validate each hardware spec
    for key, val in hardwareSpecs.items():
      if not isinstance(key, str) or not key.isdigit():
        return Response(False, "Invalid hardware spec ID format.")
      if not isinstance(val, (int, float)) or val < 0:
        return Response(False, "Invalid hardware spec amount.")
  except (json.JSONDecodeError, ValueError, TypeError):
    return Response(False, "Invalid hardware specs JSON format.")
  
  userId = get_authenticated_user_id(token)
  return functionality.createReservation(userId, date, duration, computerId, containerId, hardwareSpecs, adminReserveUserEmail, description, shmSizePercent, ramDiskSizePercent)

@router.get("/get_current_reservations")
async def getCurrentReservations(token: str = Depends(oauth2_scheme)):
  ForceAuthentication(token)
  return functionality.getCurrentReservations()

@router.post("/cancel_reservation")
async def cancelReservation(reservationId: str, token: str = Depends(oauth2_scheme)):
  userId = get_authenticated_user_id(token)
  return functionality.cancelReservation(userId, reservationId)

@router.post("/extend_reservation")
async def extendReservation(reservationId: str, duration : int, token: str = Depends(oauth2_scheme)):
  userId = get_authenticated_user_id(token)
  return functionality.extendReservation(userId, reservationId, duration)

@router.post("/restart_container")
async def RestartContainer(reservationId: str, token: str = Depends(oauth2_scheme)):
  userId = get_authenticated_user_id(token)
  return functionality.restartContainer(userId, reservationId)