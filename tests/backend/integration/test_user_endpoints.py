"""Integration tests for /api/user endpoints."""

import pytest


class TestLogin:

    def test_login_admin_success(self, test_client):
        resp = test_client.post(
            "/api/user/login",
            data={"username": "admin@foo.com", "password": "test"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body
        assert body["token_type"] == "bearer"

    def test_login_user_success(self, test_client):
        resp = test_client.post(
            "/api/user/login",
            data={"username": "user@foo.com", "password": "test"},
        )
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    def test_login_empty_username(self, test_client):
        # OAuth2PasswordRequestForm treats empty string as missing → 422
        resp = test_client.post(
            "/api/user/login",
            data={"username": "", "password": "test"},
        )
        assert resp.status_code in (400, 422)

    def test_login_empty_password(self, test_client):
        resp = test_client.post(
            "/api/user/login",
            data={"username": "admin@foo.com", "password": ""},
        )
        assert resp.status_code in (400, 422)

    def test_login_wrong_password(self, test_client):
        resp = test_client.post(
            "/api/user/login",
            data={"username": "admin@foo.com", "password": "wrong"},
        )
        assert resp.status_code == 400
        assert "Incorrect password" in resp.json()["detail"]

    def test_login_nonexistent_user(self, test_client):
        resp = test_client.post(
            "/api/user/login",
            data={"username": "nobody@foo.com", "password": "test"},
        )
        assert resp.status_code == 400
        assert "User not found" in resp.json()["detail"]


class TestCheckToken:

    def test_valid_token(self, test_client, admin_token):
        resp = test_client.get(
            "/api/user/check_token",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] is True
        assert data["data"]["email"] == "admin@foo.com"

    def test_invalid_token(self, test_client):
        resp = test_client.get(
            "/api/user/check_token",
            headers={"Authorization": "Bearer invalid_token_value"},
        )
        assert resp.status_code == 401

    def test_returns_user_roles(self, test_client, admin_token):
        resp = test_client.get(
            "/api/user/check_token",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        data = resp.json()["data"]
        assert "roles" in data
        assert "admin" in data["roles"]

    def test_returns_reservation_limits(self, test_client, admin_token):
        resp = test_client.get(
            "/api/user/check_token",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        data = resp.json()["data"]
        assert "reservationLimits" in data
        limits = data["reservationLimits"]
        assert "minDuration" in limits
        assert "maxDuration" in limits
        assert "maxActiveReservations" in limits


class TestProfile:

    def test_profile_returns_user_data(self, test_client, admin_token):
        resp = test_client.get(
            "/api/user/profile",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] is True
        user = data["data"]["user"]
        assert user["email"] == "admin@foo.com"
        assert "userId" in user
        assert "createdAt" in user

    def test_profile_unauthenticated(self, test_client):
        resp = test_client.get("/api/user/profile")
        assert resp.status_code in (401, 422)


class TestHasPassword:

    def test_user_with_password(self, test_client, user_token):
        resp = test_client.get(
            "/api/user/has_password",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["hasPassword"] is True


class TestChangePassword:

    def test_change_password_success(self, test_client, user_token):
        resp = test_client.post(
            "/api/user/change_password",
            json={"currentPassword": "test", "newPassword": "newpass123"},
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] is True

        # Can login with new password
        resp = test_client.post(
            "/api/user/login",
            data={"username": "user@foo.com", "password": "newpass123"},
        )
        assert resp.status_code == 200

    def test_change_password_wrong_current(self, test_client, user_token):
        resp = test_client.post(
            "/api/user/change_password",
            json={"currentPassword": "wrong", "newPassword": "newpass123"},
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] is False
        assert "incorrect" in resp.json()["message"].lower()

    def test_change_password_too_short(self, test_client, user_token):
        resp = test_client.post(
            "/api/user/change_password",
            json={"currentPassword": "test", "newPassword": "ab"},
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] is False
        assert "at least 5" in resp.json()["message"]
