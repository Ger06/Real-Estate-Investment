"""
PendingProperty model for URL queue management
"""
import uuid
import enum
from datetime import datetime
from sqlalchemy import (
    Column, String, Text, Numeric, DateTime, Enum, ForeignKey, Index, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.property import PropertySource, Currency


class PendingPropertyStatus(str, enum.Enum):
    """Pending property status"""
    PENDING = "PENDING"      # Waiting for review/scraping
    SCRAPED = "SCRAPED"      # Successfully scraped and saved
    SKIPPED = "SKIPPED"      # User manually skipped
    ERROR = "ERROR"          # Scraping failed
    DUPLICATE = "DUPLICATE"  # Already exists in Property table


class PendingProperty(Base):
    """Queue of property URLs discovered by search monitoring"""

    __tablename__ = "pending_properties"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Relationship to search
    saved_search_id = Column(
        UUID(as_uuid=True),
        ForeignKey("saved_searches.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Property URL and metadata
    source_url = Column(Text, nullable=False, index=True)
    source = Column(Enum(PropertySource), nullable=False, index=True)
    source_id = Column(String(255), nullable=True)

    # Preview data (extracted from listing page)
    title = Column(String(500), nullable=True)
    price = Column(Numeric(12, 2), nullable=True)
    currency = Column(Enum(Currency), nullable=True)
    thumbnail_url = Column(Text, nullable=True)
    location_preview = Column(String(500), nullable=True)  # "Palermo, CABA"

    # Status tracking
    status = Column(
        Enum(PendingPropertyStatus),
        default=PendingPropertyStatus.PENDING,
        nullable=False,
        index=True
    )
    error_message = Column(Text, nullable=True)  # If status = ERROR

    # References
    property_id = Column(
        UUID(as_uuid=True),
        ForeignKey("properties.id", ondelete="SET NULL"),
        nullable=True
    )

    # Metadata
    discovered_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    scraped_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    saved_search = relationship("SavedSearch", back_populates="pending_properties")
    property = relationship("Property", backref="pending_entry")

    # Indexes and constraints
    __table_args__ = (
        UniqueConstraint('source_url', name='uq_pending_source_url'),
        Index('idx_pending_search_status', 'saved_search_id', 'status'),
        Index('idx_pending_discovered', 'discovered_at'),
        Index('idx_pending_status', 'status', 'discovered_at'),
    )

    def __repr__(self) -> str:
        return f"<PendingProperty {self.source_url[:50]}>"
