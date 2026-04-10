"""Audit log recording and retrieval functionality.

Provides functions to record significant user and admin actions into the
AuditLog table, automatically clean up old entries based on retention
settings, and retrieve paginated audit log entries for the admin UI.
"""

import json
from datetime import datetime, timedelta, timezone
from dateutil import parser as date_parser
from sqlalchemy import select, delete, or_, func
from sqlalchemy.orm import joinedload
from database import (
    AuditLog, User, Reservation, ReservedContainer, ReservedHardwareSpec,
    Container, Session,
)
from helpers.server import api_response, orm_to_dict
from helpers.pagination import apply_pagination, get_total_count
from helpers.settings_handler import settings_handler
from helpers.logger import log
from helpers.request_context import get_client_ip


def log_action(actor_user_id, action, resource_type=None, resource_id=None, details=None):
    """Record an audit log entry for a significant action.

    The client IP address is automatically captured from the request context
    (set by middleware), so callers do not need to pass it.

    This function is fire-and-forget: it catches all exceptions internally
    so that audit logging never breaks the calling operation.

    Args:
        actor_user_id: The userId of the user who performed the action.
            None for failed logins of unknown users.
        action: The action type string (e.g. "LOGIN", "RESERVATION_CREATE").
        resource_type: The type of resource affected (e.g. "reservation",
            "user", "role"). None for login events.
        resource_id: The database ID of the affected resource. None when
            not applicable.
        details: Optional dict of additional context. Serialized to JSON.
            Must never contain passwords, tokens, or SSH keys.
    """
    try:
        retention_days = settings_handler.get_setting("auditLog.retentionDays")
        if retention_days is not None and retention_days == -1:
            return  # Audit logging is disabled
        details_json = json.dumps(details) if details else None
        with Session() as session:
            entry = AuditLog(
                userId=actor_user_id,
                action=action,
                resourceType=resource_type,
                resourceId=resource_id,
                details=details_json,
                ipAddress=get_client_ip()
            )
            session.add(entry)
            session.commit()
            _cleanup_old_logs(session)
    except Exception as e:
        log.error(f"Failed to write audit log entry: {e}")


def purge_all_logs():
    """Delete all audit log entries. Called when audit logging is disabled.

    Failures are logged but never raised.
    """
    try:
        with Session() as session:
            session.execute(delete(AuditLog))
            session.commit()
    except Exception as e:
        log.error(f"Failed to purge audit logs: {e}")


def _cleanup_old_logs(session):
    """Delete audit log entries older than the configured retention period.

    Reads the auditLog.retentionDays setting. If the value is greater than
    zero, deletes all AuditLog rows with createdAt before the cutoff date.
    Failures are logged but never raised.

    Args:
        session: Active SQLAlchemy session (used for the delete operation).
    """
    try:
        retention_days = settings_handler.get_setting("auditLog.retentionDays")
        if retention_days and retention_days > 0:
            cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
            session.execute(
                delete(AuditLog).where(AuditLog.createdAt < cutoff)
            )
            session.commit()
    except Exception as e:
        log.error(f"Failed to clean up old audit logs: {e}")


