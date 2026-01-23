#!/usr/bin/env python3
"""
Test script for Selenium image download from amiga.abime.net
Tests downloading an image with Anubis bot protection
"""

import sys
import os
import time
from urllib.parse import urlparse, urljoin

# Add parent directory to path to import app functions
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.common.by import By
    HAS_SELENIUM = True
except ImportError:
    print("❌ Selenium not installed. Install with: pip install selenium")
    HAS_SELENIUM = False
    sys.exit(1)

import requests

def test_selenium_download(url: str, output_path: str = "test_image.png"):
    """Test downloading an image using Selenium"""
    
    if not HAS_SELENIUM:
        print("❌ Selenium not available")
        return False
    
    print(f"🧪 Testing Selenium download for: {url}")
    print("=" * 80)
    
    # Initialize Selenium driver
    try:
        options = Options()
        # Don't use headless mode for testing - we want to see what's happening
        # options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36')
        
        print("📱 Initializing Chrome WebDriver...")
        driver = webdriver.Chrome(options=options)
        driver.set_page_load_timeout(60)
        print("✅ WebDriver initialized")
    except Exception as e:
        print(f"❌ Failed to initialize Selenium: {e}")
        return False
    
    try:
        base_url = "https://amiga.abime.net"
        
        # Step 1: Visit main site first to get initial cookies
        print(f"\n📄 Step 1: Visiting main site: {base_url}")
        driver.get(base_url)
        
        # Wait for page to load
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
        except:
            time.sleep(2)
        
        page_source = driver.page_source
        if "Making sure you're not a bot" in page_source:
            print("⏳ Bot protection detected on main site, waiting...")
            for i in range(30):
                time.sleep(1)
                page_source = driver.page_source
                if "Making sure you're not a bot" not in page_source:
                    print(f"✅ Bot protection passed on main site after {i+1} seconds")
                    break
                if i % 5 == 0:
                    print(f"   Still waiting... ({i+1}/30)")
            else:
                print("❌ Bot challenge did not complete on main site")
                return False
        else:
            print("✅ No bot protection on main site")
        
        time.sleep(2)
        
        # Get cookies after main site visit
        cookies_after_main = driver.get_cookies()
        print(f"🍪 Got {len(cookies_after_main)} cookies from main site")
        for cookie in cookies_after_main[:3]:  # Show first 3
            print(f"   - {cookie['name']}: {cookie['value'][:50]}...")
        
        # Step 2: Navigate to the image URL
        print(f"\n📄 Step 2: Navigating to image URL: {url}")
        driver.get(url)
        
        # Wait for page to load
        try:
            WebDriverWait(driver, 10).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
        except:
            time.sleep(2)
        
        # Check current URL and page source
        current_url = driver.current_url
        print(f"📍 Current URL: {current_url}")
        page_source = driver.page_source[:500]  # First 500 chars
        print(f"📄 Page source preview: {page_source[:200]}...")
        
        # Check if we hit bot protection
        if "Making sure you're not a bot" in driver.page_source:
            print("⏳ Bot protection detected on image URL, waiting for challenge...")
            challenge_start = time.time()
            for i in range(60):
                time.sleep(1)
                current_url = driver.current_url
                page_source = driver.page_source
                
                # Check if challenge completed
                if "Making sure you're not a bot" not in page_source:
                    # Check if it's actually an image now
                    is_html = "<!doctype" in page_source.lower() or "<html" in page_source.lower()
                    if not is_html or len(page_source) < 1000:
                        elapsed = time.time() - challenge_start
                        print(f"✅ Bot challenge completed after {elapsed:.1f} seconds")
                        print(f"   Page source length: {len(page_source)}")
                        print(f"   Is HTML: {is_html}")
                        break
                
                if i % 5 == 0:
                    print(f"   Still waiting... ({i+1}/60 seconds)")
            else:
                print("❌ Bot challenge did not complete within 60 seconds")
                print(f"   Final page source length: {len(driver.page_source)}")
                print(f"   Still contains 'Making sure you're not a bot': {'Making sure you\'re not a bot' in driver.page_source}")
                return False
        else:
            print("✅ No bot protection detected on image URL")
        
        time.sleep(2)
        
        # Step 3: Get final cookies
        cookies_after_image = driver.get_cookies()
        print(f"\n🍪 Got {len(cookies_after_image)} cookies after image URL visit")
        for cookie in cookies_after_image[:5]:  # Show first 5
            print(f"   - {cookie['name']}: {cookie['value'][:50]}...")
        
        # Step 3: Try to extract image directly from Selenium
        print(f"\n📥 Step 3: Extracting image from Selenium...")
        
        # Method 1: Try to find img element and get its src
        try:
            img_elements = driver.find_elements(By.TAG_NAME, "img")
            print(f"   Found {len(img_elements)} img elements")
            for i, img in enumerate(img_elements):
                img_src = img.get_attribute("src")
                print(f"   img[{i}] src: {img_src[:100] if img_src else 'None'}...")
                if img_src and img_src.startswith("data:image"):
                    # Data URL - extract directly
                    import base64
                    print(f"   Found data URL image!")
                    header, data = img_src.split(",", 1)
                    image_data = base64.b64decode(data)
                    with open(output_path, 'wb') as f:
                        f.write(image_data)
                    print(f"✅ Successfully extracted image from data URL")
                    print(f"   File size: {len(image_data)} bytes")
                    return True
        except Exception as e:
            print(f"   Error finding img elements: {e}")
        
        # Method 2: Try to get the image via JavaScript (if it's loaded in the page)
        try:
            # Check if there's an image loaded in the page
            img_data_url = driver.execute_script("""
                var img = document.querySelector('img');
                if (img && img.complete && img.naturalWidth > 0) {
                    var canvas = document.createElement('canvas');
                    canvas.width = img.naturalWidth;
                    canvas.height = img.naturalHeight;
                    var ctx = canvas.getContext('2d');
                    ctx.drawImage(img, 0, 0);
                    return canvas.toDataURL('image/png');
                }
                return null;
            """)
            if img_data_url:
                print(f"   Found image via canvas!")
                import base64
                header, data = img_data_url.split(",", 1)
                image_data = base64.b64decode(data)
                with open(output_path, 'wb') as f:
                    f.write(image_data)
                print(f"✅ Successfully extracted image via canvas")
                print(f"   File size: {len(image_data)} bytes")
                return True
        except Exception as e:
            print(f"   Error extracting via canvas: {e}")
        
        # Method 3: Try to get the actual image URL from the page
        try:
            # The page might have the image URL somewhere
            actual_img_url = driver.execute_script("""
                // Try to find the actual image source
                var img = document.querySelector('img');
                if (img) return img.src;
                // Or check if there's a link to the image
                var link = document.querySelector('link[rel="preload"][as="image"]');
                if (link) return link.href;
                return null;
            """)
            if actual_img_url and actual_img_url.startswith("http"):
                print(f"   Found actual image URL: {actual_img_url}")
                url = actual_img_url
        except Exception as e:
            print(f"   Error finding image URL: {e}")
        
        # Method 4: Fallback to requests with cookies (might still fail)
        print(f"\n📥 Step 4: Trying requests with cookies (fallback)...")
        session = requests.Session()
        
        # Set all cookies
        for cookie in cookies_after_image:
            if 'domain' in cookie and cookie['domain']:
                session.cookies.set(cookie['name'], cookie['value'], domain=cookie['domain'])
            else:
                session.cookies.set(cookie['name'], cookie['value'])
        
        # Set headers
        user_agent = driver.execute_script("return navigator.userAgent;")
        session.headers.update({
            'User-Agent': user_agent,
            'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': base_url,
            'Origin': base_url
        })
        
        print(f"   User-Agent: {user_agent[:80]}...")
        print(f"   Requesting: {url}")
        
        response = session.get(url, timeout=30, allow_redirects=True)
        
        print(f"\n📊 Response details:")
        print(f"   Status Code: {response.status_code}")
        print(f"   Content-Type: {response.headers.get('Content-Type', 'Not set')}")
        print(f"   Content-Length: {len(response.content)} bytes")
        
        # Check if it's HTML or image
        content_preview = response.content[:200].decode('utf-8', errors='ignore')
        is_html = content_preview.strip().lower().startswith('<!doctype') or \
                  content_preview.strip().lower().startswith('<html')
        
        print(f"   Is HTML: {is_html}")
        print(f"   Content preview: {content_preview[:100]}...")
        
        if response.status_code == 200 and not is_html:
            # Save the image
            with open(output_path, 'wb') as f:
                f.write(response.content)
            print(f"\n✅ Successfully downloaded image to: {output_path}")
            print(f"   File size: {len(response.content)} bytes")
            return True
        else:
            print(f"\n❌ Failed to download image via requests")
            if is_html:
                print(f"   Reason: Response is HTML (bot protection), not image")
            else:
                print(f"   Reason: HTTP {response.status_code}")
            return False
        
    except Exception as e:
        print(f"\n❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        print(f"\n🔒 Closing WebDriver...")
        driver.quit()
        print("✅ Test completed")

if __name__ == "__main__":
    test_url = "https://amiga.abime.net/screen/5101-5200/5154_screen0.png"
    output_file = "test_downloaded_image.png"
    
    print("=" * 80)
    print("Selenium Image Download Test")
    print("=" * 80)
    
    success = test_selenium_download(test_url, output_file)
    
    if success:
        print("\n✅ Test PASSED")
        sys.exit(0)
    else:
        print("\n❌ Test FAILED")
        sys.exit(1)
