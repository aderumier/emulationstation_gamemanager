#!/usr/bin/env python3
"""
Test script for Google Images scraping using an alternative approach
Based on: https://github.com/amitgurkhe/Image_webScraper/blob/main/google_image_downloader.py
"""

import requests
import os
import time
from urllib.parse import urlparse, parse_qs
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import json

class GoogleImageDownloader:
    def __init__(self, search_query, num_images=10):
        self.search_query = search_query
        self.num_images = num_images
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
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        
        try:
            # Try to connect to Selenium Docker container first
            self.driver = webdriver.Remote(
                command_executor='http://localhost:4444/wd/hub',
                options=chrome_options
            )
            print("✅ Connected to Selenium Docker container")
        except Exception as e:
            print(f"❌ Failed to connect to Selenium Docker: {e}")
            print("🔧 Falling back to local Chrome driver...")
            try:
                self.driver = webdriver.Chrome(options=chrome_options)
                print("✅ Connected to local Chrome driver")
            except Exception as e2:
                print(f"❌ Failed to connect to local Chrome driver: {e2}")
                raise Exception("Could not initialize WebDriver")
    
    def search_images(self):
        """Search for images on Google Images"""
        print(f"🔍 Searching for: {self.search_query}")
        
        # Construct Google Images search URL
        search_url = f"https://www.google.com/search?q={self.search_query.replace(' ', '+')}&tbm=isch"
        print(f"🔗 Search URL: {search_url}")
        
        try:
            self.driver.get(search_url)
            time.sleep(3)
            
            # Wait for images to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "img"))
            )
            
            # Find all image elements
            images = self.driver.find_elements(By.CSS_SELECTOR, "img")
            print(f"📸 Found {len(images)} image elements")
            
            image_urls = []
            processed_count = 0
            
            for i, img in enumerate(images[:self.num_images * 3]):  # Get more than needed to filter
                try:
                    src = img.get_attribute("src")
                    if not src:
                        continue
                    
                    # Skip data URLs and small images
                    if src.startswith("data:image/"):
                        continue
                    
                    # Skip Google's own images
                    if any(domain in src for domain in ["googleusercontent.com", "gstatic.com", "google.com"]):
                        continue
                    
                    # Try to get the original image URL
                    original_url = self.get_original_image_url(img)
                    if original_url and original_url not in image_urls:
                        image_urls.append(original_url)
                        processed_count += 1
                        print(f"✅ Found image {processed_count}: {original_url[:100]}...")
                        
                        if processed_count >= self.num_images:
                            break
                            
                except Exception as e:
                    print(f"⚠️ Error processing image {i}: {e}")
                    continue
            
            print(f"🎯 Successfully extracted {len(image_urls)} image URLs")
            return image_urls
            
        except Exception as e:
            print(f"❌ Error during search: {e}")
            return []
    
    def get_original_image_url(self, img_element):
        """Try to get the original image URL by clicking on the image"""
        try:
            # Scroll to the image
            self.driver.execute_script("arguments[0].scrollIntoView(true);", img_element)
            time.sleep(1)
            
            # Click on the image
            img_element.click()
            time.sleep(2)
            
            # Look for the original image in the preview
            preview_images = self.driver.find_elements(By.CSS_SELECTOR, "img[src*='http']")
            
            for preview_img in preview_images:
                src = preview_img.get_attribute("src")
                if src and not any(domain in src for domain in ["googleusercontent.com", "gstatic.com", "google.com"]):
                    return src
            
            # If no preview found, try to find imgurl in the page
            page_source = self.driver.page_source
            if "imgurl=" in page_source:
                # Extract imgurl from page source
                import re
                imgurl_match = re.search(r'imgurl=([^&"]+)', page_source)
                if imgurl_match:
                    imgurl = imgurl_match.group(1)
                    # Decode URL
                    from urllib.parse import unquote
                    decoded_url = unquote(imgurl)
                    return decoded_url
            
            return None
            
        except Exception as e:
            print(f"⚠️ Error getting original URL: {e}")
            return None
    
    def download_image(self, url, save_path):
        """Download an image from URL"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            with open(save_path, 'wb') as f:
                f.write(response.content)
            
            return True
            
        except Exception as e:
            print(f"❌ Error downloading {url}: {e}")
            return False
    
    def download_images(self, save_directory):
        """Download all found images"""
        if not os.path.exists(save_directory):
            os.makedirs(save_directory)
        
        image_urls = self.search_images()
        
        if not image_urls:
            print("❌ No images found to download")
            return
        
        print(f"📥 Starting download of {len(image_urls)} images...")
        
        success_count = 0
        for i, url in enumerate(image_urls):
            try:
                # Generate filename
                parsed_url = urlparse(url)
                filename = f"image_{i+1}_{os.path.basename(parsed_url.path)}"
                if not filename.endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')):
                    filename += '.jpg'
                
                save_path = os.path.join(save_directory, filename)
                
                if self.download_image(url, save_path):
                    success_count += 1
                    print(f"✅ Downloaded: {filename}")
                else:
                    print(f"❌ Failed to download: {filename}")
                
                time.sleep(1)  # Be respectful to the server
                
            except Exception as e:
                print(f"❌ Error processing image {i+1}: {e}")
        
        print(f"🎉 Successfully downloaded {success_count}/{len(image_urls)} images")
    
    def close(self):
        """Close the driver"""
        if self.driver:
            self.driver.quit()

def main():
    """Main function to test the Google Image Downloader"""
    print("🚀 Starting Google Images Downloader Test")
    print("=" * 50)
    
    # Test parameters
    search_query = "Alan Wake"
    num_images = 5
    save_directory = "test_downloaded_images"
    
    downloader = None
    try:
        # Create downloader instance
        downloader = GoogleImageDownloader(search_query, num_images)
        
        # Download images
        downloader.download_images(save_directory)
        
        print("=" * 50)
        print("✅ Test completed successfully!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        
    finally:
        if downloader:
            downloader.close()

if __name__ == "__main__":
    main()
