from fastapi import APIRouter
from endpoints.responses import app as functionality

router = APIRouter(
    prefix="/api/app",
    tags=["App"],
    responses={404: {"description": "Not found"}},
)

@router.get("/config")
async def getPublicConfig():
    """
    Get public app configuration (no authentication required)
    
    This endpoint provides public configuration data that's needed
    by the frontend before users log in, including app info,
    reservation limits, and instruction messages.
    """
    return functionality.getPublicConfig() 