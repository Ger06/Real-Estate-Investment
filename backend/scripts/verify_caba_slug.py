import requests
import time

def verify_caba_slugs():
    slugs = [
        "capital-federal",
        "caba",
        "ciudad-de-buenos-aires",
        "buenos-aires",
        "capital",
        "ciudad-autonoma-de-buenos-aires",
        "bs-as",
        "almagro", # Control
    ]
    
    base_prefix = "https://www.remax.com.ar/departamentos-en-venta-en-"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    print("--- Testing CABA Slugs ---")
    for s in slugs:
        url = f"{base_prefix}{s}"
        print(f"Testing: {url}")
        try:
            resp = requests.get(url, headers=headers, allow_redirects=True)
            print(f"  Status: {resp.status_code}")
            print(f"  Final URL: {resp.url}")
            
            title = "No Title"
            if "<title>" in resp.text:
                title = resp.text.split('<title>')[1].split('</title>')[0]
            print(f"  Title: {title}")
            
            if "Explorá" in title or "Venta y Alquiler" in title:
                 print("  ❌ Generic/Home Page")
            else:
                 print("  ✅ VALID PAGE (Specific Title)")
                 
        except Exception as e:
            print(f"  Error: {e}")
        
        print("-" * 20)
        time.sleep(1)

if __name__ == "__main__":
    verify_caba_slugs()
