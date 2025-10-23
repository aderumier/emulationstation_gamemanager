#!/usr/bin/env python3
"""
Debug script to find current Google Images selectors
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import time

def debug_google_selectors():
    print("🔍 Debugging Google Images selectors...")
    
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    try:
        driver = webdriver.Remote(
            command_executor='http://localhost:4444/wd/hub',
            options=chrome_options
        )
        print("✅ Connected to Selenium Docker")
        
        # Go to Google Images
        driver.get("https://www.google.com/search?q=Alan+Wake&tbm=isch")
        time.sleep(5)
        
        print("🔍 Looking for image containers...")
        
        # Try different selectors
        selectors_to_try = [
            "//div[@class='czzyk XOEbc']",  # Original pruthvik selector
            "//div[contains(@class, 'czzyk')]",
            "//div[contains(@class, 'XOEbc')]",
            "//div[@data-ved]",
            "//img[contains(@src, 'data:image')]",
            "//img[contains(@src, 'http')]",
            "//div[contains(@class, 'isv-r')]",
            "//div[contains(@class, 'PNCib')]",
            "//div[contains(@class, 'ViTmJb')]",
            "//div[contains(@class, 'BUooTd')]"
        ]
        
        for selector in selectors_to_try:
            try:
                elements = driver.find_elements(By.XPATH, selector)
                print(f"✅ Selector '{selector}': Found {len(elements)} elements")
                if elements and len(elements) > 0:
                    print(f"   First element classes: {elements[0].get_attribute('class')}")
            except Exception as e:
                print(f"❌ Selector '{selector}': Error - {e}")
        
        # Look for the full-size image selector
        print("\n🔍 Looking for full-size image selectors...")
        full_size_selectors = [
            "//img[@class='sFlh5c FyHeAf iPVvYb']",  # Original pruthvik selector
            "//img[contains(@class, 'sFlh5c')]",
            "//img[contains(@class, 'FyHeAf')]",
            "//img[contains(@class, 'iPVvYb')]",
            "//img[contains(@src, 'http') and not(contains(@src, 'googleusercontent'))]"
        ]
        
        for selector in full_size_selectors:
            try:
                elements = driver.find_elements(By.XPATH, selector)
                print(f"✅ Full-size selector '{selector}': Found {len(elements)} elements")
            except Exception as e:
                print(f"❌ Full-size selector '{selector}': Error - {e}")
        
        driver.quit()
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    debug_google_selectors()
