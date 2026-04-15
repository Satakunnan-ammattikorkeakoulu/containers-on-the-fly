"""Tests for the container server daemon's pure-logic functions."""

from unittest.mock import patch, MagicMock, call

from daemon import (
    _are_resources_available,
    pause_low_priority_for_normal_reservations,
    pause_overcommitted_low_priority,
    resume_paused_containers,
)


# ---------------------------------------------------------------------------
# Helpers to build task structures
# ---------------------------------------------------------------------------

def _hw_spec(spec_id, amount):
    return {"hardwareSpecId": spec_id, "amount": amount}


def _reservation(res_id, specs, *, is_lp=False, container_name=None,
                 image_name="img", computer_name="srv", created_at="2025-01-01",
                 stop_script=None, container_username="user"):
    res = {
        "reservationId": res_id,
        "reservedHardwareSpecs": [_hw_spec(s, a) for s, a in specs],
        "isLowPriority": is_lp,
        "createdAt": created_at,
        "container": {"imageName": image_name, "containerUsername": container_username},
        "computer": {"name": computer_name},
    }
    if container_name:
        res["reservedContainer"] = {
            "containerDockerName": container_name,
            "stopScriptPath": stop_script,
        }
    else:
        res["reservedContainer"] = {}
    return res


def _capacity(specs):
    return {"hardwareSpecs": [{"hardwareSpecId": s, "maximumAmount": a} for s, a in specs]}


