#!/usr/bin/env python3
import sys
import argparse
import xml.etree.ElementTree as ET
from pathlib import Path

def get_referenced_roms(gamelist_path, directory):
    """Parse gamelist.xml and return a set of absolute paths to referenced ROMs."""
    referenced = set()
    try:
        tree = ET.parse(gamelist_path)
        root = tree.getroot()
        for game in root.findall(".//game"):
            path_elem = game.find("path")
            if path_elem is not None and path_elem.text:
                rel_path = path_elem.text
                if rel_path.startswith("./"):
                    rel_path = rel_path[2:]
                
                # Resolve relative to the directory containing gamelist.xml
                abs_path = (directory / rel_path).resolve()
                referenced.add(str(abs_path))
    except Exception as e:
        print(f"Error parsing {gamelist_path}: {e}", file=sys.stderr)
        sys.exit(1)
        
    return referenced

def main():
    parser = argparse.ArgumentParser(description="Delete ROM files not referenced in gamelist.xml.")
    parser.add_argument("directory", help="The directory containing gamelist.xml and ROM files.")
    parser.add_argument("extension", help="The ROM file extension to check (e.g., .zip, nes, .iso).")
    parser.add_argument("--dry-run", action="store_true", help="Print files that would be deleted without actually deleting them.")
    
    args = parser.parse_args()
    
    directory = Path(args.directory).resolve()
    extension = args.extension.lower()
    if not extension.startswith("."):
        extension = "." + extension
        
    if not directory.is_dir():
        print(f"Error: Directory {directory} does not exist.", file=sys.stderr)
        sys.exit(1)
        
    gamelist_path = directory / "gamelist.xml"
    if not gamelist_path.exists():
        print(f"Error: gamelist.xml not found in {directory}.", file=sys.stderr)
        sys.exit(1)
        
    print(f"Parsing {gamelist_path}...")
    referenced_roms = get_referenced_roms(gamelist_path, directory)
    print(f"Found {len(referenced_roms)} referenced ROMs in gamelist.xml.")
    
    print(f"Scanning for '{extension}' files in {directory} and subdirectories...")
    all_rom_files = list(directory.rglob(f"*{extension}"))
    
    deleted_count = 0
    unknown_files = []
    
    for rom_path in all_rom_files:
        if not rom_path.is_file():
            continue
            
        abs_rom_path = str(rom_path.resolve())
        if abs_rom_path not in referenced_roms:
            unknown_files.append(rom_path)
            
    if not unknown_files:
        print("No unknown ROMs found.")
        return
        
    for rom_path in unknown_files:
        if args.dry_run:
            print(f"[DRY-RUN] Would delete: {rom_path}")
        else:
            try:
                rom_path.unlink()
                print(f"Deleted: {rom_path}")
                deleted_count += 1
            except Exception as e:
                print(f"Error deleting {rom_path}: {e}", file=sys.stderr)
                
    if args.dry_run:
        print(f"Dry run complete. {len(unknown_files)} files would be deleted.")
    else:
        print(f"Done. Deleted {deleted_count} unknown ROM(s).")

if __name__ == "__main__":
    main()
