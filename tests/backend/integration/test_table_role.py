"""Integration tests for helpers/tables/role.py CRUD and related operations."""

import database as db
from sqlalchemy import select
from helpers.tables.role import (
    get_roles, get_roles_with_mount_counts, get_role_by_id,
    is_role_name_taken, validate_role_name,
    add_role, edit_role, remove_role,
    get_role_mounts, save_role_mounts,
    get_role_hardware_limits, save_role_hardware_limits,
    get_role_reservation_limits, save_role_reservation_limits,
)


class TestGetRoles:

    def test_returns_built_in_roles(self):
        roles = get_roles()
        names = [r.name for r in roles]
        assert "everyone" in names
        assert "admin" in names

    def test_includes_added_roles(self):
        add_role("testers")
        roles = get_roles()
        names = [r.name for r in roles]
        assert "testers" in names


class TestGetRolesWithMountCounts:

    def test_returns_dicts_with_mount_count(self):
        result = get_roles_with_mount_counts()
        assert isinstance(result, list)
        for r in result:
            assert "mountCount" in r
            assert isinstance(r["mountCount"], int)


class TestGetRoleById:

    def test_found(self):
        roles = get_roles()
        role = get_role_by_id(roles[0].roleId)
        assert role is not None

    def test_not_found(self):
        assert get_role_by_id(99999) is None


class TestIsRoleNameTaken:

    def test_taken(self):
        with db.Session() as session:
            assert is_role_name_taken(session, "admin") is True

    def test_not_taken(self):
        with db.Session() as session:
            assert is_role_name_taken(session, "unique_role_xyz") is False

    def test_case_insensitive(self):
        with db.Session() as session:
            assert is_role_name_taken(session, "ADMIN") is True

    def test_exclude_self(self):
        with db.Session() as session:
            admin_role = session.execute(
                select(db.Role).where(db.Role.name == "admin")
            ).scalar_one()
            assert is_role_name_taken(session, "admin", excludeRoleId=admin_role.roleId) is False


class TestValidateRoleName:

    def test_empty_name(self):
        valid, msg = validate_role_name("")
        assert valid is False
        assert "required" in msg.lower()

    def test_whitespace_only(self):
        valid, msg = validate_role_name("   ")
        assert valid is False

    def test_reserved_admin(self):
        valid, msg = validate_role_name("admin")
        assert valid is False
        assert "reserved" in msg.lower()

    def test_reserved_everyone(self):
        valid, msg = validate_role_name("Everyone")
        assert valid is False

    def test_valid_name(self):
        valid, msg = validate_role_name("developers")
        assert valid is True
        assert msg == ""


class TestAddRole:

    def test_creates_role(self):
        success, msg, role_dict = add_role("scientists")
        assert success is True
        assert role_dict is not None
        assert role_dict["name"] == "scientists"

    def test_duplicate_fails(self):
        add_role("engineers")
        success, msg, _ = add_role("engineers")
        assert success is False
        assert "already exists" in msg

    def test_reserved_name_fails(self):
        success, msg, _ = add_role("admin")
        assert success is False


class TestEditRole:

    def test_updates_name(self):
        _, _, role_dict = add_role("old_name")
        success, msg, updated = edit_role(role_dict["roleId"], "new_name")
        assert success is True
        assert updated["name"] == "new_name"

    def test_not_found(self):
        success, msg, _ = edit_role(99999, "whatever")
        assert success is False
        assert "not found" in msg.lower()

    def test_reserved_name_blocked(self):
        _, _, role_dict = add_role("temp_role")
        success, msg, _ = edit_role(role_dict["roleId"], "admin")
        assert success is False


class TestRemoveRole:

    def test_removes_custom_role(self):
        _, _, role_dict = add_role("disposable")
        success, msg = remove_role(role_dict["roleId"])
        assert success is True
        assert get_role_by_id(role_dict["roleId"]) is None

    def test_blocks_builtin_admin(self):
        roles = get_roles()
        admin = next(r for r in roles if r.name == "admin")
        success, msg = remove_role(admin.roleId)
        assert success is False
        assert "built-in" in msg.lower()

    def test_blocks_builtin_everyone(self):
        roles = get_roles()
        everyone = next(r for r in roles if r.name == "everyone")
        success, msg = remove_role(everyone.roleId)
        assert success is False

    def test_not_found(self):
        success, msg = remove_role(99999)
        assert success is False


