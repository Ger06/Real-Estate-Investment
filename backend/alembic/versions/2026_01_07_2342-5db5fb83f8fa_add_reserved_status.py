"""add reserved status

Revision ID: 5db5fb83f8fa
Revises: ab7bde6fa664
Create Date: 2026-01-07 23:42:11.190540

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5db5fb83f8fa'
down_revision: Union[str, None] = 'ab7bde6fa664'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add 'RESERVED' value to propertystatus enum
    # We use commit to ensure it runs outside of transaction block if needed, 
    # but Alembic usually handles transactions. 
    # For safety with enums, we can use this approach:
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE propertystatus ADD VALUE IF NOT EXISTS 'RESERVED'")


def downgrade() -> None:
    # Postgres does not support removing values from enums
    pass
