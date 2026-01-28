"""
Monitoring Service
Orchestrates saved searches execution and pending property management
"""
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.models.saved_search import SavedSearch
from app.models.pending_property import PendingProperty, PendingPropertyStatus
from app.models.property import (
    Property, PropertyImage, PropertySource, PropertyType,
    OperationType, Currency, PropertyStatus
)
from app.scrapers.listing_argenprop import ArgenpropListingScraper
from app.scrapers.listing_zonaprop import ZonapropListingScraper
from app.scrapers.listing_remax import RemaxListingScraper
from app.scrapers.listing_mercadolibre import MercadoLibreListingScraper
from app.scrapers import ArgenpropScraper, ZonapropScraper, RemaxScraper, MercadoLibreScraper

logger = logging.getLogger(__name__)


class MonitoringService:
    """
    Service for executing saved searches and managing pending properties.

    Flow:
    1. Execute saved search -> Call listing scrapers for each portal
    2. For each discovered URL:
       - Check if exists in Property table (by source_url)
       - Check if exists in PendingProperty table
       - If new: add to pending queue (or auto-scrape if enabled)
    3. Update execution statistics
    """

    # Map portal names to listing scraper classes
    LISTING_SCRAPERS = {
        "argenprop": ArgenpropListingScraper,
        "zonaprop": ZonapropListingScraper,
        "remax": RemaxListingScraper,
        "mercadolibre": MercadoLibreListingScraper,
    }

    # Map portal names to property scraper classes
    PROPERTY_SCRAPERS = {
        "argenprop": ArgenpropScraper,
        "zonaprop": ZonapropScraper,
        "remax": RemaxScraper,
        "mercadolibre": MercadoLibreScraper,
    }

    def __init__(self, db: AsyncSession):
        self.db = db

    async def execute_search(
        self,
        search: SavedSearch,
        max_properties: int = 100,
    ) -> Dict[str, Any]:
        """
        Execute a saved search across all configured portals.

        Args:
            search: SavedSearch model instance
            max_properties: Maximum properties to discover per portal

        Returns:
            Dict with execution results:
            {
                'success': bool,
                'total_found': int,
                'new_properties': int,
                'duplicates': int,
                'scraped': int,
                'pending': int,
                'errors': List[dict]
            }
        """
        results = {
            'success': True,
            'total_found': 0,
            'new_properties': 0,
            'duplicates': 0,
            'scraped': 0,
            'pending': 0,
            'errors': [],
        }

        # Build search params from SavedSearch model
        search_params = self._build_search_params(search)
        print(f"[DEBUG] Search params: {search_params}")

        # Execute search for each portal
        for portal in search.portals:
            portal_lower = portal.lower()

            if portal_lower not in self.LISTING_SCRAPERS:
                logger.warning(f"Listing scraper not implemented for portal: {portal}")
                results['errors'].append({
                    'portal': portal,
                    'error': f"Scraper de listados no implementado para {portal}",
                })
                continue

            try:
                # Create listing scraper instance
                scraper_class = self.LISTING_SCRAPERS[portal_lower]
                scraper = scraper_class(search_params)

                # For Remax, pass DB session for cache lookups
                if portal_lower == "remax":
                    scraper.set_db_session(self.db)
                    await scraper.load_cache_from_db()

                # Debug: show the URL that will be scraped
                test_url = scraper.build_search_url(page=1)
                print(f"[DEBUG] Scraping URL (monitoring service): {test_url}", flush=True)

                # Scrape listings
                logger.info(f"Executing search on {portal} for '{search.name}'")
                cards = await scraper.scrape_all_pages(max_properties=max_properties)
                print(f"[DEBUG] Found {len(cards)} cards")

                # Special handling for MercadoLibre bot detection
                if portal_lower == "mercadolibre" and len(cards) == 0:
                    results['errors'].append({
                        'portal': portal,
                        'error': (
                            "MercadoLibre tiene protección anti-bots activa. "
                            "No se encontraron propiedades automáticamente. "
                            f"Puedes buscar manualmente en: {test_url}"
                        ),
                        'search_url': test_url,
                        'type': 'bot_detection',
                    })
                    logger.warning(f"MercadoLibre bot detection active for search '{search.name}'")

                results['total_found'] += len(cards)

                # Process each discovered property
                for card in cards:
                    try:
                        is_new, status = await self._process_discovered_property(
                            card=card,
                            search=search,
                            portal=portal_lower,
                        )

                        if is_new:
                            results['new_properties'] += 1
                            if status == 'scraped':
                                results['scraped'] += 1
                            else:
                                results['pending'] += 1
                        else:
                            results['duplicates'] += 1

                    except Exception as e:
                        logger.error(f"Error processing card {card.get('source_url')}: {e}")
                        results['errors'].append({
                            'portal': portal,
                            'url': card.get('source_url'),
                            'error': str(e),
                        })

            except Exception as e:
                logger.error(f"Error executing search on {portal}: {e}")
                results['errors'].append({
                    'portal': portal,
                    'error': str(e),
                })
                results['success'] = False

        # Update search execution stats
        search.last_executed_at = datetime.utcnow()
        search.total_executions = (search.total_executions or 0) + 1
        search.total_properties_found = (search.total_properties_found or 0) + results['new_properties']

        await self.db.commit()

        return results

    def _build_search_params(self, search: SavedSearch) -> Dict[str, Any]:
        """Convert SavedSearch model to scraper params dict"""
        params = {
            'operation_type': search.operation_type.value if search.operation_type else 'venta',
        }

        if search.property_type:
            params['property_type'] = search.property_type.value

        if search.city:
            params['city'] = search.city

        if search.province:
            params['province'] = search.province

        if search.neighborhoods:
            params['neighborhoods'] = search.neighborhoods

        if search.min_price:
            params['min_price'] = float(search.min_price)

        if search.max_price:
            params['max_price'] = float(search.max_price)

        if search.currency:
            params['currency'] = search.currency.value

        if search.min_area:
            params['min_area'] = float(search.min_area)

        if search.max_area:
            params['max_area'] = float(search.max_area)

        if search.min_bedrooms:
            params['min_bedrooms'] = search.min_bedrooms

        if search.max_bedrooms:
            params['max_bedrooms'] = search.max_bedrooms

        if search.min_bathrooms:
            params['min_bathrooms'] = search.min_bathrooms

        return params

    async def _process_discovered_property(
        self,
        card: Dict[str, Any],
        search: SavedSearch,
        portal: str,
    ) -> Tuple[bool, str]:
        """
        Process a discovered property card.

        Returns:
            Tuple of (is_new, status):
            - is_new: True if this is a new property
            - status: 'pending', 'scraped', or 'duplicate'
        """
        source_url = card.get('source_url')
        if not source_url:
            return False, 'error'

        # Check 1: Does this URL already exist in Property table?
        stmt = select(Property).where(Property.source_url == source_url)
        result = await self.db.execute(stmt)
        existing_property = result.scalar_one_or_none()

        if existing_property:
            return False, 'duplicate'

        # Check 2: Does this URL already exist in PendingProperty table?
        stmt = select(PendingProperty).where(PendingProperty.source_url == source_url)
        result = await self.db.execute(stmt)
        existing_pending = result.scalar_one_or_none()

        if existing_pending:
            return False, 'duplicate'

        # It's a new property - add to pending queue
        pending = PendingProperty(
            saved_search_id=search.id,
            source_url=source_url,
            source=PropertySource(portal),
            source_id=card.get('source_id'),
            title=card.get('title'),
            price=card.get('price'),
            currency=card.get('currency'),
            thumbnail_url=card.get('thumbnail_url'),
            location_preview=card.get('location_preview'),
            status=PendingPropertyStatus.PENDING,
            discovered_at=datetime.utcnow(),
        )
        self.db.add(pending)

        # Auto-scrape if enabled
        if search.auto_scrape:
            try:
                property_id = await self._scrape_and_save_property(pending)
                if property_id:
                    pending.status = PendingPropertyStatus.SCRAPED
                    pending.property_id = property_id
                    pending.scraped_at = datetime.utcnow()
                    return True, 'scraped'
            except Exception as e:
                logger.error(f"Auto-scrape failed for {source_url}: {e}")
                pending.status = PendingPropertyStatus.ERROR
                pending.error_message = str(e)[:500]

        return True, 'pending'

    async def _scrape_and_save_property(self, pending: PendingProperty) -> Optional[UUID]:
        """
        Scrape full property data and save to database.

        Returns:
            Property UUID if successful, None otherwise
        """
        portal = pending.source.value
        url = pending.source_url

        if portal not in self.PROPERTY_SCRAPERS:
            raise ValueError(f"No property scraper for portal: {portal}")

        # Create property scraper
        scraper_class = self.PROPERTY_SCRAPERS[portal]
        scraper = scraper_class(url)

        # Scrape property data
        scraped_data = await scraper.scrape()
        scraped_data['source_url'] = url

        # Convert to Property model
        property_data = self._scraped_to_property(scraped_data)
        new_property = Property(**property_data)

        # Add images
        if scraped_data.get('images'):
            for idx, img_url in enumerate(scraped_data['images'][:20]):
                image = PropertyImage(
                    url=img_url,
                    is_primary=(idx == 0),
                    order=idx,
                )
                new_property.images.append(image)

        self.db.add(new_property)
        await self.db.flush()  # Get the ID without committing

        return new_property.id

    def _scraped_to_property(self, scraped_data: dict) -> dict:
        """Convert scraped data to Property model format"""
        location_data = scraped_data.get('location', {})
        features = scraped_data.get('features', {})
        contact = scraped_data.get('contact', {})

        # Convert source string to enum
        source_str = scraped_data.get('source', 'manual').upper()
        try:
            source_enum = PropertySource(source_str.lower())
        except ValueError:
            source_enum = PropertySource.MANUAL

        # Convert property_type string to enum
        prop_type_str = scraped_data.get('property_type', 'casa').lower()
        try:
            prop_type_enum = PropertyType(prop_type_str)
        except ValueError:
            prop_type_enum = PropertyType.CASA

        # Convert operation_type string to enum
        op_type_str = scraped_data.get('operation_type', 'venta').lower()
        try:
            op_type_enum = OperationType(op_type_str)
        except ValueError:
            op_type_enum = OperationType.VENTA

        # Convert currency string to enum
        currency_str = scraped_data.get('currency', 'USD').upper()
        try:
            currency_enum = Currency(currency_str)
        except ValueError:
            currency_enum = Currency.USD

        # Convert status string to enum (PropertyStatus uses uppercase values)
        status_str = scraped_data.get('status', 'active').upper()
        try:
            status_enum = PropertyStatus(status_str)
        except ValueError:
            status_enum = PropertyStatus.ACTIVE

        property_data = {
            'source': source_enum,
            'source_url': scraped_data.get('source_url'),
            'source_id': scraped_data.get('source_id'),
            'property_type': prop_type_enum,
            'operation_type': op_type_enum,
            'title': scraped_data.get('title', 'Sin título'),
            'description': scraped_data.get('description'),
            'price': scraped_data.get('price', 0),
            'currency': currency_enum,
            'address': scraped_data.get('address'),
            'neighborhood': location_data.get('neighborhood'),
            'city': location_data.get('city', 'Buenos Aires'),
            'province': location_data.get('province', 'Buenos Aires'),
            'covered_area': features.get('covered_area'),
            'total_area': features.get('total_area'),
            'bedrooms': features.get('bedrooms'),
            'bathrooms': features.get('bathrooms'),
            'parking_spaces': features.get('parking_spaces'),
            'amenities': {'list': features.get('amenities', [])} if features.get('amenities') else None,
            'real_estate_agency': contact.get('real_estate_agency'),
            'contact_info': contact if any(contact.values()) else None,
            'status': status_enum,
            'scraped_at': datetime.utcnow(),
        }

        # Calculate price per sqm
        if property_data['price'] and property_data.get('total_area'):
            property_data['price_per_sqm'] = property_data['price'] / property_data['total_area']

        return property_data

    async def scrape_pending_properties(
        self,
        search_id: Optional[UUID] = None,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """
        Scrape pending properties from the queue.

        Args:
            search_id: Optional filter by saved search
            limit: Maximum number of properties to scrape

        Returns:
            Dict with results
        """
        results = {
            'success': True,
            'scraped': 0,
            'errors': 0,
            'error_details': [],
        }

        # Build query for pending properties
        stmt = select(PendingProperty).where(
            PendingProperty.status == PendingPropertyStatus.PENDING
        )

        if search_id:
            stmt = stmt.where(PendingProperty.saved_search_id == search_id)

        stmt = stmt.order_by(PendingProperty.discovered_at.asc()).limit(limit)

        result = await self.db.execute(stmt)
        pending_properties = result.scalars().all()

        for pending in pending_properties:
            try:
                property_id = await self._scrape_and_save_property(pending)

                if property_id:
                    pending.status = PendingPropertyStatus.SCRAPED
                    pending.property_id = property_id
                    pending.scraped_at = datetime.utcnow()
                    results['scraped'] += 1
                else:
                    pending.status = PendingPropertyStatus.ERROR
                    pending.error_message = "No se pudo obtener datos de la propiedad"
                    results['errors'] += 1

            except Exception as e:
                logger.error(f"Error scraping {pending.source_url}: {e}")
                pending.status = PendingPropertyStatus.ERROR
                pending.error_message = str(e)[:500]
                results['errors'] += 1
                results['error_details'].append({
                    'pending_id': str(pending.id),
                    'url': pending.source_url,
                    'error': str(e),
                })

        await self.db.commit()
        return results

    async def scrape_single_pending(self, pending_id: UUID) -> Dict[str, Any]:
        """
        Scrape a single pending property by ID.

        Returns:
            Dict with result
        """
        stmt = select(PendingProperty).where(PendingProperty.id == pending_id)
        result = await self.db.execute(stmt)
        pending = result.scalar_one_or_none()

        if not pending:
            return {
                'success': False,
                'message': 'Propiedad pendiente no encontrada',
                'pending_id': pending_id,
            }

        if pending.status != PendingPropertyStatus.PENDING:
            return {
                'success': False,
                'message': f'La propiedad ya fue procesada (estado: {pending.status.value})',
                'pending_id': pending_id,
            }

        try:
            property_id = await self._scrape_and_save_property(pending)

            if property_id:
                pending.status = PendingPropertyStatus.SCRAPED
                pending.property_id = property_id
                pending.scraped_at = datetime.utcnow()
                await self.db.commit()

                return {
                    'success': True,
                    'message': 'Propiedad scrapeada exitosamente',
                    'pending_id': pending_id,
                    'property_id': property_id,
                }
            else:
                pending.status = PendingPropertyStatus.ERROR
                pending.error_message = "No se pudo obtener datos"
                await self.db.commit()

                return {
                    'success': False,
                    'message': 'No se pudieron obtener datos de la propiedad',
                    'pending_id': pending_id,
                }

        except Exception as e:
            pending.status = PendingPropertyStatus.ERROR
            pending.error_message = str(e)[:500]
            await self.db.commit()

            return {
                'success': False,
                'message': f'Error al scrapear: {str(e)}',
                'pending_id': pending_id,
            }

    async def skip_pending(self, pending_id: UUID) -> Dict[str, Any]:
        """
        Mark a pending property as skipped (user doesn't want to scrape it).
        """
        stmt = select(PendingProperty).where(PendingProperty.id == pending_id)
        result = await self.db.execute(stmt)
        pending = result.scalar_one_or_none()

        if not pending:
            return {
                'success': False,
                'message': 'Propiedad pendiente no encontrada',
                'pending_id': pending_id,
            }

        pending.status = PendingPropertyStatus.SKIPPED
        pending.updated_at = datetime.utcnow()
        await self.db.commit()

        return {
            'success': True,
            'message': 'Propiedad marcada como omitida',
            'pending_id': pending_id,
        }

    async def get_pending_stats(self, user_id: UUID) -> Dict[str, Any]:
        """
        Get statistics about pending properties for a user.
        """
        # Get user's saved searches
        search_stmt = select(SavedSearch.id).where(SavedSearch.user_id == user_id)
        search_result = await self.db.execute(search_stmt)
        search_ids = [row[0] for row in search_result.fetchall()]

        if not search_ids:
            return {
                'total_pending': 0,
                'total_scraped': 0,
                'total_skipped': 0,
                'total_errors': 0,
                'by_search': [],
                'by_portal': [],
            }

        # Count by status
        stats = {}
        for status in PendingPropertyStatus:
            count_stmt = select(func.count()).select_from(PendingProperty).where(
                and_(
                    PendingProperty.saved_search_id.in_(search_ids),
                    PendingProperty.status == status
                )
            )
            result = await self.db.execute(count_stmt)
            stats[status.value.lower()] = result.scalar() or 0

        # Count by search
        by_search_stmt = select(
            SavedSearch.id,
            SavedSearch.name,
            func.count(PendingProperty.id).label('count')
        ).outerjoin(
            PendingProperty,
            and_(
                PendingProperty.saved_search_id == SavedSearch.id,
                PendingProperty.status == PendingPropertyStatus.PENDING
            )
        ).where(
            SavedSearch.id.in_(search_ids)
        ).group_by(SavedSearch.id, SavedSearch.name)

        by_search_result = await self.db.execute(by_search_stmt)
        by_search = [
            {'search_id': str(row[0]), 'search_name': row[1], 'pending_count': row[2]}
            for row in by_search_result.fetchall()
        ]

        # Count by portal
        by_portal_stmt = select(
            PendingProperty.source,
            func.count(PendingProperty.id).label('count')
        ).where(
            and_(
                PendingProperty.saved_search_id.in_(search_ids),
                PendingProperty.status == PendingPropertyStatus.PENDING
            )
        ).group_by(PendingProperty.source)

        by_portal_result = await self.db.execute(by_portal_stmt)
        by_portal = [
            {'portal': row[0].value, 'pending_count': row[1]}
            for row in by_portal_result.fetchall()
        ]

        return {
            'total_pending': stats.get('pending', 0),
            'total_scraped': stats.get('scraped', 0),
            'total_skipped': stats.get('skipped', 0),
            'total_errors': stats.get('error', 0),
            'by_search': by_search,
            'by_portal': by_portal,
        }
