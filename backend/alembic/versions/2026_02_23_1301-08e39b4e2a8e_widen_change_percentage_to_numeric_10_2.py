"""widen_change_percentage_to_numeric_10_2

Revision ID: 08e39b4e2a8e
Revises: 3cd8ec7a5338
Create Date: 2026-02-23 13:01:12.823052

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '08e39b4e2a8e'
down_revision: Union[str, None] = '3cd8ec7a5338'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('price_history', 'change_percentage',
               existing_type=sa.NUMERIC(precision=5, scale=2),
               type_=sa.Numeric(precision=10, scale=2),
               existing_nullable=True)


def downgrade() -> None:
    op.alter_column('price_history', 'change_percentage',
               existing_type=sa.Numeric(precision=10, scale=2),
               type_=sa.NUMERIC(precision=5, scale=2),
               existing_nullable=True)
