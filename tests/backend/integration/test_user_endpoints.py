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


class TestUpdateSshKey:

    def test_set_valid_rsa_key(self, test_client, user_token):
        key = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQ... user@host"
        resp = test_client.post(
            "/api/user/update_ssh_key",
            json={"sshPublicKey": key},
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] is True

    def test_set_valid_ed25519_key(self, test_client, user_token):
        key = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAI... user@host"
        resp = test_client.post(
            "/api/user/update_ssh_key",
            json={"sshPublicKey": key},
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] is True

    def test_invalid_key_format_rejected(self, test_client, user_token):
        resp = test_client.post(
            "/api/user/update_ssh_key",
            json={"sshPublicKey": "not-a-valid-key"},
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] is False
        assert "Invalid" in resp.json()["message"]

    def test_remove_key_with_empty_string(self, test_client, user_token):
        resp = test_client.post(
            "/api/user/update_ssh_key",
            json={"sshPublicKey": ""},
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] is True

    def test_unauthenticated_rejected(self, test_client):
        resp = test_client.post(
            "/api/user/update_ssh_key",
            json={"sshPublicKey": "ssh-rsa AAAA..."},
        )
        assert resp.status_code in (401, 422)


class TestUpdateScriptPaths:

    def test_set_valid_paths(self, test_client, user_token):
        resp = test_client.post(
            "/api/user/update_script_paths",
            json={
                "startScriptPath": "/home/user/start.sh",
                "stopScriptPath": "/home/user/stop.sh",
            },
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] is True

    def test_invalid_path_rejected(self, test_client, user_token):
        resp = test_client.post(
            "/api/user/update_script_paths",
            json={
                "startScriptPath": "relative/path.sh",
                "stopScriptPath": "",
            },
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] is False

    def test_remove_paths_with_empty_strings(self, test_client, user_token):
        resp = test_client.post(
            "/api/user/update_script_paths",
            json={"startScriptPath": "", "stopScriptPath": ""},
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] is True

    def test_paths_shown_in_profile(self, test_client, user_token):
        # Set paths
        test_client.post(
            "/api/user/update_script_paths",
            json={
                "startScriptPath": "/opt/scripts/start.sh",
                "stopScriptPath": "/opt/scripts/stop.sh",
            },
            headers={"Authorization": f"Bearer {user_token}"},
        )
        # Check profile
        resp = test_client.get(
            "/api/user/profile",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        user = resp.json()["data"]["user"]
        assert user["startScriptPath"] == "/opt/scripts/start.sh"
        assert user["stopScriptPath"] == "/opt/scripts/stop.sh"
