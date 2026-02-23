"""Add remax cache tables

Revision ID: 1a373ffba082
Revises: 91215869b900
Create Date: 2026-01-27 10:59:00.000000

"""
from typing import Sequence, Union
import uuid
from datetime import datetime

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '1a373ffba082'
down_revision: Union[str, None] = '91215869b900'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create remax_location_cache table
    op.create_table(
        'remax_location_cache',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, default=uuid.uuid4),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('remax_id', sa.String(50), nullable=False),
        sa.Column('display_name', sa.String(255), nullable=False),
        sa.Column('parent_location', sa.String(255), nullable=True),
        sa.Column('verified_at', sa.DateTime(), nullable=False, default=datetime.utcnow),
        sa.Column('created_at', sa.DateTime(), nullable=False, default=datetime.utcnow),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_remax_location_cache_name', 'remax_location_cache', ['name'], unique=True)
    op.create_index('idx_remax_location_parent', 'remax_location_cache', ['parent_location'])

    # Create remax_property_type_cache table
    op.create_table(
        'remax_property_type_cache',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, default=uuid.uuid4),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('remax_ids', sa.String(100), nullable=False),
        sa.Column('display_name', sa.String(100), nullable=False),
        sa.Column('verified_at', sa.DateTime(), nullable=False, default=datetime.utcnow),
        sa.Column('created_at', sa.DateTime(), nullable=False, default=datetime.utcnow),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_remax_property_type_cache_name', 'remax_property_type_cache', ['name'], unique=True)

    # Pre-populate with verified location IDs
    now = datetime.utcnow()

    # Capital Federal neighborhoods
    locations_caba = [
        ("capital federal", "1", "Capital Federal", "Capital Federal"),
        ("caba", "1", "Capital Federal", "Capital Federal"),
        ("buenos aires", "1", "Capital Federal", "Capital Federal"),
        ("almagro", "25002", "Almagro", "Capital Federal"),
        ("balvanera", "25003", "Balvanera", "Capital Federal"),
        ("barracas", "25004", "Barracas", "Capital Federal"),
        ("barrio norte", "25005", "Barrio Norte", "Capital Federal"),
        ("belgrano", "25006", "Belgrano", "Capital Federal"),
        ("boedo", "25009", "Boedo", "Capital Federal"),
        ("caballito", "25010", "Caballito", "Capital Federal"),
        ("chacarita", "25011", "Chacarita", "Capital Federal"),
        ("coghlan", "25012", "Coghlan", "Capital Federal"),
        ("colegiales", "25014", "Colegiales", "Capital Federal"),
        ("constitucion", "25015", "Constitucion", "Capital Federal"),
        ("flores", "25019", "Flores", "Capital Federal"),
        ("floresta", "25020", "Floresta", "Capital Federal"),
        ("la boca", "25022", "La Boca", "Capital Federal"),
        ("liniers", "25024", "Liniers", "Capital Federal"),
        ("mataderos", "25026", "Mataderos", "Capital Federal"),
        ("monte castro", "25027", "Monte Castro", "Capital Federal"),
        ("monserrat", "25028", "Monserrat", "Capital Federal"),
        ("nueva pompeya", "25029", "Nueva Pompeya", "Capital Federal"),
        ("nunez", "25031", "Nunez", "Capital Federal"),
        ("palermo", "25033", "Palermo", "Capital Federal"),
        ("parque chacabuco", "25034", "Parque Chacabuco", "Capital Federal"),
        ("parque chas", "25035", "Parque Chas", "Capital Federal"),
        ("parque patricios", "25036", "Parque Patricios", "Capital Federal"),
        ("paternal", "25037", "Paternal", "Capital Federal"),
        ("puerto madero", "25040", "Puerto Madero", "Capital Federal"),
        ("recoleta", "25041", "Recoleta", "Capital Federal"),
        ("retiro", "25042", "Retiro", "Capital Federal"),
        ("saavedra", "25043", "Saavedra", "Capital Federal"),
        ("san cristobal", "25047", "San Cristobal", "Capital Federal"),
        ("san nicolas", "25045", "San Nicolas", "Capital Federal"),
        ("san telmo", "25046", "San Telmo", "Capital Federal"),
        ("velez sarsfield", "25048", "Velez Sarsfield", "Capital Federal"),
        ("versalles", "25049", "Versalles", "Capital Federal"),
        ("villa crespo", "25053", "Villa Crespo", "Capital Federal"),
        ("villa del parque", "25052", "Villa del Parque", "Capital Federal"),
        ("villa devoto", "25044", "Villa Devoto", "Capital Federal"),
        ("devoto", "25044", "Villa Devoto", "Capital Federal"),
        ("villa lugano", "25058", "Villa Lugano", "Capital Federal"),
        ("villa luro", "25059", "Villa Luro", "Capital Federal"),
        ("villa ortuzar", "25060", "Villa Ortuzar", "Capital Federal"),
        ("villa pueyrredon", "25061", "Villa Pueyrredon", "Capital Federal"),
        ("villa real", "25062", "Villa Real", "Capital Federal"),
        ("villa riachuelo", "25063", "Villa Riachuelo", "Capital Federal"),
        ("villa santa rita", "25064", "Villa Santa Rita", "Capital Federal"),
        ("villa soldati", "25065", "Villa Soldati", "Capital Federal"),
        ("villa urquiza", "25054", "Villa Urquiza", "Capital Federal"),
    ]

    # GBA zones
    locations_gba = [
        ("zona norte", "2", "GBA Norte", "GBA"),
        ("zona sur", "3", "GBA Sur", "GBA"),
        ("zona oeste", "4", "GBA Oeste", "GBA"),
        ("san isidro", "21", "San Isidro", "GBA Norte"),
        ("tigre", "22", "Tigre", "GBA Norte"),
        ("pilar", "23", "Pilar", "GBA Norte"),
        ("vicente lopez", "24", "Vicente Lopez", "GBA Norte"),
    ]

    # Other cities/provinces
    locations_other = [
        ("la plata", "5", "La Plata", "Buenos Aires"),
        ("mar del plata", "6", "Mar del Plata", "Buenos Aires"),
        ("cordoba", "14", "Cordoba", "Cordoba"),
        ("rosario", "15", "Rosario", "Santa Fe"),
        ("mendoza", "13", "Mendoza", "Mendoza"),
        ("salta", "16", "Salta", "Salta"),
        ("santa fe", "17", "Santa Fe", "Santa Fe"),
        ("tucuman", "18", "Tucuman", "Tucuman"),
    ]

    all_locations = locations_caba + locations_gba + locations_other

    # Insert locations
    op.bulk_insert(
        sa.table(
            'remax_location_cache',
            sa.column('id', postgresql.UUID),
            sa.column('name', sa.String),
            sa.column('remax_id', sa.String),
            sa.column('display_name', sa.String),
            sa.column('parent_location', sa.String),
            sa.column('verified_at', sa.DateTime),
            sa.column('created_at', sa.DateTime),
        ),
        [
            {
                'id': str(uuid.uuid4()),
                'name': name,
                'remax_id': remax_id,
                'display_name': display_name,
                'parent_location': parent,
                'verified_at': now,
                'created_at': now,
            }
            for name, remax_id, display_name, parent in all_locations
        ]
    )

    # Pre-populate with verified property type IDs
    property_types = [
        ("departamento", "1,2", "Departamento"),
        ("casa", "3,4", "Casa"),
        ("ph", "12", "PH"),
        ("terreno", "6,7", "Terreno"),
        ("local", "9,10,11", "Local Comercial"),
        ("oficina", "8", "Oficina"),
        ("cochera", "13", "Cochera"),
        ("galpon", "14", "Galpon"),
    ]

    op.bulk_insert(
        sa.table(
            'remax_property_type_cache',
            sa.column('id', postgresql.UUID),
            sa.column('name', sa.String),
            sa.column('remax_ids', sa.String),
            sa.column('display_name', sa.String),
            sa.column('verified_at', sa.DateTime),
            sa.column('created_at', sa.DateTime),
        ),
        [
            {
                'id': str(uuid.uuid4()),
                'name': name,
                'remax_ids': remax_ids,
                'display_name': display_name,
                'verified_at': now,
                'created_at': now,
            }
            for name, remax_ids, display_name in property_types
        ]
    )


def downgrade() -> None:
    op.drop_index('ix_remax_property_type_cache_name', table_name='remax_property_type_cache')
    op.drop_table('remax_property_type_cache')
    op.drop_index('idx_remax_location_parent', table_name='remax_location_cache')
    op.drop_index('ix_remax_location_cache_name', table_name='remax_location_cache')
    op.drop_table('remax_location_cache')
