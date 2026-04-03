"""Add removed column to User table

Revision ID: 2e66b76996d2
Revises: 46f24bea56fc
Create Date: 2026-04-03 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2e66b76996d2'
down_revision: Union[str, Sequence[str], None] = '46f24bea56fc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('User', sa.Column('removed', sa.Boolean(), nullable=True))


def downgrade() -> None:
    op.drop_column('User', 'removed')
