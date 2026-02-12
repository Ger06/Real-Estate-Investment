"""
Properties API endpoints
"""
import asyncio
import logging
import time
from typing import List, Optional
from datetime import datetime
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from geoalchemy2.shape import from_shape, to_shape
from shapely.geometry import Point

from app.database import get_db
from app.models.property import Property, PropertyImage, PropertySource, PriceHistory, PropertyStatus
from app.models.pending_property import PendingProperty
from app.schemas.property import (
    PropertyScrapeRequest,
    PropertyScrapeResponse,
    PropertyCreate,
    PropertyUpdate,
    PropertyResponse,
    PropertyListResponse,
    PropertyMapItem,
    PropertyMapResponse,
)
from app.scrapers import ArgenpropScraper, ZonapropScraper, RemaxScraper, MercadoLibreScraper
from app.services.geocoding import geocoding_service
from app.services.address import normalize_address_fields
from app.api.deps import get_current_user
from app.models.user import User


router = APIRouter()

logger = logging.getLogger(__name__)


def _try_geocode(property_obj: Property) -> bool:
    """Try to geocode a property if it has no location. Returns True if geocoded."""
    if property_obj.location is not None:
        return False
    try:
        coords = geocoding_service.geocode_address(
            address=property_obj.address,
            street=property_obj.street,
            street_number=property_obj.street_number,
            neighborhood=property_obj.neighborhood,
            city=property_obj.city,
            province=property_obj.province,
        )
        if coords:
            lat, lng = coords
            property_obj.location = geocoding_service.make_point(lat, lng)
            logger.info(f"Auto-geocoded property '{property_obj.title[:50]}' -> ({lat}, {lng})")
            return True
    except Exception as e:
        logger.warning(f"Auto-geocode failed for '{property_obj.title[:50]}': {e}")
    return False


def _apply_property_filters(
    stmt,
    property_type: Optional[str] = None,
    operation_type: Optional[str] = None,
    status_filter: Optional[str] = None,
    currency: Optional[str] = None,
    price_min: Optional[float] = None,
    price_max: Optional[float] = None,
    area_min: Optional[float] = None,
    area_max: Optional[float] = None,
    bedrooms_min: Optional[int] = None,
    bathrooms_min: Optional[int] = None,
    neighborhood: Optional[str] = None,
    city: Optional[str] = None,
    has_location: Optional[bool] = None,
):
    """Apply common property filters to a query statement"""
    if property_type:
        stmt = stmt.where(Property.property_type == property_type)
    if operation_type:
        stmt = stmt.where(Property.operation_type == operation_type)
    if status_filter:
        stmt = stmt.where(Property.status == status_filter)
    if currency:
        stmt = stmt.where(Property.currency == currency)
    if price_min is not None:
        stmt = stmt.where(Property.price >= price_min)
    if price_max is not None:
        stmt = stmt.where(Property.price <= price_max)
    if area_min is not None:
        stmt = stmt.where(Property.total_area >= area_min)
    if area_max is not None:
        stmt = stmt.where(Property.total_area <= area_max)
    if bedrooms_min is not None:
        stmt = stmt.where(Property.bedrooms >= bedrooms_min)
    if bathrooms_min is not None:
        stmt = stmt.where(Property.bathrooms >= bathrooms_min)
    if neighborhood:
        stmt = stmt.where(Property.neighborhood.ilike(f"%{neighborhood}%"))
    if city:
        stmt = stmt.where(Property.city.ilike(f"%{city}%"))
    if has_location is True:
        stmt = stmt.where(Property.location.isnot(None))
    elif has_location is False:
        stmt = stmt.where(Property.location.is_(None))
    return stmt


