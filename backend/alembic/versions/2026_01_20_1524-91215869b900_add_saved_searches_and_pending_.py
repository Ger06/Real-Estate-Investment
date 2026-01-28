"""Add saved_searches and pending_properties

Revision ID: 91215869b900
Revises: 5db5fb83f8fa
Create Date: 2026-01-20 15:24:19.778732

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '91215869b900'
down_revision: Union[str, None] = '5db5fb83f8fa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create the new enum type for pending property status
    pendingpropertystatus = postgresql.ENUM(
        'PENDING', 'SCRAPED', 'SKIPPED', 'ERROR', 'DUPLICATE',
        name='pendingpropertystatus',
        create_type=False
    )
    pendingpropertystatus.create(op.get_bind(), checkfirst=True)

    # Create saved_searches table (using existing enum types)
    op.create_table('saved_searches',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('portals', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('property_type', postgresql.ENUM('CASA', 'PH', 'DEPARTAMENTO', 'TERRENO', 'LOCAL', 'OFICINA', name='propertytype', create_type=False), nullable=True),
        sa.Column('operation_type', postgresql.ENUM('VENTA', 'ALQUILER', 'ALQUILER_TEMPORAL', name='operationtype', create_type=False), nullable=False),
        sa.Column('city', sa.String(length=255), nullable=True),
        sa.Column('neighborhoods', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('province', sa.String(length=255), nullable=True),
        sa.Column('min_price', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('max_price', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('currency', postgresql.ENUM('USD', 'ARS', name='currency', create_type=False), nullable=False),
        sa.Column('min_area', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('max_area', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('min_bedrooms', sa.Integer(), nullable=True),
        sa.Column('max_bedrooms', sa.Integer(), nullable=True),
        sa.Column('min_bathrooms', sa.Integer(), nullable=True),
        sa.Column('auto_scrape', sa.Boolean(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('last_executed_at', sa.DateTime(), nullable=True),
        sa.Column('total_executions', sa.Integer(), nullable=False),
        sa.Column('total_properties_found', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_search_last_executed', 'saved_searches', ['last_executed_at'], unique=False)
    op.create_index('idx_search_user_active', 'saved_searches', ['user_id', 'is_active'], unique=False)
    op.create_index(op.f('ix_saved_searches_operation_type'), 'saved_searches', ['operation_type'], unique=False)
    op.create_index(op.f('ix_saved_searches_property_type'), 'saved_searches', ['property_type'], unique=False)
    op.create_index(op.f('ix_saved_searches_user_id'), 'saved_searches', ['user_id'], unique=False)

    # Create pending_properties table
    op.create_table('pending_properties',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('saved_search_id', sa.UUID(), nullable=False),
        sa.Column('source_url', sa.Text(), nullable=False),
        sa.Column('source', postgresql.ENUM('ARGENPROP', 'ZONAPROP', 'REMAX', 'MERCADOLIBRE', 'MANUAL', name='propertysource', create_type=False), nullable=False),
        sa.Column('source_id', sa.String(length=255), nullable=True),
        sa.Column('title', sa.String(length=500), nullable=True),
        sa.Column('price', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('currency', postgresql.ENUM('USD', 'ARS', name='currency', create_type=False), nullable=True),
        sa.Column('thumbnail_url', sa.Text(), nullable=True),
        sa.Column('location_preview', sa.String(length=500), nullable=True),
        sa.Column('status', postgresql.ENUM('PENDING', 'SCRAPED', 'SKIPPED', 'ERROR', 'DUPLICATE', name='pendingpropertystatus', create_type=False), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('property_id', sa.UUID(), nullable=True),
        sa.Column('discovered_at', sa.DateTime(), nullable=False),
        sa.Column('scraped_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['property_id'], ['properties.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['saved_search_id'], ['saved_searches.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('source_url', name='uq_pending_source_url')
    )
    op.create_index('idx_pending_discovered', 'pending_properties', ['discovered_at'], unique=False)
    op.create_index('idx_pending_search_status', 'pending_properties', ['saved_search_id', 'status'], unique=False)
    op.create_index('idx_pending_status', 'pending_properties', ['status', 'discovered_at'], unique=False)
    op.create_index(op.f('ix_pending_properties_saved_search_id'), 'pending_properties', ['saved_search_id'], unique=False)
    op.create_index(op.f('ix_pending_properties_source'), 'pending_properties', ['source'], unique=False)
    op.create_index(op.f('ix_pending_properties_source_url'), 'pending_properties', ['source_url'], unique=False)
    op.create_index(op.f('ix_pending_properties_status'), 'pending_properties', ['status'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_pending_properties_status'), table_name='pending_properties')
    op.drop_index(op.f('ix_pending_properties_source_url'), table_name='pending_properties')
    op.drop_index(op.f('ix_pending_properties_source'), table_name='pending_properties')
    op.drop_index(op.f('ix_pending_properties_saved_search_id'), table_name='pending_properties')
    op.drop_index('idx_pending_status', table_name='pending_properties')
    op.drop_index('idx_pending_search_status', table_name='pending_properties')
    op.drop_index('idx_pending_discovered', table_name='pending_properties')
    op.drop_table('pending_properties')
    op.drop_index(op.f('ix_saved_searches_user_id'), table_name='saved_searches')
    op.drop_index(op.f('ix_saved_searches_property_type'), table_name='saved_searches')
    op.drop_index(op.f('ix_saved_searches_operation_type'), table_name='saved_searches')
    op.drop_index('idx_search_user_active', table_name='saved_searches')
    op.drop_index('idx_search_last_executed', table_name='saved_searches')
    op.drop_table('saved_searches')

    # Drop the new enum type
    postgresql.ENUM(name='pendingpropertystatus').drop(op.get_bind(), checkfirst=True)
