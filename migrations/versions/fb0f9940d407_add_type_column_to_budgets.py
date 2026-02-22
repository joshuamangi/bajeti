"""add type column to budgets

Revision ID: fb0f9940d407
Revises: 57a2c175a301
Create Date: 2026-01-20 22:56:29.464253

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fb0f9940d407'
down_revision: Union[str, Sequence[str], None] = '57a2c175a301'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # SQLite requires batch mode for constraints
    with op.batch_alter_table("budgets", recreate="always") as batch_op:
        batch_op.add_column(
            sa.Column(
                "type",
                sa.String(length=20),
                nullable=False,
                server_default="expense",
            )
        )

        batch_op.create_check_constraint(
            "ck_budgets_type",
            "type IN ('expense', 'savings')"
        )

    # Ensure existing rows are explicitly set
    op.execute("UPDATE budgets SET type = 'expense'")


def downgrade():
    with op.batch_alter_table("budgets", recreate="always") as batch_op:
        batch_op.drop_constraint("ck_budgets_type", type_="check")
        batch_op.drop_column("type")
