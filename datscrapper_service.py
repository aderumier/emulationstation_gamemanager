#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DAT Scrapper Service - Local DAT file scrapper for game metadata
Copyright (C) 2024 Alexandre Derumier <aderumier@gmail.com>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import json
import os
import xml.etree.ElementTree as ET
import time
import logging
from typing import Dict, List, Optional, Any
from difflib import SequenceMatcher
from collections import namedtuple
from game_utils import normalize_game_name, calculate_similarity

# Lightweight namedtuple for DAT entries
DATEntry = namedtuple('DATEntry', ['name', 'normalized', 'description', 'year', 'publisher', 'developer', 'manufacturer', 'genre'])

class DATScrapperService:
    def __init__(self, config: Dict, scrappers_config: Dict = None, systems_config: Dict = None):
        self.config = config
        self.scrappers_config = scrappers_config or {}
        self.systems_config = systems_config or {}
        self.logger = logging.getLogger(__name__)
        
        # DAT files path
        self.dat_path = 'var/db/dats'
        
        # In-memory DAT data cache
        self.dat_cache = {}  # {system_name: {rom_name: DATEntry}}
        self.dat_cache_time = {}  # {system_name: timestamp}
        
        # Cache duration (30 minutes)
        self.cache_duration = 30 * 60
        
        # Ensure DAT directory exists
        os.makedirs(self.dat_path, exist_ok=True)
        
        self.logger.info(f"DAT Scrapper service initialized with {len(self.systems_config)} systems configured")
    
    def load_dat_file(self, system_name: str) -> Dict[str, DATEntry]:
        """Load DAT file for a specific system"""
        try:
            print(f"🔧 DEBUG: load_dat_file called for system '{system_name}'")
            
            # Check if we have a cached version
            if system_name in self.dat_cache:
                cache_time = self.dat_cache_time.get(system_name, 0)
                if time.time() - cache_time < self.cache_duration:
                    print(f"🔧 DEBUG: Using cached DAT data for {system_name}")
                    return self.dat_cache[system_name]
            
            # Get DAT file path from systems config
            system_config = self.systems_config.get(system_name, {})
            print(f"🔧 DEBUG: System config for '{system_name}': {system_config}")
            dat_file = system_config.get('dat_file')
            print(f"🔧 DEBUG: DAT file configured: '{dat_file}'")
            
            if not dat_file:
                print(f"⚠️ No DAT file configured for system {system_name}")
                return {}
            
            dat_file_path = os.path.join(self.dat_path, dat_file)
            print(f"🔧 DEBUG: Full DAT file path: '{dat_file_path}'")
            
            if not os.path.exists(dat_file_path):
                print(f"⚠️ DAT file not found: {dat_file_path}")
                return {}
            
            self.logger.info(f"Loading DAT file: {dat_file_path}")
            
            # Parse XML file
            tree = ET.parse(dat_file_path)
            root = tree.getroot()
            
            def local_name(tag):
                """Return local part of tag (strip XML namespace if present)."""
                return tag.split('}')[-1] if tag and '}' in tag else (tag or '')
            
            dat_entries = {}
            
            # Parse each machine/game entry (handle both formats and XML namespaces)
            entries = []
            for elem in root.iter():
                ln = local_name(elem.tag)
                if ln == 'machine':
                    entries.append(elem)
                elif ln == 'game':
                    entries.append(elem)
            if entries:
                # Prefer calling it "machine" if we found at least one machine
                first_tag = local_name(entries[0].tag)
                print(f"🔧 DEBUG: Using <{first_tag}> format for DAT file ({len(entries)} entries)")
            else:
                print(f"🔧 DEBUG: No <machine> or <game> elements found in DAT (check XML namespace/structure)")
            
            def find_child(elem, local_tag_name):
                """Find first child element with given local tag name (ignores namespace)."""
                for child in elem:
                    if local_name(child.tag) == local_tag_name:
                        return child
                return None
            
            for entry in entries:
                rom_name = entry.get('name', '').strip()
                if not rom_name:
                    continue
                # Index by machine name without extension (e.g. "cnonball.zip" -> "cnonball")
                rom_key = os.path.splitext(os.path.basename(rom_name))[0]
                
                # Extract metadata (find by local name so namespaced XML works)
                description = find_child(entry, 'description')
                description_text = description.text.strip() if description is not None and description.text else ''
                
                year = find_child(entry, 'year')
                year_text = year.text.strip() if year is not None and year.text else ''
                
                publisher = find_child(entry, 'publisher')
                publisher_text = publisher.text.strip() if publisher is not None and publisher.text else ''
                
                developer = find_child(entry, 'developer')
                developer_text = developer.text.strip() if developer is not None and developer.text else ''
                
                manufacturer = find_child(entry, 'manufacturer')
                manufacturer_text = manufacturer.text.strip() if manufacturer is not None and manufacturer.text else ''
                
                genre = find_child(entry, 'genre')
                genre_text = genre.text.strip() if genre is not None and genre.text else ''
                
                # Create normalized name for matching
                normalized_name = normalize_game_name(description_text)
                
                date_entry = DATEntry(
                    name=description_text,
                    normalized=normalized_name,
                    description=description_text,
                    year=year_text,
                    publisher=publisher_text,
                    developer=developer_text,
                    manufacturer=manufacturer_text,
                    genre=genre_text
                )
                
                # Store by machine name without extension so ROM "cnonball.zip" matches machine name "cnonball.zip"
                dat_entries[rom_key] = date_entry
            
            # Cache the results
            self.dat_cache[system_name] = dat_entries
            self.dat_cache_time[system_name] = time.time()
            
            self.logger.info(f"Loaded {len(dat_entries)} entries from DAT file for {system_name}")
            return dat_entries
            
        except Exception as e:
            self.logger.error(f"Error loading DAT file for {system_name}: {e}")
            return {}
    
    def find_game_by_rom_name(self, system_name: str, rom_name: str) -> Optional[DATEntry]:
        """Find a game entry by ROM filename (without extension)"""
        try:
            print(f"🔧 DEBUG: find_game_by_rom_name called with system_name='{system_name}', rom_name='{rom_name}'")
            dat_entries = self.load_dat_file(system_name)
            print(f"🔧 DEBUG: Loaded {len(dat_entries)} DAT entries for system '{system_name}'")
            
            # Remove file extension from rom_name for matching
            rom_filename = os.path.basename(rom_name)  # Extract filename without path
            rom_base_name = os.path.splitext(rom_filename)[0]  # Remove extension
            print(f"🔧 DEBUG: Looking for ROM base name: '{rom_base_name}'")
            
            # Direct match first
            if rom_base_name in dat_entries:
                print(f"🔧 DEBUG: Found direct match for '{rom_base_name}'")
                return dat_entries[rom_base_name]
            
            # Try case-insensitive match
            for key, entry in dat_entries.items():
                if key.lower() == rom_base_name.lower():
                    print(f"🔧 DEBUG: Found case-insensitive match for '{rom_base_name}' -> '{key}'")
                    return entry
            
            print(f"🔧 DEBUG: No match found for '{rom_base_name}'")
            print(f"🔧 DEBUG: First 10 DAT entries: {list(dat_entries.keys())[:10]}")
            return None
            
        except Exception as e:
            print(f"❌ Error finding game by ROM name: {e}")
            return None
    
    def search_games(self, system_name: str, query: str, limit: int = 20) -> List[DATEntry]:
        """Search for games in DAT file by name similarity"""
        try:
            dat_entries = self.load_dat_file(system_name)
            
            if not dat_entries:
                return []
            
            query_normalized = normalize_game_name(query)
            matches = []
            
            for rom_name, entry in dat_entries.items():
                # Calculate similarity with normalized names
                similarity = calculate_similarity(query_normalized, entry.normalized)
                
                if similarity > 0.3:  # Minimum similarity threshold
                    matches.append((entry, similarity))
            
            # Sort by similarity (highest first)
            matches.sort(key=lambda x: x[1], reverse=True)
            
            # Return top matches
            return [entry for entry, _ in matches[:limit]]
            
        except Exception as e:
            self.logger.error(f"Error searching games: {e}")
            return []
    
    def clear_cache(self, system_name: str = None):
        """Clear DAT cache for specific system or all systems"""
        if system_name:
            self.dat_cache.pop(system_name, None)
            self.dat_cache_time.pop(system_name, None)
            self.logger.info(f"Cleared DAT cache for {system_name}")
        else:
            self.dat_cache.clear()
            self.dat_cache_time.clear()
            self.logger.info("Cleared all DAT cache")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_entries = sum(len(entries) for entries in self.dat_cache.values())
        return {
            'cached_systems': len(self.dat_cache),
            'total_entries': total_entries,
            'cache_times': self.dat_cache_time.copy()
        }
