"""Container server daemon -- manages Docker container lifecycle via REST API.

Polls the backend API every 10 seconds for reservation state changes and
performs Docker operations accordingly. Communicates exclusively through
the backend REST API instead of direct database access.
"""

from time import sleep
from datetime import timezone, datetime, timedelta
import sys

from helpers.logger import log
from helpers.settings_handler import settings_handler
from api_client import DaemonApiClient
from helpers.utils import create_password

from docker.containers import start_container, stop_container, restart_container, run_stop_script
from docker.monitoring import collect_server_metrics, collect_server_logs
from docker.ports import get_available_port, is_port_in_use
from docker.image_builder import build_and_push_image, remove_image, update_all_image_sizes
from docker.ssh_host_keys import ensure_host_keys

# Global state
run: bool = True
computer_id: int = None
api: DaemonApiClient = None


def time_now():
    """Return the current UTC datetime."""
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Daemon main loop
# ---------------------------------------------------------------------------

def main():
    """Run the daemon's main polling loop.

    Fetches all tasks from the backend API in a single call per cycle,
    then processes each task category. Server monitoring is updated every
    30 seconds, and orphan container cleanup runs every 60 seconds.
    """
    while run:
        for i in range(6):
            try:
                tasks = api.get_tasks()
                if tasks is None:
                    log.warning("Failed to fetch tasks from backend, skipping cycle")
                    sleep(10)
                    continue

                pause_low_priority_for_normal_reservations(tasks)
                pause_lower_lp_for_higher_lp(tasks)
                pause_overcommitted_low_priority(tasks)
                stop_finished_servers(tasks)
                start_new_servers(tasks)
                resume_paused_containers(tasks)
                restart_crashed_servers(tasks)
                restart_servers_requiring_restart(tasks)
                process_image_builds(tasks)
                process_image_removals(tasks)

            except Exception as e:
                log.error(f"Error in main loop iteration: {e}")

            # Update monitoring data every 3rd iteration (every 30 seconds)
            if i % 3 == 0:
                submit_monitoring()

            sleep(10)
        # Run orphan cleanup every 60 seconds
        stop_orphan_container_reservations()


# ---------------------------------------------------------------------------
# Lifecycle handlers
# ---------------------------------------------------------------------------

def stop_finished_servers(tasks):
    """Stop containers whose reservations have ended."""
    if not settings_handler.get_setting("docker.enabled"):
        return

    stop_timeout = tasks.get("stopScriptTimeoutSeconds", 40)
    for res in tasks.get("reservationsToStop", []):
        try:
            stop_docker_container(res, stop_timeout)
        except Exception as e:
            log.error(f"Error stopping container for reservation {res['reservationId']}: {e}")


def start_new_servers(tasks):
    """Start containers for reservations that are due to begin."""
    if not settings_handler.get_setting("docker.enabled"):
        return

    for res in tasks.get("reservationsToStart", []):
        try:
            start_docker_container(res, tasks)
        except Exception as e:
            log.error(f"Error starting container for reservation {res['reservationId']}: {e}")


def restart_crashed_servers(tasks):
    """Restart containers that have exited unexpectedly."""
    if not settings_handler.get_setting("docker.enabled"):
        return

    for res in tasks.get("runningReservations", []):
        try:
            rc = res.get("reservedContainer", {})
            container_docker_name = rc.get("containerDockerName") if rc else None
            if not container_docker_name:
                continue

            from python_on_whales import docker
            try:
                container_state = docker.container.inspect(container_docker_name)
                if container_state.state.status == "exited":
                    log.warning(f"Container exited unexpectedly for reservation {res['reservationId']}, restarting")
                    restart_docker_container(res)
            except Exception:
                pass  # Container may not exist
        except Exception as e:
            log.error(f"Error checking crashed container for reservation {res['reservationId']}: {e}")


def restart_servers_requiring_restart(tasks):
    """Restart containers that have been flagged for restart."""
    if not settings_handler.get_setting("docker.enabled"):
        return

    for res in tasks.get("reservationsToRestart", []):
        try:
            restart_docker_container(res)
        except Exception as e:
            log.error(f"Error restarting container for reservation {res['reservationId']}: {e}")


def process_image_builds(tasks):
    """Build Docker images for containers with pending build requests."""
    for container_data in tasks.get("containersToBuild", []):
        container_id = container_data["containerId"]
        image_name = container_data["imageName"]
        log.info(f"Building image for container {container_id} ({image_name})")
        try:
            build_and_push_image(container_data, api)
        except Exception as e:
            log.error(f"Error building image for container {container_id} ({image_name}): {e}")


