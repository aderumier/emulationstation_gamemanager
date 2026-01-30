import os
import pickle
import time
import logging
from typing import Dict, List, Optional

class IGDBService:
    """Service for interacting with IGDB database and platform partition index"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # IGDB database paths
        self.db_path = 'var/db/igdb'
        self.igdb_db_file = os.path.join(self.db_path, 'igdb_db.pkl')
        self.platform_index_file = os.path.join(self.db_path, 'igdb_platform_partition_index.pkl')
        self.companies_file = os.path.join(self.db_path, 'igdb_companies.pkl')
        self.genres_file = os.path.join(self.db_path, 'igdb_genres.pkl')
        
        # In-memory databases
        self.igdb_data = {}  # {game_id: game_data}
        self.platform_index = {}  # {platform_id: {first_char: {normalized_name: game_id}}}
        self.companies = {}  # {company_id: company_name}
        self.genres = {}  # {genre_id: genre_name}
        
        # Load status
        self._loaded = False
        
        # Load databases
        self._load_databases()
    
    def _load_databases(self):
        """Load IGDB databases from pickle files"""
        try:
            start_time = time.time()
            # Load IGDB databases from pickle files (info logs only)
            self.logger.info("🔄 Loading IGDB databases from pickle files...")
            
            # Load consolidated IGDB database
            if os.path.exists(self.igdb_db_file):
                with open(self.igdb_db_file, 'rb') as f:
                    self.igdb_data = pickle.load(f)
                self.logger.info(f"✅ Loaded IGDB database with {len(self.igdb_data)} games")
                
            else:
                self.logger.warning(f"IGDB database file not found: {self.igdb_db_file}")
            
            # Load platform partition index
            if os.path.exists(self.platform_index_file):
                with open(self.platform_index_file, 'rb') as f:
                    self.platform_index = pickle.load(f)
                
                # Calculate statistics
                total_platforms = len(self.platform_index)
                total_partitions = sum(len(platform_data) for platform_data in self.platform_index.values())
                total_games = sum(sum(len(partition_data) for partition_data in platform_data.values()) for platform_data in self.platform_index.values())
                
                self.logger.info(f"✅ Loaded platform partition index with {total_platforms} platforms, {total_partitions} partitions, {total_games} games")
                
            else:
                self.logger.warning(f"Platform partition index file not found: {self.platform_index_file}")
            
            # Load companies lookup
            if os.path.exists(self.companies_file):
                with open(self.companies_file, 'rb') as f:
                    self.companies = pickle.load(f)
                self.logger.info(f"✅ Loaded companies lookup with {len(self.companies)} companies")
            else:
                self.logger.warning(f"Companies file not found: {self.companies_file}")
            
            # Load genres lookup
            if os.path.exists(self.genres_file):
                with open(self.genres_file, 'rb') as f:
                    self.genres = pickle.load(f)
                self.logger.info(f"✅ Loaded genres lookup with {len(self.genres)} genres")
            else:
                self.logger.warning(f"Genres file not found: {self.genres_file}")
            
            end_time = time.time()
            self.logger.info(f"✅ IGDB service loaded in {end_time - start_time:.2f} seconds!")
            self._loaded = True
            
        except Exception as e:
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
    
    def get_genre_name(self, genre_id: int) -> Optional[str]:
        """Get genre name by ID"""
        if not self.is_loaded():
            return None
        return self.genres.get(genre_id)
    
    def search_games_by_name(self, game_name: str, platform_id: Optional[int] = None, limit: int = 10) -> List[Dict]:
        """Search for games by name using similarity search on specific platform only"""
        if not self.is_loaded():
            return []
        
        # Import normalization and similarity functions
        from game_utils import normalize_game_name, calculate_similarity
        
        # Normalize the search query
        normalized_query = normalize_game_name(game_name, remove_paranthesis=True, remove_articles=True)
        
        if not normalized_query:
            return []
        
        # Search on specific platform only
        if platform_id is not None:
            # Check if platform exists in index
            if platform_id not in self.platform_index:
                return []
            
            platform_data = self.platform_index[platform_id]
            first_char = normalized_query[0].lower()
            
            if first_char not in platform_data:
                return []
            
            # Get all games for this platform and first character
            partition_games = platform_data[first_char]
            
            # Calculate similarity for each game and deduplicate by game ID
            game_similarities = {}  # {game_id: max_similarity}
            game_data_cache = {}    # {game_id: game_data}
            
            for normalized_name, game_id in partition_games.items():
                similarity = calculate_similarity(normalized_query, normalized_name)
                if similarity > 0.3:  # Minimum similarity threshold
                    # Keep track of the highest similarity for this game ID
                    if game_id not in game_similarities or similarity > game_similarities[game_id]:
                        game_similarities[game_id] = similarity
                        
                        # Get game data only once per game ID
                        if game_id not in game_data_cache:
                            game_data = self.get_game_by_id(game_id)
                            if game_data:
                                game_data['id'] = game_id  # Add the ID back since it was removed from consolidated data
                                game_data_cache[game_id] = game_data
            
            # Build final results with highest similarity scores
            results = []
            for game_id, max_similarity in game_similarities.items():
                if game_id in game_data_cache:
                    game_data = game_data_cache[game_id].copy()
                    game_data['_similarity_score'] = round(max_similarity, 3)
                    results.append(game_data)
            
            # Sort by similarity score (highest first)
            results.sort(key=lambda x: x.get('_similarity_score', 0), reverse=True)
            
            # Limit results to top 20, then apply user's limit
            limited_results = results[:limit]
            return limited_results
        
        return []
    
    def find_similar_games(self, game_name: str, platform_id: Optional[int] = None, limit: int = 10) -> List[Dict]:
        """Find similar games by name using similarity search"""
        return self.search_games_by_name(game_name, platform_id, limit)
    