def get_audit_logs(request):
    """Retrieve paginated audit log entries with optional filtering.

    Args:
        request: An AuditLogRequest instance with page, itemsPerPage,
            sortBy, and filters fields. Supported filter keys:
            action, resourceType, user (email/name search), ip, dateFrom, dateTo.

    Returns:
        An api_response dict with logs list, totalItems, and retentionDays.
    """
    # Parse date filters upfront so validation happens before any queries
    parsed_from = None
    parsed_to = None
    filters = request.filters if request.filters else {}
    if filters.get("dateFrom"):
        try:
            parsed_from = date_parser.parse(filters["dateFrom"])
        except (ValueError, TypeError):
            return api_response(False, "Invalid dateFrom filter.")
    if filters.get("dateTo"):
        try:
            parsed_to = date_parser.parse(filters["dateTo"])
        except (ValueError, TypeError):
            return api_response(False, "Invalid dateTo filter.")

    def _apply_filters(query, filters):
        """Apply audit log filters to a query. Used for both data and count queries."""
        if filters.get("action"):
            query = query.where(AuditLog.action == filters["action"])
        if filters.get("resourceType"):
            query = query.where(AuditLog.resourceType == filters["resourceType"])
        if filters.get("user"):
            user_search = f"%{filters['user']}%"
            query = query.where(
                or_(User.email.ilike(user_search), User.name.ilike(user_search))
            )
        if filters.get("ip"):
            query = query.where(AuditLog.ipAddress.ilike(f"%{filters['ip']}%"))
        if parsed_from:
            query = query.where(AuditLog.createdAt >= parsed_from)
        if parsed_to:
            query = query.where(AuditLog.createdAt < parsed_to + timedelta(days=1))
        return query

    with Session() as session:
        base_query = select(AuditLog, User.email, User.name).outerjoin(
            User, AuditLog.userId == User.userId
        )
        base_query = _apply_filters(base_query, filters)

        count_query = select(AuditLog.auditLogId).outerjoin(
            User, AuditLog.userId == User.userId
        )
        count_query = _apply_filters(count_query, filters)

        total_items = get_total_count(session, count_query)

        allowed_sort_keys = {
            "auditLogId": AuditLog.auditLogId,
            "action": AuditLog.action,
            "resourceType": AuditLog.resourceType,
            "createdAt": AuditLog.createdAt,
            "userEmail": User.email,
        }

        # Default sort by createdAt desc if no sort specified
        sort_by = request.sortBy if request.sortBy else []

        paginated = apply_pagination(
            base_query, sort_by, request.page,
            request.itemsPerPage, allowed_sort_keys
        )

        rows = session.execute(paginated).all()

        logs = []
        for row in rows:
            audit_log = row[0]
            user_email = row[1]
            user_name = row[2]
            parsed_details = None
            if audit_log.details:
                try:
                    parsed_details = json.loads(audit_log.details)
                except (json.JSONDecodeError, TypeError):
                    parsed_details = audit_log.details

            logs.append({
                "auditLogId": audit_log.auditLogId,
                "userId": audit_log.userId,
                "userEmail": user_email,
                "userName": user_name,
                "action": audit_log.action,
                "resourceType": audit_log.resourceType,
                "resourceId": audit_log.resourceId,
                "details": parsed_details,
                "ipAddress": audit_log.ipAddress,
                "createdAt": audit_log.createdAt.isoformat() if audit_log.createdAt else None,
            })

        retention_days = settings_handler.get_setting("auditLog.retentionDays")

        return api_response(True, "Audit logs fetched.", {
            "logs": logs,
            "totalItems": total_items,
            "retentionDays": retention_days,
        })


UNREAD_ACTIVITY_COUNT_CAP = 99

# Audit log actions that count toward the unread activity badge.
# These are events that happen *to* a reservation without the user
# initiating them, so seeing the badge means "something requires your
# attention." User-initiated events (create, extend, restart, cancel,
# description update) and routine successful starts are intentionally
# excluded so the badge does not increment while the user is actively
# using the application.
NOTABLE_ACTIVITY_ACTIONS = [
    "RESERVATION_PAUSED",
    "RESERVATION_RESUMED",
    "RESERVATION_AUTO_STOPPED",
    "RESERVATION_ERROR",
]


def mark_user_activity_seen(user_id):
    """Update the user's activityLastSeenAt to NOW() and return the prior value.

    The returned ``previousLastSeenAt`` represents the cutoff *before* this
    call moved the marker forward, so the frontend can use it to render
    "NEW" indicators for rows that arrived between the user's last visit
    and now without any race condition.

    Args:
        user_id: The ID of the user whose seen marker to update.

    Returns:
        An api_response dict containing ``previousLastSeenAt`` (ISO string
        or None if the user had never opened the activity feed before).
    """
    try:
        with Session() as session:
            user = session.execute(
                select(User).where(User.userId == user_id)
            ).scalar_one_or_none()
            if user is None:
                return api_response(False, "User not found.")
            previous = user.activityLastSeenAt
            user.activityLastSeenAt = datetime.utcnow()
            session.commit()
            return api_response(True, "Activity marked as seen.", {
                "previousLastSeenAt": previous.isoformat() if previous else None,
            })
    except Exception as e:
        log.error(f"Failed to mark activity as seen for user {user_id}: {e}")
        return api_response(False, "Failed to update activity marker.")


