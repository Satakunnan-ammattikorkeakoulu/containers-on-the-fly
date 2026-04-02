"""Business logic for daemon API endpoints.

Handles the backend side of the daemon polling and action reporting cycle:
assembles task bundles for the daemon, processes status updates for
reservations and container images, and triggers email notifications.
"""

from datetime import datetime, timezone, timedelta
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from database import (
    Session, Reservation, ReservedContainer, ReservedContainerPort,
    ReservedHardwareSpec, HardwareSpec, Computer, Container, ContainerPort,
    User, Role, RoleMount, ServerStatus, ServerLogs,
)
from helpers.server import api_response, orm_to_dict
from helpers.email_notifications import (
    send_container_started_email, send_container_error_email,
    send_container_paused_email, send_container_resumed_email,
    send_admin_failure_alert,
)
from logger import log


def _time_now():
    """Return the current UTC datetime as a naive datetime.

    Uses a naive (timezone-unaware) datetime to match the format stored
    in the database by MariaDB/SQLAlchemy, avoiding comparison errors.
    """
    return datetime.utcnow()


def _serialize_reservation(res, include_container=False, include_user=False,
                           include_hardware=False, include_mounts=False):
    """Serialize a Reservation ORM object to a JSON-safe dict.

    Args:
        res: Reservation ORM object (must be within a session scope).
        include_container: Include container image details and ports.
        include_user: Include user email, SSH key, roles.
        include_hardware: Include reserved hardware specs.
        include_mounts: Include role mounts for the reservation's computer.

    Returns:
        Dict with reservation data.
    """
    data = {
        "reservationId": res.reservationId,
        "computerId": res.computerId,
        "userId": res.userId,
        "status": res.status,
        "startDate": res.startDate.isoformat() if res.startDate else None,
        "endDate": res.endDate.isoformat() if res.endDate else None,
        "isLowPriority": res.isLowPriority,
        "createdAt": res.createdAt.isoformat() if res.createdAt else None,
    }

    # Reserved container info
    rc = res.reservedContainer
    if rc:
        data["reservedContainer"] = {
            "reservedContainerId": rc.reservedContainerId,
            "containerId": rc.containerId,
            "containerDockerName": rc.containerDockerName,
            "containerStatus": rc.containerStatus,
            "containerDockerId": rc.containerDockerId,
            "sshPassword": rc.sshPassword,
            "containerDockerErrorMessage": rc.containerDockerErrorMessage,
            "shmSizePercent": rc.shmSizePercent,
            "ramDiskSizePercent": rc.ramDiskSizePercent,
            "startScriptPath": rc.startScriptPath,
            "stopScriptPath": rc.stopScriptPath,
        }
    else:
        data["reservedContainer"] = None

    if include_hardware:
        specs = []
        for s in res.reservedHardwareSpecs:
            spec_data = {
                "reservedHardwareSpecId": s.reservedHardwareSpecId,
                "hardwareSpecId": s.hardwareSpecId,
                "amount": s.amount,
            }
            if s.hardwareSpec:
                spec_data["hardwareSpec"] = {
                    "hardwareSpecId": s.hardwareSpec.hardwareSpecId,
                    "type": s.hardwareSpec.type,
                    "maximumAmount": s.hardwareSpec.maximumAmount,
                    "internalId": s.hardwareSpec.internalId,
                    "format": s.hardwareSpec.format,
                }
            specs.append(spec_data)
        data["reservedHardwareSpecs"] = specs

    if include_container and rc and rc.container:
        c = rc.container
        data["container"] = {
            "containerId": c.containerId,
            "imageName": c.imageName,
            "name": c.name,
            "dockerfileCommands": c.dockerfileCommands,
            "baseImage": c.baseImage,
            "buildStatus": c.buildStatus,
            "containerUsername": c.containerUsername,
            "passwordCommand": c.passwordCommand,
            "sshKeyDeployCommands": c.sshKeyDeployCommands,
            "containerCmd": c.containerCmd,
            "managedExternally": c.managedExternally,
            "containerPorts": [
                {
                    "containerPortId": p.containerPortId,
                    "serviceName": p.serviceName,
                    "port": p.port,
                }
                for p in c.containerPorts
            ],
        }

    if include_user and res.user:
        user_data = {
            "userId": res.user.userId,
            "email": res.user.email,
            "sshPublicKey": res.user.sshPublicKey,
            "startScriptPath": res.user.startScriptPath,
            "stopScriptPath": res.user.stopScriptPath,
        }
        if include_mounts:
            user_data["roles"] = []
            for role in res.user.roles:
                role_data = {
                    "roleId": role.roleId,
                    "name": role.name,
                    "mounts": [
                        {
                            "hostPath": m.hostPath,
                            "containerPath": m.containerPath,
                            "readOnly": m.readOnly,
                            "computerId": m.computerId,
                        }
                        for m in role.mounts
                        if m.computerId == res.computerId
                    ],
                }
                user_data["roles"].append(role_data)
        data["user"] = user_data

    if res.computer:
        data["computer"] = {
            "computerId": res.computer.computerId,
            "name": res.computer.name,
            "ip": res.computer.ip,
        }

    return data