def process_image_removals(tasks):
    """Remove Docker images for containers that have been deleted."""
    for container_data in tasks.get("containersToRemove", []):
        container_id = container_data["containerId"]
        image_name = container_data["imageName"]
        log.info(f"Removing image for container {container_id} ({image_name})")
        try:
            remove_image(container_data, api)
        except Exception as e:
            log.error(f"Error removing image for container {container_id} ({image_name}): {e}")


def pause_low_priority_for_normal_reservations(tasks):
    """Pause running low-priority containers to free resources for normal reservations.

    For each pending normal reservation, compute resources used by every other
    active reservation (LP + normal, started + reserved) and pause LP if the
    pending normal would otherwise overcommit. Same accounting as
    _are_resources_available(), so the pause happens in the same cycle as the
    start — avoiding the brief overcommit window that would otherwise be
    cleaned up by pause_overcommitted_low_priority one cycle later.
    """
    if not settings_handler.get_setting("docker.enabled"):
        return

    normal_pending = tasks.get("normalPendingReservations", [])
    if not normal_pending:
        return

    lp_running = tasks.get("lowPriorityRunning", [])
    if not lp_running:
        return

    computer_capacity = tasks.get("computerCapacity", {})
    all_active = tasks.get("allActiveReservations", [])

    try:
        total_capacity = {}
        for spec in computer_capacity.get("hardwareSpecs", []):
            total_capacity[spec["hardwareSpecId"]] = spec["maximumAmount"]

        for normal_res in normal_pending:
            needed = {}
            for spec in normal_res.get("reservedHardwareSpecs", []):
                needed[spec["hardwareSpecId"]] = spec["amount"]

            # Used by every other active reservation, including LP. Excluding
            # self avoids double-counting the pending normal's own demand
            # against itself in the deficit formula.
            used = {}
            for res in all_active:
                if res.get("reservationId") == normal_res.get("reservationId"):
                    continue
                for spec in res.get("reservedHardwareSpecs", []):
                    sid = spec["hardwareSpecId"]
                    used[sid] = used.get(sid, 0) + spec["amount"]

            deficit = {}
            for sid, amount in needed.items():
                available = total_capacity.get(sid, 0) - used.get(sid, 0)
                if amount > available:
                    deficit[sid] = amount - available

            if not deficit:
                continue

            # Pause LP containers. Order: lowest priority first (highest
            # lowPriorityLevel number), then newest first within the same
            # level (LIFO). This makes idle/background LP get paused before
            # standard LP when a normal reservation needs resources.
            lp_sorted = sorted(
                lp_running,
                key=lambda r: (r.get("lowPriorityLevel", 1), r.get("createdAt", "")),
                reverse=True,
            )
            to_pause = []

            for lp_res in lp_sorted:
                if not deficit:
                    break
                lp_specs = {}
                for spec in lp_res.get("reservedHardwareSpecs", []):
                    lp_specs[spec["hardwareSpecId"]] = spec["amount"]

                has_overlap = any(sid in lp_specs for sid in deficit)
                if not has_overlap:
                    continue

                to_pause.append(lp_res)
                for sid in list(deficit.keys()):
                    if sid in lp_specs:
                        deficit[sid] -= lp_specs[sid]
                        if deficit[sid] <= 0:
                            del deficit[sid]

            # Execute pauses
            for lp_res in to_pause:
                try:
                    rc = lp_res.get("reservedContainer", {})
                    container_docker_name = rc.get("containerDockerName") if rc else None
                    if container_docker_name:
                        stop_script = rc.get("stopScriptPath")
                        if stop_script:
                            container_data = lp_res.get("container", {})
                            container_username = (container_data.get("containerUsername") or "user") if container_data else "user"
                            run_stop_script(container_docker_name, stop_script, container_username, tasks.get("stopScriptTimeoutSeconds", 40))
                        stop_container(container_docker_name)

                    container_data = lp_res.get("container", {})
                    image_name = container_data.get("imageName", "unknown") if container_data else "unknown"
                    computer_name = lp_res.get("computer", {}).get("name", "unknown")

                    api.report_paused(lp_res["reservationId"], image_name, computer_name)
                    log.info(f"Low-priority reservation {lp_res['reservationId']} paused for normal reservation {normal_res['reservationId']}")

                    # Remove from running list and active list so resource
                    # checks later in this cycle see the freed capacity.
                    if lp_res in lp_running:
                        lp_running.remove(lp_res)
                    _remove_from_active(tasks, lp_res["reservationId"])

                except Exception as e:
                    log.error(f"Error pausing low-priority reservation {lp_res['reservationId']}: {e}")

    except Exception as e:
        log.error(f"Error in pause_low_priority_for_normal_reservations: {e}")


