"""Integration tests for helpers/tables/audit_log.py operations."""

from unittest.mock import patch
import database as db
from sqlalchemy import select
from helpers.tables.audit_log import log_action, get_audit_logs
from helpers.request_context import set_client_ip


class _FakeRequest:
    """Minimal stand-in for AuditLogRequest Pydantic model."""
    def __init__(self, page=1, items=10, sort_by=None, filters=None):
        self.page = page
        self.itemsPerPage = items
        self.sortBy = sort_by or []
        self.filters = filters or {}


class TestLogAction:

    def test_creates_entry(self, seed_test_data):
        with db.Session() as s:
            user = s.execute(select(db.User).where(db.User.email == "admin@foo.com")).scalar_one()
            user_id = user.userId

        set_client_ip("127.0.0.1")
        log_action(user_id, "LOGIN")

        with db.Session() as s:
            entries = s.execute(select(db.AuditLog)).scalars().all()
            assert len(entries) == 1
            assert entries[0].action == "LOGIN"
            assert entries[0].userId == user_id
            assert entries[0].ipAddress == "127.0.0.1"

    def test_with_details(self, seed_test_data):
        with db.Session() as s:
            user = s.execute(select(db.User).where(db.User.email == "admin@foo.com")).scalar_one()
            user_id = user.userId

        log_action(user_id, "RESERVATION_CREATE", "reservation", 42,
                   details={"container": "ubuntu"})

        with db.Session() as s:
            entry = s.execute(select(db.AuditLog)).scalar_one()
            assert entry.resourceType == "reservation"
            assert entry.resourceId == 42
            assert '"container"' in entry.details

    def test_none_actor(self):
        set_client_ip("10.0.0.1")
        log_action(None, "LOGIN_FAILED")
        with db.Session() as s:
            entry = s.execute(select(db.AuditLog)).scalar_one()
            assert entry.userId is None
            assert entry.action == "LOGIN_FAILED"

    def test_error_does_not_raise(self):
        with patch("helpers.tables.audit_log.Session", side_effect=RuntimeError("db down")):
            log_action(1, "TEST")  # should not raise


class TestGetAuditLogs:

    def test_returns_paginated_logs(self, seed_test_data):
        with db.Session() as s:
            user = s.execute(select(db.User).where(db.User.email == "admin@foo.com")).scalar_one()
            user_id = user.userId

        for i in range(5):
            log_action(user_id, f"ACTION_{i}")

        result = get_audit_logs(_FakeRequest(page=1, items=3))
        assert result["status"] is True
        assert result["data"]["totalItems"] == 5
        assert len(result["data"]["logs"]) == 3

    def test_filter_by_action(self, seed_test_data):
        with db.Session() as s:
            user = s.execute(select(db.User).where(db.User.email == "admin@foo.com")).scalar_one()
            user_id = user.userId

        log_action(user_id, "LOGIN")
        log_action(user_id, "LOGOUT")

        result = get_audit_logs(_FakeRequest(filters={"action": "LOGIN"}))
        assert result["status"] is True
        assert result["data"]["totalItems"] == 1
        assert result["data"]["logs"][0]["action"] == "LOGIN"

    def test_empty_result(self):
        result = get_audit_logs(_FakeRequest())
        assert result["status"] is True
        assert result["data"]["totalItems"] == 0
        assert result["data"]["logs"] == []

    def test_filter_by_user(self, seed_test_data):
        with db.Session() as s:
            admin = s.execute(select(db.User).where(db.User.email == "admin@foo.com")).scalar_one()
            user = s.execute(select(db.User).where(db.User.email == "user@foo.com")).scalar_one()

        log_action(admin.userId, "LOGIN")
        log_action(user.userId, "LOGOUT")

        result = get_audit_logs(_FakeRequest(filters={"user": "admin@foo.com"}))
        assert result["status"] is True
        assert result["data"]["totalItems"] == 1

    def test_sort_by_created_at(self, seed_test_data):
        with db.Session() as s:
            user = s.execute(select(db.User).where(db.User.email == "admin@foo.com")).scalar_one()
            user_id = user.userId

        log_action(user_id, "FIRST")
        log_action(user_id, "SECOND")

        result = get_audit_logs(_FakeRequest(
            sort_by=[{"key": "createdAt", "order": "asc"}]
        ))
        assert result["status"] is True
        actions = [l["action"] for l in result["data"]["logs"]]
        assert actions == ["FIRST", "SECOND"]


class TestCleanupOldLogs:

    def test_deletes_logs_older_than_retention(self, seed_test_data):
        from datetime import datetime, timezone, timedelta
        from helpers.tables.audit_log import _cleanup_old_logs

        with db.Session() as s:
            user = s.execute(select(db.User).where(db.User.email == "admin@foo.com")).scalar_one()
            user_id = user.userId

        set_client_ip("127.0.0.1")
        log_action(user_id, "OLD_ACTION")

        # Manually backdate the log entry
        with db.Session() as s:
            entry = s.execute(select(db.AuditLog)).scalar_one()
            entry.createdAt = datetime.now(timezone.utc) - timedelta(days=100)
            s.commit()

        with patch("helpers.tables.audit_log.settings_handler") as mock_sh:
            mock_sh.get_setting.return_value = 7
            with db.Session() as s:
                _cleanup_old_logs(s)

        with db.Session() as s:
            count = s.execute(select(db.AuditLog)).scalars().all()
            assert len(count) == 0

    def test_keeps_logs_within_retention(self, seed_test_data):
        from helpers.tables.audit_log import _cleanup_old_logs

        with db.Session() as s:
            user = s.execute(select(db.User).where(db.User.email == "admin@foo.com")).scalar_one()
            user_id = user.userId

        set_client_ip("127.0.0.1")
        log_action(user_id, "RECENT_ACTION")

        with patch("helpers.tables.audit_log.settings_handler") as mock_sh:
            mock_sh.get_setting.return_value = 7
            with db.Session() as s:
                _cleanup_old_logs(s)

        with db.Session() as s:
            count = s.execute(select(db.AuditLog)).scalars().all()
            assert len(count) == 1


class TestMarkUserActivitySeen:

    def test_updates_activity_last_seen(self, seed_test_data):
        from helpers.tables.audit_log import mark_user_activity_seen

        with db.Session() as s:
            user = s.execute(select(db.User).where(db.User.email == "user@foo.com")).scalar_one()
            user_id = user.userId

        result = mark_user_activity_seen(user_id)
        assert result["status"] is True
        assert result["data"]["previousLastSeenAt"] is None

    def test_returns_previous_last_seen(self, seed_test_data):
        from helpers.tables.audit_log import mark_user_activity_seen

        with db.Session() as s:
            user = s.execute(select(db.User).where(db.User.email == "user@foo.com")).scalar_one()
            user_id = user.userId

        # First call sets the marker
        mark_user_activity_seen(user_id)
        # Second call returns the previous value
        result = mark_user_activity_seen(user_id)
        assert result["status"] is True
        assert result["data"]["previousLastSeenAt"] is not None

    def test_user_not_found(self):
        from helpers.tables.audit_log import mark_user_activity_seen

        result = mark_user_activity_seen(99999)
        assert result["status"] is False