class TestRoleMounts:

    def test_get_mounts_empty(self):
        _, _, role_dict = add_role("no_mounts")
        mounts = get_role_mounts(role_dict["roleId"])
        assert mounts == []

    def test_save_and_get_mounts(self, seed_test_data):
        _, _, role_dict = add_role("with_mounts")
        from helpers.tables.computer import get_computers
        computers = get_computers()
        comp_id = computers[0].computerId

        mounts = [
            {"computerId": comp_id, "hostPath": "/data/shared",
             "containerPath": "/mnt/shared", "readOnly": True},
        ]
        success, msg = save_role_mounts(role_dict["roleId"], mounts)
        assert success is True

        result = get_role_mounts(role_dict["roleId"])
        assert len(result) == 1
        assert result[0]["hostPath"] == "/data/shared"
        assert result[0]["readOnly"] is True

    def test_save_replaces_existing(self, seed_test_data):
        _, _, role_dict = add_role("replace_mounts")
        from helpers.tables.computer import get_computers
        comp_id = get_computers()[0].computerId

        save_role_mounts(role_dict["roleId"], [
            {"computerId": comp_id, "hostPath": "/old", "containerPath": "/old"},
        ])
        save_role_mounts(role_dict["roleId"], [
            {"computerId": comp_id, "hostPath": "/new", "containerPath": "/new"},
        ])

        result = get_role_mounts(role_dict["roleId"])
        assert len(result) == 1
        assert result[0]["hostPath"] == "/new"

    def test_missing_fields_fails(self):
        _, _, role_dict = add_role("bad_mounts")
        success, msg = save_role_mounts(role_dict["roleId"], [{"hostPath": "/x"}])
        assert success is False

    def test_role_not_found(self):
        assert get_role_mounts(99999) == []


class TestRoleReservationLimits:

    def test_admin_defaults(self):
        roles = get_roles()
        admin = next(r for r in roles if r.name == "admin")
        limits = get_role_reservation_limits(admin.roleId)
        assert limits["minDuration"] == 1
        assert limits["maxDuration"] == 1440
        assert limits["maxActiveReservations"] == 99

    def test_regular_role_defaults(self):
        roles = get_roles()
        everyone = next(r for r in roles if r.name == "everyone")
        limits = get_role_reservation_limits(everyone.roleId)
        assert limits["minDuration"] == 1
        assert limits["maxDuration"] == 48
        assert limits["maxActiveReservations"] == 1

    def test_save_and_get(self):
        _, _, role_dict = add_role("limited_role")
        success, msg = save_role_reservation_limits(role_dict["roleId"], {
            "minDuration": 2,
            "maxDuration": 24,
            "maxActiveReservations": 3,
        })
        assert success is True

        limits = get_role_reservation_limits(role_dict["roleId"])
        assert limits["minDuration"] == 2
        assert limits["maxDuration"] == 24
        assert limits["maxActiveReservations"] == 3

    def test_min_exceeds_max_fails(self):
        _, _, role_dict = add_role("bad_limits")
        success, msg = save_role_reservation_limits(role_dict["roleId"], {
            "minDuration": 100,
            "maxDuration": 10,
            "maxActiveReservations": 1,
        })
        assert success is False
        assert "cannot be greater" in msg.lower()

    def test_out_of_range_fails(self):
        _, _, role_dict = add_role("range_limits")
        success, msg = save_role_reservation_limits(role_dict["roleId"], {
            "minDuration": 0,
            "maxDuration": 24,
            "maxActiveReservations": 1,
        })
        assert success is False

    def test_missing_field_fails(self):
        _, _, role_dict = add_role("missing_limits")
        success, msg = save_role_reservation_limits(role_dict["roleId"], {
            "minDuration": 1,
        })
        assert success is False

    def test_role_not_found(self):
        assert get_role_reservation_limits(99999) == {}
