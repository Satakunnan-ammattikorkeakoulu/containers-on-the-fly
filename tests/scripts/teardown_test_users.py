"""
Remove temporary test users created by setup_test_users.py.

Reads user IDs from tests/.test_credentials.json and deletes them from the database.

Usage:
    cd webapp/backend && python ../../tests/scripts/teardown_test_users.py
"""

import sys
import os
import json

# Add backend to path
backend_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..', 'webapp', 'backend'))
sys.path.insert(0, backend_dir)
os.chdir(backend_dir)

from database import (
    User, UserRole, Reservation, ReservedHardwareSpec, ReservedContainer,
    ReservedContainerPort, Computer, Container, ContainerPort, HardwareSpec,
    Role, RoleMount, RoleHardwareLimit, ServerStatus, Session
)
from sqlalchemy import select, delete, text

CREDENTIALS_FILE = os.path.join(os.path.dirname(__file__), '..', '.test_credentials.json')
BRUNO_ENV_FILE = os.path.join(os.path.dirname(__file__), '..', 'api', 'environments', 'test.bru')

def teardown_test_users():
    if not os.path.exists(CREDENTIALS_FILE):
        print("No credentials file found — nothing to clean up.")
        return

    with open(CREDENTIALS_FILE, "r") as f:
        credentials = json.load(f)

    user_ids = []
    if "admin_user_id" in credentials:
        user_ids.append(credentials["admin_user_id"])
    if "user_user_id" in credentials:
        user_ids.append(credentials["user_user_id"])

    if not user_ids:
        print("No user IDs in credentials file — nothing to clean up.")
        os.remove(CREDENTIALS_FILE)
        return

    with Session() as session:
        # Find reservations owned by test users
        reservation_ids = [
            r.reservationId for r in
            session.execute(
                select(Reservation).where(Reservation.userId.in_(user_ids))
            ).scalars().all()
        ]

        if reservation_ids:
            # Delete reserved hardware specs
            session.execute(delete(ReservedHardwareSpec).where(
                ReservedHardwareSpec.reservationId.in_(reservation_ids)
            ))

            # Get reserved container IDs
            rc_ids = [
                r.reservedContainerId for r in
                session.execute(
                    select(Reservation.reservedContainerId).where(
                        Reservation.reservationId.in_(reservation_ids)
                    )
                ).all()
            ]

            # Delete reservations
            session.execute(delete(Reservation).where(
                Reservation.reservationId.in_(reservation_ids)
            ))

            if rc_ids:
                # Delete reserved container ports
                session.execute(delete(ReservedContainerPort).where(
                    ReservedContainerPort.reservedContainerId.in_(rc_ids)
                ))
                # Delete reserved containers
                session.execute(delete(ReservedContainer).where(
                    ReservedContainer.reservedContainerId.in_(rc_ids)
                ))

        # Delete role assignments (FK constraint)
        session.execute(delete(UserRole).where(UserRole.userId.in_(user_ids)))
        # Delete users
        session.execute(delete(User).where(User.userId.in_(user_ids)))

        # Clean up test-created resources (computers, containers, roles)
        for name in ['bruno-test-server']:
            comp = session.execute(select(Computer).where(Computer.name == name)).scalar_one_or_none()
            if comp:
                session.execute(delete(ServerStatus).where(ServerStatus.computerId == comp.computerId))
                session.execute(delete(HardwareSpec).where(HardwareSpec.computerId == comp.computerId))
                session.execute(delete(RoleMount).where(RoleMount.computerId == comp.computerId))
                session.execute(delete(Computer).where(Computer.computerId == comp.computerId))

        for img in ['bruno-test-container']:
            cont = session.execute(select(Container).where(Container.imageName == img)).scalar_one_or_none()
            if cont:
                session.execute(delete(ContainerPort).where(ContainerPort.containerId == cont.containerId))
                session.execute(delete(Container).where(Container.containerId == cont.containerId))

        for rname in ['bruno-test-role']:
            role = session.execute(select(Role).where(Role.name == rname)).scalar_one_or_none()
            if role:
                session.execute(delete(RoleHardwareLimit).where(RoleHardwareLimit.roleId == role.roleId))
                session.execute(delete(RoleMount).where(RoleMount.roleId == role.roleId))
                session.execute(delete(Role).where(Role.roleId == role.roleId))

        session.commit()

    print(f"Deleted test users: {credentials.get('admin_email')}, {credentials.get('user_email')}")

    os.remove(CREDENTIALS_FILE)
    print(f"Removed {CREDENTIALS_FILE}")

    # Clean up generated Bruno test environment
    if os.path.exists(BRUNO_ENV_FILE):
        os.remove(BRUNO_ENV_FILE)
        print(f"Removed {BRUNO_ENV_FILE}")

if __name__ == "__main__":
    teardown_test_users()
