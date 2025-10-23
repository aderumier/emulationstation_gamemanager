#!/usr/bin/env python3
"""
Test script implementing approach similar to pruthvik-sheth/google-images-scraper
Based on: https://github.com/pruthvik-sheth/google-images-scraper/blob/main/scraping/scraper.py
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

class PruthvikStyleGoogleImageScraper:
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
        
        # Random user agent
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
    
    def search_and_download_images(self, search_queries, output_directory="downloaded_images", max_images_per_query=10):
        """
        Search and download images for multiple queries (similar to pruthvik-sheth approach)
        """
        print(f"🔍 Starting image search for {len(search_queries)} queries")
        print(f"📁 Output directory: {output_directory}")
        
        # Create output directory
        if not os.path.exists(output_directory):
            os.makedirs(output_directory)
        
        total_downloaded = 0
        results_summary = {}
        
        for i, query in enumerate(search_queries):
            print(f"\n{'='*60}")
            print(f"🔍 Processing query {i+1}/{len(search_queries)}: '{query}'")
            print(f"{'='*60}")
            
            try:
                # Search for images without aspect ratio filter first
                images = self.search_images(query, max_images_per_query, aspect_ratio="any")
                
                if not images:
                    print(f"❌ No images found for query: {query}")
                    results_summary[query] = {"found": 0, "downloaded": 0}
                    continue
                
                print(f"📸 Found {len(images)} images for query: {query}")
                
                # Create query-specific directory
                query_dir = os.path.join(output_directory, self.sanitize_filename(query))
                if not os.path.exists(query_dir):
                    os.makedirs(query_dir)
                
                # Download images
                downloaded_count = self.download_images(images, query_dir, query)
                
                results_summary[query] = {
                    "found": len(images),
                    "downloaded": downloaded_count
                }
                
                total_downloaded += downloaded_count
                print(f"✅ Downloaded {downloaded_count}/{len(images)} images for '{query}'")
                
                # Be respectful to the server
                time.sleep(2)
                
            except Exception as e:
                print(f"❌ Error processing query '{query}': {e}")
                results_summary[query] = {"found": 0, "downloaded": 0, "error": str(e)}
                continue
        
        # Print summary
        print(f"\n{'='*60}")
        print(f"📊 FINAL SUMMARY")
        print(f"{'='*60}")
        print(f"Total queries processed: {len(search_queries)}")
        print(f"Total images downloaded: {total_downloaded}")
        print(f"Output directory: {output_directory}")
        
        print(f"\n📋 Detailed Results:")
        for query, stats in results_summary.items():
            if "error" in stats:
                print(f"  ❌ {query}: ERROR - {stats['error']}")
            else:
                print(f"  ✅ {query}: {stats['downloaded']}/{stats['found']} images")
        
        return results_summary
    
    def search_images(self, query, max_images=10, aspect_ratio="landscape"):
        """Search for images using Google Images with aspect ratio filtering"""
        print(f"🔍 Searching for: {query} (aspect ratio: {aspect_ratio})")
        
        # Construct search URL with aspect ratio parameter
        # imgar:x = landscape, imgar:s = square, imgar:t = tall, imgar:w = wide
        aspect_map = {
            "landscape": "w",  # wide
            "square": "s",     # square  
            "tall": "t",       # tall
            "any": ""          # no filter
        }
        
        aspect_param = aspect_map.get(aspect_ratio, "")
        if aspect_param:
            search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}&tbm=isch&tbs=imgar:{aspect_param}"
        else:
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
                    
                    # Apply filtering (similar to our improved approach)
                    if not self.filter_unwanted_images(src, width, height):
                        continue
                    
                    # Extract metadata
                    metadata = self.extract_image_metadata(src, width, height)
                    
                    # Try to get full-size URL for Base64 images
                    full_size_url = src
                    if src.startswith("data:image/"):
                        print(f"🔍 Attempting to get full-size URL for Base64 image {processed_count + 1}")
                        full_size_url = self.get_full_size_url(img, processed_count + 1)
                        if full_size_url and full_size_url != src:
                            print(f"✅ Found full-size URL: {full_size_url[:50]}...")
                        else:
                            print(f"⚠️ Using Base64 thumbnail as fallback")
                    
                    # Add to results
                    results.append({
                        "index": processed_count + 1,
                        "url": full_size_url,
                        "original_url": src,
                        "title": f"{query} - Image {processed_count + 1}",
                        "format": metadata["format"],
                        "width": width,
                        "height": height,
                        "size_estimate": metadata["size_estimate"],
                        "is_base64": metadata["is_base64"],
                        "source": "Google Images",
                        "query": query
                    })
                    
                    processed_count += 1
                    print(f"✅ Added image {processed_count}: {width}x{height} ({metadata['format']})")
                    
                    if processed_count >= max_images:
                        break
                        
                except Exception as e:
                    print(f"⚠️ Error processing image {i}: {e}")
                    continue
            
            print(f"🎯 Successfully processed {len(results)} images for '{query}'")
            return results
            
        except Exception as e:
            print(f"❌ Error during search: {e}")
            return []
    
    def get_full_size_url(self, img_element, image_index):
        """Try to get full-size URL by clicking on the image"""
        try:
            # Scroll to make sure the image is visible
            self.driver.execute_script("arguments[0].scrollIntoView(true);", img_element)
            time.sleep(1)
            
            # Try to click on the image or its container
            try:
                # First try clicking the image directly
                img_element.click()
                time.sleep(2)
            except:
                # If direct click fails, try clicking the parent container
                try:
                    parent = img_element.find_element(By.XPATH, "./..")
                    parent.click()
                    time.sleep(2)
                except:
                    print(f"⚠️ Could not click image {image_index}")
                    return None
            
            # Look for full-size image in the page
            full_size_imgs = self.driver.find_elements(By.CSS_SELECTOR, "img[src*='http']")
            
            for full_img in full_size_imgs:
                src = full_img.get_attribute("src")
                if src and src.startswith("http") and not any(domain in src for domain in ["googleusercontent.com", "gstatic.com"]):
                    # Check if this looks like a full-size image
                    try:
                        width_attr = full_img.get_attribute("width")
                        height_attr = full_img.get_attribute("height")
                        if width_attr and height_attr:
                            width = int(width_attr)
                            height = int(height_attr)
                            if width > 400 and height > 300:  # Reasonable full-size dimensions
                                print(f"✅ Found full-size image: {width}x{height}")
                                return src
                    except:
                        continue
            
            # If no full-size image found, try to extract from imgres URLs
            current_url = self.driver.current_url
            if "imgres" in current_url:
                parsed_url = urlparse(current_url)
                query_params = parse_qs(parsed_url.query)
                if 'imgurl' in query_params:
                    imgurl = query_params['imgurl'][0]
                    if not any(domain in imgurl for domain in ["googleusercontent.com", "encrypted-tbn", "gstatic.com"]):
                        print(f"✅ Found imgurl parameter: {imgurl[:50]}...")
                        return imgurl
            
            return None
            
        except Exception as e:
            print(f"⚠️ Error getting full-size URL for image {image_index}: {e}")
            return None
    
    def filter_unwanted_images(self, src, width=None, height=None):
        """Filter out unwanted images with stricter quality requirements"""
        if not src:
            return False
        
        # Skip data URLs that are too small
        if src.startswith("data:image/"):
            if width and height:
                # Reasonable filtering for better quality images
                if width < 200 or height < 150:
                    print(f"🔍 Skipping small image: {width}x{height}")
                    return False
                # Skip very wide or very tall images (likely banners/logos)
                if width > height * 5 or height > width * 5:
                    print(f"🔍 Skipping banner/logo: {width}x{height}")
                    return False
                # Prefer landscape images but allow some portrait
                if height > width * 2:
                    print(f"🔍 Skipping tall portrait image: {width}x{height}")
                    return False
            return True
        
        # Skip Google's own images
        if any(domain in src for domain in ["googleusercontent.com", "gstatic.com", "google.com"]):
            return False
        
        # Skip common unwanted patterns
        unwanted_patterns = [
            "logo", "icon", "avatar", "thumbnail", "favicon",
            "button", "banner", "ad", "advertisement", "sprite"
        ]
        
        src_lower = src.lower()
        for pattern in unwanted_patterns:
            if pattern in src_lower:
                return False
        
        return True
    
    def extract_image_metadata(self, src, width=None, height=None):
        """Extract metadata from image URL"""
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
    
    def download_images(self, images, save_directory, query):
        """Download images from results"""
        downloaded_count = 0
        
        for result in images:
            try:
                src = result["url"]
                format_ext = result["format"] or "jpg"
                filename = f"{self.sanitize_filename(query)}_image_{result['index']}_{result['width']}x{result['height']}.{format_ext}"
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
        
        return downloaded_count
    
    def sanitize_filename(self, filename):
        """Sanitize filename for filesystem"""
        # Remove or replace invalid characters
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        
        # Limit length
        if len(filename) > 100:
            filename = filename[:100]
        
        return filename.strip()
    
    def close(self):
        """Close the driver"""
        if self.driver:
            self.driver.quit()

def main():
    """Main function to test Pruthvik-style approach"""
    print("🚀 Starting Pruthvik-Style Google Images Scraper Test")
    print("=" * 70)
    
    scraper = None
    try:
        scraper = PruthvikStyleGoogleImageScraper()
        
        # Test parameters (similar to pruthvik-sheth approach with multiple queries)
        search_queries = [
            "Alan Wake",
            "Super Mario Bros",
            "The Legend of Zelda"
        ]
        output_directory = "pruthvik_landscape_images"
        max_images_per_query = 10  # Search more images to find better quality ones
        
        # Search and download images
        results = scraper.search_and_download_images(
            search_queries, 
            output_directory, 
            max_images_per_query
        )
        
        print("=" * 70)
        print("✅ Test completed successfully!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        
    finally:
        if scraper:
            scraper.close()

if __name__ == "__main__":
    main()
