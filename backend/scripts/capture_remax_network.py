import sys
import os
import json
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

def capture_network():
    # Enable Performance Logging
    capabilities = DesiredCapabilities.CHROME
    capabilities["goog:loggingPrefs"] = {"performance": "ALL"}

    chrome_options = Options()
    # chrome_options.add_argument('--headless') # Needs to be headed to reliably trigger JS events sometimes, but let's try headless first
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    # In Selenium 4, capabilities are passed via options
    chrome_options.set_capability("goog:loggingPrefs", {"performance": "ALL"})

    driver = webdriver.Chrome(options=chrome_options)

    try:
        print("Loading Remax Home...")
        driver.get("https://www.remax.com.ar")
        time.sleep(5)
        
        # Clear initial logs
        driver.get_log("performance")
        
        # Interact with search
        print("Interacting with search input...")
        # Need to re-find the input logic from selenium_search_flow.py which worked partially
        
        # Wait for input
        inputs = driver.find_elements(By.CSS_SELECTOR, "input[placeholder*='buscar'], input[placeholder*='Buscar'], input[type='text']")
        if not inputs:
            print("No input found!")
            return
            
        search_input = inputs[0]
        QUERY = "Villa Crespo"
        
        print(f"Typing '{QUERY}'...")
        driver.execute_script("arguments[0].value = arguments[1];", search_input, QUERY)
        driver.execute_script("arguments[0].dispatchEvent(new Event('input'));", search_input)
        driver.execute_script("arguments[0].dispatchEvent(new Event('change'));", search_input)
        search_input.send_keys(" ") 
        search_input.send_keys(Keys.BACKSPACE)
        
        print("Waiting for network requests...")
        time.sleep(5)
        
        # Analyze logs
        logs = driver.get_log("performance")
        print(f"Captured {len(logs)} logs")
        
        found_relevant = False
        for entry in logs:
            message = json.loads(entry["message"])
            method = message["message"]["method"]
            
            if method == "Network.responseReceived":
                url = message["message"]["params"]["response"]["url"]
                
                # Filter for likely API calls
                if "api" in url or "json" in url or "suggest" in url or "algolia" in url or "search" in url:
                    status = message["message"]["params"]["response"]["status"]
                    print(f"Response: {url} [{status}]")
                    found_relevant = True
                    
                    # Note: Selenium perf logs don't contain response BODY easily.
                    # We usually just identity the URL pattern here.
                    
        if not found_relevant:
            print("No obvious API calls found looking for 'api', 'json', 'suggest', 'search'")

    except Exception as e:
        print(f"Error: {e}")
        
    finally:
        driver.quit()

if __name__ == "__main__":
    capture_network()
