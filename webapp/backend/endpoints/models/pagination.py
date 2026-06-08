"""Shared Pydantic models for server-side pagination, sorting, and filtering.

Used by admin and reservation endpoints to accept pagination parameters
from Vuetify 3's v-data-table-server component.
"""

from pydantic import BaseModel
from typing import Dict, Any, List


class SortItem(BaseModel):
    """A single sort directive from the frontend table.

    Attributes:
        key: Column key to sort by (validated against a whitelist per endpoint).
        order: Sort direction, either "asc" or "desc".
    """

    key: str
    order: str = "desc"


class PaginationParams(BaseModel):
    """Base pagination parameters matching Vuetify 3 v-data-table-server options.

    Attributes:
        page: 1-based page number.
        itemsPerPage: Number of items per page. Use -1 for all items.
        sortBy: List of sort directives.
        filters: Dictionary of filter key-value pairs (endpoint-specific).
    """

    page: int = 1
    itemsPerPage: int = 10
    sortBy: List[SortItem] = []
    filters: Dict[str, Any] = {}
