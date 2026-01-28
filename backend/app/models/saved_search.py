"""
SavedSearch model for property monitoring
"""
import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Text, Numeric, Integer, DateTime, Enum, Boolean,
    ForeignKey, Index
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.property import PropertyType, OperationType, Currency


class SavedSearch(Base):
    """Saved property search configuration for monitoring"""

    __tablename__ = "saved_searches"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # User relationship (nullable while auth is disabled)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)

    # Search configuration
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Portal selection (can monitor multiple portals)
    # ["argenprop", "zonaprop", "remax", "mercadolibre"]
    portals = Column(JSONB, nullable=False)

    # Search filters
    property_type = Column(Enum(PropertyType), nullable=True, index=True)
    operation_type = Column(Enum(OperationType), nullable=False, index=True)

    # Location filters
    city = Column(String(255), nullable=True)
    neighborhoods = Column(JSONB, nullable=True)  # ["Palermo", "Recoleta"]
    province = Column(String(255), nullable=True)

    # Price range
    min_price = Column(Numeric(12, 2), nullable=True)
    max_price = Column(Numeric(12, 2), nullable=True)
    currency = Column(Enum(Currency), nullable=False, default=Currency.USD)

    # Area range (m²)
    min_area = Column(Numeric(10, 2), nullable=True)
    max_area = Column(Numeric(10, 2), nullable=True)

    # Additional filters
    min_bedrooms = Column(Integer, nullable=True)
    max_bedrooms = Column(Integer, nullable=True)
    min_bathrooms = Column(Integer, nullable=True)

    # Execution configuration
    auto_scrape = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # Tracking
    last_executed_at = Column(DateTime, nullable=True, index=True)
    total_executions = Column(Integer, default=0, nullable=False)
    total_properties_found = Column(Integer, default=0, nullable=False)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", backref="saved_searches")
    pending_properties = relationship(
        "PendingProperty",
        back_populates="saved_search",
        cascade="all, delete-orphan",
        lazy="selectin"
    )

    # Indexes
    __table_args__ = (
        Index('idx_search_user_active', 'user_id', 'is_active'),
        Index('idx_search_last_executed', 'last_executed_at'),
    )

    def __repr__(self) -> str:
        return f"<SavedSearch {self.name}>"
