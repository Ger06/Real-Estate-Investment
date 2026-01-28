import sys
import os
import asyncio
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Add backend directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
sys.path.append(backend_dir)

from app.scrapers.listing_remax import RemaxListingScraper

async def test_slugs():
    scraper = RemaxListingScraper({})
    driver = scraper._get_driver()
    
    test_urls = [
        "https://www.remax.com.ar/departamentos-en-venta-en-palermo",       # Control (SSR validated)
        "https://www.remax.com.ar/departamentos-en-venta-en-villa-del-parque", # Control (Worked in repro)
        "https://www.remax.com.ar/ph-en-venta-en-palermo",                  # Test PH + Top Zone
        "https://www.remax.com.ar/ph-en-venta-en-villa-del-parque",         # Test PH + Working Zone
        "https://www.remax.com.ar/ph-en-venta-en-villa-crespo",              # Target
        "https://www.remax.com.ar/casas-en-venta-en-villa-crespo",           # Test Zone validity
    ]

    print("\n--- Starting Selenium Slug Verification ---")
    
    try:
        for url in test_urls:
            print(f"\nTesting: {url}")
            driver.get(url)
            
            # Wait a bit for title update or redirect
            await asyncio.sleep(3)
            
            title = driver.title
            print(f"  Title: {title}")
            
            # Check for 0 results text
            body_text = driver.find_element(By.TAG_NAME, "body").text.lower()
            if "no encontramos" in body_text or "0 propiedades" in body_text:
                print("  ⚠️  Page says 'No results'")
            else:
                # Count cards
                cards = driver.find_elements(By.CSS_SELECTOR, ".card-remax, .listing-card")
                if not cards:
                     # fallback
                     divs = driver.find_elements(By.CSS_SELECTOR, "div")
                     cards = [d for d in divs if 'card' in d.get_attribute("class") and 'image' not in d.get_attribute("class")]
                
                print(f"  Found {len(cards)} potential cards")
            
            if "Explorá propiedades" in title or "Venta y Alquiler" in title:
                print("  ⚠️  Generic Title (Soft 404?)")
            else:
                 print("  ✅  Specific Page")

    finally:
        driver.quit()

if __name__ == "__main__":
    asyncio.run(test_slugs())
