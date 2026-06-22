"""
Property model for real estate listings
"""
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column, String, Text, Numeric, Integer, DateTime, Enum, Boolean,
    ForeignKey, Index
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from geoalchemy2 import Geography
import enum

from app.database import Base


class PropertySource(str, enum.Enum):
    """Property data source"""
    ARGENPROP = "argenprop"
    ZONAPROP = "zonaprop"
    REMAX = "remax"
    MERCADOLIBRE = "mercadolibre"
    MANUAL = "manual"


class PropertyType(str, enum.Enum):
    """Type of property"""
    CASA = "casa"
    PH = "ph"
    DEPARTAMENTO = "departamento"
    TERRENO = "terreno"
    LOCAL = "local"
    OFICINA = "oficina"


class OperationType(str, enum.Enum):
    """Operation type"""
    VENTA = "venta"
    ALQUILER = "alquiler"
    ALQUILER_TEMPORAL = "alquiler_temporal"


class Currency(str, enum.Enum):
    """Currency"""
    USD = "USD"
    ARS = "ARS"


class PropertyStatus(str, enum.Enum):
    """Property status"""
    ACTIVE = "ACTIVE"
    SOLD = "SOLD"
    RENTED = "RENTED"
    RESERVED = "RESERVED"
    REMOVED = "REMOVED"


class PropertyCondition(str, enum.Enum):
    """Property condition"""
    NEW = "nuevo"
    BRAND_NEW = "a_estrenar"
    GOOD = "buen_estado"
    TO_REFURBISH = "a_refaccionar"
    UNDER_CONSTRUCTION = "en_construccion"
    EXCELLENT = "excelente"


class Property(Base):
    """Property model"""
    
    __tablename__ = "properties"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Source information
    source = Column(Enum(PropertySource), nullable=False, index=True)
    source_url = Column(Text, nullable=True)
    source_id = Column(String(255), nullable=True)
    
    # Property details
    property_type = Column(Enum(PropertyType), nullable=False, index=True)
    operation_type = Column(Enum(OperationType), nullable=False, index=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    
    # Pricing
    price = Column(Numeric(12, 2), nullable=False, index=True)
    currency = Column(Enum(Currency), nullable=False, default=Currency.USD)
    price_per_sqm = Column(Numeric(10, 2), nullable=True)
    estimated_value = Column(Numeric(12, 2), nullable=True)  # Valor estimado por el analista
    
    # Location
    location = Column(Geography(geometry_type='POINT', srid=4326), nullable=True)
    address = Column(String(500), nullable=True)
    street = Column(String(255), nullable=True)  # Calle
    street_number = Column(String(50), nullable=True)  # Altura
    neighborhood = Column(String(255), nullable=True, index=True)
    city = Column(String(255), nullable=False, index=True)
    province = Column(String(255), nullable=False)
    postal_code = Column(String(20), nullable=True)
    
    # Areas (in square meters)
    covered_area = Column(Numeric(10, 2), nullable=True)
    semi_covered_area = Column(Numeric(10, 2), nullable=True)
    uncovered_area = Column(Numeric(10, 2), nullable=True)
    total_area = Column(Numeric(10, 2), nullable=True)
    
    # Property characteristics
    floor_level = Column(Integer, nullable=True)
    bedrooms = Column(Integer, nullable=True)
    bathrooms = Column(Integer, nullable=True)
    parking_spaces = Column(Integer, nullable=True)
    amenities = Column(JSONB, nullable=True)
    property_condition = Column(Enum(PropertyCondition), nullable=True)  # Estado del inmueble
    
    # Contact information
    real_estate_agency = Column(String(255), nullable=True)
    contact_info = Column(JSONB, nullable=True)

    # Analysis fields
    observations = Column(Text, nullable=True)  # Observaciones: humedad, escalera, etc.

    # Status
    status = Column(Enum(PropertyStatus), nullable=False, default=PropertyStatus.ACTIVE, index=True)
    
    # Metadata
    scraped_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    
    # Relationships
    # created_by_user = relationship("User", back_populates="properties", foreign_keys=[created_by])
    images = relationship("PropertyImage", back_populates="property", cascade="all, delete-orphan", lazy="selectin")
    price_history = relationship("PriceHistory", back_populates="property", cascade="all, delete-orphan", lazy="selectin")
    # visits = relationship("PropertyVisit", back_populates="property", cascade="all, delete-orphan")
    investment_projects = relationship("InvestmentProject", back_populates="property")
    
    # Indexes
    __table_args__ = (
        Index('idx_property_location', 'location', postgresql_using='gist'),
        Index('idx_property_price_range', 'price', 'currency'),
        Index('idx_property_search', 'city', 'neighborhood', 'property_type'),
    )
    
    def __repr__(self) -> str:
        return f"<Property {self.title[:50]}>"


class PropertyImage(Base):
    """Property image model"""
    
    __tablename__ = "property_images"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    property_id = Column(UUID(as_uuid=True), ForeignKey("properties.id"), nullable=False)
    url = Column(Text, nullable=True)
    file_path = Column(String(500), nullable=True)
    is_primary = Column(Boolean, default=False, nullable=False)
    order = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    property = relationship("Property", back_populates="images")
    
    def __repr__(self) -> str:
        return f"<PropertyImage {self.id}>"


class PriceHistory(Base):
    """Price history tracking"""
    
    __tablename__ = "price_history"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    property_id = Column(UUID(as_uuid=True), ForeignKey("properties.id"), nullable=False, index=True)
    price = Column(Numeric(12, 2), nullable=False)
    previous_price = Column(Numeric(12, 2), nullable=True)
    currency = Column(Enum(Currency), nullable=False)
    change_percentage = Column(Numeric(10, 2), nullable=True)
    recorded_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    property = relationship("Property", back_populates="price_history")
    
    __table_args__ = (
        Index('idx_price_history_lookup', 'property_id', 'recorded_at'),
    )
    
    def __repr__(self) -> str:
        return f"<PriceHistory {self.property_id} - {self.price}>"


class PropertyVisit(Base):
    """Property visit tracking"""
    
    __tablename__ = "property_visits"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    property_id = Column(UUID(as_uuid=True), ForeignKey("properties.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    visit_date = Column(DateTime, nullable=False)
    notes = Column(Text, nullable=True)
    rating = Column(Integer, nullable=True)  # 1-5 scale
    photos = Column(JSONB, nullable=True)  # Array of photo URLs/paths
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    # property = relationship("Property", back_populates="visits")
    # user = relationship("User", back_populates="visits")
    
    def __repr__(self) -> str:
        return f"<PropertyVisit {self.property_id} - {self.visit_date}>"
