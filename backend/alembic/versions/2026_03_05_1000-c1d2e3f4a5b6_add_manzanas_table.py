"""Add manzanas table for choropleth map

Revision ID: c1d2e3f4a5b6
Revises: a8f2c3e4d5b6
Create Date: 2026-03-05 10:00:00.000000

Stores CABA city block (manzana) polygons from open data portal
for choropleth map visualization.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from geoalchemy2 import Geometry


revision: str = 'c1d2e3f4a5b6'
down_revision: Union[str, None] = 'a8f2c3e4d5b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'manzanas',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('manzana_id', sa.String(50), nullable=True),
        sa.Column('smp', sa.String(50), nullable=True),
        sa.Column('barrio', sa.String(100), nullable=True),
        sa.Column('comuna', sa.Integer(), nullable=True),
        sa.Column('geom', Geometry('MULTIPOLYGON', srid=4326), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('manzana_id'),
    )
    op.create_index(
        'ix_manzanas_geom',
        'manzanas',
        ['geom'],
        postgresql_using='gist',
    )


def downgrade() -> None:
    op.drop_index('ix_manzanas_geom', table_name='manzanas')
    op.drop_table('manzanas')
