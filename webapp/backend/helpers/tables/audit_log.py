"""Audit log recording and retrieval functionality.

Provides functions to record significant user and admin actions into the
AuditLog table, automatically clean up old entries based on retention
settings, and retrieve paginated audit log entries for the admin UI.
"""

import json
from datetime import datetime, timedelta, timezone
from dateutil import parser as date_parser
from sqlalchemy import select, delete, or_
from database import AuditLog, User, Session
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
