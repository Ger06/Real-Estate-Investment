"""
Remax Scraper
Extracts property data from www.remax.com.ar
Data is embedded in JSON scripts
"""
import re
import json
import logging
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse
from .base import BaseScraper

logger = logging.getLogger(__name__)


class RemaxScraper(BaseScraper):
    """Scraper for Remax portal"""

    DOMAIN = "remax.com.ar"
    CDN_BASE_URL = "https://d1acdg20u0pmxj.cloudfront.net/"
    IMAGE_RESOLUTION = "1080xAUTO"
    IMAGE_EXTENSION = ".jpg"

    def validate_url(self) -> bool:
        """Check if URL is from Remax"""
        parsed = urlparse(self.url)
        return self.DOMAIN in parsed.netloc

    def extract_data(self) -> Dict[str, Any]:
        """Extract all property data from Remax"""
        if not self.soup:
            raise ValueError("HTML not parsed. Call fetch_page() first.")

        # Extract data from embedded JSON
        listing_data = self._extract_json_data()

        if not listing_data:
            raise ValueError("Could not find property data in page")

        # Extract address info (returns dict with full_address, street, street_number)
        address_info = self._extract_address_from_html()

        # Also check JSON for address data
        json_address = listing_data.get("publicationAddress", "")
        if not address_info['full_address'] and json_address:
            address_info['full_address'] = json_address
            self._parse_street_and_number(address_info)

        data = {
            "source": "remax",
            "title": listing_data.get("title", ""),
            "description": listing_data.get("description", ""),
            "price": self._extract_price(listing_data),
            "currency": self._extract_currency(listing_data),
            "property_type": self._extract_property_type(listing_data),
            "operation_type": self._extract_operation_type(listing_data),
            "location": self._extract_location(listing_data),
            "address": address_info['full_address'],
            "street": address_info['street'],
            "street_number": address_info['street_number'],
            "images": self._extract_images(listing_data),
            "features": self._extract_features(listing_data),
            "contact": self._extract_contact(listing_data),
            "source_id": listing_data.get("id", ""),
            "status": self._extract_status(listing_data),
        }

        return data

    def _extract_json_data(self) -> Optional[Dict[str, Any]]:
        """Extract property data from embedded JSON script"""
        if not self.soup:
            return None

        # Priority 0: Angular ng-state script (most reliable for Remax SPA)
        ng_state = self.soup.find('script', id='ng-state', type='application/json')
        if ng_state and ng_state.string:
            try:
                data = json.loads(ng_state.string)
                result = self._find_listing_in_json(data)
                if result:
                    logger.info("[remax] Found listing data in ng-state script")
                    return result
            except (json.JSONDecodeError, KeyError, TypeError):
                logger.debug("[remax] Failed to parse ng-state script")

        # Find all script tags
        for script in self.soup.find_all('script'):
            if not script.string:
                continue

            script_text = script.string

            # Look for the script containing property data
            # Remax embeds data in a specific format
            if '"id":' in script_text and '"title":' in script_text:
                try:
                    # Parse the JSON
                    data = json.loads(script_text)
                    result = self._find_listing_in_json(data)
                    if result:
                        return result

                except (json.JSONDecodeError, KeyError, TypeError):
                    continue

        # Fallback: Try to extract from __NEXT_DATA__ script
        next_data_script = self.soup.find('script', id='__NEXT_DATA__')
        if next_data_script and next_data_script.string:
            try:
                data = json.loads(next_data_script.string)
                page_props = data.get('props', {}).get('pageProps', {})
                if 'listing' in page_props:
                    return page_props['listing']
                if 'property' in page_props:
                    return page_props['property']
                # Return entire pageProps if it has listing-like data
                if 'title' in page_props and 'price' in page_props:
                    return page_props
            except (json.JSONDecodeError, KeyError, TypeError):
                pass

        return None

    def _find_listing_in_json(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Search for listing data within a parsed JSON structure."""
        if not isinstance(data, dict):
            return None

        # Pattern 1: {"random_key": {"b": {"data": {...}}}}
        for key in data:
            if isinstance(data[key], dict):
                if 'b' in data[key] and isinstance(data[key]['b'], dict):
                    if 'data' in data[key]['b']:
                        return data[key]['b']['data']

        # Pattern 2: Direct listing data at root
        if 'title' in data and ('price' in data or 'photos' in data):
            return data

        # Pattern 3: Nested under 'listing' or 'property'
        for nested_key in ['listing', 'property', 'data', 'result']:
            if nested_key in data and isinstance(data[nested_key], dict):
                nested = data[nested_key]
                if 'title' in nested:
                    return nested

        # Pattern 4: Search in nested pageProps (Next.js)
        if 'props' in data and isinstance(data['props'], dict):
            page_props = data['props'].get('pageProps', {})
            if 'listing' in page_props:
                return page_props['listing']
            if 'property' in page_props:
                return page_props['property']

        return None

    def _extract_price(self, listing_data: Dict[str, Any]) -> Optional[float]:
        """Extract price from listing data"""
        price = listing_data.get("price")
        if price:
            try:
                return float(price)
            except (ValueError, TypeError):
                return None
        return None

    def _extract_currency(self, listing_data: Dict[str, Any]) -> str:
        """Extract currency from listing data"""
        currency_obj = listing_data.get("currency", {})

        if isinstance(currency_obj, dict):
            currency_value = currency_obj.get("value", "")
            if currency_value:
                return currency_value.upper()

        # Fallback: check operation type
        operation_type = listing_data.get("operationType", {})
        if isinstance(operation_type, dict):
            operation_name = operation_type.get("name", "").lower()
            if "alquiler" in operation_name:
                return "ARS"

        return "USD"

    def _extract_property_type(self, listing_data: Dict[str, Any]) -> str:
        """Extract property type"""
        # Check propertyType field
        property_type_obj = listing_data.get("propertyType", {})

        if isinstance(property_type_obj, dict):
            type_name = property_type_obj.get("name", "").lower()
        else:
            type_name = ""

        # Also check title
        title = listing_data.get("title", "").lower()

        combined = f"{type_name} {title}"

        if 'departamento' in combined or 'depto' in combined:
            return "departamento"
        elif 'casa' in combined:
            return "casa"
        elif 'ph' in combined:
            return "ph"
        elif 'terreno' in combined or 'lote' in combined:
            return "terreno"
        elif 'local' in combined or 'comercial' in combined:
            return "local"
        elif 'oficina' in combined:
            return "oficina"

        return "casa"

    def _extract_operation_type(self, listing_data: Dict[str, Any]) -> str:
        """Extract operation type"""
        # Check operationType field
        operation_obj = listing_data.get("operationType", {})

        if isinstance(operation_obj, dict):
            operation_name = operation_obj.get("name", "").lower()

            if "alquiler temporal" in operation_name or "temporal" in operation_name:
                return "alquiler_temporal"
            elif "alquiler" in operation_name:
                return "alquiler"
            elif "venta" in operation_name:
                return "venta"

        # Fallback: check URL
        url_lower = self.url.lower()
        if '/alquiler' in url_lower:
            return "alquiler"
        elif '/venta' in url_lower:
            return "venta"

        # Fallback: check title
        title = listing_data.get("title", "").lower()
        if "alquiler" in title:
            return "alquiler"
        elif "venta" in title:
            return "venta"

        return "venta"

    def _extract_location(self, listing_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract location data"""
        neighborhood = ""
        city = ""
        province = "Buenos Aires"

        # Debug: log what we're working with
        logger.info(f"[remax] _extract_location - title: {listing_data.get('title', '')[:80]}")
        logger.info(f"[remax] _extract_location - publicationAddress: {listing_data.get('publicationAddress', '')}")
        logger.info(f"[remax] _extract_location - neighborhood field: {listing_data.get('neighborhood', 'NOT FOUND')}")
        logger.info(f"[remax] _extract_location - city field: {listing_data.get('city', 'NOT FOUND')}")

        # Known neighborhoods to look for (used for validation and extraction)
        known_neighborhoods = [
            'Palermo', 'Belgrano', 'Recoleta', 'Caballito', 'Villa Crespo',
            'Colegiales', 'Núñez', 'Nunez', 'Almagro', 'San Telmo', 'La Boca',
            'Villa Urquiza', 'Saavedra', 'Coghlan', 'Chacarita', 'Villa Devoto',
            'Flores', 'Floresta', 'Boedo', 'Barracas', 'Puerto Madero',
            'Retiro', 'San Nicolás', 'San Nicolas', 'Monserrat', 'Constitución',
            'Parque Patricios', 'Parque Chacabuco', 'Villa del Parque',
            'Villa Pueyrredón', 'Villa Pueyrredon', 'Liniers', 'Mataderos',
            'Versalles', 'Monte Castro', 'Villa Luro', 'Velez Sarsfield',
            'Villa Real', 'Villa Santa Rita', 'Agronomía', 'Villa Ortúzar',
            'Parque Chas', 'Villa General Mitre', 'Paternal', 'Villa Soldati',
            'Villa Lugano', 'Nueva Pompeya', 'Parque Avellaneda', 'Mataderos',
        ]
        known_neighborhoods_lower = [nb.lower() for nb in known_neighborhoods]

        # Generic city/province names that should NOT be treated as neighborhoods
        generic_locations = [
            'buenos aires', 'capital federal', 'caba', 'argentina',
            'gran buenos aires', 'gba', 'provincia de buenos aires',
        ]

        # Priority 1: Check if there's a location/neighborhood object in JSON
        if 'neighborhood' in listing_data:
            neighborhood_obj = listing_data['neighborhood']
            if isinstance(neighborhood_obj, dict):
                neighborhood = neighborhood_obj.get('name', '')
            elif isinstance(neighborhood_obj, str):
                neighborhood = neighborhood_obj

        if 'city' in listing_data:
            city_obj = listing_data['city']
            if isinstance(city_obj, dict):
                city = city_obj.get('name', '')
            elif isinstance(city_obj, str):
                city = city_obj

        if 'state' in listing_data or 'province' in listing_data:
            prov_obj = listing_data.get('state') or listing_data.get('province')
            if isinstance(prov_obj, dict):
                province = prov_obj.get('name', province)
            elif isinstance(prov_obj, str):
                province = prov_obj

        # Also check for nested 'location' object (some Remax JSON structures)
        if 'location' in listing_data and isinstance(listing_data['location'], dict):
            loc = listing_data['location']
            if not neighborhood and loc.get('neighborhood'):
                neighborhood = loc['neighborhood']
            if not city and loc.get('city'):
                city = loc['city']
            if loc.get('state') or loc.get('province'):
                province = loc.get('state') or loc.get('province') or province

        # Priority 2: Parse from publicationAddress
        # Remax format: "Street 1234, Neighborhood, City" or "Neighborhood, City"
        if not neighborhood or not city:
            address = listing_data.get("publicationAddress", "")
            if address:
                parts = [p.strip() for p in address.split(',') if p.strip()]

                if len(parts) == 1:
                    part_lower = parts[0].lower()
                    # Only set as city if it looks like a city, not a neighborhood
                    if part_lower in generic_locations:
                        if not city:
                            city = parts[0]
                    else:
                        # Could be a neighborhood
                        if not neighborhood and part_lower not in generic_locations:
                            neighborhood = parts[0]
                elif len(parts) == 2:
                    # "Neighborhood, City" or "Street, City"
                    part0_lower = parts[0].lower()
                    part1_lower = parts[1].lower()

                    # If first part is generic (Buenos Aires), don't use as neighborhood
                    if part0_lower not in generic_locations and not neighborhood:
                        neighborhood = parts[0]
                    if not city:
                        city = parts[1]
                elif len(parts) >= 3:
                    # "Street, Neighborhood, City"
                    part_m2_lower = parts[-2].lower()
                    if part_m2_lower not in generic_locations and not neighborhood:
                        neighborhood = parts[-2]  # Second to last
                    if not city:
                        city = parts[-1]  # Last

        # Priority 3: ALWAYS extract from title - this is the most reliable for Remax
        # Even if we have a neighborhood, check if it's generic and override with title
        title = listing_data.get("title", "")
        title_lower = title.lower()

        # Check if current neighborhood is generic (like "Buenos Aires")
        neighborhood_is_generic = neighborhood.lower() in generic_locations if neighborhood else True

        # Extract neighborhood from title if we don't have one or current one is generic
        if neighborhood_is_generic:
            for nb in known_neighborhoods:
                if nb.lower() in title_lower:
                    neighborhood = nb
                    break

        # Extract city from title
        if not city or city.lower() in generic_locations:
            if "capital federal" in title_lower or "caba" in title_lower:
                city = "Capital Federal"

        # Determine province based on city
        if city:
            city_lower = city.lower()
            if city_lower in ['capital federal', 'caba', 'ciudad de buenos aires', 'ciudad autónoma de buenos aires']:
                province = "Capital Federal"
                city = "Capital Federal"  # Normalize
            elif city_lower == 'buenos aires':
                # "Buenos Aires" as city usually means Capital Federal
                city = "Capital Federal"
                province = "Capital Federal"

        # Final defaults
        if not city:
            city = "Capital Federal"  # Default to Capital Federal for Remax (most listings are there)

        # Debug: log the final result
        logger.info(f"[remax] _extract_location - RESULT: neighborhood='{neighborhood}', city='{city}', province='{province}'")

        return {
            "neighborhood": neighborhood,
            "city": city,
            "province": province,
        }

    def _extract_address_from_html(self) -> Dict[str, str]:
        """
        Extract address from HTML.
        Returns dict with 'full_address', 'street', 'street_number'.
        """
        result = {
            'full_address': '',
            'street': '',
            'street_number': '',
        }

        if not self.soup:
            return result

        # Look for address in title or h1
        title_elem = self.soup.find('title')
        if title_elem:
            title_text = title_elem.get_text()
            # Extract address from title like: "Departamento en venta 2 ambientes en Santa Rosa 5100, Palermo, Capital Federal"
            # Or: "VENTA PH 4 AMBIENTES COGHLAN QUINCHO Y TERRAZA" - no address in title
            match = re.search(r'en ([^,]+,\s*[^,]+,\s*[^-]+)', title_text)
            if match:
                result['full_address'] = match.group(1).strip()

        # Try to find address in specific HTML elements
        address_selectors = [
            '.property-address',
            '.address',
            '[class*="address"]',
            '[class*="ubicacion"]',
            '[class*="location"]',
            'span[itemprop="streetAddress"]',
        ]

        for selector in address_selectors:
            elem = self.soup.select_one(selector)
            if elem:
                addr_text = elem.get_text(strip=True)
                if addr_text and len(addr_text) > 5:
                    result['full_address'] = addr_text
                    break

        # Try to extract street and number from full address
        if result['full_address']:
            self._parse_street_and_number(result)

        return result

    def _parse_street_and_number(self, result: Dict[str, str]) -> None:
        """Parse street name and number from full address string."""
        full_addr = result['full_address']
        if not full_addr:
            return

        # Take first part before comma (usually street + number)
        first_part = full_addr.split(',')[0].strip()

        # Pattern: "Street Name 1234" or "Av. Street Name 1234"
        # Match: everything before a number at the end
        match = re.match(r'^(.+?)\s+(\d+)\s*$', first_part)
        if match:
            result['street'] = match.group(1).strip()
            result['street_number'] = match.group(2)
        else:
            # No number found, entire first part is street
            result['street'] = first_part

    def _build_image_url(self, raw_path: str) -> Optional[str]:
        """
        Build a proper CDN image URL from a raw path.

        Remax rawValue format: "listings/{LISTING_UUID}/{IMAGE_UUID}"
        CDN URL format: "https://d1acdg20u0pmxj.cloudfront.net/listings/{LISTING_UUID}/{RESOLUTION}/{IMAGE_UUID}.jpg"

        Supported CDN resolutions: 1080xAUTO (.jpg), 360x200 (.jpg/.webp).
        Other resolutions (1024x1024, etc.) return 403.
        """
        if not raw_path:
            return None

        # Already a full URL
        if raw_path.startswith("http"):
            return raw_path

        # Strip leading slash
        raw_path = raw_path.lstrip("/")

        # Expected: "listings/{LISTING_UUID}/{IMAGE_UUID}"
        parts = raw_path.split("/")
        if len(parts) == 3 and parts[0] == "listings":
            listing_uuid = parts[1]
            image_uuid = parts[2]
            # Remove any existing extension
            image_uuid = re.sub(r'\.\w+$', '', image_uuid)
            url = (
                f"{self.CDN_BASE_URL}listings/{listing_uuid}/"
                f"{self.IMAGE_RESOLUTION}/{image_uuid}{self.IMAGE_EXTENSION}"
            )
            return url

        # If it already has a resolution segment (4 parts): listings/UUID/RES/UUID.ext
        if len(parts) == 4 and parts[0] == "listings":
            # Upgrade resolution if needed
            listing_uuid = parts[1]
            image_uuid = re.sub(r'\.\w+$', '', parts[3])
            url = (
                f"{self.CDN_BASE_URL}listings/{listing_uuid}/"
                f"{self.IMAGE_RESOLUTION}/{image_uuid}{self.IMAGE_EXTENSION}"
            )
            return url

        # Unknown format - use as-is with CDN base
        return f"{self.CDN_BASE_URL}{raw_path}"

    def _is_valid_property_image(self, url: str) -> bool:
        """Filter out non-property images (SVGs, icons, logos, agent photos)."""
        url_lower = url.lower()
        exclude_patterns = [
            '.svg', '/icons/', '/logo', '/agent/', '/agents/',
            '/avatar/', '/favicon', '/brand/', '/sprite',
            'placeholder', 'default-photo', '/assets/',
        ]
        return not any(pattern in url_lower for pattern in exclude_patterns)

    def _extract_images(self, listing_data: Dict[str, Any]) -> List[str]:
        """
        Extract image URLs using multiple strategies.

        Strategy 1: JSON photos array (rawValue, then value fallback)
        Strategy 2: HTML <img> tags filtered by CDN domain
        Strategy 3: og:image meta tag as last resort
        """
        images: List[str] = []
        seen: set = set()

        def _add_image(url: str) -> None:
            if url and url not in seen and self._is_valid_property_image(url):
                seen.add(url)
                images.append(url)

        # Strategy 1: JSON photos array
        photos = listing_data.get("photos", [])
        if photos:
            for photo in photos:
                if isinstance(photo, dict):
                    # Try rawValue first (actual Remax key)
                    raw_path = photo.get("rawValue", "") or photo.get("value", "")
                    if raw_path:
                        full_url = self._build_image_url(raw_path)
                        if full_url:
                            _add_image(full_url)
                elif isinstance(photo, str) and photo:
                    full_url = self._build_image_url(photo)
                    if full_url:
                        _add_image(full_url)

            if images:
                logger.info(f"[remax] Strategy 1 (JSON photos): found {len(images)} images")

        # Strategy 2: HTML <img> tags with CDN domain
        if not images and self.soup:
            cdn_domain = "d1acdg20u0pmxj.cloudfront.net"
            for img in self.soup.find_all("img"):
                src = img.get("src", "") or img.get("data-src", "")
                if cdn_domain in src and "/listings/" in src:
                    # Upgrade resolution in URL if present
                    upgraded = self._upgrade_image_resolution(src)
                    _add_image(upgraded)

            if images:
                logger.info(f"[remax] Strategy 2 (HTML img tags): found {len(images)} images")

        # Strategy 3: og:image meta tag
        if not images and self.soup:
            og_image = self.soup.find("meta", property="og:image")
            if og_image:
                content = og_image.get("content", "")
                if content:
                    _add_image(content)
                    logger.info("[remax] Strategy 3 (og:image): found 1 image")

        if not images:
            logger.warning("[remax] No images found with any strategy")

        return images[:20]

    def _upgrade_image_resolution(self, url: str) -> str:
        """
        Upgrade an existing CDN image URL to the configured resolution.
        Replaces resolution segments like '312x312' or '640x480' with IMAGE_RESOLUTION.
        """
        return re.sub(
            r'/\d+x\d+/',
            f'/{self.IMAGE_RESOLUTION}/',
            url,
            count=1,
        )

    def _extract_features(self, listing_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract property features"""
        features = {
            "bedrooms": listing_data.get("bedrooms"),
            "bathrooms": listing_data.get("bathrooms"),
            "parking_spaces": listing_data.get("parkingSpaces"),
            "covered_area": self._get_surface_value(listing_data, "covered"),
            "total_area": self._get_surface_value(listing_data, "total"),
        }

        # If surface data not in JSON, extract from HTML spans
        if not features["covered_area"] or not features["total_area"]:
            html_surfaces = self._extract_surface_from_html()
            if not features["covered_area"]:
                features["covered_area"] = html_surfaces.get("covered")
            if not features["total_area"]:
                features["total_area"] = html_surfaces.get("total")

        # Extract amenities from description or features list
        amenities = []
        description = listing_data.get("description", "").lower()

        amenity_keywords = [
            'pileta', 'piscina', 'gimnasio', 'seguridad', 'parrilla',
            'balcón', 'terraza', 'jardín', 'quincho', 'sum', 'laundry'
        ]

        for keyword in amenity_keywords:
            if keyword in description:
                amenities.append(keyword)

        # Check if there's a features list
        if 'features' in listing_data and isinstance(listing_data['features'], list):
            for feature in listing_data['features']:
                if isinstance(feature, dict):
                    feature_name = feature.get('value', '').lower()
                    if feature_name and feature_name not in amenities:
                        # Only add amenities, not services
                        category = feature.get('category', '')
                        if category == 'amenities':
                            amenities.append(feature_name)

        features['amenities'] = amenities

        return features

    def _extract_surface_from_html(self) -> Dict[str, Optional[float]]:
        """Extract surface areas from HTML spans"""
        surfaces = {"covered": None, "total": None}

        if not self.soup:
            return surfaces

        # Find spans with class 'feature-detail'
        for span in self.soup.find_all('span', class_='feature-detail'):
            text = span.get_text(strip=True).lower()

            # Extract surface values
            # Format: "superficie total: 28.26 m²"
            if 'superficie total' in text:
                match = re.search(r'(\d+(?:\.\d+)?)', text)
                if match:
                    surfaces["total"] = float(match.group(1))

            elif 'superficie cubierta' in text:
                match = re.search(r'(\d+(?:\.\d+)?)', text)
                if match:
                    surfaces["covered"] = float(match.group(1))

        return surfaces

    def _get_surface_value(self, listing_data: Dict[str, Any], surface_type: str) -> Optional[float]:
        """Extract surface area value"""
        # Surface fields in Remax: surfaceTotal, surfaceCovered, surfaceSemiCovered
        if surface_type == "total":
            value = listing_data.get("surfaceTotal")
        elif surface_type == "covered":
            value = listing_data.get("surfaceCovered")
        else:
            return None

        if value:
            try:
                return float(value)
            except (ValueError, TypeError):
                return None

        return None

    def _extract_contact(self, listing_data: Dict[str, Any]) -> Dict[str, str]:
        """Extract contact information"""
        contact = {
            "real_estate_agency": "",
            "phone": "",
            "email": "",
        }

        # Remax agent/office info
        if 'office' in listing_data:
            office = listing_data['office']
            if isinstance(office, dict):
                contact['real_estate_agency'] = office.get('name', '')
                contact['phone'] = office.get('phone', '')
                contact['email'] = office.get('email', '')

        # Check for agent info
        if 'agent' in listing_data:
            agent = listing_data['agent']
            if isinstance(agent, dict):
                if not contact['real_estate_agency']:
                    contact['real_estate_agency'] = agent.get('name', '')
                if not contact['phone']:
                    contact['phone'] = agent.get('phone', '')
                if not contact['email']:
                    contact['email'] = agent.get('email', '')

        return contact

    def _extract_source_id(self) -> str:
        """Extract property ID from URL or data"""
        # Remax uses slug-based URLs
        # Extract from URL path: /listings/slug-here
        parts = self.url.rstrip('/').split('/')
        if parts:
            return parts[-1]

        return ""

    def _extract_status(self, listing_data: Dict[str, Any]) -> str:
        """
        Extract property status (active, sold, rented, reserved)
        Checks JSON data and page text
        """
        # Check JSON data for status field
        if listing_data.get("status"):
            status = listing_data.get("status", "").lower()
            if "sold" in status or "vendid" in status:
                return "sold"
            if "rent" in status or "alquil" in status:
                return "rented"
            if "reserv" in status:
                return "reserved"

        # Check title
        title = listing_data.get("title", "").lower()

        # Use partial matching to catch words even when joined together
        if "vendid" in title or "sold" in title:
            return "sold"
        if "alquil" in title or "rented" in title:
            return "rented"
        if "reservad" in title or "reserved" in title:
            return "reserved"

        # Check page text (check more content, not just 500 chars)
        if self.soup:
            page_text = self.soup.get_text().lower()

            # Check first 1000 characters for status indicators
            text_snippet = page_text[:1000]

            # Priority 1: Check for combined status patterns (more specific)
            # These patterns are more reliable than single keywords
            if "ventareservad" in text_snippet or "saledreserved" in text_snippet:
                return "reserved"
            if "ventavendid" in text_snippet or "salesold" in text_snippet:
                return "sold"
            if "alquileralquilad" in text_snippet or "rentrented" in text_snippet:
                return "rented"

            # Priority 2: Check for status badges/indicators in specific areas
            # Look for property-specific sections, not navigation menus
            property_section = page_text[400:1000]  # Skip navigation/header

            if "reservad" in property_section or "reserved" in property_section:
                return "reserved"
            if "vendid" in property_section or "sold" in property_section:
                return "sold"
            if "alquilad" in property_section or "rented" in property_section:  # More specific than "alquil"
                return "rented"

        # Default to active
        return "active"
