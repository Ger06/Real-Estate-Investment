"""
MercadoLibre Scraper
Extracts property data from inmuebles.mercadolibre.com.ar / departamento.mercadolibre.com.ar
Uses curl_cffi for Cloudflare bypass, Selenium as last resort.
"""
import asyncio
import re
import json
import logging
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from .base import BaseScraper
from .http_client import fetch_with_browser_fingerprint
from .utils import clean_price as _clean_price

logger = logging.getLogger(__name__)


class MercadoLibreScraper(BaseScraper):
    """Scraper for MercadoLibre portal. Uses curl_cffi, Selenium as last resort."""

    DOMAINS = ["mercadolibre.com.ar"]

    def validate_url(self) -> bool:
        """Check if URL is from MercadoLibre"""
        parsed = urlparse(self.url)
        return any(domain in parsed.netloc for domain in self.DOMAINS)

    async def fetch_page(self) -> str:
        """
        Fetch page with 3-level fallback:
        1. curl_cffi with Chrome TLS fingerprint (works on Render without Chrome)
        2. httpx (fallback if curl_cffi not installed)
        3. Selenium (last resort, only works where Chrome is installed)
        """
        # Level 1+2: curl_cffi / httpx via base class
        try:
            html = await super().fetch_page()
            if len(html) > 5000:
                logger.info(f"[mercadolibre] fetch_with_browser_fingerprint OK, length: {len(html)}")
                return html
            logger.warning("[mercadolibre] Response too short, trying Selenium...")
        except Exception as e:
            logger.warning(f"[mercadolibre] HTTP fetch failed: {e}, trying Selenium...")

        # Level 3: Selenium fallback
        return await asyncio.to_thread(self._fetch_with_selenium)

    def _fetch_with_selenium(self) -> str:
        """Fetch page using Selenium as last resort."""
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
        except ImportError:
            raise RuntimeError(
                "Neither curl_cffi nor Selenium+Chrome available. "
                "Install curl_cffi for production: pip install curl_cffi"
            )

        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument(f'user-agent={self.user_agent}')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
        chrome_options.add_experimental_option('useAutomationExtension', False)

        driver = None
        try:
            driver = webdriver.Chrome(options=chrome_options)
            driver.get(self.url)

            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )

            import time
            time.sleep(4)

            html = driver.page_source
            return html

        finally:
            if driver:
                driver.quit()

    def extract_data(self) -> Dict[str, Any]:
        """Extract all property data from MercadoLibre"""
        if not self.soup:
            raise ValueError("HTML not parsed. Call fetch_page() first.")

        # Try to extract from JSON-LD first
        json_data = self._extract_json_ld()

        # Extract address details
        address_info = self._extract_address_details()

        data = {
            "source": "mercadolibre",
            "title": self._extract_title(json_data),
            "description": self._extract_description(),
            "price": self._extract_price(json_data),
            "currency": self._extract_currency(json_data),
            "property_type": self._extract_property_type(),
            "operation_type": self._extract_operation_type(),
            "location": self._extract_location(),
            "address": address_info.get('full_address', ''),
            "street": address_info.get('street', ''),
            "street_number": address_info.get('street_number', ''),
            "images": self._extract_images(json_data),
            "features": self._extract_features(),
            "contact": self._extract_contact(),
            "source_id": self._extract_source_id(),
            "status": self._extract_status(json_data),
        }

        return data

    def _extract_json_ld(self) -> Optional[Dict[str, Any]]:
        """Extract data from JSON-LD structured data"""
        if not self.soup:
            return None

        scripts = self.soup.find_all('script', type='application/ld+json')
        for script in scripts:
            if script.string:
                try:
                    data = json.loads(script.string)
                    if isinstance(data, dict) and data.get('@type') == 'Product':
                        return data
                except (json.JSONDecodeError, AttributeError):
                    continue

        return None

    def _extract_title(self, json_data: Optional[Dict[str, Any]]) -> str:
        """Extract property title"""
        # Try JSON-LD first
        if json_data and 'name' in json_data:
            return json_data['name']

        # Fallback to h1
        h1 = self.soup.find('h1') if self.soup else None
        if h1:
            return h1.get_text(strip=True)

        return "Propiedad sin título"

    def _extract_description(self) -> str:
        """Extract property description"""
        if not self.soup:
            return ""

        # MercadoLibre uses specific classes for description
        selectors = [
            '.ui-pdp-description__content',
            '[class*="description"]',
            '#description',
        ]

        for selector in selectors:
            desc_elem = self.soup.select_one(selector)
            if desc_elem:
                desc = desc_elem.get_text(strip=True)
                if len(desc) > 50:
                    return desc

        return ""

    def _extract_price(self, json_data: Optional[Dict[str, Any]]) -> Optional[float]:
        """Extract price"""
        # Try JSON-LD first
        if json_data and 'offers' in json_data:
            offers = json_data['offers']
            if isinstance(offers, dict) and 'price' in offers:
                try:
                    return float(offers['price'])
                except (ValueError, TypeError):
                    pass

        # Fallback to HTML
        if not self.soup:
            return None

        # Look for price in span elements
        price_spans = self.soup.find_all('span', class_=lambda x: x and 'price' in str(x).lower())
        for span in price_spans:
            text = span.get_text(strip=True)
            price_amount, _ = _clean_price(text)
            if price_amount:
                return price_amount

        return None

    def _extract_currency(self, json_data: Optional[Dict[str, Any]]) -> str:
        """Extract currency"""
        # Try JSON-LD first
        if json_data and 'offers' in json_data:
            offers = json_data['offers']
            if isinstance(offers, dict) and 'priceCurrency' in offers:
                currency = offers['priceCurrency']
                if currency == 'USD':
                    return 'USD'
                elif currency == 'ARS':
                    return 'ARS'

        # Fallback to HTML
        if not self.soup:
            return "USD"

        # Look for currency symbols in price elements
        price_divs = self.soup.find_all('div', class_=lambda x: x and 'price' in str(x).lower())
        for div in price_divs:
            text = div.get_text()
            if 'US$' in text or 'USD' in text:
                return "USD"
            if 'AR$' in text or 'ARS' in text or '$' in text:
                return "ARS"

        return "USD"

    def _extract_property_type(self) -> str:
        """Extract property type"""
        # Extract from title and URL
        title = self._extract_title(None).lower()
        url_lower = self.url.lower()
        combined = f"{title} {url_lower}"

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

    def _extract_operation_type(self) -> str:
        """Extract operation type"""
        url_lower = self.url.lower()
        title = self._extract_title(None).lower()
        combined = f"{url_lower} {title}"

        if 'alquiler-temporal' in combined or 'temporal' in combined:
            return "alquiler_temporal"
        elif 'alquiler' in combined:
            return "alquiler"
        elif 'venta' in combined:
            return "venta"

        return "venta"

    def _extract_location(self) -> Dict[str, Any]:
        """Extract location data"""
        neighborhood = ""
        city = "Buenos Aires"
        province = "Buenos Aires"

        if not self.soup:
            return {"neighborhood": neighborhood, "city": city, "province": province}

        # MercadoLibre uses ui-vip-location classes
        location_elem = self.soup.select_one('.ui-vip-location__subtitle')
        if location_elem:
            location_text = location_elem.get_text(strip=True)
            # Format: "Armenia Al 2100, Palermo, Capital Federal, Capital Federal"
            parts = [p.strip() for p in location_text.split(',')]

            if len(parts) >= 2:
                # Second part is usually the neighborhood
                neighborhood = parts[1] if len(parts) > 1 else parts[0]

            if len(parts) >= 3:
                city = parts[2]

            if len(parts) >= 4:
                province = parts[3]

        # Fallback: extract from title
        if not neighborhood:
            title = self._extract_title(None)
            match = re.search(r'(Palermo|Belgrano|Recoleta|Caballito|Villa Crespo|Colegiales|Núñez|Almagro|San Telmo|La Boca)', title, re.IGNORECASE)
            if match:
                neighborhood = match.group(1)

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

        if not self.soup:
            return result

        # Look for full address in location subtitle
        location_elem = self.soup.select_one('.ui-vip-location__subtitle')
        if location_elem:
            location_text = location_elem.get_text(strip=True)
            # Extract first part (street address)
            parts = location_text.split(',')
            if parts:
                address = parts[0].strip()
                result['full_address'] = address
                self._parse_street_number(result, address)

        return result

    def _parse_street_number(self, result: Dict[str, str], address: str) -> None:
        """Parse street and number from address string."""
        if not address:
            return

        # Pattern: "Street Name Al 1234" or "Street Name 1234" or "Av. Street 1234"
        # MercadoLibre often uses "Al" before the number: "Armenia Al 2100"
        match = re.match(r'^(.+?)\s+(?:Al\s+)?(\d+)\s*$', address, re.IGNORECASE)
        if match:
            result['street'] = match.group(1).strip()
            result['street_number'] = match.group(2)
        else:
            # No number found, entire address is street
            result['street'] = address

    def _extract_address(self) -> str:
        """Extract street address (legacy compatibility)"""
        return self._extract_address_details().get('full_address', '')

    def _extract_images(self, json_data: Optional[Dict[str, Any]]) -> List[str]:
        """Extract image URLs using multiple strategies"""
        images = []
        seen = set()

        def _add(url: str) -> None:
            if url and url not in seen:
                # Skip non-property images
                lower = url.lower()
                if any(skip in lower for skip in ['frontend-assets', 'default', 'exhibitor', 'placeholder', 'logo', '.svg']):
                    return
                seen.add(url)
                # Upgrade ML image resolution: -O (small) -> -F (full size)
                upgraded = re.sub(r'-[A-Z]\.(\w+)$', r'-F.\1', url)
                images.append(upgraded)

        # Strategy 1: JSON-LD images
        if json_data and 'image' in json_data:
            img_data = json_data['image']
            if isinstance(img_data, list):
                for img in img_data:
                    _add(img)
            elif isinstance(img_data, str):
                _add(img_data)

        # Strategy 2: HTML img tags from gallery/carousel
        if self.soup:
            # ML gallery uses figure elements or specific image classes
            for selector in [
                'figure img[src*="mlstatic"]',
                'figure img[data-src*="mlstatic"]',
                'img[class*="ui-pdp-image"][src*="mlstatic"]',
                'img[data-zoom*="mlstatic"]',
                'img[src*="http2.mlstatic.com/D_"]',
                'img[data-src*="http2.mlstatic.com/D_"]',
            ]:
                for img in self.soup.select(selector):
                    for attr in ['data-zoom', 'data-src', 'src']:
                        val = img.get(attr, '')
                        if 'mlstatic' in val:
                            _add(val)
                            break

        # Strategy 3: Search all img tags with mlstatic
        if not images and self.soup:
            for img in self.soup.find_all('img'):
                for attr in ['data-src', 'src']:
                    val = img.get(attr, '')
                    if 'http2.mlstatic.com' in val and '/D_' in val:
                        _add(val)
                        break

        # Strategy 4: og:image as last resort
        if not images and self.soup:
            og = self.soup.find('meta', property='og:image')
            if og:
                _add(og.get('content', ''))

        return images[:20]

    def _extract_features(self) -> Dict[str, Any]:
        """Extract property features from specs table and page text"""
        features = {
            "bedrooms": None,
            "bathrooms": None,
            "parking_spaces": None,
            "covered_area": None,
            "total_area": None,
        }

        if not self.soup:
            return features

        # Strategy 1: Extract from specs/attributes table rows
        # MercadoLibre uses table rows with label + value pairs
        spec_selectors = [
            'tr.andes-table__row',
            '[class*="specs"] tr',
            '[class*="attribute"] tr',
            'table tr',
        ]

        spec_items = []
        for selector in spec_selectors:
            rows = self.soup.select(selector)
            if rows:
                for row in rows:
                    cells = row.find_all(['td', 'th', 'span'])
                    row_text = row.get_text(' ', strip=True).lower()
                    spec_items.append(row_text)
                break

        # Also check for key-value pairs in list format
        for selector in ['[class*="specs"] li', '[class*="attribute"] li', '[class*="features"] li']:
            items = self.soup.select(selector)
            for item in items:
                spec_items.append(item.get_text(' ', strip=True).lower())

        # Parse spec items for structured data
        for item in spec_items:
            if not features['total_area'] and ('superficie total' in item or 'sup. total' in item):
                m = re.search(r'(\d+(?:[.,]\d+)?)', item)
                if m:
                    features['total_area'] = float(m.group(1).replace(',', '.'))

            if not features['covered_area'] and ('superficie cubierta' in item or 'sup. cubierta' in item or 'cubiertos' in item):
                m = re.search(r'(\d+(?:[.,]\d+)?)', item)
                if m:
                    features['covered_area'] = float(m.group(1).replace(',', '.'))

            if not features['bedrooms'] and ('dormitorio' in item or 'habitaci' in item):
                m = re.search(r'(\d+)', item)
                if m:
                    features['bedrooms'] = int(m.group(1))

            if not features['bedrooms'] and 'ambiente' in item:
                m = re.search(r'(\d+)', item)
                if m:
                    features['bedrooms'] = int(m.group(1))

            if not features['bathrooms'] and 'baño' in item:
                m = re.search(r'(\d+)', item)
                if m:
                    features['bathrooms'] = int(m.group(1))

            if not features['parking_spaces'] and ('cochera' in item or 'estacionamiento' in item):
                m = re.search(r'(\d+)', item)
                if m:
                    features['parking_spaces'] = int(m.group(1))

        # Strategy 2: Fallback to full page text regex
        if not any([features['total_area'], features['covered_area'], features['bedrooms']]):
            text = self.soup.get_text()

            if not features['bedrooms']:
                bed_match = re.search(r'(\d+)\s*dormitorio|(\d+)\s*ambiente', text, re.IGNORECASE)
                if bed_match:
                    features['bedrooms'] = int(bed_match.group(1) or bed_match.group(2))

            if not features['bathrooms']:
                bath_match = re.search(r'(\d+)\s*baño', text, re.IGNORECASE)
                if bath_match:
                    features['bathrooms'] = int(bath_match.group(1))

            if not features['parking_spaces']:
                parking_match = re.search(r'(\d+)\s*cochera', text, re.IGNORECASE)
                if parking_match:
                    features['parking_spaces'] = int(parking_match.group(1))

            if not features['total_area']:
                area_match = re.search(r'(\d+(?:[.,]\d+)?)\s*m[²2]?\s*totales?', text, re.IGNORECASE)
                if area_match:
                    features['total_area'] = float(area_match.group(1).replace(',', '.'))

            if not features['covered_area']:
                area_cub_match = re.search(r'(\d+(?:[.,]\d+)?)\s*m[²2]?\s*cubiertos?', text, re.IGNORECASE)
                if area_cub_match:
                    features['covered_area'] = float(area_cub_match.group(1).replace(',', '.'))

        # Extract amenities
        amenities = []
        amenity_keywords = [
            'pileta', 'piscina', 'gimnasio', 'seguridad', 'parrilla',
            'balcón', 'terraza', 'jardín', 'quincho', 'sum', 'laundry'
        ]

        description = self._extract_description().lower()
        for keyword in amenity_keywords:
            if keyword in description:
                amenities.append(keyword)

        features['amenities'] = amenities

        return features

    def _extract_contact(self) -> Dict[str, str]:
        """Extract contact information"""
        # MercadoLibre doesn't usually show direct contact info
        # It uses internal messaging system
        return {
            "real_estate_agency": "",
            "phone": "",
            "email": "",
        }

    def _extract_source_id(self) -> str:
        """Extract property ID from URL"""
        # MercadoLibre uses MLA-XXXXXXX format
        match = re.search(r'MLA-?(\d+)', self.url)
        if match:
            return f"MLA{match.group(1)}"

        # Fallback
        parts = self.url.rstrip('/').split('/')
        return parts[-1] if parts else ""

    def _extract_status(self, json_data: Optional[Dict[str, Any]]) -> str:
        """
        Extract property status (active, sold, rented, reserved)
        Checks JSON-LD data and page indicators
        """
        # Check JSON-LD for availability
        if json_data:
            offers = json_data.get("offers", {})
            availability = offers.get("availability", "").lower()

            if "sold" in availability or "outofstock" in availability:
                return "sold"
            if "discontinued" in availability:
                return "removed"

        # Check page for status indicators
        if self.soup:
            page_text = self.soup.get_text().lower()
            title_text = page_text[:200]  # Check title area

            sold_keywords = ['vendido', 'vendida', 'sold', 'no disponible', 'pausado']
            rented_keywords = ['alquilado', 'alquilada', 'rented']
            reserved_keywords = ['reservado', 'reservada', 'reserved']

            for keyword in sold_keywords:
                if keyword in title_text or keyword in page_text[:500]:
                    return "sold"
            for keyword in rented_keywords:
                if keyword in title_text or keyword in page_text[:500]:
                    return "rented"
            for keyword in reserved_keywords:
                if keyword in title_text or keyword in page_text[:500]:
                    return "reserved"

            # Check for MercadoLibre specific status badges
            status_selectors = [
                '.ui-pdp-header__status',
                '[class*="status"]',
                '.ui-pdp-badge',
            ]

            for selector in status_selectors:
                status_elem = self.soup.select_one(selector)
                if status_elem:
                    status_text = status_elem.get_text().lower()
                    for keyword in sold_keywords:
                        if keyword in status_text:
                            return "sold"
                    for keyword in reserved_keywords:
                        if keyword in status_text:
                            return "reserved"

        # Default to active
        return "active"
