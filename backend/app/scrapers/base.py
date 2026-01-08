"""
Base Scraper Class
All scrapers should inherit from this class
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from urllib.parse import urlparse
import httpx
from bs4 import BeautifulSoup


class BaseScraper(ABC):
    """Base class for all property scrapers"""

    def __init__(self, url: str, user_agent: Optional[str] = None):
        """
        Initialize scraper

        Args:
            url: Property URL to scrape
            user_agent: Optional custom user agent
        """
        self.url = url
        self.user_agent = user_agent or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        self.soup: Optional[BeautifulSoup] = None

    @abstractmethod
    def validate_url(self) -> bool:
        """
        Validate if URL belongs to this portal

        Returns:
            bool: True if URL is valid for this scraper
        """
        pass

    @abstractmethod
    def extract_data(self) -> Dict[str, Any]:
        """
        Extract property data from the page

        Returns:
            Dict with property data
        """
        pass

    async def fetch_page(self) -> str:
        """
        Fetch the HTML content of the page with explicit UTF-8 encoding

        Returns:
            HTML content as string
        """
        async with httpx.AsyncClient() as client:
            headers = {
                "User-Agent": self.user_agent,
                "Accept-Charset": "utf-8",
            }
            response = await client.get(self.url, headers=headers, timeout=30.0)
            response.raise_for_status()

            # Explicit UTF-8 decoding with Latin-1 fallback
            try:
                return response.content.decode('utf-8')
            except UnicodeDecodeError:
                # Fallback for legacy Argentine sites
                return response.content.decode('latin-1')

    def parse_html(self, html: str) -> None:
        """
        Parse HTML content with BeautifulSoup and explicit UTF-8 encoding

        Args:
            html: HTML content string
        """
        self.soup = BeautifulSoup(html, 'html.parser', from_encoding='utf-8')

    async def scrape(self) -> Dict[str, Any]:
        """
        Main scraping method

        Returns:
            Dict with extracted property data

        Raises:
            ValueError: If URL is not valid for this scraper
            Exception: If scraping fails
        """
        if not self.validate_url():
            raise ValueError(f"URL {self.url} is not valid for {self.__class__.__name__}")

        # Fetch and parse page
        html = await self.fetch_page()
        self.parse_html(html)

        # Extract data
        data = self.extract_data()

        # Add source URL
        data['source_url'] = self.url

        return data

    def extract_text(self, selector: str, default: str = "") -> str:
        """
        Helper to extract text from CSS selector

        Args:
            selector: CSS selector
            default: Default value if not found

        Returns:
            Extracted text or default
        """
        if not self.soup:
            return default

        element = self.soup.select_one(selector)
        return element.get_text(strip=True) if element else default

    def extract_texts(self, selector: str) -> List[str]:
        """
        Helper to extract multiple texts from CSS selector

        Args:
            selector: CSS selector

        Returns:
            List of extracted texts
        """
        if not self.soup:
            return []

        elements = self.soup.select(selector)
        return [elem.get_text(strip=True) for elem in elements]

    def extract_attr(self, selector: str, attr: str, default: str = "") -> str:
        """
        Helper to extract attribute from CSS selector

        Args:
            selector: CSS selector
            attr: Attribute name
            default: Default value if not found

        Returns:
            Extracted attribute or default
        """
        if not self.soup:
            return default

        element = self.soup.select_one(selector)
        return element.get(attr, default) if element else default
