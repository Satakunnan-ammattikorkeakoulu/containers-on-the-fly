"""Reservation API endpoints for browsing hardware, creating, managing, and
cancelling container reservations.

Endpoints handle input validation and sanitization before delegating
business logic to ``endpoints.responses.reservation``.
"""

from fastapi import APIRouter, Depends
from helpers.server import api_response, force_authentication
from helpers.auth import is_admin, get_authenticated_user_id
from endpoints.responses.user import validate_script_path
from fastapi.security import OAuth2PasswordBearer
from endpoints.responses import reservation as functionality
from endpoints.models.reservation import ReservationFilters, UserReservationRequest, UserActivityRequest
import json
import re

router = APIRouter(
    prefix="/api/reservation",
    tags=["Reservation"],
    responses={404: {"description": "Not found"}},
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/user/login")

@router.get("/get_available_hardware")
def get_available_hardware(date : str, duration: int, token: str = Depends(oauth2_scheme)):
  """Retrieve hardware resources available for a given date and duration.

  Args:
      date: Desired start date/time string for the reservation.
      duration: Reservation duration in hours.
      token: OAuth2 bearer token (injected by Depends).

  Returns:
      Available hardware specs per computer wrapped in an API response.
  """
  userId = get_authenticated_user_id(token)
  return functionality.get_available_hardware(date, duration, None, is_admin(userId), None, userId)

@router.get("/get_availability_timeline")
def get_availability_timeline(startDate: str, endDate: str, token: str = Depends(oauth2_scheme)):
  """Retrieve a timeline of hardware availability over a date range.

  Args:
      startDate: Start of the date range.
      endDate: End of the date range.
      token: OAuth2 bearer token (injected by Depends).

  Returns:
      Availability timeline data wrapped in an API response.
  """
  userId = get_authenticated_user_id(token)
  return functionality.get_availability_timeline(startDate, endDate, is_admin(userId))

@router.get("/get_all_reservations_for_calendar")
def get_all_reservations_for_calendar(startDate: str, endDate: str, token: str = Depends(oauth2_scheme)):
  """Retrieve all reservations within a date range for the calendar view.

  Args:
      startDate: Start of the date range.
      endDate: End of the date range.
      token: OAuth2 bearer token (injected by Depends).

  Returns:
      List of reservations formatted for calendar display.
  """
  force_authentication(token)
  return functionality.get_all_reservations_for_calendar(startDate, endDate)

@router.post("/get_own_reservations")
def get_own_reservations(request: UserReservationRequest, token: str = Depends(oauth2_scheme)):
  """Retrieve the authenticated user's own reservations with pagination.

  Args:
      request: Pagination, sorting, and filter parameters.
      token: OAuth2 bearer token (injected by Depends).

  Returns:
      Paginated list of the user's reservations with status counts.
  """
  userId = get_authenticated_user_id(token)
  return functionality.get_own_reservations(userId, request)

@router.post("/get_own_activity")
def get_own_activity(request: UserActivityRequest, token: str = Depends(oauth2_scheme)):
  """Retrieve audit log entries for the authenticated user's own reservations.

  Args:
      request: Pagination, sorting, and filter parameters.
      token: OAuth2 bearer token (injected by Depends).

  Returns:
      Paginated list of audit log entries for the user's reservations,
      along with the current audit log retention setting.
  """
  userId = get_authenticated_user_id(token)
  return functionality.get_own_activity(userId, request)

@router.post("/mark_activity_seen")
def mark_activity_seen(token: str = Depends(oauth2_scheme)):
  """Mark the authenticated user's activity feed as seen up to now.

  Args:
      token: OAuth2 bearer token (injected by Depends).

  Returns:
      Response containing the previous activityLastSeenAt value so the
      caller can highlight rows that arrived since the prior view.
  """
  userId = get_authenticated_user_id(token)
  return functionality.mark_own_activity_seen(userId)

@router.get("/get_public_computers")
def get_public_computers(token: str = Depends(oauth2_scheme)):
  """Return names and IP addresses of all public computers.

  Args:
      token: OAuth2 bearer token (injected by Depends).

  Returns:
      API response with a list of public computers (name and IP only).
  """
  userId = get_authenticated_user_id(token)
  return functionality.get_public_computers(userId)

@router.get("/get_own_reservation_details")
def get_own_reservation_details(reservationId: int, token: str = Depends(oauth2_scheme)):
  """Retrieve detailed information for one of the user's own reservations.

  Args:
      reservationId: ID of the reservation to retrieve.
      token: OAuth2 bearer token (injected by Depends).

  Returns:
      Reservation details (container info, hardware, ports) wrapped in an
      API response, or an error if the reservation does not belong to the user.
  """
  userId = get_authenticated_user_id(token)
  return functionality.get_own_reservation_details(reservationId, userId)

@router.post("/create_reservation")
def create_reservation(date: str, duration: int, computerId: int, containerId: int, hardwareSpecs, adminReserveUserEmail, description: str = "", shmSizePercent: int = 50, ramDiskSizePercent: int = 0, isLowPriority: bool = False, startScriptPath: str = "", stopScriptPath: str = "", token: str = Depends(oauth2_scheme)):
  """Create a new container reservation after validating all inputs.

  Validates date, duration, IDs, email format, description length (max 40),
  SHM/RAM-disk percentages, script paths, and hardware specs JSON
  before delegating to the business logic layer.

  Args:
      date: Desired start date/time string (max 50 chars).
      duration: Reservation duration in hours (1 -- 8760).
      computerId: ID of the target computer/server.
      containerId: ID of the container image to launch.
      hardwareSpecs: JSON string mapping hardware spec IDs to amounts.
      adminReserveUserEmail: Email of the user to reserve for (admin only),
          or empty/None for self-reservation.
      description: Optional short description (max 40 chars).
      shmSizePercent: Shared memory size as a percentage of RAM (0 -- 90).
      ramDiskSizePercent: RAM disk size as a percentage of RAM (0 -- 60).
      isLowPriority: Whether this is a low-priority reservation (default False).
      startScriptPath: Absolute path to a start script inside the container
          (optional, overrides user profile default).
      stopScriptPath: Absolute path to a stop script inside the container
          (optional, overrides user profile default).
      token: OAuth2 bearer token (injected by Depends).

  Returns:
      Success API response with reservation details, or failure response
      with a validation error message.
  """
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
    if len(description) > 40:
      return api_response(False, "Description too long (max 40 characters).")
    # Remove potentially harmful characters
    description = re.sub(r'[<>"\']', '', description)

  # Validate SHM size percentage
  if not isinstance(shmSizePercent, int) or shmSizePercent < 10 or shmSizePercent > 90:
    return api_response(False, "SHM size percentage must be between 10 and 90.")

  # Validate RAM disk size percentage
  if not isinstance(ramDiskSizePercent, int) or ramDiskSizePercent < 0 or ramDiskSizePercent > 60:
    return api_response(False, "RAM disk size percentage must be between 0 and 60.")

  # Validate script paths
  if startScriptPath:
    startScriptPath = str(startScriptPath).strip()
    if startScriptPath:
      error = validate_script_path(startScriptPath)
      if error:
        return api_response(False, f"Start script path: {error}")

  if stopScriptPath:
    stopScriptPath = str(stopScriptPath).strip()
    if stopScriptPath:
      error = validate_script_path(stopScriptPath)
      if error:
        return api_response(False, f"Stop script path: {error}")

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
  return functionality.create_reservation(userId, date, duration, computerId, containerId, hardwareSpecs, adminReserveUserEmail, description, shmSizePercent, ramDiskSizePercent, isLowPriority, startScriptPath, stopScriptPath)

@router.get("/get_current_reservations")
def get_current_reservations(token: str = Depends(oauth2_scheme)):
  """Retrieve all currently active (running) reservations.

  Args:
      token: OAuth2 bearer token (injected by Depends).

  Returns:
      List of active reservations wrapped in an API response.
  """
  force_authentication(token)
  return functionality.get_current_reservations()

@router.post("/cancel_reservation")
def cancel_reservation(reservationId: int, token: str = Depends(oauth2_scheme)):
  """Cancel a reservation owned by the authenticated user.

  Args:
      reservationId: ID of the reservation to cancel.
      token: OAuth2 bearer token (injected by Depends).

  Returns:
      Success or failure API response.
  """
  userId = get_authenticated_user_id(token)
  return functionality.cancel_reservation(userId, reservationId)

@router.post("/extend_reservation")
def extend_reservation(reservationId: int, duration : int, token: str = Depends(oauth2_scheme)):
  """Extend the end time of an active reservation.

  Args:
      reservationId: ID of the reservation to extend.
      duration: Additional hours to add to the reservation.
      token: OAuth2 bearer token (injected by Depends).

  Returns:
      Success or failure API response.
  """
  userId = get_authenticated_user_id(token)
  return functionality.extend_reservation(userId, reservationId, duration)

@router.post("/update_reservation_description")
def update_reservation_description(reservationId: int, description: str = "", token: str = Depends(oauth2_scheme)):
  """Update the description of an existing reservation.

  Sanitizes the description by stripping whitespace and removing
  potentially harmful characters before saving.

  Args:
      reservationId: ID of the reservation to update.
      description: New description text (max 40 chars after sanitization).
      token: OAuth2 bearer token (injected by Depends).

  Returns:
      Success or failure API response.
  """
  userId = get_authenticated_user_id(token)

  # Validate and sanitize description
  description = str(description).strip()
  if len(description) > 40:
    return api_response(False, "Description too long (max 40 characters).")
  description = re.sub(r'[<>"\']', '', description)

  return functionality.update_reservation_description(userId, reservationId, description)

@router.post("/restart_container")
def restart_container(reservationId: int, token: str = Depends(oauth2_scheme)):
  """Restart the Docker container associated with a reservation.

  Args:
      reservationId: ID of the reservation whose container to restart.
      token: OAuth2 bearer token (injected by Depends).

  Returns:
      Success or failure API response.
  """
  userId = get_authenticated_user_id(token)
  return functionality.restart_container(userId, reservationId)