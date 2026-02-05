"""
Argenprop Scraper
Extracts property data from www.argenprop.com.ar
"""
import re
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse, urljoin
from .base import BaseScraper
from .utils import clean_price as _clean_price


class ArgenpropScraper(BaseScraper):
    """Scraper for Argenprop portal"""

    DOMAIN = "argenprop.com"

    def validate_url(self) -> bool:
        """Check if URL is from Argenprop"""
        parsed = urlparse(self.url)
        return self.DOMAIN in parsed.netloc

    def extract_data(self) -> Dict[str, Any]:
        """Extract all property data from Argenprop"""
        if not self.soup:
            raise ValueError("HTML not parsed. Call fetch_page() first.")

        # Extract address details
        address_info = self._extract_address_details()

        data = {
            "source": "argenprop",
            "title": self._extract_title(),
            "description": self._extract_description(),
            "price": self._extract_price(),
            "currency": self._extract_currency(),
            "property_type": self._extract_property_type(),
            "operation_type": self._extract_operation_type(),
            "location": self._extract_location(),
            "address": address_info.get('full_address', ''),
            "street": address_info.get('street', ''),
            "street_number": address_info.get('street_number', ''),
            "images": self._extract_images(),
            "features": self._extract_features(),
            "contact": self._extract_contact(),
            "source_id": self._extract_source_id(),
            "status": self._extract_status(),
        }

        return data

    def _extract_title(self) -> str:
        """Extract property title"""
        # Try multiple selectors
        selectors = [
            'h1.property-title',
            'h1[class*="title"]',
            'h1',
            '.title-property',
        ]

        for selector in selectors:
            title = self.extract_text(selector)
            if title:
                return title

        return "Propiedad sin título"

    def _extract_description(self) -> str:
        """Extract property description"""
        selectors = [
            '.property-description',
            '[class*="description"]',
            '.description',
            '#description',
        ]

        for selector in selectors:
            desc = self.extract_text(selector)
            if desc and len(desc) > 50:  # Validate it's actual description
                return desc

        return ""

    def _extract_price(self) -> Optional[float]:
        """Extract price as float"""
        selectors = [
            '.price',
            '[class*="price"]',
            '.property-price',
            '[data-price]',
        ]

        price_text = ""
        for selector in selectors:
            price_text = self.extract_text(selector)
            if price_text:
                break

        price_amount, _ = _clean_price(price_text)
        return price_amount

    def _extract_currency(self) -> str:
        """Extract currency (USD or ARS)"""
        selectors = [
            '.price',
            '[class*="price"]',
            '.currency',
        ]

        for selector in selectors:
            text = self.extract_text(selector)
            if 'USD' in text or 'U$S' in text or 'dólar' in text.lower():
                return "USD"
            if 'ARS' in text or '$' in text or 'peso' in text.lower():
                return "ARS"

        # Default to USD for Argentina
        return "USD"

    def _extract_property_type_from_url(self) -> Optional[str]:
        """Extract property type from URL path (most reliable)"""
        url_lower = self.url.lower()

        # Argenprop URLs: /ph-en-venta/, /departamento-en-venta/, etc.
        if '/ph-' in url_lower or '/ph/' in url_lower:
            return "ph"
        elif '/departamento' in url_lower or '/depto' in url_lower:
            return "departamento"
        elif '/casa' in url_lower:
            return "casa"
        elif '/terreno' in url_lower or '/lote' in url_lower:
            return "terreno"
        elif '/local' in url_lower:
            return "local"
        elif '/oficina' in url_lower:
            return "oficina"
        elif '/cochera' in url_lower or '/garage' in url_lower:
            return "cochera"

        return None

    def _extract_property_type(self) -> str:
        """Extract property type"""
        # Priority 1: URL path (most reliable)
        url_type = self._extract_property_type_from_url()
        if url_type:
            return url_type

        # Priority 2: Text mining (check specific types first)
        title = self._extract_title().lower()
        desc = self._extract_description().lower()
        combined = f"{title} {desc}"

        # Check PH first (more specific than departamento)
        if ' ph ' in combined or combined.startswith('ph ') or 'propiedad horizontal' in combined:
            return "ph"
        elif 'departamento' in combined or 'depto' in combined:
            return "departamento"
        elif 'casa' in combined:
            return "casa"
        elif 'terreno' in combined or 'lote' in combined:
            return "terreno"
        elif 'local' in combined or 'comercial' in combined:
            return "local"
        elif 'oficina' in combined:
            return "oficina"

        return "casa"  # Default

    def _extract_operation_type_from_url(self) -> Optional[str]:
        """Extract operation type from URL path (most reliable)"""
        url_lower = self.url.lower()

        if '/alquiler-temporario/' in url_lower or '/temporal/' in url_lower:
            return "alquiler_temporal"
        elif '/alquiler/' in url_lower:
            return "alquiler"
        elif '/venta/' in url_lower or 'en-venta' in url_lower:
            return "venta"

        return None

    def _extract_operation_type(self) -> str:
        """Extract operation type with prioritized sources"""

        # Priority 1: URL path (99% reliable)
        url_operation = self._extract_operation_type_from_url()
        if url_operation:
            return url_operation

        # Priority 2: Text mining (fallback)
        title = self._extract_title().lower()
        desc = self._extract_description().lower()
        combined = f"{title} {desc}"

        # FIX: Check venta BEFORE alquiler, more specific patterns
        if 'alquiler temporario' in combined or 'alquiler temporal' in combined:
            return "alquiler_temporal"
        elif 'venta' in combined or 'vende' in combined or 'en venta' in combined:
            return "venta"
        elif 'alquiler' in combined or 'alquila' in combined:
            return "alquiler"

        return "venta"  # Default (Argenprop es principalmente ventas)

    def _extract_location(self) -> Dict[str, Any]:
        """Extract location data"""
        if not self.soup:
            return {"neighborhood": "", "city": "Buenos Aires", "province": "Buenos Aires"}

        neighborhood = ""
        city = ""
        province = "Buenos Aires"

        # Strategy 1: Look for titlebar with format "Venta en Coghlan, Capital Federal"
        titlebar_selectors = [
            'h2.titlebar__title',
            'h2[class*="titlebar"]',
            '.titlebar h2',
            '.titlebar__title',
        ]
        for sel in titlebar_selectors:
            titlebar = self.soup.select_one(sel)
            if titlebar:
                text = titlebar.get_text(strip=True)
                match = re.search(
                    r'(?:Venta|Alquiler|Alquiler temporario)\s+en\s+([^,]+),\s*(.+)',
                    text, re.IGNORECASE,
                )
                if match:
                    neighborhood = match.group(1).strip()
                    city = match.group(2).strip()
                    break

        # Strategy 2: Look for any element with "Venta en X, Y" or "Alquiler en X, Y"
        if not neighborhood:
            for tag in self.soup.find_all(['h1', 'h2', 'h3', 'p', 'span', 'div']):
                text = tag.get_text(strip=True)
                if len(text) > 150 or len(text) < 10:
                    continue
                match = re.search(
                    r'(?:Venta|Alquiler|Alquiler temporario)\s+en\s+([^,]+),\s*(.+)',
                    text, re.IGNORECASE,
                )
                if match:
                    neighborhood = match.group(1).strip()
                    city = match.group(2).strip()
                    break

        # Strategy 3: Location/address CSS selectors
        if not neighborhood:
            selectors = [
                '.location',
                '[class*="location"]',
                '.property-location',
                '[class*="ubic"]',
            ]

            for selector in selectors:
                location_text = self.extract_text(selector)
                if location_text:
                    parts = [p.strip() for p in location_text.split(',')]
                    if len(parts) >= 1 and not neighborhood:
                        neighborhood = parts[0]
                    if len(parts) >= 2 and not city:
                        city = parts[1]
                    break

        # Strategy 4: Look for spans/small elements with known neighborhoods
        if not neighborhood:
            known_neighborhoods = [
                'palermo', 'belgrano', 'recoleta', 'caballito', 'coghlan',
                'villa crespo', 'colegiales', 'nuñez', 'nunez', 'almagro',
                'san telmo', 'villa urquiza', 'saavedra', 'chacarita',
                'villa devoto', 'flores', 'floresta', 'boedo', 'barracas',
                'villa del parque', 'villa luro', 'villa pueyrredon',
                'liniers', 'mataderos', 'paternal', 'parque patricios',
                'puerto madero', 'san nicolas', 'monserrat', 'barrio norte',
                'constitucion', 'balvanera', 'la boca',
            ]
            for elem in self.soup.find_all(['span', 'p', 'div', 'a']):
                text = elem.get_text(strip=True)
                if not text or len(text) > 60:
                    continue
                text_lower = text.lower().strip()
                for nb in known_neighborhoods:
                    if text_lower == nb or text_lower.startswith(nb + ','):
                        neighborhood = text.split(',')[0].strip()
                        break
                if not city and text_lower == 'capital federal':
                    city = text
                if neighborhood:
                    break

        # Strategy 5: Extract from URL as fallback
        # URL formats: /ph-en-venta-en-coghlan-3-ambientes--18186163
        #              /departamento-en-venta-en-villa-crespo--12345
        if not neighborhood:
            url_lower = self.url.lower()
            # Try with ambientes suffix
            match = re.search(r'-en-([a-z-]+)-\d+-ambientes', url_lower)
            if not match:
                # Try without ambientes: -en-NEIGHBORHOOD--ID
                match = re.search(r'-en-([a-z][a-z-]+?)--\d+', url_lower)
            if match:
                raw = match.group(1).strip('-')
                # Skip generic location words
                if raw not in ('venta', 'alquiler', 'capital-federal', 'buenos-aires'):
                    neighborhood = raw.replace('-', ' ').title()

        # Normalize city
        if not city:
            city = "Buenos Aires"
        if "capital federal" in city.lower():
            province = "Capital Federal"

        return {
            "neighborhood": neighborhood,
            "city": city,
            "province": province,
        }

    def _extract_address_details(self) -> Dict[str, str]:
        """
        Extract address details including street and number.
        Returns dict with 'full_address', 'street', 'street_number'.
        """
        result = {
            'full_address': '',
            'street': '',
            'street_number': '',
        }

        selectors = [
            '.titlebar__address',
            '[class*="address"]',
            '.street-address',
            'address',
            '[class*="direccion"]',
        ]

        for selector in selectors:
            addr = self.extract_text(selector)
            if addr:
                result['full_address'] = addr
                self._parse_street_number(result, addr)
                return result

        # Fallback: look for text that matches street address patterns
        if self.soup:
            for elem in self.soup.find_all(['p', 'span', 'div', 'h3']):
                text = elem.get_text(strip=True)
                if not text or len(text) > 120 or len(text) < 5:
                    continue
                # Match patterns like "Av. Balbin 2800" or "Calle 123"
                if re.match(
                    r'^(Av\.?|Avenida|Calle|Bv\.?|Boulev|Pasaje|Pje\.?)\s',
                    text, re.IGNORECASE,
                ):
                    result['full_address'] = text
                    self._parse_street_number(result, text)
                    return result
                # Match "Word(s) 1234" (street name + number)
                if re.match(r'^[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(\s[A-Za-záéíóúñ]+)*\s\d{2,5}$', text):
                    result['full_address'] = text
                    self._parse_street_number(result, text)
                    return result

        return result

    def _parse_street_number(self, result: Dict[str, str], address: str) -> None:
        """Parse street and number from address string."""
        if not address:
            return

        # Pattern: "Street Name 1234" or "Av. Street Name 1234"
        match = re.match(r'^(.+?)\s+(\d+)\s*$', address)
        if match:
            result['street'] = match.group(1).strip()
            result['street_number'] = match.group(2)
        else:
            # No number found, entire address is street
            result['street'] = address

    def _extract_address(self) -> str:
        """Extract street address (legacy compatibility)"""
        return self._extract_address_details().get('full_address', '')

    def _normalize_image_url(self, img_url: str) -> Optional[str]:
        """Convert relative URLs to absolute, validate format"""
        if not img_url:
            return None

        img_url = img_url.strip().strip('"\'')

        # Skip placeholders and data URIs
        if img_url.startswith('data:') or 'placeholder' in img_url.lower():
            return None

        # Convert relative to absolute
        if img_url.startswith('//'):
            return f"https:{img_url}"
        elif img_url.startswith('/'):
            return urljoin(self.url, img_url)
        elif img_url.startswith('http'):
            return img_url
        else:
            # Relative path without leading slash
            return urljoin(self.url, img_url)

    def _extract_images(self) -> List[str]:
        """Extract image URLs with multiple strategies"""
        images = []

        if not self.soup:
            return images

        # Strategy 1: Check multiple image attributes
        image_attrs = ['src', 'data-src', 'data-original', 'data-lazy', 'data-lazy-src']

        # Real Argenprop selectors (from inspection)
        selectors = [
            '.gallery .gallery-content li img',  # Main gallery images
            '.simple-carousel ul li img',  # Carousel images
            '.gallery img',  # Alternative gallery selector
            '[class*="gallery"] img',  # Any gallery-related class
            'img[data-lazy]',  # Lazy-loaded images
        ]

        for selector in selectors:
            imgs = self.soup.select(selector)
            for img in imgs:
                # Try all possible image attributes
                for attr in image_attrs:
                    img_url = img.get(attr)
                    if img_url:
                        normalized = self._normalize_image_url(img_url)
                        if normalized:
                            images.append(normalized)
                        break  # Found image, move to next img tag

        # Strategy 2: Check picture/source tags
        pictures = self.soup.select('picture source')
        for source in pictures:
            srcset = source.get('srcset') or source.get('data-srcset')
            if srcset:
                # srcset can have multiple URLs, take the first
                first_url = srcset.split(',')[0].strip().split(' ')[0]
                normalized = self._normalize_image_url(first_url)
                if normalized:
                    images.append(normalized)

        # Strategy 3: Look for JSON-LD or schema.org data with images
        scripts = self.soup.find_all('script', type='application/ld+json')
        for script in scripts:
            try:
                import json
                if script.string:
                    data = json.loads(script.string)
                    if isinstance(data, dict) and 'image' in data:
                        img_data = data['image']
                        if isinstance(img_data, list):
                            for img_url in img_data:
                                normalized = self._normalize_image_url(img_url)
                                if normalized:
                                    images.append(normalized)
                        elif isinstance(img_data, str):
                            normalized = self._normalize_image_url(img_data)
                            if normalized:
                                images.append(normalized)
            except (json.JSONDecodeError, AttributeError):
                continue

        # Remove duplicates while preserving order
        seen = set()
        unique_images = []
        for img in images:
            if img not in seen:
                seen.add(img)
                unique_images.append(img)

        return unique_images[:20]  # Limit to 20 images

    def _extract_features(self) -> Dict[str, Any]:
        """Extract property features"""
        features = {
            "bedrooms": self._extract_number_feature(['dormitorio', 'ambiente', 'cuarto']),
            "bathrooms": self._extract_number_feature(['baño']),
            "parking_spaces": self._extract_number_feature(['cochera', 'garage', 'estacionamiento']),
            "covered_area": self._extract_area_feature(['cubierta', 'cubierto']),
            "total_area": self._extract_area_feature(['total', 'terreno']),
        }

        # Extract amenities
        amenities = []
        amenity_keywords = [
            'pileta', 'piscina', 'gimnasio', 'seguridad', 'parrilla',
            'balcón', 'terraza', 'jardín', 'quincho', 'sum'
        ]

        description = self._extract_description().lower()
        for keyword in amenity_keywords:
            if keyword in description:
                amenities.append(keyword)

        features['amenities'] = amenities

        return features

    def _extract_number_feature(self, keywords: List[str]) -> Optional[int]:
        """Extract numeric feature (bedrooms, bathrooms, etc.)"""
        text = f"{self._extract_title()} {self._extract_description()}".lower()

        for keyword in keywords:
            # Look for patterns like "3 dormitorios" or "dormitorios: 3"
            pattern = rf'(\d+)\s*{keyword}|{keyword}[:\s]+(\d+)'
            match = re.search(pattern, text)
            if match:
                number = match.group(1) or match.group(2)
                try:
                    return int(number)
                except ValueError:
                    continue

        return None

    def _extract_area_feature(self, keywords: List[str]) -> Optional[float]:
        """Extract area in square meters"""
        text = f"{self._extract_title()} {self._extract_description()}".lower()

        for keyword in keywords:
            # Look for patterns like "80 m2" or "superficie: 120m²"
            pattern = rf'(\d+(?:[.,]\d+)?)\s*(?:m2|m²|mts²|metros)?\s*{keyword}|{keyword}[:\s]+(\d+(?:[.,]\d+)?)\s*(?:m2|m²|mts²)?'
            match = re.search(pattern, text)
            if match:
                area_str = match.group(1) or match.group(2)
                area_str = area_str.replace(',', '.')
                try:
                    return float(area_str)
                except ValueError:
                    continue

        return None

    def _extract_contact(self) -> Dict[str, str]:
        """Extract contact information"""
        contact = {
            "real_estate_agency": "",
            "phone": "",
            "email": "",
        }

        # Extract agency name
        selectors = [
            '.agency-name',
            '[class*="inmobiliaria"]',
            '.real-estate-name',
        ]

        for selector in selectors:
            agency = self.extract_text(selector)
            if agency:
                contact['real_estate_agency'] = agency
                break

        # Extract phone (look for Argentine format)
        text = self.soup.get_text() if self.soup else ""
        phone_pattern = r'(?:\+54|0)?[\s-]?\d{2,4}[\s-]?\d{4}[\s-]?\d{4}'
        phone_match = re.search(phone_pattern, text)
        if phone_match:
            contact['phone'] = phone_match.group(0).strip()

        # Extract email
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        email_match = re.search(email_pattern, text)
        if email_match:
            contact['email'] = email_match.group(0)

        return contact

    def _extract_source_id(self) -> str:
        """Extract property ID from URL"""
        # Argenprop URLs usually contain an ID
        match = re.search(r'/(\d+)(?:/|$|-)', self.url)
        if match:
            return match.group(1)

        # Fallback: use last part of URL
        parts = self.url.rstrip('/').split('/')
        return parts[-1] if parts else ""

    def _extract_status(self) -> str:
        """
        Extract property status (active, sold, rented, reserved)
        Looks for badges, title indicators, or description text
        """
        if not self.soup:
            return "active"

        # Get all text from the page
        page_text = self.soup.get_text().lower()
        title_text = self._extract_title().lower()

        # Check for sold indicators
        sold_keywords = ['vendido', 'vendida', 'sold', 'no disponible']
        for keyword in sold_keywords:
            if keyword in title_text or keyword in page_text[:500]:  # Check first 500 chars
                return "sold"

        # Check for rented indicators
        rented_keywords = ['alquilado', 'alquilada', 'rented', 'rentado']
        for keyword in rented_keywords:
            if keyword in title_text or keyword in page_text[:500]:
                return "rented"

        # Check for reserved indicators
        reserved_keywords = ['reservado', 'reservada', 'reserved', 'en reserva']
        for keyword in reserved_keywords:
            if keyword in title_text or keyword in page_text[:500]:
                return "reserved"

        # Check for removed/inactive indicators
        removed_keywords = ['removido', 'eliminado', 'fuera del mercado', 'retirado']
        for keyword in removed_keywords:
            if keyword in title_text or keyword in page_text[:500]:
                return "removed"

        # Check for status badges/labels in HTML
        status_selectors = [
            '.status-badge',
            '.property-status',
            '[class*="status"]',
            '.badge',
            '.label',
        ]

        for selector in status_selectors:
            status_elem = self.soup.select_one(selector)
            if status_elem:
                status_text = status_elem.get_text().lower()
                if any(kw in status_text for kw in sold_keywords):
                    return "sold"
                if any(kw in status_text for kw in rented_keywords):
                    return "rented"
                if any(kw in status_text for kw in reserved_keywords):
                    return "reserved"

        # Default to active if no indicators found
        return "active"
