"""
MercadoLibre Scraper
Extracts property data from inmuebles.mercadolibre.com.ar / departamento.mercadolibre.com.ar
Uses Selenium to handle dynamic content
"""
import re
import json
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from .base import BaseScraper


class MercadoLibreScraper(BaseScraper):
    """Scraper for MercadoLibre portal using Selenium"""

    DOMAINS = ["mercadolibre.com.ar"]

    def validate_url(self) -> bool:
        """Check if URL is from MercadoLibre"""
        parsed = urlparse(self.url)
        return any(domain in parsed.netloc for domain in self.DOMAINS)

    async def fetch_page(self) -> str:
        """Fetch page using Selenium to handle dynamic content"""
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

            # Wait for page to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )

            # Additional wait for dynamic content
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

        data = {
            "source": "mercadolibre",
            "title": self._extract_title(json_data),
            "description": self._extract_description(),
            "price": self._extract_price(json_data),
            "currency": self._extract_currency(json_data),
            "property_type": self._extract_property_type(),
            "operation_type": self._extract_operation_type(),
            "location": self._extract_location(),
            "address": self._extract_address(),
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
            # Extract numbers from text like "US$119.000"
            price_clean = re.sub(r'[^\d]', '', text)
            if price_clean:
                try:
                    return float(price_clean)
                except ValueError:
                    continue

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

    def _extract_address(self) -> str:
        """Extract street address"""
        if not self.soup:
            return ""

        # Look for full address in location subtitle
        location_elem = self.soup.select_one('.ui-vip-location__subtitle')
        if location_elem:
            location_text = location_elem.get_text(strip=True)
            # Extract first part (street address)
            parts = location_text.split(',')
            if parts:
                return parts[0].strip()

        return ""

    def _extract_images(self, json_data: Optional[Dict[str, Any]]) -> List[str]:
        """Extract image URLs"""
        images = []

        # Try JSON-LD first
        if json_data and 'image' in json_data:
            img_data = json_data['image']
            if isinstance(img_data, list):
                images.extend(img_data)
            elif isinstance(img_data, str):
                images.append(img_data)

        # Fallback: extract from HTML
        if not images and self.soup:
            img_tags = self.soup.find_all('img', {'src': lambda x: x and 'http2.mlstatic.com' in x})

            for img in img_tags:
                src = img.get('src', '')
                # Filter out small icons/logos
                if src and 'http2.mlstatic.com' in src:
                    # Exclude default/placeholder images
                    if 'default' not in src.lower() and 'exhibitor' not in src.lower():
                        images.append(src)

        # Remove duplicates
        seen = set()
        unique_images = []
        for img in images:
            if img not in seen:
                seen.add(img)
                unique_images.append(img)

        return unique_images[:20]

    def _extract_features(self) -> Dict[str, Any]:
        """Extract property features"""
        features = {
            "bedrooms": None,
            "bathrooms": None,
            "parking_spaces": None,
            "covered_area": None,
            "total_area": None,
        }

        if not self.soup:
            return features

        # MercadoLibre shows features as text
        text = self.soup.get_text()

        # Extract bedrooms/ambientes
        bed_match = re.search(r'(\d+)\s*dormitorio|(\d+)\s*ambiente', text, re.IGNORECASE)
        if bed_match:
            features['bedrooms'] = int(bed_match.group(1) or bed_match.group(2))

        # Extract bathrooms
        bath_match = re.search(r'(\d+)\s*baño', text, re.IGNORECASE)
        if bath_match:
            features['bathrooms'] = int(bath_match.group(1))

        # Extract parking
        parking_match = re.search(r'(\d+)\s*cochera', text, re.IGNORECASE)
        if parking_match:
            features['parking_spaces'] = int(parking_match.group(1))

        # Extract area
        area_match = re.search(r'(\d+)\s*m²?\s*totales?', text, re.IGNORECASE)
        if area_match:
            features['total_area'] = float(area_match.group(1))

        area_cub_match = re.search(r'(\d+)\s*m²?\s*cubierto', text, re.IGNORECASE)
        if area_cub_match:
            features['covered_area'] = float(area_cub_match.group(1))

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