def get_user_unread_activity_count(session, user_id, last_seen_at):
    """Count audit log entries for a user's reservations newer than ``last_seen_at``.

    Returns 0 if ``last_seen_at`` is None or no rows are newer. The
    returned value is capped at ``UNREAD_ACTIVITY_COUNT_CAP``; the
    frontend renders ``99+`` once the cap is hit.

    Args:
        session: Active SQLAlchemy session.
        user_id: The requesting user's ID.
        last_seen_at: DateTime cutoff. Entries with createdAt strictly
            greater than this value are counted.

    Returns:
        Integer count, clamped to ``[0, UNREAD_ACTIVITY_COUNT_CAP]``.
    """
    if last_seen_at is None:
        return 0
    try:
        count_query = (
            select(func.count())
            .select_from(AuditLog)
            .where(
                AuditLog.resourceType == "reservation",
                AuditLog.action.in_(NOTABLE_ACTIVITY_ACTIONS),
                AuditLog.resourceId.in_(
                    select(Reservation.reservationId).where(Reservation.userId == user_id)
                ),
                AuditLog.createdAt > last_seen_at,
            )
        )
        count = session.execute(count_query).scalar() or 0
        if count > UNREAD_ACTIVITY_COUNT_CAP:
            return UNREAD_ACTIVITY_COUNT_CAP + 1  # sentinel meaning "over the cap"
        return count
    except Exception as e:
        log.error(f"Failed to compute unread activity count: {e}")
        return 0


def get_user_reservation_activity(user_id, request):
    """Retrieve paginated audit log entries for a user's own reservations.

    Returns audit log rows where resourceType is "reservation" AND the
    resourceId belongs to a reservation owned by ``user_id``. The actor
    of each event may be the user themselves, an admin, or the system
    (e.g. daemon-initiated pause/resume/auto-stop), but every returned
    entry concerns a reservation the user owns.

    Args:
        user_id: The ID of the user whose reservation activity to fetch.
        request: A PaginationParams-derived request with page, itemsPerPage,
            sortBy, and filters. Supported filter keys: action, dateFrom, dateTo.

    Returns:
        An api_response dict with logs list, totalItems, and retentionDays.
    """
    parsed_from = None
    parsed_to = None
    filters = request.filters if request.filters else {}
    if filters.get("dateFrom"):
        try:
            parsed_from = date_parser.parse(filters["dateFrom"])
        except (ValueError, TypeError):
            return api_response(False, "Invalid dateFrom filter.")
    if filters.get("dateTo"):
        try:
            parsed_to = date_parser.parse(filters["dateTo"])
        except (ValueError, TypeError):
            return api_response(False, "Invalid dateTo filter.")

    def _apply_filters(query):
        query = query.where(
            AuditLog.resourceType == "reservation",
            AuditLog.resourceId.in_(
                select(Reservation.reservationId).where(Reservation.userId == user_id)
            ),
        )
        if filters.get("action"):
            query = query.where(AuditLog.action == filters["action"])
        if parsed_from:
            query = query.where(AuditLog.createdAt >= parsed_from)
        if parsed_to:
            query = query.where(AuditLog.createdAt < parsed_to + timedelta(days=1))
        return query

    with Session() as session:
        base_query = _apply_filters(select(AuditLog))
        count_query = _apply_filters(select(AuditLog.auditLogId))

        total_items = get_total_count(session, count_query)

        allowed_sort_keys = {
            "auditLogId": AuditLog.auditLogId,
            "action": AuditLog.action,
            "createdAt": AuditLog.createdAt,
        }

        sort_by = request.sortBy if request.sortBy else []

        paginated = apply_pagination(
            base_query, sort_by, request.page,
            request.itemsPerPage, allowed_sort_keys
        )

        rows = session.execute(paginated).scalars().all()

        # Only a small whitelist of detail keys is forwarded to the user-facing
        # activity feed. This keeps raw Docker stderr, internal paths, and
        # similar infrastructure detail from leaking out of the admin audit log,
        # and lets the frontend format a human-readable label without rendering
        # the full JSON details blob.
        user_visible_detail_keys = {
            "cancelledBy", "duration", "success",
            "resumeFailure", "isLowPriority",
            "oldEndDate", "newEndDate",
        }

        logs = []
        for audit_log in rows:
            parsed_details = None
            if audit_log.details:
                try:
                    parsed_details = json.loads(audit_log.details)
                except (json.JSONDecodeError, TypeError):
                    parsed_details = None

            safe_details = {}
            if isinstance(parsed_details, dict):
                safe_details = {
                    k: parsed_details[k]
                    for k in user_visible_detail_keys
                    if k in parsed_details
                }

            logs.append({
                "auditLogId": audit_log.auditLogId,
                "action": audit_log.action,
                "resourceId": audit_log.resourceId,
                "details": safe_details,
                "createdAt": audit_log.createdAt.isoformat() if audit_log.createdAt else None,
            })

        reservation_ids = {
            entry["resourceId"] for entry in logs
            if entry.get("resourceId") is not None
        }
        reservation_summaries = _build_reservation_summaries(
            session, user_id, reservation_ids
        )

        # Snapshot of when the user last viewed the activity feed, used by
        # the frontend to highlight rows newer than this cutoff with a
        # "NEW" chip. The frontend captures this once on view-open and
        # holds it for the lifetime of the open view.
        last_seen_row = session.execute(
            select(User.activityLastSeenAt).where(User.userId == user_id)
        ).first()
        last_seen_at = last_seen_row[0] if last_seen_row else None

        retention_days = settings_handler.get_setting("auditLog.retentionDays")

        return api_response(True, "Activity fetched.", {
            "logs": logs,
            "totalItems": total_items,
            "retentionDays": retention_days,
            "reservationSummaries": reservation_summaries,
            "activityLastSeenAt": last_seen_at.isoformat() if last_seen_at else None,
            "notableActions": list(NOTABLE_ACTIVITY_ACTIONS),
        })