def pause_overcommitted_low_priority(tasks):
    """Pause LP containers when total resource usage exceeds computer capacity.

    Unlike pause_low_priority_for_normal_reservations() which only reacts to
    pending normal reservations that can't start, this function detects
    overcommitment across all running containers (LP + normal) and pauses LP
    containers until total usage is back within capacity. This handles the
    case where Docker successfully started both normal and LP containers
    but their combined allocation exceeds the computer's limits.

    Works for CPUs, RAM, and GPUs — each GPU is a separate HardwareSpec
    with maximumAmount=1, so if an LP and normal reservation both use the
    same GPU, overcommit is detected and the LP container is paused.

    Args:
        tasks: The task bundle from the backend API containing
            lowPriorityRunning, computerCapacity, and allActiveReservations.
    """
    if not settings_handler.get_setting("docker.enabled"):
        return

    lp_running = tasks.get("lowPriorityRunning", [])
    if not lp_running:
        return

    computer_capacity = tasks.get("computerCapacity", {})
    all_active = tasks.get("allActiveReservations", [])

    try:
        # Build total capacity map
        total_capacity = {}
        for spec in computer_capacity.get("hardwareSpecs", []):
            total_capacity[spec["hardwareSpecId"]] = spec["maximumAmount"]

        # Calculate total resource usage across actually-running reservations.
        # Pending ("reserved") reservations are excluded — they aren't consuming
        # resources yet, so counting them would falsely flag overcommit and
        # cause the older running LP to be paused for a newer pending LP.
        # Pending LPs that can't fit are blocked by _are_resources_available
        # at start time instead.
        total_used = {}
        for res in all_active:
            if res.get("status") != "started":
                continue
            for spec in res.get("reservedHardwareSpecs", []):
                sid = spec["hardwareSpecId"]
                total_used[sid] = total_used.get(sid, 0) + spec["amount"]

        # Calculate overcommit per resource
        overcommit = {}
        for sid, used in total_used.items():
            capacity = total_capacity.get(sid, 0)
            if used > capacity:
                overcommit[sid] = used - capacity

        if not overcommit:
            return

        log.warning(f"Resource overcommit detected: {overcommit}")

        # Pause LP containers until overcommit resolved. Order matches
        # pause_low_priority_for_normal_reservations: lowest priority
        # (highest lowPriorityLevel) first, then newest first within tier.
        lp_sorted = sorted(
            lp_running,
            key=lambda r: (r.get("lowPriorityLevel", 1), r.get("createdAt", "")),
            reverse=True,
        )
        to_pause = []

        for lp_res in lp_sorted:
            if not overcommit:
                break
            lp_specs = {}
            for spec in lp_res.get("reservedHardwareSpecs", []):
                lp_specs[spec["hardwareSpecId"]] = spec["amount"]

            has_overlap = any(sid in lp_specs for sid in overcommit)
            if not has_overlap:
                continue

            to_pause.append(lp_res)
            for sid in list(overcommit.keys()):
                if sid in lp_specs:
                    overcommit[sid] -= lp_specs[sid]
                    if overcommit[sid] <= 0:
                        del overcommit[sid]

        # Execute pauses (same pattern as pause_low_priority_for_normal_reservations)
        for lp_res in to_pause:
            try:
                rc = lp_res.get("reservedContainer", {})
                container_docker_name = rc.get("containerDockerName") if rc else None
                if container_docker_name:
                    stop_script = rc.get("stopScriptPath")
                    if stop_script:
                        container_data = lp_res.get("container", {})
                        container_username = (container_data.get("containerUsername") or "user") if container_data else "user"
                        run_stop_script(container_docker_name, stop_script, container_username, tasks.get("stopScriptTimeoutSeconds", 40))
                    stop_container(container_docker_name)

                container_data = lp_res.get("container", {})
                image_name = container_data.get("imageName", "unknown") if container_data else "unknown"
                computer_name = lp_res.get("computer", {}).get("name", "unknown")

                api.report_paused(lp_res["reservationId"], image_name, computer_name)
                log.info(f"Overcommitted low-priority reservation {lp_res['reservationId']} paused")

                if lp_res in lp_running:
                    lp_running.remove(lp_res)
                _remove_from_active(tasks, lp_res["reservationId"])

            except Exception as e:
                log.error(f"Error pausing overcommitted LP reservation {lp_res['reservationId']}: {e}")

    except Exception as e:
        log.error(f"Error in pause_overcommitted_low_priority: {e}")


