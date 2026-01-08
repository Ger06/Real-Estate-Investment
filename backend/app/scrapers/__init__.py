"""
Web Scrapers for Real Estate Portals
"""
from .base import BaseScraper
from .argenprop import ArgenpropScraper
from .zonaprop import ZonapropScraper
from .remax import RemaxScraper
from .mercadolibre import MercadoLibreScraper

__all__ = ["BaseScraper", "ArgenpropScraper", "ZonapropScraper", "RemaxScraper", "MercadoLibreScraper"]
