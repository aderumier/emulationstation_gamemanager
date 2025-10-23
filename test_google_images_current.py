#!/usr/bin/env python3
"""
Test script for current Google Images layout (udm=2)
"""

import requests
import os
import time
import json
import base64
import io
from urllib.parse import urlparse, parse_qs, unquote
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from PIL import Image
import re

class CurrentGoogleImageDownloader:
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
            self.driver = webdriver.Remote(
                command_executor='http://localhost:4444/wd/hub',
                options=chrome_options
            )
            print("✅ Connected to Selenium Docker container")
        except Exception as e:
            print(f"❌ Failed to connect to Selenium Docker: {e}")
            raise Exception("Could not initialize WebDriver")
    
    def search_and_download_images(self, search_query, num_images=5, save_directory="downloaded_images"):
        """Search and download images using current Google Images layout"""
        print(f"🔍 Searching for: {search_query}")
        
        # Create save directory
        if not os.path.exists(save_directory):
            os.makedirs(save_directory)
        
        # Construct Google Images search URL
        search_url = f"https://www.google.com/search?q={search_query.replace(' ', '+')}&tbm=isch"
        print(f"🔗 Search URL: {search_url}")
        
        try:
            self.driver.get(search_url)
            time.sleep(5)
            
            print(f"📄 Page title: {self.driver.title}")
            print(f"🌐 Current URL: {self.driver.current_url}")
            
            # Wait for images to load
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "img"))
                )
                print("✅ Images loaded successfully")
            except TimeoutException:
                print("❌ Timeout waiting for images to load")
                return
            
            # Find all image elements with data-ved attribute (current Google Images layout)
            image_containers = self.driver.find_elements(By.CSS_SELECTOR, "[data-ved] img")
            print(f"📸 Found {len(image_containers)} image containers")
            
            downloaded_count = 0
            
            for i, img in enumerate(image_containers[:num_images * 3]):  # Get more than needed
                try:
                    print(f"\n🖼️ Processing image {i+1}...")
                    
                    # Get the image source
                    src = img.get_attribute("src")
                    if not src:
                        print(f"  ⚠️ No src attribute")
                        continue
                    
                    print(f"  📍 Image src: {src[:100]}...")
                    
                    # Handle Base64 images
                    if src.startswith("data:image/"):
                        print(f"  🔍 Processing Base64 image...")
                        
                        # Check image dimensions
                        try:
                            header, data = src.split(',', 1)
                            image_data = base64.b64decode(data)
                            image = Image.open(io.BytesIO(image_data))
                            width, height = image.size
                            
                            print(f"  📏 Dimensions: {width}x{height}")
                            
                            # Skip small images
                            if width < 100 or height < 100:
                                print(f"  ⏭️ Skipping small image ({width}x{height})")
                                continue
                            
                            # Save the Base64 image
                            filename = f"image_{downloaded_count+1}_{width}x{height}.jpg"
                            save_path = os.path.join(save_directory, filename)
                            
                            with open(save_path, 'wb') as f:
                                f.write(image_data)
                            
                            print(f"  ✅ Saved Base64 image: {filename}")
                            downloaded_count += 1
                            
                        except Exception as e:
                            print(f"  ❌ Error processing Base64 image: {e}")
                            continue
                    
                    # Handle HTTP images
                    elif src.startswith("http"):
                        print(f"  🌐 Processing HTTP image...")
                        
                        # Skip Google's own images
                        if any(domain in src for domain in ["googleusercontent.com", "gstatic.com", "google.com"]):
                            print(f"  ⏭️ Skipping Google image")
                            continue
                        
                        # Try to download the image
                        try:
                            headers = {
                                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                            }
                            
                            response = requests.get(src, headers=headers, timeout=10)
                            response.raise_for_status()
                            
                            # Generate filename
                            parsed_url = urlparse(src)
                            filename = f"image_{downloaded_count+1}_{os.path.basename(parsed_url.path)}"
                            if not filename.endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')):
                                filename += '.jpg'
                            
                            save_path = os.path.join(save_directory, filename)
                            
                            with open(save_path, 'wb') as f:
                                f.write(response.content)
                            
                            print(f"  ✅ Downloaded HTTP image: {filename}")
                            downloaded_count += 1
                            
                        except Exception as e:
                            print(f"  ❌ Error downloading HTTP image: {e}")
                            continue
                    
                    else:
                        print(f"  ⚠️ Unknown image type: {src[:50]}...")
                        continue
                    
                    # Check if we have enough images
                    if downloaded_count >= num_images:
                        print(f"  🎯 Reached target of {num_images} images")
                        break
                    
                    time.sleep(1)  # Be respectful
                    
                except Exception as e:
                    print(f"  ❌ Error processing image {i+1}: {e}")
                    continue
            
            print(f"\n🎉 Successfully downloaded {downloaded_count} images to '{save_directory}'")
            
        except Exception as e:
            print(f"❌ Error during search: {e}")
    
    def try_alternative_approach(self, search_query, num_images=5, save_directory="downloaded_images"):
        """Try alternative approach using different selectors and methods"""
        print(f"\n🔄 Trying alternative approach...")
        
        try:
            # Try with different URL parameters
            alt_url = f"https://www.google.com/search?q={search_query.replace(' ', '+')}&tbm=isch&udm=1"
            print(f"🔗 Alternative URL: {alt_url}")
            
            self.driver.get(alt_url)
            time.sleep(5)
            
            # Try different selectors
            selectors_to_try = [
                "img[src*='encrypted-tbn']",
                ".rg_i img",
                ".mimg",
                "img[data-src]",
                "[data-ved] img"
            ]
            
            for selector in selectors_to_try:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    print(f"  {selector}: {len(elements)} elements")
                    
                    if elements:
                        # Process first few elements
                        for i, img in enumerate(elements[:3]):
                            try:
                                src = img.get_attribute("src") or img.get_attribute("data-src")
                                if src and src.startswith("data:image/"):
                                    print(f"    Found Base64 image: {src[:50]}...")
                                    
                                    # Save Base64 image
                                    header, data = src.split(',', 1)
                                    image_data = base64.b64decode(data)
                                    
                                    filename = f"alt_image_{i+1}.jpg"
                                    save_path = os.path.join(save_directory, filename)
                                    
                                    with open(save_path, 'wb') as f:
                                        f.write(image_data)
                                    
                                    print(f"    ✅ Saved: {filename}")
                                    
                            except Exception as e:
                                print(f"    ❌ Error: {e}")
                                
                except Exception as e:
                    print(f"  {selector}: Error - {e}")
            
        except Exception as e:
            print(f"❌ Alternative approach failed: {e}")
    
    def close(self):
        """Close the driver"""
        if self.driver:
            self.driver.quit()

def main():
    """Main function to test current Google Images"""
    print("🚀 Starting Current Google Images Test")
    print("=" * 60)
    
    downloader = None
    try:
        downloader = CurrentGoogleImageDownloader()
        
        # Test parameters
        search_query = "Alan Wake"
        num_images = 5
        save_directory = "test_current_images"
        
        # Try main approach
        downloader.search_and_download_images(search_query, num_images, save_directory)
        
        # Try alternative approach
        downloader.try_alternative_approach(search_query, num_images, save_directory)
        
        print("=" * 60)
        print("✅ Test completed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        
    finally:
        if downloader:
            downloader.close()

if __name__ == "__main__":
    main()
