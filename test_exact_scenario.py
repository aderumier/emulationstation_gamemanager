#!/usr/bin/env python3
"""
Test the exact scenario: remove gamelist, scan, add game, scan again
This will help identify where the issue is
"""
import os
import sys
import shutil
import tempfile
from pathlib import Path

def test_exact_scenario():
    """Test the exact scenario step by step"""
    
    print("🧪 Exact Scenario Test")
    print("=" * 50)
    
    # Step 1: Remove gamelist.xml (already done)
    print("✅ Step 1: Gamelist.xml already removed")
    
    # Step 2: Check current ROM files
    system_path = "/home/aderumier/cursorscraper/roms/windows"
    print(f"\n🔍 Step 2: Checking current ROM files in {system_path}")
    
    rom_files = []
    for root, dirs, files in os.walk(system_path):
        for file in files:
            if file.endswith('.wsquashfs'):
                rel_path = os.path.relpath(os.path.join(root, file), system_path)
                rom_files.append(rel_path)
    
    print(f"📦 Found {len(rom_files)} ROM files")
    
    # Check if gameX.wsquashfs exists
    gamex_exists = any('gameX.wsquashfs' in rom for rom in rom_files)
    print(f"🎯 gameX.wsquashfs exists: {gamex_exists}")
    
    if gamex_exists:
        print(f"✅ gameX.wsquashfs found in ROM files")
    else:
        print(f"❌ gameX.wsquashfs NOT found in ROM files")
        return False
    
    # Step 3: Simulate the ROM scan logic that would create the initial gamelist
    print(f"\n🔧 Step 3: Simulating initial ROM scan logic")
    
    # This is what happens when there's no existing gamelist (initial import)
    # All ROM files should be added as new games
    new_games = []
    for rom_file in rom_files:
        game_entry = {
            'name': os.path.splitext(os.path.basename(rom_file))[0],
            'path': f'./{rom_file}',
            'desc': '',
            'image': '',
            'releasedate': '',
            'developer': '',
            'publisher': '',
            'genre': '',
            'players': '',
            'playcount': '0',
            'lastplayed': '',
            'favorite': 'false',
            'hidden': 'false'
        }
        new_games.append(game_entry)
    
    print(f"📊 Would create {len(new_games)} games in initial gamelist")
    
    # Check if gameX would be included
    gamex_included = any('gameX' in game['name'] for game in new_games)
    print(f"🎯 gameX would be included in initial gamelist: {gamex_included}")
    
    if gamex_included:
        gamex_game = next(game for game in new_games if 'gameX' in game['name'])
        print(f"✅ gameX game entry: {gamex_game['name']} -> {gamex_game['path']}")
    else:
        print(f"❌ gameX NOT included in initial gamelist")
        return False
    
    # Step 4: Simulate adding another game and rescanning
    print(f"\n➕ Step 4: Simulating adding another game")
    
    # Create another test game
    another_game_path = os.path.join(system_path, "gameY.wsquashfs")
    with open(another_game_path, 'w') as f:
        f.write("test content")
    
    print(f"✅ Created gameY.wsquashfs")
    
    # Rescan ROM files
    rom_files_second = []
    for root, dirs, files in os.walk(system_path):
        for file in files:
            if file.endswith('.wsquashfs'):
                rel_path = os.path.relpath(os.path.join(root, file), system_path)
                rom_files_second.append(rel_path)
    
    print(f"📦 Found {len(rom_files_second)} ROM files in second scan")
    
    # Check if both test games exist
    gamex_exists_second = any('gameX.wsquashfs' in rom for rom in rom_files_second)
    gamey_exists_second = any('gameY.wsquashfs' in rom for rom in rom_files_second)
    
    print(f"🎯 gameX.wsquashfs exists in second scan: {gamex_exists_second}")
    print(f"🎯 gameY.wsquashfs exists in second scan: {gamey_exists_second}")
    
    # Step 5: Simulate the ROM scan logic with existing games
    print(f"\n🔧 Step 5: Simulating ROM scan with existing games")
    
    # Create existing games from the first scan (simulating gamelist.xml)
    existing_games = new_games.copy()
    
    # Apply the ROM scan logic
    existing_roms_by_filename = {}
    for game in existing_games:
        rom_path = game.get('path', '')
        if rom_path:
            normalized_path = rom_path.lstrip('./')
            filename = os.path.basename(normalized_path)
            existing_roms_by_filename[filename] = normalized_path
    
    print(f"📊 Existing ROMs by filename mapping ({len(existing_roms_by_filename)} games):")
    for filename in sorted(existing_roms_by_filename.keys())[:10]:  # Show first 10
        print(f"  {filename}")
    if len(existing_roms_by_filename) > 10:
        print(f"  ... and {len(existing_roms_by_filename) - 10} more")
    
    # Find new ROMs
    new_roms = []
    for rom_file in rom_files_second:
        filename = os.path.basename(rom_file)
        if filename not in existing_roms_by_filename:
            new_roms.append(rom_file)
    
    # Find missing ROMs
    missing_roms = []
    for game in existing_games:
        rom_path = game.get('path', '')
        if rom_path:
            normalized_path = rom_path.lstrip('./')
            rom_filename = os.path.basename(normalized_path)
            
            rom_found = False
            for found_rom in rom_files_second:
                if os.path.basename(found_rom) == rom_filename:
                    rom_found = True
                    break
            
            if not rom_found:
                missing_roms.append(game)
    
    print(f"\n📊 RESULTS:")
    print(f"  New ROMs to add: {len(new_roms)}")
    for rom in new_roms:
        print(f"    + {rom}")
    
    print(f"  Missing ROMs to remove: {len(missing_roms)}")
    for game in missing_roms:
        print(f"    - {game['path']} -> {game['name']}")
    
    # Check specific cases
    gamey_in_new = any('gameY.wsquashfs' in rom for rom in new_roms)
    gamex_in_missing = any('gameX' in game['name'] for game in missing_roms)
    
    print(f"\n🔍 SPECIFIC CHECKS:")
    print(f"  gameY.wsquashfs detected as new: {gamey_in_new}")
    print(f"  gameX.wsquashfs marked as missing: {gamex_in_missing}")
    
    # Cleanup
    if os.path.exists(another_game_path):
        os.remove(another_game_path)
        print(f"\n🧹 Cleaned up gameY.wsquashfs")
    
    # Overall result
    success = gamey_in_new and not gamex_in_missing
    
    if success:
        print(f"\n✅ SUCCESS: ROM scan logic is working correctly!")
        print(f"   - New game (gameY) detected as new: ✅")
        print(f"   - Existing game (gameX) not marked as missing: ✅")
        return True
    else:
        print(f"\n❌ FAILURE: ROM scan logic has issues!")
        print(f"   - New game (gameY) detected as new: {'✅' if gamey_in_new else '❌'}")
        print(f"   - Existing game (gameX) not marked as missing: {'✅' if not gamex_in_missing else '❌'}")
        return False

if __name__ == "__main__":
    print("🚀 Starting Exact Scenario Test")
    print("=" * 50)
    
    success = test_exact_scenario()
    
    if success:
        print("\n✅ All tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Tests failed!")
        sys.exit(1)
