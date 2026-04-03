"""Admin API endpoints for managing containers, computers, users, roles, and settings.

All endpoints in this module require admin-level authentication. Delegates
business logic to ``endpoints.responses.admin``.
"""

from fastapi import APIRouter, Depends
from helpers.server import force_authentication
from fastapi.security import OAuth2PasswordBearer
from endpoints.responses import admin as functionality
from endpoints.models.admin import ContainerEdit, ComputerEdit, UserEdit, RoleMountsEdit, RoleHardwareLimitsEdit, RoleReservationLimitsEdit, AdminUsersRequest, AuditLogRequest, AnalyticsRequest
from endpoints.models.reservation import AdminReservationRequest
from pydantic import BaseModel, Field
from typing import Dict, Any

router = APIRouter(
    prefix="/api/admin",
    tags=["Admin"],
    responses={404: {"description": "Not found"}},
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="user/login")  # Make sure the tokenUrl is correct

@router.post("/reservations")
def get_reservations(request: AdminReservationRequest, token: str = Depends(oauth2_scheme)):
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
def get_users(request: AdminUsersRequest, token: str = Depends(oauth2_scheme)):
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
def get_hardware(token: str = Depends(oauth2_scheme)):
  """Retrieve all hardware specifications.

  Args:
      token: OAuth2 bearer token (injected by Depends).

  Returns:
      List of hardware specs wrapped in an API response.
  """
  force_authentication(token, "admin")
  return functionality.get_hardware()

@router.get("/containers")
def get_containers(token: str = Depends(oauth2_scheme)):
  """Retrieve all container definitions.

  Args:
      token: OAuth2 bearer token (injected by Depends).

  Returns:
      List of container definitions wrapped in an API response.
  """
  force_authentication(token, "admin")
  return functionality.get_containers()

@router.get("/computers")
def get_computers(token: str = Depends(oauth2_scheme)):
  """Retrieve all computer (server) records.

  Args:
      token: OAuth2 bearer token (injected by Depends).

  Returns:
      List of computers wrapped in an API response.
  """
  force_authentication(token, "admin")
  return functionality.get_computers()

@router.get("/computer")
def get_computer(computerId : int, token: str = Depends(oauth2_scheme)):
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
def save_computer(computerEdit : ComputerEdit, token: str = Depends(oauth2_scheme)):
  """Create or update a computer record.

  Args:
      computerEdit: Pydantic model with computer fields to save.
      token: OAuth2 bearer token (injected by Depends).

  Returns:
      Success or failure API response.
  """
  actor_user_id = force_authentication(token, "admin")
  return functionality.save_computer(computerEdit, actor_user_id)

@router.post("/remove_computer")
def remove_computer(computerId : int, token: str = Depends(oauth2_scheme)):
  """Remove a computer record by ID.

  Args:
      computerId: ID of the computer to remove.
      token: OAuth2 bearer token (injected by Depends).

  Returns:
      Success or failure API response.
  """
  actor_user_id = force_authentication(token, "admin")
  return functionality.remove_computer(computerId, actor_user_id)

@router.get("/container")
def get_container(containerId : int, token: str = Depends(oauth2_scheme)):
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
def save_container(containerEdit : ContainerEdit, token: str = Depends(oauth2_scheme)):
  """Create or update a container definition.

  Args:
      containerEdit: Pydantic model with container fields to save.
      token: OAuth2 bearer token (injected by Depends).

  Returns:
      Success or failure API response.
  """
  actor_user_id = force_authentication(token, "admin")
  return functionality.save_container(containerEdit, actor_user_id)

@router.get("/container_remove_info")
def get_container_remove_info(containerId: int, token: str = Depends(oauth2_scheme)):
  """Get information needed for the container removal confirmation dialog.

  Returns the number of active reservations using this container,
  whether the image is managed externally, and the image name.

  Args:
      containerId: ID of the container to check.
      token: OAuth2 bearer token (injected by Depends).

  Returns:
      API response with activeReservations count, managedExternally flag,
      and imageName.
  """
  force_authentication(token, "admin")
  return functionality.get_container_remove_info(containerId)

@router.post("/remove_container")
def remove_container(containerId : int, token: str = Depends(oauth2_scheme)):
  """Remove a container definition by ID.

  Args:
      containerId: ID of the container to remove.
      token: OAuth2 bearer token (injected by Depends).

  Returns:
      Success or failure API response.
  """
  actor_user_id = force_authentication(token, "admin")
  return functionality.remove_container(containerId, actor_user_id)

@router.get("/container_defaults")
def get_container_defaults(username: str = "user", token: str = Depends(oauth2_scheme)):
  """Get default values for a new container (Dockerfile body, CMD, runtime commands).

  Used by the frontend to pre-fill the container creation form and for
  the "Reset to Defaults" button. The username parameter controls which
  username is interpolated into the default Dockerfile body template.

  Args:
      username: Linux username to interpolate into defaults.
      token: OAuth2 bearer token (injected by Depends).

  Returns:
      API response with default Dockerfile body, CMD, password command,
      and SSH key deploy commands.
  """
  force_authentication(token, "admin")
  return functionality.get_container_defaults(username)

