"""Tests for container server helpers/utils.py."""

import string
from helpers.utils import create_password


class TestCreatePassword:

    def test_default_length_is_40(self):
        assert len(create_password()) == 40

    def test_custom_length(self):
        assert len(create_password(20)) == 20

    def test_alphanumeric_only(self):
        allowed = set(string.ascii_letters + string.digits)
        pw = create_password()
        assert all(c in allowed for c in pw)

    def test_two_passwords_are_different(self):
        assert create_password() != create_password()

    def test_zero_length_returns_empty(self):
        assert create_password(0) == ""
