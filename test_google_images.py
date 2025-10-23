#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for Google Images scraping using the actual functions from app.py
"""

import os
import sys
import time
import requests

# Add the current directory to the path so we can import from app.py
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the actual functions from app.py
from app import search_google_images, download_google_image

def test_google_images():
    """Test the actual Google Images functions from app.py"""
    print("🔧 DEBUG: Testing Google Images functions from app.py")
    print("=" * 50)
    
    # Test parameters
    search_key = "Alan Wake"
    aspect_ratio = "landscape"
    
    # Create test directory
    test_dir = "test_images"
    if not os.path.exists(test_dir):
        os.makedirs(test_dir)
    
    # Test 1: Search for images
    print(f"🔧 DEBUG: Testing search for '{search_key}' with aspect ratio '{aspect_ratio}'...")
    try:
        images = search_google_images(search_key, aspect_ratio)
        print(f"🔧 DEBUG: Search returned {len(images)} images")
        
        if not images:
            print("❌ No images found!")
            return
        
        # Show some details about the found images
        for i, img in enumerate(images[:3]):
            print(f"  {i+1}: {img.get('title', 'No title')} - {img.get('url', 'No URL')[:50]}...")
        
        # Test 2: Try to download the first image
        if images:
            first_image = images[0]
            print(f"\n🔧 DEBUG: Testing download of first image...")
            
            # Use the actual download function from app.py
            result = download_google_image(
                image_url=first_image['url'],
                game_name=search_key,
                system_name="test_system",
                media_type="fanart"
            )
            
            if result.get('success'):
                print(f"✅ Successfully downloaded: {result.get('filename')}")
                print(f"   File path: {result.get('file_path')}")
                print(f"   Gamelist updated: {result.get('gamelist_updated')}")
            else:
                print(f"❌ Download failed: {result.get('error')}")
        
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n🔧 DEBUG: Test completed!")

if __name__ == "__main__":
    test_google_images()
