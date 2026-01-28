import requests
import gzip
import io

def check_sitemap_control():
    # Only checking sitemap0 as it likely has the listings/categories
    url = "https://www.remax.com.ar/sitemap-pages.xml" # Try pages first? or listings?
    # Original script found 6 submaps. usually sitemap-listings.xml or sitemap0.xml
    # Let's try sitemap0.xml again
    
    urls = [
        "https://www.remax.com.ar/sitemap0.xml",
        "https://www.remax.com.ar/sitemap-pages.xml"
    ]
    
    headers = {"User-Agent": "Mozilla/5.0"}
    
    for u in urls:
        print(f"Checking {u}...")
        try:
            r = requests.get(u, headers=headers)
            content = r.content
            # Decode
            text = ""
            try:
                # Gzip check logic needed? requests auto-decodes gzip usually if headers say so
                # But sitemaps are often .xml.gz
                if u.endswith('.gz'):
                     text = gzip.decompress(content).decode('utf-8')
                else:
                     text = content.decode('utf-8')
            except:
                 text = content.decode('utf-8', errors='ignore')
            
            # Search
            keywords = ["palermo", "villa-crespo", "capital-federal", "caba", "almagro"]
            for k in keywords:
                if k in text:
                    print(f"  FOUND '{k}' in {u}:")
                    # Print context
                    idx = text.find(k)
                    start = max(0, idx - 100)
                    end = min(len(text), idx + 100)
                    print(f"    ...{text[start:end]}...")
                else:
                    print(f"  '{k}' NOT found in {u}")
                    
        except Exception as e:
            print(f"Error {e}")

if __name__ == "__main__":
    check_sitemap_control()
