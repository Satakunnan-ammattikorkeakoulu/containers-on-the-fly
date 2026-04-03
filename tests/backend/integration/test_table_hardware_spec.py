"""Integration tests for helpers/tables/hardware_spec.py CRUD operations."""

import database as db
from sqlalchemy import select
from helpers.tables.hardware_spec import (
    get_hardware_specs, add_hardware_spec, remove_hardware_spec,
    edit_hardware_spec,
)


def _create_computer(name="hw-server", ip="10.0.0.5"):
    """Create a computer with all required fields and return its ID."""
    with db.Session() as session:
        comp = db.Computer(name=name, public=True, ip=ip)
        session.add(comp)
        session.commit()
        return session.execute(
            select(db.Computer).where(db.Computer.name == name)
        ).scalar_one().computerId


class TestGetHardwareSpecs:

    def test_returns_all(self, seed_test_data):
        result = get_hardware_specs()
        assert isinstance(result, list)
        assert len(result) >= 3  # cpus, ram, gpus from seed

    def test_filter_by_id(self, seed_test_data):
        all_specs = get_hardware_specs()
        spec_id = all_specs[0].hardwareSpecId
        result = get_hardware_specs(filter=str(spec_id))
        assert result is not None
        assert len(result) == 1
        assert result[0].hardwareSpecId == spec_id

    def test_filter_no_match(self):
        result = get_hardware_specs(filter="99999")
        assert result is None

    def test_filter_non_numeric(self):
        result = get_hardware_specs(filter="abc")
        assert result is None


class TestAddHardwareSpec:

    def test_creates_spec(self):
        comp_id = _create_computer("add-hw-server")
        add_hardware_spec(comp_id, "cpu", 16, 1, 8, 2, "cores")
        specs = get_hardware_specs()
        assert any(s.type == "cpu" and s.maximumAmount == 16 for s in specs)


class TestRemoveHardwareSpec:

    def test_removes_spec(self):
        comp_id = _create_computer("rm-hw-server")
        add_hardware_spec(comp_id, "ram", 64, 1, 32, 8, "GB")
        specs = get_hardware_specs()
        ram_spec = next(s for s in specs if s.type == "ram" and s.maximumAmount == 64)
        remove_hardware_spec(ram_spec.hardwareSpecId)
        result = get_hardware_specs(filter=str(ram_spec.hardwareSpecId))
        assert result is None


class TestEditHardwareSpec:

    def test_edit_all_fields(self):
        comp_id = _create_computer("edit-hw-server")
        add_hardware_spec(comp_id, "gpu", 4, 0, 2, 0, "GPUs")
        specs = get_hardware_specs()
        spec = next(s for s in specs if s.type == "gpu" and s.maximumAmount == 4)

        edit_hardware_spec(
            spec.hardwareSpecId,
            new_computer_id=None,
            new_type="gpu",
            new_max=8,
            new_min=1,
            new_user_max=4,
            new_user_default=1,
            new_format="GPUs",
        )

        result = get_hardware_specs(filter=str(spec.hardwareSpecId))
        assert result[0].maximumAmount == 8
        assert result[0].minimumAmount == 1

    def test_edit_partial_fields(self):
        comp_id = _create_computer("partial-hw-server")
        add_hardware_spec(comp_id, "cpu", 8, 1, 4, 2, "cores")
        specs = get_hardware_specs()
        spec = next(s for s in specs if s.type == "cpu" and s.maximumAmount == 8)

        edit_hardware_spec(
            spec.hardwareSpecId,
            new_computer_id=None,
            new_type=None,
            new_max=16,
            new_min=None,
            new_user_max=None,
            new_user_default=None,
            new_format=None,
        )

        result = get_hardware_specs(filter=str(spec.hardwareSpecId))
        assert result[0].maximumAmount == 16
        assert result[0].type == "cpu"  # unchanged
