"""add recurring expenses and their runs

Revision ID: b2c4e6f8a1d3
Revises: a7d3c2f19b40
Create Date: 2026-10-29 12:00:00.000000

Monthly recurring bills (docs/design/recurring.md). New tables only; no existing data changes.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2c4e6f8a1d3'
down_revision: Union[str, Sequence[str], None] = 'a7d3c2f19b40'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.create_table(
        "recurring_expenses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("category_id", sa.Integer(), sa.ForeignKey("categories.id"), nullable=False),
        sa.Column("name", sa.String(length=60), nullable=False),
        sa.Column("amount", sa.Numeric(), nullable=False),
        sa.Column("anchor_day", sa.Integer(), nullable=False),
        sa.Column("next_due", sa.Date(), nullable=False),
        sa.Column("mode", sa.String(length=10), nullable=False, server_default="ask_first"),
        sa.Column("paused", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime()),
        sa.Column("updated_at", sa.DateTime()),
        sa.CheckConstraint("mode IN ('ask_first', 'auto')", name="ck_recurring_mode"),
        sa.CheckConstraint("anchor_day BETWEEN 1 AND 31", name="ck_recurring_anchor_day"),
    )
    op.create_index("ix_recurring_expenses_user_id", "recurring_expenses", ["user_id"])
    op.create_table(
        "recurring_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("recurring_id", sa.Integer(), sa.ForeignKey("recurring_expenses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("action", sa.String(length=10), nullable=False),
        sa.Column("expense_id", sa.Integer(), sa.ForeignKey("expenses.id", ondelete="SET NULL"), nullable=True),
        sa.Column("amount", sa.Numeric(), nullable=True),
        sa.Column("created_at", sa.DateTime()),
        sa.UniqueConstraint("recurring_id", "due_date", name="uq_recurring_run_due_date"),
        sa.CheckConstraint("action IN ('approved', 'skipped', 'auto')", name="ck_recurring_run_action"),
    )


def downgrade():
    op.drop_table("recurring_runs")
    op.drop_index("ix_recurring_expenses_user_id", table_name="recurring_expenses")
    op.drop_table("recurring_expenses")