# ---------------------------------------------------------------------------
# GET /api/daemon/tasks
# ---------------------------------------------------------------------------

def get_tasks(computer_id: int):
    """Assemble all actionable work for a single daemon polling cycle.

    Queries the database once with eager-loaded relationships and
    categorizes reservations by lifecycle state. Returns everything
    the daemon needs in one response.

    Args:
        computer_id: Database ID of the computer this daemon manages.

    Returns:
        API response with all task bundles for the daemon.
    """
    now = _time_now()
    look_ahead_end = now + timedelta(minutes=30)

    with Session() as session:
        # Load all reservations for this computer with relevant relations
        all_reservations = session.execute(
            select(Reservation)
            .options(
                joinedload(Reservation.reservedContainer).joinedload(ReservedContainer.container).joinedload(Container.containerPorts),
                joinedload(Reservation.reservedHardwareSpecs).joinedload(ReservedHardwareSpec.hardwareSpec),
                joinedload(Reservation.user).joinedload(User.roles).joinedload(Role.mounts),
                joinedload(Reservation.computer),
            )
            .where(Reservation.computerId == computer_id)
        ).unique().scalars().all()

        # Also load the "everyone" role mounts for this computer
        everyone_role = session.execute(
            select(Role)
            .options(joinedload(Role.mounts))
            .where(Role.name == "everyone")
        ).unique().scalar_one_or_none()

        everyone_mounts = []
        if everyone_role:
            everyone_mounts = [
                {
                    "hostPath": m.hostPath,
                    "containerPath": m.containerPath,
                    "readOnly": m.readOnly,
                    "computerId": m.computerId,
                }
                for m in everyone_role.mounts
                if m.computerId == computer_id
            ]

        # Categorize reservations
        reservations_to_start = []
        reservations_to_stop = []
        reservations_to_restart = []
        running_reservations = []
        paused_reservations = []
        normal_pending = []
        lp_running = []
        all_active = []
        future_normal = []

        for res in all_reservations:
            # To start: status=reserved, startDate < now
            if res.status == "reserved" and res.startDate < now:
                if res.isLowPriority:
                    reservations_to_start.append(
                        _serialize_reservation(res, include_container=True, include_user=True,
                                               include_hardware=True, include_mounts=True)
                    )
                else:
                    normal_pending.append(
                        _serialize_reservation(res, include_container=True, include_user=True,
                                               include_hardware=True, include_mounts=True)
                    )
                    reservations_to_start.append(
                        _serialize_reservation(res, include_container=True, include_user=True,
                                               include_hardware=True, include_mounts=True)
                    )

            # To stop: end date passed
            if res.status in ("started", "reserved", "restart_error", "paused") and res.endDate < now:
                reservations_to_stop.append(
                    _serialize_reservation(res, include_container=True)
                )

            # To restart: status=restart, not expired
            if res.status == "restart" and res.endDate > now:
                reservations_to_restart.append(
                    _serialize_reservation(res, include_container=True)
                )

            # Running: for crash detection
            if res.status == "started" and res.startDate < now and res.endDate > now:
                running_reservations.append(
                    _serialize_reservation(res, include_container=True)
                )

            # Paused: LP containers waiting to resume
            if res.status == "paused" and res.endDate > now:
                paused_reservations.append(
                    _serialize_reservation(res, include_container=True, include_user=True,
                                           include_hardware=True)
                )

            # LP running: for preemption logic
            if (res.status == "started" and res.isLowPriority
                    and res.endDate > now):
                lp_running.append(
                    _serialize_reservation(res, include_container=True, include_user=True,
                                           include_hardware=True)
                )

            # All active: for resource calculation
            if res.status in ("started", "reserved") and res.endDate > now:
                all_active.append(
                    _serialize_reservation(res, include_hardware=True)
                )

            # Future normal: for LP resume look-ahead
            if (not res.isLowPriority
                    and res.status in ("reserved", "started")
                    and res.startDate < look_ahead_end
                    and res.endDate > now):
                future_normal.append(
                    _serialize_reservation(res, include_hardware=True)
                )

        # Sort paused by createdAt ascending (FIFO)
        paused_reservations.sort(key=lambda r: r.get("createdAt", ""))

        # Computer hardware capacity
        computer = session.execute(
            select(Computer)
            .options(joinedload(Computer.hardwareSpecs))
            .where(Computer.computerId == computer_id)
        ).unique().scalar_one_or_none()

        computer_capacity = {}
        if computer:
            computer_capacity = {
                "computerId": computer.computerId,
                "name": computer.name,
                "ip": computer.ip,
                "hardwareSpecs": [
                    {
                        "hardwareSpecId": s.hardwareSpecId,
                        "type": s.type,
                        "maximumAmount": s.maximumAmount,
                        "internalId": s.internalId,
                        "format": s.format,
                    }
                    for s in computer.hardwareSpecs
                ],
            }

        # Containers to build/remove
        all_containers = session.execute(
            select(Container)
        ).scalars().all()

        containers_to_build = [
            {
                "containerId": c.containerId,
                "imageName": c.imageName,
                "baseImage": c.baseImage,
                "dockerfileCommands": c.dockerfileCommands,
                "containerUsername": c.containerUsername,
                "passwordCommand": c.passwordCommand,
                "sshKeyDeployCommands": c.sshKeyDeployCommands,
                "containerCmd": c.containerCmd,
            }
            for c in all_containers if c.buildStatus == "pending"
        ]

        containers_to_remove = [
            {
                "containerId": c.containerId,
                "imageName": c.imageName,
            }
            for c in all_containers if c.buildStatus == "removing"
        ]

        return api_response(True, "Tasks retrieved", {
            "reservationsToStart": reservations_to_start,
            "reservationsToStop": reservations_to_stop,
            "reservationsToRestart": reservations_to_restart,
            "runningReservations": running_reservations,
            "pausedReservations": paused_reservations,
            "normalPendingReservations": normal_pending,
            "lowPriorityRunning": lp_running,
            "allActiveReservations": all_active,
            "futureNormalReservations": future_normal,
            "computerCapacity": computer_capacity,
            "containersToBuild": containers_to_build,
            "containersToRemove": containers_to_remove,
            "everyoneMounts": everyone_mounts,
        })


