"""
Create temporary test users (admin + normal) for E2E and API tests.

Connects directly to the production database using the backend's settings.
Writes credentials to tests/.test_credentials.json for test frameworks to read.

Usage:
    cd webapp/backend && python ../../tests/scripts/setup_test_users.py
"""

import sys
import os
import json
import secrets
import string
import base64

# Add backend to path
backend_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..', 'webapp', 'backend'))
sys.path.insert(0, backend_dir)
os.chdir(backend_dir)

from database import User, Role, UserRole, Session
from helpers.auth import hash_password
from sqlalchemy import select

# Generate random credentials
def random_password(length=40):
    chars = string.ascii_letters + string.digits
    return ''.join(secrets.choice(chars) for _ in range(length))

def random_suffix():
    return secrets.token_hex(6)

CREDENTIALS_FILE = os.path.join(os.path.dirname(__file__), '..', '.test_credentials.json')

def create_test_users():
    suffix = random_suffix()
    admin_email = f"e2e-admin-{suffix}@test.local"
    user_email = f"e2e-user-{suffix}@test.local"
    admin_password = random_password()
    user_password = random_password()

    with Session() as session:
        # Create admin user
        h = hash_password(admin_password)
        admin_user = User(
            email=admin_email,
            password=base64.b64encode(h["hashedPassword"]).decode("utf-8"),
            passwordSalt=base64.b64encode(h["salt"]).decode("utf-8"),
        )
        admin_role = session.execute(
            select(Role).where(Role.name == "admin")
        ).scalar_one_or_none()
        if admin_role:
            admin_user.roles.append(admin_role)
        session.add(admin_user)

        # Create normal user
        h = hash_password(user_password)
        normal_user = User(
            email=user_email,
            password=base64.b64encode(h["hashedPassword"]).decode("utf-8"),
            passwordSalt=base64.b64encode(h["salt"]).decode("utf-8"),
        )
        session.add(normal_user)
        session.commit()

        admin_user_id = admin_user.userId
        user_user_id = normal_user.userId

    # Write credentials to file
    credentials = {
        "admin_email": admin_email,
        "admin_password": admin_password,
        "admin_user_id": admin_user_id,
        "user_email": user_email,
        "user_password": user_password,
        "user_user_id": user_user_id,
    }
    with open(CREDENTIALS_FILE, "w") as f:
        json.dump(credentials, f, indent=2)

    print(f"Created test admin:  {admin_email}")
    print(f"Created test user:   {user_email}")
    print(f"Credentials written to {os.path.abspath(CREDENTIALS_FILE)}")

if __name__ == "__main__":
    create_test_users()
