"""
MercadoLibre Listing Scraper
Scrapes search result pages from inmuebles.mercadolibre.com.ar to extract property URLs
Uses undetected-chromedriver to bypass bot detection.

## Cookies / Autenticación (IMPORTANTE)

MercadoLibre redirige a verificación de cuenta cuando no detecta cookies válidas de sesión.
Para resolver esto, el scraper copia las cookies del perfil de Chrome del usuario a un
directorio temporal y las usa en la sesión de Selenium.

### Cómo funciona actualmente (desarrollo local):
1. _prepare_temp_profile() copia Cookies, Cookies-journal, Network/ y Local State
   desde el perfil de Chrome del usuario (~\AppData\Local\Google\Chrome\User Data\Default)
   a un directorio temporal.
2. El driver de Selenium arranca con ese perfil temporal, heredando las cookies válidas.
3. Al cerrar, el directorio temporal se limpia automáticamente.
4. NO requiere cerrar Chrome — usa una copia independiente del perfil.

### Requisito:
- El usuario debe haber visitado MercadoLibre al menos una vez desde Chrome
  para que existan cookies válidas en el perfil.

### Configuración (env vars):
- CHROME_USER_DATA_DIR: ruta al directorio User Data de Chrome
  (default: ~/AppData/Local/Google/Chrome/User Data)
- CHROME_PROFILE_DIR: nombre del perfil (default: "Default")

### TODO - Producción (Render):
Este approach solo funciona en desarrollo local. En Render no hay Chrome con sesión activa.
Opciones para producción:
1. Exportar cookies de MercadoLibre a un archivo JSON y subirlo como variable de entorno
   o archivo en Render. El scraper las inyectaría via driver.add_cookie() en vez de
   copiar el perfil. Las cookies expiran (días a meses), hay que renovarlas periódicamente.
2. Usar la API pública de MercadoLibre (si hay endpoints disponibles para listings).
3. Mantener el scraping de MercadoLibre solo en ejecución local.
"""
import os
import re
import shutil
import tempfile
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
from .listing_base import BaseListingScraper

logger = logging.getLogger(__name__)


class MercadoLibreListingScraper(BaseListingScraper):
    """
    Scraper for MercadoLibre Inmuebles search results.
    Uses Selenium for JavaScript-rendered content.

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
        self._temp_profile_dir = None

    def _prepare_temp_profile(self) -> str:
        """
        Copy essential cookie/session files from the user's Chrome profile
        to a temporary directory. This avoids lock file conflicts and
        corrupt state files while preserving MercadoLibre session cookies.
        """
        chrome_user_data = os.environ.get(
            'CHROME_USER_DATA_DIR',
            os.path.join(os.path.expanduser('~'), 'AppData', 'Local', 'Google', 'Chrome', 'User Data')
        )
        chrome_profile = os.environ.get('CHROME_PROFILE_DIR', 'Default')

        src_profile = os.path.join(chrome_user_data, chrome_profile)
        temp_dir = tempfile.mkdtemp(prefix='ml_scraper_')
        dst_profile = os.path.join(temp_dir, chrome_profile)
        os.makedirs(dst_profile, exist_ok=True)

        # Copy Local State (contains cookie encryption key, needed by Chrome)
        local_state_src = os.path.join(chrome_user_data, 'Local State')
        if os.path.exists(local_state_src):
            shutil.copy2(local_state_src, temp_dir)

        # Copy only essential session/cookie files from the profile
        essential_files = [
            'Cookies',
            'Cookies-journal',
            'Network',  # directory with cookies in newer Chrome versions
        ]
        for filename in essential_files:
            src = os.path.join(src_profile, filename)
            dst = os.path.join(dst_profile, filename)
            if os.path.isdir(src):
                shutil.copytree(src, dst, dirs_exist_ok=True)
            elif os.path.exists(src):
                shutil.copy2(src, dst)

        print(f"[DEBUG] [mercadolibre] Copied cookies from {src_profile} to {dst_profile}")
        self._temp_profile_dir = temp_dir
        return temp_dir

    def _get_driver(self, headless: bool = False):
        """
        Create and return a configured Chrome WebDriver using copied cookies
        from the user's Chrome profile.

        Copies essential cookie files to a temp directory to avoid profile lock
        conflicts while inheriting valid MercadoLibre session cookies.

        Configuration via environment variables:
            - CHROME_USER_DATA_DIR: Path to Chrome's User Data directory
            - CHROME_PROFILE_DIR: Profile directory name (default: "Default")

        Args:
            headless: Whether to run in headless mode. Note: MercadoLibre detection
                     works better without headless mode (opens visible browser window).
        """
        if self.driver:
            return self.driver

        chrome_profile = os.environ.get('CHROME_PROFILE_DIR', 'Default')

        # Create temp profile with copied cookies
        temp_user_data = self._prepare_temp_profile()

        if USE_UNDETECTED:
            print(f"[DEBUG] [mercadolibre] Using undetected-chromedriver (headless={headless})")
            options = uc.ChromeOptions()
            options.add_argument(f'--profile-directory={chrome_profile}')

            if headless:
                options.add_argument('--headless=new')

            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--window-size=1920,1080')

            self.driver = uc.Chrome(options=options, user_data_dir=temp_user_data)
        else:
            print("[DEBUG] [mercadolibre] Using regular selenium (undetected not available)")
            chrome_options = Options()
            chrome_options.add_argument(f'--user-data-dir={temp_user_data}')
            chrome_options.add_argument(f'--profile-directory={chrome_profile}')

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
        """Close the WebDriver and clean up temporary profile directory"""
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
            self.driver = None

        if self._temp_profile_dir and os.path.exists(self._temp_profile_dir):
            try:
                shutil.rmtree(self._temp_profile_dir, ignore_errors=True)
            except Exception:
                pass
            self._temp_profile_dir = None

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
                print("[DEBUG] [mercadolibre] No listing cards found with any selector")
                # Last resort: wait more and try again
                time.sleep(3)

            html = driver.page_source
            print(f"[DEBUG] [mercadolibre] Got HTML, length: {len(html)}")
            return html

        except Exception as e:
            print(f"[DEBUG] [mercadolibre] Selenium error: {e}")
            raise

    async def scrape_all_pages(self, max_properties: int = 100) -> List[Dict[str, Any]]:
        """Override to ensure driver is closed after scraping"""
        try:
            return await super().scrape_all_pages(max_properties)
        finally:
            self._close_driver()

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
