"""Seed test data for development and testing.

Creates test accounts and a server entry with hardware specs if they
do not already exist. Safe to run multiple times (idempotent).

Created entities:
  - Admin user:  admin@foo.com (password: test)
  - Normal user: user@foo.com (password: test)
  - Computer 'server1' with CPU, RAM, and GPU hardware specs

Usage:
    cd webapp/backend && python ../../scripts/seed_test_data.py
"""

import sys
import os
import base64

# Add backend to path
backend_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'webapp', 'backend'))
sys.path.insert(0, backend_dir)
os.chdir(backend_dir)

from database import Session, User, Role, Computer, HardwareSpec
from helpers.auth import hash_password
from helpers.settings_handler import settings_handler
from sqlalchemy import select


def seed():
    """Seed test data into the database.

    Creates an admin user, a normal user, a computer, and hardware specs
    if they do not already exist. Prints what was created.
    """
    created = []

    with Session() as session:
        # Admin user
        admin_user = session.execute(select(User).where(User.email == "admin@foo.com")).scalar_one_or_none()
        if admin_user is None:
            print("Creating admin user: admin@foo.com")
            h = hash_password("test")
            admin_user = User(
                email="admin@foo.com",
                password=base64.b64encode(h["hashedPassword"]).decode('utf-8'),
                passwordSalt=base64.b64encode(h["salt"]).decode('utf-8')
            )
            admin_role = session.execute(select(Role).where(Role.name == "admin")).scalar_one_or_none()
            if admin_role:
                admin_user.roles.append(admin_role)
            session.add(admin_user)
            session.commit()
            created.append("admin user (admin@foo.com)")

        # Normal user
        normal_user = session.execute(select(User).where(User.email == "user@foo.com")).scalar_one_or_none()
        if normal_user is None:
            print("Creating normal user: user@foo.com")
            h = hash_password("test")
            normal_user = User(
                email="user@foo.com",
                password=base64.b64encode(h["hashedPassword"]).decode('utf-8'),
                passwordSalt=base64.b64encode(h["salt"]).decode('utf-8')
            )
            session.add(normal_user)
            session.commit()
            created.append("normal user (user@foo.com)")

        # Computer
        computer = session.execute(select(Computer).where(Computer.name == "server1")).scalar_one_or_none()
        if computer is None:
            print("Creating computer: server1")
            computer = Computer(
                name="server1",
                ip=settings_handler.get_setting("app.serverIp"),
                public=True
            )
            session.add(computer)
            session.commit()
            created.append("computer (server1)")

        # Hardware specs for computer
        computer = session.execute(select(Computer).where(Computer.name == "server1")).scalar_one_or_none()
        if len(computer.hardwareSpecs) == 0:
            print("Creating hardware specs for server1")
            computer.hardwareSpecs.append(HardwareSpec(
                type="gpus",
                maximumAmount=0,
                maximumAmountForUser=1,
                maximumAmountForUserLowPriority=1,
                defaultAmountForUser=0,
                minimumAmount=0,
                format="GPUs",
            ))
            computer.hardwareSpecs.append(HardwareSpec(
                type="ram",
                maximumAmount=10,
                maximumAmountForUser=10,
                maximumAmountForUserLowPriority=10,
                defaultAmountForUser=1,
                minimumAmount=1,
                format="GB",
            ))
            computer.hardwareSpecs.append(HardwareSpec(
                type="cpus",
                maximumAmount=5,
                maximumAmountForUser=5,
                maximumAmountForUserLowPriority=5,
                defaultAmountForUser=1,
                minimumAmount=1,
                format="CPUs",
            ))
            session.commit()
            created.append("hardware specs (GPUs, RAM, CPUs)")

    # Summary
    if created:
        print(f"\nSeeded {len(created)} item(s): {', '.join(created)}")
        print("\nTest credentials:")
        print("  Admin:  admin@foo.com / test")
        print("  User:   user@foo.com / test")
    else:
        print("All test data already exists. Nothing to create.")


if __name__ == "__main__":
    seed()