def pause_lower_lp_for_higher_lp(tasks):
    """Pause running low-priority containers to free resources for higher-priority
    low-priority reservations.

    Mirrors pause_low_priority_for_normal_reservations(), but operates within
    the low-priority class: an LP at level N preempts running LP at level > N.
    This is what lets an "Idle" LLM reservation (level 3) yield when a
    "Standard" low-priority job (level 1) needs the server.

    Candidates considered: pending (status="reserved") LPs and paused LPs.
    Paused higher-priority LPs are included so they can preempt lower-priority
    running LPs and then be resumed by resume_paused_containers later in the
    same cycle — otherwise a paused Standard LP would sit forever while
    lower-priority Idle LPs hold the resources it needs.

    Args:
        tasks: The task bundle from the backend API containing
            lowPriorityPendingReservations, pausedReservations,
            lowPriorityRunning, computerCapacity, and allActiveReservations.
    """
    if not settings_handler.get_setting("docker.enabled"):
        return

    lp_pending = tasks.get("lowPriorityPendingReservations", [])
    paused_lp = [
        p for p in tasks.get("pausedReservations", [])
        if p.get("isLowPriority", False)
    ]
    candidates = list(lp_pending) + paused_lp
    if not candidates:
        return

    lp_running = tasks.get("lowPriorityRunning", [])
    if not lp_running:
        return

    computer_capacity = tasks.get("computerCapacity", {})
    all_active = tasks.get("allActiveReservations", [])

    try:
        # Process highest-priority (lowest level number) candidate first
        candidates_sorted = sorted(
            candidates,
            key=lambda r: (r.get("lowPriorityLevel", 1), r.get("createdAt", "")),
        )

        total_capacity = {}
        for spec in computer_capacity.get("hardwareSpecs", []):
            total_capacity[spec["hardwareSpecId"]] = spec["maximumAmount"]

        for candidate_res in candidates_sorted:
            candidate_level = candidate_res.get("lowPriorityLevel", 1)

            # Lower-priority LP still running that this candidate can preempt
            preemptable = [
                r for r in lp_running
                if r.get("lowPriorityLevel", 1) > candidate_level
            ]
            if not preemptable:
                continue

            # Compute current usage from actually-running reservations only.
            # Pending ("reserved") reservations — including the pending higher-
            # priority LP itself — are excluded so the deficit formula
            # (needed + used - capacity) doesn't double-count `needed` into
            # `used` and over-pause lower-priority LP.
            used = {}
            for res in all_active:
                if res.get("status") != "started":
                    continue
                for spec in res.get("reservedHardwareSpecs", []):
                    sid = spec["hardwareSpecId"]
                    used[sid] = used.get(sid, 0) + spec["amount"]

            needed = {}
            for spec in candidate_res.get("reservedHardwareSpecs", []):
                needed[spec["hardwareSpecId"]] = spec["amount"]

            resources_ok = True
            for sid, amount in needed.items():
                available = total_capacity.get(sid, 0) - used.get(sid, 0)
                if amount > available:
                    resources_ok = False
                    break
            if resources_ok:
                continue

            deficit = {}
            for sid, amount in needed.items():
                available = total_capacity.get(sid, 0) - used.get(sid, 0)
                if amount > available:
                    deficit[sid] = amount - available

            # Pause lower-priority LP: lowest priority (highest level)
            # first, newest first within the same level.
            preemptable_sorted = sorted(
                preemptable,
                key=lambda r: (r.get("lowPriorityLevel", 1), r.get("createdAt", "")),
                reverse=True,
            )
            to_pause = []

            for lp_res in preemptable_sorted:
                if not deficit:
                    break
                lp_specs = {}
                for spec in lp_res.get("reservedHardwareSpecs", []):
                    lp_specs[spec["hardwareSpecId"]] = spec["amount"]

                has_overlap = any(sid in lp_specs for sid in deficit)
                if not has_overlap:
                    continue

                to_pause.append(lp_res)
                for sid in list(deficit.keys()):
                    if sid in lp_specs:
                        deficit[sid] -= lp_specs[sid]
                        if deficit[sid] <= 0:
                            del deficit[sid]

            for lp_res in to_pause:
                try:
                    rc = lp_res.get("reservedContainer", {})
                    container_docker_name = rc.get("containerDockerName") if rc else None
                    if container_docker_name:
                        stop_script = rc.get("stopScriptPath")
                        if stop_script:
                            container_data = lp_res.get("container", {})
                            container_username = (container_data.get("containerUsername") or "user") if container_data else "user"
                            run_stop_script(container_docker_name, stop_script, container_username, tasks.get("stopScriptTimeoutSeconds", 40))
                        stop_container(container_docker_name)

                    container_data = lp_res.get("container", {})
                    image_name = container_data.get("imageName", "unknown") if container_data else "unknown"
                    computer_name = lp_res.get("computer", {}).get("name", "unknown")

                    api.report_paused(lp_res["reservationId"], image_name, computer_name)
                    log.info(
                        f"Low-priority reservation {lp_res['reservationId']} (level "
                        f"{lp_res.get('lowPriorityLevel', 1)}) paused for higher-priority "
                        f"low-priority reservation {candidate_res['reservationId']} "
                        f"(level {candidate_level})"
                    )

                    if lp_res in lp_running:
                        lp_running.remove(lp_res)
                    _remove_from_active(tasks, lp_res["reservationId"])

                except Exception as e:
                    log.error(f"Error pausing LP-vs-LP reservation {lp_res['reservationId']}: {e}")

    except Exception as e:
        log.error(f"Error in pause_lower_lp_for_higher_lp: {e}")



