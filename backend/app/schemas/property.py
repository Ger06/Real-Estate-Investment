"""
Property Schemas
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, HttpUrl, Field, field_validator
from uuid import UUID


# Scraping Schemas
class PropertyScrapeRequest(BaseModel):
    """Request to scrape a property URL"""
    url: str = Field(..., description="Property URL to scrape")
    save_to_db: bool = Field(True, description="Whether to save to database")

    @field_validator('url')
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate URL format"""
        if not v.startswith(('http://', 'https://')):
            raise ValueError('URL must start with http:// or https://')
        return v


class PropertyScrapeResponse(BaseModel):
    """Response after scraping a property"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    property_id: Optional[UUID] = None


# Property Create/Update Schemas
class PropertyImageCreate(BaseModel):
    """Schema for creating property images"""
    url: Optional[str] = None
    file_path: Optional[str] = None
    is_primary: bool = False
    order: int = 0


class PropertyCreate(BaseModel):
    """Schema for creating a property"""
    # Source
    source: str
    source_url: Optional[str] = None
    source_id: Optional[str] = None

    # Basic info
    property_type: str
    operation_type: str
    title: str
    description: Optional[str] = None

    # Pricing
    price: float
    currency: str = "USD"
    estimated_value: Optional[float] = None  # Valor estimado por el analista

    # Location
    address: Optional[str] = None
    street: Optional[str] = None  # Calle
    street_number: Optional[str] = None  # Altura
    neighborhood: Optional[str] = None
    city: str = "Buenos Aires"
    province: str = "Buenos Aires"
    postal_code: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    # Areas
    covered_area: Optional[float] = None
    semi_covered_area: Optional[float] = None
    uncovered_area: Optional[float] = None
    total_area: Optional[float] = None

    # Characteristics
    floor_level: Optional[int] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[int] = None
    parking_spaces: Optional[int] = None
    amenities: Optional[Dict[str, Any]] = None
    property_condition: Optional[str] = None  # nuevo, a_estrenar, buen_estado, etc

    # Contact
    real_estate_agency: Optional[str] = None
    contact_info: Optional[Dict[str, Any]] = None

    # Analysis
    observations: Optional[str] = None  # humedad, escalera, etc

    # Images
    images: Optional[List[PropertyImageCreate]] = None

    # Status
    status: str = "active"


class PropertyUpdate(BaseModel):
    """Schema for updating a property"""
    title: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    currency: Optional[str] = None
    estimated_value: Optional[float] = None
    street: Optional[str] = None
    street_number: Optional[str] = None
    property_condition: Optional[str] = None
    observations: Optional[str] = None
    status: Optional[str] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[int] = None
    parking_spaces: Optional[int] = None
    amenities: Optional[Dict[str, Any]] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


# Response Schemas
class PropertyImageResponse(BaseModel):
    """Property image response"""
    id: UUID
    url: Optional[str]
    file_path: Optional[str]
    is_primary: bool
    order: int
    created_at: datetime

    class Config:
        from_attributes = True


class PropertyResponse(BaseModel):
    """Property response schema"""
    id: UUID
    source: str
    source_url: Optional[str]
    source_id: Optional[str]

    property_type: str
    operation_type: str
    title: str
    description: Optional[str]

    price: float
    currency: str
    price_per_sqm: Optional[float]
    estimated_value: Optional[float]

    address: Optional[str]
    street: Optional[str]
    street_number: Optional[str]
    neighborhood: Optional[str]
    city: str
    province: str
    postal_code: Optional[str]

    covered_area: Optional[float]
    semi_covered_area: Optional[float]
    uncovered_area: Optional[float]
    total_area: Optional[float]

    floor_level: Optional[int]
    bedrooms: Optional[int]
    bathrooms: Optional[int]
    parking_spaces: Optional[int]
    amenities: Optional[Dict[str, Any]]
    property_condition: Optional[str]

    real_estate_agency: Optional[str]
    contact_info: Optional[Dict[str, Any]]

    observations: Optional[str]

    status: str
    scraped_at: Optional[datetime]
    created_at: datetime
    updated_at: Optional[datetime]

    images: List[PropertyImageResponse] = []

    class Config:
        from_attributes = True
        # Exclude PostGIS geography field from serialization
        exclude = {'location'}


class PropertyListResponse(BaseModel):
    """List of properties with pagination"""
    total: int
    skip: int
    limit: int
    items: List[PropertyResponse]


# Map Schemas
class PropertyMapItem(BaseModel):
    """Lightweight schema for map markers"""
    id: UUID
    title: str
    property_type: str
    operation_type: str
    price: float
    currency: str
    price_per_sqm: Optional[float] = None
    total_area: Optional[float] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[int] = None
    neighborhood: Optional[str] = None
    city: str
    address: Optional[str] = None
    status: str
    latitude: float
    longitude: float
    primary_image_url: Optional[str] = None
    observations: Optional[str] = None
    source_url: Optional[str] = None

    class Config:
        from_attributes = True


class PropertyMapResponse(BaseModel):
    """Map response with all geocoded properties"""
    total: int
    items: List[PropertyMapItem]
