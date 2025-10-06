#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Launchbox Service - Local database scrapper for Launchbox
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
import re
import time
import logging
from typing import Dict, List, Optional, Any
from collections import namedtuple
from game_utils import normalize_game_name, calculate_similarity

# Lightweight namedtuple for search index entries
LaunchboxItem = namedtuple('LaunchboxItem', ['name', 'normalized', 'game_id', 'item_type'])

class LaunchboxService:
    def __init__(self, config: Dict, scrappers_config: Dict = None, systems_config: Dict = None, target_platform: str = None):
        self.config = config
        self.scrappers_config = scrappers_config or {}
        self.systems_config = systems_config or {}
        self.logger = logging.getLogger(__name__)
        
        # Launchbox metadata path
        self.metadata_path = config.get('launchbox_metadata_path', 'var/db/launchbox/Metadata.xml')
        
        # In-memory databases: {platform: {gameid: {attributes}}}
        self.databases = {}
        
        # Global partitioned similarity indexes: {platform: {first_char: [LaunchboxItem]}}
        # We maintain two indexes like the original implementation:
        # - _global_similarity_index_with_parens: with parentheses and articles (for exact matches)
        # - _global_similarity_index_no_parens: without parentheses (for similarity searches)
        # LaunchboxItem is lightweight namedtuple, full game_data stored separately
        self._global_similarity_index_with_parens = {}
        self._global_similarity_index_no_parens = {}
        
        # Memory optimization flags
        self._memory_efficient_mode = False
        self._large_platform_threshold = 1000  # Games threshold for memory-efficient mode (lowered for better memory usage)
        
        # Load Launchbox databases (all platforms or specific platform)
        self._load_databases(target_platform)
        
        # Build partitioned similarity indexes for loaded platforms during startup
        self._build_all_partitioned_indexes()
    
    def _load_databases(self, target_platform: str = None):
        """Load Launchbox platforms into memory (all platforms or specific platform)"""
        try:
            # For now, always load directly from XML to avoid import issues
            if target_platform:
                self.logger.info(f"Loading Launchbox data for platform '{target_platform}' from XML...")
                self._load_from_xml_direct(target_platform)
            else:
                self.logger.info("Loading Launchbox data for all platforms from XML...")
                self._load_from_xml_direct()
            
            self.logger.info(f"Loaded Launchbox data for {len(self.databases)} platforms")
            
        except Exception as e:
            self.logger.error(f"Error loading Launchbox databases: {e}")
    
    def _process_games_from_cache(self, global_metadata_cache):
        """Process games from the global metadata cache"""
        # Get mapping configuration
        mapping_config = self.scrappers_config.get('launchbox', {}).get('mapping', {})
        fields_to_load = set(['Name', 'Platform', 'DatabaseID'])  # Always load these core fields
        if mapping_config:
            fields_to_load.update(mapping_config.keys())
        
        # Process all games from global cache
        processed_count = 0
        for db_id, entry in global_metadata_cache.items():
            game_elem = entry.get('game')
            if game_elem is None:
                continue
            
            game_data = {}
            
            # Parse basic game fields from cached element
            for child in game_elem:
                tag = child.tag
                text = child.text.strip() if child.text else ''
                
                if tag in fields_to_load:
                    game_data[tag] = text
            
            platform = game_data.get('Platform')
            if not platform:
                continue
            
            # Initialize platform database if not exists
            if platform not in self.databases:
                self.databases[platform] = {}
            
            # Link alternate names to this game from cache
            alt_names = []
            for alt_elem in entry.get('alternate_names', []) or []:
                alt_name = alt_elem.find('AlternateName')
                if alt_name is not None and alt_name.text:
                    alt_names.append(alt_name.text.strip())
            game_data['AlternateNames'] = alt_names
            
            # Store game data
            self.databases[platform][db_id] = game_data
            processed_count += 1
        
        print(f"DEBUG: Processed {processed_count} games into {len(self.databases)} platforms")
    
    def _load_from_xml_direct(self, target_platform: str = None):
        """Load Launchbox data directly from XML file (standalone mode)"""
        import xml.etree.ElementTree as ET
        
        if not os.path.exists(self.metadata_path):
            self.logger.warning(f"Launchbox metadata file not found: {self.metadata_path}")
            return
        
        if target_platform:
            self.logger.info(f"Loading Launchbox data for platform '{target_platform}' from {self.metadata_path}...")
        else:
            self.logger.info(f"Loading Launchbox data for all platforms from {self.metadata_path}...")
        
        # Get mapping configuration
        mapping_config = self.scrappers_config.get('launchbox', {}).get('mapping', {})
        fields_to_load = set(['Name', 'Platform', 'DatabaseID'])  # Always load these core fields
        if mapping_config:
            fields_to_load.update(mapping_config.keys())
        
        # Process games using iterparse for memory efficiency
        processed_count = 0
        context = ET.iterparse(self.metadata_path, events=('start', 'end'))
        context = iter(context)
        event, root = next(context)
        
        for event, elem in context:
            if event == 'end' and elem.tag == 'Game':
                game_data = {}
                
                # Parse basic game fields
                for child in elem:
                    tag = child.tag
                    text = child.text.strip() if child.text else ''
                    
                    if tag in fields_to_load:
                        game_data[tag] = text
                
                platform = game_data.get('Platform')
                if not platform:
                    elem.clear()
                    continue
                
                # If target_platform is specified, only load that platform
                if target_platform and platform != target_platform:
                    elem.clear()
                    continue
                
                # Initialize platform database if not exists
                if platform not in self.databases:
                    self.databases[platform] = {}
                
                # Get alternate names
                alt_names = []
                for alt_elem in elem.findall('.//AlternateName'):
                    if alt_elem.text:
                        alt_names.append(alt_elem.text.strip())
                
                # Store only essential data to minimize memory usage
                db_id = game_data.get('DatabaseID', str(len(self.databases[platform])))
                essential_data = {
                    'Name': game_data.get('Name', ''),
                    'DatabaseID': db_id,
                    'AlternateNames': alt_names
                }
                
                # Only add other fields if they're actually needed for the mapping
                for field in fields_to_load:
                    if field not in ['Name', 'DatabaseID'] and field in game_data:
                        essential_data[field] = game_data[field]
                
                self.databases[platform][db_id] = essential_data
                processed_count += 1
                
                # Clear element to free memory
                elem.clear()
        
        if target_platform:
            self.logger.info(f"Processed {processed_count} games for platform '{target_platform}' from XML")
        else:
            self.logger.info(f"Processed {processed_count} games into {len(self.databases)} platforms from XML")
        
        # Check if platform is too large and enable memory-efficient mode
        if target_platform and processed_count > self._large_platform_threshold:
            self.logger.warning(f"Platform '{target_platform}' has {processed_count:,} games - enabling memory-efficient mode!")
            self._memory_efficient_mode = True
            self.logger.warning(f"Memory-efficient mode: Only essential data will be kept in memory for large platforms.")
    
    def _build_all_partitioned_indexes(self):
        """Build partitioned similarity indexes for loaded platforms during startup"""
        try:
            if len(self.databases) == 1:
                platform_name = list(self.databases.keys())[0]
                print(f"🔧 Building partitioned similarity indexes for platform '{platform_name}'...")
                self.logger.info(f"🔧 Building partitioned similarity indexes for platform '{platform_name}'...")
            else:
                print("🔧 Building partitioned similarity indexes for all Launchbox platforms...")
                self.logger.info("🔧 Building partitioned similarity indexes for all Launchbox platforms...")
            
            start_time = time.time()
            
            total_platforms = len(self.databases)
            processed_platforms = 0
            
            for platform_name, games_dict in self.databases.items():
                if processed_platforms < 5:  # Only show first 5 platforms in detail
                    print(f"🔧 Building partitioned indexes for {platform_name} ({len(games_dict)} games)...")
                self.logger.info(f"🔧 Building partitioned indexes for {platform_name} ({len(games_dict)} games)...")
                
                # Initialize platform indexes
                self._global_similarity_index_with_parens[platform_name] = {}
                self._global_similarity_index_no_parens[platform_name] = {}
                
                for game_id, game_data in games_dict.items():
                    # Index main name with both normalization methods
                    main_name = game_data.get('Name', '')
                    if main_name:
                        # Index with parentheses and articles (for exact matches)
                        normalized_with_parens = normalize_game_name(main_name, remove_paranthesis=False, remove_articles=False)
                        if normalized_with_parens:
                            first_char = normalized_with_parens[0] if normalized_with_parens else 'other'
                            if first_char not in self._global_similarity_index_with_parens[platform_name]:
                                self._global_similarity_index_with_parens[platform_name][first_char] = []
                            self._global_similarity_index_with_parens[platform_name][first_char].append(
                                LaunchboxItem(
                                    name=main_name,
                                    normalized=normalized_with_parens,
                                    game_id=game_id,
                                    item_type='main'
                                )
                            )
                        
                        # Index without parentheses (for similarity searches)
                        normalized_no_parens = normalize_game_name(main_name, remove_paranthesis=True, remove_articles=True)
                        if normalized_no_parens:
                            first_char = normalized_no_parens[0] if normalized_no_parens else 'other'
                            if first_char not in self._global_similarity_index_no_parens[platform_name]:
                                self._global_similarity_index_no_parens[platform_name][first_char] = []
                            self._global_similarity_index_no_parens[platform_name][first_char].append(
                                LaunchboxItem(
                                    name=main_name,
                                    normalized=normalized_no_parens,
                                    game_id=game_id,
                                    item_type='main'
                                )
                            )
                    
                    # Index alternate names with both normalization methods
                    alternate_names = game_data.get('AlternateNames', [])
                    for alt_name in alternate_names:
                        # Index with parentheses and articles
                        alt_normalized_with_parens = normalize_game_name(alt_name, remove_paranthesis=False, remove_articles=False)
                        if alt_normalized_with_parens:
                            first_char = alt_normalized_with_parens[0] if alt_normalized_with_parens else 'other'
                            if first_char not in self._global_similarity_index_with_parens[platform_name]:
                                self._global_similarity_index_with_parens[platform_name][first_char] = []
                            self._global_similarity_index_with_parens[platform_name][first_char].append(
                                LaunchboxItem(
                                    name=alt_name,
                                    normalized=alt_normalized_with_parens,
                                    game_id=game_id,
                                    item_type='alternate'
                                )
                            )
                        
                        # Index without parentheses
                        alt_normalized_no_parens = normalize_game_name(alt_name, remove_paranthesis=True, remove_articles=True)
                        if alt_normalized_no_parens:
                            first_char = alt_normalized_no_parens[0] if alt_normalized_no_parens else 'other'
                            if first_char not in self._global_similarity_index_no_parens[platform_name]:
                                self._global_similarity_index_no_parens[platform_name][first_char] = []
                            self._global_similarity_index_no_parens[platform_name][first_char].append(
                                LaunchboxItem(
                                    name=alt_name,
                                    normalized=alt_normalized_no_parens,
                                    game_id=game_id,
                                    item_type='alternate'
                                )
                            )
                
                processed_platforms += 1
                partition_count_with = len(self._global_similarity_index_with_parens[platform_name])
                partition_count_without = len(self._global_similarity_index_no_parens[platform_name])
                if processed_platforms <= 5:  # Only show first 5 platforms in detail
                    print(f"✅ Partitioned indexes built for {platform_name} (with_parens: {partition_count_with}, no_parens: {partition_count_without} partitions)")
                self.logger.info(f"✅ Partitioned indexes built for {platform_name} (with_parens: {partition_count_with}, no_parens: {partition_count_without} partitions)")
            
            end_time = time.time()
            if len(self.databases) == 1:
                platform_name = list(self.databases.keys())[0]
                print(f"✅ Partitioned similarity indexes built for platform '{platform_name}' in {end_time - start_time:.2f} seconds!")
                self.logger.info(f"✅ Partitioned similarity indexes built for platform '{platform_name}' in {end_time - start_time:.2f} seconds!")
            else:
                print(f"✅ All partitioned similarity indexes built successfully in {end_time - start_time:.2f} seconds!")
                print(f"📊 Processed {processed_platforms} platforms with partitioned indexes")
                self.logger.info(f"✅ All partitioned similarity indexes built successfully in {end_time - start_time:.2f} seconds!")
                self.logger.info(f"📊 Processed {processed_platforms} platforms with partitioned indexes")
            
            # Memory optimization: Clear full game data for large platforms
            if self._memory_efficient_mode:
                self.logger.info("🧹 Memory-efficient mode: Clearing full game data to save memory...")
                for platform_name in self.databases:
                    original_count = len(self.databases[platform_name])
                    # Keep only essential data: Name, DatabaseID, AlternateNames
                    essential_data = {}
                    for game_id, game_data in self.databases[platform_name].items():
                        essential_data[game_id] = {
                            'Name': game_data.get('Name', ''),
                            'DatabaseID': game_data.get('DatabaseID', ''),
                            'AlternateNames': game_data.get('AlternateNames', [])
                        }
                    self.databases[platform_name] = essential_data
                    self.logger.info(f"🧹 Platform '{platform_name}': Reduced from {original_count} full records to {len(essential_data)} essential records")
            
            # Additional memory optimization: Force garbage collection
            import gc
            gc.collect()
            self.logger.info("🧹 Forced garbage collection to free memory")
            
        except Exception as e:
            print(f"❌ Error building partitioned indexes: {e}")
            self.logger.error(f"Error building partitioned indexes: {e}")
    
    def find_game_exact(self, platform_name: str, game_title: str) -> Optional[Dict]:
        """Find a game in the Launchbox database by exact title match (for scrapper tasks)"""
        if platform_name not in self.databases:
            self.logger.warning(f"No Launchbox platform found: {platform_name}")
            return None
        
        # Try both normalization methods for exact matches
        # First try with parentheses and articles (more precise)
        normalized_with_parens = normalize_game_name(game_title, remove_paranthesis=False, remove_articles=False)
        if normalized_with_parens and platform_name in self._global_similarity_index_with_parens:
            first_char = normalized_with_parens[0] if normalized_with_parens else 'other'
            if first_char in self._global_similarity_index_with_parens[platform_name]:
                partition_items = self._global_similarity_index_with_parens[platform_name][first_char]
                for item in partition_items:
                    if item.normalized == normalized_with_parens:
                        game_data = self.databases[platform_name][item.game_id]
                        # Add match metadata
                        game_data['_match_type'] = item.item_type
                        game_data['_matched_name'] = item.name
                        return game_data
        
        # Fallback: try without parentheses
        normalized_no_parens = normalize_game_name(game_title, remove_paranthesis=True, remove_articles=True)
        if normalized_no_parens and platform_name in self._global_similarity_index_no_parens:
            first_char = normalized_no_parens[0] if normalized_no_parens else 'other'
            if first_char in self._global_similarity_index_no_parens[platform_name]:
                partition_items = self._global_similarity_index_no_parens[platform_name][first_char]
                for item in partition_items:
                    if item.normalized == normalized_no_parens:
                        game_data = self.databases[platform_name][item.game_id]
                        # Add match metadata
                        game_data['_match_type'] = item.item_type
                        game_data['_matched_name'] = item.name
                        return game_data
        
        return None
    
    def search_games(self, platform_name: str, query: str, limit: int = 10) -> List[Dict]:
        """Search for games by query string using global partitioned similarity search (for manual search)"""
        if platform_name not in self._global_similarity_index_no_parens:
            self.logger.warning(f"Partitioned index not found for platform: {platform_name}")
            return []
        
        # Use the no-parens index for similarity searches (like the original implementation)
        normalized_query = normalize_game_name(query, remove_paranthesis=True, remove_articles=True)
        if not normalized_query:
            return []
        
        # Get the first character to search in the right partition
        first_char = normalized_query[0]
        
        results = []
        
        # Search only in the matching partition
        if first_char in self._global_similarity_index_no_parens[platform_name]:
            partition_items = self._global_similarity_index_no_parens[platform_name][first_char]
            
            for item in partition_items:
                # Calculate similarity using configured algorithm
                # item is now a LaunchboxItem namedtuple, access with dot notation
                similarity = calculate_similarity(normalized_query, item.normalized)
                
                if similarity > 0.3:  # Lower threshold for search display
                    game_data = self.databases[platform_name][item.game_id]
                    results.append({
                        'id': item.game_id,
                        'title': game_data.get('Name', ''),
                        'platform': platform_name,
                        'score': round(similarity, 3),
                        'match_type': item.item_type,
                        'matched_name': item.name,
                        'game_data': game_data
                    })
        
        # Sort by similarity and return top results
        results.sort(key=lambda x: x['score'], reverse=True)
        return results[:limit]
    
    def find_game_by_id(self, platform_name: str, game_id: str) -> Optional[Dict]:
        """Find a game by platform and game ID (for existing launchboxid lookups)"""
        if platform_name not in self.databases:
            return None
        
        game_data = self.databases[platform_name].get(game_id)
        if game_data:
            # Add match metadata
            game_data['_match_type'] = 'launchboxid'
            game_data['_matched_name'] = game_data.get('Name', '')
        return game_data
    
    def get_game_by_id(self, platform_name: str, game_id: str) -> Optional[Dict]:
        """Get game data by platform and game ID (without match metadata)"""
        if platform_name not in self.databases:
            return None
        return self.databases[platform_name].get(game_id)
    
    def get_platforms(self) -> List[str]:
        """Get list of available platforms"""
        return list(self.databases.keys())
    
    def get_platform_game_count(self, platform_name: str) -> int:
        """Get number of games for a specific platform"""
        if platform_name not in self.databases:
            return 0
        return len(self.databases[platform_name])
    
    def get_platform_stats(self) -> Dict[str, int]:
        """Get statistics for all platforms"""
        return {platform: len(games) for platform, games in self.databases.items()}
    
    @classmethod
    def for_platform(cls, config: Dict, scrappers_config: Dict, systems_config: Dict, target_platform: str):
        """Create a LaunchboxService instance for a specific platform (optimized for worker processes)"""
        return cls(config, scrappers_config, systems_config, target_platform)
