"""Pydantic request models for reservation API endpoints.

Defines the JSON body schemas used by reservation-related POST endpoints.
"""

from pydantic import BaseModel
from typing import Dict, Any
from endpoints.models.pagination import PaginationParams


class ReservationFilters(BaseModel):
    """Request model for filtering reservations in list queries.

    Attributes:
        filters: Dictionary of filter criteria. Supported keys depend on the
            endpoint but may include status, computerId, userId, and date ranges.
    """

    filters: Dict[str, Any]


class AdminReservationRequest(PaginationParams):
    """Request model for paginated, filtered admin reservation listing.

    Inherits page, itemsPerPage, sortBy, and filters from PaginationParams.
    Supported filter keys: status, reservationId.
    """

    pass


class UserReservationRequest(PaginationParams):
    """Request model for paginated, filtered user reservation listing.

    Inherits page, itemsPerPage, sortBy, and filters from PaginationParams.
    Supported filter keys: status.
    """

    pass


class UserActivityRequest(PaginationParams):
    """Request model for paginated user reservation activity listing.

    Inherits page, itemsPerPage, sortBy, and filters from PaginationParams.
    Returns audit log entries scoped to the authenticated user's own
    reservations. Supported filter keys: action, dateFrom, dateTo.
    """

    pass
