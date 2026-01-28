import sys
import os
import asyncio
from selenium.webdriver.common.by import By

# Add backend directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
sys.path.append(backend_dir)

from app.scrapers.listing_remax import RemaxListingScraper

async def test_filters():
    scraper = RemaxListingScraper({})
    driver = scraper._get_driver()
    
    base_url = "https://www.remax.com.ar/propiedades-en-venta-en-palermo"
    
    # IDs to test
    # 1, 2 are standard. PH might be 9, 10, 11?
    test_ids = [1, 2, 3, 4, 9, 10, 11]
    
    print("\n--- Testing Property Type IDs ---")
    
    try:
        for pid in test_ids:
            url = f"{base_url}?sort=-createdAt&in:propertyTypeId={pid}"
            print(f"\nTesting ID {pid}: {url}")
            driver.get(url)
            await asyncio.sleep(3)
            
            # Extract first few titles to guess type
            titles = []
            cards = driver.find_elements(By.CSS_SELECTOR, ".card__title, .card__description")
            for c in cards[:5]:
                titles.append(c.text)
                
            print(f"  Found {len(cards)} cards")
            if titles:
                print(f"  Sample Titles: {titles}")
            
            # Check for "Empty"
            body = driver.find_element(By.TAG_NAME, "body").text.lower()
            if "no encontramos" in body:
                print("  ⚠️  No results")

    finally:
        driver.quit()

if __name__ == "__main__":
    asyncio.run(test_filters())
