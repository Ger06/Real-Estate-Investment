"""
Geocoding Service using LocationIQ (Nominatim-compatible API)
Free tier: 5000 req/day, 2 req/sec. Requires API key.

Uses a 6-level cascade from most precise (structured query with street+number)
to least precise (neighborhood centroid), with centroid detection and jitter.
"""
import re
import random
import time
import logging
from typing import Optional, Tuple, List

from geopy.geocoders import Nominatim as _Nominatim
from geopy.extra.rate_limiter import RateLimiter
from geoalchemy2.shape import from_shape
from shapely.geometry import Point

from app.core.config import settings
from app.services.address import clean_raw_address, CABA_NEIGHBORHOODS

logger = logging.getLogger(__name__)

# Bounding box for CABA + GBA (Gran Buenos Aires)
# Roughly: lat -35.0 to -34.3, lng -58.9 to -58.2
BUENOS_AIRES_BOUNDS = {
    "lat_min": -35.0,
    "lat_max": -34.3,
    "lng_min": -58.9,
    "lng_max": -58.2,
}

# Approximate centroids of CABA neighborhoods (lat, lng)
# Used to detect when the geocoder returns a neighborhood-level result
CABA_CENTROIDS = {
    "agronomía": (-34.5983, -58.4897),
    "almagro": (-34.6089, -58.4196),
    "balvanera": (-34.6096, -58.4025),
    "barracas": (-34.6416, -58.3820),
    "belgrano": (-34.5600, -58.4560),
    "boedo": (-34.6280, -58.4170),
    "caballito": (-34.6189, -58.4370),
    "chacarita": (-34.5880, -58.4540),
    "coghlan": (-34.5620, -58.4720),
    "colegiales": (-34.5740, -58.4490),
    "constitución": (-34.6280, -58.3840),
    "flores": (-34.6320, -58.4620),
    "floresta": (-34.6320, -58.4830),
    "la boca": (-34.6350, -58.3630),
    "la paternal": (-34.5970, -58.4680),
    "liniers": (-34.6420, -58.5200),
    "mataderos": (-34.6540, -58.5090),
    "monte castro": (-34.6180, -58.4930),
    "monserrat": (-34.6140, -58.3780),
    "nueva pompeya": (-34.6490, -58.4180),
    "núñez": (-34.5460, -58.4580),
    "palermo": (-34.5740, -58.4240),
    "parque avellaneda": (-34.6440, -58.4800),
    "parque chacabuco": (-34.6370, -58.4400),
    "parque chas": (-34.5860, -58.4780),
    "parque patricios": (-34.6380, -58.4020),
    "puerto madero": (-34.6180, -58.3610),
    "recoleta": (-34.5870, -58.3960),
    "retiro": (-34.5920, -58.3750),
    "saavedra": (-34.5540, -58.4880),
    "san cristóbal": (-34.6230, -58.4010),
    "san nicolás": (-34.6050, -58.3820),
    "san telmo": (-34.6220, -58.3740),
    "vélez sarsfield": (-34.6350, -58.4920),
    "versalles": (-34.6300, -58.5170),
    "villa crespo": (-34.5980, -58.4380),
    "villa del parque": (-34.6050, -58.4880),
    "villa devoto": (-34.6020, -58.5130),
    "villa general mitre": (-34.6100, -58.4710),
    "villa lugano": (-34.6710, -58.4730),
    "villa luro": (-34.6380, -58.5010),
    "villa ortúzar": (-34.5840, -58.4680),
    "villa pueyrredón": (-34.5780, -58.4960),
    "villa real": (-34.6180, -58.5130),
    "villa riachuelo": (-34.6780, -58.4630),
    "villa santa rita": (-34.6170, -58.4810),
    "villa soldati": (-34.6620, -58.4430),
    "villa urquiza": (-34.5690, -58.4870),
}

# Distance threshold in degrees (~100m) for centroid detection
_CENTROID_THRESHOLD_DEG = 0.001

# Jitter range in degrees (~100m) applied to centroid-level results
_JITTER_RANGE = 0.001


