import os
from bs4 import BeautifulSoup

def analyze_html():
    file_path = 'remax_debug_api.html'
    if not os.path.exists(file_path):
        print(f"File {file_path} not found.")
        return

    print(f"Reading {file_path}...")
    with open(file_path, 'r', encoding='utf-8') as f:
        html = f.read()

    soup = BeautifulSoup(html, 'html.parser')
    
    print(f"\nPage Title: {soup.title.string if soup.title else 'No Title'}")
    
    # Check for "No results" messages
    print("\n--- Checking for 'No results' text ---")
    body_text = soup.get_text().lower()
    keywords = ["no encontramos", "no hay resultados", "0 propiedades", "cero propiedades"]
    for kw in keywords:
        if kw in body_text:
            print(f"⚠️  Found '{kw}' in page text")
    
    # Check for result count
    print("\n--- Checking for result count ---")
    # Remax often has "X Propiedades en venta" or similar
    import re
    match = re.search(r'(\d+)\s+Propiedades', body_text, re.IGNORECASE)
    if match:
        print(f"Found property count text: {match.group(0)}")
    
    # Check for cards logic mismatch
    print("\n--- Checking Card Elements ---")
    divs = soup.find_all('div')
    potential_cards = []
    for div in divs:
        classes = div.get('class', [])
        if any('card' in c.lower() or 'listing' in c.lower() or 'property' in c.lower() for c in classes):
            potential_cards.append(div)
            
    print(f"Found {len(potential_cards)} divs with 'card/listing/property' in class")
    
    # Detailed analysis of first 5 potential cards
    for i, div in enumerate(potential_cards[:10]):
        classes = div.get('class', [])
        is_card = any('card' in c.lower() or 'listing' in c.lower() or 'property' in c.lower() for c in classes)
        is_image = any('image' in c.lower() or 'img' in c.lower() or 'carousel' in c.lower() or 'slider' in c.lower() for c in classes)
        
        print(f"Div {i}: classes={classes}")
        print(f"  -> Is Card? {is_card}")
        print(f"  -> Is Image? {is_image} (Excluded: {is_card and is_image})")
        print(f"  -> Config would accept: {is_card and not is_image}")

if __name__ == "__main__":
    analyze_html()
