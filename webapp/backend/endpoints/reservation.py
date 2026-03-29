from fastapi import APIRouter, Depends
from helpers.server import api_response, force_authentication
from helpers.auth import check_token, is_admin, get_authenticated_user_id
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
async def get_available_hardware(date : str, duration: int, token: str = Depends(oauth2_scheme)):
  userId = get_authenticated_user_id(token)
  return functionality.get_available_hardware(date, duration, None, is_admin(userId), None, userId)

@router.get("/get_availability_timeline")
async def get_availability_timeline(startDate: str, endDate: str, token: str = Depends(oauth2_scheme)):
  userId = get_authenticated_user_id(token)
  return functionality.get_availability_timeline(startDate, endDate, is_admin(userId))

@router.get("/get_all_reservations_for_calendar")
async def get_all_reservations_for_calendar(startDate: str, endDate: str, token: str = Depends(oauth2_scheme)):
  force_authentication(token)
  return functionality.get_all_reservations_for_calendar(startDate, endDate)

@router.post("/get_own_reservations")
async def get_own_reservations(filters : ReservationFilters, token: str = Depends(oauth2_scheme)):
  userId = get_authenticated_user_id(token)
  return functionality.get_own_reservations(userId, filters)

@router.get("/get_own_reservation_details")
async def get_own_reservation_details(reservationId: int, token: str = Depends(oauth2_scheme)):
  userId = get_authenticated_user_id(token)
  return functionality.get_own_reservation_details(reservationId, userId)

@router.post("/create_reservation")
async def create_reservation(date: str, duration: int, computerId: int, containerId: int, hardwareSpecs, adminReserveUserEmail, description: str = "", shmSizePercent: int = 50, ramDiskSizePercent: int = 0, token: str = Depends(oauth2_scheme)):
  force_authentication(token)

  # Validate date parameter
  if not date or not isinstance(date, str) or len(date) > 50:
    return api_response(False, "Invalid date parameter.")

  # Validate duration
  if not isinstance(duration, int) or duration <= 0 or duration > 8760:  # Max 1 year
    return api_response(False, "Invalid duration parameter.")

  # Validate computer and container IDs
  if not isinstance(computerId, int) or computerId <= 0:
    return api_response(False, "Invalid computer ID.")
  if not isinstance(containerId, int) or containerId <= 0:
    return api_response(False, "Invalid container ID.")

  # Validate and sanitize email
  if adminReserveUserEmail:
    adminReserveUserEmail = str(adminReserveUserEmail).strip()
    if len(adminReserveUserEmail) > 255:
      return api_response(False, "Admin email address too long.")
    # Basic email validation
    if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', adminReserveUserEmail):
      return api_response(False, "Invalid admin email format.")

  # Validate and sanitize description
  if description:
    description = str(description).strip()
    if len(description) > 50:
      return api_response(False, "Description too long (max 50 characters).")
    # Remove potentially harmful characters
    description = re.sub(r'[<>"\']', '', description)

  # Validate SHM size percentage
  if not isinstance(shmSizePercent, int) or shmSizePercent < 0 or shmSizePercent > 90:
    return api_response(False, "SHM size percentage must be between 0 and 90.")

  # Validate RAM disk size percentage
  if not isinstance(ramDiskSizePercent, int) or ramDiskSizePercent < 0 or ramDiskSizePercent > 60:
    return api_response(False, "RAM disk size percentage must be between 0 and 60.")

  # Validate hardwareSpecs JSON
  try:
    hardwareSpecs = json.loads(hardwareSpecs)
    if not isinstance(hardwareSpecs, dict):
      return api_response(False, "Hardware specs must be a valid JSON object.")

    # Validate each hardware spec
    for key, val in hardwareSpecs.items():
      if not isinstance(key, str) or not key.isdigit():
        return api_response(False, "Invalid hardware spec ID format.")
      if not isinstance(val, (int, float)) or val < 0:
        return api_response(False, "Invalid hardware spec amount.")
  except (json.JSONDecodeError, ValueError, TypeError):
    return api_response(False, "Invalid hardware specs JSON format.")

  userId = get_authenticated_user_id(token)
  return functionality.create_reservation(userId, date, duration, computerId, containerId, hardwareSpecs, adminReserveUserEmail, description, shmSizePercent, ramDiskSizePercent)

@router.get("/get_current_reservations")
async def get_current_reservations(token: str = Depends(oauth2_scheme)):
  force_authentication(token)
  return functionality.get_current_reservations()

@router.post("/cancel_reservation")
async def cancel_reservation(reservationId: str, token: str = Depends(oauth2_scheme)):
  userId = get_authenticated_user_id(token)
  return functionality.cancel_reservation(userId, reservationId)

@router.post("/extend_reservation")
async def extend_reservation(reservationId: str, duration : int, token: str = Depends(oauth2_scheme)):
  userId = get_authenticated_user_id(token)
  return functionality.extend_reservation(userId, reservationId, duration)

@router.post("/restart_container")
async def restart_container(reservationId: str, token: str = Depends(oauth2_scheme)):
  userId = get_authenticated_user_id(token)
  return functionality.restart_container(userId, reservationId)