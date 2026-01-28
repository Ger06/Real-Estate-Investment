import requests
import json

def probe_listing_api():
    base_url = "https://api-ar.redremax.com/remaxweb-ar/api"
    
    endpoints = [
        "/listing/search",
        "/listings/search",
        "/property/search",
        "/properties/search",
        "/search/listings",
        "/search/properties",
        "/listing/findAll",
        "/listings"
    ]
    
    # Villa Crespo City ID = 25042 (Found earlier)
    # Operation Venta = 1
    # Property Depto = 1,2
    
    params_variations = [
        {"in:cityId": 25042, "page": 0, "pageSize": 10},
        {"cityId": 25042, "page": 0, "pageSize": 10},
        {"locationId": 25042},
        {"in:operationId": 1},
    ]
    
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Origin": "https://www.remax.com.ar",
        "Referer": "https://www.remax.com.ar/"
    }
    
    print("--- Probing Listing API ---")
    
    for ep in endpoints:
        url = f"{base_url}{ep}"
        print(f"Testing {url}")
        
        for params in params_variations:
            try:
                resp = requests.get(url, params=params, headers=headers)
                print(f"  Params: {params} -> Status: {resp.status_code}")
                if resp.status_code == 200:
                    try:
                        data = resp.json()
                        # Check if it looks like a listing response
                        is_valid = False
                        if isinstance(data, dict):
                            if 'data' in data and isinstance(data['data'], list) and len(data['data']) > 0:
                                is_valid = True
                            elif 'content' in data:
                                is_valid = True
                            elif 'total' in data and data['total'] > 0:
                                is_valid = True
                                
                        if is_valid:
                            print("  ✅ SUCCESS! Found listings endpoint.")
                            print(json.dumps(data, indent=2)[:500])
                            return # Stop on first success
                    except:
                        pass
            except Exception as e:
                print(f"  Error: {e}")

if __name__ == "__main__":
    probe_listing_api()
