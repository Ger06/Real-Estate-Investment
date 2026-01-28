import requests
import time

def check_keyword_filtering():
    base_url = "https://www.remax.com.ar/departamentos-en-venta-en-ciudad-de-buenos-aires"
    
    # Potential query params for text search
    params_to_test = [
        "keywords=Villa%20Crespo",
        "search=Villa%20Crespo",
        "q=Villa%20Crespo",
        "address=Villa%20Crespo",
        "location=Villa%20Crespo",
        "query=Villa%20Crespo", 
        "filter=Villa%20Crespo"
    ]
    
    print(f"Base URL: {base_url}")
    print("Testing if query params affect the page... (checking title/content)")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    # Reference Request (No params)
    print("\nReference Request (No params)...")
    try:
        resp = requests.get(base_url, headers=headers)
        ref_len = len(resp.text)
        print(f"  Length: {ref_len}")
    except Exception as e:
        print(f"  Error: {e}")
        return

    for p in params_to_test:
        url = f"{base_url}?{p}"
        print(f"\nTesting: {url}")
        try:
            resp = requests.get(url, headers=headers)
            print(f"  Status: {resp.status_code}")
            print(f"  Length: {len(resp.text)}")
            
            diff = abs(len(resp.text) - ref_len)
            print(f"  Diff from Ref: {diff} bytes")
            
            if diff > 1000:
                print("  ✅ SIGNIFICANT difference! (Might be filtering)")
                # Check for "Villa Crespo" in text count
                count = resp.text.lower().count("villa crespo")
                print(f"  'Villa Crespo' count: {count}")
            else:
                print("  ❌ No significant difference.")
                 
        except Exception as e:
            print(f"  Error: {e}")
        time.sleep(1)

if __name__ == "__main__":
    check_keyword_filtering()
