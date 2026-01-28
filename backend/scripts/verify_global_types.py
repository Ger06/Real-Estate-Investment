import requests
import time

def verify_global_types():
    base_prefix = "https://www.remax.com.ar/"
    slugs = [
        "casas-en-venta",         # Houses
        "departamentos-en-venta", # PHs map to this?
        "ph-en-venta",            # Does this exist globally?
        "ph-venta",
        "propiedades-en-venta",   # Catch all?
    ]
    
    headers = {
        "User-Agent": "Mozilla/5.0"
    }
    
    print("--- Testing Global Type Slugs ---")
    for s in slugs:
        url = f"{base_prefix}{s}"
        print(f"Testing: {url}")
        try:
            resp = requests.get(url, headers=headers, allow_redirects=True)
            title = "No Title"
            if "<title>" in resp.text:
                title = resp.text.split('<title>')[1].split('</title>')[0]
            
            if "Explorá" in title or "Venta y Alquiler" in title:
                 print(f"  ❌ Redirect/Home: {title}")
            else:
                 print(f"  ✅ Specific Title: {title}")
                 
        except Exception as e:
            print(f"  Error: {e}")
        time.sleep(1)

if __name__ == "__main__":
    verify_global_types()