# ---------------------------------------------------------------------------
# Action endpoints: reservation lifecycle
# ---------------------------------------------------------------------------

def report_started(reservation_id: int, data, computer_id: int):
    """Record that a container started successfully and send notification.

    Args:
        reservation_id: Database ID of the reservation.
        data: ReservationStartedRequest with container details.
        computer_id: The authenticated daemon's computer ID.

    Returns:
        API response.
    """
    with Session() as session:
        reservation = session.execute(
            select(Reservation)
            .options(
                joinedload(Reservation.reservedContainer).joinedload(ReservedContainer.container).joinedload(Container.containerPorts),
                joinedload(Reservation.user),
                joinedload(Reservation.computer),
            )
            .where(
                Reservation.reservationId == reservation_id,
                Reservation.computerId == computer_id,
            )
        ).unique().scalar_one_or_none()

        if not reservation:
            return api_response(False, "Reservation not found")

        rc = reservation.reservedContainer

        # Update reservation status
        reservation.status = "started"
        rc.containerDockerName = data.containerDockerName
        rc.sshPassword = data.sshPassword
        rc.startedAt = _time_now()
        rc.containerDockerId = data.containerDockerId
        rc.containerStatus = "running"

        # Create port mappings
        for port in data.ports:
            rc.reservedContainerPorts.append(ReservedContainerPort(
                outsidePort=port.outsidePort,
                containerPortForeign=port.containerPortId,
            ))

        session.commit()

        # Build port list for email
        container_obj = rc.container
        email_ports = []
        for port in data.ports:
            # Find the service name from the container's port definitions
            service_name = "Unknown"
            for cp in container_obj.containerPorts:
                if cp.containerPortId == port.containerPortId:
                    service_name = cp.serviceName
                    break
            email_ports.append({
                "serviceName": service_name,
                "localPort": None,
                "outsidePort": port.outsidePort,
            })

        # Send notification email
        send_container_started_email(
            reservation.user.email,
            container_obj.imageName,
            reservation.computer.ip,
            email_ports,
            data.sshPassword,
            data.nonCriticalErrors,
            reservation.endDate,
            container_obj.containerUsername or "user",
        )

        log.info(f"Container started for reservation {reservation_id}, user={reservation.userId}, docker_name={data.containerDockerName}")
        return api_response(True, "Reservation marked as started")