def resume_paused_containers(tasks):
    """Resume paused low-priority containers when resources become available."""
    if not settings_handler.get_setting("docker.enabled"):
        return

    paused = tasks.get("pausedReservations", [])
    if not paused:
        return

    try:
        computer_capacity = tasks.get("computerCapacity", {})
        all_active = tasks.get("allActiveReservations", [])
        future_normal = tasks.get("futureNormalReservations", [])
        future_low_priority = tasks.get("futureLowPriorityReservations", [])

        total_capacity = {}
        for spec in computer_capacity.get("hardwareSpecs", []):
            total_capacity[spec["hardwareSpecId"]] = spec["maximumAmount"]

        used = {}
        for res in all_active:
            for spec in res.get("reservedHardwareSpecs", []):
                sid = spec["hardwareSpecId"]
                used[sid] = used.get(sid, 0) + spec["amount"]

        # Resume in priority order: highest priority (lowest level number)
        # first, then oldest first within the same level (FIFO).
        paused_sorted = sorted(
            paused,
            key=lambda r: (r.get("lowPriorityLevel", 1), r.get("createdAt", "")),
        )

        for paused_res in paused_sorted:
            needed = {}
            for spec in paused_res.get("reservedHardwareSpecs", []):
                needed[spec["hardwareSpecId"]] = spec["amount"]

            # Check if resources are available
            resources_ok = True
            for sid, amount in needed.items():
                available = total_capacity.get(sid, 0) - used.get(sid, 0)
                if amount > available:
                    resources_ok = False
                    break

            if not resources_ok:
                continue

            my_level = paused_res.get("lowPriorityLevel", 1)

            # Look-ahead: don't resume if a higher-priority reservation is
            # about to need these resources. Normal reservations always
            # outrank LP. Future LP only outrank this candidate if their
            # level is strictly lower than mine.
            higher_priority_future = list(future_normal)
            for future_lp in future_low_priority:
                if future_lp.get("reservationId") == paused_res.get("reservationId"):
                    continue
                if future_lp.get("lowPriorityLevel", 1) < my_level:
                    higher_priority_future.append(future_lp)

            would_conflict = False
            for future_res in higher_priority_future:
                for f_spec in future_res.get("reservedHardwareSpecs", []):
                    f_sid = f_spec["hardwareSpecId"]
                    if f_sid in needed:
                        future_needed = f_spec["amount"]
                        spec_available = total_capacity.get(f_sid, 0) - used.get(f_sid, 0)
                        if future_needed > (spec_available - needed.get(f_sid, 0)):
                            would_conflict = True
                            break
                if would_conflict:
                    break

            if would_conflict:
                log.debug(f"Skipping resume of paused reservation {paused_res['reservationId']}: would conflict with upcoming higher-priority reservation")
                continue

            # Resume
            api.report_resumed(paused_res["reservationId"])
            log.info(f"Resuming paused low-priority reservation {paused_res['reservationId']}")

            # Update used resources for subsequent iterations
            for sid, amount in needed.items():
                used[sid] = used.get(sid, 0) + amount

    except Exception as e:
        log.error(f"Error in resume_paused_containers: {e}")


def stop_orphan_container_reservations():
    """Clean up Docker containers that have no matching active reservation."""
    try:
        known_names = api.get_orphan_check()

        from python_on_whales import docker
        running_containers = docker.ps()
        reservation_containers = [c for c in running_containers if c.name.startswith("reservation-")]

        for container in reservation_containers:
            time_running = datetime.now(timezone.utc) - container.state.started_at
            if time_running > timedelta(minutes=30):
                if container.name not in known_names:
                    log.warning(f"Orphan container detected: {container.name}, stopping it")
                    try:
                        stop_container(container.name)
                        log.info(f"Orphan container stopped: {container.name}")
                    except Exception as e:
                        log.error(f"Error stopping orphan container {container.name}: {e}")
    except Exception as e:
        log.error(f"Error in orphan container cleanup: {e}")


