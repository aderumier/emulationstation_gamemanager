#!/usr/bin/env python3
"""
Rename media files in gamelist.xml to match ROM filenames.

For each game in the gamelist.xml:
- Extracts the ROM filename (without extension)
- Finds all media files declared in media fields
- Renames each media file to: ROM_filename + original_extension
- Updates the gamelist.xml with the new paths
"""

import os
import sys
import xml.etree.ElementTree as ET
import argparse
from pathlib import Path


def parse_gamelist_xml(file_path):
    """Parse gamelist.xml file and return root element and tree"""
    try:
        if not os.path.exists(file_path):
            print(f"❌ Gamelist file does not exist: {file_path}")
            return None, None
        
        tree = ET.parse(file_path)
        root = tree.getroot()
        return root, tree
    except Exception as e:
        print(f"❌ Error parsing gamelist.xml: {e}")
        return None, None


def get_media_fields_from_config():
    """Get list of media fields from config.json"""
    try:
        config_path = 'var/config/config.json'
        if os.path.exists(config_path):
            import json
            with open(config_path, 'r') as f:
                config = json.load(f)
            media_fields = config.get('media_fields', {})
            return list(media_fields.keys())
    except Exception as e:
        print(f"⚠️  Warning: Could not load config.json: {e}")
    
    # Fallback to common media fields
    return ['image', 'video', 'marquee', 'fanart', 'boxart', 'cartridge', 
            'titleshot', 'manual', 'boxback', 'thumbnail', 'screenshot']


def get_rom_filename_without_ext(rom_path):
    """Extract ROM filename without extension from path"""
    if not rom_path:
        return None
    
    # Handle relative paths like "./game.zip" or "game.zip"
    rom_path = rom_path.strip()
    if rom_path.startswith('./'):
        rom_path = rom_path[2:]
    
    # Get just the filename
    rom_filename = os.path.basename(rom_path)
    
    # Remove extension
    rom_name_without_ext = os.path.splitext(rom_filename)[0]
    
    return rom_name_without_ext


def resolve_media_path(media_path, gamelist_dir):
    """Resolve media path to absolute path"""
    if not media_path or not media_path.strip():
        return None
    
    media_path = media_path.strip()
    
    # Handle relative paths
    if media_path.startswith('./'):
        media_path = media_path[2:]
    
    # If path is relative, make it relative to gamelist directory
    if not os.path.isabs(media_path):
        # Check if it's already relative to gamelist directory
        full_path = os.path.join(gamelist_dir, media_path)
        if os.path.exists(full_path):
            return full_path
        
        # Try relative to parent of gamelist directory (typical structure)
        parent_dir = os.path.dirname(gamelist_dir)
        full_path = os.path.join(parent_dir, media_path)
        if os.path.exists(full_path):
            return full_path
    
    # If it's already absolute, use as-is
    if os.path.exists(media_path):
        return media_path
    
    return None


def get_media_directory(media_path):
    """Get the directory part of a media path"""
    if not media_path:
        return None
    
    # Handle relative paths
    if media_path.startswith('./'):
        media_path = media_path[2:]
    
    return os.path.dirname(media_path)


