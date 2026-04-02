"""Daemon API endpoints for container server communication.

All endpoints in this module require daemon API key authentication via
X-Daemon-Api-Key and X-Daemon-Server-Name headers. These endpoints are
used exclusively by the container server daemon, not by the frontend.
"""

from fastapi import APIRouter, Header
from helpers.server import force_daemon_authentication, api_response
from endpoints.responses import daemon as functionality
from endpoints.models.daemon import (
    ReservationStartedRequest, ReservationStartFailedRequest,
    ReservationRestartedRequest, ReservationPausedRequest,
    BuildProgressRequest, BuildCompleteRequest,
    ImageRemovedRequest, ImageSizeRequest, ImageSizeBatchRequest,
    MonitoringRequest,
)

router = APIRouter(
    prefix="/api/daemon",
    tags=["Daemon"],
    responses={404: {"description": "Not found"}},
)


def _auth(api_key: str, server_name: str) -> int:
    """Authenticate daemon and return computer ID.

    Args:
        api_key: Value of X-Daemon-Api-Key header.
        server_name: Value of X-Daemon-Server-Name header.

    Returns:
        The computerId for the authenticated server.
    """
    return force_daemon_authentication(api_key, server_name)


# ---------------------------------------------------------------------------
# Polling
# ---------------------------------------------------------------------------

@router.get("/tasks")
async def get_tasks(
    x_daemon_api_key: str = Header(...),
    x_daemon_server_name: str = Header(...),
):
    """Return all actionable work for a single daemon polling cycle.

    Called every 10 seconds by the daemon. Returns reservations to
    start, stop, restart, pause, resume, plus containers to build/remove
    and computer hardware capacity.
    """
    computer_id = _auth(x_daemon_api_key, x_daemon_server_name)
    return functionality.get_tasks(computer_id)


@router.get("/orphan-check")
async def get_orphan_check(
    x_daemon_api_key: str = Header(...),
    x_daemon_server_name: str = Header(...),
):
    """Return running reservation docker names for orphan detection.

    Called every 60 seconds by the daemon.
    """
    computer_id = _auth(x_daemon_api_key, x_daemon_server_name)
    return functionality.get_orphan_check_data(computer_id)


@router.get("/computer-id/{server_name}")
async def get_computer_id(
    server_name: str,
    x_daemon_api_key: str = Header(...),
    x_daemon_server_name: str = Header(...),
):
    """Resolve a server name to its database computer ID.

    Called once at daemon startup.
    """
    _auth(x_daemon_api_key, x_daemon_server_name)
    return functionality.get_computer_id_by_name(server_name)


# ---------------------------------------------------------------------------
# Reservation lifecycle actions
# ---------------------------------------------------------------------------

@router.post("/reservation/{reservation_id}/started")
async def reservation_started(
    reservation_id: int,
    request: ReservationStartedRequest,
    x_daemon_api_key: str = Header(...),
    x_daemon_server_name: str = Header(...),
):
    """Report that a container started successfully."""
    computer_id = _auth(x_daemon_api_key, x_daemon_server_name)
    return functionality.report_started(reservation_id, request, computer_id)


@router.post("/reservation/{reservation_id}/start-failed")
async def reservation_start_failed(
    reservation_id: int,
    request: ReservationStartFailedRequest,
    x_daemon_api_key: str = Header(...),
    x_daemon_server_name: str = Header(...),
):
    """Report that a container failed to start."""
    computer_id = _auth(x_daemon_api_key, x_daemon_server_name)
    return functionality.report_start_failed(reservation_id, request, computer_id)


@router.post("/reservation/{reservation_id}/stopped")
async def reservation_stopped(
    reservation_id: int,
    x_daemon_api_key: str = Header(...),
    x_daemon_server_name: str = Header(...),
):
    """Report that a container was stopped."""
    computer_id = _auth(x_daemon_api_key, x_daemon_server_name)
    return functionality.report_stopped(reservation_id, computer_id)


