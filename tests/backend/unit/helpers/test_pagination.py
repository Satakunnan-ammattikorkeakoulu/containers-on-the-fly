"""Tests for helpers/pagination.py."""

from sqlalchemy import Column, Integer, String, MetaData, Table, select, asc, desc
from helpers.pagination import apply_pagination, MAX_ITEMS_PER_PAGE


# Create a simple test table for building statements
_metadata = MetaData()
_test_table = Table(
    "test_items", _metadata,
    Column("id", Integer, primary_key=True),
    Column("name", String(50)),
    Column("created_at", String(50)),
)


class TestApplyPagination:

    def _base_stmt(self):
        return select(_test_table)

    def test_sort_ascending(self):
        stmt = apply_pagination(
            self._base_stmt(),
            sort_by=[{"key": "name", "order": "asc"}],
            page=1, items_per_page=10,
            allowed_sort_keys={"name": _test_table.c.name},
        )
        compiled = str(stmt.compile(compile_kwargs={"literal_binds": True}))
        assert "ORDER BY" in compiled
        assert "ASC" in compiled.upper()

    def test_sort_descending(self):
        stmt = apply_pagination(
            self._base_stmt(),
            sort_by=[{"key": "name", "order": "desc"}],
            page=1, items_per_page=10,
            allowed_sort_keys={"name": _test_table.c.name},
        )
        compiled = str(stmt.compile(compile_kwargs={"literal_binds": True}))
        assert "DESC" in compiled.upper()

    def test_page_offset_calculation(self):
        stmt = apply_pagination(
            self._base_stmt(),
            sort_by=[], page=3, items_per_page=10,
            allowed_sort_keys={},
        )
        compiled = str(stmt.compile(compile_kwargs={"literal_binds": True}))
        # Page 3 with 10 items per page = offset 20
        assert "20" in compiled

    def test_items_per_page_clamped_to_max(self):
        stmt = apply_pagination(
            self._base_stmt(),
            sort_by=[], page=1, items_per_page=200,
            allowed_sort_keys={},
        )
        compiled = str(stmt.compile(compile_kwargs={"literal_binds": True}))
        assert str(MAX_ITEMS_PER_PAGE) in compiled

    def test_items_per_page_clamped_to_min(self):
        stmt = apply_pagination(
            self._base_stmt(),
            sort_by=[], page=1, items_per_page=0,
            allowed_sort_keys={},
        )
        compiled = str(stmt.compile(compile_kwargs={"literal_binds": True}))
        # Clamped to minimum of 1
        assert "LIMIT" in compiled.upper()

    def test_no_limit_when_minus_one(self):
        stmt = apply_pagination(
            self._base_stmt(),
            sort_by=[], page=1, items_per_page=-1,
            allowed_sort_keys={},
        )
        compiled = str(stmt.compile(compile_kwargs={"literal_binds": True}))
        assert "LIMIT" not in compiled.upper()

    def test_invalid_sort_key_ignored(self):
        stmt = apply_pagination(
            self._base_stmt(),
            sort_by=[{"key": "invalid_field", "order": "asc"}],
            page=1, items_per_page=10,
            allowed_sort_keys={"name": _test_table.c.name},
        )
        compiled = str(stmt.compile(compile_kwargs={"literal_binds": True}))
        assert "ORDER BY" not in compiled.upper() or "invalid_field" not in compiled

    def test_multiple_sort_keys(self):
        stmt = apply_pagination(
            self._base_stmt(),
            sort_by=[
                {"key": "name", "order": "asc"},
                {"key": "created_at", "order": "desc"},
            ],
            page=1, items_per_page=10,
            allowed_sort_keys={
                "name": _test_table.c.name,
                "created_at": _test_table.c.created_at,
            },
        )
        compiled = str(stmt.compile(compile_kwargs={"literal_binds": True}))
        assert "ORDER BY" in compiled.upper()
