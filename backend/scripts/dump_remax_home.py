import sys
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time

def dump_home_source():
    chrome_options = Options()
    # chrome_options.add_argument('--headless') # Run headed to avoid some bot detection? No, let's try headless first for speed.
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    driver = webdriver.Chrome(options=chrome_options)
    
    try:
        print("Loading Remax Home...")
        driver.get("https://www.remax.com.ar")
        time.sleep(5)
        
        print("Saving source...")
        with open("remax_home_source.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
            
        print("Saved to remax_home_source.html")
        
    finally:
        driver.quit()

if __name__ == "__main__":
    dump_home_source()
