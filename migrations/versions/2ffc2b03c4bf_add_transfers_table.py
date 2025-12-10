"""Add transfers table

Revision ID: 2ffc2b03c4bf
Revises: b1f83c6087da
Create Date: 2025-12-09 15:11:28.336772

"""
from datetime import datetime
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2ffc2b03c4bf'
down_revision: Union[str, Sequence[str], None] = 'b1f83c6087da'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "transfers",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("from_category_id", sa.Integer,
                  sa.ForeignKey("categories.id"), nullable=True),
        sa.Column("to_category_id", sa.Integer, sa.ForeignKey(
            "categories.id"), nullable=True),
        sa.Column("amount", sa.Numeric, nullable=False),
        sa.Column("description", sa.String, nullable=True),
        sa.Column("month", sa.String, index=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime, default=datetime.utcnow),
        sa.Column("updated_at", sa.DateTime, default=datetime.utcnow),
    )


def downgrade() -> None:
    op.drop_table("transfers")
