import sys
import os
import asyncio
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

def click_suggestion():
    chrome_options = Options()
    # chrome_options.add_argument('--headless') # Headed to see what happens
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    
    driver = webdriver.Chrome(options=chrome_options)
    
    try:
        print("Loading Home...")
        driver.get("https://www.remax.com.ar")
        time.sleep(5)
        
        inputs = driver.find_elements(By.CSS_SELECTOR, "input[placeholder*='buscar'], input[placeholder*='Buscar'], input[type='text']")
        if not inputs:
            print("No input found")
            return
            
        search_input = inputs[0]
        QUERY = "Villa Crespo"
        
        print(f"Typing {QUERY}...")
        driver.execute_script("arguments[0].value = arguments[1];", search_input, QUERY)
        driver.execute_script("arguments[0].dispatchEvent(new Event('input'));", search_input)
        driver.execute_script("arguments[0].dispatchEvent(new Event('change'));", search_input)
        search_input.send_keys(" ")
        search_input.send_keys(Keys.BACKSPACE)
        
        print("Waiting for suggestions...")
        time.sleep(5)
        
        # Dump processed HTML to see dropdown
        # Look for typical angular material dropdowns
        selectors = [
             ".mat-mdc-option", ".mat-option", ".pac-item", "li[role='option']", 
             ".search-result-item", "div.suggestion"
        ]
        
        clicked = False
        for sel in selectors:
            opts = driver.find_elements(By.CSS_SELECTOR, sel)
            if opts:
                print(f"Found {len(opts)} options for {sel}")
                for o in opts:
                    print(f"  Option text: {o.text}")
                    if "Villa Crespo" in o.text:
                        print("  clicking...")
                        o.click()
                        clicked = True
                        break
            if clicked: break
            
        if not clicked:
            print("No options found. Saving screenshot.")
            driver.save_screenshot("suggestion_fail.png")
            
        # Wait for nav
        time.sleep(5)
        print(f"Final URL: {driver.current_url}")
        print(f"Final Title: {driver.title}")

    finally:
        driver.quit()

if __name__ == "__main__":
    click_suggestion()
