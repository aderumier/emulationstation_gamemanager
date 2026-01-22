#!/usr/bin/env python3
"""
Test script to retrieve PDF from amiga.abime.net using Selenium
Tests two approaches:
1. Direct PDF download
2. Visit game page first to pass challenge, then download PDF with cookies
"""

import os
import sys
import time
import base64
import logging
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import requests

# Suppress Selenium/Chrome logging
logging.getLogger('selenium').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)
logging.getLogger('chromedriver').setLevel(logging.WARNING)

def init_selenium_driver():
    """Initialize Selenium Chrome driver"""
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    chrome_options.add_argument('--log-level=3')
    chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        return driver
    except Exception as e:
        print(f"Failed to initialize Chrome driver: {e}")
        return None

def test_direct_pdf_download(pdf_url):
    """Test 1: Try to download PDF directly"""
    print("\n" + "="*80)
    print("TEST 1: Direct PDF Download")
    print("="*80)
    
    driver = init_selenium_driver()
    if not driver:
        print("❌ Failed to initialize driver")
        return False
    
    try:
        print(f"Navigating to: {pdf_url}")
        driver.get(pdf_url)
        time.sleep(5)
        
        # Check for bot protection
        page_source = driver.page_source
        current_url = driver.current_url
        
        print(f"Current URL: {current_url}")
        print(f"Page source length: {len(page_source)}")
        
        if "Making sure you're not a bot" in page_source or "anubis" in page_source.lower():
            print("⚠️  Bot protection detected, waiting for challenge...")
            for i in range(30):
                time.sleep(1)
                page_source = driver.page_source
                if "Making sure you're not a bot" not in page_source and "anubis" not in page_source.lower():
                    print(f"✅ Challenge completed after {i+1} seconds")
                    time.sleep(3)
                    break
            else:
                print("❌ Challenge did not complete after 30 seconds")
                return False
        
        # Try browser fetch API
        print("\nAttempting browser fetch API...")
        pdf_base64 = driver.execute_async_script("""
            var callback = arguments[arguments.length - 1];
            fetch(arguments[0], {
                credentials: 'include',
                headers: {
                    'Accept': 'application/pdf'
                }
            })
            .then(response => {
                const contentType = response.headers.get('content-type') || '';
                const contentTypeLower = contentType.toLowerCase();
                
                console.log('Content-Type:', contentType);
                console.log('Status:', response.status);
                
                if (contentTypeLower.includes('text/html') || 
                    contentTypeLower.includes('text/plain') ||
                    contentTypeLower.includes('application/xhtml')) {
                    return response.text().then(text => {
                        console.log('Got HTML content, first 500 chars:', text.substring(0, 500));
                        throw new Error('Invalid content-type: ' + contentType + ' (expected PDF)');
                    });
                }
                
                if (!contentTypeLower.includes('pdf') && 
                    !contentTypeLower.includes('application/octet-stream') &&
                    !contentTypeLower.includes('application/pdf')) {
                    return response.clone().text().then(text => {
                        if (text.trim().toLowerCase().startsWith('<!doctype') || 
                            text.trim().toLowerCase().startsWith('<html') ||
                            text.includes('Making sure you') ||
                            text.includes('anubis')) {
                            throw new Error('Bot protection HTML detected (content-type: ' + contentType + ')');
                        }
                        throw new Error('Unknown content-type: ' + contentType + ' (expected PDF)');
                    });
                }
                
                return response.arrayBuffer();
            })
            .then(buffer => {
                const bytes = new Uint8Array(buffer);
                console.log('Response size:', bytes.length);
                
                if (bytes.length < 4) {
                    throw new Error('Response too short to be a PDF');
                }
                const header = String.fromCharCode(bytes[0], bytes[1], bytes[2], bytes[3]);
                console.log('First 4 bytes:', header);
                
                if (header !== '%PDF') {
                    const preview = String.fromCharCode.apply(null, Array.from(bytes.slice(0, 100)));
                    console.log('First 100 chars:', preview);
                    throw new Error('Response does not start with %PDF header (got: ' + header + ')');
                }
                
                let binary = '';
                for (let i = 0; i < bytes.length; i++) {
                    binary += String.fromCharCode(bytes[i]);
                }
                callback(btoa(binary));
            })
            .catch(error => {
                console.error('Fetch error:', error);
                callback('ERROR: ' + error.message);
            });
        """, pdf_url)
        
        if pdf_base64 and not pdf_base64.startswith('ERROR:'):
            pdf_content = base64.b64decode(pdf_base64)
            print(f"✅ Successfully retrieved PDF via browser fetch: {len(pdf_content)} bytes")
            print(f"First 20 bytes: {pdf_content[:20]}")
            
            # Save to file
            output_path = "test_direct_pdf.pdf"
            with open(output_path, 'wb') as f:
                f.write(pdf_content)
            print(f"✅ Saved to: {output_path}")
            return True
        elif pdf_base64:
            print(f"❌ Browser fetch returned error: {pdf_base64}")
            return False
        else:
            print("❌ Browser fetch returned no data")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        driver.quit()

