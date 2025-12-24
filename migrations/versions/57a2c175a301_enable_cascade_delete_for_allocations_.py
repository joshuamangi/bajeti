"""enable cascade delete for allocations.category_id

Revision ID: 57a2c175a301
Revises: 39c364cc7756
Create Date: 2025-12-24 22:14:56.963199

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '57a2c175a301'
down_revision: Union[str, Sequence[str], None] = '39c364cc7756'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    with op.batch_alter_table("allocations", recreate="always") as batch_op:

        batch_op.create_foreign_key(
            "fk_allocations_category",
            "categories",
            ["category_id"],
            ["id"],
            ondelete="CASCADE"
        )

        batch_op.create_foreign_key(
            "fk_allocations_budget",
            "budgets",
            ["budget_id"],
            ["id"],
            ondelete="CASCADE"
        )

        batch_op.create_unique_constraint(
            "uq_allocations_budget_category",
            ["budget_id", "category_id"]
        )


def downgrade():
    with op.batch_alter_table("allocations", recreate="always") as batch_op:

        batch_op.create_foreign_key(
            "fk_allocations_category",
            "categories",
            ["category_id"],
            ["id"]
        )

        batch_op.create_foreign_key(
            "fk_allocations_budget",
            "budgets",
            ["budget_id"],
            ["id"]
        )

        batch_op.create_unique_constraint(
            "uq_allocations_budget_category",
            ["budget_id", "category_id"]
        )
