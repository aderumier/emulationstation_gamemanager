#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for Google search with cookie handling
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
import time
import os

def test_google_search_with_cookies():
    """Test Google search with proper cookie handling"""
    print("🔧 DEBUG: Testing Google search with cookie handling")
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
        
        # Navigate directly to Google Images search
        search_url = "https://www.google.com/search?q=Alan+Wake&tbm=isch&imgar=xw"
        
        print(f"🔧 DEBUG: Navigating to: {search_url}")
        driver.get(search_url)
        
        # Wait for page to load and handle potential cookie popup
        wait = WebDriverWait(driver, 10)
        
        try:
            # Check for cookie consent popup and handle it
            print("🔧 DEBUG: Checking for cookie consent popup...")
            
            # Common cookie consent button selectors
            cookie_selectors = [
                "button[id*='accept']",
                "button[class*='accept']", 
                "button:contains('Accept')",
                "button:contains('I agree')",
                "button:contains('Accept all')",
                "#L2AGLb",  # Google's accept button ID
                "button[aria-label*='Accept']"
            ]
            
            cookie_accepted = False
            for selector in cookie_selectors:
                try:
                    if ":contains(" in selector:
                        # Use XPath for text content
                        xpath = f"//button[contains(text(), '{selector.split(':contains(')[1].split(')')[0]}')]"
                        cookie_button = driver.find_element(By.XPATH, xpath)
                    else:
                        cookie_button = driver.find_element(By.CSS_SELECTOR, selector)
                    
                    if cookie_button.is_displayed():
                        print(f"🔧 DEBUG: Found cookie consent button with selector: {selector}")
                        cookie_button.click()
                        print("🔧 DEBUG: Clicked cookie consent button")
                        cookie_accepted = True
                        time.sleep(2)  # Wait for popup to disappear
                        break
                except:
                    continue
            
            if not cookie_accepted:
                print("🔧 DEBUG: No cookie consent popup found or already accepted")
        
        except Exception as e:
            print(f"🔧 DEBUG: Error handling cookie popup: {e}")
        
        # Wait a bit more for page to fully load
        time.sleep(3)
        
        print("\n🔧 DEBUG: Examining page structure...")
        
        # Get page title to verify we're on the right page
        page_title = driver.title
        print(f"📄 Page title: {page_title}")
        
        # Look for search results
        search_results = driver.find_elements(By.CSS_SELECTOR, "div.g, div[data-ved]")
        print(f"🔍 Found {len(search_results)} search result elements")
        
        # Look for any links that might contain image URLs
        all_links = driver.find_elements(By.TAG_NAME, "a")
        print(f"🔗 Found {len(all_links)} total links")
        
        # Check for any links with imgurl parameter
        imgurl_links = []
        for link in all_links[:50]:  # Check first 50 links
            href = link.get_attribute('href')
            if href and 'imgurl=' in href:
                imgurl_links.append(link)
        
        print(f"🖼️ Found {len(imgurl_links)} links with imgurl parameter")
        
        if imgurl_links:
            print("\n✅ Links with imgurl parameter:")
            for i, link in enumerate(imgurl_links[:5]):  # Show first 5
                href = link.get_attribute('href')
                print(f"  {i+1}: {href[:100]}...")
                
                # Extract imgurl parameter
                from urllib.parse import urlparse, parse_qs
                parsed_url = urlparse(href)
                query_params = parse_qs(parsed_url.query)
                
                if 'imgurl' in query_params:
                    imgurl = query_params['imgurl'][0]
                    print(f"     imgurl: {imgurl[:100]}...")
        else:
            print("\n❌ No links with imgurl parameter found")
        
        # Since we're already on Images page, let's try hovering over images to trigger imgurl generation
        print("\n🔧 DEBUG: Trying to trigger imgurl generation by hovering over images...")
        
        # Find Base64 thumbnail images
        all_imgs = driver.find_elements(By.TAG_NAME, "img")
        base64_thumbnails = []
        for img in all_imgs:
            src = img.get_attribute("src") or img.get_attribute("data-src")
            if src and src.startswith("data:image/"):
                base64_thumbnails.append(img)
        
        print(f"🖼️ Found {len(base64_thumbnails)} Base64 thumbnails")
        
        if base64_thumbnails:
            # Try hovering over first few thumbnails
            for i, thumbnail in enumerate(base64_thumbnails[:5]):
                try:
                    print(f"🔧 DEBUG: Hovering over thumbnail {i+1}")
                    
                    # Scroll to make sure the image is visible
                    driver.execute_script("arguments[0].scrollIntoView(true);", thumbnail)
                    time.sleep(1)
                    
                    # Simulate hover
                    driver.execute_script("arguments[0].dispatchEvent(new MouseEvent('mouseover', {bubbles: true}));", thumbnail)
                    time.sleep(2)  # Wait for hover effects
                    
                    # Check for imgurl parameters after hover
                    all_links_after_hover = driver.find_elements(By.TAG_NAME, "a")
                    imgurl_links_after_hover = []
                    for link in all_links_after_hover:
                        href = link.get_attribute('href')
                        if href and 'imgurl=' in href:
                            imgurl_links_after_hover.append(link)
                    
                    if imgurl_links_after_hover:
                        print(f"✅ Found {len(imgurl_links_after_hover)} links with imgurl after hover!")
                        for j, link in enumerate(imgurl_links_after_hover[:3]):
                            href = link.get_attribute('href')
                            print(f"  {j+1}: {href[:100]}...")
                            
                            # Extract imgurl parameter
                            from urllib.parse import urlparse, parse_qs
                            parsed_url = urlparse(href)
                            query_params = parse_qs(parsed_url.query)
                            
                            if 'imgurl' in query_params:
                                imgurl = query_params['imgurl'][0]
                                print(f"     imgurl: {imgurl[:100]}...")
                        break  # Found imgurl, no need to continue
                    else:
                        print(f"❌ No imgurl found after hover {i+1}")
                    
                    # Mouse out to reset
                    driver.execute_script("arguments[0].dispatchEvent(new MouseEvent('mouseout', {bubbles: true}));", thumbnail)
                    
                except Exception as e:
                    print(f"❌ Error hovering over thumbnail {i+1}: {e}")
                    continue
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if driver:
            driver.quit()

if __name__ == "__main__":
    test_google_search_with_cookies()
