"""Integration tests for helpers/tables/user_whitelist.py operations."""

from helpers.tables.user_whitelist import (
    view_all, add_to_whitelist, remove_from_whitelist,
)


class TestViewAll:

    def test_returns_empty_initially(self):
        result = view_all()
        assert isinstance(result, list)
        assert len(result) == 0

    def test_returns_all_after_adding(self):
        add_to_whitelist("a@test.com")
        add_to_whitelist("b@test.com")
        result = view_all()
        assert len(result) == 2

    def test_filter_by_email(self):
        add_to_whitelist("filter@test.com")
        result = view_all(opt_filter="filter@test.com")
        assert len(result) == 1
        assert result[0].email == "filter@test.com"

    def test_filter_no_match(self):
        result = view_all(opt_filter="ghost@test.com")
        assert result == []


class TestAddToWhitelist:

    def test_adds_email(self):
        result = add_to_whitelist("new@test.com")
        assert result == {"msg": "success"}
        assert len(view_all(opt_filter="new@test.com")) == 1

    def test_duplicate_returns_none(self):
        add_to_whitelist("dup@test.com")
        result = add_to_whitelist("dup@test.com")
        assert result is None


class TestRemoveFromWhitelist:

    def test_removes_email(self):
        add_to_whitelist("rm@test.com")
        result = remove_from_whitelist("rm@test.com")
        assert result == {"msg": "success"}
        assert view_all(opt_filter="rm@test.com") == []

    def test_not_found_returns_none(self):
        result = remove_from_whitelist("ghost@test.com")
        assert result is None
