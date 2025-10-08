#!/usr/bin/env python3
"""
IGDB Service for loading and searching IGDB database

This service loads the consolidated IGDB database and platform partition index
from pickle files for fast game lookups and searches.
"""

import os
import pickle
import logging
import time
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

class IGDBService:
    """Service for interacting with IGDB database and platform partition index"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # IGDB database paths
        self.db_path = 'var/db/igdb'
        self.igdb_db_file = os.path.join(self.db_path, 'igdb_db.pkl')
        self.platform_index_file = os.path.join(self.db_path, 'igdb_platform_partition_index.pkl')
        self.companies_file = os.path.join(self.db_path, 'igdb_companies.pkl')
        
        # In-memory databases
        self.igdb_data = {}  # {game_id: game_data}
        self.platform_index = {}  # {platform_id: {first_char: {normalized_name: game_id}}}
        self.companies = {}  # {company_id: company_name}
        
        # Load status
        self._loaded = False
        
        # Load databases
        self._load_databases()
    
    def _load_databases(self):
        """Load IGDB databases from pickle files"""
        try:
            start_time = time.time()
            print("🔄 Loading IGDB databases from pickle files...")
            self.logger.info("🔄 Loading IGDB databases from pickle files...")
            
            print(f"🔧 DEBUG IGDB: Looking for files:")
            print(f"🔧 DEBUG IGDB: - igdb_db_file: {self.igdb_db_file}")
            print(f"🔧 DEBUG IGDB: - platform_index_file: {self.platform_index_file}")
            
            # Load consolidated IGDB database
            if os.path.exists(self.igdb_db_file):
                print(f"🔧 DEBUG IGDB: Loading igdb_db.pkl...")
                with open(self.igdb_db_file, 'rb') as f:
                    self.igdb_data = pickle.load(f)
                print(f"✅ Loaded IGDB database with {len(self.igdb_data)} games")
                self.logger.info(f"✅ Loaded IGDB database with {len(self.igdb_data)} games")
                
                # Debug: Show some sample game IDs
                if self.igdb_data:
                    sample_ids = list(self.igdb_data.keys())[:5]
                    print(f"🔧 DEBUG IGDB: Sample game IDs: {sample_ids}")
            else:
                print(f"⚠️ IGDB database file not found: {self.igdb_db_file}")
                self.logger.warning(f"IGDB database file not found: {self.igdb_db_file}")
            
            # Load platform partition index
            if os.path.exists(self.platform_index_file):
                print(f"🔧 DEBUG IGDB: Loading platform partition index...")
                with open(self.platform_index_file, 'rb') as f:
                    self.platform_index = pickle.load(f)
                
                # Calculate statistics
                total_platforms = len(self.platform_index)
                total_entries = sum(
                    len(partition_data) 
                    for platform_data in self.platform_index.values() 
                    for partition_data in platform_data.values()
                )
                print(f"✅ Loaded platform partition index with {total_platforms} platforms and {total_entries} entries")
                self.logger.info(f"✅ Loaded platform partition index with {total_platforms} platforms and {total_entries} entries")
                
                # Debug: Show available platforms and their partition counts
                print(f"🔧 DEBUG IGDB: Available platforms:")
                for platform_id, platform_data in self.platform_index.items():
                    partition_count = len(platform_data)
                    total_games = sum(len(partition_data) for partition_data in platform_data.values())
                    print(f"🔧 DEBUG IGDB: - Platform {platform_id}: {partition_count} partitions, {total_games} games")
            else:
                print(f"⚠️ Platform partition index file not found: {self.platform_index_file}")
                self.logger.warning(f"Platform partition index file not found: {self.platform_index_file}")
            
            # Load companies lookup
            if os.path.exists(self.companies_file):
                print(f"🔧 DEBUG IGDB: Loading companies lookup...")
                with open(self.companies_file, 'rb') as f:
                    self.companies = pickle.load(f)
                print(f"✅ Loaded companies lookup with {len(self.companies)} companies")
                self.logger.info(f"✅ Loaded companies lookup with {len(self.companies)} companies")
            else:
                print(f"⚠️ Companies file not found: {self.companies_file}")
                self.logger.warning(f"Companies file not found: {self.companies_file}")
            
            end_time = time.time()
            print(f"✅ IGDB service loaded in {end_time - start_time:.2f} seconds!")
            self.logger.info(f"✅ IGDB service loaded in {end_time - start_time:.2f} seconds!")
            self._loaded = True
            
        except Exception as e:
            print(f"❌ Failed to load IGDB service: {e}")
            self.logger.error(f"Failed to load IGDB service: {e}")
            import traceback
            traceback.print_exc()
            self._loaded = False
    
    def is_loaded(self) -> bool:
        """Check if the service is loaded and ready"""
        return self._loaded and bool(self.igdb_data)
    
    def get_game_by_id(self, game_id: int) -> Optional[Dict]:
        """Get game data by ID"""
        if not self.is_loaded():
            return None
        return self.igdb_data.get(game_id)
    
    def get_company_name(self, company_id: int) -> Optional[str]:
        """Get company name by ID"""
        if not self.is_loaded():
            return None
        return self.companies.get(company_id)
    
    def search_games_by_name(self, game_name: str, platform_id: Optional[int] = None, limit: int = 10) -> List[Dict]:
        """Search for games by name using similarity search on specific platform only"""
        print(f"🔧 DEBUG IGDB: search_games_by_name called with game_name='{game_name}', platform_id={platform_id}")
        
        if not self.is_loaded():
            print("🔧 DEBUG IGDB: Service not loaded")
            return []
        
        # Import normalization and similarity functions
        from game_utils import normalize_game_name, calculate_similarity
        
        # Normalize the search query
        normalized_query = normalize_game_name(game_name, remove_paranthesis=True, remove_articles=True)
        print(f"🔧 DEBUG IGDB: Normalized query: '{normalized_query}'")
        
        if not normalized_query:
            print("🔧 DEBUG IGDB: Normalized query is empty")
            return []
        
        # Require platform_id - no fallback to all platforms
        if not platform_id:
            print("🔧 DEBUG IGDB: No platform_id provided")
            return []
        
        print(f"🔧 DEBUG IGDB: Searching platform_id={platform_id}")
        
        results = []
        first_char = normalized_query[0] if normalized_query else 'other'
        print(f"🔧 DEBUG IGDB: First character: '{first_char}'")
        
        # Search only in the specific platform (always use integer keys)
        if platform_id in self.platform_index:
            print(f"🔧 DEBUG IGDB: Platform {platform_id} found in index")
            platform_data = self.platform_index[platform_id]
            print(f"🔧 DEBUG IGDB: Platform {platform_id} has {len(platform_data)} partitions")
            
            if first_char in platform_data:
                partition_data = platform_data[first_char]
                print(f"🔧 DEBUG IGDB: Partition '{first_char}' has {len(partition_data)} games")
                
                # Debug: Show some sample normalized names in this partition
                sample_names = list(partition_data.keys())[:10]
                print(f"🔧 DEBUG IGDB: Sample normalized names in partition '{first_char}': {sample_names}")
                
                # Calculate similarity for all games in this partition
                similarity_count = 0
                for normalized_name, game_id in partition_data.items():
                    similarity = calculate_similarity(normalized_query, normalized_name)
                    similarity_count += 1
                    
                    # Debug: Show similarity for first few games to see what's happening
                    if similarity_count <= 5:
                        print(f"🔧 DEBUG IGDB: Similarity check: '{normalized_query}' vs '{normalized_name}' = {similarity}")
                    
                    if similarity > 0.3:  # Lower threshold for search display
                        print(f"🔧 DEBUG IGDB: Found match: '{normalized_name}' (ID: {game_id}) with similarity {similarity}")
                        game_data = self.get_game_by_id(game_id)
                        if game_data:
                            game_data['_similarity_score'] = round(similarity, 3)
                            game_data['id'] = game_id  # Add the ID back since it was removed from consolidated data
                            results.append(game_data)
                        else:
                            print(f"🔧 DEBUG IGDB: Game data not found for ID {game_id}")
                
                print(f"🔧 DEBUG IGDB: Checked {similarity_count} games in partition, found {len(results)} matches")
            else:
                print(f"🔧 DEBUG IGDB: Partition '{first_char}' not found in platform {platform_id}")
                print(f"🔧 DEBUG IGDB: Available partitions: {list(platform_data.keys())}")
        else:
            print(f"🔧 DEBUG IGDB: Platform {platform_id} not found in index")
            print(f"🔧 DEBUG IGDB: Available platforms: {list(self.platform_index.keys())}")
        
        # Sort by similarity score (highest first)
        results.sort(key=lambda x: x.get('_similarity_score', 0), reverse=True)
        print(f"🔧 DEBUG IGDB: Returning {len(results)} results")
        return results[:limit]
    
    def find_similar_games(self, game_name: str, platform_id: Optional[int] = None, limit: int = 10) -> List[Dict]:
        """Find similar games using similarity search on specific platform only (higher threshold)"""
        if not self.is_loaded():
            return []
        
        # Import normalization and similarity functions
        from game_utils import normalize_game_name, calculate_similarity
        
        # Normalize the search query
        normalized_query = normalize_game_name(game_name, remove_paranthesis=True, remove_articles=True)
        if not normalized_query:
            return []
        
        # Require platform_id - no fallback to all platforms
        if not platform_id:
            return []
        
        results = []
        first_char = normalized_query[0] if normalized_query else 'other'
        
        # Search only in the specific platform (always use integer keys)
        if platform_id in self.platform_index:
            platform_data = self.platform_index[platform_id]
            if first_char in platform_data:
                partition_data = platform_data[first_char]
                
                # Calculate similarity for all games in this partition
                for normalized_name, game_id in partition_data.items():
                    similarity = calculate_similarity(normalized_query, normalized_name)
                    
                    if similarity > 0.6:  # Higher threshold for similar games
                        game_data = self.get_game_by_id(game_id)
                        if game_data:
                            game_data['_similarity_score'] = round(similarity, 3)
                            game_data['id'] = game_id  # Add the ID back since it was removed from consolidated data
                            results.append(game_data)
        
        # Sort by similarity score (highest first)
        results.sort(key=lambda x: x.get('_similarity_score', 0), reverse=True)
        return results[:limit]
    
    def get_platforms(self) -> List[Dict]:
        """Get list of all platforms with game counts"""
        if not self.is_loaded():
            return []
        
        platforms = []
        for platform_id_str, platform_data in self.platform_index.items():
            total_games = sum(len(partition_data) for partition_data in platform_data.values())
            platforms.append({
                'id': int(platform_id_str),
                'game_count': total_games
            })
        
        return sorted(platforms, key=lambda x: x['game_count'], reverse=True)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics"""
        if not self.is_loaded():
            return {}
        
        total_platforms = len(self.platform_index)
        total_entries = sum(
            len(partition_data) 
            for platform_data in self.platform_index.values() 
            for partition_data in platform_data.values()
        )
        
        return {
            'total_games': len(self.igdb_data),
            'total_platforms': total_platforms,
            'total_index_entries': total_entries,
            'loaded': self._loaded
        }
    
    def debug_search_game(self, game_name: str, platform_id: int = None):
        """Debug function to search for a specific game and show detailed info"""
        print(f"🔧 DEBUG IGDB: Searching for '{game_name}' in platform {platform_id}")
        
        # Import normalization function
        from game_utils import normalize_game_name
        
        # Normalize the search query
        normalized_query = normalize_game_name(game_name, remove_paranthesis=True, remove_articles=True)
        print(f"🔧 DEBUG IGDB: Normalized query: '{normalized_query}'")
        
        if not normalized_query:
            print("🔧 DEBUG IGDB: Normalized query is empty")
            return
        
        first_char = normalized_query[0] if normalized_query else 'other'
        print(f"🔧 DEBUG IGDB: First character: '{first_char}'")
        
        # Search in all platforms if no platform specified
        platforms_to_search = [str(platform_id)] if platform_id else list(self.platform_index.keys())
        
        for platform_id_str in platforms_to_search:
            # Always use integer keys
            platform_id_int = int(platform_id_str)
            if platform_id_int in self.platform_index:
                platform_data = self.platform_index[platform_id_int]
                print(f"🔧 DEBUG IGDB: Platform {platform_id_str} found, has {len(platform_data)} partitions")
                
                if first_char in platform_data:
                    partition_data = platform_data[first_char]
                    print(f"🔧 DEBUG IGDB: Partition '{first_char}' in platform {platform_id_str} has {len(partition_data)} games")
                    
                    # Look for exact matches first
                    if normalized_query in partition_data:
                        game_id = partition_data[normalized_query]
                        print(f"🔧 DEBUG IGDB: EXACT MATCH FOUND! '{normalized_query}' -> Game ID {game_id}")
                        game_data = self.get_game_by_id(game_id)
                        if game_data:
                            print(f"🔧 DEBUG IGDB: Game data: {game_data.get('name', 'Unknown')}")
                        else:
                            print(f"🔧 DEBUG IGDB: Game data not found for ID {game_id}")
                    else:
                        print(f"🔧 DEBUG IGDB: No exact match for '{normalized_query}' in platform {platform_id_str}")
                        
                        # Show some similar names
                        similar_names = [name for name in partition_data.keys() if normalized_query in name or name in normalized_query]
                        if similar_names:
                            print(f"🔧 DEBUG IGDB: Similar names found: {similar_names[:5]}")
                        else:
                            print(f"🔧 DEBUG IGDB: No similar names found")
                else:
                    print(f"🔧 DEBUG IGDB: Partition '{first_char}' not found in platform {platform_id_str}")
            else:
                print(f"🔧 DEBUG IGDB: Platform {platform_id_str} not found in index")
