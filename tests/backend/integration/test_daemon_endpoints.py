"""Integration tests for /api/daemon endpoints."""

import pytest
from datetime import datetime, timezone, timedelta

from sqlalchemy import select
import database as db


# Daemon auth headers for test requests
DAEMON_HEADERS = {
    "X-Daemon-Api-Key": "test-daemon-api-key",
    "X-Daemon-Server-Name": "server1",
}


class TestDaemonAuthGuard:

    def test_missing_api_key_rejected(self, test_client):
        resp = test_client.get("/api/daemon/tasks")
        assert resp.status_code == 422  # missing required header

    def test_wrong_api_key_rejected(self, test_client):
        resp = test_client.get(
            "/api/daemon/tasks",
            headers={
                "X-Daemon-Api-Key": "wrong-key",
                "X-Daemon-Server-Name": "server1",
            },
        )
        assert resp.status_code == 401

    def test_missing_server_name_rejected(self, test_client):
        resp = test_client.get(
            "/api/daemon/tasks",
            headers={"X-Daemon-Api-Key": "test-daemon-api-key"},
        )
        assert resp.status_code == 422  # missing required header

    def test_unknown_server_name_rejected(self, test_client):
        resp = test_client.get(
            "/api/daemon/tasks",
            headers={
                "X-Daemon-Api-Key": "test-daemon-api-key",
                "X-Daemon-Server-Name": "nonexistent-server",
            },
        )
        assert resp.status_code == 401


class TestGetTasks:

    def test_returns_task_structure(self, test_client):
        resp = test_client.get("/api/daemon/tasks", headers=DAEMON_HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] is True
        assert "data" in data
        task_data = data["data"]
        assert "reservationsToStart" in task_data
        assert "reservationsToStop" in task_data


class TestOrphanCheck:

    def test_returns_container_names(self, test_client):
        resp = test_client.get("/api/daemon/orphan-check", headers=DAEMON_HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] is True
        assert "runningContainerNames" in data["data"]
        assert isinstance(data["data"]["runningContainerNames"], list)


class TestGetComputerId:

    def test_resolves_server_name(self, test_client):
        resp = test_client.get(
            "/api/daemon/computer-id/server1", headers=DAEMON_HEADERS
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] is True
        assert "computerId" in data["data"]
        assert isinstance(data["data"]["computerId"], int)

    def test_unknown_server_name(self, test_client):
        resp = test_client.get(
            "/api/daemon/computer-id/nonexistent", headers=DAEMON_HEADERS
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] is False


class TestResetStaleBuilds:

    def test_resets_stale_builds(self, test_client):
        resp = test_client.post("/api/daemon/reset-stale-builds", headers=DAEMON_HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] is True


class TestSubmitMonitoring:

    def test_accepts_monitoring_data(self, test_client):
        monitoring_data = {
            "cpuUsagePercent": 45.2,
            "cpuCores": 8,
            "memoryTotalBytes": 16000000000,
            "memoryUsedBytes": 8000000000,
            "memoryUsagePercent": 50.0,
            "diskTotalBytes": 500000000000,
            "diskUsedBytes": 250000000000,
            "diskFreeBytes": 250000000000,
            "diskUsagePercent": 50.0,
            "dockerContainersRunning": 2,
            "dockerContainersTotal": 5,
            "loadAvg1Min": 1.5,
            "loadAvg5Min": 1.2,
            "loadAvg15Min": 0.9,
            "systemUptimeSeconds": 86400,
        }
        resp = test_client.post(
            "/api/daemon/monitoring",
            json=monitoring_data,
            headers=DAEMON_HEADERS,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] is True


class TestReservationLifecycle:

    def _create_reservation(self):
        """Create a reservation directly in the DB for lifecycle testing."""
        now = datetime.now(timezone.utc)
        with db.Session() as session:
            computer = session.execute(
                select(db.Computer).where(db.Computer.name == "server1")
            ).scalar_one()
            user = session.execute(
                select(db.User).where(db.User.email == "user@foo.com")
            ).scalar_one()
            container = session.execute(
                select(db.Container).where(db.Container.imageName == "ubuntu-base")
            ).scalar_one()
            # Create ReservedContainer first (FK target for Reservation)
            reserved_container = db.ReservedContainer(
                containerId=container.containerId,
            )
            session.add(reserved_container)
            session.flush()
            reservation = db.Reservation(
                userId=user.userId,
                computerId=computer.computerId,
                reservedContainerId=reserved_container.reservedContainerId,
                startDate=now,
                endDate=now + timedelta(hours=4),
                status="reserved",
            )
            session.add(reservation)
            session.flush()
            res_id = reservation.reservationId
            session.commit()
            return res_id

    def test_report_stopped(self, test_client):
        res_id = self._create_reservation()
        # First change status to "started" so stop makes sense
        with db.Session() as session:
            res = session.execute(
                select(db.Reservation).where(db.Reservation.reservationId == res_id)
            ).scalar_one()
            res.status = "started"
            session.commit()

        resp = test_client.post(
            f"/api/daemon/reservation/{res_id}/stopped",
            headers=DAEMON_HEADERS,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] is True

    def test_report_stopped_nonexistent_reservation(self, test_client):
        resp = test_client.post(
            "/api/daemon/reservation/99999/stopped",
            headers=DAEMON_HEADERS,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] is False

    def test_report_start_failed(self, test_client):
        res_id = self._create_reservation()
        resp = test_client.post(
            f"/api/daemon/reservation/{res_id}/start-failed",
            json={"errorMessage": "GPU not available"},
            headers=DAEMON_HEADERS,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] is True

        # Verify status changed to error
        with db.Session() as session:
            res = session.execute(
                select(db.Reservation).where(db.Reservation.reservationId == res_id)
            ).scalar_one()
            assert res.status == "error"
