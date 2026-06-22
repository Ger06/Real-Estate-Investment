"""
FastAPI Application Entry Point
"""
import json
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from sqlalchemy import text

from app.core.config import settings
from app.core.logging import setup_logging
from app.api.v1.router import api_router
from app.database import AsyncSessionLocal

logger = logging.getLogger(__name__)

BARRIOS_GEOJSON = Path(__file__).parent.parent / "data" / "barrios.geojson"


def _geometry_to_wkt(geometry: dict) -> str:
    geom_type = geometry["type"]
    coords = geometry["coordinates"]
    if geom_type == "Polygon":
        rings = ", ".join(
            f"({', '.join(f'{x} {y}' for x, y in ring)})" for ring in coords
        )
        return f"MULTIPOLYGON(({rings}))"
    elif geom_type == "MultiPolygon":
        polygons = []
        for polygon in coords:
            rings = ", ".join(
                f"({', '.join(f'{x} {y}' for x, y in ring)})" for ring in polygon
            )
            polygons.append(f"({rings})")
        return f"MULTIPOLYGON({', '.join(polygons)})"
    raise ValueError(f"Unsupported geometry type: {geom_type}")


async def _seed_barrios() -> None:
    if not BARRIOS_GEOJSON.exists():
        logger.warning("barrios.geojson not found, skipping seed")
        return
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(text("SELECT COUNT(*) FROM barrios"))
            if result.scalar() > 0:
                return

            logger.info("Seeding barrios table...")
            with open(BARRIOS_GEOJSON, encoding="utf-8") as f:
                data = json.load(f)

            insert_sql = text("""
                INSERT INTO barrios (nombre, comuna, geom)
                VALUES (:nombre, :comuna, ST_GeomFromText(:wkt, 4326))
                ON CONFLICT (nombre) DO NOTHING
            """)

            inserted = 0
            for feature in data.get("features", []):
                props = feature.get("properties") or {}
                geometry = feature.get("geometry")
                if not geometry:
                    continue
                nombre = (
                    props.get("BARRIO") or props.get("barrio") or
                    props.get("NOMBRE_BARRIO") or props.get("nombre_barrio") or
                    props.get("nombre") or props.get("NOMBRE") or
                    props.get("name") or props.get("NAME")
                )
                if not nombre:
                    continue
                nombre = nombre.strip().upper()
                comuna = props.get("COMUNA") or props.get("comuna")
                if comuna is not None:
                    try:
                        comuna = int(comuna)
                    except (ValueError, TypeError):
                        comuna = None
                try:
                    wkt = _geometry_to_wkt(geometry)
                    await db.execute(insert_sql, {"nombre": nombre, "comuna": comuna, "wkt": wkt})
                    inserted += 1
                except Exception as e:
                    logger.warning(f"Error inserting barrio {nombre}: {e}")

            await db.commit()
            logger.info(f"Barrios seeded: {inserted} inserted")
    except Exception as e:
        logger.error(f"Barrios seed failed (non-fatal): {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    setup_logging()
    await _seed_barrios()
    yield


def create_application() -> FastAPI:
    """Create and configure FastAPI application"""
    
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        description="Real Estate Investment Analysis Platform API",
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        docs_url=f"{settings.API_V1_STR}/docs",
        redoc_url=f"{settings.API_V1_STR}/redoc",
        lifespan=lifespan,
    )

    # Set up CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add GZip compression
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    # Include API router
    app.include_router(api_router, prefix=settings.API_V1_STR)

    @app.get("/health")
    async def health_check():
        """Health check endpoint"""
        return {"status": "healthy", "version": settings.VERSION}

    return app


app = create_application()


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
