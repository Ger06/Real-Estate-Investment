"""
Remax Cache Schemas
"""
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field
from uuid import UUID


# ============ Location Cache Schemas ============

class RemaxLocationCreate(BaseModel):
    """Schema for creating a new Remax location cache entry"""
    name: str = Field(..., min_length=1, max_length=255, description="Normalized name (lowercase)")
    remax_id: str = Field(..., min_length=1, max_length=50, description="Remax internal ID")
    display_name: str = Field(..., min_length=1, max_length=255, description="Display name for UI")
    parent_location: Optional[str] = Field(None, max_length=255, description="Parent location (e.g., Capital Federal)")


class RemaxLocationUpdate(BaseModel):
    """Schema for updating a Remax location cache entry"""
    remax_id: Optional[str] = Field(None, min_length=1, max_length=50)
    display_name: Optional[str] = Field(None, min_length=1, max_length=255)
    parent_location: Optional[str] = Field(None, max_length=255)


class RemaxLocationResponse(BaseModel):
    """Response schema for Remax location cache entry"""
    id: UUID
    name: str
    remax_id: str
    display_name: str
    parent_location: Optional[str]
    verified_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True


class RemaxLocationListResponse(BaseModel):
    """List response for Remax locations"""
    total: int
    items: List[RemaxLocationResponse]


# ============ Property Type Cache Schemas ============

class RemaxPropertyTypeCreate(BaseModel):
    """Schema for creating a new Remax property type cache entry"""
    name: str = Field(..., min_length=1, max_length=100, description="Normalized name (lowercase)")
    remax_ids: str = Field(..., min_length=1, max_length=100, description="Remax internal IDs (comma-separated)")
    display_name: str = Field(..., min_length=1, max_length=100, description="Display name for UI")


class RemaxPropertyTypeUpdate(BaseModel):
    """Schema for updating a Remax property type cache entry"""
    remax_ids: Optional[str] = Field(None, min_length=1, max_length=100)
    display_name: Optional[str] = Field(None, min_length=1, max_length=100)


class RemaxPropertyTypeResponse(BaseModel):
    """Response schema for Remax property type cache entry"""
    id: UUID
    name: str
    remax_ids: str
    display_name: str
    verified_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True


class RemaxPropertyTypeListResponse(BaseModel):
    """List response for Remax property types"""
    total: int
    items: List[RemaxPropertyTypeResponse]


# ============ Bulk Import Schemas ============

class RemaxLocationBulkCreate(BaseModel):
    """Schema for bulk importing Remax locations"""
    locations: List[RemaxLocationCreate]


class RemaxPropertyTypeBulkCreate(BaseModel):
    """Schema for bulk importing Remax property types"""
    property_types: List[RemaxPropertyTypeCreate]


class BulkImportResponse(BaseModel):
    """Response for bulk import operations"""
    success: bool
    imported: int
    skipped: int
    errors: List[str] = []
