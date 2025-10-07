#!/usr/bin/env python3
"""
Test script for progress tracking functionality
"""

from lemon64_spider import Lemon64Spider
import os
import json

def test_progress_tracking():
    """Test the progress tracking system"""
    print("🧪 Testing progress tracking system...")
    
    spider = Lemon64Spider()
    
    # Test 1: Clear any existing progress
    print("\n1️⃣ Clearing existing progress...")
    spider.clear_progress()
    
    # Test 2: Load progress (should be empty)
    print("\n2️⃣ Loading progress (should be empty)...")
    loaded = spider.load_progress()
    print(f"   Loaded: {loaded}")
    print(f"   Progress data: {spider.progress_data}")
    
    # Test 3: Update progress
    print("\n3️⃣ Updating progress...")
    spider.update_progress(offset=20, page_count=1, games_collected=15, status="running")
    print(f"   Updated progress: {spider.progress_data}")
    
    # Test 4: Load progress again
    print("\n4️⃣ Loading progress again...")
    loaded = spider.load_progress()
    print(f"   Loaded: {loaded}")
    print(f"   Progress data: {spider.progress_data}")
    
    # Test 5: Check if progress file exists
    print("\n5️⃣ Checking progress file...")
    if os.path.exists(spider.progress_file):
        print(f"   ✅ Progress file exists: {spider.progress_file}")
        with open(spider.progress_file, 'r') as f:
            content = json.load(f)
        print(f"   Content: {content}")
    else:
        print(f"   ❌ Progress file not found: {spider.progress_file}")
    
    # Test 6: Clear progress
    print("\n6️⃣ Clearing progress...")
    spider.clear_progress()
    print(f"   Progress after clear: {spider.progress_data}")
    
    print("\n✅ Progress tracking test completed!")

if __name__ == "__main__":
    test_progress_tracking()










