"""Integration tests for /api/reservation endpoints."""

import json
from datetime import datetime, timezone, timedelta


def _future_date(hours=1):
    """Return an ISO datetime string hours from now."""
    return (datetime.now(timezone.utc) + timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%S")


class TestGetAvailableHardware:

    def test_returns_computers(self, test_client, user_token):
        resp = test_client.get(
            f"/api/reservation/get_available_hardware?date={_future_date()}&duration=2",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] is True
        assert "computers" in data["data"]
        assert len(data["data"]["computers"]) >= 1

    def test_unauthenticated(self, test_client):
        resp = test_client.get(
            f"/api/reservation/get_available_hardware?date={_future_date()}&duration=2",
        )
        assert resp.status_code in (401, 422)

    def test_hardware_specs_in_response(self, test_client, user_token):
        resp = test_client.get(
            f"/api/reservation/get_available_hardware?date={_future_date()}&duration=2",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        computers = resp.json()["data"]["computers"]
        assert len(computers) > 0
        computer = computers[0]
        assert "hardwareSpecs" in computer


class TestGetCurrentReservations:

    def test_returns_list(self, test_client, user_token):
        resp = test_client.get(
            "/api/reservation/get_current_reservations",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] is True


class TestGetOwnReservations:

    def test_returns_own_reservations(self, test_client, user_token):
        resp = test_client.post(
            "/api/reservation/get_own_reservations",
            json={"page": 1, "itemsPerPage": 10, "sortBy": [], "filters": {"status": ""}},
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] is True
        assert "reservations" in data["data"]
        assert "totalItems" in data["data"]
        assert "activeReservationCount" in data["data"]


class TestCreateReservation:

    def _get_test_ids(self, test_client, token):
        """Get computerId, containerId, and hardware specs for test reservation."""
        resp = test_client.get(
            f"/api/reservation/get_available_hardware?date={_future_date()}&duration=2",
            headers={"Authorization": f"Bearer {token}"},
        )
        computers = resp.json()["data"]["computers"]
        computer = computers[0]
        computer_id = computer["computerId"]

        # Get container
        resp = test_client.get(
            "/api/admin/containers",
            headers={"Authorization": f"Bearer {token}"},
        )
        container_id = resp.json()["data"]["containers"][0]["containerId"]

        # Build hardware specs from available specs
        hw_specs = {}
        for spec in computer["hardwareSpecs"]:
            if spec["type"] in ("cpus", "ram"):
                hw_specs[str(spec["hardwareSpecId"])] = spec["minimumAmount"]

        return computer_id, container_id, hw_specs

    def test_create_reservation_unauthenticated(self, test_client):
        resp = test_client.post(
            "/api/reservation/create_reservation"
            "?date=2030-01-01T00:00:00&duration=2&computerId=1&containerId=1"
            "&hardwareSpecs={}&adminReserveUserEmail=",
        )
        assert resp.status_code in (401, 422)

    def test_description_too_long(self, test_client, admin_token):
        computer_id, container_id, hw_specs = self._get_test_ids(test_client, admin_token)
        resp = test_client.post(
            "/api/reservation/create_reservation"
            f"?date={_future_date()}&duration=2"
            f"&computerId={computer_id}&containerId={container_id}"
            f"&hardwareSpecs={json.dumps(hw_specs)}"
            f"&adminReserveUserEmail="
            f"&description={'x' * 51}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] is False
        assert "Description too long" in resp.json()["message"]

    def test_shm_size_out_of_range(self, test_client, admin_token):
        computer_id, container_id, hw_specs = self._get_test_ids(test_client, admin_token)
        resp = test_client.post(
            "/api/reservation/create_reservation"
            f"?date={_future_date()}&duration=2"
            f"&computerId={computer_id}&containerId={container_id}"
            f"&hardwareSpecs={json.dumps(hw_specs)}"
            f"&adminReserveUserEmail="
            f"&shmSizePercent=95",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] is False
        assert "SHM" in resp.json()["message"]


class TestGetCalendarReservations:

    def test_returns_list(self, test_client, user_token):
        now = datetime.now(timezone.utc)
        start = now.strftime("%Y-%m-%dT%H:%M:%S")
        end = (now + timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%S")
        resp = test_client.get(
            f"/api/reservation/get_all_reservations_for_calendar?startDate={start}&endDate={end}",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] is True
