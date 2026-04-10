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
    send_container_resume_failed_email, send_admin_failure_alert,
)
from helpers.logger import log
from helpers.tables.audit_log import log_action


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
            if res.status in ("started", "reserved", "restart_error", "paused", "stopping") and res.endDate < now:
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

        # Detect if this is a resume of a previously-paused low-priority container
        # (must be checked before overwriting containerStatus below)
        is_resume = rc.containerStatus == "paused"

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

        # Collect email data while still in session scope
        container_obj = rc.container
        email_recipient = reservation.user.email
        email_image_name = container_obj.imageName
        email_computer_ip = reservation.computer.ip
        email_end_date = reservation.endDate
        email_username = container_obj.containerUsername or "user"
        email_is_low_priority = reservation.isLowPriority
        log_user_id = reservation.userId

        # Build port list for email (include portType for type-aware rendering)
        email_ports = []
        for port in data.ports:
            # Find the service name, local port, and port type from the container's port definitions
            service_name = "Unknown"
            local_port = None
            port_type = None
            for cp in container_obj.containerPorts:
                if cp.containerPortId == port.containerPortId:
                    service_name = cp.serviceName
                    local_port = cp.port
                    port_type = cp.portType
                    break
            email_ports.append({
                "serviceName": service_name,
                "localPort": local_port,
                "outsidePort": port.outsidePort,
                "portType": port_type,
                "containerPortId": port.containerPortId,
            })

        email_primary_port_id = container_obj.primaryConnectionPortId
        audit_computer_name = reservation.computer.name

    # Send notification email outside session to avoid holding DB connection during SMTP I/O
    if is_resume:
        send_container_resumed_email(
            email_recipient, email_image_name, email_computer_ip,
            email_ports, data.sshPassword,
            email_end_date, email_username,
            primary_connection_port_id=email_primary_port_id,
        )
    else:
        send_container_started_email(
            email_recipient, email_image_name, email_computer_ip,
            email_ports, data.sshPassword, data.nonCriticalErrors,
            email_end_date, email_username,
            primary_connection_port_id=email_primary_port_id,
            is_low_priority=email_is_low_priority,
        )

    log_action(
        None,
        "RESERVATION_RESUMED" if is_resume else "RESERVATION_STARTED",
        "reservation", reservation_id,
        {"computerName": audit_computer_name, "imageName": email_image_name,
         "isLowPriority": email_is_low_priority},
    )

    log.info(f"Container started for reservation {reservation_id}, user={log_user_id}, docker_name={data.containerDockerName}, resume={is_resume}")
    return api_response(True, "Reservation marked as started")


def report_start_failed(reservation_id: int, data, computer_id: int):
    """Record that a container failed to start and send error notifications.

    Detects whether this is a fresh start failure or a failed resume of a
    previously-paused low-priority container (by checking if containerStatus
    was "paused" prior to this call). Sends a tailored email accordingly.
    The reservation is marked as "error" — a terminal state with no retry.

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

        # Detect if this is a failed resume of a previously-paused low-priority container
        # (must be checked before overwriting containerStatus below)
        is_resume_failure = reservation.reservedContainer.containerStatus == "paused"

        reservation.status = "error"
        reservation.reservedContainer.containerDockerErrorMessage = data.errorMessage
        reservation.reservedContainer.containerStatus = "error"
        session.commit()

        # Collect email data while still in session scope
        container_obj = reservation.reservedContainer.container
        email_recipient = reservation.user.email
        image_name = container_obj.imageName if container_obj else "unknown"
        computer_name = reservation.computer.name

    # Send notification emails outside session to avoid holding DB connection during SMTP I/O
    if is_resume_failure:
        send_container_resume_failed_email(
            email_recipient, image_name, computer_name,
            reservation_id, data.errorMessage,
        )
    else:
        send_container_error_email(email_recipient, data.errorMessage)
    send_admin_failure_alert(
        email_recipient, reservation_id,
        image_name, computer_name, data.errorMessage,
    )

    log_action(
        None, "RESERVATION_ERROR", "reservation", reservation_id,
        {"computerName": computer_name, "imageName": image_name,
         "errorMessage": data.errorMessage, "resumeFailure": is_resume_failure},
    )

    log.error(f"Container start failed for reservation {reservation_id}: {data.errorMessage}, resume_failure={is_resume_failure}")
    return api_response(True, "Reservation marked as error")


def report_stopped(reservation_id: int, computer_id: int):
    """Record that a container was stopped.

    Distinguishes between a user/admin-initiated stop (status already
    "stopping", because cancel_reservation set it) and an automatic
    stop triggered by the reservation's endDate being reached.

    Args:
        reservation_id: Database ID of the reservation.
        computer_id: The authenticated daemon's computer ID.

    Returns:
        API response.
    """
    with Session() as session:
        reservation = session.execute(
            select(Reservation)
            .options(
                joinedload(Reservation.reservedContainer).joinedload(ReservedContainer.container),
                joinedload(Reservation.computer),
            )
            .where(
                Reservation.reservationId == reservation_id,
                Reservation.computerId == computer_id,
            )
        ).unique().scalar_one_or_none()

        if not reservation:
            return api_response(False, "Reservation not found")

        # If the reservation is already in "stopping", a user/admin triggered
        # the cancel and the RESERVATION_CANCEL / RESERVATION_ADMIN_EDIT entry
        # is already in the audit log; don't double-log here.
        was_user_initiated = reservation.status == "stopping"

        reservation.status = "stopped"
        reservation.reservedContainer.stoppedAt = _time_now()
        reservation.reservedContainer.containerStatus = "stopped"

        audit_computer_name = reservation.computer.name if reservation.computer else None
        audit_image_name = (
            reservation.reservedContainer.container.imageName
            if reservation.reservedContainer and reservation.reservedContainer.container
            else None
        )

        session.commit()

    if not was_user_initiated:
        log_action(
            None, "RESERVATION_AUTO_STOPPED", "reservation", reservation_id,
            {"computerName": audit_computer_name, "imageName": audit_image_name,
             "reason": "endDate reached"},
        )

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

        # Collect email data while still in session scope
        email_recipient = reservation.user.email

    # Send notification email outside session to avoid holding DB connection during SMTP I/O
    send_container_paused_email(
        email_recipient, data.imageName,
        data.computerName, reservation_id,
    )

    log_action(
        None, "RESERVATION_PAUSED", "reservation", reservation_id,
        {"computerName": data.computerName, "imageName": data.imageName},
    )

    log.info(f"Low-priority reservation {reservation_id} paused")
    return api_response(True, "Reservation marked as paused")


def report_resumed(reservation_id: int, computer_id: int):
    """Record that a paused container is ready to resume.

    Sets status back to "reserved" so the daemon picks it up for start
    on the next polling cycle. The resumed email is sent later from
    report_started, which detects the resume case via containerStatus
    being "paused" prior to the start.

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
                Reservation.status.in_(["started", "stopping"]),
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
