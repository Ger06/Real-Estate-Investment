"""
Remax Cache API endpoints
Admin endpoints for managing Remax location and property type ID cache
"""
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime

from app.database import get_db
from app.models.remax_cache import RemaxLocationCache, RemaxPropertyTypeCache
from app.schemas.remax_cache import (
    RemaxLocationCreate,
    RemaxLocationUpdate,
    RemaxLocationResponse,
    RemaxLocationListResponse,
    RemaxLocationBulkCreate,
    RemaxPropertyTypeCreate,
    RemaxPropertyTypeUpdate,
    RemaxPropertyTypeResponse,
    RemaxPropertyTypeListResponse,
    RemaxPropertyTypeBulkCreate,
    BulkImportResponse,
)


router = APIRouter()


# ============ Location Cache Endpoints ============

@router.get("/locations", response_model=RemaxLocationListResponse)
async def list_remax_locations(
    parent_location: Optional[str] = Query(None, description="Filter by parent location"),
    search: Optional[str] = Query(None, description="Search by name or display name"),
    db: AsyncSession = Depends(get_db),
):
    """
    List all cached Remax locations.

    These are verified location IDs that can be used for Remax searches.
    """
    stmt = select(RemaxLocationCache)

    if parent_location:
        stmt = stmt.where(RemaxLocationCache.parent_location == parent_location)

    if search:
        search_term = f"%{search.lower()}%"
        stmt = stmt.where(
            (RemaxLocationCache.name.ilike(search_term)) |
            (RemaxLocationCache.display_name.ilike(search_term))
        )

    stmt = stmt.order_by(RemaxLocationCache.parent_location, RemaxLocationCache.display_name)

    # Get total count
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_result = await db.execute(count_stmt)
    total = total_result.scalar() or 0

    # Get all results
    result = await db.execute(stmt)
    locations = result.scalars().all()

    return RemaxLocationListResponse(
        total=total,
        items=[RemaxLocationResponse.model_validate(loc) for loc in locations],
    )


@router.get("/locations/{location_id}", response_model=RemaxLocationResponse)
async def get_remax_location(
    location_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific Remax location by ID."""
    stmt = select(RemaxLocationCache).where(RemaxLocationCache.id == location_id)
    result = await db.execute(stmt)
    location = result.scalar_one_or_none()

    if not location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Localidad no encontrada en cache",
        )

    return RemaxLocationResponse.model_validate(location)


@router.post("/locations", response_model=RemaxLocationResponse, status_code=status.HTTP_201_CREATED)
async def create_remax_location(
    location_in: RemaxLocationCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Add a new Remax location to the cache.

    Use this to add locations after verifying their IDs on remax.com.ar.
    The name should be lowercase (e.g., "palermo", "villa devoto").
    """
    # Normalize name to lowercase
    normalized_name = location_in.name.lower().strip()

    # Check if already exists
    stmt = select(RemaxLocationCache).where(RemaxLocationCache.name == normalized_name)
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"La localidad '{normalized_name}' ya existe en el cache",
        )

    # Create new entry
    location = RemaxLocationCache(
        name=normalized_name,
        remax_id=location_in.remax_id,
        display_name=location_in.display_name,
        parent_location=location_in.parent_location,
        verified_at=datetime.utcnow(),
    )
    db.add(location)
    await db.commit()
    await db.refresh(location)

    return RemaxLocationResponse.model_validate(location)


@router.put("/locations/{location_id}", response_model=RemaxLocationResponse)
async def update_remax_location(
    location_id: UUID,
    location_in: RemaxLocationUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a Remax location in the cache."""
    stmt = select(RemaxLocationCache).where(RemaxLocationCache.id == location_id)
    result = await db.execute(stmt)
    location = result.scalar_one_or_none()

    if not location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Localidad no encontrada en cache",
        )

    # Update fields
    update_data = location_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(location, field, value)

    location.verified_at = datetime.utcnow()  # Update verification timestamp

    await db.commit()
    await db.refresh(location)

    return RemaxLocationResponse.model_validate(location)


@router.delete("/locations/{location_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_remax_location(
    location_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Delete a Remax location from the cache."""
    stmt = select(RemaxLocationCache).where(RemaxLocationCache.id == location_id)
    result = await db.execute(stmt)
    location = result.scalar_one_or_none()

    if not location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Localidad no encontrada en cache",
        )

    await db.delete(location)
    await db.commit()

    return None


