"""Integration tests for helpers/tables/user_access_control.py operations."""

from helpers.tables.user_access_control import (
    get_blacklisted_emails, set_blacklisted_emails,
    get_whitelisted_emails, set_whitelisted_emails,
)


class TestBlacklist:

    def test_get_empty(self):
        assert get_blacklisted_emails() == []

    def test_set_and_get(self):
        set_blacklisted_emails(["bad@test.com", "evil@test.com"])
        result = get_blacklisted_emails()
        assert sorted(result) == ["bad@test.com", "evil@test.com"]

    def test_replaces_existing(self):
        set_blacklisted_emails(["old@test.com"])
        set_blacklisted_emails(["new@test.com"])
        result = get_blacklisted_emails()
        assert result == ["new@test.com"]

    def test_skips_empty_strings(self):
        set_blacklisted_emails(["valid@test.com", "", "  ", "also@test.com"])
        result = get_blacklisted_emails()
        assert sorted(result) == ["also@test.com", "valid@test.com"]

    def test_returns_true_on_success(self):
        assert set_blacklisted_emails(["x@test.com"]) is True

    def test_clear_all(self):
        set_blacklisted_emails(["old@test.com"])
        set_blacklisted_emails([])
        assert get_blacklisted_emails() == []


class TestWhitelist:

    def test_get_empty(self):
        assert get_whitelisted_emails() == []

    def test_set_and_get(self):
        set_whitelisted_emails(["good@test.com", "vip@test.com"])
        result = get_whitelisted_emails()
        assert sorted(result) == ["good@test.com", "vip@test.com"]

    def test_replaces_existing(self):
        set_whitelisted_emails(["old@test.com"])
        set_whitelisted_emails(["new@test.com"])
        result = get_whitelisted_emails()
        assert result == ["new@test.com"]

    def test_skips_empty_strings(self):
        set_whitelisted_emails(["valid@test.com", "", "  "])
        result = get_whitelisted_emails()
        assert result == ["valid@test.com"]

    def test_returns_true_on_success(self):
        assert set_whitelisted_emails(["x@test.com"]) is True
