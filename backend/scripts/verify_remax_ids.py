import requests
import json
import time

def test_ids_and_slugs():
    search_api = "https://api-ar.redremax.com/remaxweb-ar/api/search/findAll"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Origin": "https://www.remax.com.ar",
        "Referer": "https://www.remax.com.ar/",
        "Accept": "application/json, text/plain, */*"
    }
    
    # 1. Check Palermo (Control)
    print("Fetching Palermo data...")
    try:
        resp = requests.get(f"{search_api}/Palermo?level=1", headers=headers)
        data = resp.json()
        print(json.dumps(data.get('data', {}).get('geoSearch', [])[:1], indent=2))
    except Exception as e:
        print(f"Error fetching palermo: {e}")

    # 2. Test URL construction with IDs (Villa Crespo)
    # cityId: 25042
    # id: 6108850 (This seems to be a global ID?)
    
    base_url = "https://www.remax.com.ar/listings/buy"
    params = [
        "in:cityId=25042",
        "in:locationId=25042",
        "in:cityId=6108850", 
        "cityId=25042",
        "location=villa-crespo-capital-federal"
    ]
    
    print("\nTesting ID-based URLs for Villa Crespo...")
    for p in params:
        url = f"{base_url}?page=0&pageSize=24&sort=-createdAt&{p}"
        print(f"Testing: {url}")
        try:
            r = requests.get(url, headers=headers)
            title = r.text.split('<title>')[1].split('</title>')[0] if '<title>' in r.text else 'No Title'
            
            # Check length/redirect
            # remax redirects to home if invalid params sometimes
            if "Explorá" in title or "Venta y Alquiler" in title:
                print(f"  ❌ Generic Title: {title}")
            else:
                 print(f"  ✅ Specific Title: {title}")
                 
        except Exception as e:
            print(f"Error: {e}")
        time.sleep(1)

if __name__ == "__main__":
    test_ids_and_slugs()
