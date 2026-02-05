"""
Remax Listing Scraper
Scrapes search result pages from www.remax.com.ar to extract property URLs
Uses curl_cffi for initial fetch, Selenium as fallback for JavaScript-rendered content.

Location and property type IDs are loaded from the database cache (remax_location_cache
and remax_property_type_cache tables). If a location is not in the cache, the search
will fail with a descriptive error.
"""
import re
import json
import time
import asyncio
import logging
from typing import Dict, Any, List, Optional, Tuple
from urllib.parse import urljoin, urlparse, quote
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from .listing_base import BaseListingScraper
from .http_client import fetch_with_browser_fingerprint

logger = logging.getLogger(__name__)


class RemaxListingScraper(BaseListingScraper):
    """
    Scraper for Remax search results / listing pages.
    Uses Selenium for JavaScript-rendered content.

    Location and property type IDs are loaded from database cache.
    Use set_db_session() before scraping to enable cache lookup.

    Builds URLs like:
    - https://www.remax.com.ar/listings/buy?page=1
    - https://www.remax.com.ar/listings/buy?city=Capital+Federal&page=1
    - https://www.remax.com.ar/listings/rent?propertyType=Departamento&page=1
    """

    PORTAL_NAME = "remax"
    BASE_URL = "https://www.remax.com.ar"
    MAX_PAGES = 10
    DELAY_BETWEEN_PAGES = 3.0

    # Operation IDs (static - these don't change)
    OPERATION_IDS = {
        "venta": "1",
        "alquiler": "2",
        "alquiler_temporal": "3",
    }

    # Currency IDs for price filter (static - these don't change)
    CURRENCY_IDS = {
        "USD": "1",
        "ARS": "2",
    }

    def __init__(self, search_params: Dict[str, Any], user_agent: Optional[str] = None):
        super().__init__(search_params, user_agent)
        self.driver = None
        self._last_raw_count = 0  # Track raw results for Deep Scrape termination
        self._db: Optional[AsyncSession] = None
        # Cache loaded from DB (populated by load_cache_from_db)
        self._location_cache: Dict[str, Tuple[str, str]] = {}
        self._property_type_cache: Dict[str, str] = {}
        self._cache_loaded = False

    def set_db_session(self, db: AsyncSession) -> None:
        """Set database session for cache lookups."""
        self._db = db

    async def load_cache_from_db(self) -> None:
        """
        Load location and property type caches from the database.
        Must be called before build_search_url if using DB cache.
        """
        if self._cache_loaded:
            return

        if not self._db:
            logger.warning("No DB session set, cache will be empty")
            return

        # Import here to avoid circular imports
        from app.models.remax_cache import RemaxLocationCache, RemaxPropertyTypeCache

        # Load locations
        stmt = select(RemaxLocationCache)
        result = await self._db.execute(stmt)
        locations = result.scalars().all()

        self._location_cache = {
            loc.name: (loc.remax_id, loc.display_name)
            for loc in locations
        }
        logger.info(f"Loaded {len(self._location_cache)} Remax locations from cache")

        # Load property types
        stmt = select(RemaxPropertyTypeCache)
        result = await self._db.execute(stmt)
        types = result.scalars().all()

        self._property_type_cache = {
            t.name: t.remax_ids
            for t in types
        }
        logger.info(f"Loaded {len(self._property_type_cache)} Remax property types from cache")
        self._cache_loaded = True

    def _get_location_from_cache(self, location_name: str) -> Optional[Tuple[str, str]]:
        """
        Get location ID from cache.

        Args:
            location_name: Location name to look up

        Returns:
            Tuple of (remax_id, display_name) or None if not found
        """
        normalized = location_name.lower().strip()
        return self._location_cache.get(normalized)

    def _get_property_type_from_cache(self, type_name: str) -> Optional[str]:
        """
        Get property type IDs from cache.

        Args:
            type_name: Property type name to look up

        Returns:
            Remax IDs string (e.g., "1,2") or None if not found
        """
        normalized = type_name.lower().strip()
        return self._property_type_cache.get(normalized)

    def _get_driver(self):
        """Create and return a configured Chrome WebDriver (lazy import)"""
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

    def build_search_url(self, page: int = 1) -> str:
        """
        Build Remax search URL using API query parameters.

        Uses cached location and property type IDs from the database.
        If cache is not loaded or location not found, raises ValueError.

        URL format:
        /listings/buy?page=0&pageSize=24&sort=-createdAt&in:operationId=1&in:typeId=1,2&pricein=1:min:max&locations=in::::ID@Name:::
        """
        params = self.search_params
        logger.debug(f"[remax] Search params received: {params}")

        # Build query parameters
        query_parts = []

        # Pagination (0-based)
        query_parts.append(f"page={page - 1}")
        query_parts.append("pageSize=24")
        query_parts.append("sort=-createdAt")

        # Operation type
        op_param = params.get("operation_type", "venta").lower()
        operation_id = self.OPERATION_IDS.get(op_param, "1")
        query_parts.append(f"in:operationId={operation_id}")

        # Property stages (all active)
        query_parts.append("in:eStageId=0,1,2,3,4")

        # Property type - use cache
        prop_param = params.get("property_type", "").lower()
        if prop_param:
            prop_type_ids = self._get_property_type_from_cache(prop_param)
            if prop_type_ids:
                query_parts.append(f"in:typeId={prop_type_ids}")
                logger.debug(f"[remax] Property type '{prop_param}' -> IDs: {prop_type_ids}")
            else:
                logger.debug(f"[remax] Property type '{prop_param}' not found in cache")

        # Price range
        min_price = params.get("min_price")
        max_price = params.get("max_price")
        currency = params.get("currency", "USD").upper()
        currency_id = self.CURRENCY_IDS.get(currency, "1")

        if min_price or max_price:
            min_val = int(min_price) if min_price else 0
            max_val = int(max_price) if max_price else 99999999
            query_parts.append(f"pricein={currency_id}:{min_val}:{max_val}")

        # Location (neighborhood takes priority over city) - use cache
        neighborhoods = params.get("neighborhoods", [])
        city = params.get("city", "")

        logger.debug(f"[remax] Neighborhoods: {neighborhoods}, City: '{city}'")

        location_id = None
        location_name = None
        location_not_found = None  # Track which location wasn't found

        # Priority: first neighborhood, then city
        if neighborhoods:
            for nb in neighborhoods:
                nb_key = nb.lower().strip()
                cached = self._get_location_from_cache(nb_key)
                if cached:
                    location_id, location_name = cached
                    logger.debug(f"[remax] Found location from neighborhood '{nb}': ID={location_id}, Name={location_name}")
                    break
                else:
                    location_not_found = nb

        if not location_id and city:
            city_key = city.lower().strip()
            cached = self._get_location_from_cache(city_key)
            if cached:
                location_id, location_name = cached
                logger.debug(f"[remax] Found location from city '{city}': ID={location_id}, Name={location_name}")
            else:
                # Try partial match in cache
                for key, (lid, lname) in self._location_cache.items():
                    if city_key in key or key in city_key:
                        location_id, location_name = lid, lname
                        logger.debug(f"[remax] Found location from partial match '{city}' -> '{key}': ID={location_id}")
                        break

                if not location_id:
                    location_not_found = city

        # If a specific location was requested but not found in cache, raise error
        if location_not_found and not location_id:
            available_locations = sorted(self._location_cache.keys())[:20]
            raise ValueError(
                f"Localidad '{location_not_found}' no disponible para Remax. "
                f"Contactar admin para agregar el ID. "
                f"Localidades disponibles: {', '.join(available_locations)}..."
            )

        if location_id:
            # Format: in::::ID@Name:::
            location_param = f"in::::{location_id}@{location_name}:::"
            query_parts.append(f"locations={quote(location_param, safe='')}")
        else:
            logger.debug("[remax] No location specified, using global search")

        # Build URL
        base_path = "/listings/buy" if op_param == "venta" else "/listings/rent"
        full_url = f"{self.BASE_URL}{base_path}?{'&'.join(query_parts)}"

        logger.debug(f"[remax] Generated Search URL: {full_url}")
        return full_url

    async def fetch_page(self, url: str) -> str:
        """
        Fetch page with fallback:
        1. curl_cffi / httpx (may work if data is in initial HTML or embedded JSON)
        2. Selenium (for JavaScript-rendered content)

        Remax is a React SPA — property links only appear after JS renders.
        We check for actual property link patterns, not just the word "listings".
        """
        # Level 1+2: curl_cffi / httpx - try first, Remax may embed data in JSON
        try:
            html = await super().fetch_page(url)
            # Check if we got ACTUAL property links (not just the word "listings" in JS code)
            # Property URLs look like: /listings/ph-3-ambientes-... or /listings/venta-casa-...
            has_property_links = bool(re.search(r'href="[^"]*?/listings/[a-z]+-[a-z]+-', html, re.IGNORECASE))
            has_next_data = '__NEXT_DATA__' in html and '"listings"' in html

            if len(html) > 5000 and (has_property_links or has_next_data):
                logger.info(f"[remax] fetch_with_browser_fingerprint OK, length: {len(html)}, has_links={has_property_links}")
                return html
            logger.info(f"[remax] HTTP fetch got page but no property links detected (length={len(html)}), trying Selenium...")
        except Exception as e:
            logger.warning(f"[remax] HTTP fetch failed: {e}, trying Selenium...")

        # Level 3: Selenium fallback for JS-rendered content
        return await asyncio.to_thread(self._fetch_with_selenium, url)

    def _fetch_with_selenium(self, url: str) -> str:
        """Fetch page using Selenium for JavaScript-rendered content."""
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
            logger.info(f"[remax] Selenium loading: {url}")
            driver.get(url)

            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )

            # Wait for Angular app to initialize
            time.sleep(4)

            # Remax-specific card selectors (Angular app uses these classes)
            remax_card_selectors = [
                'a.card-remax__href',  # Main card links
                '.card-remax',  # Card containers
                '[class*="card-remax"]',  # Any card-remax class
                'a.carousel__href',  # Carousel image links
            ]

            # Try to wait for Remax-specific cards first
            found_cards = False
            for selector in remax_card_selectors:
                try:
                    WebDriverWait(driver, 8).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    logger.info(f"[remax] Found Remax cards with selector: {selector}")
                    found_cards = True
                    break
                except Exception:
                    continue

            if not found_cards:
                logger.warning("[remax] No Remax cards found, waiting longer and scrolling...")
                # Scroll to trigger lazy loading
                driver.execute_script("window.scrollTo(0, 300);")
                time.sleep(2)
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight / 2);")
                time.sleep(3)
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(3)
                # Scroll back up to load all content
                driver.execute_script("window.scrollTo(0, 0);")
                time.sleep(2)

                # Try waiting again
                for selector in remax_card_selectors:
                    try:
                        WebDriverWait(driver, 5).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                        )
                        logger.info(f"[remax] Found Remax cards after scrolling: {selector}")
                        found_cards = True
                        break
                    except Exception:
                        continue

            if not found_cards:
                # Fallback: try generic card selectors
                generic_selectors = [
                    '[class*="CardContainer"]',
                    '[class*="property-card"]',
                    '[class*="listing-card"]',
                    'article',
                ]
                for selector in generic_selectors:
                    try:
                        WebDriverWait(driver, 3).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                        )
                        logger.info(f"[remax] Found generic cards: {selector}")
                        break
                    except Exception:
                        continue

            # Final wait for any remaining JS rendering
            time.sleep(2)

            html = driver.page_source
            logger.info(f"[remax] Got HTML via Selenium, length: {len(html)}")

            # Debug: check if cards are in the HTML
            if 'card-remax__href' in html:
                logger.info("[remax] card-remax__href found in HTML source")
            else:
                logger.warning("[remax] card-remax__href NOT found in HTML source")

            return html

        except Exception as e:
            logger.error(f"[remax] Selenium error: {e}")
            raise

    async def scrape_all_pages(self, max_properties: int = 100) -> List[Dict[str, Any]]:
        """
        Override to support Deep Scraping for fallback zones.
        Even if a page returns 0 *filtered* results, we continue if there were *raw* results,
        up to MAX_PAGES.

        Also loads cache from DB before starting if DB session is set.
        """
        # Load cache from DB if session is set and cache not already loaded
        if self._db and not self._cache_loaded:
            await self.load_cache_from_db()

        all_properties: List[Dict[str, Any]] = []
        current_page = 1

        # Track Consecutive Empty Pages (filtered)
        # If we see many empty pages even with raw results, maybe we should stop eventually?
        # For now, we trust MAX_PAGES (which is small, e.g. 10) to bound us.

        while len(all_properties) < max_properties and current_page <= self.MAX_PAGES:
            try:
                # Scrape current page
                cards = await self.scrape_page(current_page)

                # Append cards (if any passed filtering)
                if cards:
                    all_properties.extend(cards)

                # Check termination conditions:
                # 1. No raw results found on page? -> We reached end of site listings. STOP.
                if self._last_raw_count == 0:
                    logger.info(f"[{self.PORTAL_NAME}] No properties found on source page {current_page}, stopping")
                    break

                # 2. Has next page button?
                if not self.has_next_page():
                    logger.info(f"[{self.PORTAL_NAME}] No next page detected, stopping")
                    break

                # 3. Fallback Mode Logging
                if not cards and self._last_raw_count > 0:
                    logger.info(f"[{self.PORTAL_NAME}] Page {current_page} had {self._last_raw_count} raw items but 0 matches. Deep scraping next page...")

                # Rate limiting delay between pages
                await asyncio.sleep(self.DELAY_BETWEEN_PAGES)
                current_page += 1

            except Exception as e:
                logger.error(f"[{self.PORTAL_NAME}] Error on page {current_page}, stopping: {str(e)}")
                break

        try:
            # Clean up
            self._close_driver()
        except:
            pass

        # Trim to max_properties
        result = all_properties[:max_properties]
        logger.info(f"[{self.PORTAL_NAME}] Total properties scraped: {len(result)}")
        return result

    def extract_property_cards(self) -> List[Dict[str, Any]]:
        """Extract property listings from Remax search results page"""
        if not self.soup:
            self._last_raw_count = 0
            return []



        cards = []

        # Debug: show all links on the page to understand structure
        all_links = self.soup.select('a[href]')
        logger.debug(f"[remax] Total links on page: {len(all_links)}")

        # Collect unique hrefs for debugging
        hrefs_debug = set()
        for link in all_links:
            href = link.get('href', '')
            if href and len(href) > 5:
                hrefs_debug.add(href[:100])

        # Show listing-like hrefs
        listing_hrefs = [h for h in hrefs_debug if '/listing' in h.lower()]
        logger.debug(f"[remax] Listing-like hrefs: {listing_hrefs[:15]}")
        logger.debug(f"[remax] Sample hrefs: {list(hrefs_debug)[:20]}")

        # Debug: Show relevant CSS classes
        all_elements = self.soup.select('[class]')
        class_names = set()
        for elem in all_elements:
            for cls in elem.get('class', []):
                if any(kw in cls.lower() for kw in ['card', 'listing', 'property', 'result', 'item']):
                    class_names.add(cls)
        logger.debug(f"[remax] Relevant CSS classes: {list(class_names)[:30]}")

        # Look for property links with multiple patterns
        # Remax uses Angular and specific class names for property cards
        property_patterns = [
            'a.card-remax__href[href*="/listings/"]',  # Remax card links (most specific)
            'a.carousel__href[href*="/listings/"]',  # Remax carousel image links
            'a[href*="/listings/"]',  # Standard listings path (fallback)
            'a[href*="remax.com.ar/listing"]',  # Absolute URLs
            'a[href*="/propiedad"]',  # Alternative property path
            'a[href*="MLS"]',  # MLS number links
        ]

        seen_urls = set()

        for pattern in property_patterns:
            links = self.soup.select(pattern)
            logger.info(f"[remax] Pattern '{pattern}' found {len(links)} links")

            # Debug: show first few hrefs for this pattern
            if links:
                sample_hrefs = [l.get('href', '')[:80] for l in links[:5]]
                logger.info(f"[remax] Sample hrefs for '{pattern}': {sample_hrefs}")

            for link in links:
                href = link.get('href', '')
                if not href:
                    continue

                # Skip search/category pages
                skip_patterns = [
                    '/listings/buy', '/listings/rent', '/listings/sell',
                    '/listings?', 'page=', '/propiedades-en-'
                ]
                if any(skip in href for skip in skip_patterns):
                    logger.debug(f"[remax] Skipping search/category URL: {href[:80]}")
                    continue

                # For /listings/ URLs, ensure there's an actual slug after
                if '/listings/' in href:
                    path_after = href.split('/listings/')[-1].split('?')[0]
                    if not path_after or path_after in ['buy', 'rent', 'sell', '']:
                        logger.debug(f"[remax] Skipping empty slug URL: {href[:80]}")
                        continue

                # Build full URL
                if href.startswith('/'):
                    full_url = urljoin(self.BASE_URL, href)
                elif href.startswith('http'):
                    full_url = href
                else:
                    full_url = f"{self.BASE_URL}/{href}"

                # Avoid duplicates
                if full_url in seen_urls:
                    continue
                seen_urls.add(full_url)

                # Extract data from the link and its parent container
                card_data = self._extract_card_data(link, full_url)
                if card_data:
                    cards.append(card_data)
                    logger.info(f"[remax] Added card: {full_url[:70]}...")

        if not cards:
            logger.debug("[remax] No cards found with link patterns, trying card containers...")
            cards = self._extract_cards_from_containers()

        # Enrich cards with all photos from ng-state JSON
        self._enrich_cards_with_photos(cards)

        # Update raw count state for scrape_all_pages logic
        self._last_raw_count = len(cards)
        logger.debug(f"[remax] Extracted {len(cards)} raw property cards")

        # Return all cards without aggressive filtering
        # The URL already filters by location when available
        # Only apply minimal filtering for specific edge cases
        return cards

    CDN_BASE_URL = "https://d1acdg20u0pmxj.cloudfront.net/"

    def _build_cdn_image_url(self, raw_path: str) -> Optional[str]:
        """Build a CDN image URL from a rawValue path (listings/UUID/UUID)."""
        if not raw_path:
            return None
        if raw_path.startswith("http"):
            return raw_path
        raw_path = raw_path.lstrip("/")
        parts = raw_path.split("/")
        if len(parts) == 3 and parts[0] == "listings":
            listing_uuid = parts[1]
            image_uuid = re.sub(r'\.\w+$', '', parts[2])
            return f"{self.CDN_BASE_URL}listings/{listing_uuid}/1080xAUTO/{image_uuid}.jpg"
        if len(parts) == 4 and parts[0] == "listings":
            listing_uuid = parts[1]
            image_uuid = re.sub(r'\.\w+$', '', parts[3])
            return f"{self.CDN_BASE_URL}listings/{listing_uuid}/1080xAUTO/{image_uuid}.jpg"
        return f"{self.CDN_BASE_URL}{raw_path}"

    def _enrich_cards_with_photos(self, cards: List[Dict[str, Any]]) -> None:
        """
        Enrich card data with all photos from ng-state JSON.

        The ng-state script contains full listing data including all photos.
        Match listings to cards by slug and add all image URLs.
        """
        if not self.soup or not cards:
            return

        ng_state = self.soup.find('script', id='ng-state', type='application/json')
        if not ng_state or not ng_state.string:
            return

        try:
            data = json.loads(ng_state.string)
        except (json.JSONDecodeError, TypeError):
            return

        # Build slug -> photos mapping from ng-state
        slug_to_photos: Dict[str, List[str]] = {}
        for key, value in data.items():
            if not isinstance(value, dict) or 'b' not in value:
                continue
            b = value['b']
            if not isinstance(b, dict) or 'data' not in b:
                continue
            outer = b['data']
            if not isinstance(outer, dict) or 'data' not in outer:
                continue
            items = outer['data']
            if not isinstance(items, list):
                continue

            for item in items:
                if not isinstance(item, dict):
                    continue
                slug = item.get('slug', '')
                photos = item.get('photos', [])
                if slug and photos:
                    urls = []
                    for photo in photos:
                        if isinstance(photo, dict):
                            raw = photo.get('rawValue', '') or photo.get('value', '')
                            if raw:
                                url = self._build_cdn_image_url(raw)
                                if url:
                                    urls.append(url)
                    if urls:
                        slug_to_photos[slug] = urls

        if not slug_to_photos:
            return

        logger.info(f"[remax] Found photos for {len(slug_to_photos)} listings in ng-state")

        # Match cards to photos by slug
        for card in cards:
            source_url = card.get('source_url', '')
            # Extract slug from URL: /listings/{slug}
            match = re.search(r'/listings/([^/?]+)', source_url)
            if not match:
                continue
            slug = match.group(1)
            photos = slug_to_photos.get(slug)
            if photos:
                card['images'] = photos[:20]
                # Update thumbnail to first photo if current thumbnail is missing or SVG
                if not card.get('thumbnail_url') or '.svg' in (card.get('thumbnail_url') or ''):
                    card['thumbnail_url'] = photos[0]

    def _extract_cards_from_containers(self) -> List[Dict[str, Any]]:
        """Fallback: Extract property cards by finding card containers"""
        cards = []

        # Look for card-like containers
        container_selectors = [
            '[class*="CardContainer"]',
            '[class*="PropertyCard"]',
            '[class*="property-card"]',
            '[class*="listing-card"]',
            '[class*="result-item"]',
            '[class*="search-result"]',
            'article[class*="card"]',
            '[data-testid*="listing"]',
            '[data-testid*="property"]',
        ]

        for selector in container_selectors:
            containers = self.soup.select(selector)
            if containers:
                logger.debug(f"[remax] Found {len(containers)} containers with selector: {selector}")

                for container in containers:
                    # Find link within container
                    link = container.select_one('a[href]')
                    if not link:
                        continue

                    href = link.get('href', '')
                    if not href or len(href) < 5:
                        continue

                    # Build full URL
                    if href.startswith('/'):
                        full_url = urljoin(self.BASE_URL, href)
                    elif href.startswith('http'):
                        full_url = href
                    else:
                        full_url = f"{self.BASE_URL}/{href}"

                    card_data = self._extract_card_data(link, full_url)
                    if card_data:
                        cards.append(card_data)

                if cards:
                    break  # Found cards, stop trying other selectors

        # If still no cards, try extracting from embedded JSON data
        if not cards:
            cards = self._extract_from_json_data()

        return cards

    def _extract_from_json_data(self) -> List[Dict[str, Any]]:
        """Extract property data from JSON embedded in script tags (common for React sites)"""
        cards = []

        # Look for script tags with JSON data
        script_tags = self.soup.select('script')

        for script in script_tags:
            script_text = script.string
            if not script_text:
                continue

            # Look for patterns that might contain listing data
            patterns_to_try = [
                r'__NEXT_DATA__[^{]*({.*?})\s*</script>',  # Next.js
                r'window\.__INITIAL_STATE__\s*=\s*({.*?});',  # Redux state
                r'window\.listings\s*=\s*(\[.*?\]);',  # Direct listings array
                r'"listings"\s*:\s*(\[.*?\])',  # Listings in JSON
                r'"properties"\s*:\s*(\[.*?\])',  # Properties in JSON
            ]

            for pattern in patterns_to_try:
                matches = re.findall(pattern, script_text, re.DOTALL)
                for match in matches:
                    try:
                        data = json.loads(match)
                        if isinstance(data, list):
                            items = data
                        elif isinstance(data, dict):
                            # Try to find listings array in the dict
                            items = (
                                data.get('listings') or
                                data.get('properties') or
                                data.get('results') or
                                data.get('props', {}).get('pageProps', {}).get('listings') or
                                []
                            )
                        else:
                            continue

                        for item in items:
                            if isinstance(item, dict):
                                card = self._parse_json_listing(item)
                                if card:
                                    cards.append(card)

                        if cards:
                            logger.debug(f"[remax] Extracted {len(cards)} cards from JSON data")
                            return cards

                    except json.JSONDecodeError:
                        continue

        return cards

    def _parse_json_listing(self, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse a single listing from JSON data"""
        # Try to extract URL - different possible keys
        url = (
            item.get('url') or
            item.get('link') or
            item.get('detailUrl') or
            item.get('propertyUrl') or
            item.get('slug')
        )

        if not url:
            # Try to build URL from ID
            listing_id = item.get('id') or item.get('mlsId') or item.get('listingId')
            if listing_id:
                url = f"/listings/{listing_id}"

        if not url:
            return None

        # Build full URL
        if url.startswith('/'):
            full_url = urljoin(self.BASE_URL, url)
        elif url.startswith('http'):
            full_url = url
        else:
            full_url = f"{self.BASE_URL}/listings/{url}"

        # Extract price
        price = item.get('price') or item.get('listPrice') or item.get('salePrice')
        if isinstance(price, dict):
            price = price.get('amount') or price.get('value')

        # Extract currency
        currency = item.get('currency') or item.get('priceCurrency')
        if not currency:
            currency = 'USD' if price and price > 10000 else None

        return {
            'source': 'remax',
            'source_url': full_url,
            'source_id': item.get('id') or item.get('mlsId') or self._extract_id_from_url(full_url),
            'title': item.get('title') or item.get('name') or item.get('address'),
            'price': int(price) if price else None,
            'currency': currency,
            'thumbnail_url': item.get('image') or item.get('photo') or item.get('mainPhoto'),
            'location_preview': item.get('address') or item.get('location') or item.get('neighborhood'),
        }

    def _extract_card_data(self, link_elem, url: str) -> Optional[Dict[str, Any]]:
        """Extract data from a listing link element"""
        data = {
            'source': 'remax',
            'source_url': url,
            'source_id': self._extract_id_from_url(url),
            'title': None,
            'price': None,
            'currency': None,
            'thumbnail_url': None,
            'location_preview': None,
            'address': None,
        }

        # Try to find the parent card container
        # Remax structure: div.card-remax > div.card-remax__container > a.card-remax__href
        # Property images are in the carousel at div.card-remax level,
        # NOT inside div.card-remax__container (which only has SVG icons).
        # We need to walk up to div.card-remax (the outermost card div).
        parent = link_elem
        card_candidate = None
        for _ in range(6):  # Go up to 6 levels
            parent = parent.parent
            if parent is None:
                break
            parent_class = parent.get('class', [])
            is_card = any('card' in c.lower() or 'listing' in c.lower() or 'property' in c.lower()
                   for c in parent_class if isinstance(c, str))
            is_image = any('image' in c.lower() or 'img' in c.lower() or 'carousel' in c.lower() or 'slider' in c.lower()
                   for c in parent_class if isinstance(c, str))

            if is_card and not is_image:
                card_candidate = parent
                # Don't break - keep going up to find the outermost card container
                # e.g. card-remax__container -> card-remax

        search_context = card_candidate if card_candidate else (parent if parent else link_elem)

        # Extract title
        # Remax often puts the title in .card__description
        title_elem = search_context.select_one(
            '.card__description, h2, h3, h4, [class*="title"], [class*="Title"], [class*="description"]'
        )
        if title_elem:
            data['title'] = title_elem.get_text(strip=True)[:500]
        else:
            # Use link text as fallback
            link_text = link_elem.get_text(strip=True)
            if link_text and len(link_text) > 10:
                data['title'] = link_text[:500]

        # Extract price
        price_elem = search_context.select_one(
            '.card__price, [class*="price"], [class*="Price"]'
        )
        if price_elem:
            price_text = price_elem.get_text(strip=True)
            price_amount, currency = self.clean_price(price_text)
            data['price'] = price_amount
            data['currency'] = currency

        # Extract all property images from HTML - skip SVGs, icons, assets, agent photos
        html_images = []
        for img_elem in search_context.find_all('img'):
            img_url = None
            for attr in ['src', 'data-src', 'data-lazy', 'srcset']:
                candidate = img_elem.get(attr)
                if candidate and not candidate.startswith('data:'):
                    if attr == 'srcset':
                        candidate = candidate.split(',')[0].split()[0]
                    img_url = candidate
                    break

            if not img_url:
                continue

            # Skip non-property images
            url_lower = img_url.lower()
            if any(skip in url_lower for skip in ['.svg', '/assets/', '/icons/', '/agents/', '/logo', '/avatar/']):
                continue

            if img_url.startswith('//'):
                img_url = f"https:{img_url}"
            elif img_url.startswith('/'):
                img_url = urljoin(self.BASE_URL, img_url)

            if img_url not in html_images:
                html_images.append(img_url)

        if html_images:
            data['thumbnail_url'] = html_images[0]
            data['images'] = html_images

        # Extract location
        # Remax separates street address (.card__address) and neighborhood/city (.card__ubication)
        
        # 1. Street Address
        # Use specific class first
        address_elem = search_context.select_one('.card__address')
        if not address_elem:
             address_elem = search_context.select_one('[class*="address"]:not([class*="ubication"])')
        
        if address_elem:
            val = address_elem.get_text(strip=True)
            if val:
                data['address'] = val[:200]
        
        # 2. Neighborhood / City
        # Avoid matching the parent container .card__ubication-and-address
        ubication_elem = search_context.select_one('.card__ubication')
        if not ubication_elem:
             ubication_elem = search_context.select_one('[class*="ubication"]:not([class*="address"])')
             
        if ubication_elem:
            val = ubication_elem.get_text(strip=True)
            if val:
                data['location_preview'] = val[:200]
        
        # Fallback if separate fields not found
        if not data.get('address') and not data.get('location_preview'):
             location_elem = search_context.select_one(
                '[class*="location"], [class*="Location"]'
             )
             if location_elem:
                 data['location_preview'] = location_elem.get_text(strip=True)[:200]

        # Extract Features (Area, Rooms, Baths)
        # Look for feature items
        feature_items = search_context.select('.card__feature--item, .feature--item, [class*="feature--item"]')
        
        obs_list = []
        for item in feature_items:
            text = item.get_text(strip=True).lower()
            
            # Clean text for easier parsing
            clean_token = text.replace(':', '')
            
            # Helper to extract float safely
            def get_float(s):
                # Matches numbers like 54.44 or 54,44 or 100
                match = re.search(r'(\d+(?:[\.,]\d+)?)', s)
                if match:
                    val_str = match.group(1).replace(',', '.')
                    # If it looks like thousands (e.g. 1.200), we might need careful handling,
                    # but for area 54.44 is common.
                    # User reported 88.06 becoming 8806.
                    return float(val_str)
                return None

            # Area
            if 'm² totales' in clean_token:
                val = get_float(clean_token)
                if val:
                    data['total_area'] = val
            elif 'm² cubiertos' in clean_token:
                val = get_float(clean_token)
                if val:
                    data['covered_area'] = val
            elif 'semicubierta' in clean_token or 'semi cub' in clean_token:
                val = get_float(clean_token)
                if val:
                    # Storing in a custom way or relying on schema?
                    # Schema usually has total/covered. We can put this in observations or just log it.
                    # User said "semi_covered_area" in db. If not in dict, maybe put in observations?
                    # The standard dictionary keys check: 'semi_covered_area' isn't standard in Monitoring?
                    # Let's check if we can add it to data. If parser ignores it, fine.
                    data['semi_covered_area'] = val

            # Rooms / Bedrooms
            elif 'dormitorio' in clean_token:
                nums = re.findall(r'(\d+)', clean_token)
                if nums:
                    data['bedrooms'] = int(nums[0])
            elif 'ambiente' in clean_token and 'bedrooms' not in data:
                # Fallback: Estimate bedrooms as environments - 1 (usually living room)
                nums = re.findall(r'(\d+)', clean_token)
                if nums:
                    amb = int(nums[0])
                    data['bedrooms'] = max(0, amb - 1) if amb > 1 else 0

            # Bathrooms
            elif 'baño' in clean_token:
                nums = re.findall(r'(\d+)', clean_token)
                if nums:
                    data['bathrooms'] = int(nums[0])
            
            # Parking
            elif 'cochera' in clean_token:
                 nums = re.findall(r'(\d+)', clean_token)
                 if nums:
                     data['parking_spaces'] = int(nums[0])
                 else:
                     data['parking_spaces'] = 1
            
            # Observations (Antiquity, Floors)
            # We iterate all items, so we can append to a list then join
            elif 'antigüedad' in clean_token or 'años' in clean_token:
                 obs_list.append(item.get_text(strip=True))
            elif 'pisos' in clean_token:
                 obs_list.append(item.get_text(strip=True))

        if obs_list:
             data['observations'] = ' | '.join(obs_list)


        # If location preview is just address, try to append from URL slug if possible?
        # Actually, let's just stick to what's on the card for now.

        return data

    def _extract_id_from_url(self, url: str) -> Optional[str]:
        """Extract listing ID/slug from URL"""
        # Remax URLs: /listings/venta-departamento-en-palermo-123
        match = re.search(r'/listings/([^/?]+)', url)
        if match:
            slug = match.group(1)
            # Skip search pages
            if slug not in ['buy', 'rent']:
                return slug
        return None

    def has_next_page(self) -> bool:
        """Check if there's a next page of results"""
        if not self.soup:
            return False

        # Look for pagination elements
        pagination_selectors = [
            'a[href*="page="]',
            'button[class*="next"]',
            '[class*="pagination"] a',
            'a[rel="next"]',
            'button[aria-label*="Next"]',
            'button[aria-label*="Siguiente"]',
        ]

        for selector in pagination_selectors:
            try:
                elements = self.soup.select(selector)
                for elem in elements:
                    # Check disabled state
                    if elem.has_attr('disabled'):
                        continue
                    
                    # For buttons with aria-label, we trust the label
                    if elem.name == 'button' and ('next' in elem.get('aria-label', '').lower() or 'siguiente' in elem.get('aria-label', '').lower()):
                        return True

                    text = elem.get_text(strip=True).lower()
                    if 'siguiente' in text or 'next' in text or '>' in text:
                        return True
            except Exception:
                continue

        # Debug: Dump HTML for card analysis
        with open("remax_card_dump.html", "w", encoding="utf-8") as f:
            f.write(str(self.soup))
        logger.info("[remax] Dumped HTML to remax_card_dump.html for analysis")

        return False

    def get_total_results(self) -> Optional[int]:
        """Try to extract total number of results from page"""
        if not self.soup:
            return None

        selectors = [
            '[class*="result-count"]',
            '[class*="ResultCount"]',
            '[class*="total"]',
        ]

        for selector in selectors:
            elem = self.soup.select_one(selector)
            if elem:
                text = elem.get_text()
                numbers = re.findall(r'(\d+)', text.replace('.', '').replace(',', ''))
                if numbers:
                    return max(int(n) for n in numbers)

        return None