class _LocationIQ(_Nominatim):
    """Nominatim-compatible geocoder pointing to LocationIQ."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # LocationIQ serves API at /v1/search, not /search
        self.api = f"{self.scheme}://{self.domain}/v1/search"
        self.reverse_api = f"{self.scheme}://{self.domain}/v1/reverse"

    def _construct_url(self, base_api, params):
        params["key"] = settings.LOCATIONIQ_API_KEY
        return super()._construct_url(base_api, params)


def _clean_address(address: str) -> str:
    """
    Clean scraped address for better geocoding results.
    Delegates to address.clean_raw_address().
    """
    return clean_raw_address(address)


def _build_street_query(
    street: Optional[str] = None,
    street_number: Optional[str] = None,
    address: Optional[str] = None,
) -> Optional[str]:
    """
    Build a "Calle 1234" string from structured fields or by extracting from address.
    Returns None if no street info can be determined.
    """
    if street:
        # Clean the street name
        clean_street = street.strip()
        if street_number:
            return f"{clean_street} {street_number.strip()}"
        return clean_street

    # Try to extract street + number from raw address using regex
    if address:
        cleaned = _clean_address(address)
        # Match patterns like "Superi 2900", "Av. Cabildo 1234"
        match = re.match(r'^(.+?)\s+(\d{1,5})\b', cleaned)
        if match:
            return f"{match.group(1).strip()} {match.group(2)}"
        # Return cleaned address if no number found (street-only)
        if cleaned:
            return cleaned

    return None


def _is_in_buenos_aires(lat: float, lng: float) -> bool:
    """Check if coordinates fall within the CABA/GBA bounding box"""
    return (
        BUENOS_AIRES_BOUNDS["lat_min"] <= lat <= BUENOS_AIRES_BOUNDS["lat_max"]
        and BUENOS_AIRES_BOUNDS["lng_min"] <= lng <= BUENOS_AIRES_BOUNDS["lng_max"]
    )


def _is_centroid(lat: float, lng: float) -> Optional[str]:
    """
    Check if coordinates match a known CABA neighborhood centroid.
    Returns the neighborhood name if within ~100m of a centroid, else None.
    """
    for name, (clat, clng) in CABA_CENTROIDS.items():
        if (abs(lat - clat) < _CENTROID_THRESHOLD_DEG
                and abs(lng - clng) < _CENTROID_THRESHOLD_DEG):
            return name
    return None


def _add_jitter(lat: float, lng: float) -> Tuple[float, float]:
    """Add small random offset (±~100m) to avoid marker stacking."""
    jlat = lat + random.uniform(-_JITTER_RANGE, _JITTER_RANGE)
    jlng = lng + random.uniform(-_JITTER_RANGE, _JITTER_RANGE)
    return (jlat, jlng)


def _make_cache_key(
    address: Optional[str],
    street: Optional[str],
    street_number: Optional[str],
    neighborhood: Optional[str],
    city: str,
) -> str:
    """Build a normalized cache key from address components."""
    parts = [
        (address or "").strip().lower(),
        (street or "").strip().lower(),
        (street_number or "").strip().lower(),
        (neighborhood or "").strip().lower(),
        city.strip().lower(),
    ]
    return "|".join(parts)


class GeocodingService:
    """Geocoding service using LocationIQ (Nominatim-compatible API)"""

    def __init__(self):
        self._geocoder = _LocationIQ(
            user_agent="real_estate_inv_ar_gerar_v1",
            timeout=settings.GEOCODING_TIMEOUT,
            domain="us1.locationiq.com",
            scheme="https",
        )
        self._geocode = RateLimiter(
            self._geocoder.geocode,
            min_delay_seconds=1.0,   # LocationIQ free = 2 req/sec
            max_retries=3,
            error_wait_seconds=10.0,
        )
        # Session cache: identical address components -> same coordinates.
        # Avoids calling the geocoder multiple times for the same address and
        # guarantees identical addresses land on the same map point.
        # Call clear_cache() after a batch run.
        self._cache: dict[str, Optional[Tuple[float, float]]] = {}

    def clear_cache(self):
        """Clear the session cache (call after a batch geocoding run)."""
        self._cache.clear()

    def geocode_address(
        self,
        address: Optional[str] = None,
        street: Optional[str] = None,
        street_number: Optional[str] = None,
        neighborhood: Optional[str] = None,
        city: str = "Buenos Aires",
        province: str = "Buenos Aires",
    ) -> Optional[Tuple[float, float]]:
        """
        Geocode an address to (latitude, longitude) using a 6-level cascade:

        1. Structured query: street + number + city (structured params)
        2. Structured query: street + number without city
        3. Free-text: cleaned address + neighborhood + city
        4. Free-text: cleaned address + city
        5. Free-text: neighborhood + city (centroid fallback)
        6. None

        Results are validated against CABA/GBA bounds.
        Centroid-level results get random jitter to avoid marker stacking.
        """
        # Check session cache first — identical addresses get identical coords
        cache_key = _make_cache_key(address, street, street_number, neighborhood, city)
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            if cached:
                logger.info(f"[cache hit] '{address or street}' -> ({cached[0]}, {cached[1]})")
            return cached

        queries: List[dict] = []
        street_str = _build_street_query(street, street_number, address)

        # Level 1: Structured with street + city
        if street_str:
            queries.append({
                "type": "structured",
                "level": 1,
                "params": {
                    "street": street_str,
                    "city": city,
                    "country": "Argentina",
                },
            })

        # Level 2: Structured with street only (city might confuse)
        if street_str:
            queries.append({
                "type": "structured",
                "level": 2,
                "params": {
                    "street": street_str,
                    "state": province or "Buenos Aires",
                    "country": "Argentina",
                },
            })

        # Level 3: Free-text with cleaned address + neighborhood + city
        if address:
            cleaned = _clean_address(address)
            if neighborhood and cleaned:
                queries.append({
                    "type": "free",
                    "level": 3,
                    "query": f"{cleaned}, {neighborhood}, {city}, Argentina",
                })

        # Level 4: Free-text with cleaned address + city
        if address:
            cleaned = _clean_address(address)
            if cleaned:
                queries.append({
                    "type": "free",
                    "level": 4,
                    "query": f"{cleaned}, {city}, Argentina",
                })

        # Level 5: Neighborhood + city (centroid fallback)
        if neighborhood:
            queries.append({
                "type": "free",
                "level": 5,
                "query": f"{neighborhood}, {city}, {province}, Argentina",
            })

        for q in queries:
            try:
                if q["type"] == "structured":
                    location = self._geocode(
                        query=q["params"],
                        country_codes=settings.GEOCODING_COUNTRY_BIAS.lower(),
                    )
                    label = str(q["params"])
                else:
                    location = self._geocode(
                        q["query"],
                        country_codes=settings.GEOCODING_COUNTRY_BIAS.lower(),
                    )
                    label = q["query"]

                if location and _is_in_buenos_aires(location.latitude, location.longitude):
                    lat, lng = location.latitude, location.longitude

                    # Check if result is a neighborhood centroid
                    centroid_name = _is_centroid(lat, lng)
                    if centroid_name:
                        logger.warning(
                            f"[level {q['level']}] Geocoded '{label}' -> centroid of "
                            f"'{centroid_name}' - imprecise (neighborhood-level). Adding jitter."
                        )
                        lat, lng = _add_jitter(lat, lng)
                    else:
                        logger.info(
                            f"[level {q['level']}] Geocoded '{label}' -> ({lat}, {lng})"
                        )

                    result = (lat, lng)
                    self._cache[cache_key] = result
                    return result

                elif location:
                    logger.warning(
                        f"[level {q['level']}] Geocoded '{label}' -> "
                        f"({location.latitude}, {location.longitude}) "
                        f"but OUTSIDE Buenos Aires bounds, skipping"
                    )
            except Exception as e:
                logger.warning(f"[level {q['level']}] Geocoding failed for '{q}': {e}")
                if "429" in str(e):
                    # LocationIQ rate limit — wait and let the next property
                    # try after the inter-property delay in the caller.
                    logger.warning(
                        "LocationIQ 429 rate limit — aborting remaining cascade levels "
                        "for this property. Waiting 5s before continuing."
                    )
                    time.sleep(5)
                    break
                continue

        logger.warning(
            f"Could not geocode: address='{address}', street='{street}', "
            f"street_number='{street_number}', neighborhood='{neighborhood}', city='{city}'"
        )
        self._cache[cache_key] = None
        return None

    @staticmethod
    def make_point(lat: float, lng: float):
        """Create a PostGIS WKBElement from lat/lng"""
        point = Point(lng, lat)  # PostGIS uses (lon, lat)
        return from_shape(point, srid=4326)


# Singleton instance
geocoding_service = GeocodingService()
