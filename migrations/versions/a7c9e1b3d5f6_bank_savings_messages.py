"""Bank savings messages

Revision ID: a7c9e1b3d5f6
Revises: f6a8b0c2d4e5
Create Date: 2026-11-01 10:00:00.000000

Bank transfers to M-Pesa and card purchases become savings withdrawals, and bank deposits add
to a savings budget (docs/design/payments.md). New nullable columns only:
- pending_payments: account ("Card ending 1234"), budget_id (the deposit's budget, for Undo)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a7c9e1b3d5f6'
down_revision: Union[str, Sequence[str], None] = 'f6a8b0c2d4e5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # SQLite cannot add a foreign key with ALTER TABLE, so the table is rebuilt in batch mode.
    with op.batch_alter_table("pending_payments") as batch_op:
        batch_op.add_column(sa.Column("account", sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column("budget_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key("fk_pending_payments_budget_id", "budgets", ["budget_id"], ["id"],
                                    ondelete="SET NULL")


def downgrade():
    with op.batch_alter_table("pending_payments", recreate="always") as batch_op:
        batch_op.drop_constraint("fk_pending_payments_budget_id", type_="foreignkey")
        batch_op.drop_column("budget_id")
        batch_op.drop_column("account")
