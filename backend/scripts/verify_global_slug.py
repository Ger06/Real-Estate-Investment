import requests
import time

def verify_global_slug():
    # Candidates for global search
    slugs = [
        "departamentos-en-venta",
        "propiedades-en-venta",
        "venta-de-departamentos",
        "comprar-propiedades",
        "listings/buy", # English?
    ]
    
    base_url = "https://www.remax.com.ar/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    valid_url = None
    
    print("--- Finding Valid Global URL ---")
    for s in slugs:
        url = f"{base_url}{s}"
        print(f"Testing: {url}")
        try:
            resp = requests.get(url, headers=headers, allow_redirects=True)
             # check title
            title = "No Title"
            if "<title>" in resp.text:
                title = resp.text.split('<title>')[1].split('</title>')[0]
            
            if "Explorá" in title or "Venta y Alquiler" in title:
                 # Usually home page has this title
                 if s == "comprar-propiedades":
                     # This might be valid?
                     pass
                 print(f"  ❌ Redirect/Home: {title}")
            else:
                 print(f"  ✅ Specific Title: {title}")
                 valid_url = url
                 break
        except:
            pass
    
    if valid_url:
        print(f"\n--- Testing Keywords on {valid_url} ---")
        # Test keyword
        kw_url = f"{valid_url}?keywords=Villa%20Crespo"
        print(f"Fetching {kw_url}")
        r = requests.get(kw_url, headers=headers)
        
        lower_text = r.text.lower()
        count = lower_text.count("villa crespo")
        print(f"  'Villa Crespo' count: {count}")
        
        # Compare to control (no keyword)
        r_ref = requests.get(valid_url, headers=headers)
        print(f"  Ref length: {len(r_ref.text)} vs Keyword length: {len(r.text)}")

if __name__ == "__main__":
    verify_global_slug()
