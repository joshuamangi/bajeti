"""recalculate budget and allocation for march 2026 withdrawals

Revision ID: 877adbb8bce2
Revises: fb0f9940d407
Create Date: 2026-03-03 14:13:23.091183

"""
from decimal import Decimal
from typing import Sequence, Union
from sqlalchemy.sql import text
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '877adbb8bce2'
down_revision: Union[str, Sequence[str], None] = 'fb0f9940d407'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    connection = op.get_bind()

    # 1️⃣ Get all March 2026 withdrawals
    withdrawals = connection.execute(sa.text("""
        SELECT id, category_id, amount, user_id
        FROM expenses
        WHERE month = '2026-03'
        AND type = 'withdrawal'
    """)).fetchall()

    for w in withdrawals:
        category_id = w.category_id
        amount = float(w.amount)
        user_id = w.user_id

        # 2️⃣ Find allocation
        allocation = connection.execute(text("""
            SELECT a.id, a.budget_id, a.allocated_amount
            FROM allocations a
            JOIN budgets b ON a.budget_id = b.id
            WHERE a.category_id = :category_id
            AND b.user_id = :user_id
        """), {
            "category_id": category_id,
            "user_id": user_id
        }).fetchone()

        if allocation:
            allocation_id = allocation.id
            budget_id = allocation.budget_id

            # 3️⃣ Reduce allocation
            connection.execute(text("""
                UPDATE allocations
                SET allocated_amount = allocated_amount - :amount
                WHERE id = :allocation_id
            """), {
                "amount": amount,
                "allocation_id": allocation_id
            })

            # 4️⃣ Reduce budget
            connection.execute(text("""
                UPDATE budgets
                SET amount = amount - :amount
                WHERE id = :budget_id
            """), {
                "amount": amount,
                "budget_id": budget_id
            })


def downgrade():
    connection = op.get_bind()

    # Reverse the operation (add back amounts)

    withdrawals = connection.execute(text("""
        SELECT id, category_id, amount, user_id
        FROM expenses
        WHERE month = '2026-03'
        AND type = 'withdrawal'
    """)).fetchall()

    for w in withdrawals:
        category_id = w.category_id
        amount = float(w.amount)
        user_id = w.user_id

        allocation = connection.execute(text("""
            SELECT a.id, a.budget_id
            FROM allocations a
            JOIN budgets b ON a.budget_id = b.id
            WHERE a.category_id = :category_id
            AND b.user_id = :user_id
        """), {
            "category_id": category_id,
            "user_id": user_id
        }).fetchone()

        if allocation:
            allocation_id = allocation.id
            budget_id = allocation.budget_id

            connection.execute(text("""
                UPDATE allocations
                SET allocated_amount = allocated_amount + :amount
                WHERE id = :allocation_id
            """), {
                "amount": amount,
                "allocation_id": allocation_id
            })

            connection.execute(text("""
                UPDATE budgets
                SET amount = amount + :amount
                WHERE id = :budget_id
            """), {
                "amount": amount,
                "budget_id": budget_id
            })
