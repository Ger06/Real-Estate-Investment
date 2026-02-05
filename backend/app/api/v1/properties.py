"""
Properties API endpoints
"""
from typing import List, Optional
from datetime import datetime
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from geoalchemy2.shape import from_shape
from shapely.geometry import Point

from app.database import get_db
from app.models.property import Property, PropertyImage, PropertySource, PriceHistory, PropertyStatus
from app.schemas.property import (
    PropertyScrapeRequest,
    PropertyScrapeResponse,
    PropertyCreate,
    PropertyUpdate,
    PropertyResponse,
    PropertyListResponse,
)
from app.scrapers import ArgenpropScraper, ZonapropScraper, RemaxScraper, MercadoLibreScraper
from app.api.deps import get_current_user
from app.models.user import User


router = APIRouter()


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
    db: AsyncSession = Depends(get_db),
):
    """
    List all properties with pagination
    """
    # Get total count
    count_stmt = select(func.count()).select_from(Property)
    total_result = await db.execute(count_stmt)
    total = total_result.scalar()

    # Get properties
    stmt = (
        select(Property)
        .offset(skip)
        .limit(limit)
        .order_by(Property.created_at.desc())
    )
    result = await db.execute(stmt)
    properties = result.scalars().all()

    return PropertyListResponse(
        total=total or 0,
        skip=skip,
        limit=limit,
        items=properties,
    )


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
    current_user: User = Depends(get_current_user),
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
    for field, value in update_data.items():
        setattr(property_obj, field, value)

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

                # Update location
                property_obj.address = scraped_data.get('address', property_obj.address)
                # Only update street/street_number if they're empty (preserve manual edits)
                if not property_obj.street and scraped_data.get('street'):
                    property_obj.street = scraped_data.get('street')
                if not property_obj.street_number and scraped_data.get('street_number'):
                    property_obj.street_number = scraped_data.get('street_number')
                property_obj.neighborhood = location_data.get('neighborhood', property_obj.neighborhood)
                property_obj.city = location_data.get('city', property_obj.city)
                property_obj.province = location_data.get('province', property_obj.province)

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
        'address': scraped_data.get('address'),
        'street': scraped_data.get('street'),
        'street_number': scraped_data.get('street_number'),
        'neighborhood': location_data.get('neighborhood'),
        'city': location_data.get('city', 'Capital Federal'),
        'province': location_data.get('province', 'Capital Federal'),
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