@router.post("/rebuild_container_image")
def rebuild_container_image(containerId: int, token: str = Depends(oauth2_scheme)):
  """Queue a container image rebuild.

  Sets the container's buildStatus to "pending" so the Docker utility
  daemon picks it up on its next polling cycle. Does not perform the
  build itself — the web server has no Docker access.

  Args:
      containerId: ID of the container whose image should be rebuilt.
      token: OAuth2 bearer token (injected by Depends).

  Returns:
      Success or failure API response.
  """
  actor_user_id = force_authentication(token, "admin")
  return functionality.rebuild_container_image(containerId, actor_user_id)

@router.get("/container_build_status")
def get_container_build_status(containerId: int, token: str = Depends(oauth2_scheme)):
  """Get the current build status and log for a container image.

  Used by the frontend to poll build progress while an image is being
  built by the Docker utility daemon.

  Args:
      containerId: ID of the container to check.
      token: OAuth2 bearer token (injected by Depends).

  Returns:
      API response with buildStatus and buildLog.
  """
  force_authentication(token, "admin")
  return functionality.get_container_build_status(containerId)

@router.post("/edit_reservation")
def edit_reservation(reservationId : int, endDate : str, token: str = Depends(oauth2_scheme)):
  """Edit a reservation's end date.

  Args:
      reservationId: ID of the reservation to edit.
      endDate: New end date/time string for the reservation.
      token: OAuth2 bearer token (injected by Depends).

  Returns:
      Success or failure API response.
  """
  actor_user_id = force_authentication(token, "admin")
  return functionality.edit_reservation(reservationId, endDate, actor_user_id)

@router.get("/user")
def get_user(userId: int, token: str = Depends(oauth2_scheme)):
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
def save_user(userEdit: UserEdit, token: str = Depends(oauth2_scheme)):
    """Update a user's profile data.

    Args:
        userEdit: Pydantic model containing the user ID and fields to update.
        token: OAuth2 bearer token (injected by Depends).

    Returns:
        Success or failure API response.
    """
    actor_user_id = force_authentication(token, "admin")
    return functionality.save_user(userEdit.userId, userEdit.data, actor_user_id)

@router.get("/user_anonymize_info")
def get_user_anonymize_info(userId: int, token: str = Depends(oauth2_scheme)):
    """Get information needed for the user anonymization confirmation dialog.

    Args:
        userId: ID of the user to check.
        token: OAuth2 bearer token (injected by Depends).

    Returns:
        API response with active reservation count, audit log entry count,
        and admin status.
    """
    force_authentication(token, "admin")
    return functionality.get_user_anonymize_info(userId)

@router.post("/anonymize_user")
def anonymize_user(userId: int, token: str = Depends(oauth2_scheme)):
    """Anonymize a user's personal data (GDPR soft-deletion).

    Args:
        userId: ID of the user to anonymize.
        token: OAuth2 bearer token (injected by Depends).

    Returns:
        Success or failure API response.
    """
    actor_user_id = force_authentication(token, "admin")
    return functionality.anonymize_user(userId, actor_user_id)

@router.get("/roles")
def get_roles(token: str = Depends(oauth2_scheme)):
    """Retrieve all roles.

    Args:
        token: OAuth2 bearer token (injected by Depends).

    Returns:
        List of roles wrapped in an API response.
    """
    force_authentication(token, "admin")
    return functionality.get_all_roles()

@router.post("/save_role")
def save_role(roleId: int = None, name: str = None, token: str = Depends(oauth2_scheme)):
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
    actor_user_id = force_authentication(token, "admin")
    if roleId:
        return functionality.edit_role(roleId, name, actor_user_id)
    else:
        return functionality.add_role(name, actor_user_id)

@router.post("/remove_role")
def remove_role(roleId: int, token: str = Depends(oauth2_scheme)):
    """Remove a role by ID.

    Args:
        roleId: ID of the role to remove.
        token: OAuth2 bearer token (injected by Depends).

    Returns:
        Success or failure API response.
    """
    actor_user_id = force_authentication(token, "admin")
    return functionality.remove_role(roleId, actor_user_id)

@router.get("/role_mounts")
def get_role_mounts(roleId: int, token: str = Depends(oauth2_scheme)):
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
def save_role_mounts(roleMountsEdit: RoleMountsEdit, token: str = Depends(oauth2_scheme)):
    """Save volume mount configurations for a role.

    Args:
        roleMountsEdit: Pydantic model with the role ID and mount list.
        token: OAuth2 bearer token (injected by Depends).

    Returns:
        Success or failure API response.
    """
    actor_user_id = force_authentication(token, "admin")
    return functionality.save_role_mounts(roleMountsEdit.roleId, roleMountsEdit.mounts, actor_user_id)

