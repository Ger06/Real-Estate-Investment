"""
Remax Cache models for storing verified IDs of locations and property types
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class RemaxLocationCache(Base):
    """
    Cache for Remax location IDs.

    Remax uses internal IDs for each neighborhood/city. This table stores
    verified ID mappings that have been confirmed to work.

    Example: Chacarita -> ID 25011, Villa Devoto -> ID 25044
    """
    __tablename__ = "remax_location_cache"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Normalized name for lookup (lowercase, e.g., "chacarita", "villa devoto")
    name = Column(String(255), unique=True, nullable=False, index=True)

    # Remax internal ID (e.g., "25011", "25044")
    remax_id = Column(String(50), nullable=False)

    # Display name for UI (e.g., "Chacarita", "Villa Devoto")
    display_name = Column(String(255), nullable=False)

    # Parent location for grouping (e.g., "Capital Federal", "GBA Norte")
    parent_location = Column(String(255), nullable=True)

    # Tracking
    verified_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index('idx_remax_location_parent', 'parent_location'),
    )

    def __repr__(self) -> str:
        return f"<RemaxLocationCache {self.name} -> {self.remax_id}>"


class RemaxPropertyTypeCache(Base):
    """
    Cache for Remax property type IDs.

    Remax uses internal IDs for property types. Some types map to multiple IDs.

    Example: Departamento -> "1,2", PH -> "12", Casa -> "3,4"
    """
    __tablename__ = "remax_property_type_cache"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Normalized name for lookup (lowercase, e.g., "departamento", "ph")
    name = Column(String(100), unique=True, nullable=False, index=True)

    # Remax internal IDs (comma-separated if multiple, e.g., "1,2", "12")
    remax_ids = Column(String(100), nullable=False)

    # Display name for UI (e.g., "Departamento", "PH")
    display_name = Column(String(100), nullable=False)

    # Tracking
    verified_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self) -> str:
        return f"<RemaxPropertyTypeCache {self.name} -> {self.remax_ids}>"
