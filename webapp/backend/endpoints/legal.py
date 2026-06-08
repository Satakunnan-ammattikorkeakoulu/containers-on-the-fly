"""Public legal document endpoints (no authentication required).

Provides privacy policy and terms of service content for display
on the login page and throughout the application.
"""

from fastapi import APIRouter
from endpoints.responses import legal as functionality

router = APIRouter(
    prefix="/api/legal",
    tags=["Legal"],
    responses={404: {"description": "Not found"}},
)

@router.get("/privacy-policy")
def get_privacy_policy():
    """Return privacy policy content (no authentication required).

    Returns:
        API response containing the privacy policy Markdown content,
        organization name, and contact email.
    """
    return functionality.get_privacy_policy()

@router.get("/terms-of-service")
def get_terms_of_service():
    """Return terms of service content (no authentication required).

    Returns:
        API response containing the terms of service Markdown content,
        organization name, and contact email.
    """
    return functionality.get_terms_of_service()
