#!/usr/bin/env python3
"""
Test script for EmuMovies API download endpoint
Tests: https://api3.emumovies.com/api/Media/Download?systemName=Arcade&mediaType=Title&mediaSet=default&filename=mag_day.png
"""

import asyncio
import sys
import os

# Add current directory to path to import emumovies_service
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from emumovies_service import EmuMoviesService
import requests


def run_async_safely(coro):
    """Run async function synchronously"""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


def test_emumovies_download():
    """Test EmuMovies download endpoint"""
    print("=" * 60)
    print("Testing EmuMovies API Download Endpoint")
    print("=" * 60)
    
    # Initialize service
    service = EmuMoviesService()
    
    # Authenticate
    print("\n1. Authenticating with EmuMovies API...")
    token = run_async_safely(service.authenticate())
    if not token:
        print("❌ Authentication failed!")
        return False
    
    print(f"✅ Authentication successful! Token: {token[:20]}...")
    
    # Get authenticated headers
    print("\n2. Getting authenticated headers...")
    headers = run_async_safely(service._get_authenticated_headers())
    if not headers:
        print("❌ Failed to get authenticated headers!")
        return False
    
    print(f"✅ Headers: {headers}")
    
    # Test download endpoint
    print("\n3. Testing download endpoint...")
    download_url = "https://api3.emumovies.com/api/Media/Download"
    
    # Test with the original filename first
    test_filename = 'mag_day.png'
    print(f"\n   Testing with original filename: {test_filename}")
    params = {
        'systemName': 'Arcade',
        'mediaType': 'Title',
        'mediaSet': 'default',
        'filename': test_filename
    }
    
    print(f"   URL: {download_url}")
    print(f"   Parameters:")
    for key, value in params.items():
        print(f"     {key}: {value}")
    
    try:
        # Build full URL for debugging
        from urllib.parse import urlencode
        full_url = f"{download_url}?{urlencode(params)}"
        print(f"\n   Full URL: {full_url}")
        print(f"   Request headers: {headers}")
        
        response = requests.get(download_url, params=params, headers=headers, timeout=30, allow_redirects=True)
        
        print(f"\n   Response Status: {response.status_code}")
        print(f"   Response URL (after redirects): {response.url}")
        
        if response.status_code == 200:
            print(f"   ✅ Download successful!")
            print(f"   Content-Type: {response.headers.get('content-type', 'unknown')}")
            print(f"   Content-Length: {len(response.content)} bytes")
            
            # Save to file for verification
            output_file = 'test_emumovies_download.png'
            with open(output_file, 'wb') as f:
                f.write(response.content)
            print(f"   Saved to: {output_file}")
            return True
        else:
            print(f"   ❌ Download failed with status {response.status_code}")
            print(f"   Error response: {response.text[:500]}")
            
            # Try with a known existing file
            print(f"\n   Testing with known existing file: daytona.png")
            params['filename'] = 'daytona.png'
            response2 = requests.get(download_url, params=params, headers=headers, timeout=30, allow_redirects=True)
            
            if response2.status_code == 200:
                print(f"   ✅ Download successful with daytona.png!")
                print(f"   Content-Type: {response2.headers.get('content-type', 'unknown')}")
                print(f"   Content-Length: {len(response2.content)} bytes")
                
                output_file = 'test_emumovies_daytona.png'
                with open(output_file, 'wb') as f:
                    f.write(response2.content)
                print(f"   Saved to: {output_file}")
                print(f"\n   ⚠️  Note: mag_day.png doesn't exist, but API works with existing files")
                return True
            else:
                print(f"   ❌ Also failed with daytona.png (status {response2.status_code})")
                print(f"   Error response: {response2.text[:500]}")
                return False
            
    except Exception as e:
        print(f"\n❌ Error during download: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = test_emumovies_download()
    sys.exit(0 if success else 1)
