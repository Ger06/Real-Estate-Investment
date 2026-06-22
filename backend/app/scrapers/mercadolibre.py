"""
MercadoLibre Scraper
Extracts property data from inmuebles.mercadolibre.com.ar / departamento.mercadolibre.com.ar

Strategy:
1. curl_cffi / httpx HTML fetch (Chrome TLS fingerprint, via BaseScraper)
2. Selenium as fallback (only when Chrome is available, e.g. local development)

Note: ML Items API via client_credentials does not grant item-read permission for
real estate listings (always returns 403). HTML parsing is the only viable strategy.
"""
import re
import json
import asyncio
import time
import logging
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse
from .base import BaseScraper
from .utils import clean_price as _clean_price

logger = logging.getLogger(__name__)


class MercadoLibreScraper(BaseScraper):
    """
    Scraper for MercadoLibre portal.

    Strategy:
    1. curl_cffi / httpx HTML fetch (Chrome TLS fingerprint, via BaseScraper)
    2. Selenium as fallback when HTTP returns a short/bot-detection page
    """

    DOMAINS = ["mercadolibre.com.ar"]

    def validate_url(self) -> bool:
        """Check if URL is from MercadoLibre"""
        parsed = urlparse(self.url)
        return any(domain in parsed.netloc for domain in self.DOMAINS)

    async def scrape(self) -> Dict[str, Any]:
        """
        Fetch HTML page and extract property data.
        Falls back to Selenium if curl_cffi/httpx returns a short/invalid response.
        """
        if not self.validate_url():
            raise ValueError(f"URL not from MercadoLibre: {self.url}")

        try:
            html = await self.fetch_page()
            if html:
                self.parse_html(html)
        except Exception as e:
            logger.warning(f"[mercadolibre] HTML fetch failed (non-fatal): {e}")

        data = self.extract_data()
        data['source_url'] = self.url

        logger.info(
            f"[mercadolibre] extracted price={data.get('price')}, "
            f"currency={data.get('currency')}, title={str(data.get('title', ''))[:50]}"
        )
        return data

    async def fetch_page(self) -> str:
        """
        Fetch page HTML.
        Level 1: curl_cffi / httpx via BaseScraper.
        Level 2: Selenium fallback (only if Chrome is installed).
        """
        try:
            html = await super().fetch_page()
            if len(html) > 5000 and self._is_ml_product_page(html):
                logger.info(f"[mercadolibre] HTML fetch OK, length: {len(html)}")
                return html
            logger.warning(
                f"[mercadolibre] HTML short/invalid (len={len(html)}), trying Selenium..."
            )
        except Exception as e:
            logger.warning(f"[mercadolibre] HTTP fetch failed: {e}, trying Selenium...")

        # Level 2: Selenium fallback
        return await asyncio.to_thread(self._fetch_with_selenium)

    def _is_ml_product_page(self, html: str) -> bool:
        """Check the fetched HTML actually contains ML product content."""
        return any(marker in html for marker in [
            'ui-pdp', 'andes-money-amount', 'application/ld+json',
            'mercadolibre', 'ui-vip',
        ])

    def _fetch_with_selenium(self) -> str:
        """
        Fetch page using Chrome headless with anti-bot flags.
        Raises RuntimeError if Chrome/ChromeDriver is not installed.
        """
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.webdriver.common.by import By
        except ImportError:
            raise RuntimeError(
                "[mercadolibre] selenium not installed — cannot use Selenium fallback"
            )

        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

        try:
            driver = webdriver.Chrome(options=options)
        except Exception as e:
            raise RuntimeError(f"[mercadolibre] Chrome not available: {e}")

        try:
            driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
                "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            })
            driver.get(self.url)
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.webdriver.common.by import By
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            time.sleep(3)
            html = driver.page_source
            logger.info(f"[mercadolibre] Selenium OK, length: {len(html)}")
            return html
        finally:
            driver.quit()

    def extract_data(self) -> Dict[str, Any]:
        """Extract all property data from HTML and JSON-LD."""
        api = None  # ML API not used (client_credentials lacks item-read permission)
        json_ld = self._extract_json_ld() if self.soup else None
        address_info = self._extract_address_details()

        data = {
            "source": "mercadolibre",
            "title": self._extract_title(api, json_ld),
            "description": self._extract_description(),
            "price": self._extract_price(api, json_ld),
            "currency": self._extract_currency(api, json_ld),
            "property_type": self._extract_property_type(),
            "operation_type": self._extract_operation_type(),
            "location": self._extract_location(),
            "address": address_info.get('full_address', ''),
            "street": address_info.get('street', ''),
            "street_number": address_info.get('street_number', ''),
            "images": self._extract_images(api, json_ld),
            "features": self._extract_features(api),
            "contact": self._extract_contact(),
            "source_id": self._extract_source_id(),
            "status": self._extract_status(api, json_ld),
        }

        return data

    def _extract_json_ld(self) -> Optional[Dict[str, Any]]:
        """Extract data from JSON-LD structured data.
        JSON-LD can be a single object OR an array of objects — both are valid.
        Accepts any @type that contains an offers.price (ML real estate uses
        @type Offer or Product, not always Product).
        """
        if not self.soup:
            return None

        scripts = self.soup.find_all('script', type='application/ld+json')
        for script in scripts:
            if not script.string:
                continue
            try:
                data = json.loads(script.string)
                # Normalise to list so both formats are handled identically
                candidates = data if isinstance(data, list) else [data]
                for item in candidates:
                    if not isinstance(item, dict):
                        continue
                    # Accept any @type that has offers.price
                    offers = item.get('offers', {})
                    if isinstance(offers, dict) and offers.get('price') is not None:
                        return item
                    # Fallback: accept @type Product even without offers (original behaviour)
                    if item.get('@type') == 'Product':
                        return item
            except (json.JSONDecodeError, AttributeError):
                continue

        return None

    def _extract_title(self, api: Optional[Dict[str, Any]], json_ld: Optional[Dict[str, Any]]) -> str:
        """Extract property title. API > JSON-LD > h1."""
        if api and api.get('title'):
            return api['title']
        if json_ld and 'name' in json_ld:
            return json_ld['name']
        h1 = self.soup.find('h1') if self.soup else None
        if h1:
            return h1.get_text(strip=True)
        return "Propiedad sin título"

    def _extract_description(self) -> str:
        """Extract property description from HTML."""
        if self.soup:
            for selector in ['.ui-pdp-description__content', '[class*="description"]', '#description']:
                desc_elem = self.soup.select_one(selector)
                if desc_elem:
                    desc = desc_elem.get_text(strip=True)
                    if len(desc) > 50:
                        return desc
        return ""

    def _extract_price(self, api: Optional[Dict[str, Any]], json_ld: Optional[Dict[str, Any]]) -> Optional[float]:
        """
        Extract price.
        Priority: API > JSON-LD > HTML selectors.
        """
        # Strategy 1: ML API
        if api and api.get('price') is not None:
            try:
                return float(api['price'])
            except (ValueError, TypeError):
                pass

        # Strategy 2: JSON-LD
        if json_ld and 'offers' in json_ld:
            offers = json_ld['offers']
            if isinstance(offers, dict) and 'price' in offers:
                try:
                    return float(offers['price'])
                except (ValueError, TypeError):
                    pass

        # Strategy 3–5: HTML fallbacks
        if not self.soup:
            logger.warning(f"[mercadolibre] _extract_price: no price found for {self.url[:80]}")
            return None

        price_spans = self.soup.find_all('span', class_=lambda x: x and 'price' in str(x).lower())
        for span in price_spans:
            price_amount, _ = _clean_price(span.get_text(strip=True))
            if price_amount:
                return price_amount

        fraction = self.soup.select_one('span.andes-money-amount__fraction')
        if fraction:
            currency_sym = self.soup.select_one('span.andes-money-amount__currency-symbol')
            prefix = currency_sym.get_text(strip=True) if currency_sym else ''
            price_amount, _ = _clean_price(f"{prefix}{fraction.get_text(strip=True)}")
            if price_amount:
                return price_amount

        price_container = self.soup.select_one('div.ui-pdp-price, [class*="price__main"]')
        if price_container:
            price_amount, _ = _clean_price(price_container.get_text(strip=True))
            if price_amount:
                return price_amount

        logger.warning(f"[mercadolibre] _extract_price: no price found for {self.url[:80]}")
        return None

    def _extract_currency(self, api: Optional[Dict[str, Any]], json_ld: Optional[Dict[str, Any]]) -> str:
        """Extract currency. Priority: API > JSON-LD > HTML."""
        if api and api.get('currency_id'):
            currency = api['currency_id']
            if currency in ('USD', 'ARS'):
                return currency

        if json_ld and 'offers' in json_ld:
            offers = json_ld['offers']
            if isinstance(offers, dict) and 'priceCurrency' in offers:
                currency = offers['priceCurrency']
                if currency in ('USD', 'ARS'):
                    return currency

        if not self.soup:
            return "USD"

        sym_elem = self.soup.select_one('span.andes-money-amount__currency-symbol')
        if sym_elem:
            sym = sym_elem.get_text(strip=True)
            if 'US$' in sym or 'USD' in sym:
                return 'USD'
            if 'AR$' in sym or '$' in sym:
                return 'ARS'

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
        title = self._extract_title(None, None).lower()
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
        title = self._extract_title(None, None).lower()
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

        location_elem = self.soup.select_one('.ui-vip-location__subtitle')
        if location_elem:
            location_text = location_elem.get_text(strip=True)
            # Format: "Armenia Al 2100, Palermo, Capital Federal, Capital Federal"
            parts = [p.strip() for p in location_text.split(',')]

            if len(parts) >= 2:
                neighborhood = parts[1] if len(parts) > 1 else parts[0]

            if len(parts) >= 3:
                city = parts[2]

            if len(parts) >= 4:
                province = parts[3]

        # Fallback: extract from title
        if not neighborhood:
            title = self._extract_title(None, None)
            match = re.search(
                r'(Palermo|Belgrano|Recoleta|Caballito|Villa Crespo|Colegiales|Núñez|Almagro|San Telmo|La Boca)',
                title, re.IGNORECASE
            )
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

        location_elem = self.soup.select_one('.ui-vip-location__subtitle')
        if location_elem:
            location_text = location_elem.get_text(strip=True)
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
        match = re.match(r'^(.+?)\s+(?:Al\s+)?(\d+)\s*$', address, re.IGNORECASE)
        if match:
            result['street'] = match.group(1).strip()
            result['street_number'] = match.group(2)
        else:
            result['street'] = address

    def _extract_address(self) -> str:
        """Extract street address (legacy compatibility)"""
        return self._extract_address_details().get('full_address', '')

    def _extract_images(self, api: Optional[Dict[str, Any]], json_ld: Optional[Dict[str, Any]]) -> List[str]:
        """Extract image URLs. Priority: API pictures > JSON-LD > HTML gallery."""
        images = []
        seen = set()

        def _add(url: str) -> None:
            if url and url not in seen:
                lower = url.lower()
                if any(skip in lower for skip in ['frontend-assets', 'default', 'exhibitor', 'placeholder', 'logo', '.svg']):
                    return
                seen.add(url)
                # Upgrade ML image resolution: -O (small) -> -F (full size)
                upgraded = re.sub(r'-[A-Z]\.(\w+)$', r'-F.\1', url)
                images.append(upgraded)

        # Strategy 1: ML API pictures array
        if api and 'pictures' in api:
            for pic in api['pictures']:
                url = pic.get('secure_url') or pic.get('url', '')
                _add(url)

        # Strategy 2: JSON-LD images
        if not images and json_ld and 'image' in json_ld:
            img_data = json_ld['image']
            if isinstance(img_data, list):
                for img in img_data:
                    _add(img)
            elif isinstance(img_data, str):
                _add(img_data)

        # Strategy 3: HTML img tags from gallery/carousel
        if self.soup:
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

        # Strategy 4: Search all img tags with mlstatic
        if not images and self.soup:
            for img in self.soup.find_all('img'):
                for attr in ['data-src', 'src']:
                    val = img.get(attr, '')
                    if 'http2.mlstatic.com' in val and '/D_' in val:
                        _add(val)
                        break

        # Strategy 5: og:image as last resort
        if not images and self.soup:
            og = self.soup.find('meta', property='og:image')
            if og:
                _add(og.get('content', ''))

        return images[:20]

    def _extract_features(self, api: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract property features. Priority: API attributes > HTML specs table."""
        features: Dict[str, Any] = {
            "bedrooms": None,
            "bathrooms": None,
            "parking_spaces": None,
            "covered_area": None,
            "total_area": None,
        }

        # Strategy 1: ML API attributes array
        if api and 'attributes' in api:
            attr_map = {
                'superficie total': 'total_area',
                'total surface': 'total_area',
                'superficie cubierta': 'covered_area',
                'covered surface': 'covered_area',
                'dormitorios': 'bedrooms',
                'bedrooms': 'bedrooms',
                'ambientes': 'bedrooms',
                'baños': 'bathrooms',
                'bathrooms': 'bathrooms',
                'cocheras': 'parking_spaces',
                'garage': 'parking_spaces',
                'parking': 'parking_spaces',
            }
            for attr in api['attributes']:
                name_lower = attr.get('name', '').lower()
                for key, field in attr_map.items():
                    if key in name_lower and features[field] is None:
                        # Prefer value_struct (has unit info) over value_name string
                        value_struct = attr.get('value_struct')
                        if value_struct and value_struct.get('number') is not None:
                            val = value_struct['number']
                        else:
                            val_str = attr.get('value_name', '')
                            try:
                                val = float(str(val_str).replace(',', '.'))
                            except (ValueError, AttributeError):
                                continue
                        features[field] = int(val) if field in ('bedrooms', 'bathrooms', 'parking_spaces') else float(val)
                        break

        # Strategy 2: HTML specs table (only for fields not filled by API)
        if not self.soup:
            features['amenities'] = []
            return features

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
                    row_text = row.get_text(' ', strip=True).lower()
                    spec_items.append(row_text)
                break

        for selector in ['[class*="specs"] li', '[class*="attribute"] li', '[class*="features"] li']:
            items = self.soup.select(selector)
            for item in items:
                spec_items.append(item.get_text(' ', strip=True).lower())

        for item in spec_items:
            if features['total_area'] is None and ('superficie total' in item or 'sup. total' in item):
                m = re.search(r'(\d+(?:[.,]\d+)?)', item)
                if m:
                    features['total_area'] = float(m.group(1).replace(',', '.'))

            if features['covered_area'] is None and ('superficie cubierta' in item or 'sup. cubierta' in item or 'cubiertos' in item):
                m = re.search(r'(\d+(?:[.,]\d+)?)', item)
                if m:
                    features['covered_area'] = float(m.group(1).replace(',', '.'))

            if features['bedrooms'] is None and ('dormitorio' in item or 'habitaci' in item):
                m = re.search(r'(\d+)', item)
                if m:
                    features['bedrooms'] = int(m.group(1))

            if features['bedrooms'] is None and 'ambiente' in item:
                m = re.search(r'(\d+)', item)
                if m:
                    features['bedrooms'] = int(m.group(1))

            if features['bathrooms'] is None and 'baño' in item:
                m = re.search(r'(\d+)', item)
                if m:
                    features['bathrooms'] = int(m.group(1))

            if features['parking_spaces'] is None and ('cochera' in item or 'estacionamiento' in item):
                m = re.search(r'(\d+)', item)
                if m:
                    features['parking_spaces'] = int(m.group(1))

        # Strategy 3: Full page text regex fallback
        if not any([features['total_area'], features['covered_area'], features['bedrooms']]):
            text = self.soup.get_text()

            if features['bedrooms'] is None:
                bed_match = re.search(r'(\d+)\s*dormitorio|(\d+)\s*ambiente', text, re.IGNORECASE)
                if bed_match:
                    features['bedrooms'] = int(bed_match.group(1) or bed_match.group(2))

            if features['bathrooms'] is None:
                bath_match = re.search(r'(\d+)\s*baño', text, re.IGNORECASE)
                if bath_match:
                    features['bathrooms'] = int(bath_match.group(1))

            if features['parking_spaces'] is None:
                parking_match = re.search(r'(\d+)\s*cochera', text, re.IGNORECASE)
                if parking_match:
                    features['parking_spaces'] = int(parking_match.group(1))

            if features['total_area'] is None:
                area_match = re.search(r'(\d+(?:[.,]\d+)?)\s*m[²2]?\s*totales?', text, re.IGNORECASE)
                if area_match:
                    features['total_area'] = float(area_match.group(1).replace(',', '.'))

            if features['covered_area'] is None:
                area_cub_match = re.search(r'(\d+(?:[.,]\d+)?)\s*m[²2]?\s*cubiertos?', text, re.IGNORECASE)
                if area_cub_match:
                    features['covered_area'] = float(area_cub_match.group(1).replace(',', '.'))

        # Extract amenities from description
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
        return {
            "real_estate_agency": "",
            "phone": "",
            "email": "",
        }

    def _extract_source_id(self) -> str:
        """Extract property ID from URL"""
        match = re.search(r'MLA-?(\d+)', self.url)
        if match:
            return f"MLA{match.group(1)}"

        parts = self.url.rstrip('/').split('/')
        return parts[-1] if parts else ""

    def _extract_status(self, api: Optional[Dict[str, Any]], json_ld: Optional[Dict[str, Any]]) -> str:
        """
        Extract property status. Priority: API status > JSON-LD > page text keywords.
        """
        # Strategy 1: ML API status field
        if api and api.get('status'):
            api_status = api['status'].lower()
            if api_status == 'active':
                return "active"
            elif api_status in ('paused', 'closed', 'deleted', 'inactive'):
                return "removed"

        # Strategy 2: JSON-LD availability
        if json_ld:
            offers = json_ld.get("offers", {})
            availability = offers.get("availability", "").lower()
            if "outofstock" in availability or "discontinued" in availability:
                return "removed"
            if "sold" in availability:
                return "sold"

        # Strategy 3: page text keywords
        if self.soup:
            page_text = self.soup.get_text().lower()

            removed_keywords = [
                'finalizada', 'finalizó', 'finalizo',
                'publicación ya finalizó', 'publicacion ya finalizo',
                'esta publicación finalizó', 'vencida',
            ]
            sold_keywords = ['vendido', 'vendida', 'sold', 'no disponible', 'pausado']
            rented_keywords = ['alquilado', 'alquilada', 'rented']
            reserved_keywords = ['reservado', 'reservada', 'reserved']

            for keyword in removed_keywords:
                if keyword in page_text:
                    return "removed"

            for keyword in sold_keywords:
                if keyword in page_text[:500]:
                    return "sold"
            for keyword in rented_keywords:
                if keyword in page_text[:500]:
                    return "rented"
            for keyword in reserved_keywords:
                if keyword in page_text[:500]:
                    return "reserved"

            status_selectors = [
                '.ui-pdp-header__status',
                '[class*="status"]',
                '.ui-pdp-badge',
            ]
            for selector in status_selectors:
                status_elem = self.soup.select_one(selector)
                if status_elem:
                    status_text = status_elem.get_text().lower()
                    for keyword in removed_keywords:
                        if keyword in status_text:
                            return "removed"
                    for keyword in sold_keywords:
                        if keyword in status_text:
                            return "sold"
                    for keyword in reserved_keywords:
                        if keyword in status_text:
                            return "reserved"

        return "active"
