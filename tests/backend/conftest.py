"""
Shared test configuration for backend tests.

Module-level setup:
  1. Adds webapp/backend to sys.path
  2. Changes CWD to webapp/backend so settings.json is found on initial import
  3. Patches settings_handler to use test_settings.json (SQLite in-memory)
  4. Creates a SQLite in-memory engine and patches the database module
  5. Creates all ORM tables
"""

import sys
import os
import base64
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# 1. Path and CWD setup
# ---------------------------------------------------------------------------
_backend_dir = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "webapp", "backend")
)
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

_original_cwd = os.getcwd()
os.chdir(_backend_dir)

# ---------------------------------------------------------------------------
# 2. Mock system-level dependencies that may not be installed in test env
# ---------------------------------------------------------------------------
try:
    import ldap  # noqa: F401
except ImportError:
    sys.modules["ldap"] = MagicMock()

# ---------------------------------------------------------------------------
# 3. Patch settings_handler to use test settings (SQLite URI)
# ---------------------------------------------------------------------------
import settings_handler as _sh_module

_test_settings_path = os.path.join(os.path.dirname(__file__), "test_settings.json")
_test_settings = _sh_module.UnifiedSettings(config_location=_test_settings_path)

_sh_module.settings_handler = _test_settings
_sh_module.get_setting = _test_settings.get_setting
_sh_module.set_setting = _test_settings.set_setting
_sh_module.get_multiple_settings = _test_settings.get_multiple_settings

# ---------------------------------------------------------------------------
# 4. Create SQLite in-memory engine and patch database module
#    database.py calls create_engine() at import time with MySQL-specific pool
#    args (max_overflow) that SQLite rejects. We intercept the import by
#    temporarily replacing sqlalchemy.create_engine with a function that
#    returns our pre-built test engine.
# ---------------------------------------------------------------------------
from sqlalchemy import create_engine as _real_create_engine, event, text, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy.dialects.mysql import LONGTEXT
from sqlalchemy.ext.compiler import compiles
import sqlalchemy as _sa

# Map MySQL LONGTEXT to plain TEXT for SQLite
@compiles(LONGTEXT, "sqlite")
def _compile_longtext_sqlite(type_, compiler, **kw):
    return "TEXT"

_test_engine = _real_create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=False,
)


@event.listens_for(_test_engine, "connect")
def _enable_fk(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


# Temporarily hijack create_engine so database.py's module-level call
# returns our test engine instead of trying to build a MySQL one.
_sa.create_engine = lambda *a, **kw: _test_engine

import database as _db  # noqa: E402  (must come after settings patch)

_sa.create_engine = _real_create_engine  # restore immediately

_db.engine = _test_engine
_db.Session = sessionmaker(bind=_test_engine)

# ---------------------------------------------------------------------------
# 5. Create all tables
# ---------------------------------------------------------------------------
_db.Base.metadata.create_all(_test_engine)

# ---------------------------------------------------------------------------
# 6. Establish correct circular-import order
#    helpers.server does `from helpers.auth import *` and helpers.auth does
#    `import helpers.server`. In production, server is imported first (via
#    endpoints). Here we must mirror that order so all names resolve.
# ---------------------------------------------------------------------------
import helpers.server  # noqa: F401


# ===========================================================================
# Fixtures
# ===========================================================================


@pytest.fixture(autouse=True)
def _clean_db():
    """Truncate all tables and re-seed built-in roles before each test."""
    with _db.Session() as session:
        session.execute(text("PRAGMA foreign_keys=OFF"))
        for table in reversed(_db.Base.metadata.sorted_tables):
            session.execute(table.delete())
        session.execute(text("PRAGMA foreign_keys=ON"))
        session.commit()

    with _db.Session() as session:
        session.add(_db.Role(name="everyone"))
        session.add(_db.Role(name="admin"))
        session.commit()
    yield


@pytest.fixture
def seed_test_data():
    """Seed database with test users, computer, hardware specs, and container."""
    from helpers.auth import hash_password

    with _db.Session() as session:
        # Admin user with "admin" role
        h = hash_password("test")
        admin_user = _db.User(
            email="admin@foo.com",
            password=base64.b64encode(h["hashedPassword"]).decode("utf-8"),
            passwordSalt=base64.b64encode(h["salt"]).decode("utf-8"),
        )
        admin_role = session.execute(
            select(_db.Role).where(_db.Role.name == "admin")
        ).scalar_one()
        admin_user.roles.append(admin_role)
        session.add(admin_user)

        # Normal user (no special role)
        h = hash_password("test")
        normal_user = _db.User(
            email="user@foo.com",
            password=base64.b64encode(h["hashedPassword"]).decode("utf-8"),
            passwordSalt=base64.b64encode(h["salt"]).decode("utf-8"),
        )
        session.add(normal_user)
        session.flush()

        # Computer with hardware specs
        computer = _db.Computer(name="server1", ip="127.0.0.1", public=True)
        session.add(computer)
        session.flush()

        computer.hardwareSpecs.append(
            _db.HardwareSpec(
                type="cpus", maximumAmount=8, minimumAmount=1,
                maximumAmountForUser=8, defaultAmountForUser=2, format="CPUs",
            )
        )
        computer.hardwareSpecs.append(
            _db.HardwareSpec(
                type="ram", maximumAmount=16, minimumAmount=1,
                maximumAmountForUser=16, defaultAmountForUser=4, format="GB",
            )
        )
        computer.hardwareSpecs.append(
            _db.HardwareSpec(
                type="gpus", maximumAmount=0, minimumAmount=0,
                maximumAmountForUser=1, defaultAmountForUser=0, format="GPUs",
            )
        )

        # Container with SSH port
        container = _db.Container(
            public=True, imageName="ubuntu-base",
            name="Ubuntu Base", description="Test container",
        )
        container.containerPorts.append(
            _db.ContainerPort(serviceName="SSH", port=22)
        )
        session.add(container)
        session.commit()


@pytest.fixture
def test_client(seed_test_data):
    """Create a FastAPI TestClient backed by the seeded test database."""
    from fastapi.testclient import TestClient
    from main import app

    return TestClient(app)


@pytest.fixture
def admin_token(test_client):
    """Login as admin and return the Bearer token."""
    resp = test_client.post(
        "/api/user/login",
        data={"username": "admin@foo.com", "password": "test"},
    )
    assert resp.status_code == 200, f"Admin login failed: {resp.text}"
    return resp.json()["access_token"]


@pytest.fixture
def user_token(test_client):
    """Login as normal user and return the Bearer token."""
    resp = test_client.post(
        "/api/user/login",
        data={"username": "user@foo.com", "password": "test"},
    )
    assert resp.status_code == 200, f"User login failed: {resp.text}"
    return resp.json()["access_token"]
