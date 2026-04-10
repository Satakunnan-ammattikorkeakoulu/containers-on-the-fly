"""Add activityLastSeenAt to User table.

Adds a nullable DateTime column tracking the last time a user opened the
reservation activity feed. The frontend uses it to render an unread-count
badge and a "NEW" indicator on activity rows newer than this timestamp.

Existing users are backfilled to NOW() so they do not see every historic
audit log entry as unread on first login after the upgrade.

Revision ID: aed2d723523f
Revises: b2d4f6a8c1e3
Create Date: 2026-04-10 15:36:25.506718

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'aed2d723523f'
down_revision: Union[str, Sequence[str], None] = 'b2d4f6a8c1e3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add activityLastSeenAt column and backfill existing rows to NOW()."""
    op.add_column('User', sa.Column('activityLastSeenAt', sa.DateTime(), nullable=True))
    op.execute("UPDATE User SET activityLastSeenAt = UTC_TIMESTAMP() WHERE activityLastSeenAt IS NULL")


def downgrade() -> None:
    """Drop the activityLastSeenAt column."""
    op.drop_column('User', 'activityLastSeenAt')