def test_with_game_page_first(pdf_url, game_url):
    """Test 2: Visit game page first to pass challenge, then download PDF"""
    print("\n" + "="*80)
    print("TEST 2: Visit Game Page First, Then Download PDF")
    print("="*80)
    
    driver = init_selenium_driver()
    if not driver:
        print("❌ Failed to initialize driver")
        return False
    
    try:
        # Step 1: Visit game page to pass challenge
        print(f"\nStep 1: Visiting game page to pass challenge: {game_url}")
        driver.get(game_url)
        time.sleep(5)
        
        page_source = driver.page_source
        print(f"Page source length: {len(page_source)}")
        
        if "Making sure you're not a bot" in page_source or "anubis" in page_source.lower():
            print("⚠️  Bot protection detected on game page, waiting for challenge...")
            for i in range(30):
                time.sleep(1)
                page_source = driver.page_source
                if "Making sure you're not a bot" not in page_source and "anubis" not in page_source.lower():
                    print(f"✅ Challenge completed after {i+1} seconds")
                    time.sleep(3)
                    break
            else:
                print("❌ Challenge did not complete after 30 seconds")
                return False
        
        # Get cookies after challenge
        cookies = driver.get_cookies()
        print(f"\n✅ Got {len(cookies)} cookies after challenge")
        for cookie in cookies:
            print(f"  - {cookie['name']}: {cookie['value'][:50]}...")
        
        # Step 2: Navigate to PDF URL
        print(f"\nStep 2: Navigating to PDF URL: {pdf_url}")
        driver.get(pdf_url)
        time.sleep(5)
        
        page_source = driver.page_source
        current_url = driver.current_url
        print(f"Current URL: {current_url}")
        print(f"Page source length: {len(page_source)}")
        
        if "Making sure you're not a bot" in page_source or "anubis" in page_source.lower():
            print("⚠️  Bot protection detected on PDF page, waiting for challenge...")
            for i in range(30):
                time.sleep(1)
                page_source = driver.page_source
                if "Making sure you're not a bot" not in page_source and "anubis" not in page_source.lower():
                    print(f"✅ Challenge completed after {i+1} seconds")
                    time.sleep(3)
                    break
            else:
                print("❌ Challenge did not complete after 30 seconds")
                return False
        
        # Step 3: Try browser fetch API
        print("\nStep 3: Attempting browser fetch API...")
        pdf_base64 = driver.execute_async_script("""
            var callback = arguments[arguments.length - 1];
            fetch(arguments[0], {
                credentials: 'include',
                headers: {
                    'Accept': 'application/pdf'
                }
            })
            .then(response => {
                const contentType = response.headers.get('content-type') || '';
                const contentTypeLower = contentType.toLowerCase();
                
                console.log('Content-Type:', contentType);
                console.log('Status:', response.status);
                
                if (contentTypeLower.includes('text/html') || 
                    contentTypeLower.includes('text/plain') ||
                    contentTypeLower.includes('application/xhtml')) {
                    return response.text().then(text => {
                        console.log('Got HTML content, first 500 chars:', text.substring(0, 500));
                        throw new Error('Invalid content-type: ' + contentType + ' (expected PDF)');
                    });
                }
                
                if (!contentTypeLower.includes('pdf') && 
                    !contentTypeLower.includes('application/octet-stream') &&
                    !contentTypeLower.includes('application/pdf')) {
                    return response.clone().text().then(text => {
                        if (text.trim().toLowerCase().startsWith('<!doctype') || 
                            text.trim().toLowerCase().startsWith('<html') ||
                            text.includes('Making sure you') ||
                            text.includes('anubis')) {
                            throw new Error('Bot protection HTML detected (content-type: ' + contentType + ')');
                        }
                        throw new Error('Unknown content-type: ' + contentType + ' (expected PDF)');
                    });
                }
                
                return response.arrayBuffer();
            })
            .then(buffer => {
                const bytes = new Uint8Array(buffer);
                console.log('Response size:', bytes.length);
                
                if (bytes.length < 4) {
                    throw new Error('Response too short to be a PDF');
                }
                const header = String.fromCharCode(bytes[0], bytes[1], bytes[2], bytes[3]);
                console.log('First 4 bytes:', header);
                
                if (header !== '%PDF') {
                    const preview = String.fromCharCode.apply(null, Array.from(bytes.slice(0, 100)));
                    console.log('First 100 chars:', preview);
                    throw new Error('Response does not start with %PDF header (got: ' + header + ')');
                }
                
                let binary = '';
                for (let i = 0; i < bytes.length; i++) {
                    binary += String.fromCharCode(bytes[i]);
                }
                callback(btoa(binary));
            })
            .catch(error => {
                console.error('Fetch error:', error);
                callback('ERROR: ' + error.message);
            });
        """, pdf_url)
        
        if pdf_base64 and not pdf_base64.startswith('ERROR:'):
            pdf_content = base64.b64decode(pdf_base64)
            print(f"✅ Successfully retrieved PDF via browser fetch: {len(pdf_content)} bytes")
            print(f"First 20 bytes: {pdf_content[:20]}")
            
            # Save to file
            output_path = "test_with_game_page.pdf"
            with open(output_path, 'wb') as f:
                f.write(pdf_content)
            print(f"✅ Saved to: {output_path}")
            return True
        elif pdf_base64:
            print(f"❌ Browser fetch returned error: {pdf_base64}")
            return False
        else:
            print("❌ Browser fetch returned no data")
            return False
        
        # Step 4: Also try with requests using cookies
        print("\nStep 4: Trying requests with cookies...")
        session = requests.Session()
        for cookie in cookies:
            if 'domain' in cookie and cookie['domain']:
                session.cookies.set(cookie['name'], cookie['value'], domain=cookie['domain'])
            else:
                session.cookies.set(cookie['name'], cookie['value'])
        
        session.headers.update({
            'User-Agent': driver.execute_script("return navigator.userAgent;"),
            'Accept': 'application/pdf',
            'Referer': game_url,
            'Origin': 'https://amiga.abime.net'
        })
        
        response = session.get(pdf_url, timeout=30)
        print(f"Response status: {response.status_code}")
        print(f"Response size: {len(response.content)} bytes")
        print(f"Content-Type: {response.headers.get('Content-Type', 'N/A')}")
        
        if response.status_code == 200:
            if len(response.content) > 4 and response.content[:4] == b'%PDF':
                print(f"✅ Successfully retrieved PDF via requests: {len(response.content)} bytes")
                output_path = "test_requests_pdf.pdf"
                with open(output_path, 'wb') as f:
                    f.write(response.content)
                print(f"✅ Saved to: {output_path}")
                return True
            else:
                print(f"❌ Response is not a PDF. First 200 bytes: {response.content[:200]}")
                return False
        else:
            print(f"❌ HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        driver.quit()

def main():
    pdf_url = "https://amiga.abime.net/manual/1501-1600/1533_manual0.pdf?v=1854"
    game_url = "https://amiga.abime.net/games/view/turrican"
    
    print("Testing PDF download from amiga.abime.net")
    print(f"PDF URL: {pdf_url}")
    print(f"Game URL: {game_url}")
    
    # Test 1: Direct download
    result1 = test_direct_pdf_download(pdf_url)
    
    # Test 2: Visit game page first
    result2 = test_with_game_page_first(pdf_url, game_url)
    
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"Test 1 (Direct): {'✅ PASSED' if result1 else '❌ FAILED'}")
    print(f"Test 2 (Game Page First): {'✅ PASSED' if result2 else '❌ FAILED'}")

if __name__ == "__main__":
    main()
