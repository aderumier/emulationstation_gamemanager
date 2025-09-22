#!/usr/bin/env python3
"""
Test script for manual scrap functionality
This script tests each scraper individually to debug issues
"""

import asyncio
import sys
import os
import json

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the scraper functions
from app import (
    scrape_igdb_manual, 
    scrape_steam_manual, 
    scrape_screenscraper_manual, 
    scrape_steamgriddb_manual, 
    scrape_launchbox_manual,
    global_metadata_cache,
    load_config,
    load_scrappers_config,
    load_systems_config,
    load_metadata_cache
)

async def test_scrapers():
    """Test each scraper individually"""
    
    # Test game data (simulating what would come from the frontend)
    test_game = {
        'name': 'Berzerk',
        'path': './Berzerk (World).vec',
        'launchboxid': '116226',
        'steamid': None,  # This game doesn't have Steam ID
        'igdbid': '282317',
        'screenscraperid': '58825'
    }
    
    system_name = 'vectrex'
    
    # Load system configuration
    config = load_config()
    scrappers_config = load_scrappers_config()
    systems_config = load_systems_config()
    system_config = systems_config.get(system_name, {})
    
    print("=" * 60)
    print("TESTING MANUAL SCRAP FUNCTIONALITY")
    print("=" * 60)
    print(f"Test Game: {test_game['name']}")
    print(f"System: {system_name}")
    print(f"LaunchBox ID: {test_game.get('launchboxid')}")
    print(f"Steam ID: {test_game.get('steamid')}")
    print(f"IGDB ID: {test_game.get('igdbid')}")
    print("=" * 60)
    
    # Test 1: IGDB Scraper
    print("\n1. TESTING IGDB SCRAPER")
    print("-" * 30)
    try:
        igdb_data = await scrape_igdb_manual(test_game, system_name, system_config)
        if igdb_data:
            print("✅ IGDB scraper returned data:")
            print(f"   Text fields: {igdb_data.get('text_fields', {})}")
            print(f"   Media fields: {igdb_data.get('media_fields', {})}")
        else:
            print("❌ IGDB scraper returned no data")
    except Exception as e:
        print(f"❌ IGDB scraper error: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 2: Steam Scraper
    print("\n2. TESTING STEAM SCRAPER")
    print("-" * 30)
    try:
        steam_data = await scrape_steam_manual(test_game, system_name)
        if steam_data:
            print("✅ Steam scraper returned data:")
            print(f"   Text fields: {steam_data.get('text_fields', {})}")
            print(f"   Media fields: {steam_data.get('media_fields', {})}")
        else:
            print("❌ Steam scraper returned no data (expected - no Steam ID)")
    except Exception as e:
        print(f"❌ Steam scraper error: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 3: ScreenScraper
    print("\n3. TESTING SCREENSCRAPER")
    print("-" * 30)
    try:
        # First, let's test the ScreenScraper service directly
        from screenscraper_service import ScreenScraperService
        from credential_manager import CredentialManager
        
        # Initialize ScreenScraper service with proper config and credentials
        credential_manager = CredentialManager()
        screenscraper_config = system_config.get('screenscraper', {})
        screenscraper_credentials = credential_manager.get_screenscraper_credentials()
        
        print(f"ScreenScraper config: {screenscraper_config}")
        print(f"ScreenScraper config type: {type(screenscraper_config)}")
        
        # Get the full config (needed for systems mapping)
        config = load_config()
        
        # Handle case where screenscraper config is just an integer (system_id)
        if isinstance(screenscraper_config, int):
            system_id = screenscraper_config
        else:
            system_id = screenscraper_config.get('system_id')
        
        screenscraper_service = ScreenScraperService(config, screenscraper_credentials, scrappers_config, systems_config)
        
        print(f"Testing ScreenScraper search for: {test_game['name']}")
        search_result = await screenscraper_service.search_game(test_game['name'], system_name)
        print(f"ScreenScraper search result: {search_result}")
        
        if search_result:
            game_data = search_result.get('game_data')
            print(f"Game data type: {type(game_data)}")
            print(f"Game data keys: {list(game_data.keys()) if isinstance(game_data, dict) else 'Not a dict'}")
            if isinstance(game_data, dict) and 'noms' in game_data:
                noms = game_data['noms']
                print(f"Noms type: {type(noms)}")
                print(f"Noms value: {noms}")
                if isinstance(noms, list) and len(noms) > 0:
                    print(f"Noms[0] type: {type(noms[0])}")
                    print(f"Noms[0] value: {noms[0]}")
        
        screenscraper_data = await scrape_screenscraper_manual(test_game, system_name, system_config)
        if screenscraper_data:
            print("✅ ScreenScraper returned data:")
            print(f"   Text fields: {screenscraper_data.get('text_fields', {})}")
            print(f"   Media fields: {screenscraper_data.get('media_fields', {})}")
        else:
            print("❌ ScreenScraper returned no data")
    except Exception as e:
        print(f"❌ ScreenScraper error: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 4: SteamGridDB Scraper
    print("\n4. TESTING STEAMGRIDDB SCRAPER")
    print("-" * 30)
    try:
        steamgriddb_data = await scrape_steamgriddb_manual(test_game, system_name)
        if steamgriddb_data:
            print("✅ SteamGridDB scraper returned data:")
            print(f"   Text fields: {steamgriddb_data.get('text_fields', {})}")
            print(f"   Media fields: {steamgriddb_data.get('media_fields', {})}")
        else:
            print("❌ SteamGridDB scraper returned no data (expected - no Steam ID)")
    except Exception as e:
        print(f"❌ SteamGridDB scraper error: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 5: LaunchBox Scraper
    print("\n5. TESTING LAUNCHBOX SCRAPER")
    print("-" * 30)
    try:
        print(f"Cache size: {len(global_metadata_cache)}")
        print(f"Looking for LaunchBox ID: {test_game.get('launchboxid')}")
        print(f"Cache keys sample: {list(global_metadata_cache.keys())[:5]}")
        
        launchbox_data = await scrape_launchbox_manual(test_game, system_name)
        if launchbox_data:
            print("✅ LaunchBox scraper returned data:")
            print(f"   Text fields: {launchbox_data.get('text_fields', {})}")
            print(f"   Media fields: {launchbox_data.get('media_fields', {})}")
        else:
            print("❌ LaunchBox scraper returned no data")
    except Exception as e:
        print(f"❌ LaunchBox scraper error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("TEST COMPLETED")
    print("=" * 60)

def test_cache_loading():
    """Test if the cache is properly loaded"""
    print("\nCACHE LOADING TEST")
    print("-" * 30)
    print(f"Global metadata cache size before loading: {len(global_metadata_cache)}")
    
    # Load the cache
    print("Loading metadata cache...")
    load_metadata_cache()
    print(f"Global metadata cache size after loading: {len(global_metadata_cache)}")
    
    if global_metadata_cache:
        print("✅ Cache is loaded")
        sample_keys = list(global_metadata_cache.keys())[:5]
        print(f"Sample cache keys: {sample_keys}")
        
        # Test specific LaunchBox ID
        test_id = "116226"
        if test_id in global_metadata_cache:
            print(f"✅ LaunchBox ID {test_id} found in cache")
            game_data = global_metadata_cache[test_id]
            print(f"Game data keys: {list(game_data.keys()) if isinstance(game_data, dict) else 'Not a dict'}")
            if isinstance(game_data, dict) and 'game' in game_data:
                game_info = game_data['game']
                print(f"Game info keys: {list(game_info.keys()) if isinstance(game_info, dict) else 'Not a dict'}")
                print(f"Game name: {game_info.get('name', 'No name')}")
                print(f"Game description: {game_info.get('description', 'No description')[:100]}...")
                print(f"Game developer: {game_info.get('developer', 'No developer')}")
                print(f"Game publisher: {game_info.get('publisher', 'No publisher')}")
                print(f"Game genre: {game_info.get('genre', 'No genre')}")
                print(f"Game release_date: {game_info.get('release_date', 'No release date')}")
                if 'images' in game_data:
                    print(f"Images count: {len(game_data['images'])}")
                    for i, img in enumerate(game_data['images'][:3]):  # Show first 3 images
                        print(f"  Image {i+1}: {img.get('type', 'Unknown type')} - {img.get('url', 'No URL')}")
        else:
            print(f"❌ LaunchBox ID {test_id} NOT found in cache")
            print("Available IDs around 116226:")
            for key in sorted(global_metadata_cache.keys()):
                if key.isdigit() and abs(int(key) - int(test_id)) < 100:
                    print(f"  {key}")
    else:
        print("❌ Cache is empty or not loaded")

if __name__ == "__main__":
    print("Starting manual scrap test...")
    
    # Test cache loading first
    test_cache_loading()
    
    # Run async tests
    asyncio.run(test_scrapers())