@router.get("/role_hardware_limits")
def get_role_hardware_limits(roleId: int, token: str = Depends(oauth2_scheme)):
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
def save_role_hardware_limits(roleHardwareLimitsEdit: RoleHardwareLimitsEdit, token: str = Depends(oauth2_scheme)):
    """Save hardware resource limits for a role.

    Args:
        roleHardwareLimitsEdit: Pydantic model with the role ID and limits.
        token: OAuth2 bearer token (injected by Depends).

    Returns:
        Success or failure API response.
    """
    actor_user_id = force_authentication(token, "admin")
    return functionality.save_role_hardware_limits(roleHardwareLimitsEdit.roleId, roleHardwareLimitsEdit.hardwareLimits, actor_user_id)

@router.get("/role_reservation_limits")
def get_role_reservation_limits(roleId: int, token: str = Depends(oauth2_scheme)):
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
def save_role_reservation_limits(roleReservationLimitsEdit: RoleReservationLimitsEdit, token: str = Depends(oauth2_scheme)):
    """Save reservation limits for a role.

    Args:
        roleReservationLimitsEdit: Pydantic model with the role ID and limits.
        token: OAuth2 bearer token (injected by Depends).

    Returns:
        Success or failure API response.
    """
    actor_user_id = force_authentication(token, "admin")
    return functionality.save_role_reservation_limits(roleReservationLimitsEdit.roleId, roleReservationLimitsEdit.reservationLimits, actor_user_id)

@router.get("/server/{computer_id}/monitoring")
def get_server_monitoring(computer_id: int, token: str = Depends(oauth2_scheme)):
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
def get_servers_for_monitoring(token: str = Depends(oauth2_scheme)):
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

class TestAdData(BaseModel):
    """Request body for testing AD/LDAP connection."""

    username: str = Field(max_length=256)
    password: str = Field(max_length=256)

@router.get("/general-settings")
def get_general_settings(token: str = Depends(oauth2_scheme)):
    """Retrieve all database-backed general settings grouped by section.

    Args:
        token: OAuth2 bearer token (injected by Depends).

    Returns:
        Settings dictionary wrapped in an API response.
    """
    force_authentication(token, "admin")
    return functionality.get_general_settings()

@router.post("/general-settings")
def save_general_settings(data: GeneralSettingsData, token: str = Depends(oauth2_scheme)):
    """Save a section of general settings to the database.

    Args:
        data: Pydantic model with the section name and key-value settings.
        token: OAuth2 bearer token (injected by Depends).

    Returns:
        Success or failure API response.
    """
    actor_user_id = force_authentication(token, "admin")
    return functionality.save_general_settings(data.section, data.settings, actor_user_id)

@router.post("/test-email")
def send_test_email(data: TestEmailData, token: str = Depends(oauth2_scheme)):
    """Send a test email to verify SMTP configuration.

    Args:
        data: Pydantic model containing the recipient email address.
        token: OAuth2 bearer token (injected by Depends).

    Returns:
        Success or failure API response indicating email delivery status.
    """
    force_authentication(token, "admin")
    return functionality.send_test_email(data.email)

@router.post("/test-ad")
def test_ad_connection(data: TestAdData, token: str = Depends(oauth2_scheme)):
    """Test AD/LDAP connection with provided credentials.

    Performs an LDAP bind and search using the provided credentials against
    the currently saved LDAP configuration. Returns all attributes from the
    LDAP server response. Does not create users or modify any state.

    Args:
        data: Pydantic model containing username and password.
        token: OAuth2 bearer token (injected by Depends).

    Returns:
        Success response with full LDAP attributes, or failure with error message.
    """
    force_authentication(token, "admin")
    return functionality.test_ad_connection(data.username, data.password)

@router.post("/audit-logs")
def get_audit_logs(request: AuditLogRequest, token: str = Depends(oauth2_scheme)):
    """Retrieve paginated audit log entries with optional filtering.

    Args:
        request: Pagination, sorting, and filter parameters.
        token: OAuth2 bearer token (injected by Depends).

    Returns:
        Paginated list of audit log entries with total count and retention setting.
    """
    force_authentication(token, "admin")
    return functionality.get_audit_logs(request)

@router.post("/analytics")
async def get_analytics(request: AnalyticsRequest, token: str = Depends(oauth2_scheme)):
    """Retrieve usage analytics data for the admin dashboard.

    Args:
        request: Time range parameters (days lookback).
        token: OAuth2 bearer token (injected by Depends).

    Returns:
        Aggregated analytics including activity trends, status breakdown,
        action counts, top users, and per-server reservation counts.
    """
    force_authentication(token, "admin")
    return functionality.get_analytics(request)

