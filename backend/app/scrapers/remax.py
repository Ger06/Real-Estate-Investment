"""
Remax Scraper
Extracts property data from www.remax.com.ar
Data is embedded in JSON scripts
"""
import re
import json
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse
from .base import BaseScraper


class RemaxScraper(BaseScraper):
    """Scraper for Remax portal"""

    DOMAIN = "remax.com.ar"
    CDN_BASE_URL = "https://d1acdg20u0pmxj.cloudfront.net/"

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

        data = {
            "source": "remax",
            "title": listing_data.get("title", ""),
            "description": listing_data.get("description", ""),
            "price": self._extract_price(listing_data),
            "currency": self._extract_currency(listing_data),
            "property_type": self._extract_property_type(listing_data),
            "operation_type": self._extract_operation_type(listing_data),
            "location": self._extract_location(listing_data),
            "address": self._extract_address_from_html(),
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

        # Find all script tags
        for script in self.soup.find_all('script'):
            if not script.string:
                continue

            # Look for the script containing property data
            # Remax embeds data in a specific format
            if '"id":' in script.string and '"title":' in script.string and '"photos":' in script.string:
                try:
                    # Parse the JSON
                    data = json.loads(script.string)

                    # Navigate through the nested structure
                    # Format: {"random_key": {"b": {"data": {...}}}}
                    for key in data:
                        if isinstance(data[key], dict) and 'b' in data[key]:
                            if 'data' in data[key]['b']:
                                return data[key]['b']['data']

                except (json.JSONDecodeError, KeyError, TypeError):
                    continue

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
        city = "Buenos Aires"
        province = "Buenos Aires"

        # Try to parse from publicationAddress (JSON)
        address = listing_data.get("publicationAddress", "")

        if address:
            # Remax format is usually: "Street Address, Neighborhood, City"
            parts = [p.strip() for p in address.split(',')]

            if len(parts) >= 2:
                # Last part is usually city
                city = parts[-1]
                # Second to last is neighborhood
                if len(parts) >= 2:
                    neighborhood = parts[-2] if len(parts) == 3 else parts[0]

        # Check if there's a location object with neighborhood info
        if 'neighborhood' in listing_data:
            neighborhood_obj = listing_data['neighborhood']
            if isinstance(neighborhood_obj, dict):
                neighborhood = neighborhood_obj.get('name', neighborhood)

        # Fallback: extract from title or description
        if not neighborhood:
            title = listing_data.get("title", "")
            # Look for "Palermo", "Belgrano", etc.
            import re
            match = re.search(r'(Palermo|Belgrano|Recoleta|Caballito|Villa Crespo|Colegiales|Núñez|Almagro|San Telmo|La Boca)', title, re.IGNORECASE)
            if match:
                neighborhood = match.group(1)

        # Try to extract city from title (e.g., "Capital Federal")
        title = listing_data.get("title", "")
        if "Capital Federal" in title:
            city = "Capital Federal"

        return {
            "neighborhood": neighborhood,
            "city": city,
            "province": province,
        }

    def _extract_address_from_html(self) -> str:
        """Extract address from HTML spans"""
        if not self.soup:
            return ""

        # Look for address in title or h1
        title_elem = self.soup.find('title')
        if title_elem:
            title_text = title_elem.get_text()
            # Extract address from title like: "Departamento en venta 2 ambientes en Santa Rosa 5100, Palermo, Capital Federal"
            match = re.search(r'en ([^,]+,\s*[^,]+,\s*[^-]+)', title_text)
            if match:
                return match.group(1).strip()

        return ""

    def _extract_images(self, listing_data: Dict[str, Any]) -> List[str]:
        """Extract image URLs"""
        images = []

        photos = listing_data.get("photos", [])

        for photo in photos:
            if isinstance(photo, dict):
                # Photos are stored as relative paths
                photo_path = photo.get("value", "")

                if photo_path:
                    # Convert to absolute URL using CDN
                    full_url = f"{self.CDN_BASE_URL}{photo_path}"
                    images.append(full_url)

        return images[:20]  # Limit to 20 images

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
