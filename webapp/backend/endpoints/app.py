"""Public application endpoints that do not require authentication.

Provides configuration data needed by the frontend before user login.
"""

from fastapi import APIRouter
from endpoints.responses import app as functionality

router = APIRouter(
    prefix="/api/app",
    tags=["App"],
    responses={404: {"description": "Not found"}},
)

@router.get("/config")
def get_public_config():
    """Return public app configuration (no authentication required).

    Provides configuration data needed by the frontend before users log in,
    including app info, reservation limits, and instruction messages.

    Returns:
        API response containing the public configuration dictionary.
    """
    return functionality.get_public_config() 