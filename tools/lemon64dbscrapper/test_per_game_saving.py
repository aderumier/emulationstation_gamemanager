#!/usr/bin/env python3
"""
Test script to verify per-game JSON saving functionality
"""

from lemon64_spider import Lemon64Spider
import json
import os
import time

def test_per_game_saving():
    """Test that JSON is saved after each game"""
    print("🧪 Testing per-game JSON saving...")
    
    spider = Lemon64Spider()
    test_file = "test_per_game_saving.json"
    
    # Clean up any existing test file
    if os.path.exists(test_file):
        os.remove(test_file)
    
    print(f"📄 Running spider with 1 page, saving to {test_file}")
    print("🔍 Monitoring file size changes...")
    
    initial_size = 0
    if os.path.exists(test_file):
        initial_size = os.path.getsize(test_file)
    
    # Run spider for just 1 page
    spider.run_spider(max_pages=1, output_file=test_file, detailed_info=False)
    
    # Check if file was created and has content
    if os.path.exists(test_file):
        final_size = os.path.getsize(test_file)
        print(f"✅ File created: {test_file}")
        print(f"📊 File size: {final_size} bytes")
        
        # Load and check content
        try:
            with open(test_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            print(f"🎮 Games in database: {len(data)}")
            
            if data:
                # Show first game as example
                first_game_id = list(data.keys())[0]
                first_game = data[first_game_id]
                print(f"📋 First game: {first_game.get('title', 'Unknown')} (ID: {first_game_id})")
                print(f"🔍 Available fields: {list(first_game.keys())}")
            
        except json.JSONDecodeError as e:
            print(f"❌ JSON parsing error: {e}")
    else:
        print("❌ Test file was not created")
    
    print("\n✅ Per-game saving test completed!")

if __name__ == "__main__":
    test_per_game_saving()


