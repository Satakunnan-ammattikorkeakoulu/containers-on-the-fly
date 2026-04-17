"""Integration tests for /api/admin endpoints."""

import datetime
from unittest.mock import patch

import database as db
from sqlalchemy import select


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

    def test_get_user_includes_roles(self, test_client, admin_token):
        """get_user response includes the user's roles list."""
        # Get admin user ID
        resp = test_client.post(
            "/api/admin/users",
            json={"page": 1, "itemsPerPage": 10, "sortBy": [], "filters": {}},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        admin_user = next(
            u for u in resp.json()["data"]["users"] if u["email"] == "admin@foo.com"
        )

        resp = test_client.get(
            f"/api/admin/user?userId={admin_user['userId']}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        data = resp.json()["data"]["user"]
        assert "roles" in data
        assert "admin" in data["roles"]

    def test_get_user_roles_for_normal_user(self, test_client, admin_token):
        """Normal user without extra roles has empty roles list."""
        resp = test_client.post(
            "/api/admin/users",
            json={"page": 1, "itemsPerPage": 10, "sortBy": [], "filters": {}},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        normal_user = next(
            u for u in resp.json()["data"]["users"] if u["email"] == "user@foo.com"
        )

        resp = test_client.get(
            f"/api/admin/user?userId={normal_user['userId']}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        data = resp.json()["data"]["user"]
        assert "roles" in data
        assert isinstance(data["roles"], list)


class TestAdminUserName:
    """Tests for the name field in admin user management."""

    def test_get_users_includes_name(self, test_client, admin_token):
        resp = test_client.post(
            "/api/admin/users",
            json={"page": 1, "itemsPerPage": 10, "sortBy": [], "filters": {}},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        user = resp.json()["data"]["users"][0]
        assert "name" in user

    def test_get_user_includes_name(self, test_client, admin_token):
        # Get a user ID first
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
        assert "name" in resp.json()["data"]["user"]

    def test_save_user_sets_name(self, test_client, admin_token):
        # Get a user ID
        resp = test_client.post(
            "/api/admin/users",
            json={"page": 1, "itemsPerPage": 10, "sortBy": [], "filters": {}},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        users = resp.json()["data"]["users"]
        user = next(u for u in users if u["email"] == "user@foo.com")

        # Save with name
        resp = test_client.post(
            "/api/admin/save_user",
            json={
                "userId": user["userId"],
                "data": {
                    "email": "user@foo.com",
                    "name": "Admin Set Name",
                    "roles": user["roles"],
                },
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] is True

        # Verify name persisted
        resp = test_client.get(
            f"/api/admin/user?userId={user['userId']}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.json()["data"]["user"]["name"] == "Admin Set Name"

    def test_create_user_with_name(self, test_client, admin_token):
        resp = test_client.post(
            "/api/admin/save_user",
            json={
                "userId": -1,
                "data": {
                    "email": "named@foo.com",
                    "name": "New Named User",
                    "password": "testpass",
                    "roles": [],
                },
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] is True

        # Verify via users list
        resp = test_client.post(
            "/api/admin/users",
            json={"page": 1, "itemsPerPage": 50, "sortBy": [], "filters": {}},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        users = resp.json()["data"]["users"]
        named_user = next(u for u in users if u["email"] == "named@foo.com")
        assert named_user["name"] == "New Named User"


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


class TestAdminSaveContainer:
    """save_container rename guard and registry overwrite confirmation."""

    @staticmethod
    def _builder_payload(
        *,
        container_id=-1,
        image_name="new-image",
        confirm_overwrite=False,
        managed_externally=False,
    ):
        data = {
            "name": "New Container",
            "imageName": image_name,
            "description": "",
            "public": True,
            "managedExternally": managed_externally,
            "dockerfileCommands": "RUN echo hi",
            "baseImage": "ubuntu:24.04",
            "containerUsername": "user",
            "passwordCommand": "",
            "sshKeyDeployCommands": "",
            "containerCmd": '["/bin/bash"]',
            "ports": [{"serviceName": "SSH", "port": 22, "portType": "SSH"}],
            "removedPorts": [],
        }
        if confirm_overwrite:
            data["confirmOverwrite"] = True
        return {"containerId": container_id, "data": data}

    # -- Create path -------------------------------------------------------

    def test_create_triggers_overwrite_confirmation_on_registry_collision(
        self, test_client, admin_token
    ):
        with patch(
            "endpoints.responses.admin.image_exists_in_registry",
            return_value=True,
        ):
            resp = test_client.post(
                "/api/admin/save_container",
                json=self._builder_payload(image_name="collision-image"),
                headers={"Authorization": f"Bearer {admin_token}"},
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] is False
        assert body["data"]["needsOverwriteConfirmation"] is True
        assert body["data"]["imageName"] == "collision-image"
        # The container must not have been saved.
        with db.Session() as session:
            rows = session.execute(
                select(db.Container).where(db.Container.imageName == "collision-image")
            ).scalars().all()
            assert rows == []

    def test_create_bypasses_registry_check_with_confirm_overwrite(
        self, test_client, admin_token
    ):
        with patch(
            "endpoints.responses.admin.image_exists_in_registry",
            return_value=True,
        ) as mock_check:
            resp = test_client.post(
                "/api/admin/save_container",
                json=self._builder_payload(
                    image_name="confirmed-image", confirm_overwrite=True
                ),
                headers={"Authorization": f"Bearer {admin_token}"},
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] is True
        # Registry helper must NOT be called when confirmOverwrite is true.
        assert mock_check.call_count == 0
        # Audit log has the overwrite-confirmed entry.
        with db.Session() as session:
            logs = session.execute(
                select(db.AuditLog).where(
                    db.AuditLog.action == "CONTAINER_IMAGE_OVERWRITE_CONFIRMED"
                )
            ).scalars().all()
            assert len(logs) == 1

    def test_create_without_collision_succeeds(self, test_client, admin_token):
        with patch(
            "endpoints.responses.admin.image_exists_in_registry",
            return_value=False,
        ):
            resp = test_client.post(
                "/api/admin/save_container",
                json=self._builder_payload(image_name="fresh-image"),
                headers={"Authorization": f"Bearer {admin_token}"},
            )
        assert resp.status_code == 200
        assert resp.json()["status"] is True

    def test_create_when_registry_unreachable_succeeds(
        self, test_client, admin_token
    ):
        with patch(
            "endpoints.responses.admin.image_exists_in_registry",
            return_value=None,
        ):
            resp = test_client.post(
                "/api/admin/save_container",
                json=self._builder_payload(image_name="unknown-image"),
                headers={"Authorization": f"Bearer {admin_token}"},
            )
        assert resp.status_code == 200
        assert resp.json()["status"] is True

    def test_create_externally_managed_skips_registry_check(
        self, test_client, admin_token
    ):
        payload = self._builder_payload(
            image_name="external-image", managed_externally=True
        )
        with patch(
            "endpoints.responses.admin.image_exists_in_registry",
            return_value=True,
        ) as mock_check:
            resp = test_client.post(
                "/api/admin/save_container",
                json=payload,
                headers={"Authorization": f"Bearer {admin_token}"},
            )
        assert resp.status_code == 200
        assert resp.json()["status"] is True
        assert mock_check.call_count == 0

    # -- Edit path (rename guard) ------------------------------------------

    def _make_builder_container(self, *, built=False, building=False):
        with db.Session() as session:
            container = db.Container(
                public=True,
                name="Existing",
                imageName="existing-image",
                description="",
                managedExternally=False,
                dockerfileCommands="RUN echo hi",
                baseImage="ubuntu:24.04",
                containerUsername="user",
                containerCmd='["/bin/bash"]',
                buildStatus="building" if building else ("success" if built else None),
                lastBuiltAt=datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)
                if built else None,
            )
            container.containerPorts.append(
                db.ContainerPort(serviceName="SSH", port=22, portType="SSH")
            )
            session.add(container)
            session.commit()
            return container.containerId

    def test_rename_of_built_container_is_rejected(self, test_client, admin_token):
        container_id = self._make_builder_container(built=True)
        payload = self._builder_payload(
            container_id=container_id, image_name="renamed-image"
        )
        resp = test_client.post(
            "/api/admin/save_container",
            json=payload,
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] is False
        assert "locked" in body["message"].lower() or "cannot be changed" in body["message"].lower()
        # Name unchanged in DB.
        with db.Session() as session:
            container = session.get(db.Container, container_id)
            assert container.imageName == "existing-image"

    def test_rename_during_active_build_is_rejected(self, test_client, admin_token):
        container_id = self._make_builder_container(building=True)
        payload = self._builder_payload(
            container_id=container_id, image_name="renamed-image"
        )
        resp = test_client.post(
            "/api/admin/save_container",
            json=payload,
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] is False

    def test_rename_of_never_built_container_is_accepted(
        self, test_client, admin_token
    ):
        container_id = self._make_builder_container(built=False, building=False)
        payload = self._builder_payload(
            container_id=container_id, image_name="renamed-image"
        )
        # Edit path now runs the same registry check; mock no collision.
        with patch(
            "endpoints.responses.admin.image_exists_in_registry",
            return_value=False,
        ) as mock_check:
            resp = test_client.post(
                "/api/admin/save_container",
                json=payload,
                headers={"Authorization": f"Bearer {admin_token}"},
            )
        assert resp.status_code == 200
        assert resp.json()["status"] is True
        assert mock_check.call_count == 1
        with db.Session() as session:
            container = session.get(db.Container, container_id)
            assert container.imageName == "renamed-image"

    def test_edit_without_rename_of_built_container_is_accepted(
        self, test_client, admin_token
    ):
        container_id = self._make_builder_container(built=True)
        # Keep the same imageName; only change description-ish fields.
        payload = self._builder_payload(
            container_id=container_id, image_name="existing-image"
        )
        payload["data"]["description"] = "Updated description"
        resp = test_client.post(
            "/api/admin/save_container",
            json=payload,
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] is True

    def test_rename_allowed_when_switching_to_externally_managed(
        self, test_client, admin_token
    ):
        container_id = self._make_builder_container(built=True)
        payload = self._builder_payload(
            container_id=container_id,
            image_name="external-renamed",
            managed_externally=True,
        )
        resp = test_client.post(
            "/api/admin/save_container",
            json=payload,
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] is True
        with db.Session() as session:
            container = session.get(db.Container, container_id)
            assert container.imageName == "external-renamed"
            assert container.managedExternally is True

    def test_rename_of_unbuilt_container_with_collision_prompts_confirmation(
        self, test_client, admin_token
    ):
        container_id = self._make_builder_container(built=False, building=False)
        payload = self._builder_payload(
            container_id=container_id, image_name="colliding-new-name"
        )
        with patch(
            "endpoints.responses.admin.image_exists_in_registry",
            return_value=True,
        ):
            resp = test_client.post(
                "/api/admin/save_container",
                json=payload,
                headers={"Authorization": f"Bearer {admin_token}"},
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] is False
        assert body["data"]["needsOverwriteConfirmation"] is True
        assert body["data"]["imageName"] == "colliding-new-name"
        # Rename was NOT committed.
        with db.Session() as session:
            container = session.get(db.Container, container_id)
            assert container.imageName == "existing-image"

    def test_rename_of_unbuilt_triggers_rebuild(self, test_client, admin_token):
        container_id = self._make_builder_container(built=False, building=False)
        # Simulate prior failed build.
        with db.Session() as session:
            container = session.get(db.Container, container_id)
            container.buildStatus = "failed"
            container.buildLog = "old failure"
            session.commit()

        payload = self._builder_payload(
            container_id=container_id, image_name="renamed-retry"
        )
        with patch(
            "endpoints.responses.admin.image_exists_in_registry",
            return_value=False,
        ):
            resp = test_client.post(
                "/api/admin/save_container",
                json=payload,
                headers={"Authorization": f"Bearer {admin_token}"},
            )
        assert resp.status_code == 200
        assert resp.json()["status"] is True
        with db.Session() as session:
            container = session.get(db.Container, container_id)
            assert container.imageName == "renamed-retry"
            assert container.buildStatus == "pending"
            assert container.buildLog == ""

    def _create_via_endpoint(self, test_client, admin_token, image_name):
        resp = test_client.post(
            "/api/admin/save_container",
            json=self._builder_payload(image_name=image_name),
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        return resp.json()

    def test_rename_of_removed_rows_imagename_does_not_block_reuse(
        self, test_client, admin_token
    ):
        # Create + remove an externally-managed container, then create a new
        # one with the same imageName. Externally-managed is renamed to a
        # sentinel immediately, so the name is free right away.
        with db.Session() as session:
            container = db.Container(
                public=True,
                name="ExternalOld",
                imageName="reusable-name",
                description="",
                managedExternally=True,
            )
            container.containerPorts.append(
                db.ContainerPort(serviceName="SSH", port=22, portType="SSH")
            )
            session.add(container)
            session.commit()
            removed_id = container.containerId

        resp = test_client.post(
            f"/api/admin/remove_container?containerId={removed_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] is True

        # Verify the removed row's imageName was rewritten to the sentinel.
        with db.Session() as session:
            removed = session.get(db.Container, removed_id)
            assert removed.removed is True
            assert removed.imageName == f"__removed_{removed_id}__reusable-name"

        # Now the name is free — a fresh container can claim it.
        with patch(
            "endpoints.responses.admin.image_exists_in_registry",
            return_value=False,
        ):
            body = self._create_via_endpoint(test_client, admin_token, "reusable-name")
        assert body["status"] is True

    def test_image_builder_remove_defers_rename_until_daemon_ack(
        self, test_client, admin_token
    ):
        # Image Builder containers keep the original imageName until the
        # daemon confirms the real Docker image has been removed, because
        # the daemon needs the name to locate the image.
        container_id = self._make_builder_container(built=True)

        resp = test_client.post(
            f"/api/admin/remove_container?containerId={container_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] is True

        with db.Session() as session:
            container = session.get(db.Container, container_id)
            assert container.removed is True
            assert container.buildStatus == "removing"
            # imageName NOT yet renamed — daemon still needs it.
            assert container.imageName == "existing-image"

        # Simulate the daemon's report_image_removed callback.
        resp = test_client.post(
            f"/api/daemon/container/{container_id}/image-removed",
            json={"buildStatus": "removed"},
            headers={
                "X-Daemon-Api-Key": "test-daemon-api-key",
                "X-Daemon-Server-Name": "server1",
            },
        )
        assert resp.status_code == 200
        assert resp.json()["status"] is True

        with db.Session() as session:
            container = session.get(db.Container, container_id)
            assert container.imageName == f"__removed_{container_id}__existing-image"
            assert container.buildStatus == "removed"

    def test_rebuild_refuses_removed_container(self, test_client, admin_token):
        container_id = self._make_builder_container(built=True)
        # Mark removed directly in DB.
        with db.Session() as session:
            container = session.get(db.Container, container_id)
            container.removed = True
            session.commit()

        resp = test_client.post(
            f"/api/admin/rebuild_container_image?containerId={container_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] is False
        assert "removed" in body["message"].lower()

    def test_sentinel_rename_is_idempotent(self, test_client, admin_token):
        # Calling remove_container twice on the same externally-managed
        # container must not double-prefix the sentinel.
        with db.Session() as session:
            container = db.Container(
                public=True,
                name="Ext",
                imageName="ext-img",
                description="",
                managedExternally=True,
            )
            container.containerPorts.append(
                db.ContainerPort(serviceName="SSH", port=22, portType="SSH")
            )
            session.add(container)
            session.commit()
            cid = container.containerId

        for _ in range(2):
            resp = test_client.post(
                f"/api/admin/remove_container?containerId={cid}",
                headers={"Authorization": f"Bearer {admin_token}"},
            )
            assert resp.status_code == 200

        with db.Session() as session:
            c = session.get(db.Container, cid)
            assert c.imageName == f"__removed_{cid}__ext-img"

    def test_edit_with_confirm_overwrite_logs_audit(
        self, test_client, admin_token
    ):
        container_id = self._make_builder_container(built=False, building=False)
        payload = self._builder_payload(
            container_id=container_id,
            image_name="confirmed-rename",
            confirm_overwrite=True,
        )
        with patch(
            "endpoints.responses.admin.image_exists_in_registry",
            return_value=True,
        ) as mock_check:
            resp = test_client.post(
                "/api/admin/save_container",
                json=payload,
                headers={"Authorization": f"Bearer {admin_token}"},
            )
        assert resp.status_code == 200
        assert resp.json()["status"] is True
        # Registry must NOT be consulted when confirmOverwrite is true.
        assert mock_check.call_count == 0
        with db.Session() as session:
            logs = session.execute(
                select(db.AuditLog).where(
                    db.AuditLog.action == "CONTAINER_IMAGE_OVERWRITE_CONFIRMED",
                    db.AuditLog.resourceId == container_id,
                )
            ).scalars().all()
            assert len(logs) == 1


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


class TestAdminSaveComputer:

    def test_requires_admin(self, test_client, user_token, seed_test_data):
        resp = test_client.post(
            "/api/admin/save_computer",
            json={"computerId": 1, "data": {"name": "hack-server"}},
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert resp.status_code == 401


class TestAdminEditReservation:

    def _create_reservation_for_admin_test(self):
        from datetime import datetime, timezone, timedelta
        now = datetime.now(timezone.utc)
        with db.Session() as session:
            computer = session.execute(
                select(db.Computer).where(db.Computer.name == "server1")
            ).scalar_one()
            user = session.execute(
                select(db.User).where(db.User.email == "user@foo.com")
            ).scalar_one()
            container = session.execute(
                select(db.Container).where(db.Container.imageName == "ubuntu-base")
            ).scalar_one()
            rc = db.ReservedContainer(containerId=container.containerId)
            session.add(rc)
            session.flush()
            res = db.Reservation(
                userId=user.userId,
                computerId=computer.computerId,
                reservedContainerId=rc.reservedContainerId,
                startDate=now,
                endDate=now + timedelta(hours=4),
                status="reserved",
            )
            session.add(res)
            session.flush()
            res_id = res.reservationId
            session.commit()
            return res_id

    def test_admin_can_edit_reservation(self, test_client, admin_token, seed_test_data):
        from datetime import datetime, timezone, timedelta
        res_id = self._create_reservation_for_admin_test()
        new_end = (datetime.now(timezone.utc) + timedelta(hours=8)).isoformat()
        resp = test_client.post(
            f"/api/admin/edit_reservation?reservationId={res_id}&endDate={new_end}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] is True

    def test_rejects_non_admin(self, test_client, user_token, seed_test_data):
        resp = test_client.post(
            "/api/admin/edit_reservation?reservationId=1&endDate=2025-01-01T00:00:00",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert resp.status_code == 401

    def test_nonexistent_reservation(self, test_client, admin_token, seed_test_data):
        resp = test_client.post(
            "/api/admin/edit_reservation?reservationId=99999&endDate=2025-01-01T00:00:00",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] is False


class TestAdminServerMonitoring:

    def test_get_servers_for_monitoring(self, test_client, admin_token):
        resp = test_client.get(
            "/api/admin/servers",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] is True
