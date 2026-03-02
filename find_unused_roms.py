#!/usr/bin/env python3
"""
Script to find files and directories in roms folder that are not referenced as ROMs in gamelist.xml files.
Excludes media folders and gamelist.xml files from the search.
Works with a specific system and uses roms/<system>/gamelist.xml directly.
"""

import os
import xml.etree.ElementTree as ET
from pathlib import Path
import argparse

def get_rom_paths_from_gamelist(gamelist_path):
    """Extract all ROM paths from a gamelist.xml file."""
    rom_paths = set()
    
    try:
        tree = ET.parse(gamelist_path)
        root = tree.getroot()
        
        for game in root.findall('game'):
            path_elem = game.find('path')
            if path_elem is not None and path_elem.text:
                # Remove leading './' if present
                rom_path = path_elem.text.removeprefix('./')
                rom_paths.add(rom_path)
    
    except ET.ParseError as e:
        print(f"Error parsing {gamelist_path}: {e}")
    except FileNotFoundError:
        print(f"File not found: {gamelist_path}")
    
    return rom_paths

def find_unused_roms(roms_dir, system_name):
    """Find files and directories in roms that are not referenced in the specific system's gamelist.xml."""
    
    # Get ROM paths from the specific system's gamelist.xml
    gamelist_path = os.path.join(roms_dir, system_name, 'gamelist.xml')
    rom_paths = set()
    
    if os.path.exists(gamelist_path):
        rom_paths = get_rom_paths_from_gamelist(gamelist_path)
        print(f"Found {len(rom_paths)} ROMs in {system_name}/gamelist.xml")
    else:
        print(f"Warning: gamelist.xml not found at {gamelist_path}")
        return [], []
    
    # Get all files and directories in the specific system's roms directory
    system_roms_dir = os.path.join(roms_dir, system_name)
    unused_files = []
    unused_dirs = []
    
    if not os.path.exists(system_roms_dir):
        print(f"System ROMs directory not found: {system_roms_dir}")
        return unused_files, unused_dirs
    
    for root, dirs, files in os.walk(system_roms_dir):
        # Skip media directories
        dirs[:] = [d for d in dirs if d != 'media']
        
        # Get relative path from system roms directory
        rel_root = os.path.relpath(root, system_roms_dir)
        if rel_root == '.':
            rel_root = ''
        
        # Check files (only in the root directory of the system, not in subdirectories)
        if rel_root == '':  # We're in the root directory of the system
            for file in files:
                if file == 'gamelist.xml':
                    continue  # Skip gamelist.xml files
                
                file_path = file  # In root, the relative path is just the filename
                file_path = file_path.replace('\\', '/')  # Normalize path separators
                
                if file_path not in rom_paths:
                    full_path = os.path.join(root, file)
                    unused_files.append(full_path)
        
        # Only check for unused directories in the root of the system (not in subdirectories)
        if rel_root == '':  # We're in the root directory of the system
            for dir_name in dirs:
                if dir_name == 'media':
                    continue  # Skip media directories
                
                dir_path = dir_name  # In root, the relative path is just the directory name
                dir_path = dir_path.replace('\\', '/')  # Normalize path separators
                
                # Check if any files in this directory are referenced
                dir_has_referenced_files = False
                for rom_path in rom_paths:
                    if rom_path.startswith(dir_path + '/') or rom_path == dir_path:
                        dir_has_referenced_files = True
                        break
                
                if not dir_has_referenced_files:
                    full_dir_path = os.path.join(root, dir_name)
                    unused_dirs.append(full_dir_path)
    
    return unused_files, unused_dirs