def report_start_failed(reservation_id: int, data, computer_id: int):
    """Record that a container failed to start and send error notifications.

    Args:
        reservation_id: Database ID of the reservation.
        data: ReservationStartFailedRequest with error details.
        computer_id: The authenticated daemon's computer ID.

    Returns:
        API response.
    """
    with Session() as session:
        reservation = session.execute(
            select(Reservation)
            .options(
                joinedload(Reservation.reservedContainer).joinedload(ReservedContainer.container),
                joinedload(Reservation.user),
                joinedload(Reservation.computer),
            )
            .where(
                Reservation.reservationId == reservation_id,
                Reservation.computerId == computer_id,
            )
        ).unique().scalar_one_or_none()

        if not reservation:
            return api_response(False, "Reservation not found")

        reservation.status = "error"
        reservation.reservedContainer.containerDockerErrorMessage = data.errorMessage
        reservation.reservedContainer.containerStatus = "error"
        session.commit()

        container_obj = reservation.reservedContainer.container
        image_name = container_obj.imageName if container_obj else "unknown"

        send_container_error_email(reservation.user.email, data.errorMessage)
        send_admin_failure_alert(
            reservation.user.email, reservation_id,
            image_name, reservation.computer.name, data.errorMessage,
        )

        log.error(f"Container start failed for reservation {reservation_id}: {data.errorMessage}")
        return api_response(True, "Reservation marked as error")


def report_stopped(reservation_id: int, computer_id: int):
    """Record that a container was stopped.

    Args:
        reservation_id: Database ID of the reservation.
        computer_id: The authenticated daemon's computer ID.

    Returns:
        API response.
    """
    with Session() as session:
        reservation = session.execute(
            select(Reservation)
            .options(joinedload(Reservation.reservedContainer))
            .where(
                Reservation.reservationId == reservation_id,
                Reservation.computerId == computer_id,
            )
        ).unique().scalar_one_or_none()

        if not reservation:
            return api_response(False, "Reservation not found")

        reservation.status = "stopped"
        reservation.reservedContainer.stoppedAt = _time_now()
        reservation.reservedContainer.containerStatus = "stopped"
        session.commit()

        log.info(f"Container stopped for reservation {reservation_id}")
        return api_response(True, "Reservation marked as stopped")


