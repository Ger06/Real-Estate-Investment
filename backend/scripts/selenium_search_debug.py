import sys
import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def debug_search_flow():
    chrome_options = Options()
    # chrome_options.add_argument('--headless') # Run headless but save screenshots
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument("--window-size=1920,1080")
    
    driver = webdriver.Chrome(options=chrome_options)
    
    try:
        print("Loading Remax Home...")
        driver.get("https://www.remax.com.ar")
        time.sleep(5)
        driver.save_screenshot("step1_home.png")
        
        inputs = driver.find_elements(By.CSS_SELECTOR, "input[placeholder*='buscar'], input[placeholder*='Buscar'], input[type='text']")
        if not inputs:
            print("No input found")
            return
            
        search_input = inputs[0]
        # Try specific CSS if known
        # search_input = driver.find_element(By.CSS_SELECTOR, ".search-input")
        
        QUERY = "Villa Crespo"
        print(f"Typing {QUERY}...")
        search_input.click()
        search_input.clear()
        search_input.send_keys(QUERY)
        time.sleep(1)
        search_input.send_keys(Keys.SPACE)
        search_input.send_keys(Keys.BACKSPACE)
        time.sleep(3)
        driver.save_screenshot("step2_typed.png")
        
        print("Looking for suggestions...")
        # Check if suggestion box appears
        selectors = [
             ".mat-mdc-option", ".mat-option", ".pac-item", "li[role='option']", 
             ".search-result-item"
        ]
        
        clicked = False
        for sel in selectors:
            opts = driver.find_elements(By.CSS_SELECTOR, sel)
            if opts:
                print(f"Found {len(opts)} options for {sel}")
                for o in opts:
                    txt = o.text
                    print(f"  Option: {txt}")
                    if "Villa Crespo" in txt:
                        print(f"  Clicking option: {txt}")
                        o.click()
                        clicked = True
                        break
            if clicked: break
            
        if not clicked:
            print("No suggestion clicked. Trying ENTER key...")
            search_input.send_keys(Keys.ENTER)
            
        print("Waiting for navigation...")
        time.sleep(10)
        driver.save_screenshot("step3_result.png")
        
        print(f"Final URL: {driver.current_url}")
        print(f"Final Title: {driver.title}")
        
    finally:
        driver.quit()

if __name__ == "__main__":
    debug_search_flow()
