"""
Argenprop Listing Scraper
Scrapes search result pages from www.argenprop.com.ar to extract property URLs
"""
import re
import logging
import asyncio
from typing import Dict, Any, List, Optional
from urllib.parse import urljoin, quote
from bs4 import BeautifulSoup
from .listing_base import BaseListingScraper

logger = logging.getLogger(__name__)


class ArgenpropListingScraper(BaseListingScraper):
    """
    Scraper for Argenprop search results / listing pages.

    Builds URLs like:
    - https://www.argenprop.com/departamento/venta/capital-federal
    - https://www.argenprop.com/departamento/venta/capital-federal/palermo--precio-desde-100000-dolares--precio-hasta-200000-dolares
    - https://www.argenprop.com/departamento/alquiler/capital-federal?pagina-2
    """

    PORTAL_NAME = "argenprop"
    BASE_URL = "https://www.argenprop.com"
    MAX_PAGES = 10
    DELAY_BETWEEN_PAGES = 2.0

    # Mapping for property types in URL (Argenprop uses plural, except PH)
    PROPERTY_TYPE_MAP = {
        "departamento": "departamentos",
        "casa": "casas",
        "ph": "ph",  # PH stays singular
        "terreno": "terrenos",
        "local": "locales-comerciales",
        "oficina": "oficinas",
        "cochera": "cocheras",
        "galpon": "galpones",
        "fondo_comercio": "fondos-de-comercio",
    }

    # Mapping for operation types in URL
    OPERATION_TYPE_MAP = {
        "venta": "venta",
        "alquiler": "alquiler",
        "alquiler_temporal": "alquiler-temporario",
    }

    # Mapping for provinces/cities in URL (slug format)
    LOCATION_MAP = {
        # Capital Federal / CABA
        "capital federal": "capital-federal",
        "caba": "capital-federal",
        "buenos aires": "capital-federal",
        # GBA
        "zona norte": "zona-norte",
        "zona sur": "zona-sur",
        "zona oeste": "zona-oeste",
        # Provinces
        "cordoba": "cordoba",
        "mendoza": "mendoza",
        "santa fe": "santa-fe",
        "rosario": "rosario",
        "mar del plata": "mar-del-plata",
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
        "liniers": "liniers",
        "mataderos": "mataderos",
        "paternal": "paternal",
    }

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
        Build Argenprop search URL from parameters.

        URL structure:
        /[property_type]/[operation]/[location]/[neighborhood]--[filters]?pagina-N

        Examples:
        - /departamento/venta/capital-federal
        - /departamento/venta/capital-federal/palermo
        - /casa/alquiler/zona-norte--precio-desde-500-dolares
        """
        params = self.search_params

        # Build path segments
        segments = []

        # Property type (required for Argenprop, defaults to departamentos)
        property_type = params.get("property_type", "departamento").lower()
        if property_type in self.PROPERTY_TYPE_MAP:
            segments.append(self.PROPERTY_TYPE_MAP[property_type])
        else:
            segments.append("departamentos")  # Default

        # Operation type (required)
        operation = params.get("operation_type", "venta").lower()
        segments.append(self.OPERATION_TYPE_MAP.get(operation, "venta"))

        # Neighborhoods and Location
        # NOTE: In Argenprop, if neighborhood is specified, don't include city
        # because it makes the search broader instead of more specific
        neighborhoods = params.get("neighborhoods", [])
        has_neighborhood = neighborhoods and len(neighborhoods) >= 1

        if has_neighborhood:
            # Single neighborhood - add directly without city
            # Argenprop URLs: /ph/venta/palermo (not /ph/venta/capital-federal/palermo)
            neighborhood = neighborhoods[0].lower()
            neighborhood_slug = self.NEIGHBORHOOD_MAP.get(neighborhood, self._slugify(neighborhood))
            segments.append(neighborhood_slug)
        else:
            # No neighborhood - use city/province
            city = params.get("city", "").lower()
            province = params.get("province", "").lower()
            location = city or province
            if location:
                location_slug = self.LOCATION_MAP.get(location, self._slugify(location))
                segments.append(location_slug)

        # Price filter segment (format: dolares-100000-200000 or pesos-100000-200000)
        currency = params.get("currency", "USD").upper()
        currency_slug = "dolares" if currency == "USD" else "pesos"

        min_price = params.get("min_price")
        max_price = params.get("max_price")

        if min_price or max_price:
            min_val = int(min_price) if min_price else 0
            max_val = int(max_price) if max_price else 999999999
            segments.append(f"{currency_slug}-{min_val}-{max_val}")

        # Build base URL
        url = f"{self.BASE_URL}/{'/'.join(segments)}"

        # Add pagination
        if page > 1:
            url += f"?pagina-{page}"

        return url

    def extract_property_cards(self) -> List[Dict[str, Any]]:
        """
        Extract property listings from Argenprop search results page.

        Returns list of dicts with:
        - source_url: Full property URL
        - source_id: Property ID from Argenprop
        - title: Property title
        - price: Price amount
        - currency: USD or ARS
        - thumbnail_url: Main image thumbnail
        - location_preview: Neighborhood/city text
        """
        if not self.soup:
            return []

        cards = []

        # Argenprop listing card selectors (based on site structure)
        card_selectors = [
            'div.listing__item',
            'div[class*="listing-item"]',
            'article.property-card',
            'div.property-item',
            '.card-listing',
            'a[class*="card"]',
        ]

        card_elements = []
        for selector in card_selectors:
            card_elements = self.soup.select(selector)
            if card_elements:
                logger.debug(f"Found {len(card_elements)} cards with selector: {selector}")
                break

        if not card_elements:
            # Fallback: look for any links to property pages
            property_links = self.soup.select('a[href*="/propiedad/"], a[href*="/departamento/"], a[href*="/casa/"]')
            logger.debug(f"Fallback: found {len(property_links)} property links")

            seen_urls = set()
            for link in property_links:
                href = link.get('href', '')
                if href and href not in seen_urls and self._is_property_url(href):
                    seen_urls.add(href)
                    full_url = urljoin(self.BASE_URL, href)
                    cards.append({
                        'source_url': full_url,
                        'source_id': self._extract_id_from_url(full_url),
                        'source': 'argenprop',
                        'title': link.get_text(strip=True)[:200] or None,
                        'price': None,
                        'currency': None,
                        'thumbnail_url': None,
                        'location_preview': None,
                        'address': None,
                        'description': None,
                        'total_area': None,
                        'covered_area': None,
                        'bedrooms': None,
                        'bathrooms': None,
                        'parking_spaces': None,
                    })
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

        # Property URLs typically have a numeric ID
        has_id = bool(re.search(r'/\d+', url))

        # Exclude search/listing pages
        is_listing = any(x in url for x in ['?pagina', 'pagina-', '/buscar', '/search'])

        return has_id and not is_listing

    def _extract_id_from_url(self, url: str) -> Optional[str]:
        """Extract property ID from URL"""
        match = re.search(r'/(\d+)(?:[/-]|$)', url)
        if match:
            return match.group(1)

        # Fallback: last numeric segment
        parts = url.rstrip('/').split('/')
        for part in reversed(parts):
            if part.isdigit():
                return part

        return None

    def _parse_card(self, card) -> Optional[Dict[str, Any]]:
        """Parse a single property card element.

        Extracts all available data from an Argenprop listing card:
        URL, title, price, thumbnail, location, address, description,
        area, bedrooms, bathrooms, parking — mirroring what the
        individual property scraper (argenprop.py) produces.
        """
        data = {
            'source': 'argenprop',
            'source_url': None,
            'source_id': None,
            'title': None,
            'price': None,
            'currency': None,
            'thumbnail_url': None,
            'location_preview': None,
            'address': None,
            'neighborhood': None,
            'city': None,
            'description': None,
            'total_area': None,
            'covered_area': None,
            'semi_covered_area': None,
            'uncovered_area': None,
            'lot_area': None,
            'bedrooms': None,
            'bathrooms': None,
            'parking_spaces': None,
        }

        # --- Extract URL ---
        link_selectors = [
            'a.card__link',
            'a[href*="/propiedad/"]',
            'a[href*="--"]',
            'a[class*="link"]',
            'a',
        ]

        link = None
        for selector in link_selectors:
            link = card.select_one(selector)
            if link and link.get('href'):
                break

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

        # --- Extract title ---
        title_selectors = [
            '.card__title',
            '.card__address',
            'h2',
            'h3',
            '.title',
            '[class*="title"]',
        ]

        for selector in title_selectors:
            title_elem = card.select_one(selector)
            if title_elem:
                data['title'] = title_elem.get_text(strip=True)[:500]
                break

        # --- Extract price ---
        price_selectors = [
            '.card__price',
            '.price',
            '[class*="price"]',
            '[class*="precio"]',
        ]

        for selector in price_selectors:
            price_elem = card.select_one(selector)
            if price_elem:
                price_text = price_elem.get_text(strip=True)
                price_amount, currency = self.clean_price(price_text)
                data['price'] = price_amount
                data['currency'] = currency
                break

        # --- Extract thumbnail ---
        img_selectors = [
            'img.card__image',
            'img[class*="image"]',
            'img[src*="argenprop"]',
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

        # --- Extract location / address ---
        location_selectors = [
            '.card__location',
            '.card__address',
            '.location',
            '[class*="location"]',
            '[class*="address"]',
            '[class*="zona"]',
            '[class*="ubic"]',
        ]

        for selector in location_selectors:
            loc_elem = card.select_one(selector)
            if loc_elem:
                loc_text = loc_elem.get_text(strip=True)[:200]
                if loc_text:
                    # If it looks like a street address (has numbers), put in address
                    if re.search(r'\d', loc_text):
                        data['address'] = loc_text
                    else:
                        data['location_preview'] = loc_text
                break

        # Location fallback: scan card text for neighborhood references
        if not data['location_preview']:
            for elem in card.select('p, span, div'):
                text = elem.get_text(strip=True)
                if not text or len(text) > 100 or len(text) < 3:
                    continue
                if re.match(r'^[\$USD\d]', text):
                    continue
                text_lower = text.lower()
                # Comma-separated location: "Coghlan, Capital Federal"
                if ',' in text and any(
                    loc in text_lower for loc in [
                        'capital federal', 'buenos aires', 'caba', 'gba',
                        'córdoba', 'cordoba', 'mendoza', 'rosario',
                    ]
                ):
                    data['location_preview'] = text
                    break
                # Known neighborhoods
                known = [
                    'palermo', 'belgrano', 'recoleta', 'caballito', 'coghlan',
                    'villa crespo', 'colegiales', 'nuñez', 'nunez', 'almagro',
                    'san telmo', 'villa urquiza', 'saavedra', 'chacarita',
                    'villa devoto', 'flores', 'floresta', 'boedo', 'barracas',
                    'villa del parque', 'villa luro', 'villa pueyrredon',
                    'liniers', 'mataderos', 'paternal', 'parque patricios',
                    'puerto madero', 'san nicolas', 'monserrat', 'barrio norte',
                    'constitucion', 'balvanera', 'la boca',
                ]
                for nb in known:
                    if nb in text_lower:
                        data['location_preview'] = text
                        break
                if data['location_preview']:
                    break

        # If title looks like a street address, use it as address
        if data['title'] and not data['address']:
            title_text = data['title']
            if re.match(r'^(Av\.?|Avenida|Calle|Bv\.?|Boulev|Pasaje|Pje\.?)\s', title_text, re.IGNORECASE):
                data['address'] = title_text
            elif re.search(r'\b\d{2,5}\b', title_text) and len(title_text) < 80:
                data['address'] = title_text

        # --- Extract neighborhood from title pattern ---
        # Titles often look like "PH en Venta en Coghlan" or "Casa en Alquiler en Palermo"
        if data['title'] and not data['neighborhood']:
            title_text = data['title']
            # Pattern: "... en [Neighborhood]" at the end
            # Match: "en Coghlan", "en Villa Crespo", "en Villa del Parque"
            match = re.search(
                r'\ben\s+(?:venta|alquiler)\s+en\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+(?:del?\s+)?[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)*)',
                title_text,
                re.IGNORECASE
            )
            if match:
                data['neighborhood'] = match.group(1).strip()

        # --- Extract description ---
        desc_selectors = [
            '.card__info',
            '.card__description',
            '[class*="description"]',
            '[class*="subtitle"]',
        ]
        for selector in desc_selectors:
            desc_elem = card.select_one(selector)
            if desc_elem:
                data['description'] = desc_elem.get_text(strip=True)[:1000]
                break

        # --- Extract features (area, rooms, bathrooms, parking) ---
        features_selectors = [
            '.card__main-features',
            '.card__features',
            '[class*="main-features"]',
            '[class*="CardFeatures"]',
            '[class*="features"]',
            'ul.card__amenities',
        ]

        features_text = ""
        for selector in features_selectors:
            feat_elem = card.select_one(selector)
            if feat_elem:
                features_text = feat_elem.get_text(" ", strip=True)
                break

        # Fallback: collect text from all small spans/lis that look like features
        if not features_text:
            snippets = []
            for elem in card.select('span, li'):
                txt = elem.get_text(strip=True)
                if re.search(r'm[²2]|amb|bañ|dorm|coch|sup|cubierto', txt, re.IGNORECASE):
                    snippets.append(txt)
            if snippets:
                features_text = " ".join(snippets)

        # Last fallback: scan entire card text for feature patterns
        if not features_text:
            full_text = card.get_text(" ", strip=True)
            if re.search(r'\d+\s*m[²2]|\d+\s*amb|\d+\s*bañ|\d+\s*dorm', full_text, re.IGNORECASE):
                features_text = full_text

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

        Looks for pagination elements or "siguiente" links.
        """
        if not self.soup:
            return False

        # Look for pagination with valid CSS selectors
        pagination_selectors = [
            'a[href*="pagina-"]',
            '.pagination a.next',
            '.pagination .siguiente',
            'a[rel="next"]',
        ]

        for selector in pagination_selectors:
            try:
                next_link = self.soup.select_one(selector)
                if next_link:
                    return True
            except Exception:
                continue

        # Fallback: search for "Siguiente" / ">" links by text content
        # (replaces invalid :contains() pseudo-selector)
        for a_tag in self.soup.select('a'):
            text = a_tag.get_text(strip=True).lower()
            if text in ('siguiente', '>', 'next', '\u00bb'):
                return True

        # Check if there are more results indicated
        result_count_elem = self.soup.select_one('[class*="result-count"], [class*="total"]')
        if result_count_elem:
            text = result_count_elem.get_text()
            # Parse "Mostrando 1-20 de 150 resultados"
            match = re.search(r'(\d+)\s*-\s*(\d+)\s*de\s*(\d+)', text)
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
            '[class*="result-count"]',
            '[class*="total"]',
            '.search-results-count',
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

    async def scrape_all_pages(self, max_properties: int = 100) -> List[Dict[str, Any]]:
        """
        Scrape all pages, then enrich with detail page data (images).
        """
        cards = await super().scrape_all_pages(max_properties)
        # Enrich cards with images from detail pages
        if cards:
            cards = await self._enrich_cards_from_detail(cards)
        return cards

    async def _enrich_cards_from_detail(
        self, cards: List[Dict[str, Any]], max_details: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Fetch gallery images and location data for each property.

        Uses two API calls per property:
        1. Gallery API: /aviso/gallerypartial?idAviso=X (images)
        2. Detail page: Full URL (address, neighborhood from data attributes)
        """
        from .http_client import fetch_with_browser_fingerprint

        enriched = 0
        to_enrich = cards[:max_details]
        print(f"[DEBUG] [argenprop] Enriching {len(to_enrich)} cards...")

        for i, card in enumerate(to_enrich):
            url = card.get('source_url')
            source_id = card.get('source_id')

            if not source_id and url:
                # Extract ID from URL: /ph-en-venta-en-coghlan-18928249
                match = re.search(r'-(\d+)$', url.rstrip('/'))
                if match:
                    source_id = match.group(1)

            if not source_id:
                continue

            try:
                # Fetch images from gallery API
                images = await self._fetch_gallery_images(source_id)
                if images:
                    card['images'] = images

                # Fetch location and surface data from detail page
                if url:
                    detail_data = await self._fetch_detail_data(url)
                    if detail_data:
                        # Location data
                        if detail_data.get('address'):
                            card['address'] = detail_data['address']
                        if detail_data.get('neighborhood'):
                            card['neighborhood'] = detail_data['neighborhood']
                        if detail_data.get('city'):
                            card['city'] = detail_data['city']
                        # Surface areas (override card data with detail page data)
                        if detail_data.get('covered_area'):
                            card['covered_area'] = detail_data['covered_area']
                        if detail_data.get('semi_covered_area'):
                            card['semi_covered_area'] = detail_data['semi_covered_area']
                        if detail_data.get('uncovered_area'):
                            card['uncovered_area'] = detail_data['uncovered_area']
                        if detail_data.get('total_area'):
                            card['total_area'] = detail_data['total_area']
                        if detail_data.get('lot_area'):
                            card['lot_area'] = detail_data['lot_area']

                n_imgs = len(images) if images else 0
                neighborhood = card.get('neighborhood', '-')
                covered = card.get('covered_area', '-')
                total = card.get('total_area', '-')
                enriched += 1
                print(f"[DEBUG] [argenprop]   Card {i+1}/{len(to_enrich)}: {n_imgs} imgs, barrio={neighborhood}, cub={covered}, tot={total}")

            except Exception as e:
                logger.debug(f"[argenprop] Error enriching card {i+1}: {e}")
                print(f"[DEBUG] [argenprop]   Card {i+1}/{len(to_enrich)}: ERROR - {e}")

            # Rate limit between requests
            if i < len(to_enrich) - 1:
                await asyncio.sleep(1.5)

        print(f"[DEBUG] [argenprop] Enriched {enriched}/{len(to_enrich)} cards")
        return cards

    async def _fetch_detail_data(self, url: str) -> Dict[str, Any]:
        """
        Fetch address, neighborhood, and surface areas from detail page.

        Argenprop stores location in data attributes:
        - data-barrio="Coghlan"
        - data-localidad="Capital Federal"

        Surface areas in #section-superficie:
        - Sup. Cubierta: X m2
        - Sup. Semicubierta: X m2
        - Sup. Descubierta: X m2
        - Sup. Total: X m2
        - Sup. Terreno: X m2
        """
        from .http_client import fetch_with_browser_fingerprint

        result = {
            'address': None,
            'neighborhood': None,
            'city': None,
            'covered_area': None,
            'semi_covered_area': None,
            'uncovered_area': None,
            'total_area': None,
            'lot_area': None,
        }

        try:
            html = await fetch_with_browser_fingerprint(url, self.user_agent)
            if not html:
                return result

            soup = BeautifulSoup(html, 'html.parser')

            # === LOCATION EXTRACTION ===

            # Strategy 1: Extract from data attributes (most reliable)
            data_elem = soup.find(attrs={'data-barrio': True})
            if data_elem:
                result['neighborhood'] = data_elem.get('data-barrio')
                result['city'] = data_elem.get('data-localidad')

            # Strategy 2: Extract address from titlebar
            address_elem = soup.select_one('.titlebar__address, h2.titlebar__address')
            if address_elem:
                result['address'] = address_elem.get_text(strip=True)

            # Strategy 3: Fallback - parse location-container
            if not result['neighborhood']:
                loc_container = soup.select_one('.location-container, p.location-container')
                if loc_container:
                    loc_text = loc_container.get_text(strip=True)
                    parts = [p.strip() for p in loc_text.split(',')]
                    if len(parts) >= 1:
                        result['neighborhood'] = parts[0]
                    if len(parts) >= 2:
                        result['city'] = parts[1]

            # Strategy 4: Extract from titlebar__title
            if not result['neighborhood']:
                title_elem = soup.select_one('.titlebar__title, h2.titlebar__title')
                if title_elem:
                    title_text = title_elem.get_text(strip=True)
                    match = re.search(r'en\s+([^,]+),\s*(.+)', title_text)
                    if match:
                        result['neighborhood'] = match.group(1).strip()
                        result['city'] = match.group(2).strip()

            # === SURFACE AREA EXTRACTION ===

            # Find the superficie section
            superficie_section = soup.select_one('#section-superficie')
            if superficie_section:
                for li in superficie_section.find_all('li'):
                    text = li.get_text(strip=True)
                    # Extract number from text like "Sup. Cubierta: 67 m2"
                    match = re.search(r'(\d+(?:[.,]\d+)?)\s*m[²2]?', text)
                    if match:
                        value = float(match.group(1).replace(',', '.'))
                        text_lower = text.lower()

                        if 'cubierta' in text_lower and 'semi' not in text_lower and 'desc' not in text_lower:
                            result['covered_area'] = value
                        elif 'semicubierta' in text_lower or 'semi cubierta' in text_lower:
                            result['semi_covered_area'] = value
                        elif 'descubierta' in text_lower or 'desc' in text_lower:
                            result['uncovered_area'] = value
                        elif 'total' in text_lower:
                            result['total_area'] = value
                        elif 'terreno' in text_lower:
                            result['lot_area'] = value

            # Fallback: scan all property-features for surface data
            if not result['covered_area'] and not result['total_area']:
                for li in soup.select('.property-features li, ul.property-features li'):
                    text = li.get_text(strip=True)
                    if 'm2' in text.lower() or 'm²' in text:
                        match = re.search(r'(\d+(?:[.,]\d+)?)\s*m[²2]?', text)
                        if match:
                            value = float(match.group(1).replace(',', '.'))
                            text_lower = text.lower()

                            if 'cubierta' in text_lower and 'semi' not in text_lower:
                                if not result['covered_area']:
                                    result['covered_area'] = value
                            elif 'total' in text_lower:
                                if not result['total_area']:
                                    result['total_area'] = value

        except Exception as e:
            logger.debug(f"[argenprop] Error fetching detail data: {e}")

        return result

    async def _fetch_gallery_images(self, aviso_id: str) -> List[str]:
        """
        Fetch images from Argenprop's gallery API endpoint.

        Endpoint: /aviso/gallerypartial?idAviso=X
        Returns HTML partial with image URLs.
        """
        from .http_client import fetch_with_browser_fingerprint

        gallery_url = f"{self.BASE_URL}/aviso/gallerypartial?idAviso={aviso_id}"

        try:
            html = await fetch_with_browser_fingerprint(gallery_url, self.user_agent)
            return self._extract_gallery_images(html)
        except Exception as e:
            logger.debug(f"[argenprop] Gallery fetch failed for {aviso_id}: {e}")
            return []

    def _extract_gallery_images(self, html: str) -> List[str]:
        """Extract image URLs from gallery HTML partial."""
        images: List[str] = []
        seen: set = set()

        if not html:
            return images

        soup = BeautifulSoup(html, 'html.parser')

        # Strategy 1: Look for img tags with src or data-src
        for img in soup.find_all('img'):
            for attr in ['src', 'data-src', 'data-lazy']:
                url = img.get(attr, '')
                if url and 'static-content' in url and url not in seen:
                    # Upgrade to large version
                    upgraded = self._upgrade_image_url(url)
                    if upgraded not in seen:
                        seen.add(upgraded)
                        images.append(upgraded)
                    break

        # Strategy 2: Look for background-image in style attributes
        if not images:
            for elem in soup.find_all(attrs={'style': True}):
                style = elem.get('style', '')
                urls = re.findall(r'url\(([^)]+)\)', style)
                for url in urls:
                    url = url.strip('"\'')
                    if 'static-content' in url and url not in seen:
                        upgraded = self._upgrade_image_url(url)
                        if upgraded not in seen:
                            seen.add(upgraded)
                            images.append(upgraded)

        # Strategy 3: Extract from any URL pattern in the HTML
        if not images:
            url_matches = re.findall(
                r'https?://[^"\'>\s]+static-content/[^"\'>\s]+\.(?:jpg|jpeg|png|webp)',
                html,
                re.IGNORECASE
            )
            for url in url_matches:
                if url not in seen:
                    upgraded = self._upgrade_image_url(url)
                    if upgraded not in seen:
                        seen.add(upgraded)
                        images.append(upgraded)

        return images[:20]

    @staticmethod
    def _upgrade_image_url(url: str) -> str:
        """Upgrade Argenprop image URL to larger resolution."""
        # Argenprop uses suffixes: _u_small.jpg, _u_medium.jpg, _u_large.jpg
        # Upgrade to large version
        url = re.sub(r'_u_small\.', '_u_large.', url)
        url = re.sub(r'_u_medium\.', '_u_large.', url)
        return url
