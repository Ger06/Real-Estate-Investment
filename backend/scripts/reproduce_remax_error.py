import sys
import os
import asyncio

# Add backend directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
sys.path.append(backend_dir)

from app.scrapers.listing_remax import RemaxListingScraper

async def reproduce_issue():
    print("Reproducing Remax Neighborhood Issue...")

    # Parameters from user report
    params = {
        "name": "Test Remax Refinado",
        "portals": ["remax"],
        "operation_type": "VENTA",
        "city": "capital federal",
        "property_type": "DEPARTAMENTO",
        "auto_scrape": True,
        "neighborhoods": ["villa del parque"],
        "min_price": "200000",
        "max_price": "300000",
    }

    scraper = RemaxListingScraper(params)
    
    # 1. Check URL Generation
    url = scraper.build_search_url(page=1)
    print(f"Generated URL: {url}")
    
    # Verify expected URL structure
    expected_slug = "villa-del-parque"
    if expected_slug in url:
        print(f"✅ URL contains correct slug: {expected_slug}")
    else:
        print(f"❌ URL missing slug: {expected_slug}")

    # 2. Try full scrape logic (which uses Selenium)
    print("\nAttempting full scrape (1 page)...")
    try:
        # Override MAX_PAGES to 1 for test
        scraper.MAX_PAGES = 1
        listings = await scraper.scrape_all_pages()
        print(f"✅ Scrape successful. Found {len(listings)} listings.")
        for i, listing in enumerate(listings[:5]):
            print(f"Listing {i+1}:")
            print(f"  URL: {listing.get('source_url')}")
            print(f"  Title: {listing.get('title')}")
            print(f"  Location: {listing.get('location_preview')}")
            print(f"  Price: {listing.get('price')} {listing.get('currency')}")
    except Exception as e:
        print(f"❌ Scrape FAILED with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(reproduce_issue())
