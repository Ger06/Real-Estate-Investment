import requests
import time

def check_url(url, name):
    print(f"Testing {name}: {url}")
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        resp = requests.get(url, headers=headers, allow_redirects=True)
        print(f"  Status: {resp.status_code}")
        print(f"  Final URL: {resp.url}")
        
        title = resp.text.split('<title>')[1].split('</title>')[0] if '<title>' in resp.text else 'No Title'
        print(f"  Title: {title}")
        
        if "Explorá" in title or "Venta y Alquiler" in title:
             print("  ⚠️  Redirected to Home/Generic Page")
        else:
             print("  ✅  Seems valid specific page")

    except Exception as e:
        print(f"  Error: {e}")
    print("-" * 30)

if __name__ == "__main__":
    urls = [
        "https://www.remax.com.ar/listings/buy?address=Villa%20Crespo&sort=-createdAt",
        "https://www.remax.com.ar/listings/buy?place=Villa%20Crespo&sort=-createdAt",
        "https://www.remax.com.ar/listings/buy?location=Villa%20Crespo&sort=-createdAt",
        "https://www.remax.com.ar/en-venta-en-villa-crespo", # Another variation?
    ]
    for url in urls:
        check_url(url, "Legacy Pattern")
        time.sleep(1)
