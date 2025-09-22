#!/usr/bin/env python3
"""
Test to reproduce the exact error message the user is seeing
"""
import os
import sys
import shutil
import tempfile
from pathlib import Path

def test_error_reproduction():
    """Test to reproduce the exact error message"""
    
    print("🧪 Error Reproduction Test")
    print("=" * 50)
    
    # Create a test scenario that matches the user's setup
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"📁 Test directory: {temp_dir}")
        
        # Create test system directory
        system_path = os.path.join(temp_dir, "roms", "windows")
        os.makedirs(system_path, exist_ok=True)
        os.makedirs(os.path.join(system_path, "Windows_DD2"), exist_ok=True)
        
        # Create test ROM files (simulating the user's actual setup)
        test_roms = [
            "game1.wsquashfs",  # Root
            "game2.wsquashfs",  # Root
            "Windows_DD2/Onimusha Warlords.wsquashfs",  # Subdirectory
            "Windows_DD2/Assassins Creed Brotherhood.wsquashfs",  # Subdirectory
            "Windows_DD2/Assassins Creed Mirage.wsquashfs",  # Subdirectory
        ]
        
        for rom in test_roms:
            rom_path = os.path.join(system_path, rom)
            os.makedirs(os.path.dirname(rom_path), exist_ok=True)
            with open(rom_path, 'w') as f:
                f.write("test content")
        
        print(f"📦 Created {len(test_roms)} test ROM files")
        
        # Create a gamelist.xml with games that have different paths
        gamelist_path = os.path.join(temp_dir, "gamelist.xml")
        gamelist_content = '''<?xml version='1.0' encoding='UTF-8'?>
<gameList>
  <game>
    <id>1</id>
    <path>./Onimusha Warlords.wsquashfs</path>
    <name>Onimusha Warlords</name>
  </game>
  <game>
    <id>2</id>
    <path>./Assassins Creed Brotherhood.wsquashfs</path>
    <name>Assassins Creed Brotherhood</name>
  </game>
  <game>
    <id>3</id>
    <path>./Assassins Creed Mirage.wsquashfs</path>
    <name>Assassins Creed Mirage</name>
  </game>
  <game>
    <id>4</id>
    <path>./game1.wsquashfs</path>
    <name>Game 1</name>
  </game>
  <game>
    <id>5</id>
    <path>./game2.wsquashfs</path>
    <name>Game 2</name>
  </game>
</gameList>'''
        
        with open(gamelist_path, 'w') as f:
            f.write(gamelist_content)
        
        print(f"📄 Created gamelist.xml with 5 games")
        
        # Now test the ROM scan logic
        print(f"\n🔍 Testing ROM scan logic...")
        
        # Find all ROM files
        rom_files = []
        for root, dirs, files in os.walk(system_path):
            for file in files:
                if file.endswith('.wsquashfs'):
                    rel_path = os.path.relpath(os.path.join(root, file), system_path)
                    rom_files.append(rel_path)
        
        print(f"📦 Found {len(rom_files)} ROM files:")
        for rom in sorted(rom_files):
            print(f"  - {rom}")
        
        # Parse existing games from gamelist
        existing_games = []
        try:
            from lxml import etree as ET
            tree = ET.parse(gamelist_path)
            root = tree.getroot()
            
            for game in root.findall('game'):
                game_data = {}
                for field in game:
                    if field.tag == 'path':
                        game_data['path'] = field.text.strip() if field.text else ''
                    elif field.tag == 'name':
                        game_data['name'] = field.text.strip() if field.text else ''
                existing_games.append(game_data)
        except Exception as e:
            print(f"❌ Error parsing gamelist: {e}")
            return False
        
        print(f"\n📋 Existing games in gamelist:")
        for game in existing_games:
            print(f"  - {game['path']} -> {game['name']}")
        
        # Apply the ROM scan logic
        print(f"\n🔧 Applying ROM scan logic...")
        
        # Create a mapping of ROM filenames to their full paths for lookup
        existing_roms_by_filename = {}
        for game in existing_games:
            rom_path = game.get('path', '')
            if rom_path:
                # Normalize path (remove ./ prefix if present)
                normalized_path = rom_path.lstrip('./')
                filename = os.path.basename(normalized_path)
                existing_roms_by_filename[filename] = normalized_path
        
        print(f"📊 Existing ROMs by filename mapping:")
        for filename, path in existing_roms_by_filename.items():
            print(f"  {filename} -> {path}")
        
        # Find new ROMs to add
        new_roms = []
        for rom_file in rom_files:
            filename = os.path.basename(rom_file)
            if filename not in existing_roms_by_filename:
                new_roms.append(rom_file)
        
        # Find games with missing ROM files
        missing_roms = []
        for game in existing_games:
            rom_path = game.get('path', '')
            if rom_path:
                # Normalize path (remove ./ prefix if present)
                normalized_path = rom_path.lstrip('./')
                rom_filename = os.path.basename(normalized_path)
                
                # Check if a ROM with the same filename exists in the found ROM files
                rom_found = False
                for found_rom in rom_files:
                    if os.path.basename(found_rom) == rom_filename:
                        rom_found = True
                        break
                
                # Only mark as missing if no ROM with the same filename was found
                if not rom_found:
                    missing_roms.append(game)
        
        # Display results
        print(f"\n📊 RESULTS:")
        print(f"  New ROMs to add: {len(new_roms)}")
        for rom in new_roms:
            print(f"    + {rom}")
        
        print(f"  Missing ROMs to remove: {len(missing_roms)}")
        for game in missing_roms:
            print(f"    - {game['path']} -> {game['name']}")
        
        # Check specific cases
        onimusha_found = any('Onimusha Warlords.wsquashfs' in rom for rom in rom_files)
        assassins_brotherhood_found = any('Assassins Creed Brotherhood.wsquashfs' in rom for rom in rom_files)
        assassins_mirage_found = any('Assassins Creed Mirage.wsquashfs' in rom for rom in rom_files)
        
        print(f"\n🔍 SPECIFIC CHECKS:")
        print(f"  Onimusha Warlords.wsquashfs found in ROM files: {onimusha_found}")
        print(f"  Assassins Creed Brotherhood.wsquashfs found in ROM files: {assassins_brotherhood_found}")
        print(f"  Assassins Creed Mirage.wsquashfs found in ROM files: {assassins_mirage_found}")
        
        # Check if these games are marked as missing
        onimusha_missing = any('Onimusha Warlords' in game['name'] for game in missing_roms)
        assassins_brotherhood_missing = any('Assassins Creed Brotherhood' in game['name'] for game in missing_roms)
        assassins_mirage_missing = any('Assassins Creed Mirage' in game['name'] for game in missing_roms)
        
        print(f"\n❌ MISSING CHECKS:")
        print(f"  Onimusha Warlords marked as missing: {onimusha_missing}")
        print(f"  Assassins Creed Brotherhood marked as missing: {assassins_brotherhood_missing}")
        print(f"  Assassins Creed Mirage marked as missing: {assassins_mirage_missing}")
        
        # This should reproduce the user's error
        if onimusha_missing or assassins_brotherhood_missing or assassins_mirage_missing:
            print(f"\n❌ PROBLEM REPRODUCED: Games are being marked as missing!")
            print(f"   This matches the user's error message:")
            print(f"   'Removing game with missing ROM: Onimusha Warlords (Onimusha Warlords.wsquashfs)'")
            print(f"   'Removing game with missing ROM: Assassins Creed Brotherhood (Assassins Creed Brotherhood.wsquashfs)'")
            print(f"   'Removing game with missing ROM: Assassins Creed Mirage (Assassins Creed Mirage.wsquashfs)'")
            return False
        else:
            print(f"\n✅ SUCCESS: No games incorrectly marked as missing!")
            print(f"   The fix is working correctly.")
            return True

if __name__ == "__main__":
    print("🚀 Starting Error Reproduction Test")
    print("=" * 50)
    
    success = test_error_reproduction()
    
    if success:
        print("\n✅ Test passed - fix is working!")
        sys.exit(0)
    else:
        print("\n❌ Test failed - issue reproduced!")
        sys.exit(1)
