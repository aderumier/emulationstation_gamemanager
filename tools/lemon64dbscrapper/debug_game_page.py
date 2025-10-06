#!/usr/bin/env python3
"""
Debug script to examine the HTML structure of a specific game page
"""

import requests
from bs4 import BeautifulSoup
import re

def debug_game_page():
    """Debug the HTML structure of the 43: One Year After game page"""
    url = "https://www.lemon64.com/game/43-one-year-after"
    
    print(f"🔍 Debugging game page: {url}")
    
    # Set up session with realistic headers
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Cache-Control': 'max-age=0'
    })
    
    try:
        response = session.get(url, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        print("✅ Successfully loaded page")
        print(f"📄 Page title: {soup.title.string if soup.title else 'No title'}")
        
        # Look for game details section
        print("\n🔍 Looking for game details...")
        
        # Try to find the main content area
        main_content = soup.find('div', class_='game-details') or soup.find('div', class_='game-info') or soup.find('main')
        if main_content:
            print(f"📋 Found main content area: {main_content.name} with class: {main_content.get('class')}")
        else:
            print("❌ No main content area found")
        
        # Look for all spans that might contain game info
        print("\n🔍 Looking for spans with game information...")
        spans = soup.find_all('span')
        for i, span in enumerate(spans[:20]):  # Check first 20 spans
            text = span.get_text(strip=True)
            if text and len(text) > 2:
                print(f"  Span {i+1}: '{text}' (class: {span.get('class')})")
        
        # Look for divs that might contain game info
        print("\n🔍 Looking for divs with game information...")
        divs = soup.find_all('div', class_=re.compile(r'info|detail|game|meta'))
        for i, div in enumerate(divs[:15]):  # Check first 15 relevant divs
            text = div.get_text(strip=True)
            if text and len(text) > 5 and len(text) < 200:
                print(f"  Div {i+1}: '{text[:100]}...' (class: {div.get('class')})")
        
        # Look for specific patterns
        print("\n🔍 Looking for specific patterns...")
        
        # Look for "Publisher:" pattern
        publisher_patterns = [
            soup.find('span', string=re.compile(r'Publisher:', re.I)),
            soup.find('div', string=re.compile(r'Publisher:', re.I)),
            soup.find(text=re.compile(r'Publisher:', re.I))
        ]
        
        for i, pattern in enumerate(publisher_patterns):
            if pattern:
                print(f"  Publisher pattern {i+1}: {pattern}")
                if hasattr(pattern, 'parent'):
                    print(f"    Parent: {pattern.parent}")
                    print(f"    Next sibling: {pattern.next_sibling}")
        
        # Look for "Developer:" or similar patterns
        developer_patterns = [
            soup.find('span', string=re.compile(r'Developer:', re.I)),
            soup.find('div', string=re.compile(r'Developer:', re.I)),
            soup.find(text=re.compile(r'Developer:', re.I))
        ]
        
        for i, pattern in enumerate(developer_patterns):
            if pattern:
                print(f"  Developer pattern {i+1}: {pattern}")
                if hasattr(pattern, 'parent'):
                    print(f"    Parent: {pattern.parent}")
                    print(f"    Next sibling: {pattern.next_sibling}")
        
        # Look for "Players:" pattern
        players_patterns = [
            soup.find('span', string=re.compile(r'Players:', re.I)),
            soup.find('div', string=re.compile(r'Players:', re.I)),
            soup.find(text=re.compile(r'Players:', re.I))
        ]
        
        for i, pattern in enumerate(players_patterns):
            if pattern:
                print(f"  Players pattern {i+1}: {pattern}")
                if hasattr(pattern, 'parent'):
                    print(f"    Parent: {pattern.parent}")
                    print(f"    Next sibling: {pattern.next_sibling}")
        
        # Look for any table or structured data
        print("\n🔍 Looking for tables or structured data...")
        tables = soup.find_all('table')
        for i, table in enumerate(tables):
            print(f"  Table {i+1}: {len(table.find_all('tr'))} rows")
            rows = table.find_all('tr')[:5]  # First 5 rows
            for j, row in enumerate(rows):
                cells = row.find_all(['td', 'th'])
                if cells:
                    cell_texts = [cell.get_text(strip=True) for cell in cells]
                    print(f"    Row {j+1}: {cell_texts}")
        
        # Save HTML for manual inspection
        with open('debug_game_page.html', 'w', encoding='utf-8') as f:
            f.write(soup.prettify())
        print(f"\n💾 Full HTML saved to debug_game_page.html")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_game_page()








