"""Pydantic request models for admin API endpoints.

Defines the JSON body schemas used by admin-only POST endpoints for
editing containers, computers, users, and role configurations.
"""

from pydantic import BaseModel
from typing import Dict, Any, List
from endpoints.models.pagination import PaginationParams


class AdminUsersRequest(PaginationParams):
    """Request model for paginated, filtered admin user listing.

    Inherits page, itemsPerPage, sortBy, and filters from PaginationParams.
    Supported filter keys: role, email, userId.
    """

    pass


class AuditLogRequest(PaginationParams):
    """Request model for paginated, filtered audit log listing.

    Inherits page, itemsPerPage, sortBy, and filters from PaginationParams.
    Supported filter keys: action, resourceType, user, dateFrom, dateTo.
    """

    pass


class ContainerEdit(BaseModel):
    """Request model for editing a container's properties.

    Attributes:
        containerId: Database ID of the container to edit.
        data: Dictionary of field names and their new values.
    """

    containerId: int
    data: Dict[str, Any]


class ComputerEdit(BaseModel):
    """Request model for editing a computer's properties.

    Attributes:
        computerId: Database ID of the computer to edit.
        data: Dictionary of field names and their new values.
    """

    computerId: int
    data: Dict[str, Any]


class UserEdit(BaseModel):
    """Request model for editing a user's properties.

    Attributes:
        userId: Database ID of the user to edit.
        data: Dictionary of field names and their new values.
    """

    userId: int
    data: Dict[str, Any]


class RoleMountsEdit(BaseModel):
    """Request model for updating the volume mounts assigned to a role.

    Attributes:
        roleId: Database ID of the role whose mounts are being edited.
        mounts: List of mount configuration dictionaries, each containing
            keys such as hostPath, containerPath, readOnly, and computerId.
    """

    roleId: int
    mounts: List[Dict[str, Any]]


class RoleHardwareLimitsEdit(BaseModel):
    """Request model for updating the hardware limits assigned to a role.

    Attributes:
        roleId: Database ID of the role whose hardware limits are being edited.
        hardwareLimits: List of hardware limit dictionaries, each containing
            keys such as hardwareSpecId and maxAmount.
    """

    roleId: int
    hardwareLimits: List[Dict[str, Any]]


class RoleReservationLimitsEdit(BaseModel):
    """Request model for updating the reservation limits assigned to a role.

    Attributes:
        roleId: Database ID of the role whose reservation limits are being edited.
        reservationLimits: Dictionary of reservation limit fields and their values,
            such as maximum concurrent reservations or maximum duration.
    """

    roleId: int
    reservationLimits: Dict[str, Any]