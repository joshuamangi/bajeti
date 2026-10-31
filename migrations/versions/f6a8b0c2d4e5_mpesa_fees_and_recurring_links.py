"""M-Pesa fees and recurring links

Revision ID: f6a8b0c2d4e5
Revises: e5f7a9c1d3b4
Create Date: 2026-10-31 18:00:00.000000

Fees become their own expense in an "M-Pesa fees" category (docs/design/payments.md), and a
captured payment can be filed as a recurring payment. New nullable columns only:
- pending_payments: fee_expense_id, previous_fee, recurring_run_id
- recurring_expenses: usual_fee
- recurring_runs: fee_expense_id
- payee_rules: recurring_id
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f6a8b0c2d4e5'
down_revision: Union[str, Sequence[str], None] = 'e5f7a9c1d3b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# (table, column, referenced table or None). Adding a nullable column keeps existing rows as they are.
COLUMNS = [
    ("pending_payments", "fee_expense_id", "expenses"),
    ("pending_payments", "previous_fee", None),
    ("pending_payments", "recurring_run_id", "recurring_runs"),
    ("recurring_expenses", "usual_fee", None),
    ("recurring_runs", "fee_expense_id", "expenses"),
    ("payee_rules", "recurring_id", "recurring_expenses"),
]


def upgrade():
    # SQLite cannot add a foreign key with ALTER TABLE, so each table is rebuilt in batch mode.
    for table in ("pending_payments", "recurring_expenses", "recurring_runs", "payee_rules"):
        with op.batch_alter_table(table) as batch_op:
            for t, column, target in COLUMNS:
                if t != table:
                    continue
                if target:
                    batch_op.add_column(sa.Column(column, sa.Integer(), nullable=True))
                    batch_op.create_foreign_key(f"fk_{table}_{column}", target, [column], ["id"], ondelete="SET NULL")
                else:
                    batch_op.add_column(sa.Column(column, sa.Numeric(), nullable=True))


def downgrade():
    for table in ("payee_rules", "recurring_runs", "recurring_expenses", "pending_payments"):
        with op.batch_alter_table(table, recreate="always") as batch_op:
            for t, column, target in reversed(COLUMNS):
                if t != table:
                    continue
                if target:
                    batch_op.drop_constraint(f"fk_{table}_{column}", type_="foreignkey")
                batch_op.drop_column(column)
