"""
Barrio model - Official CABA neighborhood boundaries for choropleth map
"""
from sqlalchemy import Column, Integer, String, Index
from geoalchemy2 import Geometry

from app.database import Base


class Barrio(Base):
    __tablename__ = "barrios"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String(100), nullable=False, unique=True)
    comuna = Column(Integer, nullable=True)
    geom = Column(Geometry('MULTIPOLYGON', srid=4326), nullable=False)

    __table_args__ = (
        Index('ix_barrios_geom', 'geom', postgresql_using='gist'),
    )
