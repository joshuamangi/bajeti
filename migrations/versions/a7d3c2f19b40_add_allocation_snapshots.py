"""add allocation snapshots and analytics indexes

Revision ID: a7d3c2f19b40
Revises: 186f1cc1a7ca
Create Date: 2026-10-29 09:00:00.000000

Analytics compares each month with the allocation that applied in that month. Allocations
are one amount for every month, so the history starts here: the current month is recorded
from today's allocations and earlier months have no snapshot (owner decision, no backfill).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a7d3c2f19b40'
down_revision: Union[str, Sequence[str], None] = '186f1cc1a7ca'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.create_table(
        "allocation_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("budget_id", sa.Integer(), sa.ForeignKey("budgets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("category_id", sa.Integer(), sa.ForeignKey("categories.id", ondelete="CASCADE"), nullable=False),
        sa.Column("month", sa.String(length=7), nullable=False),
        sa.Column("amount", sa.Numeric(), nullable=False),
        sa.UniqueConstraint("budget_id", "category_id", "month", name="uq_allocation_snapshot_month"),
    )
    op.create_index("ix_expenses_user_month_category", "expenses", ["user_id", "month", "category_id"])
    op.create_index("ix_transfers_user_month", "transfers", ["user_id", "month"])

    # The current month, from today's allocations.
    op.get_bind().execute(sa.text("""
        INSERT INTO allocation_snapshots (budget_id, category_id, month, amount)
        SELECT budget_id, category_id, strftime('%Y-%m', 'now'), allocated_amount
        FROM allocations
    """))


def downgrade():
    op.drop_index("ix_transfers_user_month", table_name="transfers")
    op.drop_index("ix_expenses_user_month_category", table_name="expenses")
    op.drop_table("allocation_snapshots")
