"""Add RoleHardwareLimit table for role-based hardware limits

Revision ID: fc39c265d6b8
Revises: f3664bf56eff
Create Date: 2025-07-24 17:33:23.786713

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fc39c265d6b8'
down_revision: Union[str, Sequence[str], None] = 'f3664bf56eff'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create RoleHardwareLimit table
    op.create_table(
        'RoleHardwareLimit',
        sa.Column('roleHardwareLimitId', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('roleId', sa.Integer(), nullable=False, index=True),
        sa.Column('hardwareSpecId', sa.Integer(), nullable=False, index=True),
        sa.Column('maximumAmountForRole', sa.Integer(), nullable=True),
        sa.Column('createdAt', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updatedAt', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.ForeignKeyConstraint(['roleId'], ['Role.roleId'], name='fk_RoleHardwareLimit_roleId', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['hardwareSpecId'], ['HardwareSpec.hardwareSpecId'], name='fk_RoleHardwareLimit_hardwareSpecId', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('roleHardwareLimitId'),
        sa.UniqueConstraint('roleId', 'hardwareSpecId', name='unique_role_hardware')
    )
    
    # Indexes will be created automatically by SQLAlchemy due to index=True in the model


def downgrade() -> None:
    """Downgrade schema."""
    # Drop table (this will also drop all indexes and foreign keys)
    op.drop_table('RoleHardwareLimit')
