import os
from bs4 import BeautifulSoup
import re

def analyze_html():
    file_path = 'remax_card_dump.html'
    if not os.path.exists(file_path):
        print(f"File {file_path} not found.")
        return

    print(f"Reading {file_path}...")
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            html = f.read()
            print(f"Success! Read {len(html)} bytes.")
    except Exception as e:
        print(f"Error reading file: {e}")
        return

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
    
    for i, div in enumerate(potential_cards[:5]):
        classes = div.get('class', [])
        is_card = any('card' in c.lower() or 'listing' in c.lower() or 'property' in c.lower() for c in classes)
        is_image = any('image' in c.lower() or 'img' in c.lower() or 'carousel' in c.lower() or 'slider' in c.lower() for c in classes)
        
        print(f"Div {i}: classes={classes}")
        print(f"  -> Is Card? {is_card}")
        print(f"  -> Is Image? {is_image} (Excluded: {is_card and is_image})")
        print(f"  -> Config would accept: {is_card and not is_image}")

    print("\n--- Checking Pagination Elements ---")
    pagination_ids = ['pagination', 'paginador', 'qr-pagination']
    for pid in pagination_ids:
        elem = soup.find(id=pid)
        if elem:
            print(f"Found ID '{pid}': {elem.prettify()[:500]}...")
            # Check for links inside
            links = elem.find_all('a')
            print(f"  -> Contains {len(links)} links")
            for l in links:
                print(f"     Link: href={l.get('href')} text={l.get_text(strip=True)}")
            
            # Check for buttons inside
            buttons = elem.find_all('button')
            print(f"  -> Contains {len(buttons)} buttons")
            for i, b in enumerate(buttons):
                print(f"     Button {i}: class={b.get('class')} disabled={b.get('disabled')}")
                print(f"     Inner: {b.prettify()[:200]}")

            
            # Print specifically the 'next' button candidates
            next_candidates = elem.select('button, div.arrow')
            for cand in next_candidates:
                 print(f"     Candidate: tag={cand.name} class={cand.get('class')}")

        else:
            print(f"ID '{pid}' not found.")

    pagination_classes = soup.select('[class*="pagination"], [class*="paginator"]')
    print(f"Found {len(pagination_classes)} elements with class 'pagination/paginator'")
    for elem in pagination_classes[:5]:
        print(f"Class match: {elem.name} classes={elem.get('class')} \nContent: {elem.get_text()[:100]}...")

    print("\n--- Detailed Card Analysis for Data Extraction ---")
    for i, div in enumerate(potential_cards[:5]):
        print(f"\n--- Card {i} ---")
        # Print first 500 chars to see structure
        print(div.prettify()[:800])
        
        # Check specific fields
        print("Potential Fields:")
        
        # Look for text that might be counts
        text_nodes = div.get_text(separator='|', strip=True).split('|')
        print(f"  Text nodes: {text_nodes}")

        print("  All child elements with classes:")
        all_children = div.find_all(True)
        for child in all_children:
            classes = child.get('class')
            if classes:
                print(f"    Tag: {child.name}, Classes: {classes}, Text: {child.get_text(strip=True)[:50]}")



if __name__ == "__main__":
    analyze_html()