def report_paused(reservation_id: int, data, computer_id: int):
    """Record that a low-priority container was paused and notify user.

    Args:
        reservation_id: Database ID of the reservation.
        data: ReservationPausedRequest with image and computer names.
        computer_id: The authenticated daemon's computer ID.

    Returns:
        API response.
    """
    with Session() as session:
        reservation = session.execute(
            select(Reservation)
            .options(
                joinedload(Reservation.reservedContainer),
                joinedload(Reservation.user),
            )
            .where(
                Reservation.reservationId == reservation_id,
                Reservation.computerId == computer_id,
            )
        ).unique().scalar_one_or_none()

        if not reservation:
            return api_response(False, "Reservation not found")

        reservation.status = "paused"
        reservation.reservedContainer.stoppedAt = _time_now()
        reservation.reservedContainer.containerStatus = "paused"
        session.commit()

        send_container_paused_email(
            reservation.user.email, data.imageName,
            data.computerName, reservation_id,
        )

        log.info(f"Low-priority reservation {reservation_id} paused")
        return api_response(True, "Reservation marked as paused")


def report_resumed(reservation_id: int, computer_id: int):
    """Record that a paused container is ready to resume.

    Sets status back to "reserved" so the daemon picks it up for start
    on the next polling cycle. Sends resumed email after the container
    actually starts (via report_started).

    Args:
        reservation_id: Database ID of the reservation.
        computer_id: The authenticated daemon's computer ID.

    Returns:
        API response.
    """
    with Session() as session:
        reservation = session.execute(
            select(Reservation)
            .where(
                Reservation.reservationId == reservation_id,
                Reservation.computerId == computer_id,
            )
        ).scalar_one_or_none()

        if not reservation:
            return api_response(False, "Reservation not found")

        reservation.status = "reserved"
        session.commit()

        log.info(f"Paused reservation {reservation_id} set to reserved for resume")
        return api_response(True, "Reservation set to reserved for resume")


def report_restarted(reservation_id: int, data, computer_id: int):
    """Record the result of a container restart attempt.

    Args:
        reservation_id: Database ID of the reservation.
        data: ReservationRestartedRequest with success/error info.
        computer_id: The authenticated daemon's computer ID.

    Returns:
        API response.
    """
    with Session() as session:
        reservation = session.execute(
            select(Reservation)
            .options(joinedload(Reservation.reservedContainer))
            .where(
                Reservation.reservationId == reservation_id,
                Reservation.computerId == computer_id,
            )
        ).unique().scalar_one_or_none()

        if not reservation:
            return api_response(False, "Reservation not found")

        if data.success:
            reservation.status = "started"
            reservation.reservedContainer.containerStatus = "running"
            reservation.reservedContainer.containerDockerErrorMessage = ""
            log.info(f"Container restarted for reservation {reservation_id}")
        else:
            reservation.status = "restart_error"
            reservation.reservedContainer.containerStatus = "restart_error"
            reservation.reservedContainer.containerDockerErrorMessage = f"Container failed to restart: {data.errorMessage}"
            log.error(f"Container restart failed for reservation {reservation_id}: {data.errorMessage}")

        session.commit()
        return api_response(True, "Reservation restart status updated")


# ---------------------------------------------------------------------------
# Action endpoints: container images
# ---------------------------------------------------------------------------

