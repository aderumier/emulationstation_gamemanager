#!/usr/bin/env python3
"""
Debug test script for Google Images scraping with multiple strategies
"""

import requests
import os
import time
import json
from urllib.parse import urlparse, parse_qs, unquote
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import re

class GoogleImageDebugger:
    def __init__(self):
        self.driver = None
        self.setup_driver()
    
    def setup_driver(self):
        """Setup Chrome driver with options"""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        try:
            # Try to connect to Selenium Docker container first
            self.driver = webdriver.Remote(
                command_executor='http://localhost:4444/wd/hub',
                options=chrome_options
            )
            print("✅ Connected to Selenium Docker container")
        except Exception as e:
            print(f"❌ Failed to connect to Selenium Docker: {e}")
            raise Exception("Could not initialize WebDriver")
    
    def debug_google_images_page(self, search_query):
        """Debug what we can find on Google Images page"""
        print(f"🔍 Debugging Google Images for: {search_query}")
        
        # Construct Google Images search URL
        search_url = f"https://www.google.com/search?q={search_query.replace(' ', '+')}&tbm=isch"
        print(f"🔗 Search URL: {search_url}")
        
        try:
            self.driver.get(search_url)
            time.sleep(5)
            
            print(f"📄 Page title: {self.driver.title}")
            print(f"🌐 Current URL: {self.driver.current_url}")
            
            # Check if we got redirected or blocked
            if "consent" in self.driver.current_url.lower() or "cookies" in self.driver.current_url.lower():
                print("⚠️ Detected cookie consent page, trying to accept...")
                try:
                    # Try to find and click accept button
                    accept_buttons = self.driver.find_elements(By.XPATH, "//button[contains(text(), 'Accept') or contains(text(), 'I agree') or contains(text(), 'Accept all')]")
                    if accept_buttons:
                        accept_buttons[0].click()
                        time.sleep(3)
                        print("✅ Accepted cookies")
                    else:
                        print("❌ Could not find accept button")
                except Exception as e:
                    print(f"❌ Error accepting cookies: {e}")
            
            # Wait for images to load
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "img"))
                )
                print("✅ Images loaded successfully")
            except TimeoutException:
                print("❌ Timeout waiting for images to load")
                return
            
            # Find all image elements
            images = self.driver.find_elements(By.CSS_SELECTOR, "img")
            print(f"📸 Found {len(images)} image elements")
            
            # Analyze different types of images
            http_images = []
            data_images = []
            google_images = []
            other_images = []
            
            for i, img in enumerate(images[:50]):  # Analyze first 50 images
                try:
                    src = img.get_attribute("src")
                    if not src:
                        continue
                    
                    if src.startswith("data:image/"):
                        data_images.append((i, src[:100] + "..."))
                    elif "googleusercontent.com" in src or "gstatic.com" in src or "google.com" in src:
                        google_images.append((i, src[:100] + "..."))
                    elif src.startswith("http"):
                        http_images.append((i, src[:100] + "..."))
                    else:
                        other_images.append((i, src[:100] + "..."))
                        
                except Exception as e:
                    print(f"⚠️ Error analyzing image {i}: {e}")
            
            print(f"\n📊 Image Analysis:")
            print(f"  HTTP images: {len(http_images)}")
            print(f"  Data images: {len(data_images)}")
            print(f"  Google images: {len(google_images)}")
            print(f"  Other images: {len(other_images)}")
            
            # Show some examples
            if http_images:
                print(f"\n🌐 HTTP Image examples:")
                for i, (idx, src) in enumerate(http_images[:3]):
                    print(f"  {i+1}. [{idx}] {src}")
            
            if data_images:
                print(f"\n📦 Data Image examples:")
                for i, (idx, src) in enumerate(data_images[:3]):
                    print(f"  {i+1}. [{idx}] {src}")
            
            # Try to find clickable image containers
            print(f"\n🔍 Looking for clickable image containers...")
            clickable_elements = self.driver.find_elements(By.CSS_SELECTOR, "[data-ved], [jsname], .rg_i, .mimg")
            print(f"Found {len(clickable_elements)} potentially clickable elements")
            
            # Try clicking on first few images to see what happens
            print(f"\n🖱️ Testing image clicks...")
            for i, img in enumerate(images[:5]):
                try:
                    print(f"  Testing click on image {i+1}...")
                    
                    # Scroll to image
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", img)
                    time.sleep(1)
                    
                    # Try to click
                    img.click()
                    time.sleep(2)
                    
                    # Check if URL changed or new elements appeared
                    current_url = self.driver.current_url
                    if "imgres" in current_url:
                        print(f"    ✅ Click successful - URL changed to: {current_url[:100]}...")
                        
                        # Try to extract imgurl parameter
                        parsed_url = urlparse(current_url)
                        query_params = parse_qs(parsed_url.query)
                        
                        if 'imgurl' in query_params:
                            imgurl = query_params['imgurl'][0]
                            decoded_url = unquote(imgurl)
                            print(f"    🎯 Found imgurl: {decoded_url[:100]}...")
                        else:
                            print(f"    ⚠️ No imgurl parameter found")
                        
                        # Go back
                        self.driver.back()
                        time.sleep(2)
                        break
                    else:
                        print(f"    ⚠️ Click didn't change URL")
                        
                except Exception as e:
                    print(f"    ❌ Error clicking image {i+1}: {e}")
            
            # Check page source for any imgurl patterns
            print(f"\n🔍 Searching page source for imgurl patterns...")
            page_source = self.driver.page_source
            imgurl_matches = re.findall(r'imgurl=([^&"\']+)', page_source)
            if imgurl_matches:
                print(f"Found {len(imgurl_matches)} imgurl patterns in page source")
                for i, match in enumerate(imgurl_matches[:3]):
                    decoded_url = unquote(match)
                    print(f"  {i+1}. {decoded_url[:100]}...")
            else:
                print("No imgurl patterns found in page source")
            
            # Try alternative selectors
            print(f"\n🔍 Trying alternative selectors...")
            alt_selectors = [
                "img[data-src]",
                "img[src*='encrypted-tbn']",
                ".rg_i img",
                ".mimg",
                "[data-ved] img"
            ]
            
            for selector in alt_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    print(f"  {selector}: {len(elements)} elements")
                except Exception as e:
                    print(f"  {selector}: Error - {e}")
            
        except Exception as e:
            print(f"❌ Error during debugging: {e}")
    
    def close(self):
        """Close the driver"""
        if self.driver:
            self.driver.quit()

def main():
    """Main function to debug Google Images"""
    print("🚀 Starting Google Images Debug Test")
    print("=" * 60)
    
    debugger = None
    try:
        debugger = GoogleImageDebugger()
        debugger.debug_google_images_page("Alan Wake")
        
        print("=" * 60)
        print("✅ Debug test completed!")
        
    except Exception as e:
        print(f"❌ Debug test failed: {e}")
        
    finally:
        if debugger:
            debugger.close()

if __name__ == "__main__":
    main()