@router.post("/locations/bulk", response_model=BulkImportResponse)
async def bulk_import_locations(
    data: RemaxLocationBulkCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Bulk import Remax locations.

    Skips locations that already exist (by name).
    """
    imported = 0
    skipped = 0
    errors = []

    for loc_data in data.locations:
        normalized_name = loc_data.name.lower().strip()

        # Check if exists
        stmt = select(RemaxLocationCache).where(RemaxLocationCache.name == normalized_name)
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            skipped += 1
            continue

        try:
            location = RemaxLocationCache(
                name=normalized_name,
                remax_id=loc_data.remax_id,
                display_name=loc_data.display_name,
                parent_location=loc_data.parent_location,
                verified_at=datetime.utcnow(),
            )
            db.add(location)
            imported += 1
        except Exception as e:
            errors.append(f"{normalized_name}: {str(e)}")

    await db.commit()

    return BulkImportResponse(
        success=len(errors) == 0,
        imported=imported,
        skipped=skipped,
        errors=errors,
    )


# ============ Property Type Cache Endpoints ============

@router.get("/property-types", response_model=RemaxPropertyTypeListResponse)
async def list_remax_property_types(
    db: AsyncSession = Depends(get_db),
):
    """
    List all cached Remax property types.

    These are verified property type IDs that can be used for Remax searches.
    """
    stmt = select(RemaxPropertyTypeCache).order_by(RemaxPropertyTypeCache.display_name)
    result = await db.execute(stmt)
    types = result.scalars().all()

    return RemaxPropertyTypeListResponse(
        total=len(types),
        items=[RemaxPropertyTypeResponse.model_validate(t) for t in types],
    )


@router.get("/property-types/{type_id}", response_model=RemaxPropertyTypeResponse)
async def get_remax_property_type(
    type_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific Remax property type by ID."""
    stmt = select(RemaxPropertyTypeCache).where(RemaxPropertyTypeCache.id == type_id)
    result = await db.execute(stmt)
    prop_type = result.scalar_one_or_none()

    if not prop_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tipo de propiedad no encontrado en cache",
        )

    return RemaxPropertyTypeResponse.model_validate(prop_type)


@router.post("/property-types", response_model=RemaxPropertyTypeResponse, status_code=status.HTTP_201_CREATED)
async def create_remax_property_type(
    type_in: RemaxPropertyTypeCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Add a new Remax property type to the cache.

    Use this to add property types after verifying their IDs on remax.com.ar.
    The name should be lowercase (e.g., "departamento", "ph").
    remax_ids can be comma-separated for types with multiple IDs (e.g., "1,2").
    """
    # Normalize name to lowercase
    normalized_name = type_in.name.lower().strip()

    # Check if already exists
    stmt = select(RemaxPropertyTypeCache).where(RemaxPropertyTypeCache.name == normalized_name)
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"El tipo de propiedad '{normalized_name}' ya existe en el cache",
        )

    # Create new entry
    prop_type = RemaxPropertyTypeCache(
        name=normalized_name,
        remax_ids=type_in.remax_ids,
        display_name=type_in.display_name,
        verified_at=datetime.utcnow(),
    )
    db.add(prop_type)
    await db.commit()
    await db.refresh(prop_type)

    return RemaxPropertyTypeResponse.model_validate(prop_type)


@router.put("/property-types/{type_id}", response_model=RemaxPropertyTypeResponse)
async def update_remax_property_type(
    type_id: UUID,
    type_in: RemaxPropertyTypeUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a Remax property type in the cache."""
    stmt = select(RemaxPropertyTypeCache).where(RemaxPropertyTypeCache.id == type_id)
    result = await db.execute(stmt)
    prop_type = result.scalar_one_or_none()

    if not prop_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tipo de propiedad no encontrado en cache",
        )

    # Update fields
    update_data = type_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(prop_type, field, value)

    prop_type.verified_at = datetime.utcnow()  # Update verification timestamp

    await db.commit()
    await db.refresh(prop_type)

    return RemaxPropertyTypeResponse.model_validate(prop_type)


@router.delete("/property-types/{type_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_remax_property_type(
    type_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Delete a Remax property type from the cache."""
    stmt = select(RemaxPropertyTypeCache).where(RemaxPropertyTypeCache.id == type_id)
    result = await db.execute(stmt)
    prop_type = result.scalar_one_or_none()

    if not prop_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tipo de propiedad no encontrado en cache",
        )

    await db.delete(prop_type)
    await db.commit()

    return None


@router.post("/property-types/bulk", response_model=BulkImportResponse)
async def bulk_import_property_types(
    data: RemaxPropertyTypeBulkCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Bulk import Remax property types.

    Skips property types that already exist (by name).
    """
    imported = 0
    skipped = 0
    errors = []

    for type_data in data.property_types:
        normalized_name = type_data.name.lower().strip()

        # Check if exists
        stmt = select(RemaxPropertyTypeCache).where(RemaxPropertyTypeCache.name == normalized_name)
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            skipped += 1
            continue

        try:
            prop_type = RemaxPropertyTypeCache(
                name=normalized_name,
                remax_ids=type_data.remax_ids,
                display_name=type_data.display_name,
                verified_at=datetime.utcnow(),
            )
            db.add(prop_type)
            imported += 1
        except Exception as e:
            errors.append(f"{normalized_name}: {str(e)}")

    await db.commit()

    return BulkImportResponse(
        success=len(errors) == 0,
        imported=imported,
        skipped=skipped,
        errors=errors,
    )
