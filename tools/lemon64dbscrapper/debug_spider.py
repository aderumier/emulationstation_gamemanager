#!/usr/bin/env python3
"""
Debug script to test the Lemon64 spider and see how many games it finds
"""

import requests
from bs4 import BeautifulSoup
import re

def test_page_parsing():
    """Test parsing a single page to see how many games we can find"""
    print("🔍 Testing Lemon64 page parsing...")
    
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
        # Fetch the first page
        url = "https://www.lemon64.com/games/list.php?lineoffset=0"
        print(f"📄 Fetching: {url}")
        
        response = session.get(url, timeout=10)
        response.raise_for_status()
        
        print(f"✅ Successfully loaded page (Status: {response.status_code})")
        
        # Parse with BeautifulSoup
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Try different selectors to find game cards
        print("\n🔍 Testing different selectors:")
        
        # Selector 1: Exact match
        exact_cards = soup.find_all('div', class_='col-6 col-md-3 game-col game-col-4')
        print(f"1. Exact selector: {len(exact_cards)} cards")
        
        # Selector 2: Partial class match
        partial_cards = soup.find_all('div', class_=lambda x: x and 'game-col' in x)
        print(f"2. Partial 'game-col' match: {len(partial_cards)} cards")
        
        # Selector 3: ID pattern match
        id_cards = soup.find_all('div', id=lambda x: x and x.startswith('game-'))
        print(f"3. ID pattern 'game-*': {len(id_cards)} cards")
        
        # Selector 4: Any div with 'game' in class
        game_class_cards = soup.find_all('div', class_=lambda x: x and any('game' in cls.lower() for cls in x))
        print(f"4. Any 'game' in class: {len(game_class_cards)} cards")
        
        # Selector 5: Look for all divs and filter
        all_divs = soup.find_all('div')
        game_related = [div for div in all_divs if div.get('class') and any('game' in cls.lower() for cls in div.get('class', []))]
        print(f"5. All divs with 'game' in class: {len(game_related)} cards")
        
        # Use the best selector
        best_cards = id_cards if len(id_cards) > len(exact_cards) else exact_cards
        if len(partial_cards) > len(best_cards):
            best_cards = partial_cards
        
        print(f"\n✅ Using best selector: {len(best_cards)} cards")
        
        # Test extracting data from first few cards
        print(f"\n🎮 Testing data extraction from first 5 cards:")
        for i, card in enumerate(best_cards[:5]):
            print(f"\n--- Card {i+1} ---")
            print(f"ID: {card.get('id', 'None')}")
            print(f"Classes: {card.get('class', 'None')}")
            
            # Try to find title
            title_div = card.find('div', class_='game-grid-title')
            if title_div:
                title_link = title_div.find('a')
                if title_link:
                    title = title_link.get_text(strip=True)
                    print(f"Title: {title}")
                else:
                    print("Title: No link found in game-grid-title")
            else:
                print("Title: No game-grid-title div found")
            
            # Try to find any link
            any_link = card.find('a')
            if any_link:
                link_text = any_link.get_text(strip=True)
                print(f"Any link text: {link_text}")
            
            # Try to find any text
            all_text = card.get_text(strip=True)
            if all_text:
                print(f"All text: {all_text[:100]}...")
        
        # Check if we can find the expected structure
        print(f"\n🔍 Looking for expected HTML structure:")
        
        # Look for grid containers
        grid_containers = soup.find_all('div', class_=lambda x: x and 'grid' in ' '.join(x).lower())
        print(f"Grid containers: {len(grid_containers)}")
        
        # Look for col-* classes
        col_divs = soup.find_all('div', class_=lambda x: x and any('col-' in cls for cls in x))
        print(f"Column divs: {len(col_divs)}")
        
        # Look for specific game-related classes
        game_classes = set()
        for div in soup.find_all('div'):
            if div.get('class'):
                for cls in div.get('class'):
                    if 'game' in cls.lower():
                        game_classes.add(cls)
        
        print(f"Game-related classes found: {sorted(game_classes)}")
        
        return len(best_cards)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 0

if __name__ == "__main__":
    game_count = test_page_parsing()
    print(f"\n📊 Final result: Found {game_count} game cards")
    
    if game_count < 20:
        print("⚠️  This seems low - expected around 40 games per page")
    elif game_count >= 20:
        print("✅ This looks reasonable!")


