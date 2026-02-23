"""
Local Scraper — runs on your PC (residential IP) and uploads results to the Render API.

Usage:
    cd backend
    python -m scripts.local_scraper --api-url https://mi-app.onrender.com

The script:
1. Fetches active saved searches from the API
2. For each search, scrapes listing pages locally (bypasses Cloudflare)
3. POSTs the scraped cards to the API's /import-cards endpoint

Dependencies: curl_cffi, beautifulsoup4, lxml, httpx (all in requirements.txt)
"""
import argparse
import asyncio
import logging
import sys
from typing import Dict, Any, List, Optional

import httpx

# Import listing scrapers from the project
from app.scrapers.listing_zonaprop import ZonapropListingScraper
from app.scrapers.listing_argenprop import ArgenpropListingScraper
from app.scrapers.listing_remax import RemaxListingScraper
from app.scrapers.listing_mercadolibre import MercadoLibreListingScraper

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

LISTING_SCRAPERS = {
    "argenprop": ArgenpropListingScraper,
    "zonaprop": ZonapropListingScraper,
    "remax": RemaxListingScraper,
    "mercadolibre": MercadoLibreListingScraper,
}


def build_search_params(search: Dict[str, Any]) -> Dict[str, Any]:
    """Convert API saved-search response to scraper params dict."""
    params: Dict[str, Any] = {}

    if search.get("operation_type"):
        params["operation_type"] = search["operation_type"]
    if search.get("property_type"):
        params["property_type"] = search["property_type"]
    if search.get("city"):
        params["city"] = search["city"]
    if search.get("province"):
        params["province"] = search["province"]
    if search.get("neighborhoods"):
        params["neighborhoods"] = search["neighborhoods"]
    if search.get("min_price"):
        params["min_price"] = float(search["min_price"])
    if search.get("max_price"):
        params["max_price"] = float(search["max_price"])
    if search.get("currency"):
        params["currency"] = search["currency"]
    if search.get("min_area"):
        params["min_area"] = float(search["min_area"])
    if search.get("max_area"):
        params["max_area"] = float(search["max_area"])
    if search.get("min_bedrooms"):
        params["min_bedrooms"] = search["min_bedrooms"]
    if search.get("max_bedrooms"):
        params["max_bedrooms"] = search["max_bedrooms"]
    if search.get("min_bathrooms"):
        params["min_bathrooms"] = search["min_bathrooms"]

    return params


async def scrape_portal(
    portal: str,
    search_params: Dict[str, Any],
    max_properties: int,
) -> List[Dict[str, Any]]:
    """Run listing scraper for a single portal and return cards."""
    if portal not in LISTING_SCRAPERS:
        logger.warning(f"  No scraper for portal: {portal}")
        return []

    # Remax requires DB cache for location IDs — skip in local mode
    if portal == "remax":
        logger.warning(f"  [{portal}] Saltando: requiere cache de DB para IDs de ubicación")
        return []

    scraper_class = LISTING_SCRAPERS[portal]
    scraper = scraper_class(search_params)

    url = scraper.build_search_url(page=1)
    logger.info(f"  [{portal}] URL: {url}")

    try:
        cards = await scraper.scrape_all_pages(max_properties=max_properties)
        logger.info(f"  [{portal}] Found {len(cards)} cards")
        return cards
    except Exception as e:
        logger.error(f"  [{portal}] Scraping error: {e}")
        return []


async def run(api_url: str, max_properties: int, token: Optional[str]):
    """Main scraper loop."""
    api_url = api_url.rstrip("/")
    base = f"{api_url}/api/v1"

    headers: Dict[str, str] = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
        # 1. Fetch active saved searches
        logger.info(f"Fetching active saved searches from {base}/saved-searches/ ...")
        resp = await client.get(
            f"{base}/saved-searches/",
            params={"active_only": "true", "limit": 100},
        )
        resp.raise_for_status()
        data = resp.json()
        searches = data.get("items", [])
        logger.info(f"Found {len(searches)} active saved search(es)")

        if not searches:
            logger.info("Nothing to do.")
            return

        # 2. For each search, scrape and upload
        for search in searches:
            search_id = search["id"]
            search_name = search["name"]
            portals = search.get("portals", [])

            logger.info(f"\n{'='*60}")
            logger.info(f"Search: {search_name} (portals: {', '.join(portals)})")
            logger.info(f"{'='*60}")

            search_params = build_search_params(search)
            all_cards: List[Dict[str, Any]] = []

            for portal in portals:
                portal_lower = portal.lower()
                cards = await scrape_portal(portal_lower, search_params, max_properties)
                all_cards.extend(cards)

            if not all_cards:
                logger.info(f"  No cards found for '{search_name}', skipping upload.")
                continue

            # 3. POST cards to import endpoint
            logger.info(f"  Uploading {len(all_cards)} cards to API ...")
            import_resp = await client.post(
                f"{base}/saved-searches/{search_id}/import-cards",
                json={"cards": all_cards},
                timeout=120.0,
            )
            import_resp.raise_for_status()
            result = import_resp.json()

            logger.info(
                f"  Result: "
                f"total={result.get('total_found', 0)}, "
                f"new={result.get('new_properties', 0)}, "
                f"dupes={result.get('duplicates', 0)}, "
                f"scraped={result.get('scraped', 0)}, "
                f"errors={len(result.get('errors', []))}"
            )

            errors = result.get("errors", [])
            if errors:
                for err in errors[:5]:
                    logger.warning(f"    Error: {err}")

    logger.info("\nDone.")


def main():
    parser = argparse.ArgumentParser(
        description="Local scraper: scrape from residential IP and upload to Render API",
    )
    parser.add_argument(
        "--api-url",
        required=True,
        help="Base URL of the Render API (e.g. https://mi-app.onrender.com)",
    )
    parser.add_argument(
        "--max-properties",
        type=int,
        default=100,
        help="Max properties to scrape per portal (default: 100)",
    )
    parser.add_argument(
        "--token",
        default=None,
        help="Optional Bearer token for authenticated API access",
    )
    args = parser.parse_args()

    asyncio.run(run(api_url=args.api_url, max_properties=args.max_properties, token=args.token))


if __name__ == "__main__":
    main()
