"""Admin API endpoints for managing containers, computers, users, roles, and settings.

All endpoints in this module require admin-level authentication. Delegates
business logic to ``endpoints.responses.admin``.
"""

from fastapi import APIRouter, Depends, Request
from helpers.server import force_authentication, api_response
from fastapi.security import OAuth2PasswordBearer
from endpoints.responses import admin as functionality
from endpoints.models.admin import ContainerEdit, ComputerEdit, UserEdit, RoleMountsEdit, RoleHardwareLimitsEdit, RoleReservationLimitsEdit, AdminUsersRequest
from endpoints.models.reservation import ReservationFilters, AdminReservationRequest, UserReservationRequest
from database import Session, Computer, ContainerPort, User, Reservation, Container, ReservedContainer, ReservedHardwareSpec, HardwareSpec, UserRole, ServerStatus, ServerLogs
from sqlalchemy import desc, Column, Integer, Text, Float, ForeignKey, DateTime, UniqueConstraint, Boolean, BigInteger, func
import datetime
from pydantic import BaseModel
from helpers.tables.role import get_roles, get_role_by_id, add_role as add_role_helper, edit_role as edit_role_helper, remove_role as remove_role_helper
from helpers.server import api_response, orm_to_dict
from typing import Dict, Any, List

router = APIRouter(
    prefix="/api/admin",
    tags=["Admin"],
    responses={404: {"description": "Not found"}},
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="user/login")  # Make sure the tokenUrl is correct

@router.post("/reservations")
async def get_reservations(request: AdminReservationRequest, token: str = Depends(oauth2_scheme)):
  """Retrieve paginated reservations matching the given filters.

  Args:
      request: Pagination, sorting, and filter parameters.
      token: OAuth2 bearer token (injected by Depends).

  Returns:
      Paginated list of reservations with status counts and stats.
  """
  force_authentication(token, "admin")
  return functionality.get_reservations(request)

@router.post("/users")
async def get_users(request: AdminUsersRequest, token: str = Depends(oauth2_scheme)):
  """Retrieve paginated users matching the given filters.

  Args:
      request: Pagination, sorting, and filter parameters.
      token: OAuth2 bearer token (injected by Depends).

  Returns:
      Paginated list of users with total count and available roles.
  """
  force_authentication(token, "admin")
  return functionality.get_users(request)

@router.get("/hardware")
async def get_hardware(token: str = Depends(oauth2_scheme)):
  """Retrieve all hardware specifications.

  Args:
      token: OAuth2 bearer token (injected by Depends).

  Returns:
      List of hardware specs wrapped in an API response.
  """
  force_authentication(token, "admin")
  return functionality.get_hardware()

@router.get("/containers")
async def get_containers(token: str = Depends(oauth2_scheme)):
  """Retrieve all container definitions.

  Args:
      token: OAuth2 bearer token (injected by Depends).

  Returns:
      List of container definitions wrapped in an API response.
  """
  force_authentication(token, "admin")
  return functionality.get_containers()

@router.get("/computers")
async def get_computers(token: str = Depends(oauth2_scheme)):
  """Retrieve all computer (server) records.

  Args:
      token: OAuth2 bearer token (injected by Depends).

  Returns:
      List of computers wrapped in an API response.
  """
  force_authentication(token, "admin")
  return functionality.get_computers()

@router.get("/computer")
async def get_computer(computerId : int, token: str = Depends(oauth2_scheme)):
  """Retrieve details for a single computer.

  Args:
      computerId: ID of the computer to retrieve.
      token: OAuth2 bearer token (injected by Depends).

  Returns:
      Computer details wrapped in an API response.
  """
  force_authentication(token, "admin")
  return functionality.get_computer(computerId)

@router.post("/save_computer")
async def save_computer(computerEdit : ComputerEdit, token: str = Depends(oauth2_scheme)):
  """Create or update a computer record.

  Args:
      computerEdit: Pydantic model with computer fields to save.
      token: OAuth2 bearer token (injected by Depends).

  Returns:
      Success or failure API response.
  """
  force_authentication(token, "admin")
  return functionality.save_computer(computerEdit)

@router.post("/remove_computer")
async def remove_computer(computerId : int, token: str = Depends(oauth2_scheme)):
  """Remove a computer record by ID.

  Args:
      computerId: ID of the computer to remove.
      token: OAuth2 bearer token (injected by Depends).

  Returns:
      Success or failure API response.
  """
  force_authentication(token, "admin")
  return functionality.remove_computer(computerId)

