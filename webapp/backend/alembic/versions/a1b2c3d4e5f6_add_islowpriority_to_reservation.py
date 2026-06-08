"""Add isLowPriority to Reservation

Revision ID: a1b2c3d4e5f6
Revises: 0fdcf8e1397f
Create Date: 2026-04-01 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '0fdcf8e1397f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add isLowPriority boolean column to Reservation table."""
    op.add_column('Reservation', sa.Column('isLowPriority', sa.Boolean(), nullable=False, server_default=sa.text('0')))


def downgrade() -> None:
    """Remove isLowPriority column from Reservation table."""
    op.drop_column('Reservation', 'isLowPriority')
