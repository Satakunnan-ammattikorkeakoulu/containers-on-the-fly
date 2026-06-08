"""HTTP client for daemon-to-backend API communication.

Provides a typed interface for all daemon REST API calls. Handles
authentication via X-Daemon-Api-Key and X-Daemon-Server-Name headers,
and includes retry logic with exponential backoff for transient failures.
"""

import time
import requests
from helpers.logger import log


class DaemonApiClient:
    """HTTP client for communicating with the backend API.

    Args:
        web_host: Main server web host (domain or IP).
        web_https: Whether HTTPS is enabled.
        api_key: Shared daemon API key.
        server_name: This daemon's server name (matches Computer.name in DB).
    """

    def __init__(self, web_host: str, web_https: bool, api_key: str, server_name: str):
        scheme = "https" if web_https else "http"
        self.base = f"{scheme}://{web_host}/api/daemon"
        self.server_name = server_name
        self.session = requests.Session()
        self.session.headers["X-Daemon-Api-Key"] = api_key
        self.session.headers["X-Daemon-Server-Name"] = server_name

    def _request(self, method: str, path: str, json=None, retries=3, timeout=30, retry_delay=None):
        """Make an HTTP request with retry logic.

        Args:
            method: HTTP method (GET, POST).
            path: URL path relative to the daemon API base.
            json: Request body as dict (for POST).
            retries: Number of retry attempts on failure.
            timeout: Request timeout in seconds.
            retry_delay: Fixed delay in seconds between retries. If None,
                uses exponential backoff (2^attempt seconds).

        Returns:
            Parsed JSON response dict, or None on failure.
        """
        url = f"{self.base}{path}"
        for attempt in range(retries):
            try:
                resp = self.session.request(method, url, json=json, timeout=timeout)
                resp.raise_for_status()
                return resp.json()
            except requests.exceptions.ConnectionError as e:
                if attempt < retries - 1:
                    wait = retry_delay if retry_delay is not None else 2 ** attempt
                    log.warning(f"Backend unreachable ({e}), retrying in {wait}s ({attempt + 1}/{retries})...")
                    time.sleep(wait)
                else:
                    log.error(f"Backend unreachable after {retries} attempts: {e}")
                    return None
            except requests.exceptions.HTTPError as e:
                if resp.status_code >= 500 and attempt < retries - 1:
                    wait = retry_delay if retry_delay is not None else 2 ** attempt
                    log.warning(f"Server error {resp.status_code} for {method} {path}, retrying in {wait}s ({attempt + 1}/{retries})...")
                    time.sleep(wait)
                else:
                    log.error(f"API error {resp.status_code} for {method} {path}: {resp.text}")
                    return None
            except Exception as e:
                log.error(f"Unexpected error calling {method} {path}: {e}")
                return None

    # ------------------------------------------------------------------
    # Polling
    # ------------------------------------------------------------------

    def get_tasks(self) -> dict:
        """Fetch all actionable work for one polling cycle.

        Returns:
            Task bundle dict, or None on failure.
        """
        resp = self._request("GET", "/tasks")
        if resp and resp.get("status"):
            return resp.get("data", {})
        return None

    def get_orphan_check(self) -> list:
        """Fetch running reservation container names for orphan detection.

        Returns:
            List of container docker names, or empty list on failure.
        """
        resp = self._request("GET", "/orphan-check")
        if resp and resp.get("status"):
            return resp.get("data", {}).get("runningContainerNames", [])
        return []

    def get_computer_id(self, server_name: str) -> int:
        """Resolve a server name to its database computer ID.

        Args:
            server_name: Name of the computer.

        Returns:
            Computer ID, or None if not found.
        """
        resp = self._request("GET", f"/computer-id/{server_name}", retries=5, retry_delay=5)
        if resp and resp.get("status"):
            return resp.get("data", {}).get("computerId")
        return None

    # ------------------------------------------------------------------
    # Reservation lifecycle
    # ------------------------------------------------------------------

    def report_started(self, reservation_id: int, data: dict) -> bool:
        """Report that a container started successfully.

        Args:
            reservation_id: Database ID of the reservation.
            data: Dict with containerDockerName, sshPassword,
                containerDockerId, ports, nonCriticalErrors.

        Returns:
            True on success.
        """
        resp = self._request("POST", f"/reservation/{reservation_id}/started", json=data,
                             retries=5, retry_delay=5)
        return resp is not None and resp.get("status", False)

    def report_start_failed(self, reservation_id: int, error_message: str) -> bool:
        """Report that a container failed to start.

        Args:
            reservation_id: Database ID of the reservation.
            error_message: Error description.

        Returns:
            True on success.
        """
        resp = self._request("POST", f"/reservation/{reservation_id}/start-failed",
                             json={"errorMessage": error_message},
                             retries=5, retry_delay=5)
        return resp is not None and resp.get("status", False)

    def report_stopped(self, reservation_id: int) -> bool:
        """Report that a container was stopped.

        Args:
            reservation_id: Database ID of the reservation.

        Returns:
            True on success.
        """
        resp = self._request("POST", f"/reservation/{reservation_id}/stopped",
                             retries=5, retry_delay=5)
        return resp is not None and resp.get("status", False)

    def report_paused(self, reservation_id: int, image_name: str, computer_name: str) -> bool:
        """Report that a low-priority container was paused.

        Args:
            reservation_id: Database ID of the reservation.
            image_name: Docker image name.
            computer_name: Computer name.

        Returns:
            True on success.
        """
        resp = self._request("POST", f"/reservation/{reservation_id}/paused",
                             json={"imageName": image_name, "computerName": computer_name},
                             retries=5, retry_delay=5)
        return resp is not None and resp.get("status", False)

    def report_resumed(self, reservation_id: int) -> bool:
        """Report that a paused container is ready to resume.

        Args:
            reservation_id: Database ID of the reservation.

        Returns:
            True on success.
        """
        resp = self._request("POST", f"/reservation/{reservation_id}/resumed",
                             retries=5, retry_delay=5)
        return resp is not None and resp.get("status", False)

    def report_restarted(self, reservation_id: int, success: bool, error_message: str = "") -> bool:
        """Report the result of a container restart attempt.

        Args:
            reservation_id: Database ID of the reservation.
            success: Whether the restart succeeded.
            error_message: Error description if failed.

        Returns:
            True on success.
        """
        resp = self._request("POST", f"/reservation/{reservation_id}/restarted",
                             json={"success": success, "errorMessage": error_message},
                             retries=5, retry_delay=5)
        return resp is not None and resp.get("status", False)

    # ------------------------------------------------------------------
    # Container images
    # ------------------------------------------------------------------

    def report_build_progress(self, container_id: int, build_log: str) -> bool:
        """Update build log during an image build.

        Args:
            container_id: Database ID of the container.
            build_log: Current accumulated build log.

        Returns:
            True on success.
        """
        resp = self._request("POST", f"/container/{container_id}/build-progress",
                             json={"buildLog": build_log, "buildStatus": "building"},
                             timeout=10)
        return resp is not None and resp.get("status", False)

    def report_build_complete(self, container_id: int, data: dict) -> bool:
        """Report that an image build finished.

        Args:
            container_id: Database ID of the container.
            data: Dict with buildStatus, buildLog, imageSize, lastBuiltAt.

        Returns:
            True on success.
        """
        resp = self._request("POST", f"/container/{container_id}/build-complete", json=data,
                             retries=5, retry_delay=5)
        return resp is not None and resp.get("status", False)

    def report_image_removed(self, container_id: int, build_status: str) -> bool:
        """Report that an image was removed from Docker.

        Args:
            container_id: Database ID of the container.
            build_status: Final build status (e.g. "removed").

        Returns:
            True on success.
        """
        resp = self._request("POST", f"/container/{container_id}/image-removed",
                             json={"buildStatus": build_status})
        return resp is not None and resp.get("status", False)

    def update_image_size(self, container_id: int, image_size: int) -> bool:
        """Update the stored image size for a container.

        Args:
            container_id: Database ID of the container.
            image_size: Image size in bytes.

        Returns:
            True on success.
        """
        resp = self._request("POST", f"/container/{container_id}/image-size",
                             json={"imageSize": image_size})
        return resp is not None and resp.get("status", False)

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def reset_stale_builds(self) -> bool:
        """Reset containers stuck in 'building' status.

        Returns:
            True on success.
        """
        resp = self._request("POST", "/reset-stale-builds")
        return resp is not None and resp.get("status", False)

    def update_image_sizes_batch(self, images: list) -> bool:
        """Batch update image sizes on startup.

        Args:
            images: List of dicts with imageName and imageSize.

        Returns:
            True on success.
        """
        resp = self._request("POST", "/update-image-sizes", json={"images": images})
        return resp is not None and resp.get("status", False)

    def submit_monitoring(self, data: dict) -> bool:
        """Submit server monitoring metrics and logs.

        Args:
            data: Dict with system metrics and optional logs.

        Returns:
            True on success.
        """
        resp = self._request("POST", "/monitoring", json=data, timeout=15)
        return resp is not None and resp.get("status", False)
