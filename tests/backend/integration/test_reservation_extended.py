"""Integration tests for reservation endpoints: extend, description, activity."""

from datetime import datetime, timezone, timedelta

import database as db
from sqlalchemy import select
from helpers.tables.audit_log import log_action
from helpers.request_context import set_client_ip


def _create_reservation_in_db(status="reserved", hours_offset=0, duration_hours=4, user_email="user@foo.com"):
    """Create a reservation directly in the DB. Returns the reservation ID."""
    now = datetime.now(timezone.utc) + timedelta(hours=hours_offset)
    with db.Session() as session:
        computer = session.execute(
            select(db.Computer).where(db.Computer.name == "server1")
        ).scalar_one()
        user = session.execute(
            select(db.User).where(db.User.email == user_email)
        ).scalar_one()
        container = session.execute(
            select(db.Container).where(db.Container.imageName == "ubuntu-base")
        ).scalar_one()

        reserved_container = db.ReservedContainer(containerId=container.containerId)
        session.add(reserved_container)
        session.flush()

        reservation = db.Reservation(
            userId=user.userId,
            computerId=computer.computerId,
            reservedContainerId=reserved_container.reservedContainerId,
            startDate=now,
            endDate=now + timedelta(hours=duration_hours),
            status=status,
        )
        session.add(reservation)
        session.flush()
        res_id = reservation.reservationId
        session.commit()
        return res_id


class TestUpdateReservationDescription:

    def test_updates_description(self, test_client, user_token, seed_test_data):
        res_id = _create_reservation_in_db()
        resp = test_client.post(
            f"/api/reservation/update_reservation_description?reservationId={res_id}&description=My%20test",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] is True

    def test_admin_can_update_any_description(self, test_client, admin_token, seed_test_data):
        res_id = _create_reservation_in_db(user_email="user@foo.com")
        # Admins can edit any reservation's description
        resp = test_client.post(
            f"/api/reservation/update_reservation_description?reservationId={res_id}&description=AdminEdit",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] is True

    def test_rejects_long_description(self, test_client, user_token, seed_test_data):
        res_id = _create_reservation_in_db()
        long_desc = "A" * 51
        resp = test_client.post(
            f"/api/reservation/update_reservation_description?reservationId={res_id}&description={long_desc}",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] is False


class TestGetOwnActivity:

    def test_returns_activity(self, test_client, user_token, seed_test_data):
        res_id = _create_reservation_in_db()
        set_client_ip("127.0.0.1")
        with db.Session() as s:
            user = s.execute(select(db.User).where(db.User.email == "user@foo.com")).scalar_one()
            user_id = user.userId
        log_action(user_id, "RESERVATION_CREATE", "reservation", res_id)

        resp = test_client.post(
            "/api/reservation/get_own_activity",
            json={"page": 1, "itemsPerPage": 10, "sortBy": [], "filters": {}},
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] is True
        assert "logs" in data["data"]
        assert "totalItems" in data["data"]


class TestMarkActivitySeen:

    def test_marks_and_returns(self, test_client, user_token, seed_test_data):
        resp = test_client.post(
            "/api/reservation/mark_activity_seen",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] is True
        assert "previousLastSeenAt" in data["data"]
