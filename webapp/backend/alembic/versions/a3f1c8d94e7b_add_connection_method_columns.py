"""Add connection method columns to Container and ContainerPort

Add primaryConnectionPortId to Container for configurable primary
connection method, and portType to ContainerPort to drive type-aware
rendering (SSH, HTTP, HTTPS, VNC, Other/TCP). Backfill existing SSH
ports with portType='SSH'.

Revision ID: a3f1c8d94e7b
Revises: 2e66b76996d2
Create Date: 2026-04-08 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3f1c8d94e7b'
down_revision: Union[str, Sequence[str], None] = '2e66b76996d2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('Container', sa.Column('primaryConnectionPortId', sa.Integer(), nullable=True))
    op.add_column('ContainerPort', sa.Column('portType', sa.Text(), nullable=True))
    # Backfill existing SSH ports — catch both serviceName='SSH' and port=22 edge cases
    op.execute("UPDATE ContainerPort SET portType = 'SSH' WHERE serviceName = 'SSH' OR port = 22")


def downgrade() -> None:
    op.drop_column('ContainerPort', 'portType')
    op.drop_column('Container', 'primaryConnectionPortId')
