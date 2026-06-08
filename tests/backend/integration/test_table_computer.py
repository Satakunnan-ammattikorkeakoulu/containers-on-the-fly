"""Integration tests for helpers/tables/computer.py CRUD operations.

Note: add_computer() does not accept an 'ip' parameter, but the Computer
model requires ip (NOT NULL). Tests that create computers use the
seed_test_data fixture or direct Session access.
"""

import database as db
from sqlalchemy import select
from helpers.tables.computer import (
    get_computers, remove_computer, edit_computer,
)


def _create_computer(name, public=True, ip="10.0.0.1"):
    """Create a computer directly via Session to provide all required fields."""
    with db.Session() as session:
        comp = db.Computer(name=name, public=public, ip=ip)
        session.add(comp)
        session.commit()
        return session.execute(
            select(db.Computer).where(db.Computer.name == name)
        ).scalar_one()


class TestGetComputers:

    def test_returns_all(self, seed_test_data):
        result = get_computers()
        assert isinstance(result, list)
        assert len(result) >= 1

    def test_filter_by_name(self, seed_test_data):
        result = get_computers(filter="server1")
        assert result is not None
        assert len(result) == 1
        assert result[0].name == "server1"

    def test_filter_by_id(self, seed_test_data):
        all_comps = get_computers()
        comp_id = all_comps[0].computerId
        result = get_computers(filter=str(comp_id))
        assert result is not None
        assert result[0].computerId == comp_id

    def test_filter_no_match(self):
        result = get_computers(filter="nonexistent")
        assert result is None

    def test_filter_non_numeric_no_match(self):
        result = get_computers(filter="abc-xyz")
        assert result is None


class TestRemoveComputer:

    def test_removes_computer(self):
        comp = _create_computer("to-remove")
        remove_computer(comp.computerId)
        result = get_computers(filter="to-remove")
        assert result is None


class TestEditComputer:

    def test_edit_name(self):
        comp = _create_computer("old-name")
        edit_computer(comp.computerId, new_name="new-name")
        result = get_computers(filter="new-name")
        assert result is not None
        assert result[0].name == "new-name"

    def test_edit_public(self):
        comp = _create_computer("pub-test", public=True)
        edit_computer(comp.computerId, new_public=False)
        result = get_computers(filter="pub-test")
        assert result[0].public is False

    def test_edit_no_changes(self):
        comp = _create_computer("no-change")
        edit_computer(comp.computerId)
        result = get_computers(filter="no-change")
        assert result is not None
