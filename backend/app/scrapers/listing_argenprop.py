"""
Argenprop Listing Scraper
Scrapes search result pages from www.argenprop.com.ar to extract property URLs
"""
import re
import logging
from typing import Dict, Any, List, Optional
from urllib.parse import urljoin, quote
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
        """Parse a single property card element"""
        data = {
            'source': 'argenprop',
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

        # Extract title
        title_selectors = [
            '.card__title',
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

        # Extract price
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

        # Extract thumbnail
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

        # Extract location preview
        location_selectors = [
            '.card__location',
            '.location',
            '[class*="location"]',
            '[class*="address"]',
            '[class*="zona"]',
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

        Looks for pagination elements or "siguiente" links.
        """
        if not self.soup:
            return False

        # Look for pagination
        pagination_selectors = [
            'a[href*="pagina-"]',
            '.pagination a.next',
            '.pagination .siguiente',
            'a[rel="next"]',
            'a:contains("Siguiente")',
            'a:contains(">")',
        ]

        for selector in pagination_selectors:
            try:
                next_link = self.soup.select_one(selector)
                if next_link:
                    return True
            except Exception:
                continue

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
