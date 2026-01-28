"""
Pending Properties API endpoints
"""
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.database import get_db
from app.models.saved_search import SavedSearch
from app.models.pending_property import PendingProperty, PendingPropertyStatus
from app.schemas.pending_property import (
    PendingPropertyResponse,
    PendingPropertyWithSearchResponse,
    PendingPropertyListResponse,
    PendingPropertyStats,
    PendingPropertyScrapeRequest,
    PendingPropertyScrapeResponse,
    PendingPropertyActionResponse,
)
# from app.api.deps import get_current_user  # Temporarily disabled
# from app.models.user import User
from app.services.monitoring import MonitoringService


router = APIRouter()

# Temporary: no user filtering while auth is disabled
TEMP_USER_ID = None


@router.get("/", response_model=PendingPropertyListResponse)
async def list_pending_properties(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    search_id: Optional[UUID] = Query(None, description="Filter by saved search"),
    status_filter: Optional[str] = Query(None, description="Filter by status (pending, scraped, skipped, error)"),
    portal: Optional[str] = Query(None, description="Filter by portal"),
    db: AsyncSession = Depends(get_db),
    # current_user: User = Depends(get_current_user),  # Temporarily disabled
):
    """
    List pending properties for the current user.

    Pending properties are URLs discovered by saved searches that haven't been fully scraped yet.
    """
    # Build query (no user filter while auth is disabled)
    stmt = select(PendingProperty, SavedSearch.name.label('search_name')).join(
        SavedSearch, PendingProperty.saved_search_id == SavedSearch.id
    )

    # Apply filters
    if search_id:
        stmt = stmt.where(PendingProperty.saved_search_id == search_id)

    if status_filter:
        try:
            status_enum = PendingPropertyStatus(status_filter.upper())
            stmt = stmt.where(PendingProperty.status == status_enum)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Estado inválido: {status_filter}. Valores válidos: pending, scraped, skipped, error",
            )

    if portal:
        stmt = stmt.where(PendingProperty.source == portal.lower())

    # Get total count
    count_subquery = stmt.subquery()
    count_stmt = select(func.count()).select_from(count_subquery)
    total_result = await db.execute(count_stmt)
    total = total_result.scalar() or 0

    # Get items with pagination
    stmt = stmt.offset(skip).limit(limit).order_by(PendingProperty.discovered_at.desc())
    result = await db.execute(stmt)
    rows = result.fetchall()

    items = []
    for row in rows:
        pending = row[0]
        search_name = row[1]

        item = PendingPropertyWithSearchResponse(
            id=pending.id,
            saved_search_id=pending.saved_search_id,
            source_url=pending.source_url,
            source=pending.source.value,
            source_id=pending.source_id,
            title=pending.title,
            price=float(pending.price) if pending.price else None,
            currency=pending.currency.value if pending.currency else None,
            thumbnail_url=pending.thumbnail_url,
            location_preview=pending.location_preview,
            status=pending.status.value,
            error_message=pending.error_message,
            property_id=pending.property_id,
            discovered_at=pending.discovered_at,
            scraped_at=pending.scraped_at,
            updated_at=pending.updated_at,
            saved_search_name=search_name,
        )
        items.append(item)

    return PendingPropertyListResponse(
        total=total,
        skip=skip,
        limit=limit,
        items=items,
    )


@router.get("/stats", response_model=PendingPropertyStats)
async def get_pending_stats(
    db: AsyncSession = Depends(get_db),
    # current_user: User = Depends(get_current_user),  # Temporarily disabled
):
    """
    Get statistics about pending properties.
    """
    # Get all stats (no user filter while auth is disabled)
    total_pending = await db.execute(
        select(func.count()).select_from(PendingProperty).where(
            PendingProperty.status == PendingPropertyStatus.PENDING
        )
    )
    total_scraped = await db.execute(
        select(func.count()).select_from(PendingProperty).where(
            PendingProperty.status == PendingPropertyStatus.SCRAPED
        )
    )
    total_skipped = await db.execute(
        select(func.count()).select_from(PendingProperty).where(
            PendingProperty.status == PendingPropertyStatus.SKIPPED
        )
    )
    total_errors = await db.execute(
        select(func.count()).select_from(PendingProperty).where(
            PendingProperty.status == PendingPropertyStatus.ERROR
        )
    )

    return PendingPropertyStats(
        total_pending=total_pending.scalar() or 0,
        total_scraped=total_scraped.scalar() or 0,
        total_skipped=total_skipped.scalar() or 0,
        total_errors=total_errors.scalar() or 0,
        by_search=[],
        by_portal=[],
    )


