"""add unique constraint to allocations

Revision ID: e8b935ff95f0
Revises: d501822f0f1a
Create Date: 2025-12-14 23:07:31.125979

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e8b935ff95f0'
down_revision: Union[str, Sequence[str], None] = 'd501822f0f1a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    with op.batch_alter_table("allocations") as batch_op:
        batch_op.create_unique_constraint(
            "uq_budget_category_allocation",
            ["budget_id", "category_id"]
        )


def downgrade():
    with op.batch_alter_table("allocations") as batch_op:
        batch_op.drop_constraint(
            "uq_budget_category_allocation",
            type_="unique"
        )
