"""Integration tests for /api/reservation endpoints."""

import json
from datetime import datetime, timezone, timedelta
from urllib.parse import quote

import database as db
from sqlalchemy import select


def _future_date(hours=1):
    """Return an ISO datetime string hours from now."""
    return (datetime.now(timezone.utc) + timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%S")


def _get_test_ids(test_client, token):
    """Get computerId, containerId, and hardware specs for test reservation."""
    resp = test_client.get(
        f"/api/reservation/get_available_hardware?date={_future_date()}&duration=2",
        headers={"Authorization": f"Bearer {token}"},
    )
    data = resp.json()["data"]
    computer = data["computers"][0]
    computer_id = computer["computerId"]
    container_id = data["containers"][0]["containerId"]

    # Build hardware specs from available specs (request minimum amounts)
    hw_specs = {}
    for spec in computer["hardwareSpecs"]:
        if spec["type"] in ("cpus", "ram"):
            hw_specs[str(spec["hardwareSpecId"])] = spec["minimumAmount"]

    return computer_id, container_id, hw_specs


def _create_reservation_via_api(test_client, token, computer_id, container_id, hw_specs,
                                 hours_from_now=2, duration=2, **kwargs):
    """Create a reservation via the API and return the response."""
    date = kwargs.get("date", _future_date(hours=hours_from_now))
    query = (
        f"?date={date}&duration={duration}"
        f"&computerId={computer_id}&containerId={container_id}"
        f"&hardwareSpecs={json.dumps(hw_specs)}"
        f"&adminReserveUserEmail={kwargs.get('adminReserveUserEmail', '')}"
    )
    if "description" in kwargs:
        query += f"&description={kwargs['description']}"
    if "isLowPriority" in kwargs:
        query += f"&isLowPriority={str(kwargs['isLowPriority']).lower()}"
    if "shmSizePercent" in kwargs:
        query += f"&shmSizePercent={kwargs['shmSizePercent']}"
    if "ramDiskSizePercent" in kwargs:
        query += f"&ramDiskSizePercent={kwargs['ramDiskSizePercent']}"
    if "startNow" in kwargs:
        query += f"&startNow={str(kwargs['startNow']).lower()}"

    return test_client.post(
        f"/api/reservation/create_reservation{query}",
        headers={"Authorization": f"Bearer {token}"},
    )


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
            endDate=now + timedelta(hours=duration_hours),
            status=status,
        )
        session.add(reservation)
        session.flush()

        # Add hardware specs (cpus and ram at minimum)
        hw_specs = session.execute(
            select(db.HardwareSpec).where(db.HardwareSpec.computerId == computer.computerId)
        ).scalars().all()
        for spec in hw_specs:
            if spec.type in ("cpus", "ram"):
                reservation.reservedHardwareSpecs.append(
                    db.ReservedHardwareSpec(
                        hardwareSpecId=spec.hardwareSpecId,
                        amount=spec.minimumAmount,
                    )
                )

        session.commit()
        return reservation.reservationId


def _fully_book_computer(computer_name, hours_offset=0, duration_hours=4, user_email="admin@foo.com"):
    """Create a reservation that consumes all CPU/RAM on the named computer."""
    now = datetime.now(timezone.utc) + timedelta(hours=hours_offset)
    with db.Session() as session:
        computer = session.execute(
            select(db.Computer).where(db.Computer.name == computer_name)
        ).scalar_one()
        user = session.execute(
            select(db.User).where(db.User.email == user_email)
        ).scalar_one()
        container = session.execute(select(db.Container)).scalars().first()

        reserved_container = db.ReservedContainer(containerId=container.containerId)
        session.add(reserved_container)
        session.flush()

        reservation = db.Reservation(
            userId=user.userId,
            computerId=computer.computerId,
            reservedContainerId=reserved_container.reservedContainerId,
            startDate=now,
            endDate=now + timedelta(hours=duration_hours),
            status="reserved",
        )
        session.add(reservation)
        session.flush()

        for spec in computer.hardwareSpecs:
            if spec.type in ("cpus", "ram"):
                reservation.reservedHardwareSpecs.append(
                    db.ReservedHardwareSpec(
                        hardwareSpecId=spec.hardwareSpecId,
                        amount=spec.maximumAmount,
                    )
                )
        session.commit()


def _fully_book_computer_from(computer_id, minutes_from_now):
    """Fully book the computer with the given ID, starting minutes_from_now from now."""
    with db.Session() as session:
        name = session.execute(
            select(db.Computer.name).where(db.Computer.computerId == computer_id)
        ).scalar_one()
    _fully_book_computer(name, hours_offset=minutes_from_now / 60)


def _latest_reservation(session):
    """Return the most recently created reservation."""
    return session.execute(
        select(db.Reservation).order_by(db.Reservation.reservationId.desc()).limit(1)
    ).scalar_one()


