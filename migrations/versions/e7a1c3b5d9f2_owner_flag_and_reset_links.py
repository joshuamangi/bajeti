"""owner flag and reset links

Revision ID: e7a1c3b5d9f2
Revises: d4e6a8c0b2f3
Create Date: 2026-10-31 10:00:00.000000

users.is_owner: the household owner, who can reset other members' access. Everyone starts as
false; the owner is set once with python -m cli.set_owner.
password_reset_links: one-time links the owner creates. Only a sha256 of the token is stored.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e7a1c3b5d9f2'
down_revision: Union[str, Sequence[str], None] = 'd4e6a8c0b2f3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.add_column("users", sa.Column("is_owner", sa.Boolean(), nullable=False, server_default="0"))
    op.create_table(
        "password_reset_links",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("used_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_password_reset_links_user_id", "password_reset_links", ["user_id"])


def downgrade():
    op.drop_index("ix_password_reset_links_user_id", table_name="password_reset_links")
    op.drop_table("password_reset_links")
    # SQLite needs batch mode to drop a column
    with op.batch_alter_table("users", recreate="always") as batch_op:
        batch_op.drop_column("is_owner")
