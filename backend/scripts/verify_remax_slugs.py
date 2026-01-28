import requests
import time

def check_url(slug, name):
    url = f"https://www.remax.com.ar/{slug}-en-venta-en-villa-crespo"
    print(f"Testing {name}: {url}")
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        resp = requests.get(url, headers=headers, allow_redirects=True)
        print(f"  Status: {resp.status_code}")
        print(f"  Final URL: {resp.url}")
        print(f"  Title: {resp.text.split('<title>')[1].split('</title>')[0] if '<title>' in resp.text else 'No Title'}")
        
        if "Venta y Alquiler de Propiedades | REMAX" in resp.text:
             print("  ⚠️  Redirected to Home/Generic Page")
        else:
             print("  ✅  Seems valid specific page")
             
    except Exception as e:
        print(f"  Error: {e}")
    print("-" * 30)

if __name__ == "__main__":
    
    locations = [
        "capital-federal",
        "ciudad-de-buenos-aires",
        "buenos-aires",
    ]
    
    property_types = [
        "propiedades",
        "departamentos",
    ]
    
    base_ops = ["en-venta-en"]
    
    print("--- Brute Forcing ReMax Slugs ---")
    
    for loc in locations:
        for pt in property_types:
            for op in base_ops:
                if op == "-":
                    slug = f"{pt}-{loc}"
                elif op == "en":
                    slug = f"{pt}-en-{loc}"
                else:
                    slug = f"{pt}-{op}-{loc}"
                
                url = f"https://www.remax.com.ar/{slug}"
            
            # Fast check with requests
            try:
                headers = {"User-Agent": "Mozilla/5.0 ..."}
                resp = requests.get(url, headers=headers, allow_redirects=True, timeout=5)
                
                is_valid = False
                title = "?"
                if resp.status_code == 200:
                    if "<title>" in resp.text:
                         title = resp.text.split('<title>')[1].split('</title>')[0]
                         if "Explorá" not in title and "Venta y Alquiler" not in title:
                             is_valid = True
                
                status_icon = "✅" if is_valid else "❌"
                print(f"{status_icon} {slug} -> {title}")
                
            except Exception as e:
                print(f"⚠️ Error {slug}: {e}")
            
            time.sleep(0.5)
