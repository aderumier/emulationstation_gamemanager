#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Custom Scraper Service - Local database scrapper for custom JSON databases
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
from difflib import SequenceMatcher
from game_utils import normalize_game_name, calculate_similarity

class CustomScraperService:
    def __init__(self, config: Dict, scrappers_config: Dict = None, systems_config: Dict = None):
        self.config = config
        self.scrappers_config = scrappers_config or {}
        self.systems_config = systems_config or {}
        self.logger = logging.getLogger(__name__)
        
        # Custom database path
        self.db_path = 'var/db/custom'
        
        # In-memory databases: {db_name: {game_id: {attributes}}}
        # db_name is the JSON filename without extension
        self.databases = {}
        
        # Global partitioned index: {db_name: {letter: {normalized_name: customid}}}
        self._global_similarity_index = {}
        
        # Load all custom databases
        self._load_databases()
        
        # Try to load partitioned indexes from cache
        cache_file = os.path.join('var/cache', 'custom_partitioned_index.pkl')
        cache_exists = os.path.exists(cache_file)
        
        if cache_exists:
            # Cache exists, load it
            self._load_partitioned_indexes_from_cache()
        else:
            # Cache doesn't exist, rebuild in background thread
            print("🔍 Custom partitioned index cache not found, rebuilding in background thread...")
            self.logger.info("🔍 Custom partitioned index cache not found, rebuilding in background thread...")
            import threading
            rebuild_thread = threading.Thread(target=self._rebuild_index_in_background, daemon=True)
            rebuild_thread.start()
    
    def _load_databases(self):
        """Load all custom JSON databases into memory"""
        try:
            if not os.path.exists(self.db_path):
                self.logger.warning(f"Custom database path not found: {self.db_path}")
                os.makedirs(self.db_path, exist_ok=True)
                return
            
            # Get all JSON files in the custom directory
            json_files = [f for f in os.listdir(self.db_path) if f.endswith('.json')]
            
            for json_file in json_files:
                db_name = os.path.splitext(json_file)[0]
                file_path = os.path.join(self.db_path, json_file)
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        games_data = json.load(f)
                    
                    # Handle both dict format {game_id: game_data} and list format [{game_data}]
                    if isinstance(games_data, dict):
                        # Already in dict format with game_id as key
                        self.databases[db_name] = games_data
                    elif isinstance(games_data, list):
                        # Convert list to dict - need to find the key field
                        games_dict = {}
                        for game in games_data:
                            if isinstance(game, dict):
                                # Try to find a unique identifier
                                # Check common fields: 'id', 'name', 'url', or first key
                                game_id = None
                                if 'id' in game:
                                    game_id = str(game['id'])
                                elif 'name' in game:
                                    # Use name as ID if no id field
                                    game_id = game['name']
                                elif 'url' in game:
                                    # Extract ID from URL if available
                                    url = game['url']
                                    # Try to extract slug from URL
                                    game_id = url.split('/')[-1] if '/' in url else url
                                else:
                                    # Use first key as ID
                                    game_id = list(game.keys())[0] if game.keys() else None
                                
                                if game_id:
                                    games_dict[str(game_id)] = game
                        
                        self.databases[db_name] = games_dict
                    
                    self.logger.info(f"Loaded {len(self.databases[db_name])} games for custom database: {db_name}")
                    
                except Exception as e:
                    self.logger.error(f"Error loading {json_file}: {e}")
                    continue
            
            self.logger.info(f"Loaded {len(self.databases)} custom databases")
            
        except Exception as e:
            self.logger.error(f"Error loading custom databases: {e}")
    
    def _rebuild_index_in_background(self):
        """Rebuild partitioned indexes in background thread"""
        try:
            print("🔧 [Background] Building partitioned similarity indexes for all custom databases...")
            self.logger.info("🔧 [Background] Building partitioned similarity indexes for all custom databases...")
            start_time = time.time()
            
            # Build the index
            self._build_all_partitioned_indexes()
            
            # Save to cache after building
            self._save_partitioned_indexes_to_cache()
            
            end_time = time.time()
            print(f"✅ [Background] Custom partitioned index rebuild completed in {end_time - start_time:.2f} seconds!")
            self.logger.info(f"✅ [Background] Custom partitioned index rebuild completed in {end_time - start_time:.2f} seconds!")
            
        except Exception as e:
            print(f"❌ [Background] Error rebuilding partitioned indexes: {e}")
            self.logger.error(f"[Background] Error rebuilding partitioned indexes: {e}")
            import traceback
            traceback.print_exc()
    
    def _build_all_partitioned_indexes(self):
        """Build partitioned similarity indexes for all loaded databases during startup"""
        try:
            print("🔧 Building partitioned similarity indexes for all custom databases...")
            self.logger.info("🔧 Building partitioned similarity indexes for all custom databases...")
            start_time = time.time()
            
            total_databases = len(self.databases)
            processed_databases = 0
            
            # Create a new index (don't merge with existing - atomic replacement)
            new_index = {}
            
            for db_name, games_dict in self.databases.items():
                print(f"🔧 Building partitioned index for {db_name} ({len(games_dict)} games)...")
                self.logger.info(f"🔧 Building partitioned index for {db_name} ({len(games_dict)} games)...")
                
                # Initialize database index
                new_index[db_name] = {}
                
                for game_id, game_data in games_dict.items():
                    # Try to find game name field (common variations)
                    game_name = None
                    if isinstance(game_data, dict):
                        # Check common name fields
                        for name_field in ['name', 'title', 'game_name', 'gameName', 'Name', 'Title']:
                            if name_field in game_data and game_data[name_field]:
                                game_name = str(game_data[name_field])
                                break
                    
                    if game_name:
                        # Don't remove parentheses to preserve version info (e.g., "Game (ECS)" vs "Game (AGA)")
                        normalized_title = normalize_game_name(game_name, remove_paranthesis=False, remove_articles=False)
                        if normalized_title:
                            normalized_title = normalized_title.strip()  # Ensure no leading/trailing whitespace
                            first_char = normalized_title[0] if normalized_title else 'other'
                            if first_char not in new_index[db_name]:
                                new_index[db_name][first_char] = {}
                            # Store normalized_name -> customid mapping
                            # If key already exists, log a warning (shouldn't happen but helps debug)
                            if normalized_title in new_index[db_name][first_char]:
                                existing_id = new_index[db_name][first_char][normalized_title]
                                if existing_id != game_id:
                                    print(f"⚠️ WARNING: Duplicate normalized key '{normalized_title}' in {db_name} partition '{first_char}': existing_id={existing_id}, new_id={game_id}")
                            new_index[db_name][first_char][normalized_title] = game_id
                
                processed_databases += 1
                partition_count = len(new_index[db_name])
                print(f"✅ Partitioned index built for {db_name} ({partition_count} partitions)")
                self.logger.info(f"✅ Partitioned index built for {db_name} ({partition_count} partitions)")
            
            # Replace the old index with the new one atomically
            self._global_similarity_index = new_index
            
            end_time = time.time()
            print(f"✅ All partitioned similarity indexes built successfully in {end_time - start_time:.2f} seconds!")
            print(f"📊 Processed {processed_databases} custom databases with partitioned indexes")
            self.logger.info(f"✅ All partitioned similarity indexes built successfully in {end_time - start_time:.2f} seconds!")
            self.logger.info(f"📊 Processed {processed_databases} custom databases with partitioned indexes")
            
        except Exception as e:
            print(f"❌ Error building partitioned indexes: {e}")
            self.logger.error(f"Error building partitioned indexes: {e}")
    
    def _save_partitioned_indexes_to_cache(self):
        """Save partitioned indexes to cache file for faster startup"""
        try:
            import pickle
            import os
            
            cache_dir = 'var/cache'
            os.makedirs(cache_dir, exist_ok=True)
            cache_file = os.path.join(cache_dir, 'custom_partitioned_index.pkl')
            
            # Convert index to dictionaries for pickling
            cache_data = {}
            for db_name, db_index in self._global_similarity_index.items():
                cache_data[db_name] = {}
                for letter, normalized_dict in db_index.items():
                    cache_data[db_name][letter] = normalized_dict
            
            with open(cache_file, 'wb') as f:
                pickle.dump(cache_data, f)
            
            print(f"✅ Saved custom partitioned index to {cache_file}")
            self.logger.info(f"✅ Saved custom partitioned index to {cache_file}")
            
        except Exception as e:
            print(f"⚠️ Warning: Failed to save custom partitioned index cache: {e}")
            self.logger.warning(f"Failed to save custom partitioned index cache: {e}")
    
    def _load_partitioned_indexes_from_cache(self):
        """Load partitioned indexes from cache file"""
        try:
            import pickle
            import os
            
            cache_file = os.path.join('var/cache', 'custom_partitioned_index.pkl')
            if not os.path.exists(cache_file):
                print("🔍 No custom partitioned index cache found, will build from scratch")
                self.logger.info("🔍 No custom partitioned index cache found, will build from scratch")
                return False
            
            with open(cache_file, 'rb') as f:
                cache_data = pickle.load(f)
            
            # Convert dictionaries back to index structure
            # Handle both old format (list of items) and new format (dict)
            self._global_similarity_index = {}
            for db_name, db_index in cache_data.items():
                self._global_similarity_index[db_name] = {}
                for letter, data in db_index.items():
                    if isinstance(data, dict):
                        # New format: {normalized_name: customid}
                        self._global_similarity_index[db_name][letter] = data
                    elif isinstance(data, list):
                        # Old format: list of items, convert to dict
                        normalized_dict = {}
                        for item in data:
                            if isinstance(item, dict):
                                normalized_dict[item.get('normalized', '')] = item.get('game_id', '')
                            else:
                                # Handle namedtuple format (if present)
                                try:
                                    normalized_dict[item.normalized] = item.game_id
                                except AttributeError:
                                    pass
                        self._global_similarity_index[db_name][letter] = normalized_dict
            
            print(f"✅ Loaded custom partitioned index from cache")
            self.logger.info(f"✅ Loaded custom partitioned index from cache")
            return True
            
        except Exception as e:
            print(f"⚠️ Warning: Failed to load custom partitioned index cache: {e}")
            self.logger.warning(f"Failed to load custom partitioned index cache: {e}")
            return False
    
    def get_available_databases(self) -> List[str]:
        """Get list of available custom database names"""
        return list(self.databases.keys())
    
    def get_game_by_id(self, db_name: str, game_id: str) -> Optional[Dict]:
        """Get game data by database name and game ID"""
        if db_name in self.databases:
            return self.databases[db_name].get(game_id)
        return None
    
    def find_game_exact(self, db_name: str, game_name: str) -> Optional[tuple]:
        """
        Find a game in the custom database by exact title match using partitioned index
        
        Args:
            db_name: Name of the custom database (JSON filename without extension)
            game_name: Game name to search for
        
        Returns:
            Tuple of (game_id, game_data) if exact match found, None otherwise
        """
        if db_name not in self.databases:
            self.logger.warning(f"Database {db_name} not found")
            return None
        
        if db_name not in self._global_similarity_index:
            self.logger.warning(f"No index found for database {db_name}")
            return None
        
        # Normalize the search name (keep parentheses to match versioned games)
        normalized_search = normalize_game_name(game_name, remove_paranthesis=False, remove_articles=False)
        if not normalized_search:
            self.logger.debug(f"Normalized search is empty for '{game_name}'")
            return None
        
        # Get partition based on first character
        first_char = normalized_search[0] if normalized_search else 'other'
        
        # Search in the appropriate partition for exact match
        if first_char in self._global_similarity_index[db_name]:
            partition_dict = self._global_similarity_index[db_name][first_char]
            if normalized_search in partition_dict:
                game_id = partition_dict[normalized_search]
                game_data = self.databases[db_name].get(game_id, {})
                return (game_id, game_data)
        
        return None
    
    def find_best_matches(self, db_name: str, game_name: str, max_results: int = 10, min_similarity: float = 0.0) -> List[Dict]:
        """
        Find best matching games in a specific custom database
        
        Args:
            db_name: Name of the custom database (JSON filename without extension)
            game_name: Game name to search for
            max_results: Maximum number of results to return
            min_similarity: Minimum similarity threshold (0.0 to 1.0)
        
        Returns:
            List of dicts with 'game_id', 'name', 'similarity', and 'game_data'
        """
        if db_name not in self.databases:
            self.logger.warning(f"Database {db_name} not found")
            return []
        
        if db_name not in self._global_similarity_index:
            self.logger.warning(f"No index found for database {db_name}")
            return []
        
        # Normalize the search name (keep parentheses to match versioned games)
        normalized_search = normalize_game_name(game_name, remove_paranthesis=False, remove_articles=True)
        if not normalized_search:
            return []
        
        # Get partition based on first character
        first_char = normalized_search[0] if normalized_search else 'other'
        
        # Get candidates from the appropriate partition
        candidates = []
        if first_char in self._global_similarity_index[db_name]:
            partition_dict = self._global_similarity_index[db_name][first_char]
            # Convert dict to list of (normalized_name, game_id) tuples
            candidates = [(norm_name, game_id) for norm_name, game_id in partition_dict.items()]
        else:
            # If partition doesn't exist, search all partitions (fallback)
            for partition_dict in self._global_similarity_index[db_name].values():
                candidates.extend([(norm_name, game_id) for norm_name, game_id in partition_dict.items()])
        
        # Calculate similarity for each candidate
        matches = []
        for normalized_name, game_id in candidates:
            similarity = calculate_similarity(normalized_search, normalized_name)
            if similarity >= min_similarity:
                game_data = self.databases[db_name].get(game_id, {})
                # Get original game name from game_data
                game_name = game_data.get('name', normalized_name)
                matches.append({
                    'game_id': game_id,
                    'name': game_name,
                    'similarity': similarity,
                    'game_data': game_data
                })
        
        # Sort by similarity (descending) and return top results
        matches.sort(key=lambda x: x['similarity'], reverse=True)
        return matches[:max_results]
    
    def get_media_url(self, db_name: str, game_id: str, media_field: str) -> Optional[str]:
        """
        Get media URL for a specific game and media field
        
        Args:
            db_name: Name of the custom database
            game_id: Game ID
            media_field: Media field name (e.g., 'boxfront', 'boxback', 'titleshot', 'screenshot', 'image')
        
        Returns:
            Media URL (first item if array) or None if not found
        """
        game_data = self.get_game_by_id(db_name, game_id)
        if not game_data:
            return None
        
        # Check common field name variations
        field_variations = [
            media_field,
            media_field.lower(),
            media_field.upper(),
            media_field.capitalize(),
        ]
        
        for field in field_variations:
            if field in game_data and game_data[field]:
                value = game_data[field]
                # Handle arrays - return first item for backward compatibility
                if isinstance(value, list):
                    if len(value) > 0:
                        return value[0] if isinstance(value[0], str) else None
                    return None
                # Return single value as-is
                return value if isinstance(value, str) else None
        
        return None
    
    def get_media_urls(self, db_name: str, game_id: str, media_field: str) -> List[str]:
        """
        Get media URLs for a specific game and media field (always returns a list)
        
        Args:
            db_name: Name of the custom database
            game_id: Game ID
            media_field: Media field name (e.g., 'boxfront', 'boxback', 'titleshot', 'screenshot', 'image')
        
        Returns:
            List of media URLs (empty list if not found)
        """
        game_data = self.get_game_by_id(db_name, game_id)
        if not game_data:
            return []
        
        # Check common field name variations
        field_variations = [
            media_field,
            media_field.lower(),
            media_field.upper(),
            media_field.capitalize(),
        ]
        
        for field in field_variations:
            if field in game_data and game_data[field]:
                value = game_data[field]
                # Handle arrays - return as list
                if isinstance(value, list):
                    # Filter to only include string URLs
                    return [url for url in value if isinstance(url, str)]
                # Convert single value to list
                if isinstance(value, str):
                    return [value]
        
        return []