# ---------------------------------------------------------------------------
# Orchestration functions
# ---------------------------------------------------------------------------

def start_docker_container(res, tasks):
    """Build configuration and start a Docker container for a reservation.

    Args:
        res: Reservation dict from the tasks API response.
        tasks: Full tasks bundle for resource checking.
    """
    reservation_id = res["reservationId"]

    # Guard: if low-priority, verify resources are available
    if res.get("isLowPriority", False):
        if not _are_resources_available(res, tasks):
            api.report_paused(reservation_id,
                              res.get("container", {}).get("imageName", "unknown"),
                              res.get("computer", {}).get("name", "unknown"))
            log.info(f"Low-priority reservation {reservation_id} paused: insufficient resources")
            return

    container_data = res.get("container", {})
    if not container_data:
        api.report_start_failed(reservation_id, "Container data not found")
        return

    # Guard: if container has Dockerfile commands but hasn't been built
    if container_data.get("dockerfileCommands") and container_data.get("buildStatus") != "success":
        api.report_start_failed(reservation_id,
                                "Container image has not been built successfully. Please ask an admin to build the image first.")
        return

    ssh_password = create_password()
    image_name = container_data.get("imageName", "")
    hw_specs = {}
    gpu_specs = {}
    for spec in res.get("reservedHardwareSpecs", []):
        hs = spec.get("hardwareSpec", {})
        if hs.get("type") == "gpu":
            gpu_specs[hs.get("internalId")] = {"amount": spec["amount"]}
        else:
            hw_specs[hs.get("type")] = {"amount": spec["amount"]}

    time_now_parsed = time_now().strftime('%m_%d_%Y_%H_%M_%S')
    container_name = f"reservation-{reservation_id}-{image_name.replace(':', '').replace('/', '')}-{time_now_parsed}"

    # Detect resume: containerStatus is still "paused" on the ReservedContainer
    # even though the reservation was flipped back to "reserved". On a resume
    # we prefer to restart the container on the *same* outside ports it had
    # before the pause, so users' existing SSH configs and tunnels keep
    # working.
    rc_data = res.get("reservedContainer", {}) or {}
    is_resume = rc_data.get("containerStatus") == "paused"
    existing_ports = rc_data.get("reservedContainerPorts", []) or []

    # Held ports from paused LP reservations on this computer. The allocator
    # soft-excludes these so normal reservations don't casually grab them;
    # if the port range is genuinely exhausted, the allocator falls back
    # and returns stolen=True for the entries it had to take.
    held_entries = tasks.get("heldLowPriorityPorts", []) or []
    # A resume's own held ports are its reservedContainerPorts — don't soft-
    # exclude against ourselves, since we want to reuse those.
    own_port_ids = {ep.get("reservedContainerPortId") for ep in existing_ports}
    held_by_port: dict[int, dict] = {
        e["outsidePort"]: e
        for e in held_entries
        if e.get("reservedContainerPortId") not in own_port_ids
    }

    ports = []
    stolen_port_ids: list[int] = []
    reuse_existing_ports = False

    # Resume fast path: if every previously held outside port is still free
    # at the OS level, restart on those exact ports. All-or-nothing — any
    # conflict falls through to full reallocation (which is today's
    # behavior and is still handled correctly by the backend).
    if is_resume and existing_ports:
        can_reuse_all = all(not is_port_in_use(ep["outsidePort"]) for ep in existing_ports)
        if can_reuse_all:
            # Build the same shape the allocation loop produces, but from
            # the preserved mappings instead of fresh allocations.
            port_def_by_id = {
                pd["containerPortId"]: pd
                for pd in container_data.get("containerPorts", [])
            }
            for ep in existing_ports:
                pd = port_def_by_id.get(ep["containerPortId"])
                if pd is None:
                    # The container definition changed since the pause
                    # (e.g. a port was removed in the admin UI). Give up
                    # on reuse and fall through to fresh allocation.
                    ports = []
                    reuse_existing_ports = False
                    break
                ports.append({
                    "containerPortId": pd["containerPortId"],
                    "serviceName": pd["serviceName"],
                    "localPort": pd["port"],
                    "outsidePort": ep["outsidePort"],
                })
            else:
                reuse_existing_ports = True

    # Fresh allocation path (new start, or resume where reuse failed).
    if not reuse_existing_ports:
        ports = []
        ports_taken: set[int] = set()
        soft_exclude = set(held_by_port.keys())
        for port_def in container_data.get("containerPorts", []):
            result = get_available_port(
                exclude=ports_taken,
                soft_exclude=soft_exclude - ports_taken,
            )
            outside_port = result["port"]
            ports_taken.add(outside_port)
            if result["stolen"]:
                held = held_by_port.get(outside_port)
                if held:
                    stolen_port_ids.append(held["reservedContainerPortId"])
            ports.append({
                "containerPortId": port_def["containerPortId"],
                "serviceName": port_def["serviceName"],
                "localPort": port_def["port"],
                "outsidePort": outside_port,
            })

    # Build GPU string
    gpus_string = ""
    if gpu_specs:
        gpus_string = "device=" + ",".join(gpu_specs.keys())

    # Build port tuples for Docker
    ports_for_container = [(p["outsidePort"], p["localPort"]) for p in ports]

    rc = res.get("reservedContainer", {}) or {}
    details = {
        "name": container_name,
        "image": image_name,
        "username": container_data.get("containerUsername") or "user",
        "cpus": int(hw_specs.get("cpus", {}).get("amount", 1)),
        "gpus": gpus_string if gpus_string else None,
        "memory": f"{hw_specs.get('ram', {}).get('amount', 1)}g",
        "shm_size_percent": rc.get("shmSizePercent", 50),
        "ram_disk_percent": rc.get("ramDiskSizePercent", 0),
        "ports": ports_for_container,
        "password": ssh_password,
        "dbUserId": res.get("userId"),
        "reservation": {
            "computerId": res.get("computerId"),
            "user": {
                "email": res.get("user", {}).get("email", ""),
            },
        },
        "sshPublicKey": res.get("user", {}).get("sshPublicKey"),
        "passwordCommand": container_data.get("passwordCommand"),
        "sshKeyDeployCommands": container_data.get("sshKeyDeployCommands"),
        "startScriptPath": rc.get("startScriptPath"),
        "stopScriptPath": rc.get("stopScriptPath"),
        "startScriptTimeoutSeconds": tasks.get("startScriptTimeoutSeconds", 40),
        "stopScriptTimeoutSeconds": tasks.get("stopScriptTimeoutSeconds", 40),
    }

    # Build role mounts from user roles + everyone mounts
    role_mounts = list(tasks.get("everyoneMounts", []))
    user_data = res.get("user", {})
    for role in user_data.get("roles", []):
        for mount in role.get("mounts", []):
            mount_exists = any(
                existing["hostPath"] == mount["hostPath"]
                and existing["containerPath"] == mount["containerPath"]
                for existing in role_mounts
            )
            if not mount_exists:
                role_mounts.append(mount)
    details["roleMounts"] = role_mounts

    result = start_container(details)

    if result["started"]:
        log.info(f"Container started for reservation {reservation_id}, user={res.get('userId')}, image={image_name}, docker_name={result['containerName']}, resume_reused_ports={reuse_existing_ports}, stolen_ports={len(stolen_port_ids)}")
        # When reusing existing port rows on a resume, don't resend the
        # `ports` list — the backend keeps the existing rows and re-inserts
        # would violate the uniqueness constraint on (reservedContainerId,
        # outsidePort).
        ports_payload = (
            []
            if reuse_existing_ports
            else [{"containerPortId": p["containerPortId"], "outsidePort": p["outsidePort"]} for p in ports]
        )
        api.report_started(reservation_id, {
            "containerDockerName": container_name,
            "sshPassword": result["password"],
            "containerDockerId": result["containerId"] or "",
            "ports": ports_payload,
            "nonCriticalErrors": result["nonCriticalErrors"] or "",
            "stolenReservedContainerPortIds": stolen_port_ids,
            "reuseExistingPorts": reuse_existing_ports,
        })
    else:
        log.error(f"Failed to start container for reservation {reservation_id}: {result['error']}")
        api.report_start_failed(reservation_id, result["error"])


