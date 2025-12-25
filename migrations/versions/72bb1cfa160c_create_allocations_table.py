"""create allocations table

Revision ID: 72bb1cfa160c
Revises: 992cec269a72
Create Date: 2025-12-13 19:08:02.570962

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '72bb1cfa160c'
down_revision: Union[str, Sequence[str], None] = '992cec269a72'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.create_table(
        "allocations",
        sa.Column("id", sa.Integer(), primary_key=True),

        sa.Column("budget_id", sa.Integer(), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.Column("allocated_amount", sa.Numeric(), nullable=False),

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
            ["budget_id"],
            ["budgets.id"],
            name="fk_allocations_budget_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["categories.id"],
            name="fk_allocations_category_id",
        ),
    )


def downgrade():
    op.drop_table("allocations")
