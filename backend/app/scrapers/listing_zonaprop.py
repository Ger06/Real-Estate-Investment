"""
Zonaprop Listing Scraper
Scrapes search result pages from www.zonaprop.com.ar to extract property URLs
Uses curl_cffi for Cloudflare bypass, Selenium as last resort.
"""
import re
import logging
from typing import Dict, Any, List, Optional
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from .listing_base import BaseListingScraper
from .http_client import fetch_with_browser_fingerprint

logger = logging.getLogger(__name__)


class ZonapropListingScraper(BaseListingScraper):
    """
    Scraper for Zonaprop search results / listing pages.
    Uses Selenium to bypass Cloudflare protection.

    Builds URLs like:
    - https://www.zonaprop.com.ar/departamentos-venta-capital-federal.html
    - https://www.zonaprop.com.ar/departamentos-venta-palermo-capital-federal.html
    - https://www.zonaprop.com.ar/departamentos-venta-capital-federal-100000-200000-dolar.html
    - https://www.zonaprop.com.ar/departamentos-venta-capital-federal.html?pagina=2
    """

    PORTAL_NAME = "zonaprop"
    BASE_URL = "https://www.zonaprop.com.ar"
    MAX_PAGES = 10
    DELAY_BETWEEN_PAGES = 3.0  # Longer delay for Selenium

    # Mapping for property types in URL
    PROPERTY_TYPE_MAP = {
        "departamento": "departamentos",
        "casa": "casas",
        "ph": "ph",
        "terreno": "terrenos",
        "local": "locales-comerciales",
        "oficina": "oficinas",
        "cochera": "cocheras",
        "galpon": "galpones",
        "fondo_comercio": "fondos-de-comercio",
        "campo": "campos",
        "quinta": "quintas",
    }

    # Mapping for operation types in URL
    OPERATION_TYPE_MAP = {
        "venta": "venta",
        "alquiler": "alquiler",
        "alquiler_temporal": "alquiler-temporario",
    }

    # Mapping for locations in URL (slug format)
    LOCATION_MAP = {
        # Capital Federal / CABA
        "capital federal": "capital-federal",
        "caba": "capital-federal",
        "buenos aires": "capital-federal",
        # GBA
        "zona norte": "zona-norte-buenos-aires",
        "zona sur": "zona-sur-buenos-aires",
        "zona oeste": "zona-oeste-buenos-aires",
        "gba norte": "zona-norte-buenos-aires",
        "gba sur": "zona-sur-buenos-aires",
        "gba oeste": "zona-oeste-buenos-aires",
        # Provinces
        "cordoba": "cordoba",
        "mendoza": "mendoza",
        "santa fe": "santa-fe",
        "rosario": "rosario",
        "mar del plata": "mar-del-plata",
        "tucuman": "tucuman",
        "salta": "salta",
    }

    # Common neighborhoods mapping
    NEIGHBORHOOD_MAP = {
        # CABA
        "palermo": "palermo",
        "recoleta": "recoleta",
        "belgrano": "belgrano",
        "caballito": "caballito",
        "almagro": "almagro",
        "villa crespo": "villa-crespo",
        "villa urquiza": "villa-urquiza",
        "villa del parque": "villa-del-parque",
        "villa devoto": "villa-devoto",
        "villa luro": "villa-luro",
        "villa pueyrredon": "villa-pueyrredon",
        "nunez": "nunez",
        "colegiales": "colegiales",
        "san telmo": "san-telmo",
        "puerto madero": "puerto-madero",
        "san nicolas": "san-nicolas",
        "monserrat": "monserrat",
        "barrio norte": "barrio-norte",
        "flores": "flores",
        "floresta": "floresta",
        "devoto": "devoto",
        "saavedra": "saavedra",
        "coghlan": "coghlan",
        "chacarita": "chacarita",
        "parque patricios": "parque-patricios",
        "boedo": "boedo",
        "la boca": "la-boca",
        "balvanera": "balvanera",
        "constitucion": "constitucion",
        "retiro": "retiro",
        "san cristobal": "san-cristobal",
        "once": "once",
        "microcentro": "microcentro",
        "liniers": "liniers",
        "mataderos": "mataderos",
        "paternal": "paternal",
    }

    def __init__(self, search_params: Dict[str, Any], user_agent: Optional[str] = None):
        super().__init__(search_params, user_agent)
        self.driver = None

    def _get_driver(self):
        """Create and return a configured Chrome WebDriver (lazy, only when Selenium fallback needed)"""
        if self.driver:
            return self.driver

        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options

        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument(f'user-agent={self.user_agent}')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--disable-gpu')

        self.driver = webdriver.Chrome(options=chrome_options)
        return self.driver

    def _close_driver(self):
        """Close the WebDriver"""
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
            self.driver = None

    def _slugify(self, text: str) -> str:
        """Convert text to URL-friendly slug"""
        if not text:
            return ""
        # Lowercase and replace spaces
        slug = text.lower().strip()
        # Replace accented characters
        replacements = {
            'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u',
            'ñ': 'n', 'ü': 'u',
        }
        for old, new in replacements.items():
            slug = slug.replace(old, new)
        # Replace spaces and special chars with hyphens
        slug = re.sub(r'[^a-z0-9]+', '-', slug)
        slug = slug.strip('-')
        return slug

    def build_search_url(self, page: int = 1) -> str:
        """
        Build Zonaprop search URL from parameters.

        URL structure:
        /[property_type]-[operation]-[neighborhood]-[location]-[filters].html?pagina=N

        Examples:
        - /departamentos-venta-capital-federal.html
        - /departamentos-venta-palermo-capital-federal.html
        - /casas-alquiler-zona-norte-buenos-aires-100000-200000-dolar.html
        """
        params = self.search_params

        # Build path segments (joined by hyphens in Zonaprop)
        segments = []

        # Property type (required, defaults to departamentos)
        property_type = params.get("property_type", "departamento").lower()
        if property_type in self.PROPERTY_TYPE_MAP:
            segments.append(self.PROPERTY_TYPE_MAP[property_type])
        else:
            segments.append("departamentos")  # Default

        # Operation type (required)
        operation = params.get("operation_type", "venta").lower()
        segments.append(self.OPERATION_TYPE_MAP.get(operation, "venta"))

        # Neighborhoods OR Location (not both - neighborhood implies location)
        neighborhoods = params.get("neighborhoods", [])
        if neighborhoods and len(neighborhoods) == 1:
            # If neighborhood is specified, use it (implies the city)
            neighborhood = neighborhoods[0].lower()
            neighborhood_slug = self.NEIGHBORHOOD_MAP.get(neighborhood, self._slugify(neighborhood))
            segments.append(neighborhood_slug)
        else:
            # No neighborhood, use city/province
            city = params.get("city", "").lower()
            province = params.get("province", "").lower()

            location = city or province
            if location:
                location_slug = self.LOCATION_MAP.get(location, self._slugify(location))
                segments.append(location_slug)

        # Build filter segments
        filter_segments = []

        # Price filters (format: min-max-currency)
        currency = params.get("currency", "USD").upper()
        currency_slug = "dolar" if currency == "USD" else "peso"

        min_price = params.get("min_price")
        max_price = params.get("max_price")

        if min_price or max_price:
            min_val = int(min_price) if min_price else 0
            max_val = int(max_price) if max_price else 99999999
            filter_segments.append(f"{min_val}-{max_val}-{currency_slug}")

        # Area filters (format: min-max-m2-cubiertos)
        min_area = params.get("min_area")
        max_area = params.get("max_area")

        if min_area or max_area:
            min_val = int(min_area) if min_area else 0
            max_val = int(max_area) if max_area else 9999
            filter_segments.append(f"{min_val}-{max_val}-m2-cubiertos")

        # Bedrooms filter (format: N-ambientes)
        min_bedrooms = params.get("min_bedrooms")
        max_bedrooms = params.get("max_bedrooms")

        if min_bedrooms and max_bedrooms and min_bedrooms == max_bedrooms:
            filter_segments.append(f"{int(min_bedrooms)}-ambientes")
        elif min_bedrooms:
            filter_segments.append(f"{int(min_bedrooms)}-ambientes-o-mas")

        # Build URL
        all_segments = segments + filter_segments
        url = f"{self.BASE_URL}/{'-'.join(all_segments)}.html"

        # Add pagination
        if page > 1:
            url += f"?pagina={page}"

        return url

    async def fetch_page(self, url: str) -> str:
        """
        Fetch page with 3-level fallback:
        1. curl_cffi with Chrome TLS fingerprint (works on Render without Chrome)
        2. httpx (fallback if curl_cffi not installed)
        3. Selenium (last resort, only works where Chrome is installed)
        """
        # Level 1+2: curl_cffi / httpx via base class
        try:
            html = await super().fetch_page(url)
            if len(html) > 5000 and 'cf-browser-verification' not in html:
                logger.info(f"[zonaprop] fetch_with_browser_fingerprint OK, length: {len(html)}")
                return html
            logger.warning("[zonaprop] Got Cloudflare challenge, trying Selenium...")
        except Exception as e:
            logger.warning(f"[zonaprop] HTTP fetch failed: {e}, trying Selenium...")

        # Level 3: Selenium fallback
        return self._fetch_with_selenium(url)

    def _fetch_with_selenium(self, url: str) -> str:
        """Fetch page using Selenium as last resort."""
        import time
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
        except ImportError:
            raise RuntimeError(
                "Neither curl_cffi nor Selenium+Chrome available. "
                "Install curl_cffi for production: pip install curl_cffi"
            )

        driver = self._get_driver()

        try:
            logger.info(f"[zonaprop] Selenium loading: {url}")
            driver.get(url)

            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )

            time.sleep(4)

            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, '[data-qa="posting PROPERTY"], .postingCard, [class*="PostingCard"]'))
                )
            except Exception:
                logger.debug("[zonaprop] No property cards found with expected selectors, continuing anyway")

            html = driver.page_source
            logger.info(f"[zonaprop] Got HTML via Selenium, length: {len(html)}")
            return html

        except Exception as e:
            logger.error(f"[zonaprop] Selenium error: {e}")
            raise

    async def scrape_all_pages(self, max_properties: int = 100) -> List[Dict[str, Any]]:
        """
        Scrape all pages using Selenium.
        Override to ensure driver is closed after scraping.
        """
        try:
            return await super().scrape_all_pages(max_properties)
        finally:
            self._close_driver()

    def extract_property_cards(self) -> List[Dict[str, Any]]:
        """
        Extract property listings from Zonaprop search results page.

        Returns list of dicts with:
        - source_url: Full property URL
        - source_id: Property ID from Zonaprop
        - title: Property title
        - price: Price amount
        - currency: USD or ARS
        - thumbnail_url: Main image thumbnail
        - location_preview: Neighborhood/city text
        """
        if not self.soup:
            return []

        cards = []

        # Zonaprop listing card selectors
        card_selectors = [
            'div[data-qa="posting PROPERTY"]',
            'div.postingCard',
            'div[class*="PostingCard"]',
            'article[data-posting-type]',
            'div[class*="posting-card"]',
            '[data-qa="posting"]',
        ]

        card_elements = []
        for selector in card_selectors:
            card_elements = self.soup.select(selector)
            if card_elements:
                logger.debug(f"Found {len(card_elements)} cards with selector: {selector}")
                print(f"[DEBUG] [zonaprop] Found {len(card_elements)} cards with selector: {selector}")
                break

        if not card_elements:
            # Fallback: look for any links to property pages
            print("[DEBUG] [zonaprop] No cards found with standard selectors, trying fallback...")

            # Zonaprop property URLs contain long numeric IDs
            property_links = self.soup.select('a[href*=".html"]')
            print(f"[DEBUG] [zonaprop] Found {len(property_links)} .html links")

            seen_urls = set()
            for link in property_links:
                href = link.get('href', '')
                if href and href not in seen_urls and self._is_property_url(href):
                    seen_urls.add(href)
                    full_url = urljoin(self.BASE_URL, href)
                    cards.append({
                        'source_url': full_url,
                        'source_id': self._extract_id_from_url(full_url),
                        'source': 'zonaprop',
                        'title': link.get_text(strip=True)[:200] or None,
                        'price': None,
                        'currency': None,
                        'thumbnail_url': None,
                        'location_preview': None,
                    })

            print(f"[DEBUG] [zonaprop] Fallback found {len(cards)} property URLs")
            return cards

        # Process each card
        for card in card_elements:
            try:
                card_data = self._parse_card(card)
                if card_data and card_data.get('source_url'):
                    cards.append(card_data)
            except Exception as e:
                logger.warning(f"Error parsing card: {e}")
                continue

        return cards

    def _is_property_url(self, url: str) -> bool:
        """Check if URL is a property detail page (not a listing/search page)"""
        if not url:
            return False

        # Zonaprop property URLs end with .html and contain numeric ID (8+ digits)
        # Example: /propiedades/departamento-en-venta-en-palermo-50123456.html
        has_html = '.html' in url
        has_long_id = bool(re.search(r'-(\d{7,})\.html', url))

        # Exclude search/listing pages (they have format like departamentos-venta-capital-federal.html)
        is_listing = bool(re.match(r'^/?(departamentos|casas|ph|terrenos|oficinas|locales|cocheras)-', url))

        return has_html and has_long_id and not is_listing

    def _extract_id_from_url(self, url: str) -> Optional[str]:
        """Extract property ID from URL"""
        # Zonaprop IDs are typically 8+ digit numbers at end of URL
        # Example: departamento-en-venta-en-palermo-50123456.html
        match = re.search(r'-(\d{7,})\.html', url)
        if match:
            return match.group(1)

        # Alternative: any long numeric segment
        match = re.search(r'(\d{7,})', url)
        if match:
            return match.group(1)

        return None

    def _parse_card(self, card) -> Optional[Dict[str, Any]]:
        """Parse a single property card element"""
        data = {
            'source': 'zonaprop',
            'source_url': None,
            'source_id': None,
            'title': None,
            'price': None,
            'currency': None,
            'thumbnail_url': None,
            'location_preview': None,
        }

        # Extract URL - look for main link
        link_selectors = [
            'a[data-qa="posting PROPERTY"]',
            'a[href*=".html"]',
            'a[class*="link"]',
            'a',
        ]

        link = None
        for selector in link_selectors:
            link = card.select_one(selector)
            if link and link.get('href'):
                href = link.get('href', '')
                # Verify it's a property URL (has long ID)
                if re.search(r'-\d{7,}\.html', href):
                    break
                link = None

        # If card itself is a link
        if not link and card.name == 'a' and card.get('href'):
            link = card

        if link:
            href = link.get('href', '')
            if href.startswith('/'):
                data['source_url'] = urljoin(self.BASE_URL, href)
            elif href.startswith('http'):
                data['source_url'] = href
            else:
                data['source_url'] = f"{self.BASE_URL}/{href}"

            data['source_id'] = self._extract_id_from_url(data['source_url'])

        if not data['source_url']:
            return None

        # Extract title
        title_selectors = [
            '[data-qa="POSTING_CARD_TITLE"]',
            '[data-qa="POSTING_CARD_LOCATION"]',
            'h2',
            'h3',
            '[class*="title"]',
            '[class*="Title"]',
        ]

        for selector in title_selectors:
            title_elem = card.select_one(selector)
            if title_elem:
                data['title'] = title_elem.get_text(strip=True)[:500]
                break

        # Extract price
        price_selectors = [
            '[data-qa="POSTING_CARD_PRICE"]',
            '[class*="Price"]',
            '[class*="price"]',
        ]

        for selector in price_selectors:
            price_elem = card.select_one(selector)
            if price_elem:
                price_text = price_elem.get_text(strip=True)
                price_amount, currency = self.clean_price(price_text)
                data['price'] = price_amount
                data['currency'] = currency
                break

        # Extract thumbnail
        img_selectors = [
            'img[data-qa]',
            'img[class*="image"]',
            'img[class*="Image"]',
            'img',
        ]

        img_attrs = ['src', 'data-src', 'data-lazy', 'data-original']

        for selector in img_selectors:
            img_elem = card.select_one(selector)
            if img_elem:
                for attr in img_attrs:
                    img_url = img_elem.get(attr)
                    if img_url and not img_url.startswith('data:'):
                        if img_url.startswith('//'):
                            data['thumbnail_url'] = f"https:{img_url}"
                        elif img_url.startswith('/'):
                            data['thumbnail_url'] = urljoin(self.BASE_URL, img_url)
                        else:
                            data['thumbnail_url'] = img_url
                        break
                if data['thumbnail_url']:
                    break

        # Extract location preview
        location_selectors = [
            '[data-qa="POSTING_CARD_LOCATION"]',
            '[class*="Location"]',
            '[class*="location"]',
            '[class*="address"]',
        ]

        for selector in location_selectors:
            loc_elem = card.select_one(selector)
            if loc_elem:
                data['location_preview'] = loc_elem.get_text(strip=True)[:200]
                break

        return data

    def has_next_page(self) -> bool:
        """
        Check if there's a next page of results.

        Looks for pagination elements.
        """
        if not self.soup:
            return False

        # Look for pagination
        pagination_selectors = [
            'a[data-qa="PAGING_NEXT"]',
            'a[href*="pagina="]',
            '.pagination a.next',
            '.pagination__next',
            'a[rel="next"]',
            'li.next a',
        ]

        for selector in pagination_selectors:
            try:
                next_link = self.soup.select_one(selector)
                if next_link:
                    return True
            except Exception:
                continue

        # Check results count
        result_count_elem = self.soup.select_one('[data-qa="SEARCH_RESULTS_COUNT"], .results-count')
        if result_count_elem:
            text = result_count_elem.get_text()
            match = re.search(r'(\d+)\s*-\s*(\d+)\s*de\s*(\d+)', text.replace('.', ''))
            if match:
                current_end = int(match.group(2))
                total = int(match.group(3))
                return current_end < total

        return False

    def get_total_results(self) -> Optional[int]:
        """
        Try to extract total number of results from page.
        """
        if not self.soup:
            return None

        selectors = [
            '[data-qa="SEARCH_RESULTS_COUNT"]',
            '.results-count',
            '[class*="ResultCount"]',
            '[class*="result-count"]',
        ]

        for selector in selectors:
            elem = self.soup.select_one(selector)
            if elem:
                text = elem.get_text()
                # Look for numbers
                numbers = re.findall(r'(\d+)', text.replace('.', '').replace(',', ''))
                if numbers:
                    # Take the largest number (usually the total)
                    return max(int(n) for n in numbers)

        return None
