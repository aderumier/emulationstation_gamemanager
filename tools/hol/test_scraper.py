#!/usr/bin/env python3
"""
Test script for HOL scraper
Tests parsing of a single game page: https://amiga.abime.net/games/view/turrican-ii-the-final-fight
"""

import json
import sys
import argparse
from scrapper import HOLScraper, HAS_CLOUDSCRAPER, HAS_SELENIUM

def test_single_game(use_selenium=False, cookies_file='cookies.txt'):
    """Test scraping a single game page"""
    scraper = HOLScraper(use_selenium=use_selenium, cookies_file=cookies_file)
    
    game_url = "https://amiga.abime.net/games/view/turrican-ii-the-final-fight"
    game_name = "Turrican II: The Final Fight"
    
    print(f"🧪 Testing HOL scraper with: {game_url}")
    print("=" * 80)
    
    # Fetch the page
    soup = scraper.get_page(game_url)
    if not soup:
        print("❌ Failed to fetch the page")
        return False
    
    # Check for bot protection
    if scraper._is_bot_protection_page(soup):
        print("❌ Bot protection page detected!")
        print("\n💡 To bypass bot protection, you need to either:")
        print("   1. Provide valid cookies from a browser session:")
        print("      - Open the site in your browser")
        print("      - Use a browser extension to export cookies (e.g., 'Get cookies.txt LOCALLY')")
        print("      - Save as cookies.txt in this directory")
        print("   2. Use Selenium (requires ChromeDriver):")
        print("      python test_scraper.py --selenium")
        print("   3. Install cloudscraper (already tried if available):")
        print("      pip install cloudscraper")
        return False
    
    print("✅ Page fetched successfully")
    
    # Extract game info
    game_entries = scraper.extract_game_info(soup, game_url, game_name)
    
    if not game_entries:
        print("❌ No game entries extracted")
        return False
    
    print(f"\n✅ Extracted {len(game_entries)} version(s):")
    print("=" * 80)
    
    for i, entry in enumerate(game_entries, 1):
        print(f"\n📦 Version {i}:")
        print("-" * 40)
        print(json.dumps(entry, indent=2, ensure_ascii=False))
    
    # Validate expected fields
    print("\n" + "=" * 80)
    print("🔍 Validation:")
    print("-" * 40)
    
    all_valid = True
    for entry in game_entries:
        gameid = entry.get('gameid')
        name = entry.get('name')
        
        print(f"\n  Entry: {gameid}")
        
        # Check required fields
        if not gameid:
            print("    ❌ Missing gameid")
            all_valid = False
        else:
            print(f"    ✅ gameid: {gameid}")
        
        if not name:
            print("    ❌ Missing name")
            all_valid = False
        else:
            print(f"    ✅ name: {name}")
        
        if entry.get('release_date'):
            print(f"    ✅ release_date: {entry['release_date']}")
        else:
            print("    ⚠️  No release_date found")
        
        if entry.get('publisher'):
            print(f"    ✅ publisher: {entry['publisher']}")
        else:
            print("    ⚠️  No publisher found")
        
        if entry.get('developer'):
            print(f"    ✅ developer: {entry['developer']}")
        else:
            print("    ⚠️  No developer found")
        
        if entry.get('titleshot'):
            print(f"    ✅ titleshot: {entry['titleshot'][:60]}...")
        else:
            print("    ⚠️  No titleshot found")
        
        if entry.get('screenshot'):
            print(f"    ✅ screenshot: {entry['screenshot'][:60]}...")
        else:
            print("    ⚠️  No screenshot found")
        
        if entry.get('description'):
            desc_preview = entry['description'][:100] + "..." if len(entry['description']) > 100 else entry['description']
            print(f"    ✅ description: {desc_preview}")
        else:
            print("    ⚠️  No description found")
    
    print("\n" + "=" * 80)
    if all_valid:
        print("✅ All validations passed!")
    else:
        print("⚠️  Some validations failed")
    
    return all_valid

def test_list_page(use_selenium=False, cookies_file='cookies.txt'):
    """Test scraping the game list page"""
    scraper = HOLScraper(use_selenium=use_selenium, cookies_file=cookies_file)
    
    list_url = "https://amiga.abime.net/games/list/?view=grid&page=1"
    
    print(f"\n🧪 Testing list page parsing: {list_url}")
    print("=" * 80)
    
    soup = scraper.get_page(list_url)
    if not soup:
        print("❌ Failed to fetch the list page")
        return False
    
    # Check for bot protection
    if scraper._is_bot_protection_page(soup):
        print("❌ Bot protection page detected!")
        return False
    
    print("✅ List page fetched successfully")
    
    game_data = scraper.get_game_links_from_page(soup)
    
    if not game_data:
        print("❌ No games found on list page")
        return False
    
    print(f"✅ Found {len(game_data)} games on page 1")
    print("\nFirst 5 games:")
    print("-" * 40)
    
    for i, (url, name) in enumerate(list(game_data.items())[:5], 1):
        print(f"  {i}. {name}")
        print(f"     URL: {url}")
    
    return True


def test_html_parsing():
    """Test HTML parsing with sample HTML (no network required)"""
    from bs4 import BeautifulSoup
    
    print("\n🧪 Testing HTML parsing with sample data")
    print("=" * 80)
    
    # Sample game card HTML
    game_card_html = '''
    <div class="gamecolumn_name col-12">
        <a href="/games/view/turrican"><h4 class="">Turrican</h4></a>
    </div>
    '''
    
    soup = BeautifulSoup(game_card_html, 'html.parser')
    scraper = HOLScraper()
    
    game_data = scraper.get_game_links_from_page(soup)
    
    if game_data:
        print(f"✅ Parsed game card: {list(game_data.items())[0]}")
        return True
    else:
        print("❌ Failed to parse game card")
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Test HOL scraper')
    parser.add_argument('--selenium', action='store_true', help='Use Selenium for browser automation')
    parser.add_argument('--cookies', type=str, default='cookies.txt', help='Path to cookies.txt file')
    parser.add_argument('--offline', action='store_true', help='Only run offline tests (HTML parsing)')
    
    args = parser.parse_args()
    
    print("🚀 HOL Scraper Test Suite")
    print("=" * 80)
    print(f"\n📦 Dependencies:")
    print(f"   cloudscraper: {'✅ Available' if HAS_CLOUDSCRAPER else '❌ Not installed (pip install cloudscraper)'}")
    print(f"   selenium: {'✅ Available' if HAS_SELENIUM else '❌ Not installed (pip install selenium)'}")
    print("")
    
    if args.offline:
        # Only run offline parsing tests
        parse_result = test_html_parsing()
        print("\n" + "=" * 80)
        print("📊 Test Summary:")
        print(f"  HTML parsing test: {'✅ PASS' if parse_result else '❌ FAIL'}")
        sys.exit(0 if parse_result else 1)
    
    # Test HTML parsing first (offline)
    parse_result = test_html_parsing()
    
    # Test single game
    game_result = test_single_game(use_selenium=args.selenium, cookies_file=args.cookies)
    
    print("\n")
    
    # Test list page
    list_result = test_list_page(use_selenium=args.selenium, cookies_file=args.cookies)
    
    print("\n" + "=" * 80)
    print("📊 Test Summary:")
    print(f"  HTML parsing test: {'✅ PASS' if parse_result else '❌ FAIL'}")
    print(f"  Single game test: {'✅ PASS' if game_result else '❌ FAIL'}")
    print(f"  List page test: {'✅ PASS' if list_result else '❌ FAIL'}")
    
    sys.exit(0 if (parse_result and game_result and list_result) else 1)
