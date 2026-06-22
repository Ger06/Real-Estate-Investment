"""
One-time script to load CABA manzanas GeoJSON into PostgreSQL.

Usage:
    python backend/scripts/load_manzanas.py

Prerequisites:
    1. Download manzanas.geojson from https://data.buenosaires.gob.ar/dataset/manzanas
    2. Place it at backend/data/manzanas.geojson
    3. Run alembic upgrade head to create the manzanas table
    4. Set DATABASE_URL env var or ensure backend/.env is configured
"""
import json
import os
import sys
from pathlib import Path

# Allow running from repo root
sys.path.insert(0, str(Path(__file__).parent.parent))

import psycopg2
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

GEOJSON_PATH = Path(__file__).parent.parent / "data" / "manzanas.geojson"

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    # Build from individual vars
    host = os.environ.get("POSTGRES_HOST", "localhost")
    port = os.environ.get("POSTGRES_PORT", "5432")
    user = os.environ.get("POSTGRES_USER", "postgres")
    password = os.environ.get("POSTGRES_PASSWORD", "")
    db = os.environ.get("POSTGRES_DB", "real_estate")
    DATABASE_URL = f"postgresql://{user}:{password}@{host}:{port}/{db}"

# Convert asyncpg URL to psycopg2 format if needed
DATABASE_URL = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")


def geometry_to_wkt(geometry: dict) -> str:
    """Convert GeoJSON geometry to WKT, ensuring MULTIPOLYGON output."""
    geom_type = geometry["type"]
    coords = geometry["coordinates"]

    if geom_type == "Polygon":
        rings = []
        for ring in coords:
            pts = ", ".join(f"{x} {y}" for x, y in ring)
            rings.append(f"({pts})")
        rings_str = ", ".join(rings)
        return f"MULTIPOLYGON(({rings_str}))"

    elif geom_type == "MultiPolygon":
        polygons = []
        for polygon in coords:
            rings = []
            for ring in polygon:
                pts = ", ".join(f"{x} {y}" for x, y in ring)
                rings.append(f"({pts})")
            polygons.append(f"({', '.join(rings)})")
        return f"MULTIPOLYGON({', '.join(polygons)})"

    else:
        raise ValueError(f"Unsupported geometry type: {geom_type}")


def main():
    if not GEOJSON_PATH.exists():
        print(f"ERROR: GeoJSON file not found at {GEOJSON_PATH}")
        print("Please download it from https://data.buenosaires.gob.ar/dataset/manzanas")
        sys.exit(1)

    print(f"Loading {GEOJSON_PATH}...")
    with open(GEOJSON_PATH, encoding="utf-8") as f:
        data = json.load(f)

    features = data.get("features", [])
    print(f"Found {len(features)} features")

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    insert_sql = """
        INSERT INTO manzanas (manzana_id, smp, barrio, comuna, geom)
        VALUES (%s, %s, %s, %s, ST_GeomFromText(%s, 4326))
        ON CONFLICT (manzana_id) DO NOTHING
    """

    inserted = 0
    skipped = 0
    errors = 0

    for i, feature in enumerate(features):
        props = feature.get("properties") or {}
        geometry = feature.get("geometry")

        if not geometry:
            skipped += 1
            continue

        # Try common field names from CABA open data portal
        manzana_id = (
            props.get("ID") or props.get("id") or
            props.get("MANZANA") or props.get("manzana") or
            str(i)
        )
        smp = props.get("SMP") or props.get("smp")
        barrio = (
            props.get("BARRIO") or props.get("barrio") or
            props.get("NOMBRE_BARRIO") or props.get("nombre_barrio")
        )
        comuna = props.get("COMUNA") or props.get("comuna")
        if comuna is not None:
            try:
                comuna = int(comuna)
            except (ValueError, TypeError):
                comuna = None

        try:
            wkt = geometry_to_wkt(geometry)
            cur.execute(insert_sql, (manzana_id, smp, barrio, comuna, wkt))
            inserted += 1
        except Exception as e:
            errors += 1
            if errors <= 5:
                print(f"  Error on feature {i}: {e}")

        if (i + 1) % 500 == 0:
            conn.commit()
            print(f"  Processed {i + 1}/{len(features)}...")

    conn.commit()
    cur.close()
    conn.close()

    print(f"\nDone! Inserted: {inserted}, Skipped: {skipped}, Errors: {errors}")


if __name__ == "__main__":
    main()
