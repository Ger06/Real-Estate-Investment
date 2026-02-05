"""
Zonaprop Listing Scraper
Scrapes search result pages from www.zonaprop.com.ar to extract property URLs
Uses curl_cffi for Cloudflare bypass, Selenium as last resort.
"""
import asyncio
import re
import logging
from typing import Dict, Any, List, Optional
from urllib.parse import urljoin, urlparse, urlunparse
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

    def _get_driver(self, headless: bool = False):
        """Create and return a configured Chrome WebDriver.

        Uses undetected-chromedriver if available to bypass Cloudflare.
        Non-headless mode by default for better Cloudflare bypass.
        """
        if self.driver:
            return self.driver

        # Try undetected-chromedriver first (better for Cloudflare)
        try:
            import undetected_chromedriver as uc

            # Detect installed Chrome version to avoid driver mismatch
            version_main = None
            try:
                import winreg
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Google\Chrome\BLBeacon")
                chrome_version, _ = winreg.QueryValueEx(key, "version")
                winreg.CloseKey(key)
                version_main = int(chrome_version.split('.')[0])
                print(f"[DEBUG] [zonaprop] Detected Chrome v{version_main}")
            except Exception as e:
                print(f"[DEBUG] [zonaprop] Could not detect Chrome version: {e}")

            options = uc.ChromeOptions()
            if headless:
                options.add_argument('--headless=new')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--window-size=1920,1080')

            self.driver = uc.Chrome(options=options, version_main=version_main)
            print("[DEBUG] [zonaprop] Using undetected-chromedriver")
            return self.driver

        except ImportError:
            pass
        except Exception as e:
            print(f"[DEBUG] [zonaprop] undetected-chromedriver failed: {e}, falling back to selenium")

        # Fallback to regular selenium
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options

        chrome_options = Options()
        if headless:
            chrome_options.add_argument('--headless=new')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument(f'user-agent={self.user_agent}')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--lang=es-AR')

        self.driver = webdriver.Chrome(options=chrome_options)

        # Override navigator.webdriver flag (CF detection vector)
        self.driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {"source": """
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                Object.defineProperty(navigator, 'languages', {get: () => ['es-AR', 'es', 'en']});
                Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
                window.chrome = {runtime: {}};
            """},
        )

        print("[DEBUG] [zonaprop] Using regular selenium (headless)" if headless else "[DEBUG] [zonaprop] Using regular selenium")
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

        if min_bedrooms and max_bedrooms:
            if min_bedrooms == max_bedrooms:
                filter_segments.append(f"{int(min_bedrooms)}-ambientes")
            else:
                filter_segments.append(f"{int(min_bedrooms)}-a-{int(max_bedrooms)}-ambientes")
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
        Fetch page with fallback chain:
        1. curl_cffi with Chrome TLS fingerprint
        2. FlareSolverr (CF JS challenge solver)
        3. httpx (plain fallback)
        4. Selenium (absolute last resort)
        """
        from .http_client import _is_cf_blocked
        # Levels 1-3: curl_cffi / FlareSolverr / httpx via base class
        try:
            html = await super().fetch_page(url)
            if len(html) > 5000 and not _is_cf_blocked(html):
                logger.info(f"[zonaprop] fetch_with_browser_fingerprint OK, length: {len(html)}")
                return html
            logger.warning("[zonaprop] Got Cloudflare challenge, trying Selenium...")
        except Exception as e:
            logger.warning(f"[zonaprop] HTTP fetch failed: {e}, trying Selenium...")

        # Level 3: Selenium fallback
        return await asyncio.to_thread(self._fetch_with_selenium, url)

    def _fetch_with_selenium(self, url: str) -> str:
        """Fetch page using Selenium, handling Cloudflare JS challenges."""
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
            # Warm up: visit homepage first to get CF cookies
            logger.info("[zonaprop] Selenium: warming up with homepage visit")
            driver.get(self.BASE_URL)
            time.sleep(4)

            # Now navigate to the search URL (with cookies set)
            logger.info(f"[zonaprop] Selenium loading: {url}")
            driver.get(url)

            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )

            # Wait for Cloudflare JS challenge to resolve (datacenter IPs trigger this)
            cf_markers = [
                'Just a moment', 'Checking your browser',
                'cf-browser-verification', '__cf_chl_',
                'challenge-platform', 'cf-turnstile',
                'Attention Required', 'Access denied',
                'Enable JavaScript and cookies',
            ]
            for i in range(25):  # up to 25 seconds for CF challenge
                page_src = driver.page_source
                if any(marker in page_src for marker in cf_markers):
                    logger.debug(f"[zonaprop] Cloudflare challenge active, waiting... ({i+1}s)")
                    time.sleep(1)
                else:
                    logger.info(f"[zonaprop] Cloudflare challenge resolved after {i}s")
                    break

            # Extra wait for page content to render after CF resolves
            time.sleep(3)

            # Try to wait for property cards
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, '[data-qa="posting PROPERTY"], .postingCard, [class*="PostingCard"], a[href*=".html"]'))
                )
            except Exception:
                logger.debug("[zonaprop] No property cards found with expected selectors, continuing anyway")

            html = driver.page_source
            page_title = driver.title or "(sin título)"
            logger.info(f"[zonaprop] Got HTML via Selenium, length: {len(html)}, title: {page_title}")

            # Diagnostic: if page is suspiciously small, log what we got
            if len(html) < 50000:
                logger.warning(
                    f"[zonaprop] Page too small ({len(html)} bytes), "
                    f"likely CF block. Title: '{page_title}', "
                    f"URL: {driver.current_url}, "
                    f"HTML snippet: {html[:500]}"
                )

            return html

        except Exception as e:
            logger.error(f"[zonaprop] Selenium error: {e}")
            raise

    async def scrape_all_pages(self, max_properties: int = 100) -> List[Dict[str, Any]]:
        """
        Scrape all pages using Selenium, then enrich with detail page data.
        Override to ensure driver is closed after scraping.
        """
        try:
            cards = await super().scrape_all_pages(max_properties)
            # Enrich cards with images and features from detail pages
            if cards:
                # Create driver if not already created (curl_cffi may have been used for search)
                self._get_driver()
                cards = self._enrich_cards_from_detail(cards)
            return cards
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
                logger.debug(f"[zonaprop] Found {len(card_elements)} cards with selector: {selector}")
                break

        if not card_elements:
            # Fallback: look for any links to property pages
            logger.debug("[zonaprop] No cards found with standard selectors, trying fallback...")

            # Zonaprop property URLs contain long numeric IDs
            property_links = self.soup.select('a[href*=".html"]')
            logger.debug(f"[zonaprop] Found {len(property_links)} .html links")

            seen_urls = set()
            for link in property_links:
                href = link.get('href', '')
                if href and href not in seen_urls and self._is_property_url(href):
                    seen_urls.add(href)
                    full_url = self._clean_url(urljoin(self.BASE_URL, href))
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

            logger.debug(f"[zonaprop] Fallback found {len(cards)} property URLs")
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

    @staticmethod
    def _clean_url(url: str) -> str:
        """Strip tracking query params and fragment from property URL.

        Zonaprop appends params like ?n_src=Listado&n_pills=Parrilla&n_pg=1&n_pos=1
        which cause duplicate-detection mismatches.
        """
        parsed = urlparse(url)
        return urlunparse(parsed._replace(query="", fragment=""))

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
            'description': None,
            'total_area': None,
            'covered_area': None,
            'bedrooms': None,
            'bathrooms': None,
            'parking_spaces': None,
            'address': None,
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

            data['source_url'] = self._clean_url(data['source_url'])
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

        # Extract description / subtitle
        desc_selectors = [
            '[data-qa="POSTING_CARD_DESCRIPTION"]',
            '[class*="Description"]',
            '[class*="description"]',
            '[class*="subtitle"]',
        ]
        for selector in desc_selectors:
            desc_elem = card.select_one(selector)
            if desc_elem:
                data['description'] = desc_elem.get_text(strip=True)[:1000]
                break

        # Extract address (separate from location/neighborhood)
        address_selectors = [
            '[data-qa="POSTING_CARD_ADDRESS"]',
            '[class*="Address"]',
            '[class*="address"]',
        ]
        for selector in address_selectors:
            addr_elem = card.select_one(selector)
            if addr_elem:
                data['address'] = addr_elem.get_text(strip=True)[:300]
                break

        # Extract features (area, rooms, bathrooms, parking)
        features_selectors = [
            '[data-qa="POSTING_CARD_FEATURES"]',
            '[class*="PostingMainFeatures"]',
            '[class*="postingMainFeatures"]',
            '[class*="main-features"]',
            '[class*="CardFeatures"]',
            '[class*="posting-features"]',
        ]

        features_text = ""
        for selector in features_selectors:
            feat_elem = card.select_one(selector)
            if feat_elem:
                features_text = feat_elem.get_text(" ", strip=True)
                break

        # Fallback: collect text from all small feature spans inside the card
        if not features_text:
            feat_spans = card.select('span')
            snippets = []
            for span in feat_spans:
                txt = span.get_text(strip=True)
                # Feature-like snippets: contain m², amb, baño, dorm, coch
                if re.search(r'm[²2]|amb|bañ|dorm|coch', txt, re.IGNORECASE):
                    snippets.append(txt)
            if snippets:
                features_text = " ".join(snippets)

        if features_text:
            parsed = self.parse_features_text(features_text)
            data['total_area'] = parsed.get('total_area')
            data['covered_area'] = parsed.get('covered_area')
            data['bedrooms'] = parsed.get('bedrooms')
            data['bathrooms'] = parsed.get('bathrooms')
            data['parking_spaces'] = parsed.get('parking_spaces')

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

    # ── Detail page enrichment ─────────────────────────────────────

    def _enrich_cards_from_detail(
        self, cards: List[Dict[str, Any]], max_details: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Visit each property's detail page to extract all images and features.

        The search page only provides 1 thumbnail per listing. Detail pages
        have the full image gallery and additional property data.
        """
        import time

        enriched = 0
        to_enrich = cards[:max_details]
        print(f"[DEBUG] [zonaprop] Enriching {len(to_enrich)} cards from detail pages...")

        # Warm up: visit homepage first to get Cloudflare cookies
        try:
            print("[DEBUG] [zonaprop] Warming up driver with homepage visit...")
            self.driver.get(self.BASE_URL)
            time.sleep(3)
        except Exception as e:
            logger.debug(f"[zonaprop] Warmup failed: {e}")

        for i, card in enumerate(to_enrich):
            url = card.get('source_url')
            if not url:
                continue
            try:
                detail_data = self._extract_detail_data(url)

                # Merge images (detail page has the full gallery)
                if detail_data.get('images'):
                    card['images'] = detail_data['images']

                # Merge features not already in the search card
                for key in [
                    'total_area', 'covered_area', 'semi_covered_area',
                    'uncovered_area', 'bedrooms', 'bathrooms',
                    'parking_spaces', 'description', 'address', 'neighborhood',
                ]:
                    if detail_data.get(key) is not None and not card.get(key):
                        card[key] = detail_data[key]

                n_imgs = len(detail_data.get('images', []))
                enriched += 1
                print(f"[DEBUG] [zonaprop]   Card {i+1}/{len(to_enrich)}: {n_imgs} images")

            except Exception as e:
                logger.debug(f"[zonaprop] Error enriching card {i+1}: {e}")
                print(f"[DEBUG] [zonaprop]   Card {i+1}/{len(to_enrich)}: ERROR - {e}")

            # Rate limit between detail pages (longer delay to avoid CF blocking)
            if i < len(to_enrich) - 1:
                time.sleep(4)

        print(f"[DEBUG] [zonaprop] Enriched {enriched}/{len(to_enrich)} cards")
        return cards

    def _extract_detail_data(self, url: str) -> Dict[str, Any]:
        """Extract images and features from a property detail page."""
        import time

        data: Dict[str, Any] = {}

        self.driver.get(url)
        time.sleep(3)

        # Scroll to trigger lazy loading
        try:
            total_height = self.driver.execute_script("return document.body.scrollHeight")
            for scroll_pos in range(0, min(total_height, 3000), 500):
                self.driver.execute_script(f"window.scrollTo(0, {scroll_pos});")
                time.sleep(0.2)
            self.driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(1)
        except Exception:
            pass

        html = self.driver.page_source
        soup = BeautifulSoup(html, 'html.parser')

        # Extract images from gallery container
        images = self._extract_detail_images(soup, html)
        if images:
            data['images'] = images

        # Extract features
        features = self._extract_detail_features(soup)
        data.update(features)

        # Extract description
        desc_selectors = [
            '[class*="description"] p',
            '[class*="Description"] p',
            '#description',
            '.posting-description',
        ]
        for sel in desc_selectors:
            desc_elem = soup.select_one(sel)
            if desc_elem:
                data['description'] = desc_elem.get_text(strip=True)[:2000]
                break

        # Extract address from h4 (Zonaprop pattern: "Street 123, Neighborhood, City")
        for h4 in soup.find_all('h4'):
            text = h4.get_text(strip=True)
            if any(loc in text.lower() for loc in ['capital federal', 'buenos aires', ',']):
                parts = [p.strip() for p in text.split(',') if p.strip()]
                if parts:
                    # First part with numbers is usually the address
                    if any(c.isdigit() for c in parts[0]):
                        data['address'] = parts[0]
                    if len(parts) >= 2:
                        data['neighborhood'] = parts[-2] if len(parts) > 2 else parts[-1]
                break

        return data

    def _extract_detail_images(self, soup: BeautifulSoup, html: str) -> List[str]:
        """Extract all property images from detail page."""
        images: List[str] = []
        seen: set = set()

        # Strategy 1: Extract from embedded JavaScript 'pictures' array (has ALL images)
        # Pattern: "url1200x1200": "https://imgar.zonapropcdn.com/avisos/..."
        url_matches = re.findall(
            r'"url1200x1200"\s*:\s*"(https://imgar\.zonapropcdn\.com/avisos/[^"]+)"',
            html
        )

        for url in url_matches:
            # Skip logos and agency images
            if '/empresas/' not in url and url not in seen:
                seen.add(url)
                images.append(url)

        # Strategy 2: Gallery container with direct img elements (fallback)
        if len(images) < 3:
            gallery_selectors = [
                '#multimedia-content img',
                '#new-gallery-portal img',
                '.gallery-multimedia-represh img',
                '.item-desktop img',
            ]

            for selector in gallery_selectors:
                for img in soup.select(selector):
                    for attr in ['src', 'data-src', 'data-lazy']:
                        url = img.get(attr, '')
                        if url and 'zonapropcdn.com/avisos/' in url and url not in seen:
                            if '/empresas/' not in url:
                                upgraded = self._upgrade_image_url(url)
                                if upgraded not in seen:
                                    seen.add(upgraded)
                                    images.append(upgraded)
                            break
                if len(images) >= 3:
                    break

        # Strategy 3: Any img with zonapropcdn.com/avisos/ URL (last resort)
        if len(images) < 3:
            for img in soup.find_all('img'):
                for attr in ['src', 'data-src']:
                    url = img.get(attr, '')
                    if url and 'zonapropcdn.com/avisos/' in url and url not in seen:
                        if '/empresas/' not in url and '100x75' not in url:
                            upgraded = self._upgrade_image_url(url)
                            if upgraded not in seen:
                                seen.add(upgraded)
                                images.append(upgraded)
                        break

        return images[:20]

    @staticmethod
    def _upgrade_image_url(url: str) -> str:
        """Upgrade Zonaprop image URL to higher resolution."""
        # Replace small dimensions with 1200x1200
        url = re.sub(r'/\d+x\d+/', '/1200x1200/', url)
        # Also handle resize URLs
        url = re.sub(r'/resize/(\d+)/', r'/\1/', url)
        return url

    def _extract_detail_features(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract property features from detail page."""
        features: Dict[str, Any] = {}

        # Strategy 1: Look for h2.title-type-sup-property
        # Format: "Departamento • 96m² • 4 ambientes • 1 cochera"
        h2 = soup.find('h2', class_='title-type-sup-property')
        if h2:
            text = h2.get_text().lower()
            amb_match = re.search(r'(\d+)\s*ambiente', text)
            if amb_match:
                features['bedrooms'] = int(amb_match.group(1))
            coch_match = re.search(r'(\d+)\s*cochera', text)
            if coch_match:
                features['parking_spaces'] = int(coch_match.group(1))
            area_match = re.search(r'(\d+)\s*m', text)
            if area_match:
                features['covered_area'] = float(area_match.group(1))

        # Strategy 2: Look for li.icon-feature elements
        for li in soup.find_all('li', class_='icon-feature'):
            text = li.get_text().strip().lower()
            if 'm² tot' in text or 'm2 tot' in text:
                match = re.search(r'(\d+)', text)
                if match:
                    features['total_area'] = float(match.group(1))
            elif 'm² cub' in text or 'm2 cub' in text:
                match = re.search(r'(\d+)', text)
                if match:
                    features['covered_area'] = float(match.group(1))
            elif 'baño' in text:
                match = re.search(r'(\d+)', text)
                if match:
                    features['bathrooms'] = int(match.group(1))
            elif 'dormitorio' in text:
                match = re.search(r'(\d+)', text)
                if match:
                    features['bedrooms'] = int(match.group(1))

        # Strategy 3: Look for mainFeatures in JavaScript
        # Pattern: 'mainFeatures': { "CFT100": { ... "value": "45" ...
        # This is a fallback if HTML elements aren't found

        return features
