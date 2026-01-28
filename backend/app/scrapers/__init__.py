"""
Web Scrapers for Real Estate Portals
"""
# Property scrapers (single property page)
from .base import BaseScraper
from .argenprop import ArgenpropScraper
from .zonaprop import ZonapropScraper
from .remax import RemaxScraper
from .mercadolibre import MercadoLibreScraper

# Listing scrapers (search results / multiple properties)
from .listing_base import BaseListingScraper
from .listing_argenprop import ArgenpropListingScraper
from .listing_zonaprop import ZonapropListingScraper
from .listing_remax import RemaxListingScraper
from .listing_mercadolibre import MercadoLibreListingScraper

__all__ = [
    # Property scrapers
    "BaseScraper",
    "ArgenpropScraper",
    "ZonapropScraper",
    "RemaxScraper",
    "MercadoLibreScraper",
    # Listing scrapers
    "BaseListingScraper",
    "ArgenpropListingScraper",
    "ZonapropListingScraper",
    "RemaxListingScraper",
    "MercadoLibreListingScraper",
]
