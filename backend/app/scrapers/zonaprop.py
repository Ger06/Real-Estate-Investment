"""
Zonaprop Scraper
Extracts property data from www.zonaprop.com.ar
Uses curl_cffi for Cloudflare bypass, Selenium as last resort.
"""
import re
import json
import logging
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
from .base import BaseScraper
from .http_client import fetch_with_browser_fingerprint

logger = logging.getLogger(__name__)


class ZonapropScraper(BaseScraper):
    """Scraper for Zonaprop portal. Uses curl_cffi for Cloudflare bypass, Selenium as last resort."""

    DOMAIN = "zonaprop.com.ar"

    def validate_url(self) -> bool:
        """Check if URL is from Zonaprop"""
        parsed = urlparse(self.url)
        return self.DOMAIN in parsed.netloc

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
            if len(html) > 5000 and 'cf-browser-verification' not in html:
                logger.info("[zonaprop] fetch_with_browser_fingerprint OK")
                return html
            logger.warning("[zonaprop] Got Cloudflare challenge, trying Selenium...")
        except Exception as e:
            logger.warning(f"[zonaprop] HTTP fetch failed: {e}, trying Selenium...")

        # Level 3: Selenium (only works locally with Chrome installed)
        return self._fetch_with_selenium()

    def _fetch_with_selenium(self) -> str:
        """Fetch page using Selenium, handling Cloudflare JS challenges."""
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

        import time

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

            # Wait for Cloudflare JS challenge to resolve
            cf_markers = [
                'Just a moment', 'Checking your browser',
                'cf-browser-verification', '__cf_chl_',
                'challenge-platform', 'cf-turnstile',
            ]
            for i in range(20):
                page_src = driver.page_source
                if any(marker in page_src for marker in cf_markers):
                    logger.debug(f"[zonaprop] Cloudflare challenge active, waiting... ({i+1}s)")
                    time.sleep(1)
                else:
                    logger.info(f"[zonaprop] Cloudflare challenge resolved after {i}s")
                    break

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

        # Check if page was redirected to a different property
        redirect_warning = self._detect_redirect()

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

        if redirect_warning:
            data["warning"] = redirect_warning

        return data

    def _detect_redirect(self) -> Optional[str]:
        """
        Detect if Zonaprop redirected to a different property.
        Returns a warning message if redirect detected, None otherwise.
        """
        # Extract expected ID from URL
        url_id_match = re.search(r'-(\d+)\.html', self.url)
        expected_id = url_id_match.group(1) if url_id_match else None

        if not expected_id:
            return None

        # Check canonical URL or page content for actual ID
        if self.soup:
            # Check canonical link
            canonical = self.soup.find('link', rel='canonical')
            if canonical and canonical.get('href'):
                canonical_match = re.search(r'-(\d+)\.html', canonical['href'])
                actual_id = canonical_match.group(1) if canonical_match else None

                if actual_id and actual_id != expected_id:
                    return f"Posible redirección: URL solicitada ID={expected_id}, página muestra ID={actual_id}. La propiedad original puede haber sido removida."

            # Also check URL keywords vs page title
            url_lower = self.url.lower()
            title_tag = self.soup.find('title')
            page_title = title_tag.get_text().lower() if title_tag else ""

            # Check for CABA/Capital Federal mismatch
            if ('capital-federal' in url_lower or 'coghlan' in url_lower or 'palermo' in url_lower) \
                    and ('rosario' in page_title or 'santa fe' in page_title or 'cordoba' in page_title):
                return "Posible redirección: La URL indica Capital Federal pero la página muestra otra provincia. La propiedad original puede haber sido removida."

        return None

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

    def _extract_property_type_from_url(self) -> Optional[str]:
        """Extract property type from URL path (most reliable)"""
        url_lower = self.url.lower()

        # Zonaprop URLs: /propiedades/ph-..., /propiedades/departamento-..., etc.
        if '/ph-' in url_lower or '/ph/' in url_lower or '-ph-' in url_lower:
            return "ph"
        elif '/departamento' in url_lower or '-departamento' in url_lower:
            return "departamento"
        elif '/casa' in url_lower or '-casa-' in url_lower:
            return "casa"
        elif '/terreno' in url_lower or '/lote' in url_lower:
            return "terreno"
        elif '/local' in url_lower:
            return "local"
        elif '/oficina' in url_lower:
            return "oficina"
        elif '/cochera' in url_lower:
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
        if not self.soup:
            return {"neighborhood": "", "city": "Buenos Aires", "province": "Buenos Aires"}

        neighborhood = ""
        city = ""
        province = "Buenos Aires"

        # Strategy 1: Look for h4 with full address (most reliable for Zonaprop)
        # Format: "Superí 2900, Coghlan, Capital Federal"
        for h4 in self.soup.find_all('h4'):
            text = h4.get_text(strip=True)
            if 'capital federal' in text.lower() or 'buenos aires' in text.lower():
                parts = [p.strip() for p in text.split(',') if p.strip()]
                if len(parts) >= 2:
                    # Last part is city, second to last is neighborhood
                    city = parts[-1]
                    neighborhood = parts[-2] if len(parts) >= 2 else ""
                    break

        # Strategy 2: Try breadcrumbs (order: Province -> City -> Neighborhoods... -> Title)
        if not neighborhood:
            breadcrumbs = self.soup.select('nav[class*="breadcrumb"] a, .breadcrumb a')
            if len(breadcrumbs) >= 2:
                parts = [b.get_text(strip=True) for b in breadcrumbs if b.get_text(strip=True)]
                # Filter out navigation items
                skip_items = ['zonaprop', 'home', 'inicio', 'inmuebles', 'propiedades',
                              'ph', 'departamentos', 'casas', 'comprar', 'alquilar', 'venta', 'alquiler',
                              'departamento', 'casa', 'terreno', 'local', 'oficina', 'cochera']
                filtered = [p for p in parts if p.lower() not in skip_items]

                # Last item is often the property title (long text), exclude it
                # Property titles are usually longer than location names
                if filtered and len(filtered[-1]) > 50:
                    filtered = filtered[:-1]

                # Zonaprop breadcrumb order: Province -> City -> Area -> Neighborhood
                # Examples:
                #   Santa Fe -> Rosario -> Distrito Centro -> Abasto
                #   Buenos Aires -> Capital Federal -> Coghlan
                if len(filtered) >= 2:
                    # Look for Capital Federal or province indicators
                    for i, part in enumerate(filtered):
                        part_lower = part.lower()
                        if part_lower in ['capital federal', 'caba', 'buenos aires ciudad']:
                            city = "Capital Federal"
                            province = "Capital Federal"
                            # Everything after this is neighborhood info
                            if i + 1 < len(filtered):
                                neighborhood = filtered[-1]  # Take last as most specific
                            break
                        elif part_lower in ['buenos aires', 'santa fe', 'cordoba', 'mendoza']:
                            province = part
                            # Next item is likely city
                            if i + 1 < len(filtered):
                                city = filtered[i + 1]
                            # Last item is neighborhood
                            if i + 2 < len(filtered):
                                neighborhood = filtered[-1]
                            break
                    else:
                        # Fallback: assume second to last is city, last is neighborhood
                        city = filtered[-2] if len(filtered) >= 2 else ""
                        neighborhood = filtered[-1] if filtered else ""
                elif len(filtered) == 1:
                    city = filtered[0]

        # Strategy 3: Look for spans with location info
        if not neighborhood:
            # Find span containing neighborhood near "Capital Federal"
            for span in self.soup.find_all('span'):
                text = span.get_text(strip=True)
                if text and len(text) < 30:
                    if text.lower() == 'capital federal':
                        city = text
                    elif text.lower() in ['coghlan', 'palermo', 'belgrano', 'recoleta', 'caballito',
                                          'villa crespo', 'nunez', 'nuñez', 'almagro', 'san telmo',
                                          'villa urquiza', 'saavedra', 'chacarita', 'villa devoto',
                                          'flores', 'floresta', 'boedo', 'barracas']:
                        neighborhood = text

        # Strategy 4: Try specific Zonaprop selectors
        if not neighborhood:
            selectors = [
                'h2.title-location',
                'h3.title-location',
                '.title-location',
            ]
            for selector in selectors:
                elem = self.soup.select_one(selector)
                if elem:
                    text = elem.get_text(strip=True)
                    if text and len(text) < 100:
                        parts = [p.strip() for p in text.split(',') if p.strip()]
                        if len(parts) >= 2:
                            neighborhood = parts[0]
                            city = parts[1]
                        break

        # Normalize
        if not city:
            city = "Buenos Aires"
        if "capital federal" in city.lower() or "caba" in city.lower():
            province = "Capital Federal"
            city = "Capital Federal"

        return {
            "neighborhood": neighborhood,
            "city": city,
            "province": province,
        }

    def _extract_address(self) -> str:
        """Extract street address"""
        if not self.soup:
            return ""

        # Strategy 1: Look for h4 with full address containing street number
        # Format: "Superí 2900, Coghlan, Capital Federal"
        for h4 in self.soup.find_all('h4'):
            text = h4.get_text(strip=True)
            # Check if it has a number (street number) and location keywords
            if any(c.isdigit() for c in text):
                if 'capital federal' in text.lower() or 'buenos aires' in text.lower() or ',' in text:
                    # Extract just the street part (before neighborhood)
                    parts = [p.strip() for p in text.split(',')]
                    if parts:
                        return parts[0]  # Return just "Superí 2900"

        # Strategy 2: Try specific Zonaprop selectors
        selectors = [
            'h3.title-address',
            'h4.title-address',
            '.title-address',
            '[data-qa="POSTING_CARD_ADDRESS"]',
            '[class*="address-title"]',
            '.street-address',
            '[class*="PostingAddress"]',
        ]

        for selector in selectors:
            elem = self.soup.select_one(selector)
            if elem:
                addr = elem.get_text(strip=True)
                if addr and len(addr) > 3:
                    return addr

        # Strategy 3: Look in JSON-LD structured data
        for script in self.soup.find_all('script', type='application/ld+json'):
            try:
                if script.string:
                    data = json.loads(script.string)
                    if isinstance(data, dict):
                        address = data.get('address', {})
                        if isinstance(address, dict):
                            street = address.get('streetAddress', '')
                            if street:
                                return street
            except (json.JSONDecodeError, AttributeError):
                continue

        # Strategy 4: Look for elements with address-like content
        for elem in self.soup.find_all(['p', 'span', 'div', 'h3', 'h4']):
            classes = elem.get('class', [])
            class_str = ' '.join(classes) if classes else ''

            if 'address' in class_str.lower() or 'direccion' in class_str.lower():
                text = elem.get_text(strip=True)
                if text and len(text) > 3 and len(text) < 200:
                    if any(c.isdigit() for c in text) or any(x in text.lower() for x in ['calle', 'av.', 'avenida', 'pasaje']):
                        return text

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
