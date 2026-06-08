"""Add lowPriorityLevel to Reservation.

Adds an integer column lowPriorityLevel (1-3) to the Reservation table.
This sub-orders low-priority reservations: 1 = Standard, 2 = Background,
3 = Idle. Higher level numbers yield to lower level numbers within the
low-priority class. The column is added as nullable first, backfilled
with the default value 1 (so existing low-priority reservations keep
their current behavior), then altered to non-nullable.

The value is only behaviorally meaningful when isLowPriority is True.
For normal reservations the column is inert (defaults to 1).

Revision ID: d4e7f1a92c3b
Revises: 41b9cb8365c4
Create Date: 2026-06-01 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4e7f1a92c3b'
down_revision: Union[str, Sequence[str], None] = '41b9cb8365c4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add lowPriorityLevel column, backfill with 1, then set non-nullable."""
    op.add_column('Reservation', sa.Column('lowPriorityLevel', sa.Integer(), nullable=True))
    op.execute("UPDATE Reservation SET lowPriorityLevel = 1 WHERE lowPriorityLevel IS NULL")
    op.alter_column('Reservation', 'lowPriorityLevel',
                    existing_type=sa.Integer(),
                    nullable=False)


def downgrade() -> None:
    """Remove lowPriorityLevel column from Reservation table."""
    op.drop_column('Reservation', 'lowPriorityLevel')
