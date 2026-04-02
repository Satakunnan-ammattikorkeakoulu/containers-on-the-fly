"""Add name column to User table.

Add an optional text column ``name`` to the User table so that users
can have a display name. The name can be set by admins, by the user
themselves, or auto-populated from LDAP on login.

Revision ID: 80f5f80ca7b9
Revises: 066815016cd8
Create Date: 2026-04-02 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '80f5f80ca7b9'
down_revision: Union[str, Sequence[str], None] = '066815016cd8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add the nullable ``name`` text column to the User table."""
    op.add_column('User', sa.Column('name', sa.Text(), nullable=True))


def downgrade() -> None:
    """Drop the ``name`` column from the User table."""
    op.drop_column('User', 'name')
