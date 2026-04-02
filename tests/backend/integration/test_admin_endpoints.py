"""Integration tests for /api/admin endpoints."""


class TestAdminAuthGuard:
    """All admin endpoints must reject non-admin users."""

    def test_get_users_requires_admin(self, test_client, user_token):
        resp = test_client.post(
            "/api/admin/users",
            json={"page": 1, "itemsPerPage": 10, "sortBy": [], "filters": {}},
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert resp.status_code == 401

    def test_get_computers_requires_admin(self, test_client, user_token):
        resp = test_client.get(
            "/api/admin/computers",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert resp.status_code == 401

    def test_get_containers_requires_admin(self, test_client, user_token):
        resp = test_client.get(
            "/api/admin/containers",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert resp.status_code == 401

    def test_get_roles_requires_admin(self, test_client, user_token):
        resp = test_client.get(
            "/api/admin/roles",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert resp.status_code == 401


class TestAdminUsers:

    def test_get_users(self, test_client, admin_token):
        resp = test_client.post(
            "/api/admin/users",
            json={"page": 1, "itemsPerPage": 10, "sortBy": [], "filters": {}},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] is True
        assert "users" in data["data"]
        assert "totalItems" in data["data"]
        assert len(data["data"]["users"]) >= 2  # admin + user

    def test_get_user(self, test_client, admin_token):
        # First get all users to find an ID
        resp = test_client.post(
            "/api/admin/users",
            json={"page": 1, "itemsPerPage": 10, "sortBy": [], "filters": {}},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        user_id = resp.json()["data"]["users"][0]["userId"]

        resp = test_client.get(
            f"/api/admin/user?userId={user_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] is True


class TestAdminComputers:

    def test_get_computers(self, test_client, admin_token):
        resp = test_client.get(
            "/api/admin/computers",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] is True
        assert "computers" in data["data"]
        assert len(data["data"]["computers"]) >= 1  # server1

    def test_get_computer(self, test_client, admin_token):
        # Get computers list first
        resp = test_client.get(
            "/api/admin/computers",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        computer_id = resp.json()["data"]["computers"][0]["computerId"]

        resp = test_client.get(
            f"/api/admin/computer?computerId={computer_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] is True


class TestAdminContainers:

    def test_get_containers(self, test_client, admin_token):
        resp = test_client.get(
            "/api/admin/containers",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] is True
        assert "containers" in data["data"]
        assert len(data["data"]["containers"]) >= 1  # ubuntu-base

    def test_get_container(self, test_client, admin_token):
        resp = test_client.get(
            "/api/admin/containers",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        container_id = resp.json()["data"]["containers"][0]["containerId"]

        resp = test_client.get(
            f"/api/admin/container?containerId={container_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] is True


class TestAdminRoles:

    def test_get_roles(self, test_client, admin_token):
        resp = test_client.get(
            "/api/admin/roles",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] is True
        role_names = [r["name"] for r in data["data"]["roles"]]
        assert "admin" in role_names
        assert "everyone" in role_names

    def test_create_role(self, test_client, admin_token):
        resp = test_client.post(
            "/api/admin/save_role?name=testrole",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] is True

    def test_create_role_reserved_name_admin(self, test_client, admin_token):
        resp = test_client.post(
            "/api/admin/save_role?name=admin",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] is False

    def test_create_role_reserved_name_everyone(self, test_client, admin_token):
        resp = test_client.post(
            "/api/admin/save_role?name=everyone",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] is False

    def test_remove_role(self, test_client, admin_token):
        # Create a role first
        test_client.post(
            "/api/admin/save_role?name=deleteme",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        # Get all roles to find its ID
        resp = test_client.get(
            "/api/admin/roles",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        role_id = None
        for r in resp.json()["data"]["roles"]:
            if r["name"] == "deleteme":
                role_id = r["roleId"]
                break
        assert role_id is not None

        resp = test_client.post(
            f"/api/admin/remove_role?roleId={role_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] is True


class TestAdminGeneralSettings:

    def test_get_general_settings(self, test_client, admin_token):
        resp = test_client.get(
            "/api/admin/general-settings",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] is True

    def test_get_general_settings_requires_admin(self, test_client, user_token):
        resp = test_client.get(
            "/api/admin/general-settings",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert resp.status_code == 401


class TestAdminReservations:

    def test_get_reservations(self, test_client, admin_token):
        resp = test_client.post(
            "/api/admin/reservations",
            json={"page": 1, "itemsPerPage": 10, "sortBy": [], "filters": {}},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] is True
        assert "reservations" in data["data"]
        assert "totalItems" in data["data"]

    def test_get_reservations_with_pagination(self, test_client, admin_token):
        resp = test_client.post(
            "/api/admin/reservations",
            json={"page": 1, "itemsPerPage": 5, "sortBy": [], "filters": {}},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] is True

    def test_get_reservations_requires_admin(self, test_client, user_token):
        resp = test_client.post(
            "/api/admin/reservations",
            json={"page": 1, "itemsPerPage": 10, "sortBy": [], "filters": {}},
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert resp.status_code == 401


class TestAdminHardware:

    def test_get_hardware(self, test_client, admin_token):
        resp = test_client.get(
            "/api/admin/hardware",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] is True
        assert "hardware" in data["data"]
        # Should have cpus, ram, gpus from seed data
        types = [h["type"] for h in data["data"]["hardware"]]
        assert "cpus" in types
        assert "ram" in types

    def test_get_hardware_requires_admin(self, test_client, user_token):
        resp = test_client.get(
            "/api/admin/hardware",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert resp.status_code == 401


class TestAdminContainerDefaults:

    def test_get_container_defaults(self, test_client, admin_token):
        resp = test_client.get(
            "/api/admin/container_defaults",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] is True
        defaults = data["data"]
        assert "dockerfileBody" in defaults
        assert "containerCmd" in defaults
        assert "passwordCommand" in defaults

    def test_get_container_defaults_custom_username(self, test_client, admin_token):
        resp = test_client.get(
            "/api/admin/container_defaults?username=student",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "student" in data["dockerfileBody"]


class TestAdminServerMonitoring:

    def test_get_servers_for_monitoring(self, test_client, admin_token):
        resp = test_client.get(
            "/api/admin/servers",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] is True
