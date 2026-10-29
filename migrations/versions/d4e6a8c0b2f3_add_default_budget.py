"""add default budget flag

Revision ID: d4e6a8c0b2f3
Revises: c3d5f7a9b1e2
Create Date: 2026-10-29 15:00:00.000000

budgets.is_default: the budget that opens after login. Existing budgets get false, so nothing
changes until the owner picks one.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4e6a8c0b2f3'
down_revision: Union[str, Sequence[str], None] = 'c3d5f7a9b1e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.add_column("budgets", sa.Column("is_default", sa.Boolean(), nullable=False, server_default="0"))


def downgrade():
    # SQLite needs batch mode to drop a column
    with op.batch_alter_table("budgets", recreate="always") as batch_op:
        batch_op.drop_column("is_default")
