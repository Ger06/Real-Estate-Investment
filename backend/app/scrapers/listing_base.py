"""
Base Listing Scraper Class
For scraping search result pages (listings) to extract property URLs
"""
import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from bs4 import BeautifulSoup
from .http_client import fetch_with_browser_fingerprint

logger = logging.getLogger(__name__)

# Default user agent
DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


class BaseListingScraper(ABC):
    """
    Base class for listing page scrapers (search results).

    Unlike BaseScraper which scrapes individual property pages,
    this scrapes search result pages to extract multiple property URLs.
    """

    # Subclasses should override these
    PORTAL_NAME = "base"
    BASE_URL = ""
    MAX_PAGES = 10  # Maximum pages to scrape to prevent infinite loops
    DELAY_BETWEEN_PAGES = 2.0  # Seconds between page requests

    def __init__(
        self,
        search_params: Dict[str, Any],
        user_agent: Optional[str] = None
    ):
        """
        Initialize listing scraper with search parameters.

        Args:
            search_params: Dictionary with search filters:
                - property_type: str (casa, departamento, etc.)
                - operation_type: str (venta, alquiler)
                - city: str
                - neighborhoods: List[str]
                - province: str
                - min_price: float
                - max_price: float
                - currency: str (USD, ARS)
                - min_area: float
                - max_area: float
                - min_bedrooms: int
                - max_bedrooms: int
                - min_bathrooms: int
            user_agent: Optional custom user agent
        """
        self.search_params = search_params
        self.user_agent = user_agent or DEFAULT_USER_AGENT
        self.soup: Optional[BeautifulSoup] = None

    @abstractmethod
    def build_search_url(self, page: int = 1) -> str:
        """
        Build portal-specific search URL from parameters.

        Args:
            page: Page number (1-indexed)

        Returns:
            Complete search URL with filters applied
        """
        pass

    @abstractmethod
    def extract_property_cards(self) -> List[Dict[str, Any]]:
        """
        Extract property listings from current page.

        Returns:
            List of dicts with:
            {
                'source_url': 'https://...',
                'source_id': '12345',
                'title': 'Departamento en venta...',
                'price': 250000.0,
                'currency': 'USD',
                'thumbnail_url': 'https://...',
                'location_preview': 'Palermo, CABA',
            }
        """
        pass

    @abstractmethod
    def has_next_page(self) -> bool:
        """
        Check if there's a next page of results.

        Returns:
            True if there are more pages
        """
        pass

    async def fetch_page(self, url: str) -> str:
        """
        Fetch the HTML content of a page.

        Uses curl_cffi with Chrome TLS fingerprint (bypasses Cloudflare),
        falling back to httpx.

        Args:
            url: URL to fetch

        Returns:
            HTML content as string

        Raises:
            Exception: If all fetch methods fail
        """
        return await fetch_with_browser_fingerprint(url, user_agent=self.user_agent)

    def parse_html(self, html: str) -> None:
        """
        Parse HTML content with BeautifulSoup.

        Args:
            html: HTML content string
        """
        self.soup = BeautifulSoup(html, 'html.parser', from_encoding='utf-8')

    async def scrape_page(self, page: int = 1) -> List[Dict[str, Any]]:
        """
        Scrape a single page of listings.

        Args:
            page: Page number (1-indexed)

        Returns:
            List of property card data
        """
        url = self.build_search_url(page)
        print(f"[DEBUG] [{self.PORTAL_NAME}] Scraping page {page}: {url}")

        try:
            html = await self.fetch_page(url)
            print(f"[DEBUG] [{self.PORTAL_NAME}] Fetched HTML, length: {len(html)}")
            self.parse_html(html)
            cards = self.extract_property_cards()
            print(f"[DEBUG] [{self.PORTAL_NAME}] Found {len(cards)} properties on page {page}")
            return cards
        except Exception as e:
            print(f"[DEBUG] [{self.PORTAL_NAME}] Error scraping page {page}: {str(e)}")
            raise

    async def scrape_all_pages(self, max_properties: int = 100) -> List[Dict[str, Any]]:
        """
        Scrape all pages of search results.

        Args:
            max_properties: Maximum number of properties to extract

        Returns:
            List of all property card data dictionaries
        """
        all_properties: List[Dict[str, Any]] = []
        current_page = 1

        while len(all_properties) < max_properties and current_page <= self.MAX_PAGES:
            try:
                # Scrape current page
                cards = await self.scrape_page(current_page)

                if not cards:
                    logger.info(f"[{self.PORTAL_NAME}] No more properties found, stopping")
                    break

                all_properties.extend(cards)

                # Check if we should continue
                if not self.has_next_page():
                    logger.info(f"[{self.PORTAL_NAME}] No next page, stopping")
                    break

                # Rate limiting delay between pages
                await asyncio.sleep(self.DELAY_BETWEEN_PAGES)
                current_page += 1

            except Exception as e:
                logger.error(f"[{self.PORTAL_NAME}] Error on page {current_page}, stopping: {str(e)}")
                break

        # Trim to max_properties
        result = all_properties[:max_properties]
        logger.info(f"[{self.PORTAL_NAME}] Total properties scraped: {len(result)}")
        return result

    # Helper methods for subclasses

    def extract_text(self, selector: str, default: str = "") -> str:
        """Helper to extract text from CSS selector."""
        if not self.soup:
            return default
        element = self.soup.select_one(selector)
        return element.get_text(strip=True) if element else default

    def extract_texts(self, selector: str) -> List[str]:
        """Helper to extract multiple texts from CSS selector."""
        if not self.soup:
            return []
        elements = self.soup.select(selector)
        return [elem.get_text(strip=True) for elem in elements]

    def extract_attr(self, selector: str, attr: str, default: str = "") -> str:
        """Helper to extract attribute from CSS selector."""
        if not self.soup:
            return default
        element = self.soup.select_one(selector)
        return element.get(attr, default) if element else default

    def extract_all_attrs(self, selector: str, attr: str) -> List[str]:
        """Helper to extract attribute from all matching elements."""
        if not self.soup:
            return []
        elements = self.soup.select(selector)
        return [elem.get(attr, "") for elem in elements if elem.get(attr)]

    def clean_price(self, price_text: str) -> tuple[Optional[float], Optional[str]]:
        """
        Parse price text and extract amount and currency.

        Args:
            price_text: Price string like "USD 250.000" or "$ 250.000"

        Returns:
            Tuple of (price_amount, currency) or (None, None) if parsing fails
        """
        import re

        if not price_text:
            return None, None

        # Remove common separators and whitespace
        price_text = price_text.strip().upper()

        # Detect currency
        currency = None
        if "USD" in price_text or "U$S" in price_text or "US$" in price_text:
            currency = "USD"
        elif "ARS" in price_text or "AR$" in price_text or "$" in price_text:
            currency = "ARS"

        # Extract numbers
        numbers = re.findall(r'[\d.,]+', price_text)
        if not numbers:
            return None, currency

        # Take the first number and clean it
        price_str = numbers[0]
        # Handle different number formats (1.000.000 or 1,000,000)
        if price_str.count('.') > 1:
            # Format: 1.000.000 (periods as thousands separator)
            price_str = price_str.replace('.', '')
        elif price_str.count(',') > 1:
            # Format: 1,000,000 (commas as thousands separator)
            price_str = price_str.replace(',', '')
        elif ',' in price_str and '.' in price_str:
            # Format: 1,000.00 or 1.000,00
            if price_str.index(',') < price_str.index('.'):
                # 1,000.00 format
                price_str = price_str.replace(',', '')
            else:
                # 1.000,00 format
                price_str = price_str.replace('.', '').replace(',', '.')
        elif ',' in price_str:
            # Could be 1,000 or 1,00 - assume thousands separator
            price_str = price_str.replace(',', '')
        elif '.' in price_str:
            # Could be 1.000 or 1.00 - check position
            parts = price_str.split('.')
            if len(parts[-1]) == 2:
                # Decimal: 1.00
                pass
            else:
                # Thousands: 1.000
                price_str = price_str.replace('.', '')

        try:
            return float(price_str), currency
        except ValueError:
            return None, currency
