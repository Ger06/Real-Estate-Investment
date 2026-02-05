"""
MercadoLibre Listing Scraper
Scrapes search result pages from inmuebles.mercadolibre.com.ar to extract property URLs
Uses undetected-chromedriver to bypass bot detection.

## Cookies / Autenticación (IMPORTANTE)

MercadoLibre requiere cookies de sesión válidas. Este scraper usa un perfil
persistente de Chrome dedicado para mantener la sesión entre ejecuciones.

### Cómo funciona:
1. El scraper crea un perfil dedicado en %LOCALAPPDATA%/ml_scraper_profile/
   (configurable via ML_SCRAPER_PROFILE_DIR).
2. La primera vez que se ejecuta, MercadoLibre puede pedir login.
   El usuario debe loguarse manualmente en la ventana de Chrome que se abre.
3. Las cookies se guardan en el perfil persistente y se reutilizan en
   ejecuciones siguientes. No se borra el perfil al cerrar.
4. Si las cookies expiran, el usuario debe volver a loguarse.

### Configuración (env vars):
- ML_SCRAPER_PROFILE_DIR: ruta al directorio del perfil dedicado
  (default: %LOCALAPPDATA%/ml_scraper_profile)

### Enriquecimiento desde páginas de detalle:
Después de scrapear la página de búsqueda, el scraper visita cada
propiedad individualmente para extraer:
  - Todas las imágenes (la búsqueda solo muestra 1)
  - Superficies: total, cubierta, semicubierta, descubierta
  - Descripción completa
  - Dirección y barrio
"""
import json
import os
import re
import time
import logging
from typing import Dict, Any, List, Optional
from urllib.parse import urljoin, quote

# Use undetected-chromedriver to bypass MercadoLibre's bot detection
try:
    import undetected_chromedriver as uc
    USE_UNDETECTED = True
except ImportError:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    USE_UNDETECTED = False

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from .listing_base import BaseListingScraper

logger = logging.getLogger(__name__)

# Default persistent profile location
DEFAULT_PROFILE_DIR = os.path.join(
    os.environ.get('LOCALAPPDATA', os.path.join(os.path.expanduser('~'), 'AppData', 'Local')),
    'ml_scraper_profile'
)


