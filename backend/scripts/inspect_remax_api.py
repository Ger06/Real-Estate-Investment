import requests
import json

def test_api():
    base_url = "https://api-ar.redremax.com/remaxweb-ar/api/search/findAll/Villa%20Crespo?level=1"
    print(f"Fetching {base_url}...")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Origin": "https://www.remax.com.ar",
        "Referer": "https://www.remax.com.ar/",
        "Accept": "application/json, text/plain, */*"
    }
    
    try:
        resp = requests.get(base_url, headers=headers)
        print(f"Status: {resp.status_code}")
        
        if resp.status_code == 200:
            data = resp.json()
            print("Response JSON:")
            print(json.dumps(data, indent=2))
            
            # Look for IDs
            # Typical structure might be list of items
            if isinstance(data, list):
                for item in data:
                    print(f"Found Item: {item.get('name', '?')} - ID: {item.get('id', '?')} - Slug: {item.get('slug', '?')}")
        else:
            print(f"Error Body: {resp.text}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_api()