# =============================================================================
# get_available_hardware
# =============================================================================

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

    def test_returns_containers(self, test_client, user_token):
        """Response includes available container images."""
        resp = test_client.get(
            f"/api/reservation/get_available_hardware?date={_future_date()}&duration=2",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        data = resp.json()["data"]
        assert "containers" in data
        assert len(data["containers"]) >= 1
        assert data["containers"][0]["imageName"] == "ubuntu-base"

    def test_hardware_reduced_by_existing_reservation(self, test_client, admin_token):
        """Existing reservations reduce available hardware for the same time slot."""
        # Get baseline availability
        date_str = _future_date(hours=5)
        resp = test_client.get(
            f"/api/reservation/get_available_hardware?date={date_str}&duration=2",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        baseline_specs = resp.json()["data"]["computers"][0]["hardwareSpecs"]
        cpu_spec = next(s for s in baseline_specs if s["type"] == "cpus")
        baseline_cpu_max = cpu_spec["maximumAmount"]

        # Create a reservation that overlaps with the queried time slot
        _create_reservation_in_db(status="reserved", hours_offset=4, duration_hours=4, user_email="admin@foo.com")

        # Check availability again — should be reduced
        resp = test_client.get(
            f"/api/reservation/get_available_hardware?date={date_str}&duration=2",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        updated_specs = resp.json()["data"]["computers"][0]["hardwareSpecs"]
        cpu_spec_after = next(s for s in updated_specs if s["type"] == "cpus")
        assert cpu_spec_after["maximumAmount"] < baseline_cpu_max

    def test_admin_gets_full_user_max(self, test_client, admin_token):
        """Admin users get maximumAmountForUser equal to maximumAmount."""
        resp = test_client.get(
            f"/api/reservation/get_available_hardware?date={_future_date()}&duration=2",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        specs = resp.json()["data"]["computers"][0]["hardwareSpecs"]
        for spec in specs:
            assert spec["maximumAmountForUser"] == spec["maximumAmount"]

    def test_normal_user_gets_default_user_max(self, test_client, user_token):
        """Normal users get the default maximumAmountForUser from hardware specs."""
        resp = test_client.get(
            f"/api/reservation/get_available_hardware?date={_future_date()}&duration=2",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        specs = resp.json()["data"]["computers"][0]["hardwareSpecs"]
        cpu_spec = next(s for s in specs if s["type"] == "cpus")
        # Normal user should get the default user max (8), not the system max (8)
        # The key point: it should NOT exceed the maximumAmount
        assert cpu_spec["maximumAmountForUser"] <= cpu_spec["maximumAmount"]

    def test_role_hardware_limits_applied(self, test_client, user_token):
        """Role-based hardware limits restrict the user's maximum."""
        # Create a role with a CPU limit of 2 and assign to user
        with db.Session() as session:
            role = db.Role(name="limited_role")
            session.add(role)
            session.flush()

            user = session.execute(
                select(db.User).where(db.User.email == "user@foo.com")
            ).scalar_one()
            user.roles.append(role)

            server1 = session.execute(
                select(db.Computer).where(db.Computer.name == "server1")
            ).scalar_one()
            cpu_spec = session.execute(
                select(db.HardwareSpec).where(
                    db.HardwareSpec.type == "cpus",
                    db.HardwareSpec.computerId == server1.computerId,
                )
            ).scalar_one()

            limit = db.RoleHardwareLimit(
                roleId=role.roleId,
                hardwareSpecId=cpu_spec.hardwareSpecId,
                maximumAmountForRole=2,
            )
            session.add(limit)
            session.commit()

        resp = test_client.get(
            f"/api/reservation/get_available_hardware?date={_future_date()}&duration=2",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        specs = resp.json()["data"]["computers"][0]["hardwareSpecs"]
        cpu_spec_resp = next(s for s in specs if s["type"] == "cpus")
        assert cpu_spec_resp["maximumAmountForUser"] == 2

    def test_non_overlapping_reservation_does_not_reduce(self, test_client, admin_token):
        """Reservations in a different time slot do not affect availability."""
        # Create reservation far in the future
        _create_reservation_in_db(status="reserved", hours_offset=100, duration_hours=2, user_email="admin@foo.com")

        # Query for availability at a non-overlapping time
        resp = test_client.get(
            f"/api/reservation/get_available_hardware?date={_future_date(hours=1)}&duration=2",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        specs = resp.json()["data"]["computers"][0]["hardwareSpecs"]
        cpu_spec = next(s for s in specs if s["type"] == "cpus")
        # Full capacity should be available
        assert cpu_spec["maximumAmount"] == 8

    def test_listing_marks_only_overbooked_computer(self, test_client, admin_token):
        """Listing succeeds and flags fullyBooked per-computer."""
        _fully_book_computer("server1")

        resp = test_client.get(
            f"/api/reservation/get_available_hardware?date={_future_date()}&duration=2",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        body = resp.json()
        assert body["status"] is True, body["message"]
        by_name = {c["name"]: c for c in body["data"]["computers"]}
        assert by_name["server1"]["fullyBooked"] is True
        assert by_name["server2"]["fullyBooked"] is False

    def test_listing_fails_when_all_computers_overbooked(self, test_client, admin_token):
        """Listing returns an error only when no computer has capacity."""
        _fully_book_computer("server1")
        _fully_book_computer("server2")

        resp = test_client.get(
            f"/api/reservation/get_available_hardware?date={_future_date()}&duration=2",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        body = resp.json()
        assert body["status"] is False

    def test_start_now_ignores_client_date(self, test_client, admin_token):
        """With startNow, availability is checked from server time, not the given date."""
        # server1 is free now but fully booked two days from now
        _fully_book_computer("server1", hours_offset=48)

        resp = test_client.get(
            f"/api/reservation/get_available_hardware?date={_future_date(hours=48)}&duration=2&startNow=true",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        body = resp.json()
        assert body["status"] is True, body["message"]
        by_name = {c["name"]: c for c in body["data"]["computers"]}
        assert by_name["server1"]["fullyBooked"] is False

    def test_offset_date_is_converted_to_utc(self, test_client, admin_token):
        """A date sent with a non-UTC offset is checked against the right UTC window."""
        # server1 is fully booked from now+1h to now+2h
        _fully_book_computer("server1", hours_offset=1, duration_hours=1)
        start_utc = datetime.now(timezone.utc) + timedelta(minutes=30)
        start_with_offset = start_utc.astimezone(timezone(timedelta(hours=2))).isoformat()

        resp = test_client.get(
            f"/api/reservation/get_available_hardware?date={quote(start_with_offset)}&duration=2",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        body = resp.json()
        assert body["status"] is True, body["message"]
        by_name = {c["name"]: c for c in body["data"]["computers"]}
        assert by_name["server1"]["fullyBooked"] is True

    def test_invalid_date_returns_error(self, test_client, admin_token):
        """An unparseable date returns an error response instead of a server error."""
        resp = test_client.get(
            "/api/reservation/get_available_hardware?date=not-a-date&duration=2",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] is False


# =============================================================================
# create_reservation
# =============================================================================

class TestCreateReservation:

    def test_create_reservation_unauthenticated(self, test_client):
        resp = test_client.post(
            "/api/reservation/create_reservation"
            "?date=2030-01-01T00:00:00&duration=2&computerId=1&containerId=1"
            "&hardwareSpecs={}&adminReserveUserEmail=",
        )
        assert resp.status_code in (401, 422)

    def test_description_too_long(self, test_client, admin_token):
        computer_id, container_id, hw_specs = _get_test_ids(test_client, admin_token)
        resp = _create_reservation_via_api(
            test_client, admin_token, computer_id, container_id, hw_specs,
            description="x" * 51,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] is False
        assert "Description" in resp.json()["message"] or "description" in resp.json()["message"].lower()

    def test_shm_size_out_of_range(self, test_client, admin_token):
        computer_id, container_id, hw_specs = _get_test_ids(test_client, admin_token)
        resp = _create_reservation_via_api(
            test_client, admin_token, computer_id, container_id, hw_specs,
            shmSizePercent=95,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] is False
        assert "SHM" in resp.json()["message"] or "shm" in resp.json()["message"].lower()

    def test_create_reservation_success(self, test_client, admin_token):
        """Successfully create a reservation with valid parameters."""
        computer_id, container_id, hw_specs = _get_test_ids(test_client, admin_token)
        resp = _create_reservation_via_api(
            test_client, admin_token, computer_id, container_id, hw_specs,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] is True
        assert "Reservation created" in data["message"]

    def test_create_reservation_succeeds_when_other_computer_overbooked(self, test_client, admin_token):
        """A reservation on server2 must succeed even if server1 is fully booked."""
        _fully_book_computer("server1")

        resp = test_client.get(
            f"/api/reservation/get_available_hardware?date={_future_date()}&duration=2",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        body = resp.json()["data"]
        server2 = next(c for c in body["computers"] if c["name"] == "server2")
        container_id = body["containers"][0]["containerId"]

        hw_specs = {}
        for spec in server2["hardwareSpecs"]:
            if spec["type"] in ("cpus", "ram"):
                hw_specs[str(spec["hardwareSpecId"])] = spec["maximumAmountForUser"]

        create_resp = _create_reservation_via_api(
            test_client, admin_token, server2["computerId"], container_id, hw_specs,
        )
        assert create_resp.status_code == 200
        assert create_resp.json()["status"] is True, create_resp.json()["message"]

    def test_create_reservation_max_out_resources(self, test_client, admin_token):
        """A reservation that consumes all available CPUs and RAM must succeed.

        Regression for the bug where get_available_hardware compared the
        post-subtraction leftover against minimumAmount and rejected the
        last slice of a resource.
        """
        resp = test_client.get(
            f"/api/reservation/get_available_hardware?date={_future_date()}&duration=2",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        data = resp.json()["data"]
        computer = data["computers"][0]
        computer_id = computer["computerId"]
        container_id = data["containers"][0]["containerId"]

        hw_specs = {}
        for spec in computer["hardwareSpecs"]:
            if spec["type"] in ("cpus", "ram"):
                hw_specs[str(spec["hardwareSpecId"])] = spec["maximumAmountForUser"]

        resp = _create_reservation_via_api(
            test_client, admin_token, computer_id, container_id, hw_specs,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] is True, body["message"]

    def test_create_reservation_creates_db_record(self, test_client, admin_token):
        """Verify reservation record exists in the database after creation."""
        computer_id, container_id, hw_specs = _get_test_ids(test_client, admin_token)
        _create_reservation_via_api(
            test_client, admin_token, computer_id, container_id, hw_specs,
        )

        with db.Session() as session:
            reservations = session.execute(select(db.Reservation)).scalars().all()
            assert len(reservations) == 1
            assert reservations[0].status == "reserved"

    def test_create_reservation_stores_hardware_specs(self, test_client, admin_token):
        """Verify hardware specs are stored on the reservation."""
        computer_id, container_id, hw_specs = _get_test_ids(test_client, admin_token)
        _create_reservation_via_api(
            test_client, admin_token, computer_id, container_id, hw_specs,
        )

        with db.Session() as session:
            reservation = session.execute(select(db.Reservation)).scalar_one()
            reserved_specs = session.execute(
                select(db.ReservedHardwareSpec)
                .where(db.ReservedHardwareSpec.reservationId == reservation.reservationId)
            ).scalars().all()
            assert len(reserved_specs) == len(hw_specs)

    def test_create_reservation_normal_user_success(self, test_client, user_token):
        """Normal user can create a reservation within their limits."""
        computer_id, container_id, hw_specs = _get_test_ids(test_client, user_token)
        resp = _create_reservation_via_api(
            test_client, user_token, computer_id, container_id, hw_specs,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] is True

    def test_create_reservation_with_description(self, test_client, admin_token):
        """Reservation stores description when provided."""
        computer_id, container_id, hw_specs = _get_test_ids(test_client, admin_token)
        _create_reservation_via_api(
            test_client, admin_token, computer_id, container_id, hw_specs,
            description="Test reservation",
        )

        with db.Session() as session:
            reservation = session.execute(select(db.Reservation)).scalar_one()
            assert reservation.description == "Test reservation"

    def test_create_low_priority_reservation(self, test_client, admin_token):
        """Low-priority reservations skip the hardware availability check."""
        computer_id, container_id, hw_specs = _get_test_ids(test_client, admin_token)
        resp = _create_reservation_via_api(
            test_client, admin_token, computer_id, container_id, hw_specs,
            isLowPriority=True,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] is True

        with db.Session() as session:
            reservation = session.execute(select(db.Reservation)).scalar_one()
            assert reservation.isLowPriority is True

    def test_create_reservation_start_now_uses_server_time(self, test_client, admin_token):
        """startNow starts the reservation at server time even if the client clock is ahead."""
        computer_id, container_id, hw_specs = _get_test_ids(test_client, admin_token)
        before = datetime.now(timezone.utc).replace(tzinfo=None)
        resp = _create_reservation_via_api(
            test_client, admin_token, computer_id, container_id, hw_specs,
            hours_from_now=3, duration=2, startNow=True,
        )
        after = datetime.now(timezone.utc).replace(tzinfo=None)
        assert resp.json()["status"] is True, resp.json()["message"]

        with db.Session() as session:
            reservation = session.execute(select(db.Reservation)).scalar_one()
            start = reservation.startDate.replace(tzinfo=None)
            end = reservation.endDate.replace(tzinfo=None)
            assert before - timedelta(seconds=1) <= start <= after + timedelta(seconds=1)
            assert end - start == timedelta(hours=2)

    def test_create_reservation_without_start_now_uses_client_date(self, test_client, admin_token):
        """Without startNow, the reservation starts at the date the client sent."""
        computer_id, container_id, hw_specs = _get_test_ids(test_client, admin_token)
        resp = _create_reservation_via_api(
            test_client, admin_token, computer_id, container_id, hw_specs,
            hours_from_now=3,
        )
        assert resp.json()["status"] is True, resp.json()["message"]

        with db.Session() as session:
            reservation = session.execute(select(db.Reservation)).scalar_one()
            start = reservation.startDate.replace(tzinfo=None)
            expected = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=3)
            assert abs(start - expected) < timedelta(minutes=1)

    def test_create_reservation_past_start_moves_to_now(self, test_client, admin_token):
        """A start date that has already passed starts now and keeps the full duration."""
        computer_id, container_id, hw_specs = _get_test_ids(test_client, admin_token)
        before = datetime.now(timezone.utc).replace(tzinfo=None)
        resp = _create_reservation_via_api(
            test_client, admin_token, computer_id, container_id, hw_specs,
            hours_from_now=-1, duration=2,
        )
        after = datetime.now(timezone.utc).replace(tzinfo=None)
        assert resp.json()["status"] is True, resp.json()["message"]

        with db.Session() as session:
            reservation = session.execute(select(db.Reservation)).scalar_one()
            start = reservation.startDate.replace(tzinfo=None)
            end = reservation.endDate.replace(tzinfo=None)
            assert before - timedelta(seconds=1) <= start <= after + timedelta(seconds=1)
            assert end - start == timedelta(hours=2)

    def test_create_reservation_past_start_keeps_original_end_on_conflict(self, test_client, admin_token):
        """If the full duration from now hits a later booking, the originally chosen end is kept."""
        computer_id, container_id, hw_specs = _get_test_ids(test_client, admin_token)
        # The chosen window ends at now+1h50m; another booking takes the computer from now+1h55m
        _fully_book_computer_from(computer_id, minutes_from_now=115)
        before = datetime.now(timezone.utc).replace(tzinfo=None)
        resp = _create_reservation_via_api(
            test_client, admin_token, computer_id, container_id, hw_specs,
            hours_from_now=-10 / 60, duration=2,
        )
        after = datetime.now(timezone.utc).replace(tzinfo=None)
        assert resp.json()["status"] is True, resp.json()["message"]

        with db.Session() as session:
            reservation = _latest_reservation(session)
            start = reservation.startDate.replace(tzinfo=None)
            end = reservation.endDate.replace(tzinfo=None)
            assert before - timedelta(seconds=1) <= start <= after + timedelta(seconds=1)
            assert abs(end - (before + timedelta(minutes=110))) < timedelta(seconds=5)

    def test_create_reservation_past_start_rejected_when_original_window_taken(self, test_client, admin_token):
        """The end fallback never allows a conflict inside the originally chosen window."""
        computer_id, container_id, hw_specs = _get_test_ids(test_client, admin_token)
        # Another booking takes the computer from now+1h40m, before the chosen end (now+1h50m)
        _fully_book_computer_from(computer_id, minutes_from_now=100)
        resp = _create_reservation_via_api(
            test_client, admin_token, computer_id, container_id, hw_specs,
            hours_from_now=-10 / 60, duration=2,
        )
        assert resp.json()["status"] is False

    def test_create_reservation_start_now_keeps_click_time_end_on_conflict(self, test_client, admin_token):
        """With startNow, the end fallback counts from the time the user clicked."""
        computer_id, container_id, hw_specs = _get_test_ids(test_client, admin_token)
        _fully_book_computer_from(computer_id, minutes_from_now=115)
        before = datetime.now(timezone.utc).replace(tzinfo=None)
        resp = _create_reservation_via_api(
            test_client, admin_token, computer_id, container_id, hw_specs,
            hours_from_now=-10 / 60, duration=2, startNow=True,
        )
        assert resp.json()["status"] is True, resp.json()["message"]

        with db.Session() as session:
            reservation = _latest_reservation(session)
            end = reservation.endDate.replace(tzinfo=None)
            assert abs(end - (before + timedelta(minutes=110))) < timedelta(seconds=5)

    def test_create_reservation_start_now_ignores_unparseable_date(self, test_client, admin_token):
        """With startNow, an unparseable date doesn't fail the request."""
        computer_id, container_id, hw_specs = _get_test_ids(test_client, admin_token)
        resp = _create_reservation_via_api(
            test_client, admin_token, computer_id, container_id, hw_specs,
            date="not-a-date", startNow=True,
        )
        assert resp.json()["status"] is True, resp.json()["message"]

    def test_create_reservation_invalid_date_returns_error(self, test_client, admin_token):
        """Unparseable or out-of-range dates return an error response instead of a server error."""
        computer_id, container_id, hw_specs = _get_test_ids(test_client, admin_token)
        for bad_date in ("not-a-date", quote("0001-01-01T00:00:00+01:00")):
            resp = _create_reservation_via_api(
                test_client, admin_token, computer_id, container_id, hw_specs,
                date=bad_date,
            )
            assert resp.status_code == 200
            assert resp.json()["status"] is False
            assert resp.json()["message"] == "Invalid date parameter."

    def test_create_reservation_converts_offset_date_to_utc(self, test_client, admin_token):
        """A start date sent with a non-UTC offset is stored as UTC."""
        computer_id, container_id, hw_specs = _get_test_ids(test_client, admin_token)
        start_utc = datetime.now(timezone.utc).replace(microsecond=0) + timedelta(hours=3)
        start_with_offset = start_utc.astimezone(timezone(timedelta(hours=2))).isoformat()
        resp = _create_reservation_via_api(
            test_client, admin_token, computer_id, container_id, hw_specs,
            date=quote(start_with_offset),
        )
        assert resp.json()["status"] is True, resp.json()["message"]

        with db.Session() as session:
            reservation = session.execute(select(db.Reservation)).scalar_one()
            assert reservation.startDate.replace(tzinfo=None) == start_utc.replace(tzinfo=None)

    def test_create_reservation_audit_log_records_dates(self, test_client, admin_token):
        """The RESERVATION_CREATE audit entry records the start and end actually used."""
        computer_id, container_id, hw_specs = _get_test_ids(test_client, admin_token)
        _create_reservation_via_api(
            test_client, admin_token, computer_id, container_id, hw_specs,
            hours_from_now=-10 / 60, duration=2,
        )

        with db.Session() as session:
            reservation = session.execute(select(db.Reservation)).scalar_one()
            entry = session.execute(
                select(db.AuditLog).where(db.AuditLog.action == "RESERVATION_CREATE")
            ).scalar_one()
            details = json.loads(entry.details)
            assert datetime.fromisoformat(details["startDate"]).replace(tzinfo=None) == reservation.startDate.replace(tzinfo=None)
            assert datetime.fromisoformat(details["endDate"]).replace(tzinfo=None) == reservation.endDate.replace(tzinfo=None)

    def test_create_reservation_invalid_computer(self, test_client, admin_token):
        """Reject reservation for a non-existent computer."""
        _, container_id, hw_specs = _get_test_ids(test_client, admin_token)
        resp = _create_reservation_via_api(
            test_client, admin_token, 99999, container_id, hw_specs,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] is False

    def test_create_reservation_invalid_container(self, test_client, admin_token):
        """Reject reservation for a non-existent container."""
        computer_id, _, hw_specs = _get_test_ids(test_client, admin_token)
        resp = _create_reservation_via_api(
            test_client, admin_token, computer_id, 99999, hw_specs,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] is False

    def test_create_reservation_private_computer_denied_for_user(self, test_client, user_token):
        """A normal user cannot reserve a private computer."""
        computer_id, container_id, hw_specs = _get_test_ids(test_client, user_token)
        with db.Session() as session:
            session.get(db.Computer, computer_id).public = False
            session.commit()
        resp = _create_reservation_via_api(
            test_client, user_token, computer_id, container_id, hw_specs,
        )
        assert resp.json()["status"] is False
        assert resp.json()["message"] == "Access denied to private computer."

        with db.Session() as session:
            assert session.execute(select(db.Reservation)).first() is None

    def test_create_reservation_private_computer_allowed_for_admin(self, test_client, admin_token):
        """Admins can reserve a private computer, also on behalf of another user."""
        computer_id, container_id, hw_specs = _get_test_ids(test_client, admin_token)
        with db.Session() as session:
            session.get(db.Computer, computer_id).public = False
            session.commit()
        resp = _create_reservation_via_api(
            test_client, admin_token, computer_id, container_id, hw_specs,
            adminReserveUserEmail="user@foo.com",
        )
        assert resp.json()["status"] is True, resp.json()["message"]

    def test_create_reservation_removed_computer(self, test_client, admin_token):
        """A removed computer cannot be reserved, even by an admin."""
        computer_id, container_id, hw_specs = _get_test_ids(test_client, admin_token)
        with db.Session() as session:
            session.get(db.Computer, computer_id).removed = True
            session.commit()
        resp = _create_reservation_via_api(
            test_client, admin_token, computer_id, container_id, hw_specs,
        )
        assert resp.json()["status"] is False
        assert resp.json()["message"] == "Computer not found."

    def test_create_reservation_removed_container(self, test_client, admin_token):
        """A removed container cannot be reserved, even by an admin."""
        computer_id, container_id, hw_specs = _get_test_ids(test_client, admin_token)
        with db.Session() as session:
            session.get(db.Container, container_id).removed = True
            session.commit()
        resp = _create_reservation_via_api(
            test_client, admin_token, computer_id, container_id, hw_specs,
        )
        assert resp.json()["status"] is False
        assert resp.json()["message"] == "Container not found."

    def test_create_reservation_rejects_specs_from_another_computer(self, test_client, admin_token):
        """Hardware specs of another computer are rejected, so its capacity check can't be skipped."""
        computer_id, container_id, _ = _get_test_ids(test_client, admin_token)
        with db.Session() as session:
            other_cpu_id = session.execute(
                select(db.HardwareSpec.hardwareSpecId).where(
                    db.HardwareSpec.type == "cpus",
                    db.HardwareSpec.computerId != computer_id,
                )
            ).scalars().first()
        resp = _create_reservation_via_api(
            test_client, admin_token, computer_id, container_id, {str(other_cpu_id): 1},
        )
        assert resp.json()["status"] is False
        assert resp.json()["message"] == f"Invalid hardware specification ID: {other_cpu_id}"

        with db.Session() as session:
            assert session.execute(select(db.Reservation)).first() is None

    def test_create_reservation_rejects_non_finite_amounts(self, test_client, admin_token):
        """NaN and Infinity amounts are rejected; NaN would compare false against every limit."""
        computer_id, container_id, hw_specs = _get_test_ids(test_client, admin_token)
        spec_id = next(iter(hw_specs))
        for amount in (float("nan"), float("inf"), float("-inf")):
            resp = _create_reservation_via_api(
                test_client, admin_token, computer_id, container_id, {**hw_specs, spec_id: amount},
            )
            assert resp.json()["status"] is False
            assert resp.json()["message"] == "Invalid hardware spec amount."

    def test_create_reservation_rejects_zero_padded_spec_ids(self, test_client, admin_token):
        """Spec IDs must be plain digits; "05" would be a second entry for spec 5."""
        computer_id, container_id, hw_specs = _get_test_ids(test_client, admin_token)
        padded_specs = {f"0{key}": val for key, val in hw_specs.items()}
        resp = _create_reservation_via_api(
            test_client, admin_token, computer_id, container_id, padded_specs,
        )
        assert resp.json()["status"] is False
        assert resp.json()["message"] == "Invalid hardware spec ID format."

    def test_create_reservation_nan_with_padded_duplicate_cannot_overbook(self, test_client, user_token):
        """NaN plus a zero-padded duplicate ID can't book a computer that is already full."""
        computer_id, container_id, hw_specs = _get_test_ids(test_client, user_token)
        _fully_book_computer_from(computer_id, minutes_from_now=60)
        specs = {}
        for key in hw_specs:
            specs[key] = float("nan")
            specs[f"0{key}"] = 1
        resp = _create_reservation_via_api(
            test_client, user_token, computer_id, container_id, specs,
        )
        assert resp.json()["status"] is False

        with db.Session() as session:
            # Only the full booking exists
            assert len(session.execute(select(db.Reservation)).scalars().all()) == 1

    def test_create_reservation_exceeds_user_hardware_limit(self, test_client, user_token):
        """Normal user cannot exceed the hardware maximumAmountForUser."""
        computer_id, container_id, _ = _get_test_ids(test_client, user_token)

        # Request more CPUs than the user max (8)
        with db.Session() as session:
            server1 = session.execute(
                select(db.Computer).where(db.Computer.name == "server1")
            ).scalar_one()
            cpu_spec = session.execute(
                select(db.HardwareSpec).where(
                    db.HardwareSpec.type == "cpus",
                    db.HardwareSpec.computerId == server1.computerId,
                )
            ).scalar_one()
            ram_spec = session.execute(
                select(db.HardwareSpec).where(
                    db.HardwareSpec.type == "ram",
                    db.HardwareSpec.computerId == server1.computerId,
                )
            ).scalar_one()

        hw_specs = {
            str(cpu_spec.hardwareSpecId): 99,
            str(ram_spec.hardwareSpecId): ram_spec.minimumAmount,
        }
        resp = _create_reservation_via_api(
            test_client, user_token, computer_id, container_id, hw_specs,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] is False

    def test_active_reservation_limit_enforced(self, test_client, user_token):
        """Normal user cannot exceed active reservation limit (default 1)."""
        computer_id, container_id, hw_specs = _get_test_ids(test_client, user_token)

        # First reservation should succeed
        resp = _create_reservation_via_api(
            test_client, user_token, computer_id, container_id, hw_specs,
            hours_from_now=10, duration=2,
        )
        assert resp.json()["status"] is True

        # Second reservation should fail (default limit is 1 for normal users)
        resp = _create_reservation_via_api(
            test_client, user_token, computer_id, container_id, hw_specs,
            hours_from_now=20, duration=2,
        )
        assert resp.json()["status"] is False
        assert "active reservation" in resp.json()["message"].lower()

    def test_admin_on_behalf_of_other_user(self, test_client, admin_token):
        """Admin can create a reservation on behalf of another user."""
        computer_id, container_id, hw_specs = _get_test_ids(test_client, admin_token)
        resp = _create_reservation_via_api(
            test_client, admin_token, computer_id, container_id, hw_specs,
            adminReserveUserEmail="user@foo.com",
        )
        assert resp.status_code == 200
        assert resp.json()["status"] is True

        # Verify reservation belongs to the target user
        with db.Session() as session:
            reservation = session.execute(select(db.Reservation)).scalar_one()
            user = session.execute(
                select(db.User).where(db.User.email == "user@foo.com")
            ).scalar_one()
            assert reservation.userId == user.userId

    def test_ram_disk_percent_out_of_range(self, test_client, admin_token):
        """RAM disk percentage above 60 is rejected."""
        computer_id, container_id, hw_specs = _get_test_ids(test_client, admin_token)
        resp = _create_reservation_via_api(
            test_client, admin_token, computer_id, container_id, hw_specs,
            ramDiskSizePercent=65,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] is False


# =============================================================================
# extend_reservation
# =============================================================================

class TestExtendReservation:

    def test_extend_started_reservation(self, test_client, admin_token):
        """Successfully extend a started reservation."""
        res_id = _create_reservation_in_db(status="started", hours_offset=0, duration_hours=4, user_email="admin@foo.com")

        resp = test_client.post(
            f"/api/reservation/extend_reservation?reservationId={res_id}&duration=2",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] is True
        assert "extended" in data["message"].lower()

    def test_extend_updates_end_date(self, test_client, admin_token):
        """Verify the end date is actually updated in the database."""
        res_id = _create_reservation_in_db(status="started", hours_offset=0, duration_hours=4, user_email="admin@foo.com")

        with db.Session() as session:
            original_end = session.execute(
                select(db.Reservation).where(db.Reservation.reservationId == res_id)
            ).scalar_one().endDate

        test_client.post(
            f"/api/reservation/extend_reservation?reservationId={res_id}&duration=3",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        with db.Session() as session:
            new_end = session.execute(
                select(db.Reservation).where(db.Reservation.reservationId == res_id)
            ).scalar_one().endDate

        assert new_end > original_end
        # Should be extended by ~3 hours
        diff_hours = (new_end - original_end).total_seconds() / 3600
        assert abs(diff_hours - 3) < 0.01

    def test_extend_paused_reservation(self, test_client, admin_token):
        """Paused reservations can also be extended."""
        res_id = _create_reservation_in_db(status="paused", hours_offset=0, duration_hours=4, user_email="admin@foo.com")

        resp = test_client.post(
            f"/api/reservation/extend_reservation?reservationId={res_id}&duration=2",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] is True

    def test_cannot_extend_reserved_status(self, test_client, admin_token):
        """Cannot extend a reservation that hasn't started yet."""
        res_id = _create_reservation_in_db(status="reserved", hours_offset=1, duration_hours=4, user_email="admin@foo.com")

        resp = test_client.post(
            f"/api/reservation/extend_reservation?reservationId={res_id}&duration=2",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] is False
        assert "not active" in resp.json()["message"].lower()

    def test_cannot_extend_stopped_reservation(self, test_client, admin_token):
        """Cannot extend a stopped reservation."""
        res_id = _create_reservation_in_db(status="stopped", hours_offset=-5, duration_hours=4, user_email="admin@foo.com")

        resp = test_client.post(
            f"/api/reservation/extend_reservation?reservationId={res_id}&duration=2",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] is False

    def test_extend_duration_too_high(self, test_client, admin_token):
        """Duration above 24 hours is rejected."""
        res_id = _create_reservation_in_db(status="started", hours_offset=0, duration_hours=4, user_email="admin@foo.com")

        resp = test_client.post(
            f"/api/reservation/extend_reservation?reservationId={res_id}&duration=25",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] is False
        assert "Duration" in resp.json()["message"]

    def test_extend_negative_duration(self, test_client, admin_token):
        """Negative duration is rejected."""
        res_id = _create_reservation_in_db(status="started", hours_offset=0, duration_hours=4, user_email="admin@foo.com")

        resp = test_client.post(
            f"/api/reservation/extend_reservation?reservationId={res_id}&duration=-1",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] is False

    def test_extend_nonexistent_reservation(self, test_client, admin_token):
        """Extending a non-existent reservation returns error."""
        resp = test_client.post(
            "/api/reservation/extend_reservation?reservationId=99999&duration=2",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] is False

    def test_user_can_extend_own_reservation(self, test_client, user_token):
        """Normal user can extend their own started reservation."""
        res_id = _create_reservation_in_db(status="started", hours_offset=0, duration_hours=4, user_email="user@foo.com")

        resp = test_client.post(
            f"/api/reservation/extend_reservation?reservationId={res_id}&duration=1",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] is True

    def test_user_cannot_extend_other_users_reservation(self, test_client, user_token):
        """Normal user cannot extend another user's reservation."""
        res_id = _create_reservation_in_db(status="started", hours_offset=0, duration_hours=4, user_email="admin@foo.com")

        resp = test_client.post(
            f"/api/reservation/extend_reservation?reservationId={res_id}&duration=1",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] is False

    def test_admin_can_extend_any_reservation(self, test_client, admin_token):
        """Admin can extend another user's reservation."""
        res_id = _create_reservation_in_db(status="started", hours_offset=0, duration_hours=4, user_email="user@foo.com")

        resp = test_client.post(
            f"/api/reservation/extend_reservation?reservationId={res_id}&duration=2",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] is True

    def test_extend_unauthenticated(self, test_client):
        """Unauthenticated extension is rejected."""
        resp = test_client.post(
            "/api/reservation/extend_reservation?reservationId=1&duration=2",
        )
        assert resp.status_code in (401, 422)


# =============================================================================
# Other reservation endpoints
# =============================================================================

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
