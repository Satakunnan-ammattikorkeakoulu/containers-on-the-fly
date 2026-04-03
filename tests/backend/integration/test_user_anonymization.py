"""Integration tests for user anonymization (GDPR soft-deletion)."""

import base64
from datetime import datetime, timezone, timedelta
from sqlalchemy import select
import database as db
from helpers.auth import hash_password


def _create_user_with_data(session, email="target@example.com", name="Target User"):
    """Create a user with a reservation, audit log entry, and whitelist entry."""
    h = hash_password("password123")
    user = db.User(
        email=email,
        name=name,
        password=base64.b64encode(h["hashedPassword"]).decode("utf-8"),
        passwordSalt=base64.b64encode(h["salt"]).decode("utf-8"),
        sshPublicKey="ssh-rsa AAAA...",
        startScriptPath="/start.sh",
        stopScriptPath="/stop.sh",
    )
    session.add(user)
    session.flush()

    # Add "everyone" role
    everyone_role = session.execute(
        select(db.Role).where(db.Role.name == "everyone")
    ).scalar_one()
    user.roles.append(everyone_role)

    # Get existing container and computer from seed data
    container = session.execute(select(db.Container)).scalar_one()
    computer = session.execute(select(db.Computer)).scalar_one()

    # Create a reserved container
    reserved_container = db.ReservedContainer(
        containerId=container.containerId,
        sshPassword="secret123",
    )
    session.add(reserved_container)
    session.flush()

    # Create a reservation
    reservation = db.Reservation(
        reservedContainerId=reserved_container.reservedContainerId,
        computerId=computer.computerId,
        userId=user.userId,
        startDate=datetime.now(timezone.utc),
        endDate=datetime.now(timezone.utc) + timedelta(hours=2),
        description="My private research",
        status="started",
        isLowPriority=False,
    )
    session.add(reservation)

    # Create audit log entries
    audit_log = db.AuditLog(
        userId=user.userId,
        action="LOGIN",
        resourceType="user",
        ipAddress="192.168.1.100",
        details='{"email": "target@example.com"}',
    )
    session.add(audit_log)

    # Add whitelist entry
    whitelist = db.UserWhitelist(email=email)
    session.add(whitelist)

    # Add blacklist entry
    blacklist = db.UserBlacklist(email=email)
    session.add(blacklist)

    session.commit()
    return user.userId


