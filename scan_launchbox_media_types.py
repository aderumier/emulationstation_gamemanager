#!/usr/bin/env python3
"""
Scan LaunchBox metadata cache to extract all unique media types
and save them to a cache file for use in the configuration modal.
"""

import os
import json
import xml.etree.ElementTree as ET
from collections import Counter

def get_launchbox_metadata_path():
    """Get the path to the LaunchBox metadata file"""
    return os.path.join('var', 'db', 'launchbox', 'Metadata.xml')

def scan_media_types():
    """Scan the LaunchBox metadata cache for all unique media types"""
    metadata_path = get_launchbox_metadata_path()
    
    if not os.path.exists(metadata_path):
        print(f"❌ LaunchBox metadata not found at {metadata_path}")
        return []
    
    print(f"🔍 Scanning LaunchBox metadata at {metadata_path}")
    
    try:
        # Parse the Metadata.xml
        tree = ET.parse(metadata_path)
        root = tree.getroot()
        
        # Find all GameImage entries
        all_game_images = root.findall('.//GameImage')
        print(f"📊 Found {len(all_game_images)} GameImage entries")
        
        # Extract all unique media types
        media_types = set()
        type_counts = Counter()
        
        for game_image in all_game_images:
            type_elem = game_image.find('Type')
            if type_elem is not None and type_elem.text:
                media_type = type_elem.text.strip()
                if media_type:
                    media_types.add(media_type)
                    type_counts[media_type] += 1
        
        # Convert to sorted list
        sorted_types = sorted(media_types)
        
        print(f"✅ Found {len(sorted_types)} unique media types:")
        for media_type in sorted_types:
            count = type_counts[media_type]
            print(f"  - {media_type}: {count} images")
        
        return sorted_types
        
    except Exception as e:
        print(f"❌ Error scanning metadata: {e}")
        return []

def save_media_types_cache(media_types):
    """Save the media types to a cache file"""
    cache_dir = os.path.join('var', 'db', 'launchbox')
    os.makedirs(cache_dir, exist_ok=True)
    
    cache_file = os.path.join(cache_dir, 'mediatype.json')
    
    cache_data = {
        'media_types': media_types,
        'total_count': len(media_types),
        'last_updated': None  # Will be set by the calling code
    }
    
    try:
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Saved media types cache to {cache_file}")
        return True
        
    except Exception as e:
        print(f"❌ Error saving cache: {e}")
        return False

def main():
    """Main function"""
    print("🚀 LaunchBox Media Types Scanner")
    print("=" * 40)
    
    # Scan for media types
    media_types = scan_media_types()
    
    if not media_types:
        print("❌ No media types found")
        return 1
    
    # Save to cache
    if save_media_types_cache(media_types):
        print("✅ Media types cache created successfully")
        return 0
    else:
        print("❌ Failed to create media types cache")
        return 1

if __name__ == '__main__':
    exit(main())