@router.post("/scrape", response_model=PropertyScrapeResponse)
async def scrape_property(
    request: PropertyScrapeRequest,
    db: AsyncSession = Depends(get_db),
    # current_user: User = Depends(get_current_user),  # Temporarily disabled
):
    """
    Scrape property data from URL

    Supports:
    - Argenprop ✓
    - Zonaprop ✓
    - Remax ✓
    - MercadoLibre ✓
    """
    try:
        # Determine which scraper to use based on URL
        scraper = None

        if "argenprop.com" in request.url:
            scraper = ArgenpropScraper(request.url)
        elif "zonaprop.com" in request.url:
            scraper = ZonapropScraper(request.url)
        elif "remax.com" in request.url:
            scraper = RemaxScraper(request.url)
        elif "mercadolibre.com" in request.url:
            scraper = MercadoLibreScraper(request.url)
        else:
            return PropertyScrapeResponse(
                success=False,
                message="Portal no soportado. Portales disponibles: Argenprop, Zonaprop, Remax, MercadoLibre",
                data=None,
            )

        # Scrape the property
        scraped_data = await scraper.scrape()

        # Save to database if requested
        property_id = None
        if request.save_to_db:
            # Check if property already exists
            stmt = select(Property).where(Property.source_url == request.url)
            result = await db.execute(stmt)
            existing_property = result.scalar_one_or_none()

            if existing_property:
                return PropertyScrapeResponse(
                    success=False,
                    message="Esta propiedad ya existe en la base de datos",
                    data=scraped_data,
                    property_id=existing_property.id,
                )

            # Create property from scraped data
            property_data = _scraped_to_property(scraped_data, None)  # TODO: Add user_id when auth is enabled
            new_property = Property(**property_data)

            # Add images if any
            if scraped_data.get('images'):
                for idx, img_url in enumerate(scraped_data['images'][:20]):  # Max 20 images
                    image = PropertyImage(
                        url=img_url,
                        is_primary=(idx == 0),
                        order=idx,
                    )
                    new_property.images.append(image)

            # Save to database
            db.add(new_property)
            await db.commit()
            await db.refresh(new_property)

            property_id = new_property.id

        return PropertyScrapeResponse(
            success=True,
            message="Propiedad scrapeada exitosamente",
            data=scraped_data,
            property_id=property_id,
        )

    except Exception as e:
        return PropertyScrapeResponse(
            success=False,
            message=f"Error al scrapear: {str(e)}",
            data=None,
        )


