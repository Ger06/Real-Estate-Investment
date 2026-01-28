import sys
import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def extract_breadcrumbs():
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    
    driver = webdriver.Chrome(options=chrome_options)
    
    try:
        url = "https://www.remax.com.ar/departamentos-en-venta-en-palermo"
        print(f"Navigating to {url}...")
        driver.get(url)
        
        # Wait for breadcrumbs
        time.sleep(5)
        
        print("Extracting links...")
        links = driver.find_elements(By.TAG_NAME, "a")
        
        candidates = []
        for a in links:
            try:
                href = a.get_attribute('href')
                text = a.text
                if href and 'remax.com.ar' in href:
                    # Check text for keywords
                    t_lower = text.lower()
                    if "capital" in t_lower or "buenos aires" in t_lower or "caba" in t_lower or "inicio" in t_lower:
                        print(f"  Candidate: '{text}' -> {href}")
                        candidates.append((text, href))
            except:
                continue
                
        # Specifically look for breadcrumb class
        crumbs = driver.find_elements(By.CSS_SELECTOR, "[class*='breadcrumb']")
        if crumbs:
            print(f"Found {len(crumbs)} breadcrumb elements")
            for c in crumbs:
                 print(f"  Breadcrumb text: {c.text}")
                 
    finally:
        driver.quit()

if __name__ == "__main__":
    extract_breadcrumbs()
