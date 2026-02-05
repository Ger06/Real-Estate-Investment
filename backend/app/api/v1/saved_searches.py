"""
Saved Searches API endpoints
"""
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete

from app.database import get_db
from app.models.saved_search import SavedSearch
from app.models.pending_property import PendingProperty, PendingPropertyStatus
from app.schemas.saved_search import (
    SavedSearchCreate,
    SavedSearchUpdate,
    SavedSearchResponse,
    SavedSearchListResponse,
    SavedSearchExecuteResponse,
    ImportCardsRequest,
)
# from app.api.deps import get_current_user  # Temporarily disabled
# from app.models.user import User
from app.services.monitoring import MonitoringService


router = APIRouter()

# Temporary: no user filtering while auth is disabled
TEMP_USER_ID = None


@router.post("/", response_model=SavedSearchResponse, status_code=status.HTTP_201_CREATED)
async def create_saved_search(
    search_in: SavedSearchCreate,
    db: AsyncSession = Depends(get_db),
    # current_user: User = Depends(get_current_user),  # Temporarily disabled
):
    """
    Create a new saved search.

    Saved searches define the filters and portals to monitor for new properties.
    """
    # Create search
    search_data = search_in.model_dump()
    search_data['user_id'] = TEMP_USER_ID  # Temporarily hardcoded

    new_search = SavedSearch(**search_data)
    db.add(new_search)
    await db.commit()
    await db.refresh(new_search)

    # Add pending_count for response
    response = SavedSearchResponse.model_validate(new_search)
    response.pending_count = 0

    return response


@router.get("/", response_model=SavedSearchListResponse)
async def list_saved_searches(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    active_only: bool = Query(False, description="Only show active searches"),
    db: AsyncSession = Depends(get_db),
    # current_user: User = Depends(get_current_user),  # Temporarily disabled
):
    """
    List all saved searches for the current user.
    """
    # Build query (no user filter while auth is disabled)
    stmt = select(SavedSearch)

    if active_only:
        stmt = stmt.where(SavedSearch.is_active == True)

    # Get total count
    count_stmt = select(func.count()).select_from(
        stmt.subquery()
    )
    total_result = await db.execute(count_stmt)
    total = total_result.scalar() or 0

    # Get searches with pagination
    stmt = stmt.offset(skip).limit(limit).order_by(SavedSearch.created_at.desc())
    result = await db.execute(stmt)
    searches = result.scalars().all()

    # Get pending counts for each search
    items = []
    for search in searches:
        pending_count_stmt = select(func.count()).select_from(PendingProperty).where(
            PendingProperty.saved_search_id == search.id,
            PendingProperty.status == PendingPropertyStatus.PENDING
        )
        pending_result = await db.execute(pending_count_stmt)
        pending_count = pending_result.scalar() or 0

        response = SavedSearchResponse.model_validate(search)
        response.pending_count = pending_count
        items.append(response)

    return SavedSearchListResponse(
        total=total,
        skip=skip,
        limit=limit,
        items=items,
    )


@router.get("/{search_id}", response_model=SavedSearchResponse)
async def get_saved_search(
    search_id: UUID,
    db: AsyncSession = Depends(get_db),
    # current_user: User = Depends(get_current_user),  # Temporarily disabled
):
    """
    Get a saved search by ID.
    """
    stmt = select(SavedSearch).where(SavedSearch.id == search_id)
    result = await db.execute(stmt)
    search = result.scalar_one_or_none()

    if not search:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Búsqueda guardada no encontrada",
        )

    # Get pending count
    pending_count_stmt = select(func.count()).select_from(PendingProperty).where(
        PendingProperty.saved_search_id == search.id,
        PendingProperty.status == PendingPropertyStatus.PENDING
    )
    pending_result = await db.execute(pending_count_stmt)
    pending_count = pending_result.scalar() or 0

    response = SavedSearchResponse.model_validate(search)
    response.pending_count = pending_count

    return response


@router.put("/{search_id}", response_model=SavedSearchResponse)
async def update_saved_search(
    search_id: UUID,
    search_in: SavedSearchUpdate,
    db: AsyncSession = Depends(get_db),
    # current_user: User = Depends(get_current_user),  # Temporarily disabled
):
    """
    Update a saved search.
    """
    stmt = select(SavedSearch).where(SavedSearch.id == search_id)
    result = await db.execute(stmt)
    search = result.scalar_one_or_none()

    if not search:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Búsqueda guardada no encontrada",
        )

    # Update fields
    update_data = search_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(search, field, value)

    await db.commit()
    await db.refresh(search)

    # Get pending count
    pending_count_stmt = select(func.count()).select_from(PendingProperty).where(
        PendingProperty.saved_search_id == search.id,
        PendingProperty.status == PendingPropertyStatus.PENDING
    )
    pending_result = await db.execute(pending_count_stmt)
    pending_count = pending_result.scalar() or 0

    response = SavedSearchResponse.model_validate(search)
    response.pending_count = pending_count

    return response