class MercadoLibreListingScraper(BaseListingScraper):
    """
    Scraper for MercadoLibre Inmuebles search results.
    Uses Selenium for JavaScript-rendered content.
    Uses a persistent Chrome profile to maintain ML session cookies.

    Builds URLs like:
    - https://inmuebles.mercadolibre.com.ar/departamentos/venta/capital-federal/
    - https://inmuebles.mercadolibre.com.ar/casas/alquiler/cordoba/
    - https://inmuebles.mercadolibre.com.ar/departamentos/venta/capital-federal/_Desde_49
    """

    PORTAL_NAME = "mercadolibre"
    BASE_URL = "https://inmuebles.mercadolibre.com.ar"
    MAX_PAGES = 10
    DELAY_BETWEEN_PAGES = 3.0
    ITEMS_PER_PAGE = 48  # MercadoLibre shows 48 items per page

    # Mapping for property types (MercadoLibre specific slugs)
    PROPERTY_TYPE_MAP = {
        "departamento": "departamentos",
        "casa": "casas",
        "ph": "ph",
        "terreno": "terrenos-lotes",
        "local": "locales-comerciales",
        "oficina": "oficinas",
        "cochera": "cocheras",
        "galpon": "galpones",
        "campo": "campos",
        "quinta": "quintas",
    }

    # Mapping for operation types
    OPERATION_TYPE_MAP = {
        "venta": "venta",
        "alquiler": "alquiler",
        "alquiler_temporal": "alquiler-temporario",
    }

    # Mapping for locations (MercadoLibre uses specific slugs)
    LOCATION_MAP = {
        "capital federal": "capital-federal",
        "caba": "capital-federal",
        "buenos aires": "capital-federal",  # Default to CABA when "buenos aires" city is specified
        "gba norte": "bs-as-gba-norte",
        "gba sur": "bs-as-gba-sur",
        "gba oeste": "bs-as-gba-oeste",
        "zona norte": "bs-as-gba-norte",
        "zona sur": "bs-as-gba-sur",
        "zona oeste": "bs-as-gba-oeste",
        "cordoba": "cordoba",
        "mendoza": "mendoza",
        "santa fe": "santa-fe",
        "rosario": "santa-fe/rosario",
        "mar del plata": "bs-as-costa-atlantica/mar-del-plata",
        "costa atlantica": "bs-as-costa-atlantica",
        "provincia de buenos aires": "bs-as-costa-atlantica",
        "tucuman": "tucuman",
        "salta": "salta",
    }

    # Neighborhoods in Capital Federal
    NEIGHBORHOOD_MAP = {
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
        "barrio norte": "barrio-norte",
        "flores": "flores",
        "floresta": "floresta",
        "devoto": "villa-devoto",
        "saavedra": "saavedra",
        "chacarita": "chacarita",
        "boedo": "boedo",
        "la boca": "la-boca",
        "retiro": "retiro",
        "microcentro": "microcentro",
        "liniers": "liniers",
        "mataderos": "mataderos",
        "monte castro": "monte-castro",
        "parque chacabuco": "parque-chacabuco",
        "parque patricios": "parque-patricios",
        "paternal": "paternal",
        "pompeya": "nueva-pompeya",
        "constitucion": "constitucion",
        "once": "balvanera",
        "congreso": "balvanera",
        # Additional neighborhoods
        "coghlan": "coghlan",
        "agronomia": "agronomia",
        "villa ortuzar": "villa-ortuzar",
        "villa santa rita": "villa-santa-rita",
        "villa real": "villa-real",
        "versalles": "versalles",
        "velez sarsfield": "velez-sarsfield",
        "villa lugano": "villa-lugano",
        "villa soldati": "villa-soldati",
        "villa riachuelo": "villa-riachuelo",
        "parque chas": "parque-chas",
        "parque avellaneda": "parque-avellaneda",
        "san nicolas": "san-nicolas",
        "monserrat": "monserrat",
        "san cristobal": "san-cristobal",
        "barracas": "barracas",
    }

    def __init__(self, search_params: Dict[str, Any], user_agent: Optional[str] = None):
        super().__init__(search_params, user_agent)
        self.driver = None

    # ── Chrome profile & driver management ─────────────────────────

    def _get_persistent_profile_dir(self) -> str:
        """
        Get or create the persistent Chrome profile directory.

        Unlike the old temp-profile approach, this directory survives between
        runs so cookies created by Chrome stay valid (App-Bound Encryption
        ties cookies to the user-data-dir path).
        """
        profile_dir = os.environ.get('ML_SCRAPER_PROFILE_DIR', DEFAULT_PROFILE_DIR)
        is_first_run = not os.path.exists(profile_dir)
        if is_first_run:
            os.makedirs(profile_dir, exist_ok=True)
            logger.info(f"[mercadolibre] Created persistent profile at: {profile_dir}")
            print(f"[INFO] [mercadolibre] First run — created profile at: {profile_dir}")
            print(f"[INFO] [mercadolibre] If MercadoLibre asks you to log in, please do so in the browser window.")
        return profile_dir

    def _get_driver(self, headless: bool = False):
        """
        Create Chrome WebDriver using persistent profile for ML session.

        The persistent profile keeps cookies valid across runs because
        they were created IN this profile (avoids App-Bound Encryption issues).
        """
        if self.driver:
            return self.driver

        profile_dir = self._get_persistent_profile_dir()

        if USE_UNDETECTED:
            # Detect installed Chrome major version to avoid driver mismatch
            version_main = None
            try:
                import winreg
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Google\Chrome\BLBeacon")
                chrome_version, _ = winreg.QueryValueEx(key, "version")
                winreg.CloseKey(key)
                version_main = int(chrome_version.split('.')[0])
                print(f"[DEBUG] [mercadolibre] Detected Chrome v{version_main}")
            except Exception as e:
                print(f"[DEBUG] [mercadolibre] Could not detect Chrome version: {e}")

            print(f"[DEBUG] [mercadolibre] Using undetected-chromedriver with persistent profile")
            options = uc.ChromeOptions()

            if headless:
                options.add_argument('--headless=new')

            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--window-size=1920,1080')

            self.driver = uc.Chrome(
                options=options,
                user_data_dir=profile_dir,
                version_main=version_main,
            )
        else:
            print("[DEBUG] [mercadolibre] Using regular selenium (undetected not available)")
            chrome_options = Options()
            chrome_options.add_argument(f'--user-data-dir={profile_dir}')

            if headless:
                chrome_options.add_argument('--headless=new')

            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')

            chrome_options.add_experimental_option('excludeSwitches', ['enable-automation', 'enable-logging'])
            chrome_options.add_experimental_option('useAutomationExtension', False)

            self.driver = webdriver.Chrome(options=chrome_options)

        return self.driver

    def _close_driver(self):
        """Close the WebDriver. Profile directory is kept for next run."""
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
            self.driver = None

    # ── URL building ───────────────────────────────────────────────

    def build_search_url(self, page: int = 1) -> str:
        """
        Build MercadoLibre search URL from parameters.

        URL structure:
        /[property_type]/[operation]/[location]/[filters]_Desde_[offset]

        Examples:
        - /departamentos/venta/capital-federal/
        - /casas/alquiler/cordoba/
        - /departamentos/venta/capital-federal/_Desde_49 (page 2)
        """
        params = self.search_params

        # Build path segments
        segments = []

        # Property type (required)
        property_type = params.get("property_type", "departamento").lower()
        if property_type in self.PROPERTY_TYPE_MAP:
            segments.append(self.PROPERTY_TYPE_MAP[property_type])
        else:
            segments.append("departamentos")

        # Operation type (required)
        operation = params.get("operation_type", "venta").lower()
        segments.append(self.OPERATION_TYPE_MAP.get(operation, "venta"))

        # Location and Neighborhoods
        city = params.get("city", "").lower()
        province = params.get("province", "").lower()
        neighborhoods = params.get("neighborhoods", [])

        # Check if any neighborhood is from CABA
        neighborhood_slug = None
        is_caba_neighborhood = False
        if neighborhoods and len(neighborhoods) >= 1:
            neighborhood = neighborhoods[0].lower()
            if neighborhood in self.NEIGHBORHOOD_MAP:
                neighborhood_slug = self.NEIGHBORHOOD_MAP[neighborhood]
                is_caba_neighborhood = True

        # Determine location: if CABA neighborhood, force capital-federal
        if is_caba_neighborhood:
            segments.append("capital-federal")
        else:
            location = city or province
            if location and location in self.LOCATION_MAP:
                segments.append(self.LOCATION_MAP[location])

        # Add neighborhood if found
        if neighborhood_slug:
            segments.append(neighborhood_slug)

        # Build base URL
        url = f"{self.BASE_URL}/{'/'.join(segments)}/"

        # Add filters
        filters = []

        # Price range (MercadoLibre uses _PriceRange_minCURRENCY-maxCURRENCY)
        min_price = params.get("min_price")
        max_price = params.get("max_price")
        currency = params.get("currency", "USD").upper()

        if min_price or max_price:
            min_val = int(min_price) if min_price else 0
            max_val = int(max_price) if max_price else 999999999
            # Format: _PriceRange_100000USD-200000USD
            filters.append(f"_PriceRange_{min_val}{currency}-{max_val}{currency}")

        # Area range
        min_area = params.get("min_area")
        max_area = params.get("max_area")
        if min_area or max_area:
            min_val = int(min_area) if min_area else 0
            max_val = int(max_area) if max_area else "*"
            filters.append(f"_CoveredArea_{min_val}-{max_val}")

        # Bedrooms
        min_bedrooms = params.get("min_bedrooms")
        if min_bedrooms:
            filters.append(f"_Bedrooms_{int(min_bedrooms)}")

        # Add filters to URL
        if filters:
            url += ''.join(filters)

        # Pagination (MercadoLibre uses _Desde_X where X = (page-1) * 48 + 1)
        if page > 1:
            offset = (page - 1) * self.ITEMS_PER_PAGE + 1
            url += f"_Desde_{offset}"

        return url

    # ── Page fetching & scraping ───────────────────────────────────

    async def fetch_page(self, url: str) -> str:
        """Fetch page using Selenium for JavaScript-rendered content"""
        # MercadoLibre detection works better without headless mode
        driver = self._get_driver(headless=False)

        try:
            print(f"[DEBUG] [mercadolibre] Selenium loading: {url}")
            driver.get(url)

            # Wait for page to load
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )

            # Wait for content to render (MercadoLibre loads content dynamically)
            time.sleep(5)

            # Check if we got a verification page (bot detection)
            page_source = driver.page_source
            if 'account-verification' in page_source or 'message-code' in page_source:
                print("[DEBUG] [mercadolibre] Bot detection triggered - verification page shown")
                # Try scrolling to trigger lazy loading
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
                time.sleep(2)
                driver.execute_script("window.scrollTo(0, 0);")
                time.sleep(2)

            # Try multiple selectors for listing cards
            card_selectors = [
                'a[href*="mercadolibre.com.ar/MLA"]',
                'a[href*="/MLA-"]',
                '.ui-search-result',
                '[class*="ui-search-layout__item"]',
                'li[class*="ui-search"]',
                'ol.ui-search-layout li',
            ]

            found_cards = False
            for selector in card_selectors:
                try:
                    WebDriverWait(driver, 3).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        print(f"[DEBUG] [mercadolibre] Found {len(elements)} elements with: {selector}")
                        found_cards = True
                        break
                except Exception:
                    continue

            if not found_cards:
                # Check if ML redirected to login page
                current_url = driver.current_url
                is_login = (
                    'login' in current_url
                    or 'auth.' in current_url
                    or 'verification' in current_url
                    or 'inmuebles.mercadolibre' not in current_url
                )
                if is_login:
                    print("[INFO] [mercadolibre] Login page detected.")
                    print("[INFO] [mercadolibre] Please log in in the browser window. Waiting up to 2 minutes...")
                    # Wait for user to complete login (check every 3s, up to 2 min)
                    logged_in = False
                    for _ in range(40):
                        time.sleep(3)
                        current_url = driver.current_url
                        if 'login' not in current_url and 'auth.' not in current_url and 'verification' not in current_url:
                            logged_in = True
                            break
                    if logged_in:
                        print("[INFO] [mercadolibre] Login successful! Re-loading search page...")
                        driver.get(url)
                        time.sleep(5)
                        # Try to find cards again after login
                        for selector in card_selectors:
                            try:
                                WebDriverWait(driver, 3).until(
                                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                                )
                                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                                if elements:
                                    print(f"[DEBUG] [mercadolibre] After login: found {len(elements)} elements")
                                    found_cards = True
                                    break
                            except Exception:
                                continue
                    else:
                        print("[WARN] [mercadolibre] Login timeout (2 min). Continuing anyway...")
                else:
                    print("[DEBUG] [mercadolibre] No listing cards found with any selector")
                    time.sleep(3)

            html = driver.page_source
            print(f"[DEBUG] [mercadolibre] Got HTML, length: {len(html)}")
            return html

        except Exception as e:
            print(f"[DEBUG] [mercadolibre] Selenium error: {e}")
            raise

    async def scrape_all_pages(self, max_properties: int = 100) -> List[Dict[str, Any]]:
        """Scrape all pages, enrich from detail pages, then close driver."""
        try:
            cards = await super().scrape_all_pages(max_properties)
            # Enrich cards with images and features from detail pages
            if cards and self.driver:
                cards = self._enrich_cards_from_detail(cards)
            return cards
        finally:
            self._close_driver()

    # ── Card extraction from search results ────────────────────────

    def extract_property_cards(self) -> List[Dict[str, Any]]:
        """Extract property listings from MercadoLibre search results page"""
        if not self.soup:
            return []

        cards = []

        # MercadoLibre property URLs contain MLA- (MercadoLibre Argentina)
        # Format: https://[tipo].mercadolibre.com.ar/MLA-123456-titulo
        listing_links = self.soup.select('a[href*="mercadolibre.com.ar/MLA-"]')
        print(f"[DEBUG] [mercadolibre] Found {len(listing_links)} MLA links")

        seen_urls = set()
        for link in listing_links:
            href = link.get('href', '')
            if not href or 'MLA-' not in href:
                continue

            # Clean URL (remove tracking params)
            clean_url = self._clean_url(href)

            if clean_url in seen_urls:
                continue
            seen_urls.add(clean_url)

            # Extract data from the link and its parent container
            card_data = self._extract_card_data(link, clean_url)
            if card_data:
                cards.append(card_data)

        print(f"[DEBUG] [mercadolibre] Extracted {len(cards)} property cards")
        return cards

    def _clean_url(self, url: str) -> str:
        """Remove tracking parameters from URL"""
        # Remove everything after # or certain query params
        if '#' in url:
            url = url.split('#')[0]

        # Keep the base URL with MLA ID
        match = re.search(r'(https?://[^/]+/MLA-\d+[^?#\s]*)', url)
        if match:
            return match.group(1)

        return url

    def _extract_card_data(self, link_elem, url: str) -> Optional[Dict[str, Any]]:
        """Extract data from a listing link element"""
        data = {
            'source': 'mercadolibre',
            'source_url': url,
            'source_id': self._extract_id_from_url(url),
            'title': None,
            'price': None,
            'currency': None,
            'thumbnail_url': None,
            'location_preview': None,
        }

        # Try to find the parent card container
        parent = link_elem
        for _ in range(7):  # Go up more levels for MercadoLibre's nested structure
            if parent.parent is None:
                break
            parent = parent.parent
            parent_class = parent.get('class', [])
            if any('ui-search-result' in c or 'layout__item' in c
                   for c in parent_class if isinstance(c, str)):
                break

        search_context = parent if parent else link_elem

        # Extract title
        title_selectors = [
            'h2',
            '[class*="ui-search-item__title"]',
            '[class*="title"]',
            '.item__title',
        ]
        for selector in title_selectors:
            title_elem = search_context.select_one(selector)
            if title_elem:
                data['title'] = title_elem.get_text(strip=True)[:500]
                break

        if not data['title']:
            # Use link text as fallback
            link_text = link_elem.get_text(strip=True)
            if link_text and len(link_text) > 5:
                data['title'] = link_text[:500]

        # Extract price
        price_selectors = [
            '[class*="ui-search-price__second-line"]',
            '[class*="price-tag-fraction"]',
            '[class*="price"]',
            '.price',
        ]
        for selector in price_selectors:
            price_elem = search_context.select_one(selector)
            if price_elem:
                price_text = price_elem.get_text(strip=True)
                price_amount, currency = self.clean_price(price_text)
                if price_amount:
                    data['price'] = price_amount
                    data['currency'] = currency
                    break

        # Determine currency from symbol if not found
        if data['price'] and not data['currency']:
            currency_elem = search_context.select_one('[class*="currency-symbol"]')
            if currency_elem:
                symbol = currency_elem.get_text(strip=True)
                data['currency'] = 'USD' if 'U$S' in symbol or 'USD' in symbol else 'ARS'

        # Extract image
        img_selectors = [
            'img[class*="ui-search-result-image__element"]',
            'img[data-src*="http"]',
            'img[src*="http"]',
            'img',
        ]
        for selector in img_selectors:
            img_elem = search_context.select_one(selector)
            if img_elem:
                for attr in ['data-src', 'src', 'data-lazy']:
                    img_url = img_elem.get(attr)
                    if img_url and img_url.startswith('http') and 'placeholder' not in img_url.lower():
                        data['thumbnail_url'] = img_url
                        break
                if data['thumbnail_url']:
                    break

        # Extract location
        location_selectors = [
            '[class*="ui-search-item__location"]',
            '[class*="location"]',
            '[class*="address"]',
        ]
        for selector in location_selectors:
            loc_elem = search_context.select_one(selector)
            if loc_elem:
                data['location_preview'] = loc_elem.get_text(strip=True)[:200]
                break

        return data

    def _extract_id_from_url(self, url: str) -> Optional[str]:
        """Extract MLA ID from URL"""
        # MercadoLibre URLs: /MLA-123456789-titulo
        match = re.search(r'MLA-(\d+)', url)
        if match:
            return f"MLA-{match.group(1)}"
        return None

    def has_next_page(self) -> bool:
        """Check if there's a next page of results"""
        if not self.soup:
            return False

        # Look for pagination elements
        next_selectors = [
            'a[title="Siguiente"]',
            'a[class*="andes-pagination__link"][title*="Siguiente"]',
            'li.andes-pagination__button--next a',
            '[class*="pagination"] a[rel="next"]',
        ]

        for selector in next_selectors:
            try:
                next_elem = self.soup.select_one(selector)
                if next_elem and next_elem.get('href'):
                    return True
            except Exception:
                continue

        return False

    def get_total_results(self) -> Optional[int]:
        """Try to extract total number of results from page"""
        if not self.soup:
            return None

        selectors = [
            '[class*="ui-search-search-result__quantity-results"]',
            '[class*="quantity-results"]',
            '.ui-search-search-result__quantity-results',
        ]

        for selector in selectors:
            elem = self.soup.select_one(selector)
            if elem:
                text = elem.get_text()
                # Extract number from "1.234 resultados"
                numbers = re.findall(r'[\d.]+', text.replace(',', ''))
                if numbers:
                    # Remove dots used as thousand separators
                    num_str = numbers[0].replace('.', '')
                    try:
                        return int(num_str)
                    except ValueError:
                        pass

        return None

    # ── Detail page enrichment ─────────────────────────────────────

    def _enrich_cards_from_detail(
        self, cards: List[Dict[str, Any]], max_details: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Visit each property's detail page to extract all images and features.

        The search page only provides 1 thumbnail per listing. Detail pages
        have the full image gallery, surface areas, and other features.
        """
        enriched = 0
        to_enrich = cards[:max_details]
        print(f"[DEBUG] [mercadolibre] Enriching {len(to_enrich)} cards from detail pages...")

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
                print(f"[DEBUG] [mercadolibre]   Card {i+1}/{len(to_enrich)}: {n_imgs} images")

            except Exception as e:
                logger.debug(f"[mercadolibre] Error enriching card {i+1}: {e}")

            # Rate limit between detail pages
            if i < len(to_enrich) - 1:
                time.sleep(2)

        print(f"[DEBUG] [mercadolibre] Enriched {enriched}/{len(to_enrich)} cards")
        return cards

    def _extract_detail_data(self, url: str) -> Dict[str, Any]:
        """Extract images and features from a property detail page."""
        data: Dict[str, Any] = {}

        self.driver.get(url)
        time.sleep(3)

        # Progressive scroll to trigger lazy loading of images and content
        total_height = self.driver.execute_script("return document.body.scrollHeight")
        for scroll_pos in range(0, min(total_height, 5000), 500):
            self.driver.execute_script(f"window.scrollTo(0, {scroll_pos});")
            time.sleep(0.3)
        # Scroll back to top
        self.driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(1)

        html = self.driver.page_source
        soup = BeautifulSoup(html, 'html.parser')

        # Extract images
        images = self._extract_detail_images(soup)
        if images:
            data['images'] = images

        # Extract features (surface areas, rooms, etc.)
        features = self._extract_detail_features(soup)
        data.update(features)

        # Extract description
        desc_selectors = [
            '[class*="item-description"] p',
            '[class*="description__content"]',
            '[class*="description"] p',
        ]
        for sel in desc_selectors:
            desc_elem = soup.select_one(sel)
            if desc_elem:
                data['description'] = desc_elem.get_text(strip=True)[:2000]
                break

        # Extract location from embedded JSON (ML stores address in page state)
        # The page contains JSON with "item_address", "neighborhood", "city" fields
        address_match = re.search(r'"item_address"\s*:\s*"([^"]+)"', html)
        if address_match:
            data['address'] = address_match.group(1)

        neighborhood_match = re.search(r'"neighborhood"\s*:\s*"([^"]+)"', html)
        if neighborhood_match:
            data['neighborhood'] = neighborhood_match.group(1)

        city_match = re.search(r'"city"\s*:\s*"([^"]+)"', html)
        if city_match:
            data['city'] = city_match.group(1)

        # Fallback: Extract location / address from CSS selectors
        if not data.get('address') and not data.get('neighborhood'):
            loc_selectors = [
                '[class*="location-subtitle"]',
                '[class*="map-address"]',
                '[class*="item-location"]',
            ]
            for sel in loc_selectors:
                loc_elem = soup.select_one(sel)
                if loc_elem:
                    loc_text = loc_elem.get_text(strip=True)
                    parts = [p.strip() for p in loc_text.split(',') if p.strip()]
                    if parts:
                        if re.search(r'\d', parts[0]) and len(parts) >= 2:
                            data['address'] = parts[0]
                            data['neighborhood'] = parts[1]
                        elif not re.search(r'\d', parts[0]):
                            data['neighborhood'] = parts[0]
                    break

        return data

    def _extract_detail_images(self, soup: BeautifulSoup) -> List[str]:
        """Extract all property images from detail page."""
        images: List[str] = []
        seen: set = set()

        # Strategy 1: Gallery / carousel images
        gallery_selectors = [
            'figure img[src*="http"]',
            '[class*="gallery"] img[src*="http"]',
            '[class*="carousel"] img[src*="http"]',
            '[class*="slick"] img[src*="http"]',
            'img[src*="mlstatic.com"]',
        ]

        for selector in gallery_selectors:
            for img in soup.select(selector):
                for attr in ['data-zoom-src', 'data-src', 'src']:
                    url = img.get(attr, '')
                    if url and 'mlstatic.com' in url and url not in seen:
                        upgraded = self._upgrade_image_url(url)
                        if upgraded not in seen:
                            seen.add(upgraded)
                            images.append(upgraded)

        # Strategy 2: JSON-LD structured data
        if not images:
            for script in soup.find_all('script', type='application/ld+json'):
                try:
                    ld = json.loads(script.string or '')
                    if isinstance(ld, dict):
                        img_list = ld.get('image', [])
                        if isinstance(img_list, str):
                            img_list = [img_list]
                        for url in img_list:
                            if url and url not in seen:
                                seen.add(url)
                                images.append(url)
                except (json.JSONDecodeError, TypeError):
                    pass

        # Strategy 3: og:image meta tag
        if not images:
            og = soup.find('meta', property='og:image')
            if og and og.get('content'):
                images.append(og['content'])

        return images[:20]

    @staticmethod
    def _upgrade_image_url(url: str) -> str:
        """Upgrade ML image URL to larger resolution."""
        # ML thumbnails use smaller dimensions; replace with full-size -O variant
        url = re.sub(r'-\d+x\d+\.', '-O.', url)
        return url

    def _extract_detail_features(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract property features (surfaces, rooms, etc.) from detail page."""
        features: Dict[str, Any] = {}

        # Strategy 1: Structured specs table/rows
        spec_selectors = [
            '[class*="specs"] tr',
            '[class*="attribute"] tr',
            '[class*="specs-item"]',
            '[class*="attribute-content"]',
            'table[class*="andes-table"] tr',
        ]

        spec_rows = []
        for selector in spec_selectors:
            spec_rows = soup.select(selector)
            if spec_rows:
                break

        for row in spec_rows:
            cells = row.find_all(['td', 'th', 'span', 'p', 'dt', 'dd'])
            if len(cells) >= 2:
                label = cells[0].get_text(strip=True).lower()
                value = cells[1].get_text(strip=True)
                self._parse_feature(features, label, value)

        # Strategy 2: Key-value list items (common ML pattern)
        if not features:
            kv_selectors = [
                '[class*="technical-specifications"] li',
                '[class*="attribute"] li',
                '[class*="specs"] li',
            ]
            for selector in kv_selectors:
                items = soup.select(selector)
                for item in items:
                    text = item.get_text(strip=True)
                    if ':' in text:
                        parts = text.split(':', 1)
                        self._parse_feature(features, parts[0].strip(), parts[1].strip())
                    else:
                        self._parse_feature_text(features, text.lower())

        # Strategy 3: Highlighted feature chips (search for area patterns anywhere)
        if not features.get('total_area') and not features.get('covered_area'):
            highlight_selectors = [
                '[class*="highlight"]',
                '[class*="item-detail"]',
                '[class*="short-description"]',
            ]
            for selector in highlight_selectors:
                for elem in soup.select(selector):
                    self._parse_feature_text(features, elem.get_text(strip=True).lower())

        return features

    def _parse_feature(self, features: Dict, label: str, value: str):
        """Parse a single label-value feature pair into the features dict."""
        label = label.lower().strip()
        value = value.strip()

        if 'superficie total' in label or 'sup. total' in label:
            m = re.search(r'(\d+(?:[.,]\d+)?)', value)
            if m:
                features['total_area'] = float(m.group(1).replace(',', '.'))
        elif 'superficie cubierta' in label or 'sup. cubierta' in label or 'sup. cub' in label:
            m = re.search(r'(\d+(?:[.,]\d+)?)', value)
            if m:
                features['covered_area'] = float(m.group(1).replace(',', '.'))
        elif 'semicubierta' in label:
            m = re.search(r'(\d+(?:[.,]\d+)?)', value)
            if m:
                features['semi_covered_area'] = float(m.group(1).replace(',', '.'))
        elif 'descubierta' in label:
            m = re.search(r'(\d+(?:[.,]\d+)?)', value)
            if m:
                features['uncovered_area'] = float(m.group(1).replace(',', '.'))
        elif 'ambientes' in label or 'ambiente' in label:
            m = re.search(r'(\d+)', value)
            if m:
                features['bedrooms'] = int(m.group(1))
        elif 'dormitorio' in label:
            m = re.search(r'(\d+)', value)
            if m:
                features['bedrooms'] = int(m.group(1))
        elif 'baño' in label:
            m = re.search(r'(\d+)', value)
            if m:
                features['bathrooms'] = int(m.group(1))
        elif 'cochera' in label or 'garage' in label or 'estacionamiento' in label:
            m = re.search(r'(\d+)', value)
            if m:
                features['parking_spaces'] = int(m.group(1))

    def _parse_feature_text(self, features: Dict, text: str):
        """Parse features from unstructured text (e.g. '108 m² tot')."""
        # Total area
        m = re.search(r'(\d+(?:[.,]\d+)?)\s*m[²2]?\s*(?:total|tot)', text)
        if m and 'total_area' not in features:
            features['total_area'] = float(m.group(1).replace(',', '.'))

        # Covered area
        m = re.search(r'(\d+(?:[.,]\d+)?)\s*m[²2]?\s*(?:cubierta|cub)', text)
        if m and 'covered_area' not in features:
            features['covered_area'] = float(m.group(1).replace(',', '.'))

        # Bare area (no qualifier) → treat as total
        if 'total_area' not in features and 'covered_area' not in features:
            m = re.search(r'(\d+(?:[.,]\d+)?)\s*m[²2]', text)
            if m:
                features['total_area'] = float(m.group(1).replace(',', '.'))
