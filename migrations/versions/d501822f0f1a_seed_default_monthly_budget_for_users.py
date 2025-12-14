"""seed default monthly budget for users

Revision ID: d501822f0f1a
Revises: 72bb1cfa160c
Create Date: 2025-12-14 19:12:43.918490

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd501822f0f1a'
down_revision: Union[str, Sequence[str], None] = '72bb1cfa160c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    conn = op.get_bind()

    # Insert default budget for users who don't have one
    conn.execute(sa.text("""
        INSERT INTO budgets (name, amount, user_id, created_at, updated_at)
        SELECT
            'Monthly',
            0,
            u.id,
            CURRENT_TIMESTAMP,
            CURRENT_TIMESTAMP
        FROM users u
        WHERE NOT EXISTS (
            SELECT 1
            FROM budgets b
            WHERE b.user_id = u.id
              AND b.name = 'Monthly'
        )
    """))


def downgrade():
    # Safe rollback: remove only auto-created budgets
    conn = op.get_bind()
    conn.execute(sa.text("""
        DELETE FROM budgets
        WHERE name = 'Monthly'
    """))
