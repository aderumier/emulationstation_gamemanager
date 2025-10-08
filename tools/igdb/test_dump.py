#!/usr/bin/env python3
"""
Test script for IGDB dump functionality

This script tests the IGDB dump functionality with a small sample of data.
"""

import os
import sys
import asyncio

# Add the current directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dump import IGDBDumper

async def test_dump():
    """Test the IGDB dump with minimal data"""
    dumper = IGDBDumper(force=True)  # Force redump for testing
    
    try:
        print("🧪 Testing IGDB dump functionality...")
        
        # Initialize
        await dumper.initialize()
        print("✅ Initialization successful")
        
        # Test platforms (should be small dataset)
        platforms = await dumper.dump_platforms()
        print(f"✅ Platforms dump successful: {len(platforms)} platforms")
        
        # Test genres (should be small dataset)
        genres = await dumper.dump_genres()
        print(f"✅ Genres dump successful: {len(genres)} genres")
        
        # Test a small batch of games (for testing purposes)
        games = await dumper.dump_games(max_games=10)
        print(f"✅ Games dump successful: {len(games)} games")
        
        # Test covers for the games
        if games:
            game_ids = [game['id'] for game in games if 'id' in game]
            covers = await dumper.dump_covers(game_ids)
            print(f"✅ Covers dump successful: {len(covers)} covers")
            
            # Test artworks
            artworks = await dumper.dump_artworks(game_ids)
            print(f"✅ Artworks dump successful: {len(artworks)} artworks")
            
            # Test alternative names
            alternative_names = await dumper.dump_alternative_names(game_ids)
            print(f"✅ Alternative names dump successful: {len(alternative_names)} alternative names")
        
        print("\n🎉 All tests passed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await dumper.close()

if __name__ == '__main__':
    asyncio.run(test_dump())
