"""Pydantic request models for reservation API endpoints.

Defines the JSON body schemas used by reservation-related POST endpoints.
"""

from pydantic import BaseModel
from typing import Dict, Any


class ReservationFilters(BaseModel):
    """Request model for filtering reservations in list queries.

    Attributes:
        filters: Dictionary of filter criteria. Supported keys depend on the
            endpoint but may include status, computerId, userId, and date ranges.
    """

    filters: Dict[str, Any]