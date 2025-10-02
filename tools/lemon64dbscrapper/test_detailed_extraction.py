#!/usr/bin/env python3
"""
Test script to verify detailed game information extraction
"""

from lemon64_spider import Lemon64Spider
import json

def test_detailed_extraction():
    """Test detailed extraction for a single game"""
    print("🧪 Testing detailed game information extraction...")
    
    spider = Lemon64Spider()
    
    # Test with a known game URL (Bruce Lee as example)
    test_url = "https://www.lemon64.com/game/bruce-lee"
    
    print(f"🔍 Testing with URL: {test_url}")
    
    detailed_info = spider.extract_detailed_game_info(test_url)
    
    print("\n📊 Detailed Information Extracted:")
    print("=" * 50)
    
    for key, value in detailed_info.items():
        if isinstance(value, list):
            print(f"{key}: {len(value)} items")
            for i, item in enumerate(value[:3]):  # Show first 3 items
                print(f"  {i+1}. {item}")
            if len(value) > 3:
                print(f"  ... and {len(value) - 3} more")
        else:
            print(f"{key}: {value}")
    
    print("\n" + "=" * 50)
    
    # Save test result
    with open('test_detailed_extraction.json', 'w', encoding='utf-8') as f:
        json.dump(detailed_info, f, indent=2, ensure_ascii=False)
    
    print("💾 Test result saved to test_detailed_extraction.json")
    
    return detailed_info

if __name__ == "__main__":
    test_detailed_extraction()