def stop_docker_container(res, stop_script_timeout=40):
    """Stop a Docker container and report to backend.

    Args:
        res: Reservation dict from the tasks API response.
        stop_script_timeout: Timeout in seconds for the stop script.
    """
    reservation_id = res["reservationId"]
    rc = res.get("reservedContainer", {}) or {}
    container_docker_name = rc.get("containerDockerName")
    status = res.get("status")

    try:
        if status in ("started", "restart_error", "stopping") and container_docker_name:
            stop_script = rc.get("stopScriptPath")
            if stop_script:
                container_data = res.get("container", {})
                container_username = (container_data.get("containerUsername") or "user") if container_data else "user"
                run_stop_script(container_docker_name, stop_script, container_username, stop_script_timeout)
            stop_container(container_docker_name)
        # Paused containers are already stopped in Docker, just finalize
        api.report_stopped(reservation_id)
        log.info(f"Container stopped for reservation {reservation_id}, docker_name={container_docker_name}")
    except Exception as e:
        log.error(f"Error stopping container for reservation {reservation_id}: {e}")
        # Still report stopped so it doesn't keep retrying
        api.report_stopped(reservation_id)


def restart_docker_container(res):
    """Restart a Docker container and report to backend.

    Args:
        res: Reservation dict from the tasks API response.
    """
    reservation_id = res["reservationId"]
    rc = res.get("reservedContainer", {}) or {}
    container_docker_name = rc.get("containerDockerName")

    try:
        restart_container(container_docker_name)
        api.report_restarted(reservation_id, success=True)
        log.info(f"Container restarted for reservation {reservation_id}, docker_name={container_docker_name}")
    except Exception as e:
        log.error(f"Error restarting container for reservation {reservation_id}: {e}")
        api.report_restarted(reservation_id, success=False, error_message=str(e))


