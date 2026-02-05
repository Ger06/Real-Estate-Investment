"""
SavedSearch Schemas
"""
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, field_validator
from uuid import UUID


# Valid portals for validation
VALID_PORTALS = ["argenprop", "zonaprop", "remax", "mercadolibre"]


class SavedSearchCreate(BaseModel):
    """Schema for creating a saved search"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None

    # Portals to monitor (at least one required)
    portals: List[str] = Field(..., min_length=1)

    # Search filters
    property_type: Optional[str] = None  # casa, departamento, etc.
    operation_type: str = "venta"  # venta, alquiler

    # Location filters
    city: Optional[str] = None
    neighborhoods: Optional[List[str]] = None
    province: Optional[str] = None

    # Price range
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    currency: str = "USD"

    # Area range (m²)
    min_area: Optional[float] = None
    max_area: Optional[float] = None

    # Additional filters
    min_bedrooms: Optional[int] = None
    max_bedrooms: Optional[int] = None
    min_bathrooms: Optional[int] = None

    # Execution configuration
    auto_scrape: bool = False
    is_active: bool = True

    @field_validator('portals')
    @classmethod
    def validate_portals(cls, v: List[str]) -> List[str]:
        """Validate that all portals are valid"""
        for portal in v:
            if portal.lower() not in VALID_PORTALS:
                raise ValueError(f"Invalid portal: {portal}. Valid portals: {VALID_PORTALS}")
        return [p.lower() for p in v]

    @field_validator('operation_type')
    @classmethod
    def validate_operation_type(cls, v: str) -> str:
        """Validate operation type"""
        valid_ops = ["venta", "alquiler", "alquiler_temporal"]
        if v.lower() not in valid_ops:
            raise ValueError(f"Invalid operation type: {v}. Valid types: {valid_ops}")
        return v.lower()


class SavedSearchUpdate(BaseModel):
    """Schema for updating a saved search"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    portals: Optional[List[str]] = None
    property_type: Optional[str] = None
    operation_type: Optional[str] = None
    city: Optional[str] = None
    neighborhoods: Optional[List[str]] = None
    province: Optional[str] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    currency: Optional[str] = None
    min_area: Optional[float] = None
    max_area: Optional[float] = None
    min_bedrooms: Optional[int] = None
    max_bedrooms: Optional[int] = None
    min_bathrooms: Optional[int] = None
    auto_scrape: Optional[bool] = None
    is_active: Optional[bool] = None

    @field_validator('portals')
    @classmethod
    def validate_portals(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate that all portals are valid"""
        if v is None:
            return v
        for portal in v:
            if portal.lower() not in VALID_PORTALS:
                raise ValueError(f"Invalid portal: {portal}. Valid portals: {VALID_PORTALS}")
        return [p.lower() for p in v]


class SavedSearchResponse(BaseModel):
    """Saved search response schema"""
    id: UUID
    user_id: Optional[UUID] = None  # Optional while auth is disabled
    name: str
    description: Optional[str]

    portals: List[str]
    property_type: Optional[str]
    operation_type: str

    city: Optional[str]
    neighborhoods: Optional[List[str]]
    province: Optional[str]

    min_price: Optional[float]
    max_price: Optional[float]
    currency: str

    min_area: Optional[float]
    max_area: Optional[float]

    min_bedrooms: Optional[int]
    max_bedrooms: Optional[int]
    min_bathrooms: Optional[int]

    auto_scrape: bool
    is_active: bool

    last_executed_at: Optional[datetime]
    total_executions: int
    total_properties_found: int

    # Computed field - count of pending properties
    pending_count: int = 0

    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class SavedSearchListResponse(BaseModel):
    """List of saved searches with pagination"""
    total: int
    skip: int
    limit: int
    items: List[SavedSearchResponse]


class ImportCardData(BaseModel):
    """Schema for a single scraped property card to import"""
    source_url: str
    source_id: Optional[str] = None
    title: Optional[str] = None
    price: Optional[float] = None
    currency: Optional[str] = "USD"
    thumbnail_url: Optional[str] = None
    location_preview: Optional[str] = None
    description: Optional[str] = None
    total_area: Optional[float] = None
    covered_area: Optional[float] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[int] = None
    parking_spaces: Optional[int] = None
    address: Optional[str] = None


class ImportCardsRequest(BaseModel):
    """Request body for importing scraped cards"""
    cards: List[ImportCardData]


class SavedSearchExecuteResponse(BaseModel):
    """Response after executing a saved search"""
    success: bool
    search_id: UUID
    search_name: str
    total_found: int  # Total URLs found in listings
    new_properties: int  # New URLs (not existing)
    duplicates: int  # URLs already in DB
    scraped: int  # Auto-scraped (if auto_scrape=true)
    pending: int  # Added to pending queue
    errors: List[dict] = []