@router.get("/{pending_id}", response_model=PendingPropertyWithSearchResponse)
async def get_pending_property(
    pending_id: UUID,
    db: AsyncSession = Depends(get_db),
    # current_user: User = Depends(get_current_user),  # Temporarily disabled
):
    """
    Get a single pending property by ID.
    """
    stmt = select(PendingProperty, SavedSearch.name.label('search_name')).join(
        SavedSearch, PendingProperty.saved_search_id == SavedSearch.id
    ).where(PendingProperty.id == pending_id)
    result = await db.execute(stmt)
    row = result.fetchone()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Propiedad pendiente no encontrada",
        )

    pending = row[0]
    search_name = row[1]

    return PendingPropertyWithSearchResponse(
        id=pending.id,
        saved_search_id=pending.saved_search_id,
        source_url=pending.source_url,
        source=pending.source.value,
        source_id=pending.source_id,
        title=pending.title,
        price=float(pending.price) if pending.price else None,
        currency=pending.currency.value if pending.currency else None,
        thumbnail_url=pending.thumbnail_url,
        location_preview=pending.location_preview,
        status=pending.status.value,
        error_message=pending.error_message,
        property_id=pending.property_id,
        discovered_at=pending.discovered_at,
        scraped_at=pending.scraped_at,
        updated_at=pending.updated_at,
        saved_search_name=search_name,
    )


@router.post("/scrape", response_model=PendingPropertyScrapeResponse)
async def scrape_pending_properties(
    request: PendingPropertyScrapeRequest,
    db: AsyncSession = Depends(get_db),
    # current_user: User = Depends(get_current_user),  # Temporarily disabled
):
    """
    Scrape a batch of pending properties.

    This will take pending URLs and scrape the full property data.
    """
    # Validate search_id exists if provided
    if request.search_id:
        search_stmt = select(SavedSearch).where(SavedSearch.id == request.search_id)
        search_result = await db.execute(search_stmt)
        if not search_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Búsqueda guardada no encontrada",
            )

    service = MonitoringService(db)
    results = await service.scrape_pending_properties(
        search_id=request.search_id,
        limit=request.limit,
    )

    return PendingPropertyScrapeResponse(
        success=results['success'],
        scraped=results['scraped'],
        errors=results['errors'],
        error_details=results['error_details'],
    )


@router.post("/{pending_id}/scrape", response_model=PendingPropertyActionResponse)
async def scrape_single_pending(
    pending_id: UUID,
    db: AsyncSession = Depends(get_db),
    # current_user: User = Depends(get_current_user),  # Temporarily disabled
):
    """
    Scrape a single pending property.
    """
    # Check pending property exists
    stmt = select(PendingProperty).where(PendingProperty.id == pending_id)
    result = await db.execute(stmt)
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Propiedad pendiente no encontrada",
        )

    service = MonitoringService(db)
    result = await service.scrape_single_pending(pending_id)

    return PendingPropertyActionResponse(
        success=result['success'],
        message=result['message'],
        pending_id=pending_id,
        property_id=result.get('property_id'),
    )


@router.post("/{pending_id}/skip", response_model=PendingPropertyActionResponse)
async def skip_pending_property(
    pending_id: UUID,
    db: AsyncSession = Depends(get_db),
    # current_user: User = Depends(get_current_user),  # Temporarily disabled
):
    """
    Mark a pending property as skipped.

    Use this when you don't want to scrape a discovered property.
    """
    # Check pending property exists
    stmt = select(PendingProperty).where(PendingProperty.id == pending_id)
    result = await db.execute(stmt)
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Propiedad pendiente no encontrada",
        )

    service = MonitoringService(db)
    result = await service.skip_pending(pending_id)

    return PendingPropertyActionResponse(
        success=result['success'],
        message=result['message'],
        pending_id=pending_id,
    )


@router.delete("/{pending_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_pending_property(
    pending_id: UUID,
    db: AsyncSession = Depends(get_db),
    # current_user: User = Depends(get_current_user),  # Temporarily disabled
):
    """
    Delete a pending property.
    """
    stmt = select(PendingProperty).where(PendingProperty.id == pending_id)
    result = await db.execute(stmt)
    pending = result.scalar_one_or_none()

    if not pending:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Propiedad pendiente no encontrada",
        )

    await db.delete(pending)
    await db.commit()

    return None


@router.post("/clear-errors", response_model=dict)
async def clear_error_pending(
    search_id: Optional[UUID] = Query(None, description="Filter by saved search"),
    db: AsyncSession = Depends(get_db),
    # current_user: User = Depends(get_current_user),  # Temporarily disabled
):
    """
    Reset all error pending properties back to pending status.

    Useful for retrying failed scrapes.
    """
    # Build query
    stmt = select(PendingProperty).where(
        PendingProperty.status == PendingPropertyStatus.ERROR
    )

    if search_id:
        stmt = stmt.where(PendingProperty.saved_search_id == search_id)

    result = await db.execute(stmt)
    error_pending = result.scalars().all()

    count = 0
    for pending in error_pending:
        pending.status = PendingPropertyStatus.PENDING
        pending.error_message = None
        count += 1

    await db.commit()

    return {'cleared': count, 'message': f'{count} propiedades reseteadas a estado pendiente'}
