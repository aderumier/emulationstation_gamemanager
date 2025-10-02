#!/usr/bin/env python3
"""
Test script for Lemon64 spider
Tests the spider with a limited number of pages
"""

from lemon64_spider import Lemon64Spider
import json

def test_spider():
    """Test the spider with just 3 pages"""
    print("🧪 Testing Lemon64 spider with 3 pages...")
    
    spider = Lemon64Spider()
    # Run with test filename and detailed info enabled
    spider.run_spider(max_pages=3, output_file="lemon64db_test.json", detailed_info=True)
    
    # Print some sample data
    if spider.games_db:
        print("\n📋 Sample games:")
        sample_games = list(spider.games_db.values())[:5]
        for game in sample_games:
            print(f"   {game['id']}: {game['title']} ({game.get('year', 'N/A')}) - {game.get('publisher', 'N/A')}")
    
    return len(spider.games_db)

if __name__ == "__main__":
    game_count = test_spider()
    print(f"\n✅ Test completed! Collected {game_count} games")
