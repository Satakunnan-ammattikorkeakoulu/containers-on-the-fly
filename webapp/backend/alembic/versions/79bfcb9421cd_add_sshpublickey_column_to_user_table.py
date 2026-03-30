"""Add sshPublicKey column to User table

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
    """Upgrade schema."""
    op.add_column('User', sa.Column('sshPublicKey', sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('User', 'sshPublicKey')
