import sys
import os
import asyncio
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Add backend directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
sys.path.append(backend_dir)

from app.scrapers.listing_remax import RemaxListingScraper

async def simulate_search():
    scraper = RemaxListingScraper({})
    driver = scraper._get_driver()
    
    try:
        print("\n--- Simulating User Search Flow ---")
        driver.get("https://www.remax.com.ar")
        print("Loaded Home Page")
        
        # Wait for search input
        # Try to find the main search bar
        # Based on typical structure, usually input[type="text"] or distinct class
        wait = WebDriverWait(driver, 10)
        
        # Taking a screenshot (optional logic, but we can just dump html or look for element)
        # Assuming standard input
        search_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[placeholder*='buscar'], input[placeholder*='Buscar'], input[type='text']")))
        
        print(f"Found input: {search_input.get_attribute('placeholder')}")
        
        # Test 1: Palermo (Control)
        QUERY = "Palermo"
        print(f"Typing '{QUERY}'...")
        # Use a more robust typing method for Angular
        print(f"Typing '{QUERY}' with JS events...")
        driver.execute_script("arguments[0].value = arguments[1];", search_input, QUERY)
        driver.execute_script("arguments[0].dispatchEvent(new Event('input'));", search_input)
        driver.execute_script("arguments[0].dispatchEvent(new Event('change'));", search_input)
        
        search_input.send_keys(" ") # Trigger keyup
        search_input.send_keys(Keys.BACKSPACE)
        
        print("Parametro typed, waiting for autocomplete...")
        await asyncio.sleep(5) 
        
        # Try to find autocomplete options
        print("Looking for dropdown items...")
        
        selectors = [
            ".mat-mdc-option", # Updated MDC class
            ".mat-option", 
            "mat-option",
            ".ui-menu-item", 
            "li[role='option']", 
            "div[role='listbox']",
            ".search-result-item"
        ]
        
        clicked = False
        for sel in selectors:
            options = driver.find_elements(By.CSS_SELECTOR, sel)
            if options:
                print(f"Found {len(options)} options with selector '{sel}'")
                for opt in options[:3]:
                    print(f" - Option: {opt.text}")
                
                print(f"Clicking first option: {options[0].text}")
                options[0].click()
                clicked = True
                break
        
        if not clicked:
            print("❌ No autocomplete options found. Dumping page source snippets...")
            # Dump inputs and lists
            inputs = driver.find_elements(By.CSS_SELECTOR, "input")
            for i in inputs:
                print(f"Input: id={i.get_attribute('id')} class={i.get_attribute('class')}")
            
            # Press enter as fallback
            search_input.send_keys(Keys.ENTER)
            print("Pressed Enter (Fallback)")
        
        await asyncio.sleep(5)
        
        print(f"Current URL: {driver.current_url}")
        print(f"Page Title: {driver.title}")
        
    except Exception as e:
        print(f"Error: {e}")
        # Save screenshot
        driver.save_screenshot("search_error.png")
        print("Saved search_error.png")

    finally:
        driver.quit()

if __name__ == "__main__":
    asyncio.run(simulate_search())
