"""add_previous_price_to_price_history

Revision ID: 3cd8ec7a5338
Revises: 1a373ffba082
Create Date: 2026-02-20 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3cd8ec7a5338'
down_revision: Union[str, None] = '1a373ffba082'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('price_history', sa.Column('previous_price', sa.Numeric(precision=12, scale=2), nullable=True))


def downgrade() -> None:
    op.drop_column('price_history', 'previous_price')
