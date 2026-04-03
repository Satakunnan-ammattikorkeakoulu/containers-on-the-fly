"""Integration tests for helpers/tables/reservation.py CRUD operations."""

from datetime import datetime
import database as db
from sqlalchemy import select
from helpers.tables.reservation import (
    get_reservations, get_reservation, add_reservation,
    remove_reservation, edit_reservation,
)


def _seed_reservation():
    """Create a minimal user, computer, container, and reservation. Return reservation ID."""
    from helpers.tables.user import add_user

    add_user("resuser@test.com", "pass")
    with db.Session() as s:
        user = s.execute(select(db.User).where(db.User.email == "resuser@test.com")).scalar_one()
        user_id = user.userId

        comp = db.Computer(name="res-server", public=True, ip="10.0.0.2")
        s.add(comp)
        s.flush()

        cont = db.Container(name="res-cont", public=True, description="desc", imageName="img")
        s.add(cont)
        s.flush()

        start = datetime(2026, 1, 1, 10, 0, 0)
        end = datetime(2026, 1, 1, 12, 0, 0)
        reservation = db.Reservation(
            startDate=start, endDate=end,
            userId=user_id, computerId=comp.computerId,
            reservedContainerId=cont.containerId, status="reserved",
        )
        s.add(reservation)
        s.commit()
        return reservation.reservationId, user_id, comp.computerId, cont.containerId


class TestGetReservations:

    def test_returns_all(self):
        _seed_reservation()
        result = get_reservations()
        assert isinstance(result, list)
        assert len(result) >= 1

    def test_filter_by_status(self):
        _seed_reservation()
        result = get_reservations(filter="reserved")
        assert result is not None
        assert len(result) >= 1
        assert all(r.status == "reserved" for r in result)

    def test_filter_by_date(self):
        _seed_reservation()
        result = get_reservations(filter="2026-01-01 10:00:00")
        assert result is not None
        assert len(result) >= 1

    def test_filter_no_match(self):
        result = get_reservations(filter="nonexistent_status")
        assert result is None or result == []

    def test_no_filter_returns_all(self):
        result = get_reservations()
        assert isinstance(result, list)


class TestGetReservation:

    def test_by_id(self):
        res_id, _, _, _ = _seed_reservation()
        result = get_reservation(filter=res_id)
        assert result is not None
        assert len(result) == 1
        assert result[0].reservationId == res_id

    def test_not_found(self):
        result = get_reservation(filter=99999)
        assert result is None


class TestAddReservation:

    def test_creates_reservation(self):
        from helpers.tables.user import add_user

        add_user("addres@test.com", "pass")
        with db.Session() as s:
            user = s.execute(select(db.User).where(db.User.email == "addres@test.com")).scalar_one()
            user_id = user.userId

            comp = db.Computer(name="add-server", public=True, ip="10.0.0.3")
            s.add(comp)
            s.flush()

            cont = db.Container(name="add-cont", public=True, description="desc", imageName="img")
            s.add(cont)
            s.flush()
            comp_id = comp.computerId
            cont_id = cont.containerId
            s.commit()

        start = datetime(2026, 6, 1, 8, 0, 0)
        end = datetime(2026, 6, 1, 10, 0, 0)
        add_reservation(start, end, user_id, comp_id, cont_id)

        result = get_reservations(filter="reserved")
        assert any(r.startDate == start for r in result)


class TestRemoveReservation:

    def test_removes_reservation(self):
        res_id, _, _, _ = _seed_reservation()
        remove_reservation(res_id)
        result = get_reservation(filter=res_id)
        assert result is None


class TestEditReservation:

    def test_edit_status(self):
        res_id, _, _, _ = _seed_reservation()
        edit_reservation(res_id, new_status="started")
        result = get_reservation(filter=res_id)
        assert result[0].status == "started"

    def test_edit_dates(self):
        res_id, _, _, _ = _seed_reservation()
        new_start = datetime(2026, 2, 1, 10, 0, 0)
        new_end = datetime(2026, 2, 1, 14, 0, 0)
        edit_reservation(res_id, new_startDate=new_start, new_endDate=new_end)
        result = get_reservation(filter=res_id)
        assert result[0].startDate == new_start
        assert result[0].endDate == new_end
