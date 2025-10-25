#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MobyGames Service - Local database scrapper for MobyGames
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
from collections import namedtuple
from game_utils import normalize_game_name, calculate_similarity
# Removed web service dependency - web scraping now handled directly in task

# Lightweight namedtuple for search index entries
GameItem = namedtuple('GameItem', ['name', 'normalized', 'game_id'])

class MobyGamesService:
    def __init__(self, config: Dict, scrappers_config: Dict = None, systems_config: Dict = None):
        self.config = config
        self.scrappers_config = scrappers_config or {}
        self.systems_config = systems_config or {}
        self.logger = logging.getLogger(__name__)
        
        # Debug logging for systems_config
        self.logger.info(f"MobyGames service initialized with {len(self.systems_config)} systems configured")
        if 'namco23' in self.systems_config:
            self.logger.info(f"namco23 system config: {self.systems_config['namco23']}")
        else:
            self.logger.warning(f"namco23 not found in systems_config. Available systems: {list(self.systems_config.keys())}")
        
        # MobyGames database path
        self.db_path = 'var/db/mobygames'
        
        # Web scraping now handled directly in task
        
        # In-memory databases: {system: {gameid: {attributes}}}
        self.databases = {}
        
        # Global partitioned similarity index: {system: {first_char: [GameItem]}}
        # GameItem is lightweight namedtuple, full game_data stored separately
        # This single index handles both exact matches and similarity searches
        self._global_similarity_index = {}
        
        # Load all MobyGames databases
        self._load_databases()
        
        # Try to load partitioned indexes from cache, otherwise build them
        if not self._load_partitioned_indexes_from_cache():
            # Build partitioned similarity indexes for all systems during startup
            self._build_all_partitioned_indexes()
            # Save the indexes to cache for future use
            self._save_partitioned_indexes_to_cache()
    
    def _load_databases(self):
        """Load all MobyGames JSON databases into memory"""
        try:
            if not os.path.exists(self.db_path):
                self.logger.warning(f"MobyGames database path not found: {self.db_path}")
                return
            
            # Get all JSON files in the mobygames directory
            json_files = [f for f in os.listdir(self.db_path) if f.endswith('.json')]
            
            for json_file in json_files:
                system_name = os.path.splitext(json_file)[0]
                file_path = os.path.join(self.db_path, json_file)
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        games_data = json.load(f)
                    
                    # Convert list to dict with game ID as key
                    games_dict = {}
                    for game in games_data:
                        if isinstance(game, dict) and 'id' in game:
                            games_dict[game['id']] = game
                    
                    self.databases[system_name] = games_dict
                    
                    self.logger.info(f"Loaded {len(games_dict)} games for system: {system_name}")
                    
                except Exception as e:
                    self.logger.error(f"Error loading {json_file}: {e}")
                    continue
            
            self.logger.info(f"Loaded {len(self.databases)} MobyGames databases")
            
        except Exception as e:
            self.logger.error(f"Error loading MobyGames databases: {e}")
    
    def _build_all_partitioned_indexes(self):
        """Build partitioned similarity indexes for all loaded systems during startup"""
        try:
            print("🔧 Building partitioned similarity indexes for all MobyGames systems...")
            self.logger.info("🔧 Building partitioned similarity indexes for all MobyGames systems...")
            start_time = time.time()
            
            total_systems = len(self.databases)
            processed_systems = 0
            
            for system_name, games_dict in self.databases.items():
                print(f"🔧 Building partitioned index for {system_name} ({len(games_dict)} games)...")
                self.logger.info(f"🔧 Building partitioned index for {system_name} ({len(games_dict)} games)...")
                
                # Initialize system index
                self._global_similarity_index[system_name] = {}
                
                for game_id, game_data in games_dict.items():
                    if 'title' in game_data:
                        normalized_title = normalize_game_name(game_data['title'], remove_paranthesis=True, remove_articles=True)
                        if normalized_title:
                            first_char = normalized_title[0] if normalized_title else 'other'
                            if first_char not in self._global_similarity_index[system_name]:
                                self._global_similarity_index[system_name][first_char] = []
                            # Use lightweight GameItem namedtuple instead of dict
                            # Full game_data is already stored in self.databases[system_name][game_id]
                            self._global_similarity_index[system_name][first_char].append(
                                GameItem(
                                    name=game_data['title'],
                                    normalized=normalized_title,
                                    game_id=game_id
                                )
                            )
                
                processed_systems += 1
                partition_count = len(self._global_similarity_index[system_name])
                print(f"✅ Partitioned index built for {system_name} ({partition_count} partitions)")
                self.logger.info(f"✅ Partitioned index built for {system_name} ({partition_count} partitions)")
            
            end_time = time.time()
            print(f"✅ All partitioned similarity indexes built successfully in {end_time - start_time:.2f} seconds!")
            print(f"📊 Processed {processed_systems} systems with partitioned indexes")
            self.logger.info(f"✅ All partitioned similarity indexes built successfully in {end_time - start_time:.2f} seconds!")
            self.logger.info(f"📊 Processed {processed_systems} systems with partitioned indexes")
            
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
            cache_file = os.path.join(cache_dir, 'mobygames_partitioned_index.pkl')
            
            # Convert GameItem namedtuples to dictionaries for pickling
            cache_data = {}
            for system_name, system_index in self._global_similarity_index.items():
                cache_data[system_name] = {}
                for first_char, game_items in system_index.items():
                    cache_data[system_name][first_char] = [
                        {
                            'name': item.name,
                            'normalized': item.normalized,
                            'game_id': item.game_id
                        }
                        for item in game_items
                    ]
            
            with open(cache_file, 'wb') as f:
                pickle.dump(cache_data, f)
            
            print(f"✅ Saved MobyGames partitioned index to {cache_file}")
            self.logger.info(f"✅ Saved MobyGames partitioned index to {cache_file}")
            
        except Exception as e:
            print(f"⚠️ Warning: Failed to save MobyGames partitioned index cache: {e}")
            self.logger.warning(f"Failed to save MobyGames partitioned index cache: {e}")
    
    def _load_partitioned_indexes_from_cache(self):
        """Load partitioned indexes from cache file"""
        try:
            import pickle
            import os
            
            cache_file = os.path.join('var/cache', 'mobygames_partitioned_index.pkl')
            if not os.path.exists(cache_file):
                print("🔍 No MobyGames partitioned index cache found, will build from scratch")
                return False
            
            with open(cache_file, 'rb') as f:
                cache_data = pickle.load(f)
            
            # Convert dictionaries back to GameItem namedtuples
            self._global_similarity_index = {}
            for system_name, system_index in cache_data.items():
                self._global_similarity_index[system_name] = {}
                for first_char, game_items in system_index.items():
                    self._global_similarity_index[system_name][first_char] = [
                        GameItem(
                            name=item['name'],
                            normalized=item['normalized'],
                            game_id=item['game_id']
                        )
                        for item in game_items
                    ]
            
            total_partitions = sum(len(partitions) for partitions in self._global_similarity_index.values())
            print(f"✅ Loaded MobyGames partitioned index from cache ({len(self._global_similarity_index)} systems, {total_partitions} partitions)")
            self.logger.info(f"✅ Loaded MobyGames partitioned index from cache ({len(self._global_similarity_index)} systems, {total_partitions} partitions)")
            return True
            
        except Exception as e:
            print(f"⚠️ Warning: Failed to load MobyGames partitioned index cache: {e}")
            self.logger.warning(f"Failed to load MobyGames partitioned index cache: {e}")
            return False
    
    
    def reload_systems_config(self, systems_config: Dict):
        """Reload systems configuration after it has been updated"""
        self.systems_config = systems_config or {}
        self.logger.info(f"MobyGames service systems config reloaded with {len(self.systems_config)} systems")
        if 'namco23' in self.systems_config:
            self.logger.info(f"namco23 system config after reload: {self.systems_config['namco23']}")
        else:
            self.logger.warning(f"namco23 not found in reloaded systems_config. Available systems: {list(self.systems_config.keys())}")
    
    def get_mobygames_system(self, system_name: str) -> Optional[str]:
        """Get MobyGames system name from systems configuration"""
        if not self.systems_config:
            self.logger.warning(f"No systems_config loaded for MobyGames service")
            return None
        
        system_config = self.systems_config.get(system_name, {})
        mobygames_system = system_config.get('mobygames')
        
        self.logger.debug(f"System '{system_name}' config: {system_config}")
        self.logger.debug(f"MobyGames system for '{system_name}': {mobygames_system}")
        self.logger.debug(f"Available MobyGames databases: {list(self.databases.keys())}")
        
        if mobygames_system and mobygames_system in self.databases:
            return mobygames_system
        
        return None
    
    def find_game_exact(self, system_name: str, game_title: str) -> Optional[Dict]:
        """Find a game in the MobyGames database by exact title match (for scrapper tasks)"""
        mobygames_system = self.get_mobygames_system(system_name)
        if not mobygames_system:
            self.logger.warning(f"No MobyGames system configured for: {system_name}")
            return None
        
        # Normalize the search title
        normalized_search = normalize_game_name(game_title, remove_paranthesis=True, remove_articles=True)
        if not normalized_search:
            return None
        
        # First, search in the configured system using partitioned index
        if mobygames_system in self._global_similarity_index:
            first_char = normalized_search[0] if normalized_search else 'other'
            if first_char in self._global_similarity_index[mobygames_system]:
                partition_items = self._global_similarity_index[mobygames_system][first_char]
                for item in partition_items:
                    if item.normalized == normalized_search:
                        game_data = self.databases[mobygames_system][item.game_id]
                        # Add system information to the game data
                        game_data['system'] = mobygames_system
                        return game_data
        
        # If not found in configured system, search across all systems as fallback
        for system, partitions in self._global_similarity_index.items():
            first_char = normalized_search[0] if normalized_search else 'other'
            if first_char in partitions:
                partition_items = partitions[first_char]
                for item in partition_items:
                    if item.normalized == normalized_search:
                        game_data = self.databases[system][item.game_id]
                        # Add system information to the game data
                        game_data['system'] = system
                        return game_data
        
        return None

    def find_game_by_id(self, system_name: str, game_id: str) -> Optional[Dict]:
        """Find a game in the MobyGames database by ID"""
        mobygames_system = self.get_mobygames_system(system_name)
        if not mobygames_system:
            self.logger.warning(f"No MobyGames system configured for: {system_name}")
            return None
        
        if mobygames_system not in self.databases:
            return None
        
        # Try both string and integer versions of the ID
        game_id_str = str(game_id)
        try:
            game_id_int = int(game_id)
        except (ValueError, TypeError):
            game_id_int = None
        
        # Look up in databases - try integer first (as that's how they're stored)
        if game_id_int is not None and game_id_int in self.databases[mobygames_system]:
            return self.databases[mobygames_system][game_id_int]
        elif game_id_str in self.databases[mobygames_system]:
            return self.databases[mobygames_system][game_id_str]
        
        return None
    
    def find_game(self, system_name: str, game_title: str, similarity_threshold: float = 0.8) -> Optional[Dict]:
        """Find a game in MobyGames database by title - only searches in the configured system"""
        mobygames_system = self.get_mobygames_system(system_name)
        if not mobygames_system:
            self.logger.warning(f"No MobyGames system configured for: {system_name}")
            return None
        
        # Normalize the search title
        normalized_search = normalize_game_name(game_title, remove_paranthesis=True, remove_articles=True)
        if not normalized_search:
            return None
        
        # First try exact match using partitioned index
        if mobygames_system in self._global_similarity_index:
            first_char = normalized_search[0] if normalized_search else 'other'
            if first_char in self._global_similarity_index[mobygames_system]:
                partition_items = self._global_similarity_index[mobygames_system][first_char]
                for item in partition_items:
                    if item.normalized == normalized_search:
                        return self.databases[mobygames_system][item.game_id]
        
        # If no exact match, try similarity matching using partitioned index
        best_match = None
        best_similarity = 0.0
        
        if mobygames_system in self._global_similarity_index:
            first_char = normalized_search[0] if normalized_search else 'other'
            if first_char in self._global_similarity_index[mobygames_system]:
                partition_items = self._global_similarity_index[mobygames_system][first_char]
                for item in partition_items:
                    # Calculate similarity using configured algorithm
                    similarity = calculate_similarity(normalized_search, item.normalized)
                    
                    if similarity > best_similarity and similarity >= similarity_threshold:
                        best_similarity = similarity
                        best_match = self.databases[mobygames_system][item.game_id]
        
        return best_match
    
    def get_game_data(self, system_name: str, game_id: int) -> Optional[Dict]:
        """Get game data by system and game ID"""
        mobygames_system = self.get_mobygames_system(system_name)
        if not mobygames_system:
            return None
        
        return self.databases[mobygames_system].get(game_id)
    
    def get_available_systems(self) -> List[str]:
        """Get list of available MobyGames systems"""
        return list(self.databases.keys())
    
    def get_system_games_count(self, system_name: str) -> int:
        """Get number of games available for a system"""
        mobygames_system = self.get_mobygames_system(system_name)
        if not mobygames_system:
            return 0
        
        return len(self.databases[mobygames_system])
    
    def search_games(self, system_name: str, query: str, limit: int = 10) -> List[Dict]:
        """Search for games by query string using global partitioned similarity search (for manual search)"""
        mobygames_system = self.get_mobygames_system(system_name)
        if not mobygames_system:
            self.logger.warning(f"No MobyGames system configured for: {system_name}")
            return []
        
        normalized_query = normalize_game_name(query, remove_paranthesis=True, remove_articles=True)
        if not normalized_query:
            return []
        
        # Use pre-built global partitioned similarity index (built at startup)
        if mobygames_system not in self._global_similarity_index:
            self.logger.warning(f"Partitioned index not found for system: {mobygames_system}")
            return []
        
        # Get the first character to search in the right partition
        first_char = normalized_query[0]
        
        results = []
        
        # Search only in the matching partition
        if first_char in self._global_similarity_index[mobygames_system]:
            partition_items = self._global_similarity_index[mobygames_system][first_char]
            
            for item in partition_items:
                # Calculate similarity using configured algorithm
                # item is now a GameItem namedtuple, access with dot notation
                similarity = calculate_similarity(normalized_query, item.normalized)
                
                if similarity > 0.3:  # Lower threshold for search display
                    results.append({
                        'id': item.game_id,
                        'title': item.name,
                        'system': mobygames_system,
                        'score': round(similarity, 3)
                    })
        
        # Sort by similarity and return top results
        results.sort(key=lambda x: x['score'], reverse=True)
        return results[:limit]
    
    def scrape_additional_text_fields(self, game_id: int, mobygames_system: str) -> Dict[str, Any]:
        """Scrape additional text fields from MobyGames game page"""
        try:
            import httpx
            from bs4 import BeautifulSoup
            import random
            import time
            
            # Get game data
            if mobygames_system not in self.databases:
                return {}
            
            game_data = self.databases[mobygames_system].get(game_id)
            if not game_data or 'url' not in game_data:
                return {}
            
            game_url = game_data['url']
            if game_url.endswith('/'):
                game_url = game_url[:-1]
            
            # Check cache first
            cache_file = 'var/cache/mobygames.json'
            if os.path.exists(cache_file):
                try:
                    with open(cache_file, 'r', encoding='utf-8') as f:
                        cache_data = json.load(f)
                    
                    if str(game_id) in cache_data and 'text_fields' in cache_data[str(game_id)]:
                        self.logger.info(f"Using cached text fields for game {game_id}")
                        return cache_data[str(game_id)]['text_fields']
                except Exception as e:
                    self.logger.debug(f"Error reading cache: {e}")
            
            # Create HTTP client
            user_agents = [
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:132.0) Gecko/20100101 Firefox/132.0'
            ]
            
            headers = {
                'User-Agent': random.choice(user_agents),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
            
            # Add random delay
            time.sleep(random.uniform(0.5, 1.5))
            
            with httpx.Client(headers=headers, timeout=15.0, follow_redirects=True) as client:
                response = client.get(game_url)
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Extract text fields
                    text_fields = {}
                    
                    # Extract description
                    desc_section = soup.find('section', id='gameDescription')
                    if desc_section:
                        desc_div = desc_section.find('div', id='description-text')
                        if desc_div:
                            # Get all text content, preserving structure
                            description = desc_div.get_text(separator=' ', strip=True)
                            text_fields['description'] = description
                    
                    # Extract publisher and developer (platform-specific)
                    publishers = []
                    developers = []
                    
                    # Find the metadata dl element
                    metadata_dl = soup.find('dl', class_='metadata')
                    if metadata_dl:
                        # Find Publishers dt element
                        publishers_dt = metadata_dl.find('dt', string=lambda text: text and text.strip().lower() == 'publishers')
                        if publishers_dt:
                            publishers_dd = publishers_dt.find_next_sibling('dd')
                            if publishers_dd:
                                publisher_links = publishers_dd.find_all('a', href=lambda x: x and '/company/' in x)
                                for link in publisher_links:
                                    popover_data = link.get('data-popover')
                                    if popover_data:
                                        try:
                                            import json as json_lib
                                            popover_info = json_lib.loads(popover_data)
                                            platforms = popover_info.get('platforms', [])
                                            
                                            # Check if our platform is in the list
                                            if mobygames_system in platforms:
                                                company_name = link.get_text(strip=True)
                                                publishers.append(company_name)
                                        except Exception as e:
                                            continue
                                    else:
                                        # If no popover data, add the company anyway
                                        company_name = link.get_text(strip=True)
                                        publishers.append(company_name)
                        
                        # Find Developers dt element
                        developers_dt = metadata_dl.find('dt', string=lambda text: text and text.strip().lower() == 'developers')
                        if developers_dt:
                            developers_dd = developers_dt.find_next_sibling('dd')
                            if developers_dd:
                                developer_links = developers_dd.find_all('a', href=lambda x: x and '/company/' in x)
                                for link in developer_links:
                                    popover_data = link.get('data-popover')
                                    if popover_data:
                                        try:
                                            import json as json_lib
                                            popover_info = json_lib.loads(popover_data)
                                            platforms = popover_info.get('platforms', [])
                                            
                                            # Check if our platform is in the list
                                            if mobygames_system in platforms:
                                                company_name = link.get_text(strip=True)
                                                developers.append(company_name)
                                        except Exception as e:
                                            self.logger.debug(f"Error parsing developer popover data: {e}")
                                            continue
                                    else:
                                        # If no popover data, add the company anyway
                                        company_name = link.get_text(strip=True)
                                        developers.append(company_name)
                    
                    # Join multiple publishers/developers
                    if publishers:
                        text_fields['publisher'] = ', '.join(publishers)
                    if developers:
                        text_fields['developer'] = ', '.join(developers)
                    
                    # Extract number of votes
                    reviews_links = soup.find_all('a', href=lambda x: x and '/reviews/' in x)
                    for reviews_link in reviews_links:
                        votes_text = reviews_link.get_text(strip=True)
                        try:
                            votes = int(votes_text)
                            text_fields['nbvotes'] = votes
                            break  # Found a valid number, stop looking
                        except ValueError:
                            continue
                    
                    # Cache the results
                    self._cache_text_fields(game_id, text_fields)
                    
                    return text_fields
                
                else:
                    self.logger.warning(f"Failed to load game page: {response.status_code}")
                    return {}
                    
        except Exception as e:
            self.logger.error(f"Error scraping additional text fields for game {game_id}: {e}")
            return {}
    
    def _cache_text_fields(self, game_id: int, text_fields: Dict[str, Any]):
        """Cache text fields in var/cache/mobygames.json"""
        try:
            cache_file = 'var/cache/mobygames.json'
            
            # Load existing cache
            cache_data = {}
            if os.path.exists(cache_file):
                try:
                    with open(cache_file, 'r', encoding='utf-8') as f:
                        cache_data = json.load(f)
                except Exception as e:
                    self.logger.debug(f"Error loading cache: {e}")
            
            # Update cache
            if str(game_id) not in cache_data:
                cache_data[str(game_id)] = {}
            
            cache_data[str(game_id)]['text_fields'] = text_fields
            
            # Save cache
            os.makedirs(os.path.dirname(cache_file), exist_ok=True)
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            self.logger.error(f"Error caching text fields: {e}")