@router.post("/reservation/{reservation_id}/paused")
async def reservation_paused(
    reservation_id: int,
    request: ReservationPausedRequest,
    x_daemon_api_key: str = Header(...),
    x_daemon_server_name: str = Header(...),
):
    """Report that a low-priority container was paused."""
    computer_id = _auth(x_daemon_api_key, x_daemon_server_name)
    return functionality.report_paused(reservation_id, request, computer_id)


@router.post("/reservation/{reservation_id}/resumed")
async def reservation_resumed(
    reservation_id: int,
    x_daemon_api_key: str = Header(...),
    x_daemon_server_name: str = Header(...),
):
    """Report that a paused container is ready to resume."""
    computer_id = _auth(x_daemon_api_key, x_daemon_server_name)
    return functionality.report_resumed(reservation_id, computer_id)


@router.post("/reservation/{reservation_id}/restarted")
async def reservation_restarted(
    reservation_id: int,
    request: ReservationRestartedRequest,
    x_daemon_api_key: str = Header(...),
    x_daemon_server_name: str = Header(...),
):
    """Report the result of a container restart attempt."""
    computer_id = _auth(x_daemon_api_key, x_daemon_server_name)
    return functionality.report_restarted(reservation_id, request, computer_id)


# ---------------------------------------------------------------------------
# Container image actions
# ---------------------------------------------------------------------------

@router.post("/container/{container_id}/build-progress")
async def container_build_progress(
    container_id: int,
    request: BuildProgressRequest,
    x_daemon_api_key: str = Header(...),
    x_daemon_server_name: str = Header(...),
):
    """Update build log during an image build."""
    computer_id = _auth(x_daemon_api_key, x_daemon_server_name)
    return functionality.report_build_progress(container_id, request, computer_id)


@router.post("/container/{container_id}/build-complete")
async def container_build_complete(
    container_id: int,
    request: BuildCompleteRequest,
    x_daemon_api_key: str = Header(...),
    x_daemon_server_name: str = Header(...),
):
    """Report that an image build finished."""
    computer_id = _auth(x_daemon_api_key, x_daemon_server_name)
    return functionality.report_build_complete(container_id, request, computer_id)


@router.post("/container/{container_id}/image-removed")
async def container_image_removed(
    container_id: int,
    request: ImageRemovedRequest,
    x_daemon_api_key: str = Header(...),
    x_daemon_server_name: str = Header(...),
):
    """Report that an image was removed from Docker."""
    computer_id = _auth(x_daemon_api_key, x_daemon_server_name)
    return functionality.report_image_removed(container_id, request, computer_id)


@router.post("/container/{container_id}/image-size")
async def container_image_size(
    container_id: int,
    request: ImageSizeRequest,
    x_daemon_api_key: str = Header(...),
    x_daemon_server_name: str = Header(...),
):
    """Update the stored image size for a container."""
    computer_id = _auth(x_daemon_api_key, x_daemon_server_name)
    return functionality.update_image_size(container_id, request, computer_id)


# ---------------------------------------------------------------------------
# Utility endpoints
# ---------------------------------------------------------------------------

@router.post("/reset-stale-builds")
async def reset_stale_builds(
    x_daemon_api_key: str = Header(...),
    x_daemon_server_name: str = Header(...),
):
    """Reset containers stuck in 'building' status back to 'pending'.

    Called once at daemon startup.
    """
    computer_id = _auth(x_daemon_api_key, x_daemon_server_name)
    return functionality.reset_stale_builds(computer_id)


@router.post("/update-image-sizes")
async def update_image_sizes(
    request: ImageSizeBatchRequest,
    x_daemon_api_key: str = Header(...),
    x_daemon_server_name: str = Header(...),
):
    """Batch update image sizes on daemon startup."""
    computer_id = _auth(x_daemon_api_key, x_daemon_server_name)
    return functionality.update_image_sizes_batch(request, computer_id)


@router.post("/monitoring")
async def submit_monitoring(
    request: MonitoringRequest,
    x_daemon_api_key: str = Header(...),
    x_daemon_server_name: str = Header(...),
):
    """Submit server monitoring metrics and logs."""
    computer_id = _auth(x_daemon_api_key, x_daemon_server_name)
    return functionality.submit_monitoring(request, computer_id)
