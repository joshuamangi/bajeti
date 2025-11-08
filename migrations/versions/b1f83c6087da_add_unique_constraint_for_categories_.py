"""Add unique constraint for categories per user

Revision ID: b1f83c6087da
Revises: 922afb67a64e
Create Date: 2025-11-08 06:38:00.215421

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b1f83c6087da'
down_revision: Union[str, Sequence[str], None] = '922afb67a64e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Use batch_alter_table for SQLite compatibility
    with op.batch_alter_table('categories', schema=None) as batch_op:
        batch_op.create_unique_constraint(
            'uq_user_category_name', ['user_id', 'name'])


def downgrade() -> None:
    """Downgrade schema."""
    # Use batch_alter_table for SQLite compatibility
    with op.batch_alter_table('categories', schema=None) as batch_op:
        batch_op.drop_constraint('uq_user_category_name', type_='unique')
