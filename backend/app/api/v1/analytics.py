"""
Analytics API endpoints
"""
from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.database import get_db
from app.schemas.property import ChoroplethResponse, ColorScaleBreakpoint

router = APIRouter()

# Color scale breakpoints (USD/m²)
COLOR_SCALE = [
    ColorScaleBreakpoint(level=1, min=None,   max=1200,  color="#1a9641", label="< $1,200"),
    ColorScaleBreakpoint(level=2, min=1200,   max=1600,  color="#74c476", label="$1,200–1,600"),
    ColorScaleBreakpoint(level=3, min=1600,   max=2000,  color="#d9ef8b", label="$1,600–2,000"),
    ColorScaleBreakpoint(level=4, min=2000,   max=2400,  color="#fee08b", label="$2,000–2,400"),
    ColorScaleBreakpoint(level=5, min=2400,   max=2800,  color="#fdae61", label="$2,400–2,800"),
    ColorScaleBreakpoint(level=6, min=2800,   max=3200,  color="#f46d43", label="$2,800–3,200"),
    ColorScaleBreakpoint(level=7, min=3200,   max=4000,  color="#d73027", label="$3,200–4,000"),
    ColorScaleBreakpoint(level=8, min=4000,   max=None,  color="#a50026", label="> $4,000"),
]


def _get_color_level(price_per_sqm: float) -> int:
    if price_per_sqm < 1200:
        return 1
    elif price_per_sqm < 1600:
        return 2
    elif price_per_sqm < 2000:
        return 3
    elif price_per_sqm < 2400:
        return 4
    elif price_per_sqm < 2800:
        return 5
    elif price_per_sqm < 3200:
        return 6
    elif price_per_sqm < 4000:
        return 7
    else:
        return 8


@router.get("/market-overview")
async def get_market_overview():
    """Get market overview analytics"""
    return {"message": "Market overview - to be implemented"}


@router.get("/price-trends")
async def get_price_trends():
    """Get price trends"""
    return {"message": "Price trends - to be implemented"}


@router.get("/choropleth", response_model=ChoroplethResponse)
async def get_choropleth(
    property_type: Optional[str] = None,
    ambientes: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Returns a GeoJSON FeatureCollection of CABA city blocks (manzanas)
    colored by average price per m² (USD) for active sale properties.
    """
    # Build optional filters (applied inside the active_props CTE)
    cte_extra = []
    params: dict = {}

    if property_type:
        cte_extra.append("AND UPPER(property_type::text) = UPPER(:property_type)")
        params["property_type"] = property_type

    if ambientes is not None:
        if ambientes == 1:
            cte_extra.append("AND bedrooms IN (0, 1)")
        elif ambientes == 2:
            cte_extra.append("AND bedrooms = 1")
        elif ambientes == 3:
            cte_extra.append("AND bedrooms = 2")
        elif ambientes >= 4:
            cte_extra.append("AND bedrooms >= 3")

    cte_extra_sql = "\n            ".join(cte_extra)

    # Phase 1: spatial join using geometry (not geography) so the GiST index is used.
    # Casting to geography on both sides disables index usage → 300s+; geometry → 0.1s.
    # 0.0005 degrees ≈ 50m at Buenos Aires latitude (~34°S).
    stats_sql = text(f"""
        WITH active_props AS (
            SELECT
                id,
                location::geometry AS geom,
                COALESCE(price_per_sqm, price / NULLIF(total_area::float, 0)) AS ppsm
            FROM properties
            WHERE UPPER(operation_type::text) = 'VENTA'
            AND currency::text = 'USD'
            AND status::text = 'ACTIVE'
            AND COALESCE(price_per_sqm, price / NULLIF(total_area::float, 0)) IS NOT NULL
            AND location IS NOT NULL
            {cte_extra_sql}
        )
        SELECT m.id, m.manzana_id, m.barrio,
               COUNT(p.id)::int AS property_count,
               AVG(p.ppsm)::float AS avg_price_per_sqm
        FROM manzanas m
        JOIN active_props p ON ST_DWithin(p.geom, m.geom, 0.0005)
        GROUP BY m.id, m.manzana_id, m.barrio
        HAVING COUNT(p.id) >= 1
    """)

    stats_result = await db.execute(stats_sql, params)
    stats_rows = stats_result.fetchall()

    if not stats_rows:
        return ChoroplethResponse(
            features=[],
            color_scale=COLOR_SCALE,
            total_manzanas=0,
            total_properties=0,
        )

    # Phase 2: fetch simplified geometries for matched manzana IDs only.
    manzana_ids = [row.id for row in stats_rows]
    geom_sql = text("""
        SELECT id, ST_AsGeoJSON(ST_SimplifyPreserveTopology(geom, 0.0001))::json AS geometry
        FROM manzanas
        WHERE id = ANY(:ids)
    """)
    geom_result = await db.execute(geom_sql, {"ids": manzana_ids})
    geom_by_id = {row.id: row.geometry for row in geom_result.fetchall()}

    features = []
    total_props = 0

    for row in stats_rows:
        avg = row.avg_price_per_sqm or 0.0
        level = _get_color_level(avg)
        total_props += row.property_count

        features.append({
            "type": "Feature",
            "geometry": geom_by_id.get(row.id),
            "properties": {
                "manzana_id": row.manzana_id,
                "barrio": row.barrio,
                "property_count": row.property_count,
                "avg_price_per_sqm": round(avg, 0),
                "color_level": level,
            },
        })

    return ChoroplethResponse(
        features=features,
        color_scale=COLOR_SCALE,
        total_manzanas=len(features),
        total_properties=total_props,
    )