def _build_reservation_summaries(session, user_id, reservation_ids):
    """Return a non-sensitive summary dict keyed by reservation ID.

    Only reservations owned by ``user_id`` are loaded, so a user cannot
    use the activity API to peek at another user's reservation summary
    even if the audit log contained a foreign ID. Sensitive fields
    (ssh password, docker container name, docker container ID) are
    intentionally excluded.

    Args:
        session: Active SQLAlchemy session.
        user_id: The requesting user's ID (scopes the summary query).
        reservation_ids: Iterable of reservation IDs to summarize.

    Returns:
        Dict mapping ``str(reservationId)`` → summary dict. Reservation IDs
        with no matching row (e.g. very old rows the user no longer owns)
        are simply omitted.
    """
    if not reservation_ids:
        return {}

    reservations = session.execute(
        select(Reservation)
        .options(
            joinedload(Reservation.computer),
            joinedload(Reservation.reservedContainer).joinedload(ReservedContainer.container),
            joinedload(Reservation.reservedContainer).joinedload(ReservedContainer.reservedContainerPorts),
            joinedload(Reservation.reservedHardwareSpecs).joinedload(ReservedHardwareSpec.hardwareSpec),
        )
        .where(
            Reservation.reservationId.in_(reservation_ids),
            Reservation.userId == user_id,
        )
    ).unique().scalars().all()

    summaries = {}
    for res in reservations:
        hardware_specs = []
        for spec in res.reservedHardwareSpecs:
            if not spec.hardwareSpec or spec.amount is None or spec.amount <= 0:
                continue
            hardware_specs.append({
                "amount": spec.amount,
                "format": spec.hardwareSpec.format,
                "type": spec.hardwareSpec.type,
            })

        rc = res.reservedContainer
        image_name = None
        shm_size_percent = None
        ram_disk_size_percent = None
        ports = []
        if rc:
            shm_size_percent = rc.shmSizePercent
            ram_disk_size_percent = rc.ramDiskSizePercent
            if rc.container:
                image_name = rc.container.imageName
            for port in rc.reservedContainerPorts:
                container_port = port.containerPort
                ports.append({
                    "localPort": container_port.port if container_port else None,
                    "outsidePort": port.outsidePort,
                    "serviceName": container_port.serviceName if container_port else None,
                })

        summaries[str(res.reservationId)] = {
            "computerName": res.computer.name if res.computer else None,
            "hardwareSpecs": hardware_specs,
            "shmSizePercent": shm_size_percent,
            "ramDiskSizePercent": ram_disk_size_percent,
            "isLowPriority": bool(res.isLowPriority),
            "imageName": image_name,
            "ports": ports,
        }

    return summaries