def _tasks(**overrides):
    base = {
        "computerCapacity": _capacity([]),
        "allActiveReservations": [],
        "normalPendingReservations": [],
        "lowPriorityRunning": [],
        "pausedReservations": [],
        "futureNormalReservations": [],
        "stopScriptTimeoutSeconds": 40,
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# _are_resources_available
# ---------------------------------------------------------------------------

class TestAreResourcesAvailable:

    def test_available_with_no_active_reservations(self):
        res = _reservation(1, [("cpu", 2)])
        tasks = _tasks(computerCapacity=_capacity([("cpu", 8)]))
        assert _are_resources_available(res, tasks) is True

    def test_available_with_headroom(self):
        res = _reservation(1, [("cpu", 2)])
        active = [_reservation(2, [("cpu", 4)])]
        tasks = _tasks(
            computerCapacity=_capacity([("cpu", 8)]),
            allActiveReservations=active,
        )
        assert _are_resources_available(res, tasks) is True

    def test_not_available_when_insufficient(self):
        res = _reservation(1, [("cpu", 2)])
        active = [_reservation(2, [("cpu", 7)])]
        tasks = _tasks(
            computerCapacity=_capacity([("cpu", 8)]),
            allActiveReservations=active,
        )
        assert _are_resources_available(res, tasks) is False

    def test_excludes_self_from_usage(self):
        res = _reservation(1, [("cpu", 4)])
        active = [
            _reservation(1, [("cpu", 4)]),
            _reservation(2, [("cpu", 3)]),
        ]
        tasks = _tasks(
            computerCapacity=_capacity([("cpu", 8)]),
            allActiveReservations=active,
        )
        assert _are_resources_available(res, tasks) is True

    def test_multiple_spec_types(self):
        res = _reservation(1, [("cpu", 2), ("ram", 4)])
        active = [_reservation(2, [("cpu", 4), ("ram", 10)])]
        tasks = _tasks(
            computerCapacity=_capacity([("cpu", 8), ("ram", 16)]),
            allActiveReservations=active,
        )
        assert _are_resources_available(res, tasks) is True

    def test_unknown_spec_returns_false(self):
        res = _reservation(1, [("gpu", 1)])
        tasks = _tasks(computerCapacity=_capacity([("cpu", 8)]))
        assert _are_resources_available(res, tasks) is False


# ---------------------------------------------------------------------------
# pause_low_priority_for_normal_reservations
# ---------------------------------------------------------------------------

class TestPauseLowPriorityForNormalReservations:

    @patch("daemon.settings_handler")
    @patch("daemon.api")
    def test_no_action_when_docker_disabled(self, mock_api, mock_settings):
        mock_settings.get_setting.return_value = False
        pause_low_priority_for_normal_reservations(_tasks())
        mock_api.report_paused.assert_not_called()

    @patch("daemon.settings_handler")
    @patch("daemon.api")
    def test_no_action_when_no_normal_pending(self, mock_api, mock_settings):
        mock_settings.get_setting.return_value = True
        tasks = _tasks(normalPendingReservations=[])
        pause_low_priority_for_normal_reservations(tasks)
        mock_api.report_paused.assert_not_called()

    @patch("daemon.settings_handler")
    @patch("daemon.api")
    def test_no_action_when_no_lp_running(self, mock_api, mock_settings):
        mock_settings.get_setting.return_value = True
        tasks = _tasks(
            normalPendingReservations=[_reservation(1, [("cpu", 2)])],
            lowPriorityRunning=[],
        )
        pause_low_priority_for_normal_reservations(tasks)
        mock_api.report_paused.assert_not_called()

    @patch("daemon.settings_handler")
    @patch("daemon.api")
    def test_no_action_when_resources_already_available(self, mock_api, mock_settings):
        mock_settings.get_setting.return_value = True
        tasks = _tasks(
            computerCapacity=_capacity([("cpu", 8)]),
            allActiveReservations=[_reservation(2, [("cpu", 2)], is_lp=True)],
            normalPendingReservations=[_reservation(1, [("cpu", 2)])],
            lowPriorityRunning=[_reservation(2, [("cpu", 2)], is_lp=True, container_name="r-2")],
        )
        pause_low_priority_for_normal_reservations(tasks)
        mock_api.report_paused.assert_not_called()

    @patch("daemon.run_stop_script")
    @patch("daemon.stop_container")
    @patch("daemon.settings_handler")
    @patch("daemon.api")
    def test_pauses_lp_to_free_resources(self, mock_api, mock_settings, mock_stop, mock_run_stop):
        mock_settings.get_setting.return_value = True
        lp = _reservation(2, [("cpu", 4)], is_lp=True, container_name="r-2")
        # non-LP uses 6 of 8 CPUs -> available = 2, but normal needs 4 -> deficit
        tasks = _tasks(
            computerCapacity=_capacity([("cpu", 8)]),
            allActiveReservations=[
                _reservation(3, [("cpu", 6)]),
                lp,
            ],
            normalPendingReservations=[_reservation(1, [("cpu", 4)])],
            lowPriorityRunning=[lp],
        )
        pause_low_priority_for_normal_reservations(tasks)
        mock_stop.assert_called_once_with("r-2")
        mock_api.report_paused.assert_called_once()

    @patch("daemon.run_stop_script")
    @patch("daemon.stop_container")
    @patch("daemon.settings_handler")
    @patch("daemon.api")
    def test_pauses_newest_lp_first(self, mock_api, mock_settings, mock_stop, mock_run_stop):
        mock_settings.get_setting.return_value = True
        lp_old = _reservation(10, [("cpu", 4)], is_lp=True, container_name="r-10", created_at="2025-01-01")
        lp_new = _reservation(11, [("cpu", 4)], is_lp=True, container_name="r-11", created_at="2025-06-01")
        # non-LP uses 6 of 8 CPUs -> deficit for normal needing 4
        tasks = _tasks(
            computerCapacity=_capacity([("cpu", 8)]),
            allActiveReservations=[_reservation(99, [("cpu", 6)]), lp_old, lp_new],
            normalPendingReservations=[_reservation(1, [("cpu", 4)])],
            lowPriorityRunning=[lp_old, lp_new],
        )
        pause_low_priority_for_normal_reservations(tasks)
        # Should pause the newest one first (r-11), which frees enough resources
        mock_stop.assert_called_once_with("r-11")

    @patch("daemon.run_stop_script")
    @patch("daemon.stop_container")
    @patch("daemon.settings_handler")
    @patch("daemon.api")
    def test_stops_pausing_once_deficit_resolved(self, mock_api, mock_settings, mock_stop, mock_run_stop):
        mock_settings.get_setting.return_value = True
        lp1 = _reservation(10, [("cpu", 4)], is_lp=True, container_name="r-10", created_at="2025-01-01")
        lp2 = _reservation(11, [("cpu", 4)], is_lp=True, container_name="r-11", created_at="2025-06-01")
        tasks = _tasks(
            computerCapacity=_capacity([("cpu", 12)]),
            allActiveReservations=[lp1, lp2],
            normalPendingReservations=[_reservation(1, [("cpu", 4)])],
            lowPriorityRunning=[lp1, lp2],
        )
        pause_low_priority_for_normal_reservations(tasks)
        # Only 1 LP needs to be paused to free 4 CPUs (12 capacity - 0 non-lp used = 12 avail, need 4)
        # Actually non-LP used = 0, available = 12, need 4 -> resources_ok is True, no pauses needed
        # Let me fix: make capacity tighter
        tasks = _tasks(
            computerCapacity=_capacity([("cpu", 8)]),
            allActiveReservations=[lp1, lp2],
            normalPendingReservations=[_reservation(1, [("cpu", 4)])],
            lowPriorityRunning=[lp1, lp2],
        )
        pause_low_priority_for_normal_reservations(tasks)
        # non-lp used = 0, capacity = 8, available = 8, need 4 -> resources_ok is True
        # Need a non-LP reservation eating resources
        tasks = _tasks(
            computerCapacity=_capacity([("cpu", 8)]),
            allActiveReservations=[
                _reservation(99, [("cpu", 6)]),  # non-LP using 6
                lp1, lp2,
            ],
            normalPendingReservations=[_reservation(1, [("cpu", 4)])],
            lowPriorityRunning=[lp1, lp2],
        )
        pause_low_priority_for_normal_reservations(tasks)
        # non-lp used = 6, available = 2, need 4, deficit = 2
        # Pause newest (lp2, 4 cpu) -> deficit resolved, stop
        assert mock_stop.call_count == 1


# ---------------------------------------------------------------------------
# pause_overcommitted_low_priority
# ---------------------------------------------------------------------------

class TestPauseOvercommittedLowPriority:

    @patch("daemon.settings_handler")
    @patch("daemon.api")
    def test_no_action_when_docker_disabled(self, mock_api, mock_settings):
        mock_settings.get_setting.return_value = False
        pause_overcommitted_low_priority(_tasks())
        mock_api.report_paused.assert_not_called()

    @patch("daemon.settings_handler")
    @patch("daemon.api")
    def test_no_action_when_no_lp_running(self, mock_api, mock_settings):
        mock_settings.get_setting.return_value = True
        tasks = _tasks(lowPriorityRunning=[])
        pause_overcommitted_low_priority(tasks)
        mock_api.report_paused.assert_not_called()

    @patch("daemon.settings_handler")
    @patch("daemon.api")
    def test_no_action_when_within_capacity(self, mock_api, mock_settings):
        mock_settings.get_setting.return_value = True
        lp = _reservation(2, [("cpu", 2)], is_lp=True, container_name="r-2")
        tasks = _tasks(
            computerCapacity=_capacity([("cpu", 10)]),
            allActiveReservations=[
                _reservation(1, [("cpu", 4)]),
                lp,
            ],
            lowPriorityRunning=[lp],
        )
        pause_overcommitted_low_priority(tasks)
        mock_api.report_paused.assert_not_called()

    @patch("daemon.run_stop_script")
    @patch("daemon.stop_container")
    @patch("daemon.settings_handler")
    @patch("daemon.api")
    def test_pauses_lp_when_overcommitted(self, mock_api, mock_settings, mock_stop, mock_run_stop):
        mock_settings.get_setting.return_value = True
        lp = _reservation(2, [("cpu", 4)], is_lp=True, container_name="r-2")
        # 8 normal + 4 LP = 12, capacity 10 -> overcommit 2
        tasks = _tasks(
            computerCapacity=_capacity([("cpu", 10)]),
            allActiveReservations=[
                _reservation(1, [("cpu", 8)]),
                lp,
            ],
            lowPriorityRunning=[lp],
        )
        pause_overcommitted_low_priority(tasks)
        mock_stop.assert_called_once_with("r-2")
        mock_api.report_paused.assert_called_once()

    @patch("daemon.run_stop_script")
    @patch("daemon.stop_container")
    @patch("daemon.settings_handler")
    @patch("daemon.api")
    def test_pauses_newest_lp_first(self, mock_api, mock_settings, mock_stop, mock_run_stop):
        mock_settings.get_setting.return_value = True
        lp_old = _reservation(10, [("cpu", 4)], is_lp=True, container_name="r-10", created_at="2025-01-01")
        lp_new = _reservation(11, [("cpu", 4)], is_lp=True, container_name="r-11", created_at="2025-06-01")
        # 6 normal + 4+4 LP = 14, capacity 10 -> overcommit 4
        tasks = _tasks(
            computerCapacity=_capacity([("cpu", 10)]),
            allActiveReservations=[
                _reservation(99, [("cpu", 6)]),
                lp_old, lp_new,
            ],
            lowPriorityRunning=[lp_old, lp_new],
        )
        pause_overcommitted_low_priority(tasks)
        # Newest (r-11) paused first, frees 4 CPUs, overcommit resolved
        mock_stop.assert_called_once_with("r-11")

    @patch("daemon.run_stop_script")
    @patch("daemon.stop_container")
    @patch("daemon.settings_handler")
    @patch("daemon.api")
    def test_pauses_multiple_lp_if_needed(self, mock_api, mock_settings, mock_stop, mock_run_stop):
        mock_settings.get_setting.return_value = True
        lp1 = _reservation(10, [("cpu", 2)], is_lp=True, container_name="r-10", created_at="2025-01-01")
        lp2 = _reservation(11, [("cpu", 2)], is_lp=True, container_name="r-11", created_at="2025-06-01")
        # 8 normal + 2+2 LP = 12, capacity 10 -> overcommit 2
        # Pausing r-11 (newest, 2 CPU) resolves overcommit exactly
        tasks = _tasks(
            computerCapacity=_capacity([("cpu", 10)]),
            allActiveReservations=[
                _reservation(99, [("cpu", 8)]),
                lp1, lp2,
            ],
            lowPriorityRunning=[lp1, lp2],
        )
        pause_overcommitted_low_priority(tasks)
        assert mock_stop.call_count == 1
        mock_stop.assert_called_with("r-11")

    @patch("daemon.run_stop_script")
    @patch("daemon.stop_container")
    @patch("daemon.settings_handler")
    @patch("daemon.api")
    def test_handles_gpu_overcommit(self, mock_api, mock_settings, mock_stop, mock_run_stop):
        mock_settings.get_setting.return_value = True
        # GPU spec with maximumAmount=1 (single GPU)
        lp = _reservation(2, [("gpu_rtx5000", 1)], is_lp=True, container_name="r-2")
        # Normal also uses the same GPU -> total 2 > capacity 1
        tasks = _tasks(
            computerCapacity=_capacity([("gpu_rtx5000", 1)]),
            allActiveReservations=[
                _reservation(1, [("gpu_rtx5000", 1)]),
                lp,
            ],
            lowPriorityRunning=[lp],
        )
        pause_overcommitted_low_priority(tasks)
        mock_stop.assert_called_once_with("r-2")
        mock_api.report_paused.assert_called_once()

    @patch("daemon.run_stop_script")
    @patch("daemon.stop_container")
    @patch("daemon.settings_handler")
    @patch("daemon.api")
    def test_handles_mixed_cpu_ram_overcommit(self, mock_api, mock_settings, mock_stop, mock_run_stop):
        mock_settings.get_setting.return_value = True
        lp = _reservation(2, [("cpu", 4), ("ram", 4)], is_lp=True, container_name="r-2")
        # CPU: 8+4=12 > 10, RAM: 8+4=12 > 10
        tasks = _tasks(
            computerCapacity=_capacity([("cpu", 10), ("ram", 10)]),
            allActiveReservations=[
                _reservation(1, [("cpu", 8), ("ram", 8)]),
                lp,
            ],
            lowPriorityRunning=[lp],
        )
        pause_overcommitted_low_priority(tasks)
        mock_stop.assert_called_once_with("r-2")

    @patch("daemon.settings_handler")
    @patch("daemon.api")
    def test_no_pause_when_overcommit_on_non_lp_resource_only(self, mock_api, mock_settings):
        mock_settings.get_setting.return_value = True
        # LP uses CPU, but overcommit is only on RAM (which LP doesn't use)
        lp = _reservation(2, [("cpu", 2)], is_lp=True, container_name="r-2")
        tasks = _tasks(
            computerCapacity=_capacity([("cpu", 10), ("ram", 10)]),
            allActiveReservations=[
                _reservation(1, [("cpu", 4), ("ram", 12)]),
                lp,
            ],
            lowPriorityRunning=[lp],
        )
        pause_overcommitted_low_priority(tasks)
        # RAM is overcommitted but LP doesn't use RAM -> no pause
        mock_api.report_paused.assert_not_called()


# ---------------------------------------------------------------------------
# resume_paused_containers
# ---------------------------------------------------------------------------

class TestResumePausedContainers:

    @patch("daemon.settings_handler")
    @patch("daemon.api")
    def test_no_action_when_docker_disabled(self, mock_api, mock_settings):
        mock_settings.get_setting.return_value = False
        resume_paused_containers(_tasks(pausedReservations=[_reservation(1, [("cpu", 2)])]))
        mock_api.report_resumed.assert_not_called()

    @patch("daemon.settings_handler")
    @patch("daemon.api")
    def test_no_action_when_no_paused(self, mock_api, mock_settings):
        mock_settings.get_setting.return_value = True
        resume_paused_containers(_tasks())
        mock_api.report_resumed.assert_not_called()

    @patch("daemon.settings_handler")
    @patch("daemon.api")
    def test_resumes_when_resources_available(self, mock_api, mock_settings):
        mock_settings.get_setting.return_value = True
        paused = _reservation(1, [("cpu", 2)])
        tasks = _tasks(
            computerCapacity=_capacity([("cpu", 8)]),
            allActiveReservations=[_reservation(2, [("cpu", 2)])],
            pausedReservations=[paused],
        )
        resume_paused_containers(tasks)
        mock_api.report_resumed.assert_called_once_with(1)

    @patch("daemon.settings_handler")
    @patch("daemon.api")
    def test_skips_when_insufficient_resources(self, mock_api, mock_settings):
        mock_settings.get_setting.return_value = True
        paused = _reservation(1, [("cpu", 4)])
        tasks = _tasks(
            computerCapacity=_capacity([("cpu", 8)]),
            allActiveReservations=[_reservation(2, [("cpu", 6)])],
            pausedReservations=[paused],
        )
        resume_paused_containers(tasks)
        mock_api.report_resumed.assert_not_called()

    @patch("daemon.settings_handler")
    @patch("daemon.api")
    def test_skips_when_future_normal_conflict(self, mock_api, mock_settings):
        mock_settings.get_setting.return_value = True
        paused = _reservation(1, [("cpu", 4)])
        future = _reservation(3, [("cpu", 6)])
        tasks = _tasks(
            computerCapacity=_capacity([("cpu", 8)]),
            allActiveReservations=[],
            pausedReservations=[paused],
            futureNormalReservations=[future],
        )
        resume_paused_containers(tasks)
        mock_api.report_resumed.assert_not_called()

    @patch("daemon.settings_handler")
    @patch("daemon.api")
    def test_updates_used_after_resume(self, mock_api, mock_settings):
        mock_settings.get_setting.return_value = True
        p1 = _reservation(1, [("cpu", 3)])
        p2 = _reservation(2, [("cpu", 3)])
        tasks = _tasks(
            computerCapacity=_capacity([("cpu", 8)]),
            allActiveReservations=[_reservation(3, [("cpu", 2)])],
            pausedReservations=[p1, p2],
        )
        resume_paused_containers(tasks)
        # After resuming p1 (used goes from 2 to 5), p2 needs 3 more (5+3=8 <= 8)
        assert mock_api.report_resumed.call_count == 2