def report_build_progress(container_id: int, data, computer_id: int):
    """Update build log during an image build.

    Args:
        container_id: Database ID of the container.
        data: BuildProgressRequest with build log and status.
        computer_id: The authenticated daemon's computer ID.

    Returns:
        API response.
    """
    with Session() as session:
        container = session.execute(
            select(Container).where(Container.containerId == container_id)
        ).scalar_one_or_none()

        if not container:
            return api_response(False, "Container not found")

        container.buildStatus = data.buildStatus
        container.buildLog = data.buildLog
        session.commit()

        return api_response(True, "Build progress updated")


def report_build_complete(container_id: int, data, computer_id: int):
    """Record the final result of an image build.

    Args:
        container_id: Database ID of the container.
        data: BuildCompleteRequest with final status, log, and size.
        computer_id: The authenticated daemon's computer ID.

    Returns:
        API response.
    """
    with Session() as session:
        container = session.execute(
            select(Container).where(Container.containerId == container_id)
        ).scalar_one_or_none()

        if not container:
            return api_response(False, "Container not found")

        container.buildStatus = data.buildStatus
        container.buildLog = data.buildLog
        if data.imageSize is not None:
            container.imageSize = data.imageSize
        if data.lastBuiltAt:
            container.lastBuiltAt = datetime.fromisoformat(data.lastBuiltAt)
        session.commit()

        log.info(f"Image build complete for container {container_id} ({container.imageName}): {data.buildStatus}")
        return api_response(True, "Build result recorded")


def report_image_removed(container_id: int, data, computer_id: int):
    """Record that a container image was removed from Docker.

    Args:
        container_id: Database ID of the container.
        data: ImageRemovedRequest with final build status.
        computer_id: The authenticated daemon's computer ID.

    Returns:
        API response.
    """
    with Session() as session:
        container = session.execute(
            select(Container).where(Container.containerId == container_id)
        ).scalar_one_or_none()

        if not container:
            return api_response(False, "Container not found")

        container.buildStatus = data.buildStatus
        container.imageSize = None
        session.commit()

        log.info(f"Image removed for container {container_id} ({container.imageName})")
        return api_response(True, "Image removal recorded")


def update_image_size(container_id: int, data, computer_id: int):
    """Update the stored image size for a container.

    Args:
        container_id: Database ID of the container.
        data: ImageSizeRequest with image size in bytes.
        computer_id: The authenticated daemon's computer ID.

    Returns:
        API response.
    """
    with Session() as session:
        container = session.execute(
            select(Container).where(Container.containerId == container_id)
        ).scalar_one_or_none()

        if not container:
            return api_response(False, "Container not found")

        container.imageSize = data.imageSize
        session.commit()

        return api_response(True, "Image size updated")


# ---------------------------------------------------------------------------
# Utility endpoints
# ---------------------------------------------------------------------------

def get_computer_id_by_name(server_name: str):
    """Resolve a server name to its computer ID.

    Args:
        server_name: Name of the computer as stored in the database.

    Returns:
        API response with the computer ID.
    """
    with Session() as session:
        computer = session.execute(
            select(Computer).where(Computer.name == server_name)
        ).scalar_one_or_none()

        if not computer:
            return api_response(False, f"Computer '{server_name}' not found")

        return api_response(True, "Computer found", {
            "computerId": computer.computerId,
        })


def get_orphan_check_data(computer_id: int):
    """Get running reservation docker container names for orphan detection.

    Args:
        computer_id: Database ID of the computer.

    Returns:
        API response with list of running container docker names.
    """
    with Session() as session:
        reservations = session.execute(
            select(Reservation)
            .options(joinedload(Reservation.reservedContainer))
            .where(
                Reservation.status == "started",
                Reservation.computerId == computer_id,
                Reservation.startDate < _time_now(),
                Reservation.endDate > _time_now(),
            )
        ).unique().scalars().all()

        container_names = [
            res.reservedContainer.containerDockerName
            for res in reservations
            if res.reservedContainer and res.reservedContainer.containerDockerName
        ]

        return api_response(True, "Orphan check data retrieved", {
            "runningContainerNames": container_names,
        })


