"""create budgets table

Revision ID: 992cec269a72
Revises: 2ffc2b03c4bf
Create Date: 2025-12-13 18:52:42.017293

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '992cec269a72'
down_revision: Union[str, Sequence[str], None] = '2ffc2b03c4bf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.create_table(
        "budgets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("amount", sa.Numeric(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),

        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),

        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_budgets_user_id",
        ),

        sa.UniqueConstraint(
            "user_id",
            "name",
            name="uq_user_budget_name",
        ),
    )


def downgrade():
    op.drop_table("budgets")
