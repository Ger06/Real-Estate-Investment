"""
PendingProperty Schemas
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from uuid import UUID


class PendingPropertyResponse(BaseModel):
    """Pending property response schema"""
    id: UUID
    saved_search_id: UUID

    source_url: str
    source: str
    source_id: Optional[str]

    # Preview data
    title: Optional[str]
    price: Optional[float]
    currency: Optional[str]
    thumbnail_url: Optional[str]
    location_preview: Optional[str]

    # Status
    status: str
    error_message: Optional[str]

    # Reference to scraped property (if any)
    property_id: Optional[UUID]

    # Timestamps
    discovered_at: datetime
    scraped_at: Optional[datetime]
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class PendingPropertyWithSearchResponse(PendingPropertyResponse):
    """Pending property with saved search info"""
    saved_search_name: Optional[str] = None


class PendingPropertyListResponse(BaseModel):
    """List of pending properties with pagination"""
    total: int
    skip: int
    limit: int
    items: List[PendingPropertyWithSearchResponse]


class PendingPropertyStats(BaseModel):
    """Pending properties statistics"""
    total_pending: int
    total_scraped: int
    total_skipped: int
    total_errors: int
    by_search: List[Dict[str, Any]] = []
    by_portal: List[Dict[str, Any]] = []


class PendingPropertyScrapeRequest(BaseModel):
    """Request to scrape pending properties"""
    search_id: Optional[UUID] = None  # Filter by search (optional)
    limit: int = Field(50, ge=1, le=200)  # Max properties to scrape


class PendingPropertyScrapeResponse(BaseModel):
    """Response after scraping pending properties"""
    success: bool
    scraped: int
    errors: int
    error_details: List[Dict[str, Any]] = []


class PendingPropertyActionResponse(BaseModel):
    """Response after action on single pending property"""
    success: bool
    message: str
    pending_id: UUID
    property_id: Optional[UUID] = None  # Set if scraped successfully
