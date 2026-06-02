"""Fix Remax Capital Federal ID to CF

Revision ID: a8f2c3e4d5b6
Revises: 1a373ffba082
Create Date: 2026-02-27 10:00:00.000000

Capital Federal uses the alphanumeric code 'CF' in Remax URLs,
not the numeric ID '1' that was previously stored.
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'a8f2c3e4d5b6'
down_revision: Union[str, None] = '1a373ffba082'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "UPDATE remax_location_cache SET remax_id = 'CF' "
        "WHERE name IN ('capital federal', 'caba', 'buenos aires')"
    )


def downgrade() -> None:
    op.execute(
        "UPDATE remax_location_cache SET remax_id = '1' "
        "WHERE name IN ('capital federal', 'caba', 'buenos aires')"
    )
