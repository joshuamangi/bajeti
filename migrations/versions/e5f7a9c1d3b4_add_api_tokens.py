"""add phone tokens for the iPhone Shortcut

Revision ID: e5f7a9c1d3b4
Revises: e7a1c3b5d9f2
Create Date: 2026-10-31 12:00:00.000000

api_tokens: one row per phone token, stored as a SHA-256 hash, scope payments:capture.
New table only.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e5f7a9c1d3b4'
down_revision: Union[str, Sequence[str], None] = 'e7a1c3b5d9f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.create_table(
        "api_tokens",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(length=40), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("prefix", sa.String(length=12), nullable=False),
        sa.Column("scope", sa.String(length=30), nullable=False),
        sa.Column("created_at", sa.DateTime()),
        sa.Column("last_used_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("token_hash", name="uq_api_token_hash"),
    )
    op.create_index("ix_api_tokens_user_id", "api_tokens", ["user_id"])


def downgrade():
    op.drop_index("ix_api_tokens_user_id", table_name="api_tokens")
    op.drop_table("api_tokens")
