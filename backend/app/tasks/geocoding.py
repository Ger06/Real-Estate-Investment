"""
Geocoding Celery tasks
"""
import logging
import asyncio
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.config import settings
from app.models.property import Property
from app.services.geocoding import geocoding_service
from app.tasks import celery_app

logger = logging.getLogger(__name__)


def _get_async_session_factory():
    """Create an async session factory for use in Celery tasks"""
    engine = create_async_engine(settings.DATABASE_URL)
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def _geocode_property(session: AsyncSession, property_obj: Property) -> bool:
    """Geocode a single property and update its location"""
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
        await session.commit()
        logger.info(f"Geocoded property {property_obj.id}: ({lat}, {lng})")
        return True

    logger.warning(f"Could not geocode property {property_obj.id}")
    return False


@celery_app.task(name="geocode_single_property")
def geocode_single_property(property_id: str):
    """Geocode a single property by ID"""
    async def _run():
        SessionFactory = _get_async_session_factory()
        async with SessionFactory() as session:
            stmt = select(Property).where(Property.id == UUID(property_id))
            result = await session.execute(stmt)
            prop = result.scalar_one_or_none()

            if not prop:
                logger.error(f"Property {property_id} not found")
                return False

            return await _geocode_property(session, prop)

    return asyncio.run(_run())


@celery_app.task(name="geocode_all_properties")
def geocode_all_properties():
    """Geocode all properties that don't have coordinates"""
    async def _run():
        SessionFactory = _get_async_session_factory()
        async with SessionFactory() as session:
            stmt = select(Property).where(Property.location.is_(None))
            result = await session.execute(stmt)
            properties = result.scalars().all()

            total = len(properties)
            success = 0
            failed = 0

            for prop in properties:
                try:
                    if await _geocode_property(session, prop):
                        success += 1
                    else:
                        failed += 1
                except Exception as e:
                    logger.error(f"Error geocoding property {prop.id}: {e}")
                    failed += 1

            logger.info(f"Geocoding batch complete: {success}/{total} success, {failed} failed")
            return {"total": total, "success": success, "failed": failed}

    return asyncio.run(_run())
