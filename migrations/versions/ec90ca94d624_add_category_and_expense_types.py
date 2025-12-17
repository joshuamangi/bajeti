"""add category and expense types

Revision ID: ec90ca94d624
Revises: e8b935ff95f0
Create Date: 2025-12-17 20:32:38.314433

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ec90ca94d624'
down_revision: Union[str, Sequence[str], None] = 'e8b935ff95f0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # ---------- CATEGORIES ----------
    with op.batch_alter_table("categories", recreate="always") as batch:
        batch.add_column(
            sa.Column(
                "type",
                sa.String(length=20),
                nullable=False,
                server_default="expense"
            )
        )

        batch.create_check_constraint(
            "ck_categories_type",
            "type IN ('expense','savings')"
        )

        # replace unique constraint
        batch.drop_constraint("uq_user_category_name", type_="unique")
        batch.create_unique_constraint(
            "uq_user_category_name_type",
            ["user_id", "name", "type"]
        )

    # Backfill existing categories explicitly (SQLite-safe)
    op.execute("UPDATE categories SET type = 'expense' WHERE type IS NULL")

    # ---------- EXPENSES ----------
    with op.batch_alter_table("expenses", recreate="always") as batch:
        batch.add_column(
            sa.Column(
                "type",
                sa.String(length=20),
                nullable=False,
                server_default="spend"
            )
        )

        batch.create_check_constraint(
            "ck_expenses_type",
            "type IN ('spend','withdrawal')"
        )

    # Backfill existing expenses explicitly
    op.execute("UPDATE expenses SET type = 'spend' WHERE type IS NULL")


def downgrade():
    # ---------- EXPENSES ----------
    with op.batch_alter_table("expenses", recreate="always") as batch:
        batch.drop_constraint("ck_expenses_type", type_="check")
        batch.drop_column("type")

    # ---------- CATEGORIES ----------
    with op.batch_alter_table("categories", recreate="always") as batch:
        batch.drop_constraint("uq_user_category_name_type", type_="unique")
        batch.drop_constraint("ck_categories_type", type_="check")
        batch.drop_column("type")

        batch.create_unique_constraint(
            "uq_user_category_name",
            ["user_id", "name"]
        )