def _remove_from_active(tasks, reservation_id):
    """Remove a reservation from the in-memory active/running views.

    Called immediately after a pause so subsequent resource checks in
    the same cycle see the freed capacity. The backend authoritative
    state is updated separately via api.report_paused().
    """
    active = tasks.get("allActiveReservations", [])
    tasks["allActiveReservations"] = [r for r in active if r.get("reservationId") != reservation_id]


def _are_resources_available(res, tasks):
    """Check if hardware resources are available for a reservation.

    Args:
        res: Reservation dict to check.
        tasks: Full tasks bundle with capacity and active reservations.

    Returns:
        bool: True if resources are available.
    """
    computer_capacity = tasks.get("computerCapacity", {})
    all_active = tasks.get("allActiveReservations", [])

    total_capacity = {}
    for spec in computer_capacity.get("hardwareSpecs", []):
        total_capacity[spec["hardwareSpecId"]] = spec["maximumAmount"]

    used = {}
    for active_res in all_active:
        if active_res["reservationId"] == res["reservationId"]:
            continue
        for spec in active_res.get("reservedHardwareSpecs", []):
            sid = spec["hardwareSpecId"]
            used[sid] = used.get(sid, 0) + spec["amount"]

    for spec in res.get("reservedHardwareSpecs", []):
        sid = spec["hardwareSpecId"]
        available = total_capacity.get(sid, 0) - used.get(sid, 0)
        if spec["amount"] > available:
            return False

    return True


# ---------------------------------------------------------------------------
# Monitoring
# ---------------------------------------------------------------------------

def submit_monitoring():
    """Collect and submit server metrics to the backend."""
    try:
        metrics = collect_server_metrics()
        logs = collect_server_logs()
        if logs:
            metrics["logs"] = logs
        api.submit_monitoring(metrics)
    except Exception as e:
        log.error(f"Error submitting monitoring data: {e}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run_daemon():
    """Initialize the daemon and start the main loop.

    Reads settings, creates the API client, resolves the computer ID,
    and enters the infinite main polling loop.
    """
    global computer_id, api

    log.info("Container server daemon started.")
    log.info("Waiting 3 seconds for backend to initialize...")
    sleep(3)
    log.info("This software will run infinitely and start / stop servers for reservations.")

    # Check Docker support
    if not settings_handler.get_setting("docker.enabled"):
        log.warning("Docker support has not been enabled. Enable it with settings.json setting docker.enabled: true")

    # Read settings for API client
    daemon_api_key = settings_handler.get_setting("daemon.apiKey")
    if not daemon_api_key:
        log.critical("daemon.apiKey not configured in settings.json. Exiting.")
        sys.exit(1)

    web_host = settings_handler.get_setting("app.webHost")
    web_https = settings_handler.get_setting("app.webHttps") or False

    server_name = settings_handler.get_setting("docker.serverName")
    if not server_name:
        log.critical("docker.serverName not specified in settings.json. Exiting.")
        sys.exit(1)

    # Create API client
    api = DaemonApiClient(web_host, web_https, daemon_api_key, server_name)

    # Resolve computer ID
    computer_id = api.get_computer_id(server_name)
    if not computer_id:
        log.critical(f"Could not find computer with name '{server_name}' from the backend. Exiting.")
        sys.exit(1)

    # Reset stale builds
    api.reset_stale_builds()

    # Update image sizes on startup
    update_all_image_sizes(api)

    # Ensure persistent SSH host keys exist
    host_keys_path = settings_handler.get_setting("docker.sshHostKeysPath")
    ensure_host_keys(host_keys_path)

    main()
