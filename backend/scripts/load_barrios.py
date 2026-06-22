"""
One-time script to load CABA barrios GeoJSON into PostgreSQL.

Usage:
    python backend/scripts/load_barrios.py

Prerequisites:
    1. Download barrios.geojson from https://data.buenosaires.gob.ar/dataset/barrios
    2. Place it at backend/data/barrios.geojson
    3. Run alembic upgrade head to create the barrios table
    4. Set DATABASE_URL env var or ensure backend/.env is configured
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import psycopg2
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

GEOJSON_PATH = Path(__file__).parent.parent / "data" / "barrios.geojson"

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    host = os.environ.get("POSTGRES_HOST", "localhost")
    port = os.environ.get("POSTGRES_PORT", "5432")
    user = os.environ.get("POSTGRES_USER", "postgres")
    password = os.environ.get("POSTGRES_PASSWORD", "")
    db = os.environ.get("POSTGRES_DB", "real_estate")
    DATABASE_URL = f"postgresql://{user}:{password}@{host}:{port}/{db}"

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
        print("Download it from https://data.buenosaires.gob.ar/dataset/barrios")
        sys.exit(1)

    print(f"Loading {GEOJSON_PATH}...")
    with open(GEOJSON_PATH, encoding="utf-8") as f:
        data = json.load(f)

    features = data.get("features", [])
    print(f"Found {len(features)} features")

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    insert_sql = """
        INSERT INTO barrios (nombre, comuna, geom)
        VALUES (%s, %s, ST_GeomFromText(%s, 4326))
        ON CONFLICT (nombre) DO UPDATE SET
            comuna = EXCLUDED.comuna,
            geom = EXCLUDED.geom
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

        nombre = (
            props.get("BARRIO") or props.get("barrio") or
            props.get("NOMBRE_BARRIO") or props.get("nombre_barrio") or
            props.get("nombre") or props.get("NOMBRE") or
            props.get("name") or props.get("NAME")
        )
        if not nombre:
            print(f"  Warning: feature {i} has no barrio name, keys: {list(props.keys())}")
            skipped += 1
            continue

        nombre = nombre.strip().upper()

        comuna = props.get("COMUNA") or props.get("comuna")
        if comuna is not None:
            try:
                comuna = int(comuna)
            except (ValueError, TypeError):
                comuna = None

        try:
            wkt = geometry_to_wkt(geometry)
            cur.execute(insert_sql, (nombre, comuna, wkt))
            inserted += 1
        except Exception as e:
            errors += 1
            if errors <= 5:
                print(f"  Error on feature {i} ({nombre}): {e}")

    conn.commit()
    cur.close()
    conn.close()

    print(f"\nDone! Inserted/updated: {inserted}, Skipped: {skipped}, Errors: {errors}")


if __name__ == "__main__":
    main()