@router.get("/", response_model=PropertyListResponse)
async def list_properties(
    skip: int = 0,
    limit: int = 50,
    property_type: Optional[str] = Query(None),
    operation_type: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    currency: Optional[str] = Query(None),
    price_min: Optional[float] = Query(None),
    price_max: Optional[float] = Query(None),
    area_min: Optional[float] = Query(None),
    area_max: Optional[float] = Query(None),
    bedrooms_min: Optional[int] = Query(None),
    bathrooms_min: Optional[int] = Query(None),
    neighborhood: Optional[str] = Query(None),
    city: Optional[str] = Query(None),
    has_location: Optional[bool] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """
    List all properties with pagination and filters
    """
    # Get total count with filters
    count_stmt = select(func.count()).select_from(Property)
    count_stmt = _apply_property_filters(
        count_stmt, property_type, operation_type, status_filter, currency,
        price_min, price_max, area_min, area_max, bedrooms_min, bathrooms_min,
        neighborhood, city, has_location,
    )
    total_result = await db.execute(count_stmt)
    total = total_result.scalar()

    # Get properties with filters
    stmt = select(Property).order_by(Property.created_at.desc())
    stmt = _apply_property_filters(
        stmt, property_type, operation_type, status_filter, currency,
        price_min, price_max, area_min, area_max, bedrooms_min, bathrooms_min,
        neighborhood, city, has_location,
    )
    stmt = stmt.offset(skip).limit(limit)
    result = await db.execute(stmt)
    properties = result.scalars().all()

    return PropertyListResponse(
        total=total or 0,
        skip=skip,
        limit=limit,
        items=properties,
    )


@router.get("/map", response_model=PropertyMapResponse)
async def list_properties_for_map(
    property_type: Optional[str] = Query(None),
    operation_type: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    currency: Optional[str] = Query(None),
    price_min: Optional[float] = Query(None),
    price_max: Optional[float] = Query(None),
    area_min: Optional[float] = Query(None),
    area_max: Optional[float] = Query(None),
    bedrooms_min: Optional[int] = Query(None),
    bathrooms_min: Optional[int] = Query(None),
    neighborhood: Optional[str] = Query(None),
    city: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all geocoded properties for map display (no pagination).
    Returns lightweight items with lat/lng coordinates.
    """
    stmt = select(Property).where(Property.location.isnot(None))
    stmt = _apply_property_filters(
        stmt, property_type, operation_type, status_filter, currency,
        price_min, price_max, area_min, area_max, bedrooms_min, bathrooms_min,
        neighborhood, city, has_location=True,
    )
    stmt = stmt.order_by(Property.created_at.desc())
    result = await db.execute(stmt)
    properties = result.scalars().all()

    items = []
    for prop in properties:
        try:
            point = to_shape(prop.location)
            primary_image = next(
                (img.url for img in prop.images if img.is_primary),
                prop.images[0].url if prop.images else None,
            )
            items.append(PropertyMapItem(
                id=prop.id,
                title=prop.title,
                property_type=prop.property_type.value if hasattr(prop.property_type, 'value') else prop.property_type,
                operation_type=prop.operation_type.value if hasattr(prop.operation_type, 'value') else prop.operation_type,
                price=float(prop.price),
                currency=prop.currency.value if hasattr(prop.currency, 'value') else prop.currency,
                price_per_sqm=float(prop.price_per_sqm) if prop.price_per_sqm else None,
                total_area=float(prop.total_area) if prop.total_area else None,
                bedrooms=prop.bedrooms,
                bathrooms=prop.bathrooms,
                neighborhood=prop.neighborhood,
                city=prop.city,
                address=prop.address,
                status=prop.status.value if hasattr(prop.status, 'value') else prop.status,
                latitude=point.y,
                longitude=point.x,
                primary_image_url=primary_image,
                observations=prop.observations,
                source_url=prop.source_url,
            ))
        except Exception:
            continue

    return PropertyMapResponse(total=len(items), items=items)


def _geocode_properties_sync(properties: list, force: bool) -> dict:
    """Run geocoding in a worker thread to avoid blocking the event loop."""
    total = len(properties)
    success = 0
    failed = 0
    failed_details = []
    geocoding_service.clear_cache()

    if force:
        for prop in properties:
            prop.location = None

    for prop in properties:
        try:
            coords = geocoding_service.geocode_address(
                address=prop.address,
                street=prop.street,
                street_number=prop.street_number,
                neighborhood=prop.neighborhood,
                city=prop.city,
                province=prop.province,
            )
            if coords:
                lat, lng = coords
                prop.location = geocoding_service.make_point(lat, lng)
                success += 1
            else:
                failed += 1
                failed_details.append({
                    "id": str(prop.id),
                    "title": prop.title[:60],
                    "address": prop.address,
                    "neighborhood": prop.neighborhood,
                })
        except Exception as e:
            failed += 1
            failed_details.append({
                "id": str(prop.id),
                "title": prop.title[:60],
                "error": str(e),
            })

        time.sleep(1.0)  # inter-property delay (LocationIQ allows 2 req/sec)

    geocoding_service.clear_cache()

    return {
        "success": True,
        "message": f"Geocoding completado: {success}/{total} exitosos, {failed} fallidos",
        "total": total,
        "geocoded": success,
        "failed": failed,
        "failed_details": failed_details[:20],
    }


@router.post("/geocode-all")
async def geocode_all_properties(
    force: bool = Query(False, description="Re-geocode ALL properties, not just missing ones"),
    search_id: Optional[UUID] = Query(None, description="Geocode only properties from this saved search"),
    db: AsyncSession = Depends(get_db),
):
    """
    Geocode properties without coordinates.
    With force=true, clears all coordinates and re-geocodes everything.
    With search_id, only geocodes properties linked to that saved search.
    Uses LocationIQ (free tier, 5000 req/day) with rate limiting.
    Runs in a worker thread to avoid blocking the event loop.
    """
    if search_id:
        stmt = select(Property).join(
            PendingProperty, PendingProperty.property_id == Property.id
        ).where(PendingProperty.saved_search_id == search_id)
        if not force:
            stmt = stmt.where(Property.location.is_(None))
    elif force:
        stmt = select(Property)
    else:
        stmt = select(Property).where(Property.location.is_(None))

    result = await db.execute(stmt)
    properties = result.scalars().all()

    geocode_result = await asyncio.to_thread(_geocode_properties_sync, properties, force)

    await db.commit()

    return geocode_result


@router.post("/normalize-addresses")
async def normalize_all_addresses(
    regeocode: bool = Query(False, description="Clear coordinates so properties get re-geocoded next run"),
    db: AsyncSession = Depends(get_db),
):
    """
    Normalize address fields for all properties in the database.
    Parses street/street_number from raw address, detects neighborhoods,
    and normalizes city names.

    With regeocode=true, also clears existing coordinates so that
    a subsequent geocode-all?force=true will re-geocode with clean data.
    """
    stmt = select(Property)
    result = await db.execute(stmt)
    properties = result.scalars().all()

    total = len(properties)
    changed = 0
    street_filled = 0
    neighborhood_filled = 0

    for prop in properties:
        normalized = normalize_address_fields(
            address=prop.address,
            street=prop.street,
            street_number=prop.street_number,
            neighborhood=prop.neighborhood,
            city=prop.city,
            province=prop.province,
        )

        modified = False

        # Update address if cleaned version differs
        if normalized['address'] and normalized['address'] != prop.address:
            prop.address = normalized['address']
            modified = True

        # Fill street if it was NULL and normalizer parsed it
        if not prop.street and normalized['street']:
            prop.street = normalized['street']
            street_filled += 1
            modified = True

        # Fill street_number if it was NULL and normalizer parsed it
        if not prop.street_number and normalized['street_number']:
            prop.street_number = normalized['street_number']
            modified = True

        # Fill neighborhood if it was NULL and normalizer detected it
        if not prop.neighborhood and normalized['neighborhood']:
            prop.neighborhood = normalized['neighborhood']
            neighborhood_filled += 1
            modified = True

        # Normalize city/province
        if normalized['city'] and normalized['city'] != prop.city:
            prop.city = normalized['city']
            modified = True
        if normalized['province'] and normalized['province'] != prop.province:
            prop.province = normalized['province']
            modified = True

        if modified:
            changed += 1

        # Optionally clear coordinates for re-geocoding
        if regeocode and modified and prop.location is not None:
            prop.location = None

    await db.commit()

    return {
        "success": True,
        "message": f"Normalización completada: {changed}/{total} propiedades modificadas",
        "total": total,
        "changed": changed,
        "street_filled": street_filled,
        "neighborhood_filled": neighborhood_filled,
        "regeocode": regeocode,
    }


@router.post("/", response_model=PropertyResponse, status_code=status.HTTP_201_CREATED)
async def create_property(
    property_in: PropertyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new property manually
    """
    # Create property
    property_data = property_in.model_dump(exclude={'images'})
    property_data['created_by'] = current_user.id
    property_data['scraped_at'] = datetime.utcnow() if property_in.source != 'manual' else None

    # Normalize address fields
    normalized = normalize_address_fields(
        address=property_data.get('address'),
        street=property_data.get('street'),
        street_number=property_data.get('street_number'),
        neighborhood=property_data.get('neighborhood'),
        city=property_data.get('city'),
        province=property_data.get('province'),
    )
    property_data.update(normalized)

    # Handle location coordinates
    if property_in.latitude and property_in.longitude:
        point = Point(property_in.longitude, property_in.latitude)
        property_data['location'] = from_shape(point, srid=4326)

    # Calculate price per sqm
    if property_in.price and property_in.total_area:
        property_data['price_per_sqm'] = property_in.price / property_in.total_area

    new_property = Property(**property_data)

    # Add images if any
    if property_in.images:
        for img_data in property_in.images:
            image = PropertyImage(**img_data.model_dump())
            new_property.images.append(image)

    db.add(new_property)
    await db.commit()
    await db.refresh(new_property)

    return new_property


@router.get("/{property_id}", response_model=PropertyResponse)
async def get_property(
    property_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Get property by ID
    """
    stmt = select(Property).where(Property.id == property_id)
    result = await db.execute(stmt)
    property_obj = result.scalar_one_or_none()

    if not property_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Propiedad no encontrada",
        )

    return property_obj


@router.put("/{property_id}", response_model=PropertyResponse)
async def update_property(
    property_id: UUID,
    property_in: PropertyUpdate,
    db: AsyncSession = Depends(get_db),
    # current_user: User = Depends(get_current_user),
):
    """
    Update property
    """
    stmt = select(Property).where(Property.id == property_id)
    result = await db.execute(stmt)
    property_obj = result.scalar_one_or_none()

    if not property_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Propiedad no encontrada",
        )

    # Update fields
    update_data = property_in.model_dump(exclude_unset=True)

    # Handle lat/lng -> PostGIS Point conversion
    lat = update_data.pop("latitude", None)
    lng = update_data.pop("longitude", None)
    if lat is not None and lng is not None:
        property_obj.location = from_shape(Point(lng, lat), srid=4326)

    for field, value in update_data.items():
        setattr(property_obj, field, value)

    # Recalculate price per sqm if price or area changed
    if property_obj.price and property_obj.total_area:
        property_obj.price_per_sqm = float(property_obj.price) / float(property_obj.total_area)

    await db.commit()
    await db.refresh(property_obj)

    return property_obj


@router.delete("/{property_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_property(
    property_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete property
    """
    stmt = select(Property).where(Property.id == property_id)
    result = await db.execute(stmt)
    property_obj = result.scalar_one_or_none()

    if not property_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Propiedad no encontrada",
        )

    await db.delete(property_obj)
    await db.commit()

    return None


@router.post("/update-prices")
async def update_all_prices(
    db: AsyncSession = Depends(get_db),
):
    """
    Update prices for all properties from their source URLs.
    Creates price history entries when prices change.
    """
    try:
        # Get all properties with source URLs
        stmt = select(Property).where(Property.source_url.isnot(None))
        result = await db.execute(stmt)
        properties = result.scalars().all()

        updated_count = 0
        error_count = 0
        price_changes = []

        for property_obj in properties:
            try:
                # Determine scraper based on source URL
                scraper = None
                if "argenprop.com" in property_obj.source_url:
                    scraper = ArgenpropScraper(property_obj.source_url)
                elif "zonaprop.com" in property_obj.source_url:
                    scraper = ZonapropScraper(property_obj.source_url)
                elif "remax.com" in property_obj.source_url:
                    scraper = RemaxScraper(property_obj.source_url)
                elif "mercadolibre.com" in property_obj.source_url:
                    scraper = MercadoLibreScraper(property_obj.source_url)
                else:
                    continue

                # Scrape only to get current price and status
                scraped_data = await scraper.scrape()
                new_price = scraped_data.get('price')
                new_currency = scraped_data.get('currency', 'USD')
                new_status = scraped_data.get('status', 'active')

                if not new_price:
                    error_count += 1
                    continue

                # Update status (always, even if price didn't change)
                property_obj.status = _parse_status(new_status)

                # Check if price changed
                old_price = float(property_obj.price)
                if abs(new_price - old_price) > 0.01:  # Significant change
                    # Calculate change percentage
                    change_percentage = ((new_price - old_price) / old_price) * 100

                    # Create price history entry
                    price_history = PriceHistory(
                        property_id=property_obj.id,
                        price=new_price,
                        currency=new_currency,
                        change_percentage=change_percentage,
                        recorded_at=datetime.utcnow(),
                    )
                    db.add(price_history)

                    # Update property price
                    property_obj.price = new_price
                    property_obj.currency = new_currency
                    property_obj.scraped_at = datetime.utcnow()

                    # Recalculate price per sqm
                    if property_obj.total_area:
                        property_obj.price_per_sqm = new_price / float(property_obj.total_area)

                    updated_count += 1
                    price_changes.append({
                        'property_id': str(property_obj.id),
                        'title': property_obj.title,
                        'old_price': old_price,
                        'new_price': new_price,
                        'change_percentage': round(change_percentage, 2),
                    })

            except Exception as e:
                error_count += 1
                print(f"Error updating property {property_obj.id}: {str(e)}")
                continue

        await db.commit()

        return {
            'success': True,
            'message': f'Actualización completada: {updated_count} precios actualizados, {error_count} errores',
            'total_properties': len(properties),
            'updated_count': updated_count,
            'error_count': error_count,
            'price_changes': price_changes,
        }

    except Exception as e:
        return {
            'success': False,
            'message': f'Error al actualizar precios: {str(e)}',
        }


@router.post("/rescrape-all")
async def rescrape_all_properties(
    db: AsyncSession = Depends(get_db),
):
    """
    Re-scrape all properties from their source URLs.
    Updates all property data while preserving manually edited fields.
    """
    try:
        # Get all properties with source URLs
        stmt = select(Property).where(Property.source_url.isnot(None))
        result = await db.execute(stmt)
        properties = result.scalars().all()

        updated_count = 0
        error_count = 0
        errors = []

        for property_obj in properties:
            try:
                # Determine scraper based on source URL
                scraper = None
                if "argenprop.com" in property_obj.source_url:
                    scraper = ArgenpropScraper(property_obj.source_url)
                elif "zonaprop.com" in property_obj.source_url:
                    scraper = ZonapropScraper(property_obj.source_url)
                elif "remax.com" in property_obj.source_url:
                    scraper = RemaxScraper(property_obj.source_url)
                elif "mercadolibre.com" in property_obj.source_url:
                    scraper = MercadoLibreScraper(property_obj.source_url)
                else:
                    continue

                # Full scrape
                scraped_data = await scraper.scrape()

                if not scraped_data:
                    error_count += 1
                    continue

                # Store manually edited fields (to preserve them)
                preserved_fields = {
                    'estimated_value': property_obj.estimated_value,
                    'observations': property_obj.observations,
                    'property_condition': property_obj.property_condition,
                    'street': property_obj.street,
                    'street_number': property_obj.street_number,
                }

                # Update property with scraped data
                old_price = float(property_obj.price)
                location_data = scraped_data.get('location', {})
                features = scraped_data.get('features', {})
                contact = scraped_data.get('contact', {})

                # Update basic fields
                property_obj.title = scraped_data.get('title', property_obj.title)
                property_obj.description = scraped_data.get('description', property_obj.description)
                property_obj.property_type = scraped_data.get('property_type', property_obj.property_type)
                property_obj.operation_type = scraped_data.get('operation_type', property_obj.operation_type)
                # Update status (convert to proper enum value)
                if scraped_data.get('status'):
                    property_obj.status = _parse_status(scraped_data.get('status'))

                # Update pricing
                new_price = scraped_data.get('price')
                if new_price and abs(new_price - old_price) > 0.01:
                    # Price changed, create history entry
                    change_percentage = ((new_price - old_price) / old_price) * 100
                    price_history = PriceHistory(
                        property_id=property_obj.id,
                        price=new_price,
                        currency=scraped_data.get('currency', 'USD'),
                        change_percentage=change_percentage,
                        recorded_at=datetime.utcnow(),
                    )
                    db.add(price_history)

                property_obj.price = new_price or property_obj.price
                property_obj.currency = scraped_data.get('currency', property_obj.currency)

                # Update location — normalize address fields
                raw_address = scraped_data.get('address', property_obj.address)
                normalized = normalize_address_fields(
                    address=raw_address,
                    street=scraped_data.get('street'),
                    street_number=scraped_data.get('street_number'),
                    neighborhood=location_data.get('neighborhood', property_obj.neighborhood),
                    city=location_data.get('city', property_obj.city),
                    province=location_data.get('province', property_obj.province),
                )
                property_obj.address = normalized['address']
                # Only update street/street_number if they're empty (preserve manual edits)
                if not property_obj.street and normalized['street']:
                    property_obj.street = normalized['street']
                if not property_obj.street_number and normalized['street_number']:
                    property_obj.street_number = normalized['street_number']
                property_obj.neighborhood = normalized['neighborhood'] or property_obj.neighborhood
                property_obj.city = normalized['city'] or property_obj.city
                property_obj.province = normalized['province'] or property_obj.province

                # Update features
                property_obj.covered_area = features.get('covered_area', property_obj.covered_area)
                property_obj.total_area = features.get('total_area', property_obj.total_area)
                property_obj.bedrooms = features.get('bedrooms', property_obj.bedrooms)
                property_obj.bathrooms = features.get('bathrooms', property_obj.bathrooms)
                property_obj.parking_spaces = features.get('parking_spaces', property_obj.parking_spaces)

                if features.get('amenities'):
                    property_obj.amenities = {'list': features.get('amenities', [])}

                # Update contact
                property_obj.real_estate_agency = contact.get('real_estate_agency', property_obj.real_estate_agency)
                if any(contact.values()):
                    property_obj.contact_info = contact

                # Recalculate price per sqm
                if property_obj.price and property_obj.total_area:
                    property_obj.price_per_sqm = float(property_obj.price) / float(property_obj.total_area)

                # Restore preserved fields
                for field, value in preserved_fields.items():
                    if value is not None:
                        setattr(property_obj, field, value)

                # Update images (delete old, add new)
                # Delete existing images
                for img in property_obj.images:
                    await db.delete(img)
                property_obj.images = []

                # Add new images
                if scraped_data.get('images'):
                    for idx, img_url in enumerate(scraped_data['images'][:20]):
                        image = PropertyImage(
                            url=img_url,
                            is_primary=(idx == 0),
                            order=idx,
                        )
                        property_obj.images.append(image)

                property_obj.scraped_at = datetime.utcnow()
                updated_count += 1

            except Exception as e:
                error_count += 1
                errors.append(f"{property_obj.title}: {str(e)}")
                print(f"Error re-scraping property {property_obj.id}: {str(e)}")
                # Continue with other properties even if this one fails
                continue

        await db.commit()

        return {
            'success': True,
            'message': f'Re-scraping completado: {updated_count} propiedades actualizadas, {error_count} errores',
            'total_properties': len(properties),
            'updated_count': updated_count,
            'error_count': error_count,
        }

    except Exception as e:
        await db.rollback()
        return {
            'success': False,
            'message': f'Error al re-scrapear propiedades: {str(e)}',
        }


# Helper functions

def _parse_status(status_str: str) -> str:
    """Convert status string to valid enum value"""
    status_map = {
        'active': PropertyStatus.ACTIVE.value,
        'sold': PropertyStatus.SOLD.value,
        'rented': PropertyStatus.RENTED.value,
        'reserved': PropertyStatus.RESERVED.value,
        'removed': PropertyStatus.REMOVED.value,
    }
    return status_map.get(status_str.lower(), PropertyStatus.ACTIVE.value)


def _scraped_to_property(scraped_data: dict, user_id: UUID) -> dict:
    """Convert scraped data to Property model format"""
    location_data = scraped_data.get('location', {})
    features = scraped_data.get('features', {})
    contact = scraped_data.get('contact', {})

    # Normalize address fields before saving
    normalized = normalize_address_fields(
        address=scraped_data.get('address'),
        street=scraped_data.get('street'),
        street_number=scraped_data.get('street_number'),
        neighborhood=location_data.get('neighborhood'),
        city=location_data.get('city', 'Capital Federal'),
        province=location_data.get('province', 'Capital Federal'),
    )

    property_data = {
        'source': scraped_data.get('source', 'manual'),
        'source_url': scraped_data.get('source_url'),
        'source_id': scraped_data.get('source_id'),
        'property_type': scraped_data.get('property_type', 'casa'),
        'operation_type': scraped_data.get('operation_type', 'venta'),
        'title': scraped_data.get('title', 'Sin título'),
        'description': scraped_data.get('description'),
        'price': scraped_data.get('price', 0),
        'currency': scraped_data.get('currency', 'USD'),
        'address': normalized['address'],
        'street': normalized['street'],
        'street_number': normalized['street_number'],
        'neighborhood': normalized['neighborhood'],
        'city': normalized['city'],
        'province': normalized['province'],
        'covered_area': features.get('covered_area'),
        'total_area': features.get('total_area'),
        'bedrooms': features.get('bedrooms'),
        'bathrooms': features.get('bathrooms'),
        'parking_spaces': features.get('parking_spaces'),
        'amenities': {'list': features.get('amenities', [])} if features.get('amenities') else None,
        'real_estate_agency': contact.get('real_estate_agency'),
        'contact_info': contact if any(contact.values()) else None,
        'status': _parse_status(scraped_data.get('status', 'active')),
        'scraped_at': datetime.utcnow(),
        'created_by': user_id,
    }

    # Calculate price per sqm
    if property_data['price'] and property_data.get('total_area'):
        property_data['price_per_sqm'] = property_data['price'] / property_data['total_area']

    return property_data
