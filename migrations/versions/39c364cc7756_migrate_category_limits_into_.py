"""Migrate category limits into allocations and recalc budgets

Revision ID: 39c364cc7756
Revises: ec90ca94d624
Create Date: 2025-12-24 20:56:10.370512

"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy.sql import text
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '39c364cc7756'
down_revision: Union[str, Sequence[str], None] = 'ec90ca94d624'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    conn = op.get_bind()

    # 1. Create allocations from category limits
    conn.execute(text("""
        INSERT INTO allocations (budget_id, category_id, allocated_amount, created_at, updated_at)
        SELECT 
            b.id AS budget_id,
            c.id AS category_id,
            COALESCE(c.limit_amount, 0) AS allocated_amount,
            CURRENT_TIMESTAMP,
            CURRENT_TIMESTAMP
        FROM categories c
        JOIN budgets b ON b.user_id = c.user_id
        WHERE c.limit_amount IS NOT NULL
          AND NOT EXISTS (
            SELECT 1 FROM allocations a
            WHERE a.category_id = c.id
              AND a.budget_id = b.id
          )
    """))

    # 2. Recalculate each budget total from allocations
    conn.execute(text("""
        UPDATE budgets
        SET amount = (
            SELECT COALESCE(SUM(a.allocated_amount), 0)
            FROM allocations a
            WHERE a.budget_id = budgets.id
        )
    """))


def downgrade():
    conn = op.get_bind()

    # Restore category.limit_amount from allocations
    conn.execute(text("""
        UPDATE categories
        SET limit_amount = (
            SELECT a.allocated_amount
            FROM allocations a
            JOIN budgets b ON b.id = a.budget_id
            WHERE a.category_id = categories.id
              AND b.user_id = categories.user_id
            LIMIT 1
        )
    """))

    # Reset budget.amount from restored category limits
    conn.execute(text("""
        UPDATE budgets
        SET amount = (
            SELECT COALESCE(SUM(c.limit_amount), 0)
            FROM categories c
            WHERE c.user_id = budgets.user_id
        )
    """))

    # Remove inserted allocations
    conn.execute(text("DELETE FROM allocations"))
