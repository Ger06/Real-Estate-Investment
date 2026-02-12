"""
Address Normalization Service

Cleans and normalizes address fields before saving to the database.
Extracts street/street_number from raw address strings, detects neighborhoods,
and normalizes city names for consistent geocoding results.
"""
import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# CABA neighborhood names for cleaning addresses and detection
CABA_NEIGHBORHOODS = [
    "Agronomía", "Almagro", "Balvanera", "Barracas", "Belgrano",
    "Boedo", "Caballito", "Chacarita", "Coghlan", "Colegiales",
    "Constitución", "Flores", "Floresta", "La Boca", "La Paternal",
    "Liniers", "Mataderos", "Monte Castro", "Monserrat", "Nueva Pompeya",
    "Núñez", "Palermo", "Parque Avellaneda", "Parque Chacabuco",
    "Parque Chas", "Parque Patricios", "Puerto Madero", "Recoleta",
    "Retiro", "Saavedra", "San Cristóbal", "San Nicolás", "San Telmo",
    "Vélez Sarsfield", "Versalles", "Villa Crespo", "Villa del Parque",
    "Villa Devoto", "Villa General Mitre", "Villa Lugano", "Villa Luro",
    "Villa Ortúzar", "Villa Pueyrredón", "Villa Real", "Villa Riachuelo",
    "Villa Santa Rita", "Villa Soldati", "Villa Urquiza",
]

# Case-insensitive regex pattern for neighborhood detection/removal
_NEIGHBORHOOD_PATTERN = re.compile(
    r'\b(' + '|'.join(re.escape(n) for n in CABA_NEIGHBORHOODS) + r')\b',
    re.IGNORECASE,
)

# City name aliases -> canonical form
_CITY_ALIASES = {
    "caba": "Capital Federal",
    "ciudad de buenos aires": "Capital Federal",
    "ciudad autónoma de buenos aires": "Capital Federal",
    "c.a.b.a.": "Capital Federal",
    "c.a.b.a": "Capital Federal",
    "capital federal": "Capital Federal",
    "buenos aires": "Buenos Aires",
}


def clean_raw_address(address: str) -> str:
    """
    Clean a scraped address string for geocoding/storage.
    Removes noise like 'al', 'PB', 'Piso X', 'UF X', neighborhood names, etc.
    """
    cleaned = address.strip()

    # Remove floor/unit info: "Piso 0", "PB", "UF 1", "1°", "Dto A"
    cleaned = re.sub(r',?\s*(Piso|piso)\s*\d*', '', cleaned)
    cleaned = re.sub(r'\s+PB\b', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r',?\s*UF\s*\d+', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\s+\d+°.*$', '', cleaned)
    cleaned = re.sub(r',?\s*Dto\.?\s*\w*$', '', cleaned, flags=re.IGNORECASE)

    # Remove "Sin Número" / "Sn" / "S/N" variants
    cleaned = re.sub(r'\s+(S/?N|Sn|sin\s*n[úu]mero)\b', '', cleaned, flags=re.IGNORECASE)

    # "Superí al 2500" -> "Superí 2500"
    cleaned = re.sub(r'\s+al\s+(\d)', r' \1', cleaned, flags=re.IGNORECASE)

    # Remove "entre X y Y" patterns
    cleaned = re.sub(r'\s+entre\s+.*$', '', cleaned, flags=re.IGNORECASE)

    # Remove "e/" (entre) patterns: "Rivera e/ Conesa y Av. Crámer"
    cleaned = re.sub(r'\s+e/\s*.*$', '', cleaned)

    # Remove "esq." / "esquina" patterns
    cleaned = re.sub(r'\s+(esq\.?|esquina)\s+.*$', '', cleaned, flags=re.IGNORECASE)

    # Remove trailing CABA/Buenos Aires labels
    cleaned = re.sub(
        r',?\s*(Caba|CABA|Capital Federal|Ciudad de Buenos Aires|Buenos Aires)\s*$', '',
        cleaned, flags=re.IGNORECASE,
    )

    # Remove known neighborhood names from the address string
    cleaned = _NEIGHBORHOOD_PATTERN.sub('', cleaned)

    # Remove double spaces and trailing commas
    cleaned = re.sub(r',\s*,', ',', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    cleaned = cleaned.strip(',').strip()

    return cleaned


def _parse_street_and_number(cleaned_address: str) -> tuple:
    """
    Extract (street, street_number) from a cleaned address string.
    Returns (street, number) or (None, None) if no pattern matches.
    """
    if not cleaned_address:
        return None, None

    # Match patterns like "Superi 2900", "Av. Cabildo 1234", "Dr. Tomás M. de Anchorena 1432"
    match = re.match(r'^(.+?)\s+(\d{1,5})\b', cleaned_address)
    if match:
        return match.group(1).strip(), match.group(2)

    # No number found — return street name only
    return cleaned_address, None


def _detect_neighborhood(address: str) -> Optional[str]:
    """
    Detect a CABA neighborhood name within an address string.
    Returns the canonical (properly cased) neighborhood name, or None.
    """
    if not address:
        return None

    match = _NEIGHBORHOOD_PATTERN.search(address)
    if match:
        matched_text = match.group(1).lower()
        # Return the canonical (properly cased) version
        for canonical in CABA_NEIGHBORHOODS:
            if canonical.lower() == matched_text:
                return canonical
        return match.group(1)  # fallback to matched text
    return None


def _normalize_city(city: Optional[str]) -> Optional[str]:
    """Normalize city name to canonical form."""
    if not city:
        return city
    key = city.strip().lower()
    return _CITY_ALIASES.get(key, city.strip())


def normalize_address_fields(
    address: Optional[str] = None,
    street: Optional[str] = None,
    street_number: Optional[str] = None,
    neighborhood: Optional[str] = None,
    city: Optional[str] = None,
    province: Optional[str] = None,
) -> dict:
    """
    Normalize address fields before saving to the database.

    Pipeline:
    1. Clean raw address (remove noise like "al", "PB", "UF X", etc.)
    2. Parse street + street_number from cleaned address (if not already provided)
    3. Detect neighborhood from raw address (if not already provided)
    4. Normalize city name
    5. Return dict with all 6 cleaned fields

    Args:
        address: Raw address string from scraper
        street: Street name (may be None from card-based imports)
        street_number: Street number (may be None)
        neighborhood: Neighborhood name (may be None)
        city: City name
        province: Province name

    Returns:
        Dict with keys: address, street, street_number, neighborhood, city, province
    """
    cleaned_address = None

    # Step 1: Clean the raw address
    if address:
        cleaned_address = clean_raw_address(address)

    # Step 2: Parse street + street_number if not provided by the scraper
    if not street and cleaned_address:
        parsed_street, parsed_number = _parse_street_and_number(cleaned_address)
        if parsed_street:
            street = parsed_street
        if parsed_number and not street_number:
            street_number = parsed_number

    # Step 3: Detect neighborhood from raw address if not provided
    if not neighborhood and address:
        neighborhood = _detect_neighborhood(address)

    # Step 4: Normalize city name
    city = _normalize_city(city)
    province = _normalize_city(province)  # also normalize province

    return {
        'address': cleaned_address or address,
        'street': street,
        'street_number': street_number,
        'neighborhood': neighborhood,
        'city': city,
        'province': province,
    }