def rename_media_files(gamelist_path, dry_run=False, media_fields=None):
    """Rename all media files in gamelist.xml to match ROM filenames"""
    
    # Get gamelist directory
    gamelist_dir = os.path.dirname(os.path.abspath(gamelist_path))
    
    # Parse gamelist.xml
    root, tree = parse_gamelist_xml(gamelist_path)
    if not root:
        return False
    
    # Get media fields to process
    if not media_fields:
        media_fields = get_media_fields_from_config()
    
    print(f"📋 Processing gamelist: {gamelist_path}")
    print(f"📁 Gamelist directory: {gamelist_dir}")
    print(f"🎨 Media fields to process: {', '.join(media_fields)}")
    print()
    
    if dry_run:
        print("🔍 DRY RUN MODE - No files will be renamed")
        print()
    
    total_games = 0
    total_renamed = 0
    total_skipped = 0
    total_errors = 0
    
    # Process each game
    for game_elem in root.findall('game'):
        total_games += 1
        
        # Get game name for display
        name_elem = game_elem.find('name')
        game_name = name_elem.text if name_elem is not None else 'Unknown'
        
        # Get ROM path
        path_elem = game_elem.find('path')
        if path_elem is None or not path_elem.text:
            print(f"⚠️  [{total_games}] '{game_name}': No ROM path found, skipping")
            total_skipped += 1
            continue
        
        rom_path = path_elem.text
        rom_filename_without_ext = get_rom_filename_without_ext(rom_path)
        
        if not rom_filename_without_ext:
            print(f"⚠️  [{total_games}] '{game_name}': Could not extract ROM filename, skipping")
            total_skipped += 1
            continue
        
        print(f"[{total_games}] '{game_name}' (ROM: {rom_filename_without_ext})")
        
        # Process each media field
        game_renamed = 0
        for media_field in media_fields:
            media_elem = game_elem.find(media_field)
            if media_elem is None or not media_elem.text or not media_elem.text.strip():
                continue
            
            old_media_path = media_elem.text.strip()
            
            # Resolve absolute path
            old_abs_path = resolve_media_path(old_media_path, gamelist_dir)
            if not old_abs_path:
                print(f"   ⚠️  {media_field}: File not found: {old_media_path}")
                total_errors += 1
                continue
            
            # Get file extension
            _, ext = os.path.splitext(old_abs_path)
            if not ext:
                print(f"   ⚠️  {media_field}: No extension found: {old_abs_path}")
                total_errors += 1
                continue
            
            # Create new filename
            new_filename = f"{rom_filename_without_ext}{ext}"
            
            # Get directory for new file
            media_dir = os.path.dirname(old_abs_path)
            new_abs_path = os.path.join(media_dir, new_filename)
            
            # Check if file already has correct name
            if os.path.basename(old_abs_path) == new_filename:
                print(f"   ✓ {media_field}: Already correctly named")
                continue
            
            # Check if target file already exists
            if os.path.exists(new_abs_path):
                print(f"   ⚠️  {media_field}: Target file already exists: {new_filename}")
                total_errors += 1
                continue
            
            if dry_run:
                print(f"   🔍 {media_field}: Would rename")
                print(f"      From: {os.path.basename(old_abs_path)}")
                print(f"      To:   {new_filename}")
            else:
                try:
                    # Rename the file
                    os.rename(old_abs_path, new_abs_path)
                    print(f"   ✅ {media_field}: Renamed to {new_filename}")
                    
                    # Update gamelist.xml path
                    # Keep the same relative path structure
                    media_dir_rel = get_media_directory(old_media_path)
                    if media_dir_rel:
                        new_media_path = f"./{media_dir_rel}/{new_filename}"
                    else:
                        new_media_path = f"./{new_filename}"
                    
                    media_elem.text = new_media_path
                    game_renamed += 1
                    total_renamed += 1
                    
                except Exception as e:
                    print(f"   ❌ {media_field}: Error renaming: {e}")
                    total_errors += 1
        
        if game_renamed > 0:
            print(f"   📝 Updated {game_renamed} media file(s) in gamelist.xml")
        print()
    
    # Save updated gamelist.xml if not dry run
    if not dry_run and total_renamed > 0:
        try:
            # Format the XML nicely
            ET.indent(tree, space="  ")
            tree.write(gamelist_path, encoding='utf-8', xml_declaration=True)
            print(f"💾 Saved updated gamelist.xml")
        except Exception as e:
            print(f"❌ Error saving gamelist.xml: {e}")
            return False
    
    # Print summary
    print("=" * 60)
    print("Summary:")
    print(f"  📊 Total games processed: {total_games}")
    print(f"  ✅ Files renamed: {total_renamed}")
    print(f"  ⏭️  Games skipped: {total_skipped}")
    print(f"  ❌ Errors: {total_errors}")
    print("=" * 60)
    
    return True


def main():
    parser = argparse.ArgumentParser(
        description='Rename media files in gamelist.xml to match ROM filenames',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run to see what would be renamed
  python rename_media_to_romname.py var/gamelists/nes/gamelist.xml --dry-run
  
  # Actually rename the files
  python rename_media_to_romname.py var/gamelists/nes/gamelist.xml
  
  # Process specific media fields only
  python rename_media_to_romname.py var/gamelists/nes/gamelist.xml --fields image video marquee
        """
    )
    
    parser.add_argument(
        'gamelist_path',
        help='Path to gamelist.xml file'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be renamed without actually renaming files'
    )
    
    parser.add_argument(
        '--fields',
        nargs='+',
        help='Specific media fields to process (default: all media fields from config.json)'
    )
    
    args = parser.parse_args()
    
    # Validate gamelist path
    if not os.path.exists(args.gamelist_path):
        print(f"❌ Error: Gamelist file not found: {args.gamelist_path}")
        sys.exit(1)
    
    # Run the renaming
    success = rename_media_files(
        args.gamelist_path,
        dry_run=args.dry_run,
        media_fields=args.fields
    )
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()