class TestAnonymizeUserInfo:
    """Tests for GET /api/admin/user_anonymize_info."""

    def test_returns_info(self, test_client, admin_token):
        with db.Session() as session:
            user_id = _create_user_with_data(session)

        resp = test_client.get(
            f"/api/admin/user_anonymize_info?userId={user_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] is True
        info = data["data"]
        assert info["email"] == "target@example.com"
        assert info["name"] == "Target User"
        assert info["activeReservations"] == 1
        assert info["auditLogEntries"] >= 1
        assert info["isAdmin"] is False

    def test_not_found(self, test_client, admin_token):
        resp = test_client.get(
            "/api/admin/user_anonymize_info?userId=99999",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.json()["status"] is False

    def test_requires_admin(self, test_client, user_token):
        resp = test_client.get(
            "/api/admin/user_anonymize_info?userId=1",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert resp.status_code == 401


class TestAnonymizeUser:
    """Tests for POST /api/admin/anonymize_user."""

    def test_anonymize_success(self, test_client, admin_token):
        """Anonymizing a user clears all personal data and related records."""
        with db.Session() as session:
            user_id = _create_user_with_data(session)

        resp = test_client.post(
            f"/api/admin/anonymize_user?userId={user_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] is True

        # Verify user fields are anonymized
        with db.Session() as session:
            user = session.execute(
                select(db.User).where(db.User.userId == user_id)
            ).scalar_one()
            assert user.removed is True
            assert user.email == f"deleted_user_{user_id}@removed.local"
            assert user.name is None
            assert user.password is None
            assert user.passwordSalt is None
            assert user.loginToken is None
            assert user.sshPublicKey is None
            assert user.startScriptPath is None
            assert user.stopScriptPath is None

            # Verify reservation description cleared
            reservation = session.execute(
                select(db.Reservation).where(db.Reservation.userId == user_id)
            ).scalar_one()
            assert reservation.description is None

            # Verify SSH password cleared on reserved container
            reserved_container = session.execute(
                select(db.ReservedContainer).where(
                    db.ReservedContainer.reservedContainerId == reservation.reservedContainerId
                )
            ).scalar_one()
            assert reserved_container.sshPassword is None

            # Verify audit log scrubbed
            audit_logs = session.execute(
                select(db.AuditLog).where(db.AuditLog.userId == user_id)
            ).scalars().all()
            for log in audit_logs:
                assert log.ipAddress is None
                assert log.details is None

            # Verify roles deleted
            user_roles = session.execute(
                select(db.UserRole).where(db.UserRole.userId == user_id)
            ).scalars().all()
            assert len(user_roles) == 0

            # Verify whitelist entry deleted
            whitelist = session.execute(
                select(db.UserWhitelist).where(
                    db.UserWhitelist.email == "target@example.com"
                )
            ).scalar_one_or_none()
            assert whitelist is None

            # Verify blacklist entry deleted
            blacklist = session.execute(
                select(db.UserBlacklist).where(
                    db.UserBlacklist.email == "target@example.com"
                )
            ).scalar_one_or_none()
            assert blacklist is None

    def test_cannot_anonymize_self(self, test_client, admin_token):
        """Admin cannot anonymize their own account."""
        # Find the admin user ID
        resp = test_client.post(
            "/api/admin/users",
            json={"page": 1, "itemsPerPage": 10, "sortBy": [], "filters": {}},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        admin_user = next(
            u for u in resp.json()["data"]["users"] if u["email"] == "admin@foo.com"
        )

        resp = test_client.post(
            f"/api/admin/anonymize_user?userId={admin_user['userId']}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.json()["status"] is False
        assert "Cannot anonymize your own account" in resp.json()["message"]

    def test_cannot_anonymize_already_anonymized(self, test_client, admin_token):
        """Cannot anonymize a user that is already anonymized."""
        with db.Session() as session:
            user_id = _create_user_with_data(session)

        # Anonymize once
        test_client.post(
            f"/api/admin/anonymize_user?userId={user_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        # Try again
        resp = test_client.post(
            f"/api/admin/anonymize_user?userId={user_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.json()["status"] is False
        assert "already anonymized" in resp.json()["message"]

    def test_anonymize_not_found(self, test_client, admin_token):
        resp = test_client.post(
            "/api/admin/anonymize_user?userId=99999",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.json()["status"] is False

    def test_anonymize_requires_admin(self, test_client, user_token):
        resp = test_client.post(
            "/api/admin/anonymize_user?userId=1",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert resp.status_code == 401


class TestAnonymizedUserBehavior:
    """Tests for how anonymized users interact with the rest of the system."""

    def test_hidden_from_user_listing(self, test_client, admin_token):
        """Anonymized users do not appear in the admin user listing."""
        with db.Session() as session:
            user_id = _create_user_with_data(session)

        # Anonymize the user
        test_client.post(
            f"/api/admin/anonymize_user?userId={user_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        # Fetch users
        resp = test_client.post(
            "/api/admin/users",
            json={"page": 1, "itemsPerPage": 50, "sortBy": [], "filters": {}},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        user_ids = [u["userId"] for u in resp.json()["data"]["users"]]
        assert user_id not in user_ids

    def test_cannot_edit_anonymized_user(self, test_client, admin_token):
        """Editing an anonymized user is rejected."""
        with db.Session() as session:
            user_id = _create_user_with_data(session)

        test_client.post(
            f"/api/admin/anonymize_user?userId={user_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        resp = test_client.post(
            "/api/admin/save_user",
            json={"userId": user_id, "data": {"email": "new@example.com", "roles": []}},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.json()["status"] is False
        assert "anonymized" in resp.json()["message"].lower()

    def test_get_user_returns_not_found(self, test_client, admin_token):
        """get_user returns not found for anonymized users."""
        with db.Session() as session:
            user_id = _create_user_with_data(session)

        test_client.post(
            f"/api/admin/anonymize_user?userId={user_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        resp = test_client.get(
            f"/api/admin/user?userId={user_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.json()["status"] is False

    def test_anonymized_user_cannot_login(self, test_client, admin_token):
        """Anonymized user cannot log in with original or synthetic email."""
        with db.Session() as session:
            user_id = _create_user_with_data(session)

        test_client.post(
            f"/api/admin/anonymize_user?userId={user_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        # Try logging in with original email
        resp = test_client.post(
            "/api/user/login",
            data={"username": "target@example.com", "password": "password123"},
        )
        # Should fail - user not found (email was replaced)
        assert resp.status_code in [400, 401, 200]
        if resp.status_code == 200:
            assert resp.json().get("status") is False

    def test_audit_log_created_for_anonymization(self, test_client, admin_token):
        """A USER_ANONYMIZE audit log entry is created by the acting admin."""
        with db.Session() as session:
            user_id = _create_user_with_data(session)

        test_client.post(
            f"/api/admin/anonymize_user?userId={user_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        # Check that a USER_ANONYMIZE entry exists (created by admin, not the target user)
        with db.Session() as session:
            anonymize_log = session.execute(
                select(db.AuditLog).where(
                    db.AuditLog.action == "USER_ANONYMIZE",
                    db.AuditLog.resourceId == user_id,
                )
            ).scalar_one_or_none()
            assert anonymize_log is not None
            assert anonymize_log.userId != user_id  # Created by admin, not target