@router.get("/container")
async def get_container(containerId : int, token: str = Depends(oauth2_scheme)):
  """Retrieve details for a single container definition.

  Args:
      containerId: ID of the container to retrieve.
      token: OAuth2 bearer token (injected by Depends).

  Returns:
      Container details wrapped in an API response.
  """
  force_authentication(token, "admin")
  return functionality.get_container(containerId)

@router.post("/save_container")
async def save_container(containerEdit : ContainerEdit, token: str = Depends(oauth2_scheme)):
  """Create or update a container definition.

  Args:
      containerEdit: Pydantic model with container fields to save.
      token: OAuth2 bearer token (injected by Depends).

  Returns:
      Success or failure API response.
  """
  force_authentication(token, "admin")
  return functionality.save_container(containerEdit)

@router.post("/remove_container")
async def remove_container(containerId : int, token: str = Depends(oauth2_scheme)):
  """Remove a container definition by ID.

  Args:
      containerId: ID of the container to remove.
      token: OAuth2 bearer token (injected by Depends).

  Returns:
      Success or failure API response.
  """
  force_authentication(token, "admin")
  return functionality.remove_container(containerId)

@router.post("/edit_reservation")
async def edit_reservation(reservationId : int, endDate : str, token: str = Depends(oauth2_scheme)):
  """Edit a reservation's end date.

  Args:
      reservationId: ID of the reservation to edit.
      endDate: New end date/time string for the reservation.
      token: OAuth2 bearer token (injected by Depends).

  Returns:
      Success or failure API response.
  """
  force_authentication(token, "admin")
  return functionality.edit_reservation(reservationId, endDate)

@router.get("/user")
async def get_user(userId: int, token: str = Depends(oauth2_scheme)):
    """Retrieve details for a single user.

    Args:
        userId: ID of the user to retrieve.
        token: OAuth2 bearer token (injected by Depends).

    Returns:
        User details wrapped in an API response.
    """
    force_authentication(token, "admin")
    return functionality.get_user(userId)

@router.post("/save_user")
async def save_user(userEdit: UserEdit, token: str = Depends(oauth2_scheme)):
    """Update a user's profile data.

    Args:
        userEdit: Pydantic model containing the user ID and fields to update.
        token: OAuth2 bearer token (injected by Depends).

    Returns:
        Success or failure API response.
    """
    force_authentication(token, "admin")
    return functionality.save_user(userEdit.userId, userEdit.data)

@router.get("/roles")
async def get_roles(token: str = Depends(oauth2_scheme)):
    """Retrieve all roles.

    Args:
        token: OAuth2 bearer token (injected by Depends).

    Returns:
        List of roles wrapped in an API response.
    """
    force_authentication(token, "admin")
    return functionality.get_all_roles()

@router.post("/save_role")
async def save_role(roleId: int = None, name: str = None, token: str = Depends(oauth2_scheme)):
    """Create a new role or rename an existing one.

    If ``roleId`` is provided the existing role is renamed; otherwise a new
    role is created with the given ``name``.

    Args:
        roleId: ID of the role to edit, or None to create a new role.
        name: Display name for the role.
        token: OAuth2 bearer token (injected by Depends).

    Returns:
        Success or failure API response.
    """
    force_authentication(token, "admin")
    if roleId:
        return functionality.edit_role(roleId, name)
    else:
        return functionality.add_role(name)

@router.post("/remove_role")
async def remove_role(roleId: int, token: str = Depends(oauth2_scheme)):
    """Remove a role by ID.

    Args:
        roleId: ID of the role to remove.
        token: OAuth2 bearer token (injected by Depends).

    Returns:
        Success or failure API response.
    """
    force_authentication(token, "admin")
    return functionality.remove_role(roleId)

@router.get("/role_mounts")
async def get_role_mounts(roleId: int, token: str = Depends(oauth2_scheme)):
    """Retrieve volume mount configurations for a role.

    Args:
        roleId: ID of the role whose mounts to retrieve.
        token: OAuth2 bearer token (injected by Depends).

    Returns:
        List of mount configurations wrapped in an API response.
    """
    force_authentication(token, "admin")
    return functionality.get_role_mounts(roleId)

@router.post("/save_role_mounts")
async def save_role_mounts(roleMountsEdit: RoleMountsEdit, token: str = Depends(oauth2_scheme)):
    """Save volume mount configurations for a role.

    Args:
        roleMountsEdit: Pydantic model with the role ID and mount list.
        token: OAuth2 bearer token (injected by Depends).

    Returns:
        Success or failure API response.
    """
    force_authentication(token, "admin")
    return functionality.save_role_mounts(roleMountsEdit.roleId, roleMountsEdit.mounts)

