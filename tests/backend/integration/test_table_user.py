"""Integration tests for helpers/tables/user.py CRUD operations.

Note: get_users() and get_user() internally call cast_users_to_dict() which
references a non-existent 'userStorage' attribute. Those functions are
exercised via the endpoint test layer instead. This file tests the functions
that work independently: add_user, get_user_serverside.
"""

import database as db
from sqlalchemy import select
from helpers.tables.user import add_user, get_user_serverside


class TestAddUser:

    def test_creates_user(self):
        add_user("new@example.com", "secretpass")
        user = get_user_serverside("new@example.com")
        assert user is not None
        assert user.email == "new@example.com"

    def test_password_is_hashed(self):
        add_user("hashed@example.com", "plaintext")
        with db.Session() as s:
            user = s.execute(select(db.User).where(db.User.email == "hashed@example.com")).scalar_one()
            assert user.password != "plaintext"
            assert user.passwordSalt is not None


class TestGetUserServerside:

    def test_by_email(self, seed_test_data):
        user = get_user_serverside("admin@foo.com")
        assert user is not None
        assert user.email == "admin@foo.com"

    def test_by_id(self, seed_test_data):
        user_by_email = get_user_serverside("admin@foo.com")
        user_by_id = get_user_serverside(str(user_by_email.userId))
        assert user_by_id is not None
        assert user_by_id.email == "admin@foo.com"

    def test_not_found(self):
        assert get_user_serverside("ghost@example.com") is None

    def test_none_input(self):
        assert get_user_serverside(None) is None

    def test_non_numeric_non_email(self):
        assert get_user_serverside("not-an-id-or-email") is None
