"""
Manzana model - City blocks of CABA for choropleth map
"""
from sqlalchemy import Column, Integer, String, Index
from geoalchemy2 import Geometry

from app.database import Base


class Manzana(Base):
    __tablename__ = "manzanas"

    id = Column(Integer, primary_key=True, autoincrement=True)
    manzana_id = Column(String(50), unique=True, nullable=True)
    smp = Column(String(50), nullable=True)
    barrio = Column(String(100), nullable=True)
    comuna = Column(Integer, nullable=True)
    geom = Column(Geometry('MULTIPOLYGON', srid=4326), nullable=False)

    __table_args__ = (
        Index('ix_manzanas_geom', 'geom', postgresql_using='gist'),
    )
