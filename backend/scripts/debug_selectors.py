import os
import sys
from bs4 import BeautifulSoup

def debug_selectors():
    # Load the debug HTML saved by the previous script
    file_path = 'remax_debug.html'
    if not os.path.exists(file_path):
        print(f"File {file_path} not found. Run reproduce_remax_error.py first.")
        return

    print(f"Reading {file_path}...")
    with open(file_path, 'r', encoding='utf-8') as f:
        html = f.read()

    soup = BeautifulSoup(html, 'html.parser')
    
    # 1. Try to find cards
    print("\n--- Searching for Cards ---")
    card_selectors = [
        '[class*="CardContainer"]',
        '[class*="property-card"]',
        '[class*="listing-card"]',
        '[class*="PropertyCard"]',
        '[data-testid*="property"]',
        '[class*="result-item"]',
        'article',
        '[class*="card"]',
        '[class*="Card"]' # Case sensitive check
    ]
    
    cards = []
    for selector in card_selectors:
        found = soup.select(selector)
        print(f"Selector '{selector}': Found {len(found)} elements")
        if found and not cards:
            cards = found
            print(f"  -> Using this for detailed check")

    if not cards:
        # Fallback: find links that look like listings and go up
        print("\nFallback: Finding cards via links")
        links = soup.select('a[href*="/listings/"]')
        print(f"Found {len(links)} listing links")
        if links:
            parent = links[0]
            # Go up until we hit a likely container
            for i in range(5):
                parent = parent.parent
                if parent:
                    classes = parent.get('class', [])
                    print(f"  Level {i} up: {parent.name} class={classes}")
                    if any('card' in str(c).lower() for c in classes):
                        cards = [parent]
                        print("  -> Found card container via link!")
                        break

    if not cards:
        print("❌ Could not isolate card elements.")
        return

    # 2. Analyze first card
    card = cards[0]
    print("\n--- Analyzing First Card ---")
    print(f"Card Tag: {card.name}")
    print(f"Card Classes: {card.get('class')}")
    
    # Dump structure (simplified)
    def print_structure(element, depth=0):
        indent = "  " * depth
        info = f"<{element.name}"
        if element.get('class'):
            info += f" class='{','.join(element.get('class'))}'"
        
        text = element.get_text(strip=True)
        if text and len(text) < 50:
            info += f"> text='{text}'"
        elif text:
            info += f"> text='{text[:20]}...'"
        else:
            info += ">"
            
        print(f"{indent}{info}")
        
        for child in element.children:
            if child.name:
                print_structure(child, depth + 1)
                
    print_structure(card)

    # 3. Test Field Extractors
    print("\n--- Testing Extractors ---")
    
    # Title
    title_selectors = ['h2', 'h3', 'h4', '[class*="title"]', '[class*="Title"]', '.card__title'] 
    for sel in title_selectors:
        elem = card.select_one(sel)
        if elem:
            print(f"✅ Title '{sel}': {elem.get_text(strip=True)[:50]}")
        else:
            print(f"❌ Title '{sel}': Not found")

    # Price
    price_selectors = ['[class*="price"]', '[class*="Price"]', '.card__price']
    for sel in price_selectors:
        elem = card.select_one(sel)
        if elem:
            print(f"✅ Price '{sel}': {elem.get_text(strip=True)}")
        else:
            print(f"❌ Price '{sel}': Not found")
            
    # Location
    loc_selectors = ['[class*="location"]', '[class*="Location"]', '[class*="address"]', '.card__address', '.card__ubication']
    for sel in loc_selectors:
        elem = card.select_one(sel)
        if elem:
            print(f"✅ Location '{sel}': {elem.get_text(strip=True)}")
        else:
            print(f"❌ Location '{sel}': Not found")

if __name__ == "__main__":
    debug_selectors()