def reset_stale_builds(computer_id: int):
    """Reset containers stuck in 'building' status back to 'pending'.

    Called once at daemon startup to handle interrupted builds.

    Args:
        computer_id: The authenticated daemon's computer ID.

    Returns:
        API response with count of reset containers.
    """
    with Session() as session:
        containers = session.execute(
            select(Container).where(Container.buildStatus == "building")
        ).scalars().all()

        count = len(containers)
        for container in containers:
            container.buildStatus = "pending"

        if count > 0:
            session.commit()
            log.info(f"Reset {count} stale 'building' status(es) to 'pending'")

        return api_response(True, f"Reset {count} stale builds", {"count": count})


def update_image_sizes_batch(data, computer_id: int):
    """Batch update image sizes for all containers.

    Called once at daemon startup to sync image sizes.

    Args:
        data: ImageSizeBatchRequest with list of image name/size pairs.
        computer_id: The authenticated daemon's computer ID.

    Returns:
        API response with count of updated containers.
    """
    with Session() as session:
        updated = 0
        for item in data.images:
            container = session.execute(
                select(Container).where(Container.imageName == item.imageName)
            ).scalar_one_or_none()
            if container:
                container.imageSize = item.imageSize
                updated += 1

        if updated > 0:
            session.commit()

        return api_response(True, f"Updated {updated} image sizes", {"count": updated})


def submit_monitoring(data, computer_id: int):
    """Save server monitoring metrics and logs.

    Args:
        data: MonitoringRequest with system metrics and service logs.
        computer_id: The authenticated daemon's computer ID.

    Returns:
        API response.
    """
    with Session() as session:
        # Upsert server status
        server_status = session.execute(
            select(ServerStatus).where(ServerStatus.computerId == computer_id)
        ).scalar_one_or_none()

        if not server_status:
            server_status = ServerStatus(computerId=computer_id)
            session.add(server_status)

        server_status.isOnline = True
        server_status.cpuUsagePercent = data.cpuUsagePercent
        server_status.cpuCores = data.cpuCores
        server_status.memoryTotalBytes = data.memoryTotalBytes
        server_status.memoryUsedBytes = data.memoryUsedBytes
        server_status.memoryUsagePercent = data.memoryUsagePercent
        server_status.diskTotalBytes = data.diskTotalBytes
        server_status.diskUsedBytes = data.diskUsedBytes
        server_status.diskFreeBytes = data.diskFreeBytes
        server_status.diskUsagePercent = data.diskUsagePercent
        server_status.dockerContainersRunning = data.dockerContainersRunning
        server_status.dockerContainersTotal = data.dockerContainersTotal
        server_status.loadAvg1Min = data.loadAvg1Min
        server_status.loadAvg5Min = data.loadAvg5Min
        server_status.loadAvg15Min = data.loadAvg15Min
        server_status.systemUptimeSeconds = data.systemUptimeSeconds
        if data.softwareVersion is not None:
            server_status.softwareVersion = data.softwareVersion
        if data.versionUpdatedAt is not None:
            server_status.versionUpdatedAt = datetime.fromisoformat(data.versionUpdatedAt)

        # Upsert logs (only accept known log types)
        _ALLOWED_LOG_TYPES = {"backend", "frontend", "docker_utility"}
        if data.logs:
            for log_type, log_entry in data.logs.items():
                if log_type not in _ALLOWED_LOG_TYPES:
                    continue
                server_log = session.execute(
                    select(ServerLogs).where(
                        ServerLogs.computerId == computer_id,
                        ServerLogs.logType == log_type,
                    )
                ).scalar_one_or_none()

                if not server_log:
                    server_log = ServerLogs(
                        computerId=computer_id,
                        logType=log_type,
                    )
                    session.add(server_log)

                server_log.logContent = log_entry.content
                server_log.logLines = log_entry.lines

        session.commit()
        return api_response(True, "Monitoring data saved")
