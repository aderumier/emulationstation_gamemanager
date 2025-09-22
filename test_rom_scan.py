#!/usr/bin/env python3
import os
import glob

def test_rom_scan():
    """Test the ROM scan logic to verify the fix works"""
    
    # Simulate the system path
    system_path = "roms/windows"
    
    # Find all ROM files (simulating the ROM scan)
    rom_files = []
    for root, dirs, files in os.walk(system_path):
        for file in files:
            if file.endswith('.wsquashfs'):
                # Get relative path from system directory
                rel_path = os.path.relpath(os.path.join(root, file), system_path)
                rom_files.append(rel_path)
    
    print(f"Found {len(rom_files)} ROM files:")
    for rom in rom_files[:10]:  # Show first 10
        print(f"  - {rom}")
    
    # Simulate existing games from gamelist (before our fix, these would be marked as missing)
    existing_games = [
        {'path': './Trails in the Sky 1st Chapter.wsquashfs', 'name': 'Trails in the Sky 1st Chapter'},
        {'path': './test5.wsquashfs', 'name': 'test5'},
        {'path': './Formula Legends.wsquashfs', 'name': 'Formula Legends'},
        {'path': './test.wsquashfs', 'name': 'test'},
        {'path': './Windows_DD2/test.wsquashfs', 'name': 'test'},
    ]
    
    print(f"\nExisting games in gamelist:")
    for game in existing_games:
        print(f"  - {game['path']} -> {game['name']}")
    
    # Apply our fixed logic
    # Create a mapping of ROM filenames to their full paths for lookup
    existing_roms_by_filename = {}
    for game in existing_games:
        rom_path = game.get('path', '')
        if rom_path:
            # Normalize path (remove ./ prefix if present)
            normalized_path = rom_path.lstrip('./')
            filename = os.path.basename(normalized_path)
            existing_roms_by_filename[filename] = normalized_path
    
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
    
    print(f"\n=== RESULTS ===")
    print(f"New ROMs to add: {len(new_roms)}")
    for rom in new_roms:
        print(f"  + {rom}")
    
    print(f"\nMissing ROMs to remove: {len(missing_roms)}")
    for game in missing_roms:
        print(f"  - {game['path']} -> {game['name']}")
    
    print(f"\n=== VERIFICATION ===")
    print(f"✅ Expected: 0 missing ROMs (all games should be found by filename)")
    print(f"✅ Expected: 1+ new ROMs (including gameX.wsquashfs)")
    
    if len(missing_roms) == 0:
        print("🎉 SUCCESS: No games marked as missing - fix is working!")
    else:
        print("❌ FAILURE: Games still marked as missing - fix needs work")
    
    if 'gameX.wsquashfs' in [os.path.basename(rom) for rom in new_roms]:
        print("🎉 SUCCESS: New gameX.wsquashfs detected as new ROM!")
    else:
        print("❌ FAILURE: New gameX.wsquashfs not detected")

if __name__ == "__main__":
    test_rom_scan()