@router.get("/role_hardware_limits")
async def get_role_hardware_limits(roleId: int, token: str = Depends(oauth2_scheme)):
    """Retrieve hardware resource limits for a role.

    Args:
        roleId: ID of the role whose hardware limits to retrieve.
        token: OAuth2 bearer token (injected by Depends).

    Returns:
        Hardware limits wrapped in an API response.
    """
    force_authentication(token, "admin")
    return functionality.get_role_hardware_limits(roleId)

@router.post("/save_role_hardware_limits")
async def save_role_hardware_limits(roleHardwareLimitsEdit: RoleHardwareLimitsEdit, token: str = Depends(oauth2_scheme)):
    """Save hardware resource limits for a role.

    Args:
        roleHardwareLimitsEdit: Pydantic model with the role ID and limits.
        token: OAuth2 bearer token (injected by Depends).

    Returns:
        Success or failure API response.
    """
    force_authentication(token, "admin")
    return functionality.save_role_hardware_limits(roleHardwareLimitsEdit.roleId, roleHardwareLimitsEdit.hardwareLimits)

@router.get("/role_reservation_limits")
async def get_role_reservation_limits(roleId: int, token: str = Depends(oauth2_scheme)):
    """Retrieve reservation limits for a role.

    Args:
        roleId: ID of the role whose reservation limits to retrieve.
        token: OAuth2 bearer token (injected by Depends).

    Returns:
        Reservation limits wrapped in an API response.
    """
    force_authentication(token, "admin")
    return functionality.get_role_reservation_limits(roleId)

@router.post("/save_role_reservation_limits")
async def save_role_reservation_limits(roleReservationLimitsEdit: RoleReservationLimitsEdit, token: str = Depends(oauth2_scheme)):
    """Save reservation limits for a role.

    Args:
        roleReservationLimitsEdit: Pydantic model with the role ID and limits.
        token: OAuth2 bearer token (injected by Depends).

    Returns:
        Success or failure API response.
    """
    force_authentication(token, "admin")
    return functionality.save_role_reservation_limits(roleReservationLimitsEdit.roleId, roleReservationLimitsEdit.reservationLimits)

@router.get("/server/{computer_id}/monitoring")
async def get_server_monitoring(computer_id: int, token: str = Depends(oauth2_scheme)):
    """Retrieve monitoring data for a specific container server.

    Args:
        computer_id: ID of the computer to get monitoring data for.
        token: OAuth2 bearer token (injected by Depends).

    Returns:
        Server monitoring metrics wrapped in an API response.
    """
    force_authentication(token, "admin")
    return functionality.get_server_monitoring(computer_id)

@router.get("/servers")
async def get_servers_for_monitoring(token: str = Depends(oauth2_scheme)):
    """Retrieve all servers with their monitoring status overview.

    Args:
        token: OAuth2 bearer token (injected by Depends).

    Returns:
        List of servers with status info wrapped in an API response.
    """
    force_authentication(token, "admin")
    return functionality.get_servers_for_monitoring()

# General admin settings endpoints
class GeneralSettingsData(BaseModel):
    """Request body for saving a section of general settings."""

    section: str
    settings: Dict[str, Any]

class TestEmailData(BaseModel):
    """Request body for sending a test email."""

    email: str

@router.get("/general-settings")
async def get_general_settings(token: str = Depends(oauth2_scheme)):
    """Retrieve all database-backed general settings grouped by section.

    Args:
        token: OAuth2 bearer token (injected by Depends).

    Returns:
        Settings dictionary wrapped in an API response.
    """
    force_authentication(token, "admin")
    return functionality.get_general_settings()

@router.post("/general-settings")
async def save_general_settings(data: GeneralSettingsData, token: str = Depends(oauth2_scheme)):
    """Save a section of general settings to the database.

    Args:
        data: Pydantic model with the section name and key-value settings.
        token: OAuth2 bearer token (injected by Depends).

    Returns:
        Success or failure API response.
    """
    force_authentication(token, "admin")
    return functionality.save_general_settings(data.section, data.settings)

@router.post("/test-email")
async def send_test_email(data: TestEmailData, token: str = Depends(oauth2_scheme)):
    """Send a test email to verify SMTP configuration.

    Args:
        data: Pydantic model containing the recipient email address.
        token: OAuth2 bearer token (injected by Depends).

    Returns:
        Success or failure API response indicating email delivery status.
    """
    force_authentication(token, "admin")
    return functionality.send_test_email(data.email)

