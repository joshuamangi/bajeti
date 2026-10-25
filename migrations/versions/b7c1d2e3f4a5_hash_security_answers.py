"""Hash existing security answers

Revision ID: b7c1d2e3f4a5
Revises: 877adbb8bce2
Create Date: 2026-10-20

Security answers used to be stored in plain text. This rehashes them with bcrypt after
strip and casefold, the same way the application does now.

UPGRADE is safe to run twice: values that already look like a bcrypt hash are skipped.
Take a copy of the database file first (deploy/backup/backup.sh) and try it on that copy.

DOWNGRADE CANNOT RESTORE THE PLAIN TEXT. A hash cannot be reversed, so the downgrade
leaves the hashes in place. After a downgrade to code that compares plain text, password
reset fails for every account until its owner sets a new answer on the profile page.
Restore the pre-migration backup if you need the old values back.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from passlib.context import CryptContext

revision: str = 'b7c1d2e3f4a5'
down_revision: Union[str, Sequence[str], None] = '877adbb8bce2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _looks_hashed(value: str) -> bool:
    return value.startswith("$2") and len(value) == 60


def rehash(value):
    """Return the hash of a plain answer; leave empty and already hashed values alone."""
    if not value or _looks_hashed(value):
        return value
    return pwd_context.hash(value.strip().casefold())


def upgrade() -> None:
    bind = op.get_bind()
    users = sa.table("users", sa.column("id", sa.Integer),
                     sa.column("security_answer", sa.String))
    rows = bind.execute(
        sa.select(users.c.id, users.c.security_answer)
        .where(users.c.security_answer.is_not(None))
    ).fetchall()
    for user_id, answer in rows:
        hashed = rehash(answer)
        if hashed != answer:
            bind.execute(users.update().where(users.c.id == user_id)
                         .values(security_answer=hashed))


def downgrade() -> None:
    # Hashes cannot be turned back into the original answers; see the module docstring.
    pass
