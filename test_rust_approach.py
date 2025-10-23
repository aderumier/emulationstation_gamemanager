#!/usr/bin/env python3
"""
Test script implementing approach similar to seyli01/Google-Image-Scrapper
Based on: https://github.com/seyli01/Google-Image-Scrapper
"""

import requests
import os
import time
import json
import base64
import io
import random
import re
from urllib.parse import urlparse, parse_qs, unquote
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from PIL import Image

class RustStyleGoogleImageScraper:
    def __init__(self):
        self.driver = None
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/121.0'
        ]
        self.setup_driver()
    
    def setup_driver(self):
        """Setup Chrome driver with random user agent"""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        
        # Random user agent (like the Rust implementation)
        user_agent = random.choice(self.user_agents)
        chrome_options.add_argument(f"--user-agent={user_agent}")
        print(f"🔀 Using User-Agent: {user_agent[:50]}...")
        
        try:
            self.driver = webdriver.Remote(
                command_executor='http://localhost:4444/wd/hub',
                options=chrome_options
            )
            print("✅ Connected to Selenium Docker container")
        except Exception as e:
            print(f"❌ Failed to connect to Selenium Docker: {e}")
            raise Exception("Could not initialize WebDriver")
    
    def filter_unwanted_images(self, src, width=None, height=None):
        """Filter out unwanted images like thumbnails, icons, logos (Rust-style filtering)"""
        if not src:
            return False
        
        # Skip data URLs that are too small
        if src.startswith("data:image/"):
            if width and height:
                # Filter based on dimensions
                if width < 150 or height < 150:
                    return False
                # Skip very wide or very tall images (likely banners/logos)
                if width > height * 3 or height > width * 3:
                    return False
            return True
        
        # Skip Google's own images
        if any(domain in src for domain in ["googleusercontent.com", "gstatic.com", "google.com"]):
            return False
        
        # Skip common unwanted patterns
        unwanted_patterns = [
            "logo", "icon", "avatar", "thumbnail", "favicon",
            "button", "banner", "ad", "advertisement"
        ]
        
        src_lower = src.lower()
        for pattern in unwanted_patterns:
            if pattern in src_lower:
                return False
        
        return True
    
    def extract_image_metadata(self, src, width=None, height=None):
        """Extract metadata from image URL (similar to Rust implementation)"""
        metadata = {
            "url": src,
            "format": None,
            "width": width,
            "height": height,
            "size_estimate": None,
            "is_base64": src.startswith("data:image/") if src else False
        }
        
        if src:
            # Determine format
            if src.startswith("data:image/"):
                format_match = re.search(r'data:image/([^;]+)', src)
                if format_match:
                    metadata["format"] = format_match.group(1)
            else:
                parsed_url = urlparse(src)
                path = parsed_url.path.lower()
                if path.endswith(('.jpg', '.jpeg')):
                    metadata["format"] = "jpeg"
                elif path.endswith('.png'):
                    metadata["format"] = "png"
                elif path.endswith('.gif'):
                    metadata["format"] = "gif"
                elif path.endswith('.webp'):
                    metadata["format"] = "webp"
            
            # Estimate size for Base64 images
            if src.startswith("data:image/") and width and height:
                # Rough estimate: width * height * 3 bytes per pixel
                metadata["size_estimate"] = width * height * 3
        
        return metadata
    
    def search_images(self, query, max_results=20):
        """Search for images using Rust-style approach"""
        print(f"🔍 Searching for: {query}")
        
        # Construct search URL
        search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}&tbm=isch"
        print(f"🔗 Search URL: {search_url}")
        
        try:
            self.driver.get(search_url)
            time.sleep(5)
            
            # Wait for images to load
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "img"))
                )
                print("✅ Images loaded successfully")
            except TimeoutException:
                print("❌ Timeout waiting for images to load")
                return []
            
            # Find all image elements
            images = self.driver.find_elements(By.CSS_SELECTOR, "img")
            print(f"📸 Found {len(images)} image elements")
            
            results = []
            processed_count = 0
            
            for i, img in enumerate(images):
                try:
                    src = img.get_attribute("src")
                    if not src:
                        continue
                    
                    # Get dimensions for Base64 images
                    width, height = None, None
                    if src.startswith("data:image/"):
                        try:
                            header, data = src.split(',', 1)
                            image_data = base64.b64decode(data)
                            image = Image.open(io.BytesIO(image_data))
                            width, height = image.size
                        except Exception as e:
                            print(f"⚠️ Error getting dimensions for image {i}: {e}")
                            continue
                    
                    # Apply filtering (Rust-style)
                    if not self.filter_unwanted_images(src, width, height):
                        continue
                    
                    # Extract metadata
                    metadata = self.extract_image_metadata(src, width, height)
                    
                    # Add to results
                    results.append({
                        "index": processed_count + 1,
                        "url": src,
                        "title": f"Image {processed_count + 1}",
                        "format": metadata["format"],
                        "width": width,
                        "height": height,
                        "size_estimate": metadata["size_estimate"],
                        "is_base64": metadata["is_base64"],
                        "source": "Google Images"
                    })
                    
                    processed_count += 1
                    print(f"✅ Added image {processed_count}: {width}x{height} ({metadata['format']})")
                    
                    if processed_count >= max_results:
                        break
                        
                except Exception as e:
                    print(f"⚠️ Error processing image {i}: {e}")
                    continue
            
            print(f"🎯 Successfully processed {len(results)} images")
            return results
            
        except Exception as e:
            print(f"❌ Error during search: {e}")
            return []
    
    def save_results_json(self, results, filename="search_results.json"):
        """Save results in structured JSON format (like Rust implementation)"""
        output = {
            "query": "Alan Wake",
            "total_results": len(results),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "user_agent": self.driver.execute_script("return navigator.userAgent;"),
            "results": results
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Results saved to {filename}")
        return output
    
    def download_images(self, results, save_directory="downloaded_images"):
        """Download images from results"""
        if not os.path.exists(save_directory):
            os.makedirs(save_directory)
        
        downloaded_count = 0
        
        for result in results:
            try:
                src = result["url"]
                format_ext = result["format"] or "jpg"
                filename = f"image_{result['index']}_{result['width']}x{result['height']}.{format_ext}"
                save_path = os.path.join(save_directory, filename)
                
                if src.startswith("data:image/"):
                    # Handle Base64 images
                    header, data = src.split(',', 1)
                    image_data = base64.b64decode(data)
                    
                    with open(save_path, 'wb') as f:
                        f.write(image_data)
                    
                    print(f"✅ Downloaded Base64 image: {filename}")
                    downloaded_count += 1
                    
                elif src.startswith("http"):
                    # Handle HTTP images
                    headers = {
                        'User-Agent': random.choice(self.user_agents)
                    }
                    
                    response = requests.get(src, headers=headers, timeout=10)
                    response.raise_for_status()
                    
                    with open(save_path, 'wb') as f:
                        f.write(response.content)
                    
                    print(f"✅ Downloaded HTTP image: {filename}")
                    downloaded_count += 1
                
                time.sleep(1)  # Be respectful
                
            except Exception as e:
                print(f"❌ Error downloading image {result['index']}: {e}")
                continue
        
        print(f"🎉 Successfully downloaded {downloaded_count}/{len(results)} images")
        return downloaded_count
    
    def close(self):
        """Close the driver"""
        if self.driver:
            self.driver.quit()

def main():
    """Main function to test Rust-style approach"""
    print("🚀 Starting Rust-Style Google Images Scraper Test")
    print("=" * 60)
    
    scraper = None
    try:
        scraper = RustStyleGoogleImageScraper()
        
        # Test parameters
        query = "Alan Wake"
        max_results = 10
        
        # Search for images
        results = scraper.search_images(query, max_results)
        
        if results:
            # Save results as JSON
            json_output = scraper.save_results_json(results)
            
            # Download images
            scraper.download_images(results)
            
            print("\n📊 Summary:")
            print(f"  Query: {query}")
            print(f"  Total results: {len(results)}")
            print(f"  Base64 images: {sum(1 for r in results if r['is_base64'])}")
            print(f"  HTTP images: {sum(1 for r in results if not r['is_base64'])}")
            
            # Show format distribution
            formats = {}
            for result in results:
                fmt = result['format'] or 'unknown'
                formats[fmt] = formats.get(fmt, 0) + 1
            
            print(f"  Formats: {formats}")
            
        else:
            print("❌ No results found")
        
        print("=" * 60)
        print("✅ Test completed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        
    finally:
        if scraper:
            scraper.close()

if __name__ == "__main__":
    main()
