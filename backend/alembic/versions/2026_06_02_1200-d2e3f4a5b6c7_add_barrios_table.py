"""Add barrios table for choropleth map

Revision ID: d2e3f4a5b6c7
Revises: c1d2e3f4a5b6
Create Date: 2026-06-02 12:00:00.000000

Stores official CABA neighborhood (barrio) polygon boundaries from the
Buenos Aires open data portal for choropleth map visualization.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from geoalchemy2 import Geometry


revision: str = 'd2e3f4a5b6c7'
down_revision: Union[str, None] = 'c1d2e3f4a5b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'barrios',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('nombre', sa.String(100), nullable=False),
        sa.Column('comuna', sa.Integer(), nullable=True),
        sa.Column('geom', Geometry('MULTIPOLYGON', srid=4326), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('nombre'),
    )
    op.create_index(
        'ix_barrios_geom',
        'barrios',
        ['geom'],
        postgresql_using='gist',
    )


def downgrade() -> None:
    op.drop_index('ix_barrios_geom', table_name='barrios')
    op.drop_table('barrios')
