#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug script to examine href attributes in Google Images
"""

import os
import sys
import time

# Add the current directory to the path so we can import from app.py
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the actual functions from app.py
from app import search_google_images

def debug_href_attributes():
    """Debug the href attributes of Google Images elements"""
    print("🔧 DEBUG: Debugging href attributes in Google Images")
    print("=" * 50)
    
    # Test parameters
    search_key = "Alan Wake"
    aspect_ratio = "landscape"
    
    # Test search
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
        
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n🔧 DEBUG: Debug completed!")

if __name__ == "__main__":
    debug_href_attributes()



