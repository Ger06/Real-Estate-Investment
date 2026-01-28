import requests
import xml.etree.ElementTree as ET
import gzip
import io

def check_sitemap():
    base_url = "https://www.remax.com.ar/sitemap.xml"
    print(f"Fetching {base_url}...")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        resp = requests.get(base_url, headers=headers)
        if resp.status_code != 200:
            print(f"Failed to fetch sitemap: {resp.status_code}")
            return

        # Parse XML
        # Real sitemaps often have sub-sitemaps
        root = ET.fromstring(resp.content)
        
        # Namespaces are annoying in XML, simple hack or handle them
        # Usually sitemapindex -> sitemap -> loc
        
        sitemaps = []
        for child in root:
            # find loc using any namespace
            loc = None
            for sub in child:
                if 'loc' in sub.tag:
                    loc = sub.text
                    break
            if loc:
                sitemaps.append(loc)
                
        print(f"Found {len(sitemaps)} sub-sitemaps")
        
        # Look for 'listing' or 'property' or 'landing' sitemaps
        # Often named 'sitemap-listings.xml' or similar
        relevant_sitemaps = [s for s in sitemaps if 'landing' in s or 'search' in s or 'location' in s or 'pages' in s]
        
        if not relevant_sitemaps:
            relevant_sitemaps = sitemaps[:3] # Check first few if no obvious name
            
        for sm_url in relevant_sitemaps:
            print(f"Checking sub-sitemap: {sm_url}")
            try:
                r_sm = requests.get(sm_url, headers=headers)
                content = r_sm.content
                
                # Handle gzipped sitemaps
                if sm_url.endswith('.gz'):
                    content = gzip.decompress(content)
                
                # Naive text search for Villa Crespo
                text_content = content.decode('utf-8', errors='ignore')
                if "villa-crespo" in text_content or "Villa-Crespo" in text_content:
                    print(f"✅ FOUND 'villa-crespo' in {sm_url}")
                    # Extract roughly the lines
                    lines = text_content.split('\n')
                    for line in lines:
                        if "villa-crespo" in line:
                            print(f"  -> {line.strip()[:200]}")
                else:
                    print(f"  (Not found in {sm_url})")
                    
            except Exception as e:
                print(f"Error checking {sm_url}: {e}")
                
    except Exception as e:
        print(f"Error parsing main sitemap: {e}")

if __name__ == "__main__":
    check_sitemap()
