"""Tests for helpers/auth.py — pure functions only (no DB)."""

import string
from helpers.auth import (
    hash_password,
    is_correct_password,
    create_login_token,
    create_password,
)


# ---------------------------------------------------------------------------
# hash_password
# ---------------------------------------------------------------------------

class TestHashPassword:

    def test_returns_salt_and_hashed_password(self):
        result = hash_password("test")
        assert "salt" in result
        assert "hashedPassword" in result
        assert isinstance(result["salt"], bytes)
        assert isinstance(result["hashedPassword"], bytes)

    def test_salt_is_16_bytes(self):
        result = hash_password("test")
        assert len(result["salt"]) == 16

    def test_unique_salts_per_call(self):
        a = hash_password("test")
        b = hash_password("test")
        assert a["salt"] != b["salt"]

    def test_different_hashes_for_different_passwords(self):
        a = hash_password("alpha")
        b = hash_password("bravo")
        assert a["hashedPassword"] != b["hashedPassword"]


# ---------------------------------------------------------------------------
# is_correct_password
# ---------------------------------------------------------------------------

class TestIsCorrectPassword:

    def test_correct_password_returns_true(self):
        h = hash_password("secret")
        assert is_correct_password(h["salt"], h["hashedPassword"], "secret") is True

    def test_wrong_password_returns_false(self):
        h = hash_password("secret")
        assert is_correct_password(h["salt"], h["hashedPassword"], "wrong") is False

    def test_empty_password_returns_false(self):
        h = hash_password("secret")
        assert is_correct_password(h["salt"], h["hashedPassword"], "") is False


# ---------------------------------------------------------------------------
# create_login_token
# ---------------------------------------------------------------------------

class TestCreateLoginToken:

    def test_length_is_100(self):
        token = create_login_token()
        assert len(token) == 100

    def test_allowed_characters_only(self):
        allowed = set(string.ascii_letters + string.digits + "!_-")
        token = create_login_token()
        assert all(c in allowed for c in token)

    def test_two_tokens_are_different(self):
        assert create_login_token() != create_login_token()


# ---------------------------------------------------------------------------
# create_password
# ---------------------------------------------------------------------------

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
