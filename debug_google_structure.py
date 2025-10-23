#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug script to examine the actual HTML structure of Google Images
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time
import os

def debug_google_images_structure():
    """Debug the actual HTML structure of Google Images"""
    print("🔧 DEBUG: Debugging Google Images HTML structure")
    print("=" * 50)
    
    driver = None
    try:
        # Set up Chrome options for headless mode
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--disable-web-security')
        chrome_options.add_argument('--disable-features=VizDisplayCompositor')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
        
        # Try to connect to Selenium Docker container first, fallback to local Chrome
        try:
            print("🔧 DEBUG: Attempting to connect to Selenium Docker container...")
            driver = webdriver.Remote(
                command_executor='http://localhost:4444/wd/hub',
                options=chrome_options
            )
            print("🔧 DEBUG: Connected to Selenium Docker container")
        except Exception as e:
            print(f"🔧 DEBUG: Failed to connect to Selenium Docker: {e}")
            print("🔧 DEBUG: Falling back to local Chrome driver")
            driver = webdriver.Chrome(options=chrome_options)
        
        # Navigate to Google Images
        search_query = "Alan Wake".replace(' ', '+')
        base_url = f"https://www.google.com/search?q={search_query}&tbm=isch&imgar=xw"
        
        print(f"🔧 DEBUG: Navigating to: {base_url}")
        driver.get(base_url)
        time.sleep(5)  # Give it time to load
        
        # Scroll down to load more images
        for i in range(3):
            driver.execute_script("window.scrollBy(0, 1000);")
            time.sleep(2)
        
        print("\n🔧 DEBUG: Examining HTML structure...")
        
        # Find all img elements
        all_imgs = driver.find_elements(By.TAG_NAME, "img")
        print(f"📷 Found {len(all_imgs)} total img elements")
        
        # Look for all elements with href attributes that might contain imgurl
        print("\n🔍 Looking for all elements with href attributes...")
        
        all_elements_with_href = driver.find_elements(By.XPATH, "//*[@href]")
        print(f"📎 Found {len(all_elements_with_href)} elements with href attributes")
        
        imgurl_count = 0
        for i, element in enumerate(all_elements_with_href[:50]):  # Check first 50
            href = element.get_attribute('href')
            if href and 'imgurl=' in href:
                imgurl_count += 1
                print(f"\n✅ Element {imgurl_count} with imgurl:")
                print(f"  tag: {element.tag_name}")
                print(f"  class: {element.get_attribute('class')}")
                print(f"  href: {href[:150]}...")
                
                # Extract imgurl parameter
                from urllib.parse import urlparse, parse_qs
                parsed_url = urlparse(href)
                query_params = parse_qs(parsed_url.query)
                
                if 'imgurl' in query_params:
                    imgurl = query_params['imgurl'][0]
                    print(f"  imgurl: {imgurl[:100]}...")
                
                if imgurl_count >= 5:  # Limit output
                    break
        
        if imgurl_count == 0:
            print("\n❌ No elements found with imgurl parameter")
            print("🔍 Let's examine the structure more carefully...")
            
            # Look for Base64 images and their parent elements
            base64_count = 0
            for i, img in enumerate(all_imgs[:10]):  # Limit to first 10
                src = img.get_attribute("src") or img.get_attribute("data-src")
                if src and src.startswith("data:image/"):
                    base64_count += 1
                    print(f"\n🔍 Base64 Image {base64_count}:")
                    print(f"  src: {src[:50]}...")
                    
                    # Find all ancestors
                    try:
                        ancestors = img.find_elements(By.XPATH, "./ancestor::*")
                        print(f"  Found {len(ancestors)} ancestors")
                        
                        for j, ancestor in enumerate(ancestors[:5]):  # Check first 5 ancestors
                            href = ancestor.get_attribute('href')
                            if href:
                                print(f"    ancestor {j+1} ({ancestor.tag_name}): {href[:100]}...")
                    except Exception as e:
                        print(f"  Error finding ancestors: {e}")
                    
                    if base64_count >= 3:  # Limit output
                        break
        
        print(f"\n📊 Summary: Found {base64_count} Base64 images in first 20 img elements")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if driver:
            driver.quit()

if __name__ == "__main__":
    debug_google_images_structure()
