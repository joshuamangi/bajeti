"""populeate targets with existing categories

Revision ID: 186f1cc1a7ca
Revises: 9b38fdc94e38
Create Date: 2026-03-16 22:35:25.421503

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '186f1cc1a7ca'
down_revision: Union[str, Sequence[str], None] = '9b38fdc94e38'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    conn = op.get_bind()

    # Insert targets for existing categories and budgets
    conn.execute(sa.text("""
        INSERT INTO targets (
            budget_id,
            category_id,
            short_term_amount,
            mid_term_amount,
            long_term_amount,
            created_at,
            updated_at
        )
        SELECT
            b.id AS budget_id,
            c.id AS category_id,
            NULL,
            NULL,
            NULL,
            CURRENT_TIMESTAMP,
            CURRENT_TIMESTAMP
        FROM budgets b
        JOIN categories c
            ON b.user_id = c.user_id
           AND b.type = c.type
        WHERE NOT EXISTS (
            SELECT 1
            FROM targets t
            WHERE t.budget_id = b.id
              AND t.category_id = c.id
        );
    """))


def downgrade():
    conn = op.get_bind()

    # remove rows that were auto-created
    conn.execute(sa.text("""
        DELETE FROM targets
        WHERE short_term_amount IS NULL
        AND mid_term_amount IS NULL
        AND long_term_amount IS NULL
    """))
