"""Add low-priority limit columns for HardwareSpec, RoleReservationLimit, RoleHardwareLimit

Revision ID: b2d4f6a8c1e3
Revises: a3f1c8d94e7b
Create Date: 2026-04-10 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2d4f6a8c1e3'
down_revision: Union[str, Sequence[str], None] = 'a3f1c8d94e7b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add low-priority per-user/per-role limit columns.

    HardwareSpec.maximumAmountForUserLowPriority mirrors maximumAmountForUser and is
    backfilled to the same value so existing computers keep their current behavior.
    RoleReservationLimit.lowPriorityMaxDuration and RoleHardwareLimit.maximumAmountForRoleLowPriority
    are nullable; NULL means "inherit the normal counterpart".
    RoleReservationLimit.allowLowPriority defaults to True so the feature stays on
    for every existing role after the upgrade; admins can disable it per role
    afterwards (e.g. on the built-in "everyone" role) to restrict access.
    """
    op.add_column(
        'HardwareSpec',
        sa.Column('maximumAmountForUserLowPriority', sa.Float(), nullable=False, server_default='0')
    )
    op.execute("UPDATE HardwareSpec SET maximumAmountForUserLowPriority = maximumAmountForUser")
    op.alter_column('HardwareSpec', 'maximumAmountForUserLowPriority', server_default=None)

    op.add_column(
        'RoleReservationLimit',
        sa.Column('lowPriorityMaxDuration', sa.Integer(), nullable=True)
    )
    op.add_column(
        'RoleReservationLimit',
        sa.Column('allowLowPriority', sa.Boolean(), nullable=False, server_default=sa.text('1'))
    )
    op.alter_column('RoleReservationLimit', 'allowLowPriority', server_default=None)

    op.add_column(
        'RoleHardwareLimit',
        sa.Column('maximumAmountForRoleLowPriority', sa.Integer(), nullable=True)
    )


def downgrade() -> None:
    """Remove the low-priority limit columns."""
    op.drop_column('RoleHardwareLimit', 'maximumAmountForRoleLowPriority')
    op.drop_column('RoleReservationLimit', 'allowLowPriority')
    op.drop_column('RoleReservationLimit', 'lowPriorityMaxDuration')
    op.drop_column('HardwareSpec', 'maximumAmountForUserLowPriority')
