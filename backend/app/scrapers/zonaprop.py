"""
Zonaprop Scraper
Extracts property data from www.zonaprop.com.ar
Uses Selenium to bypass Cloudflare protection
"""
import re
import json
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse, urljoin
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from .base import BaseScraper


class ZonapropScraper(BaseScraper):
    """Scraper for Zonaprop portal using Selenium"""

    DOMAIN = "zonaprop.com.ar"

    def validate_url(self) -> bool:
        """Check if URL is from Zonaprop"""
        parsed = urlparse(self.url)
        return self.DOMAIN in parsed.netloc

    async def fetch_page(self) -> str:
        """Fetch page using Selenium to bypass Cloudflare"""
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

            # Wait for page to load (Cloudflare bypass)
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )

            # Additional wait for dynamic content
            import time
            time.sleep(3)

            html = driver.page_source
            return html

        finally:
            if driver:
                driver.quit()

    def extract_data(self) -> Dict[str, Any]:
        """Extract all property data from Zonaprop"""
        if not self.soup:
            raise ValueError("HTML not parsed. Call fetch_page() first.")

        data = {
            "source": "zonaprop",
            "title": self._extract_title(),
            "description": self._extract_description(),
            "price": self._extract_price(),
            "currency": self._extract_currency(),
            "property_type": self._extract_property_type(),
            "operation_type": self._extract_operation_type(),
            "location": self._extract_location(),
            "address": self._extract_address(),
            "images": self._extract_images(),
            "features": self._extract_features(),
            "contact": self._extract_contact(),
            "source_id": self._extract_source_id(),
            "status": self._extract_status(),
        }

        return data

    def _extract_title(self) -> str:
        """Extract property title"""
        selectors = [
            'h1',
            '.title',
            '[class*="title"]',
            'h1.posting-title',
            '.posting-description h1',
        ]

        for selector in selectors:
            title = self.extract_text(selector)
            if title:
                return title

        return "Propiedad sin título"

    def _extract_description(self) -> str:
        """Extract property description"""
        selectors = [
            '[class*="description"]',
            '.posting-description',
            '#description',
            '.property-description',
            '[data-qa="POSTING_DESCRIPTION"]',
        ]

        for selector in selectors:
            desc = self.extract_text(selector)
            if desc and len(desc) > 50:
                return desc

        return ""

    def _extract_price(self) -> Optional[float]:
        """Extract price as float"""
        # Zonaprop stores price in span elements containing currency
        if not self.soup:
            return None

        # Find all span elements that contain USD or $
        price_text = ""
        for span in self.soup.find_all('span'):
            text = span.get_text(strip=True)
            if text and any(curr in text for curr in ['USD', 'U$S', 'ARS', '$']):
                # Avoid "Expensas"
                if 'expense' not in text.lower() and 'expensa' not in text.lower():
                    price_text = text
                    break

        # Clean price text - Zonaprop format: "USD 239.000"
        # Remove currency symbols and keep only digits
        price_clean = re.sub(r'[^\d]', '', price_text)

        try:
            return float(price_clean) if price_clean else None
        except ValueError:
            return None

    def _extract_currency(self) -> str:
        """Extract currency (USD or ARS)"""
        selectors = [
            '[data-qa="POSTING_CARD_PRICE"]',
            '.price',
            '[class*="price"]',
        ]

        for selector in selectors:
            text = self.extract_text(selector)
            if 'USD' in text or 'U$S' in text or 'dólar' in text.lower():
                return "USD"
            if 'ARS' in text or '$' in text or 'peso' in text.lower():
                return "ARS"

        return "USD"

    def _extract_property_type(self) -> str:
        """Extract property type"""
        title = self._extract_title().lower()
        desc = self._extract_description().lower()
        combined = f"{title} {desc}"

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

    def _extract_operation_type_from_url(self) -> Optional[str]:
        """Extract operation type from URL path"""
        url_lower = self.url.lower()

        if '/alquiler-temporario' in url_lower or '/temporal' in url_lower:
            return "alquiler_temporal"
        elif '/alquiler' in url_lower:
            return "alquiler"
        elif '/venta' in url_lower:
            return "venta"

        return None

    def _extract_operation_type(self) -> str:
        """Extract operation type with prioritized sources"""
        # Priority 1: URL path
        url_operation = self._extract_operation_type_from_url()
        if url_operation:
            return url_operation

        # Priority 2: Text mining
        title = self._extract_title().lower()
        desc = self._extract_description().lower()
        combined = f"{title} {desc}"

        if 'alquiler temporario' in combined or 'alquiler temporal' in combined:
            return "alquiler_temporal"
        elif 'venta' in combined or 'vende' in combined or 'en venta' in combined:
            return "venta"
        elif 'alquiler' in combined or 'alquila' in combined:
            return "alquiler"

        return "venta"

    def _extract_location(self) -> Dict[str, Any]:
        """Extract location data"""
        selectors = [
            '[data-qa="POSTING_CARD_LOCATION"]',
            '.location',
            '[class*="location"]',
            '.posting-location',
        ]

        location_text = ""
        for selector in selectors:
            location_text = self.extract_text(selector)
            if location_text:
                break

        # Parse location (format varies: "Palermo, Capital Federal")
        parts = [p.strip() for p in location_text.split(',')]

        return {
            "neighborhood": parts[0] if len(parts) > 0 else "",
            "city": parts[1] if len(parts) > 1 else "Buenos Aires",
            "province": parts[2] if len(parts) > 2 else "Buenos Aires",
        }

    def _extract_address(self) -> str:
        """Extract street address"""
        selectors = [
            '[class*="address"]',
            '.street-address',
            '[data-qa="POSTING_CARD_ADDRESS"]',
        ]

        for selector in selectors:
            addr = self.extract_text(selector)
            if addr:
                return addr

        return ""

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
            return urljoin(self.url, img_url)

    def _extract_images(self) -> List[str]:
        """Extract image URLs"""
        images = []

        if not self.soup:
            return images

        # Strategy 1: JSON-LD structured data (most reliable for Zonaprop)
        scripts = self.soup.find_all('script', type='application/ld+json')
        for script in scripts:
            try:
                if script.string and 'image' in script.string:
                    data = json.loads(script.string)
                    if isinstance(data, dict) and 'image' in data:
                        img_data = data['image']
                        if isinstance(img_data, list):
                            for img_url in img_data:
                                normalized = self._normalize_image_url(img_url)
                                if normalized and self._is_valid_property_image(normalized):
                                    images.append(normalized)
                        elif isinstance(img_data, str):
                            normalized = self._normalize_image_url(img_data)
                            if normalized and self._is_valid_property_image(normalized):
                                images.append(normalized)
            except (json.JSONDecodeError, AttributeError):
                continue

        # Strategy 2: Multiple image attributes (fallback)
        if len(images) < 3:  # Only if JSON-LD didn't provide enough
            image_attrs = ['src', 'data-src', 'data-original', 'data-lazy', 'data-lazy-src']

            # Zonaprop selectors
            selectors = [
                '[class*="gallery"] img',
                '[class*="slider"] img',
                '[class*="carousel"] img',
                'picture img',
            ]

            for selector in selectors:
                imgs = self.soup.select(selector)
                for img in imgs:
                    for attr in image_attrs:
                        img_url = img.get(attr)
                        if img_url:
                            normalized = self._normalize_image_url(img_url)
                            if normalized and self._is_valid_property_image(normalized):
                                images.append(normalized)
                            break

        # Remove duplicates while preserving order
        seen = set()
        unique_images = []
        for img in images:
            if img not in seen:
                seen.add(img)
                unique_images.append(img)

        return unique_images[:20]

    def _is_valid_property_image(self, url: str) -> bool:
        """Check if URL is a valid property image (not icon/logo/svg)"""
        if not url:
            return False

        url_lower = url.lower()

        # Exclude SVGs, icons, logos
        invalid_patterns = [
            '.svg',
            'icon-',
            'logo',
            'fav-icon',
            'bell.',
            'dots.',
            'app-store',
            'google-play',
            'data-fiscal',
        ]

        for pattern in invalid_patterns:
            if pattern in url_lower:
                return False

        # Valid extensions
        valid_extensions = ['.jpg', '.jpeg', '.png', '.webp']
        has_valid_ext = any(ext in url_lower for ext in valid_extensions)

        return has_valid_ext

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

        # Zonaprop stores features in h2.title-type-sup-property
        # Format: "Departamento • 96m² • 4 ambientes • 1 cochera"
        h2 = self.soup.find('h2', class_='title-type-sup-property')
        if h2:
            text = h2.get_text().lower()

            # Extract ambientes (bedrooms)
            amb_match = re.search(r'(\d+)\s*ambiente', text)
            if amb_match:
                features['bedrooms'] = int(amb_match.group(1))

            # Extract cochera
            coch_match = re.search(r'(\d+)\s*cochera', text)
            if coch_match:
                features['parking_spaces'] = int(coch_match.group(1))

            # Extract area from h2
            area_match = re.search(r'(\d+)\s*m', text)
            if area_match:
                features['covered_area'] = float(area_match.group(1))

        # Extract from li.icon-feature elements
        # These contain: "108 m² tot.", "96 m² cub.", "2 baños"
        for li in self.soup.find_all('li', class_='icon-feature'):
            text = li.get_text().strip().lower()

            # Total area
            if 'm² tot' in text or 'm2 tot' in text:
                match = re.search(r'(\d+)', text)
                if match:
                    features['total_area'] = float(match.group(1))

            # Covered area
            elif 'm² cub' in text or 'm2 cub' in text:
                match = re.search(r'(\d+)', text)
                if match:
                    features['covered_area'] = float(match.group(1))

            # Bathrooms
            elif 'baño' in text:
                match = re.search(r'(\d+)', text)
                if match:
                    features['bathrooms'] = int(match.group(1))

            # Dormitorios
            elif 'dormitorio' in text:
                match = re.search(r'(\d+)', text)
                if match:
                    features['bedrooms'] = int(match.group(1))

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

    def _extract_number_feature(self, keywords: List[str]) -> Optional[int]:
        """Extract numeric feature"""
        text = f"{self._extract_title()} {self._extract_description()}".lower()

        for keyword in keywords:
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
            pattern = rf'(\d+(?:[.,]\d+)?)\s*(?:m2|m²|mts²|metros)?[\s-]*{keyword}|{keyword}[:\s]+(\d+(?:[.,]\d+)?)\s*(?:m2|m²|mts²)?'
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
            '[data-qa="PUBLISHER_NAME"]',
            '.agency-name',
            '[class*="inmobiliaria"]',
            '.publisher-name',
        ]

        for selector in selectors:
            agency = self.extract_text(selector)
            if agency:
                contact['real_estate_agency'] = agency
                break

        # Extract phone
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
        # Zonaprop URLs contain ID at the end: .../propiedades/.../12345678.html
        match = re.search(r'/(\d+)\.html', self.url)
        if match:
            return match.group(1)

        # Fallback
        parts = self.url.rstrip('/').split('/')
        for part in reversed(parts):
            if part.replace('.html', '').isdigit():
                return part.replace('.html', '')

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
            if keyword in title_text or keyword in page_text[:500]:
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