def main():
    parser = argparse.ArgumentParser(description='Find unused ROM files and directories for a specific system')
    parser.add_argument('--roms-dir', default='roms', help='Path to ROMs directory (default: roms)')
    parser.add_argument('--system', required=True, help='System name to check (e.g., nes, amstradcpc)')
    parser.add_argument('--show-files', action='store_true', help='Show unused files')
    parser.add_argument('--show-dirs', action='store_true', help='Show unused directories')
    parser.add_argument('--show-all', action='store_true', help='Show both unused files and directories')
    parser.add_argument('--limit', type=int, help='Limit number of results shown')
    parser.add_argument('--delete', action='store_true', help='Delete unused files and directories (DANGEROUS!)')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be deleted without actually deleting (use with --delete)')
    
    args = parser.parse_args()
    
    # If no specific options, show both by default
    if not args.show_files and not args.show_dirs and not args.show_all:
        args.show_all = True
    
    print(f"Scanning ROMs directory: {args.roms_dir}")
    print(f"Checking system: {args.system}")
    print(f"Using gamelist: {args.roms_dir}/{args.system}/gamelist.xml")
    print("-" * 50)
    
    unused_files, unused_dirs = find_unused_roms(args.roms_dir, args.system)
    
    # Apply limit if specified
    if args.limit:
        unused_files = unused_files[:args.limit]
        unused_dirs = unused_dirs[:args.limit]
    
    if args.show_all or args.show_files:
        print(f"\nUnused files ({len(unused_files)}):")
        if unused_files:
            try:
                for file_path in sorted(unused_files):
                    print(f"  {file_path}")
            except BrokenPipeError:
                # Handle broken pipe gracefully (e.g., when using head)
                pass
        else:
            print("  None found")
    
    if args.show_all or args.show_dirs:
        print(f"\nUnused directories ({len(unused_dirs)}):")
        if unused_dirs:
            try:
                for dir_path in sorted(unused_dirs):
                    print(f"  {dir_path}/")
            except BrokenPipeError:
                # Handle broken pipe gracefully (e.g., when using head)
                pass
        else:
            print("  None found")
    
    print(f"\nSummary:")
    print(f"  Unused files: {len(unused_files)}")
    print(f"  Unused directories: {len(unused_dirs)}")
    
    # Handle deletion if requested
    if args.delete:
        if args.dry_run:
            print(f"\n🔍 DRY RUN - Files that would be deleted:")
            deleted_files = 0
            
            for file_path in unused_files:
                print(f"  Would delete file: {file_path}")
                deleted_files += 1
            
            print(f"\n🔍 DRY RUN Summary:")
            print(f"  Would delete {deleted_files} files")
            if unused_dirs:
                print(f"  Note: {len(unused_dirs)} unused directories found but will NOT be deleted (safety feature)")
        else:
            # Confirm deletion
            if len(unused_files) == 0:
                print(f"\n✅ No unused files to delete.")
                if unused_dirs:
                    print(f"  Note: {len(unused_dirs)} unused directories found but will NOT be deleted (safety feature)")
            else:
                print(f"\n⚠️  WARNING: You are about to delete {len(unused_files)} files!")
                print(f"   This action cannot be undone!")
                print(f"   Files to delete: {len(unused_files)}")
                if unused_dirs:
                    print(f"   Note: {len(unused_dirs)} unused directories found but will NOT be deleted (safety feature)")
                
                # Show first few items as examples
                if unused_files:
                    print(f"\n   Example files to delete:")
                    for file_path in unused_files[:5]:
                        print(f"     {file_path}")
                    if len(unused_files) > 5:
                        print(f"     ... and {len(unused_files) - 5} more files")
                
                # Ask for confirmation
                response = input(f"\n   Type 'yes' to confirm deletion, or anything else to cancel: ").strip().lower()
                
                if response == 'yes':
                    deleted_files = 0
                    errors = []
                    
                    print(f"\n🗑️  Deleting files...")
                    for file_path in unused_files:
                        try:
                            os.remove(file_path)
                            print(f"  ✅ Deleted file: {file_path}")
                            deleted_files += 1
                        except OSError as e:
                            error_msg = f"Failed to delete file {file_path}: {e}"
                            print(f"  ❌ {error_msg}")
                            errors.append(error_msg)
                    
                    print(f"\n✅ Deletion completed!")
                    print(f"  Successfully deleted {deleted_files} files")
                    
                    if errors:
                        print(f"\n⚠️  Errors encountered:")
                        for error in errors:
                            print(f"    {error}")
                else:
                    print(f"\n❌ Deletion cancelled.")

if __name__ == "__main__":
    main()