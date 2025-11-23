#!/usr/bin/env python3
"""
Generate genres.json from scrapper_genre_mapping.json ScreenScraper mapped values.
This ensures genres.json contains only the standardized mapped genre names.
"""

import json
import os
import sys

def generate_genres_json():
    """Generate genres.json from ScreenScraper mapped values."""
    
    # Get the project root directory (parent of tools/)
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Paths
    mapping_path = os.path.join(project_root, 'var', 'config', 'scrapper_genre_mapping.json')
    genres_path = os.path.join(project_root, 'var', 'config', 'genres.json')
    
    # Check if mapping file exists
    if not os.path.exists(mapping_path):
        print(f"❌ Error: Mapping file not found: {mapping_path}")
        sys.exit(1)
    
    # Load the mapping file
    print(f"📖 Loading mapping file: {mapping_path}")
    with open(mapping_path, 'r', encoding='utf-8') as f:
        mapping_data = json.load(f)
    
    # Get ScreenScraper mapped values
    screenscraper_map = mapping_data.get('screenscraper', {}).get('map', {})
    
    if not screenscraper_map:
        print("❌ Error: No ScreenScraper mapping found in mapping file")
        sys.exit(1)
    
    # Extract all unique mapped values (the values, not the keys)
    mapped_values = set(screenscraper_map.values())
    
    # Sort alphabetically for consistency
    sorted_genres = sorted(mapped_values)
    
    print(f"✅ Found {len(sorted_genres)} unique mapped genres from ScreenScraper")
    
    # Create var/config directory if it doesn't exist
    os.makedirs(os.path.dirname(genres_path), exist_ok=True)
    
    # Write genres.json
    print(f"💾 Writing genres to: {genres_path}")
    with open(genres_path, 'w', encoding='utf-8') as f:
        json.dump(sorted_genres, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Successfully generated {genres_path} with {len(sorted_genres)} genres")
    
    # Show some examples
    print("\n📋 Sample genres (first 10):")
    for i, genre in enumerate(sorted_genres[:10], 1):
        print(f"  {i}. {genre}")
    
    # Show genres with commas
    genres_with_commas = [g for g in sorted_genres if ',' in g]
    if genres_with_commas:
        print(f"\n📋 Genres with commas in name ({len(genres_with_commas)}):")
        for genre in genres_with_commas[:10]:
            print(f"  - {genre}")

if __name__ == '__main__':
    generate_genres_json()

