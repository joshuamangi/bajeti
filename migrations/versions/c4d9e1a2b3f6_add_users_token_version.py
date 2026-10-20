"""Add users.token_version

Revision ID: c4d9e1a2b3f6
Revises: b7c1d2e3f4a5
Create Date: 2026-10-20

A counter inside every access token. Raising it (password reset, "log out everywhere")
makes all earlier tokens invalid. Existing rows start at 0, and tokens issued before this
change carry no version, which counts as 0, so nobody is logged out by the deploy.

The downgrade drops the column. Code from before this change ignores the version, so old
tokens work again after a downgrade.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'c4d9e1a2b3f6'
down_revision: Union[str, Sequence[str], None] = 'b7c1d2e3f4a5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.add_column(sa.Column("token_version", sa.Integer(), nullable=False,
                                   server_default="0"))


def downgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.drop_column("token_version")
