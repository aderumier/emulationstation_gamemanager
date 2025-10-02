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
import logging
from typing import Dict, List, Optional, Any
from difflib import SequenceMatcher
from game_utils import normalize_game_name, calculate_similarity

class MobyGamesService:
    def __init__(self, config: Dict, scrappers_config: Dict = None, systems_config: Dict = None):
        self.config = config
        self.scrappers_config = scrappers_config or {}
        self.systems_config = systems_config or {}
        self.logger = logging.getLogger(__name__)
        
        # MobyGames database path
        self.db_path = 'var/db/mobygames'
        
        # In-memory databases: {system: {gameid: {attributes}}}
        self.databases = {}
        
        # Normalized title index: {system: {normalized_title: gameid}}
        self.title_index = {}
        
        # Load all MobyGames databases
        self._load_databases()
    
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
                    
                    # Build normalized title index
                    self.title_index[system_name] = {}
                    for game_id, game_data in games_dict.items():
                        if 'title' in game_data:
                            normalized_title = normalize_game_name(game_data['title'], remove_paranthesis=True, remove_articles=True)
                            self.title_index[system_name][normalized_title] = game_id
                    
                    self.logger.info(f"Loaded {len(games_dict)} games for system: {system_name}")
                    
                except Exception as e:
                    self.logger.error(f"Error loading {json_file}: {e}")
                    continue
            
            self.logger.info(f"Loaded {len(self.databases)} MobyGames databases")
            
        except Exception as e:
            self.logger.error(f"Error loading MobyGames databases: {e}")
    
    
    def get_mobygames_system(self, system_name: str) -> Optional[str]:
        """Get MobyGames system name from systems configuration"""
        if not self.systems_config:
            return None
        
        system_config = self.systems_config.get(system_name, {})
        mobygames_system = system_config.get('mobygames')
        
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
        
        # Try exact match only
        if normalized_search in self.title_index[mobygames_system]:
            game_id = self.title_index[mobygames_system][normalized_search]
            return self.databases[mobygames_system][game_id]
        
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
        
        # First try exact match
        if normalized_search in self.title_index[mobygames_system]:
            game_id = self.title_index[mobygames_system][normalized_search]
            return self.databases[mobygames_system][game_id]
        
        # If no exact match, try similarity matching
        best_match = None
        best_similarity = 0.0
        
        for normalized_title, game_id in self.title_index[mobygames_system].items():
            # Calculate similarity using configured algorithm
            similarity = calculate_similarity(normalized_search, normalized_title)
            
            if similarity > best_similarity and similarity >= similarity_threshold:
                best_similarity = similarity
                best_match = self.databases[mobygames_system][game_id]
        
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
        """Search for games by query string using partitioned similarity search (for manual search)"""
        mobygames_system = self.get_mobygames_system(system_name)
        if not mobygames_system:
            self.logger.warning(f"No MobyGames system configured for: {system_name}")
            return []
        
        normalized_query = normalize_game_name(query, remove_paranthesis=True, remove_articles=True)
        if not normalized_query:
            return []
        
        # Build partitioned similarity index if not exists for this system
        if not hasattr(self, '_similarity_index') or self._similarity_index.get('system') != mobygames_system:
            self.logger.info(f"Building partitioned similarity index for MobyGames system: {mobygames_system}")
            self._similarity_index = {'system': mobygames_system, 'index': {}}
            
            for game_id, game_data in self.databases[mobygames_system].items():
                if 'title' in game_data:
                    normalized_title = normalize_game_name(game_data['title'], remove_paranthesis=True, remove_articles=True)
                    if normalized_title:
                        first_char = normalized_title[0] if normalized_title else 'other'
                        if first_char not in self._similarity_index['index']:
                            self._similarity_index['index'][first_char] = []
                        self._similarity_index['index'][first_char].append({
                            'name': game_data['title'],
                            'normalized': normalized_title,
                            'game_id': game_id,
                            'game_data': game_data
                        })
        
        # Get the first character to search in the right partition
        first_char = normalized_query[0]
        
        results = []
        
        # Search only in the matching partition
        if first_char in self._similarity_index['index']:
            partition_items = self._similarity_index['index'][first_char]
            
            for item in partition_items:
                # Calculate similarity using configured algorithm
                similarity = calculate_similarity(normalized_query, item['normalized'])
                
                if similarity > 0.3:  # Lower threshold for search display
                    results.append({
                        'id': item['game_id'],
                        'title': item['name'],
                        'system': mobygames_system,
                        'score': round(similarity, 3)
                    })
        
        # Sort by similarity and return top results
        results.sort(key=lambda x: x['score'], reverse=True)
        return results[:limit]