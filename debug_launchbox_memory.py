#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug script to track LaunchboxService memory usage in worker-like conditions
"""

import sys
import os
import time
import psutil
import gc
from launchbox_service import LaunchboxService

def get_memory_usage():
    """Get current memory usage in MB"""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024

def debug_memory_usage():
    """Debug memory usage step by step"""
    
    # Mock configuration
    config = {
        'launchbox_metadata_path': 'var/db/launchbox/Metadata.xml'
    }
    
    scrappers_config = {
        'launchbox': {
            'mapping': {
                'Name': 'name',
                'Overview': 'desc',
                'Developer': 'developer',
                'Publisher': 'publisher',
                'ReleaseDate': 'releasedate',
                'Rating': 'rating',
                'Genre': 'genre'
            }
        }
    }
    
    systems_config = {}
    
    print("🔍 Debugging LaunchboxService memory usage...")
    
    # Check if metadata file exists
    if not os.path.exists(config['launchbox_metadata_path']):
        print(f"❌ Launchbox metadata file not found: {config['launchbox_metadata_path']}")
        return
    
    try:
        # Step 1: Initial memory
        gc.collect()
        initial_memory = get_memory_usage()
        print(f"📊 Step 1 - Initial memory: {initial_memory:.1f} MB")
        
        # Step 2: Create service for single platform
        print(f"\n🎯 Creating LaunchboxService for 'Windows' platform...")
        start_time = time.time()
        
        service = LaunchboxService.for_platform(
            config=config,
            scrappers_config=scrappers_config,
            systems_config=systems_config,
            target_platform='Windows'
        )
        
        creation_time = time.time() - start_time
        creation_memory = get_memory_usage()
        print(f"📊 Step 2 - After service creation: {creation_memory:.1f} MB (+{creation_memory - initial_memory:.1f} MB) in {creation_time:.2f}s")
        
        # Step 3: Check what platforms were loaded
        platforms = service.get_platforms()
        print(f"📊 Step 3 - Loaded platforms: {len(platforms)} - {platforms}")
        
        # Step 4: Check database sizes
        for platform in platforms:
            count = service.get_platform_game_count(platform)
            print(f"📊 Step 4 - Platform '{platform}': {count} games")
        
        # Step 5: Check index sizes
        total_index_items = 0
        for platform in platforms:
            with_parens_count = sum(len(partition) for partition in service._global_similarity_index_with_parens.get(platform, {}).values())
            no_parens_count = sum(len(partition) for partition in service._global_similarity_index_no_parens.get(platform, {}).values())
            print(f"📊 Step 5 - Platform '{platform}' indexes: {with_parens_count} with_parens, {no_parens_count} no_parens")
            total_index_items += with_parens_count + no_parens_count
        
        print(f"📊 Step 5 - Total index items: {total_index_items}")
        
        # Step 6: Test some searches
        print(f"\n🔍 Testing searches...")
        test_games = list(service.databases.get('Windows', {}).values())[:5]
        for i, game in enumerate(test_games):
            game_name = game.get('Name', '')
            if game_name:
                search_memory_before = get_memory_usage()
                result = service.find_game_exact('Windows', game_name)
                search_memory_after = get_memory_usage()
                print(f"📊 Search {i+1} - '{game_name}': {search_memory_after - search_memory_before:.1f} MB change")
                break
        
        # Step 7: Final memory check
        final_memory = get_memory_usage()
        print(f"\n📊 Step 7 - Final memory: {final_memory:.1f} MB (+{final_memory - initial_memory:.1f} MB total)")
        
        # Step 8: Memory breakdown
        print(f"\n📊 Memory Breakdown:")
        print(f"  Service creation: {creation_memory - initial_memory:.1f} MB")
        print(f"  Searches: {final_memory - creation_memory:.1f} MB")
        print(f"  Total increase: {final_memory - initial_memory:.1f} MB")
        
        # Check if we're loading more than expected
        if len(platforms) > 1:
            print(f"⚠️  WARNING: Expected 1 platform but loaded {len(platforms)} platforms!")
            print(f"   This suggests the platform filtering is not working correctly.")
        
        if final_memory - initial_memory > 100:  # More than 100MB for single platform
            print(f"⚠️  WARNING: Memory usage is very high for single platform!")
            print(f"   Expected < 50MB, got {final_memory - initial_memory:.1f} MB")
        
        print("\n✅ Memory debug completed!")
        
    except Exception as e:
        print(f"❌ Debug failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_memory_usage()


