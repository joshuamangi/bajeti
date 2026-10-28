"""add payment capture inbox and payee rules

Revision ID: c3d5f7a9b1e2
Revises: b2c4e6f8a1d3
Create Date: 2026-10-29 15:00:00.000000

Captured M-Pesa SMS and payment emails (docs/design/payments.md). New tables only.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3d5f7a9b1e2'
down_revision: Union[str, Sequence[str], None] = 'b2c4e6f8a1d3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.create_table(
        "pending_payments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("source", sa.String(length=10), nullable=False),
        sa.Column("kind", sa.String(length=10), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=True),
        sa.Column("amount", sa.Numeric(), nullable=True),
        sa.Column("fee", sa.Numeric(), nullable=True),
        sa.Column("payee", sa.String(length=80), nullable=True),
        sa.Column("reference", sa.String(length=20), nullable=True),
        sa.Column("paid_on", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=10), nullable=False),
        sa.Column("expense_id", sa.Integer(), sa.ForeignKey("expenses.id", ondelete="SET NULL"), nullable=True),
        sa.Column("received_at", sa.DateTime()),
        sa.Column("created_at", sa.DateTime()),
        sa.UniqueConstraint("user_id", "reference", name="uq_pending_payment_reference"),
        sa.CheckConstraint("status IN ('pending', 'approved', 'dismissed')", name="ck_pending_payment_status"),
        sa.CheckConstraint("source IN ('paste', 'sms', 'email')", name="ck_pending_payment_source"),
    )
    op.create_index("ix_pending_payments_user_id", "pending_payments", ["user_id"])
    op.create_table(
        "payee_rules",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("payee", sa.String(length=80), nullable=False),
        sa.Column("category_id", sa.Integer(), sa.ForeignKey("categories.id", ondelete="CASCADE"), nullable=False),
        sa.UniqueConstraint("user_id", "payee", name="uq_payee_rule"),
    )


def downgrade():
    op.drop_table("payee_rules")
    op.drop_index("ix_pending_payments_user_id", table_name="pending_payments")
    op.drop_table("pending_payments")
