"""Add sshPublicKey column to User table.

Add an optional text column ``sshPublicKey`` to the User table so that users
can store their SSH public key in the platform. When a container is launched,
the key is automatically deployed to the container's authorized_keys file,
enabling passwordless SSH access without manual key setup each time.

Revision ID: 79bfcb9421cd
Revises: c0de8fe27417
Create Date: 2026-03-30 15:07:19.394333

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '79bfcb9421cd'
down_revision: Union[str, Sequence[str], None] = 'c0de8fe27417'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add the nullable ``sshPublicKey`` text column to the User table."""
    op.add_column('User', sa.Column('sshPublicKey', sa.Text(), nullable=True))


def downgrade() -> None:
    """Drop the ``sshPublicKey`` column from the User table."""
    op.drop_column('User', 'sshPublicKey')
