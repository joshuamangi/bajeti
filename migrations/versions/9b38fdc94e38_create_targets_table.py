"""create targets table

Revision ID: 9b38fdc94e38
Revises: 877adbb8bce2
Create Date: 2026-03-05 23:43:05.126388

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9b38fdc94e38'
down_revision: Union[str, Sequence[str], None] = '877adbb8bce2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():

    op.create_table(
        'targets',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('budget_id', sa.Integer(), nullable=False),
        sa.Column('category_id', sa.Integer(), nullable=False),

        sa.Column('short_term_amount', sa.Numeric(), nullable=True),
        sa.Column('mid_term_amount', sa.Numeric(), nullable=True),
        sa.Column('long_term_amount', sa.Numeric(), nullable=True),

        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),

        sa.ForeignKeyConstraint(
            ['budget_id'], ['budgets.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(
            ['category_id'], ['categories.id'], ondelete='CASCADE'),

        sa.UniqueConstraint('budget_id', 'category_id',
                            name='uq_budget_category_target')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('targets')