@router.delete("/{search_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_saved_search(
    search_id: UUID,
    db: AsyncSession = Depends(get_db),
    # current_user: User = Depends(get_current_user),  # Temporarily disabled
):
    """
    Delete a saved search.

    This will also delete all associated pending properties (cascade).
    """
    stmt = select(SavedSearch).where(SavedSearch.id == search_id)
    result = await db.execute(stmt)
    search = result.scalar_one_or_none()

    if not search:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Búsqueda guardada no encontrada",
        )

    # Explicitly delete pending properties first to avoid async lazy-loading
    # issues with ORM cascade (MissingGreenlet in async context)
    await db.execute(
        delete(PendingProperty).where(PendingProperty.saved_search_id == search_id)
    )
    await db.delete(search)
    await db.commit()

    return None


@router.post("/{search_id}/execute", response_model=SavedSearchExecuteResponse)
async def execute_saved_search(
    search_id: UUID,
    max_properties: int = Query(100, ge=1, le=500, description="Max properties to discover per portal"),
    db: AsyncSession = Depends(get_db),
    # current_user: User = Depends(get_current_user),  # Temporarily disabled
):
    """
    Execute a saved search to discover new properties.

    This will:
    1. Scrape listing pages from configured portals
    2. Extract property URLs
    3. Check for duplicates
    4. Add new properties to pending queue (or auto-scrape if enabled)
    """
    stmt = select(SavedSearch).where(SavedSearch.id == search_id)
    result = await db.execute(stmt)
    search = result.scalar_one_or_none()

    if not search:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Búsqueda guardada no encontrada",
        )

    if not search.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La búsqueda está desactivada",
        )

    # Execute search
    service = MonitoringService(db)
    results = await service.execute_search(search, max_properties=max_properties)

    return SavedSearchExecuteResponse(
        success=results['success'],
        search_id=search.id,
        search_name=search.name,
        total_found=results['total_found'],
        new_properties=results['new_properties'],
        duplicates=results['duplicates'],
        scraped=results['scraped'],
        pending=results['pending'],
        errors=results['errors'],
    )


@router.post("/{search_id}/import-cards", response_model=SavedSearchExecuteResponse)
async def import_cards(
    search_id: UUID,
    body: ImportCardsRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Import pre-scraped property cards into a saved search.

    Designed for the local scraper workflow: scraping happens on a local machine
    (residential IP, bypasses Cloudflare) and results are uploaded to the API.

    Deduplication by source_url, same as execute_search.
    """
    stmt = select(SavedSearch).where(SavedSearch.id == search_id)
    result = await db.execute(stmt)
    search = result.scalar_one_or_none()

    if not search:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Búsqueda guardada no encontrada",
        )

    service = MonitoringService(db)

    results = {
        'total_found': len(body.cards),
        'new_properties': 0,
        'duplicates': 0,
        'scraped': 0,
        'pending': 0,
        'errors': [],
    }

    for card_data in body.cards:
        card = card_data.model_dump()
        try:
            async with db.begin_nested():
                is_new, card_status = await service._process_discovered_property(
                    card=card,
                    search=search,
                    portal=_detect_portal(card_data.source_url, search.portals),
                )

            if is_new:
                results['new_properties'] += 1
                if card_status == 'scraped':
                    results['scraped'] += 1
                else:
                    results['pending'] += 1
            else:
                results['duplicates'] += 1

        except Exception as e:
            # Savepoint rollback is automatic — outer transaction stays valid
            results['errors'].append({
                'url': card_data.source_url,
                'error': str(e),
            })

    # Update search execution stats
    from datetime import datetime
    search.last_executed_at = datetime.utcnow()
    search.total_executions = (search.total_executions or 0) + 1
    search.total_properties_found = (search.total_properties_found or 0) + results['new_properties']

    await db.commit()

    return SavedSearchExecuteResponse(
        success=len(results['errors']) == 0,
        search_id=search.id,
        search_name=search.name,
        total_found=results['total_found'],
        new_properties=results['new_properties'],
        duplicates=results['duplicates'],
        scraped=results['scraped'],
        pending=results['pending'],
        errors=results['errors'],
    )


def _detect_portal(source_url: str, portals: list) -> str:
    """Detect portal from source URL, falling back to first portal in search."""
    url_lower = source_url.lower()
    if "zonaprop" in url_lower:
        return "zonaprop"
    if "argenprop" in url_lower:
        return "argenprop"
    if "remax" in url_lower:
        return "remax"
    if "mercadolibre" in url_lower:
        return "mercadolibre"
    # Fallback to first portal in the saved search
    if portals:
        return portals[0].lower() if hasattr(portals[0], 'lower') else str(portals[0]).lower()
    return "manual"


@router.post("/{search_id}/toggle", response_model=SavedSearchResponse)
async def toggle_saved_search(
    search_id: UUID,
    db: AsyncSession = Depends(get_db),
    # current_user: User = Depends(get_current_user),  # Temporarily disabled
):
    """
    Toggle the active state of a saved search.
    """
    stmt = select(SavedSearch).where(SavedSearch.id == search_id)
    result = await db.execute(stmt)
    search = result.scalar_one_or_none()

    if not search:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Búsqueda guardada no encontrada",
        )

    search.is_active = not search.is_active
    await db.commit()
    await db.refresh(search)

    # Get pending count
    pending_count_stmt = select(func.count()).select_from(PendingProperty).where(
        PendingProperty.saved_search_id == search.id,
        PendingProperty.status == PendingPropertyStatus.PENDING
    )
    pending_result = await db.execute(pending_count_stmt)
    pending_count = pending_result.scalar() or 0

    response = SavedSearchResponse.model_validate(search)
    response.pending_count = pending_count

    return response
