import sys
import os

# Add backend directory (parent of scripts) to path
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
sys.path.append(backend_dir)

from app.scrapers.listing_remax import RemaxListingScraper

def test_url_generation():
    print("Testing Remax URL Generation...")

    # Case 1: Standard Search (Apartment, Buy, Palermo)
    params1 = {
        "property_type": "departamento",
        "operation_type": "venta",
        "neighborhoods": ["Palermo"],
        "city": "Capital Federal"
    }
    scraper1 = RemaxListingScraper(params1)
    url1 = scraper1.build_search_url(page=1)
    print(f"\nCase 1 (Standard): {url1}")
    expected1 = "https://www.remax.com.ar/departamentos-en-venta-en-palermo?sort=-createdAt"
    if url1 == expected1:
        print("✅ Correct")
    else:
        print(f"❌ Incorrect. Expected: {expected1}")

    # Case 2: Pagination
    url2 = scraper1.build_search_url(page=3)
    print(f"\nCase 2 (Page 3): {url2}")
    if "page=2" in url2:
        print("✅ Correct (page=2 for page 3)")
    else:
        print("❌ Incorrect pagination")
        
    # Case 3: Missing Neighborhood, only City
    params3 = {
        "property_type": "casa",
        "operation_type": "alquiler",
        "city": "Cordoba"
    }
    scraper3 = RemaxListingScraper(params3)
    url3 = scraper3.build_search_url()
    print(f"\nCase 3 (City only): {url3}")
    # Expected: /casas-en-alquiler-en-cordoba
    if "/casas-en-alquiler-en-cordoba" in url3:
         print("✅ Correct")
    else:
         print("❌ Incorrect")

    # Case 4: Price Filter
    params4 = {
        "property_type": "departamento",
        "operation_type": "venta",
        "neighborhoods": ["Palermo"],
        "min_price": 100000,
        "max_price": 200000,
        "currency": "USD"
    }
    scraper4 = RemaxListingScraper(params4)
    url4 = scraper4.build_search_url()
    print(f"\nCase 4 (Price Filter): {url4}")
    if "pricein=" in url4:
        print("✅ Correct (Found pricein)")
    else:
        print("❌ Incorrect")

if __name__ == "__main__":
    test_url_generation()
