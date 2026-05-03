#!/usr/bin/env python3
"""
Steam Service - Handles Steam API interactions for game matching and media scraping
"""

import os
import json
import time
import httpx
import asyncio
import re
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
import logging
from collections import namedtuple
from game_utils import normalize_game_name, should_process_field, convert_and_resize_image_replace
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# Lightweight namedtuple for search index entries
SteamItem = namedtuple('SteamItem', ['name', 'normalized', 'appid'])

class SteamService:
    """Service for interacting with Steam API and managing app index cache"""
    
    def __init__(self, cache_dir: str = "var/db/steam"):
        self.cache_dir = cache_dir
        self.app_index_file = os.path.join(cache_dir, "appindex.json")
        # Steam Web API v1 with authentication (v2 no longer works without key)
        self.steam_api_url = "https://api.steampowered.com/IStoreService/GetAppList/v1/"
        self.cache_retention_hours = 24
        
        # Indexing cache for performance
        self._unified_index = None
        self._cached_steam_apps = None
        
        # Global partitioned similarity index: {first_char: [SteamItem]}
        # SteamItem is lightweight namedtuple, full app data stored separately
        self._global_similarity_index = {}
        self._partitioned_index = {}  # Alias for _global_similarity_index
        
        # Track whether partitioned index was loaded from cache
        self._partitioned_index_loaded_from_cache = False
        
        # Ensure cache directory exists
        os.makedirs(cache_dir, exist_ok=True)
        
        # Try to load partitioned index from cache, but don't build it here
        # The partitioned index will be built in a background thread
        self._partitioned_index_loaded_from_cache = self._load_partitioned_index_from_cache()
    
    def get_api_key(self) -> Optional[str]:
        """Get Steam API key from credentials"""
        try:
            credentials_path = 'var/config/credentials.json'
            if os.path.exists(credentials_path):
                with open(credentials_path, 'r') as f:
                    credentials = json.load(f)
                return credentials.get('steam_api_key')
            return None
        except Exception as e:
            logger.error(f"Error loading Steam API key: {e}")
            return None
    
    def save_api_key(self, api_key: str) -> bool:
        """Save Steam API key to credentials"""
        try:
            credentials_path = 'var/config/credentials.json'
            os.makedirs(os.path.dirname(credentials_path), exist_ok=True)
            
            credentials = {}
            if os.path.exists(credentials_path):
                with open(credentials_path, 'r') as f:
                    credentials = json.load(f)
            
            credentials['steam_api_key'] = api_key
            
            with open(credentials_path, 'w') as f:
                json.dump(credentials, f, indent=2)
            
            return True
        except Exception as e:
            logger.error(f"Error saving Steam API key: {e}")
            return False
    
    def close(self):
        """Close any open connections or resources"""
        # Clear cached data to free memory
        self._unified_index = None
        self._cached_steam_apps = None
    
    async def get_steam_game_data(self, steam_id: int) -> Optional[Dict]:
        """Fetch game details from Steam Storefront API by Steam App ID.

        Returns the 'data' object from the API which typically includes:
        name, short_description, header_image, release_date, developers, publishers, genres, background, etc.
        """
        if not steam_id:
            return None
        try:
            url = f"https://store.steampowered.com/api/appdetails?appids={steam_id}&l=en&cc=us"
            async with httpx.AsyncClient(timeout=30.0, headers={
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140 Safari/537.36'
            }) as client:
                resp = await client.get(url)
                if resp.status_code != 200:
                    return None
                payload = resp.json()
                entry = payload.get(str(steam_id)) or payload.get(steam_id)
                if not entry or not entry.get('success'):
                    return None
                return entry.get('data')
        except Exception:
            return None

    
    def load_app_index(self) -> Optional[List[Dict]]:
        """Load Steam app index from cache file (no automatic expiration, manual refresh only)"""
        if not os.path.exists(self.app_index_file):
            return None
        
        try:
            with open(self.app_index_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Handle both old and new cache formats
            apps = data.get('applist', {}).get('apps', []) or data.get('steam_apps', [])
            logger.info(f"Loaded Steam app index from cache with {len(apps)} apps")
            return apps
            
        except Exception as e:
            logger.error(f"Error loading Steam app index: {e}")
            return None
    
    def save_app_index(self, apps: List[Dict]) -> bool:
        """Save Steam app index to cache"""
        try:
            data = {
                'cached_at': datetime.now().isoformat(),
                'applist': {
                    'apps': apps
                }
            }
            
            with open(self.app_index_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved Steam app index to cache with {len(apps)} apps")
            return True
            
        except Exception as e:
            logger.error(f"Error saving Steam app index: {e}")
            return False
    
    async def fetch_app_index(self) -> Optional[List[Dict]]:
        """Fetch Steam app index from API (requires API key for v1 endpoint)"""
        try:
            api_key = self.get_api_key()
            if not api_key:
                logger.error("Steam API key not configured. Please set your Steam Web API key in Scrapper Configuration > Steam.")
                return None
            
            logger.info("Fetching Steam app index from API...")
            
            # v1 API requires key parameter and returns paginated results
            all_apps = []
            last_appid = 0
            max_results = 50000  # Request max per page
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                while True:
                    params = {
                        'key': api_key,
                        'max_results': max_results,
                        'include_games': 'true',
                        'include_dlc': 'false',
                        'include_software': 'false',
                        'include_videos': 'false',
                        'include_hardware': 'false'
                    }
                    if last_appid > 0:
                        params['last_appid'] = last_appid
                    
                    response = await client.get(self.steam_api_url, params=params)
                    response.raise_for_status()
                    
                    data = response.json()
                    response_data = data.get('response', {})
                    apps = response_data.get('apps', [])
                    
                    if not apps:
                        break
                    
                    # Convert v1 format to v2 format for compatibility
                    for app in apps:
                        all_apps.append({
                            'appid': app.get('appid'),
                            'name': app.get('name', '')
                        })
                    
                    # Check if there are more results
                    have_more = response_data.get('have_more_results', False)
                    if not have_more:
                        break
                    
                    last_appid = response_data.get('last_appid', 0)
                    if last_appid == 0:
                        break
                    
                    logger.info(f"Fetched {len(all_apps)} apps so far, continuing...")
                
                logger.info(f"Fetched {len(all_apps)} Steam apps from API")
                return all_apps
                
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 403:
                logger.error("Steam API key is invalid or unauthorized. Please check your API key.")
            else:
                logger.error(f"HTTP error fetching Steam app index: {e}")
            return None
        except Exception as e:
            logger.error(f"Error fetching Steam app index: {e}")
            return None
    
    async def get_app_index(self) -> Optional[List[Dict]]:
        """Get Steam app index (from cache or API)"""
        # Try to load from cache first
        apps = self.load_app_index()
        if apps is not None:
            return apps
        
        # Fetch from API if cache is invalid or missing
        apps = await self.fetch_app_index()
        if apps:
            self.save_app_index(apps)
            return apps
        
        return None
    
    def _build_unified_index(self, apps: List[Dict]) -> Dict[str, List[Dict]]:
        """Build unified search index for faster lookups"""
        if self._unified_index is not None:
            return self._unified_index
        
        logger.info("Building unified search index...")
        unified_index = {}
        
        for app in apps:
            appid = app.get('appid', 0)
            name = app.get('name', '').strip()
            
            if not name or appid <= 0:
                continue
            
            # Normalize the name for searching
            normalized_name = normalize_game_name(name)
            
            # Store by normalized name
            if normalized_name not in unified_index:
                unified_index[normalized_name] = []
            unified_index[normalized_name].append(app)
        
        self._unified_index = unified_index
        logger.info(f"Built unified index with {len(unified_index)} search terms")
        return unified_index
    
    def _build_partitioned_index(self, apps: List[Dict]):
        """Build partitioned similarity index for Steam apps"""
        try:
            print("🔧 Building partitioned similarity index for Steam apps...")
            logger.info("🔧 Building partitioned similarity index for Steam apps...")
            start_time = time.time()
            
            self._global_similarity_index = {}
            
            for app in apps:
                appid = app.get('appid', 0)
                name = app.get('name', '').strip()
                
                if not name or appid <= 0:
                    continue
                
                # Normalize the name for partitioning
                normalized_name = normalize_game_name(name, remove_paranthesis=True, remove_articles=True)
                if normalized_name:
                    first_char = normalized_name[0] if normalized_name else 'other'
                    if first_char not in self._global_similarity_index:
                        self._global_similarity_index[first_char] = []
                    
                    # Use lightweight SteamItem namedtuple instead of full app data
                    self._global_similarity_index[first_char].append(
                        SteamItem(
                            name=name,
                            normalized=normalized_name,
                            appid=appid
                        )
                    )
            
            end_time = time.time()
            partition_count = len(self._global_similarity_index)
            print(f"✅ Partitioned index built for Steam ({partition_count} partitions) in {end_time - start_time:.2f} seconds")
            logger.info(f"✅ Partitioned index built for Steam ({partition_count} partitions) in {end_time - start_time:.2f} seconds")
            
            # Set the partitioned_index attribute (alias for _global_similarity_index)
            self._partitioned_index = self._global_similarity_index
            
            # Save the index to cache
            self._save_partitioned_index_to_cache()
            
        except Exception as e:
            print(f"❌ Error building partitioned index: {e}")
            logger.error(f"Error building partitioned index: {e}")
    
    def _save_partitioned_index_to_cache(self):
        """Save partitioned index to cache file for faster startup"""
        try:
            import pickle
            
            cache_dir = 'var/cache'
            os.makedirs(cache_dir, exist_ok=True)
            cache_file = os.path.join(cache_dir, 'steam_partitioned_index.pkl')
            
            # Convert SteamItem namedtuples to dictionaries for pickling
            cache_data = {}
            for first_char, steam_items in self._global_similarity_index.items():
                cache_data[first_char] = [
                    {
                        'name': item.name,
                        'normalized': item.normalized,
                        'appid': item.appid
                    }
                    for item in steam_items
                ]
            
            with open(cache_file, 'wb') as f:
                pickle.dump(cache_data, f)
            
            print(f"✅ Saved Steam partitioned index to {cache_file}")
            logger.info(f"✅ Saved Steam partitioned index to {cache_file}")
            
        except Exception as e:
            print(f"⚠️ Warning: Failed to save Steam partitioned index cache: {e}")
            logger.warning(f"Failed to save Steam partitioned index cache: {e}")
    
    def _load_partitioned_index_from_cache(self):
        """Load partitioned index from cache file"""
        try:
            import pickle
            
            cache_dir = 'var/cache'
            cache_file = os.path.join(cache_dir, 'steam_partitioned_index.pkl')
            if not os.path.exists(cache_file):
                print("🔍 No Steam partitioned index cache found, will build from scratch")
                return False
            
            with open(cache_file, 'rb') as f:
                cache_data = pickle.load(f)
            
            # Convert dictionaries back to SteamItem namedtuples
            self._global_similarity_index = {}
            for first_char, steam_items in cache_data.items():
                self._global_similarity_index[first_char] = [
                    SteamItem(
                        name=item['name'],
                        normalized=item['normalized'],
                        appid=item['appid']
                    )
                    for item in steam_items
                ]
            
            # Set the partitioned_index attribute (alias for _global_similarity_index)
            self._partitioned_index = self._global_similarity_index
            
            total_partitions = len(self._global_similarity_index)
            print(f"✅ Loaded Steam partitioned index from cache ({total_partitions} partitions)")
            logger.info(f"✅ Loaded Steam partitioned index from cache ({total_partitions} partitions)")
            return True
            
        except Exception as e:
            print(f"⚠️ Warning: Failed to load Steam partitioned index cache: {e}")
            logger.warning(f"Failed to load Steam partitioned index cache: {e}")
            return False
    
    def _build_partitioned_index_at_startup(self):
        """Build partitioned index at startup by loading Steam apps"""
        try:
            # Check if partitioned index was already loaded from cache
            if self._partitioned_index_loaded_from_cache:
                print("✅ Steam partitioned index already loaded from cache, skipping build")
                logger.info("✅ Steam partitioned index already loaded from cache, skipping build")
                return
            
            # Check if appindex.json exists before building
            if not os.path.exists(self.app_index_file):
                print("⚠️ Steam appindex.json not found, skipping partitioned index build")
                logger.info("Steam appindex.json not found, skipping partitioned index build")
                return
            
            print("🔧 Building Steam partitioned index at startup...")
            logger.info("🔧 Building Steam partitioned index at startup...")
            
            # Load Steam apps directly from appindex.json file (bypass expiration check)
            apps = None
            try:
                with open(self.app_index_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Handle both old and new cache formats
                apps = data.get('applist', {}).get('apps', []) or data.get('steam_apps', [])
                if apps:
                    print(f"📦 Loaded {len(apps)} Steam apps from appindex.json")
                    logger.info(f"Loaded {len(apps)} Steam apps from appindex.json for index building")
            except Exception as e:
                print(f"⚠️ Error loading Steam apps from appindex.json: {e}")
                logger.warning(f"Error loading Steam apps from appindex.json: {e}")
            
            if apps:
                self._build_partitioned_index(apps)
                self._save_partitioned_index_to_cache()
                print("✅ Steam partitioned index built successfully at startup")
                logger.info("✅ Steam partitioned index built successfully at startup")
            else:
                print("⚠️ No Steam apps available to build partitioned index")
                logger.warning("No Steam apps available to build partitioned index")
                
        except Exception as e:
            print(f"❌ Error building Steam partitioned index at startup: {e}")
            logger.error(f"Error building Steam partitioned index at startup: {e}")
    
    def search_steam_apps(self, game_name: str, limit: int = 20) -> List[Dict]:
        """Search Steam apps using partitioned index for better performance"""
        if not game_name or not self._global_similarity_index:
            return []
        
        try:
            # Normalize the search name - remove parentheses for Steam matching
            steam_normalized = re.sub(r'\([^)]*\)', '', game_name)  # Remove parentheses for Steam
            normalized_search = normalize_game_name(steam_normalized)
            
            if not normalized_search:
                return []
            
            # Get the partition for the first character
            first_char = normalized_search[0] if normalized_search else 'other'
            partition = self._global_similarity_index.get(first_char, [])
            
            if not partition:
                return []
            
            # Find exact matches in the partition
            exact_matches = []
            for item in partition:
                if item.normalized == normalized_search:
                    exact_matches.append({
                        'appid': item.appid,
                        'name': item.name
                    })
            
            # Return exact matches (Steam typically has unique names)
            return exact_matches[:limit]
            
        except Exception as e:
            print(f"❌ Error searching Steam apps: {e}")
            logger.error(f"Error searching Steam apps: {e}")
            return []
    
    def find_best_match(self, game_name: str, apps: List[Dict]) -> Optional[Dict]:
        """Find the best Steam app match for a game name"""
        if not game_name or not apps:
            return None
        
        # Build unified index if not already built
        unified_index = self._build_unified_index(apps)
        
        # Normalize the search name - remove parentheses for Steam matching
        steam_normalized = re.sub(r'\([^)]*\)', '', game_name)  # Remove parentheses for Steam
        normalized_search = normalize_game_name(steam_normalized)
        
        # Debug logging
        print(f"🔧 DEBUG: Searching for '{game_name}' -> normalized: '{normalized_search}'")
        print(f"🔧 DEBUG: Unified index has {len(unified_index)} entries")
        
        # Try exact match first
        if normalized_search in unified_index:
            candidates = unified_index[normalized_search]
            print(f"🔧 DEBUG: Found exact match with {len(candidates)} candidates")
            if len(candidates) == 1:
                print(f"🔧 DEBUG: Returning single match: '{candidates[0]['name']}'")
                return {
                    'app': candidates[0],
                    'matched_name': candidates[0]['name'],
                    'confidence': 1.0
                }
            elif len(candidates) > 1:
                # Multiple exact matches, return the first one
                print(f"🔧 DEBUG: Returning first of {len(candidates)} matches: '{candidates[0]['name']}'")
                return {
                    'app': candidates[0],
                    'matched_name': candidates[0]['name'],
                    'confidence': 0.9
                }
        
        # No exact match found
        print(f"🔧 DEBUG: No exact match found for '{normalized_search}'")
        print(f"🔧 DEBUG: No match found for '{game_name}'")
        return None
    
    async def download_steam_media(self, steam_id: int, game_name: str, 
                                 roms_root: str, system_name: str,
                                 selected_fields: List[str] = None,
                                 image_type_mappings: Dict[str, str] = None,
                                 overwrite_media_fields: bool = False,
                                 gamelist_path: str = None,
                                 cancellation_event=None,
                                 rom_path: str = None) -> Dict[str, str]:
        """Download media from Steam CDN"""
        if not steam_id or not game_name:
            return {}
        
        if not image_type_mappings:
            image_type_mappings = {
                'boxart': 'capsule',
                'marquee': 'logo', 
                'fanart': 'hero',
                'image': 'screenshot'
            }
        
        if not selected_fields:
            selected_fields = list(image_type_mappings.keys())
        
        # Check for cancellation at the start
        if cancellation_event and cancellation_event.is_set():
            logger.info(f"🔧 DEBUG: Steam media download cancelled for {game_name}")
            return {}
        
        results = {}
        
        # Steam CDN URLs
        steam_urls = {
            'capsule': f"https://shared.steamstatic.com/store_item_assets/steam/apps/{steam_id}/library_600x900_2x.jpg",
            'logo': f"https://cdn.akamai.steamstatic.com/steam/apps/{steam_id}/logo.png",
            'hero': f"https://shared.steamstatic.com/store_item_assets/steam/apps/{steam_id}/library_hero.jpg",
            'screenshot': f"https://store.steampowered.com/app/{steam_id}"
        }
        
        logger.info(f"🔧 DEBUG: Steam URLs for {game_name} (Steam ID: {steam_id}):")
        logger.info(f"🔧 DEBUG: Selected fields: {selected_fields}")
        logger.info(f"🔧 DEBUG: Image type mappings: {image_type_mappings}")
        logger.info(f"🔧 DEBUG: Overwrite media fields: {overwrite_media_fields}")
        for media_type, url in steam_urls.items():
            logger.info(f"🔧 DEBUG:   {media_type}: {url}")
        
        # Create HTTP client with connection pooling and HTTP/2
        limits = httpx.Limits(max_keepalive_connections=50, max_connections=50)
        async with httpx.AsyncClient(
            timeout=30.0,
            limits=limits,
            http2=True
        ) as client:
            # Create download tasks for all selected fields
            download_tasks = []
            for gamelist_field in selected_fields:
                # Check for cancellation before each download task
                if cancellation_event and cancellation_event.is_set():
                    logger.info(f"🔧 DEBUG: Steam media download cancelled for {game_name} at {gamelist_field}")
                    return results
                
                # Get the Steam type that maps to this gamelist field
                steam_type = image_type_mappings.get(gamelist_field)
                if not steam_type or steam_type not in steam_urls:
                    continue
                
                url = steam_urls[steam_type]
                download_tasks.append(self._download_single_media(
                    client, url, steam_type, gamelist_field, game_name, 
                    steam_id, roms_root, system_name, overwrite_media_fields, gamelist_path, cancellation_event, rom_path
                ))
            
            # Execute all downloads in parallel
            if download_tasks:
                download_results = await asyncio.gather(*download_tasks, return_exceptions=True)
                
                # Process results
                for i, result in enumerate(download_results):
                    if isinstance(result, Exception):
                        logger.error(f"🔧 DEBUG: Error in download task {i}: {result}")
                    elif result:
                        target_field = result.get('target_field')
                        relative_path = result.get('relative_path')
                        if target_field and relative_path:
                            results[target_field] = relative_path
        
        return results
    
    async def download_steam_media_batch(self, games_data: List[Dict], 
                                       roms_root: str, system_name: str,
                                       selected_fields: List[str] = None,
                                       image_type_mappings: Dict[str, str] = None,
                                       max_concurrent: int = 10,
                                       progress_callback=None,
                                       overwrite_media_fields: bool = False,
                                       gamelist_path: str = None,
                                       cancellation_event=None) -> Dict[str, Dict[str, str]]:
        """Download Steam media for multiple games in parallel"""
        if not games_data:
            return {}
        
        if not image_type_mappings:
            image_type_mappings = {
                'boxart': 'capsule',
                'marquee': 'logo', 
                'fanart': 'hero',
                'image': 'screenshot'
            }
        
        if not selected_fields:
            selected_fields = list(image_type_mappings.keys())
        
        results = {}
        
        # Create HTTP client with connection pooling and HTTP/2
        limits = httpx.Limits(max_keepalive_connections=50, max_connections=50)
        async with httpx.AsyncClient(
            timeout=30.0,
            limits=limits,
            http2=True
        ) as client:
            # Process games in batches of max_concurrent
            for i in range(0, len(games_data), max_concurrent):
                # Check for cancellation before each batch
                if cancellation_event and cancellation_event.is_set():
                    logger.info(f"🔧 DEBUG: Steam batch processing cancelled at batch {i//max_concurrent + 1}")
                    break
                
                batch = games_data[i:i + max_concurrent]
                logger.info(f"🔧 DEBUG: Processing Steam batch {i//max_concurrent + 1} with {len(batch)} games")
                
                # Create tasks for this batch
                batch_tasks = []
                for game_data in batch:
                    steam_id = game_data.get('steam_id')
                    game_name = game_data.get('name', 'Unknown')
                    game = game_data.get('game', {})
                    rom_path = game.get('path', '')
                    
                    if steam_id:
                        logger.info(f"🔧 DEBUG: Processing Steam media download for '{game_name}' with Steam ID: {steam_id} (type: {type(steam_id)})")
                        batch_tasks.append(self.download_steam_media(
                            steam_id, game_name, roms_root, system_name,
                            selected_fields, image_type_mappings, overwrite_media_fields, gamelist_path, None, rom_path
                        ))
                    else:
                        logger.warning(f"🔧 DEBUG: No Steam ID for game: {game_name}")
                        batch_tasks.append(asyncio.create_task(asyncio.sleep(0)))  # Dummy task
                
                # Execute batch in parallel
                if batch_tasks:
                    logger.info(f"🔧 DEBUG: Executing {len(batch_tasks)} parallel Steam download tasks")
                    batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
                    
                    # Process batch results
                    for j, result in enumerate(batch_results):
                        if j < len(batch):
                            game_name = batch[j].get('name', f'Game_{j}')
                            game = batch[j].get('game', {})
                            rom_path = game.get('path', f"/roms/{game_name}")
                            
                            if isinstance(result, Exception):
                                logger.error(f"🔧 DEBUG: Error in batch task {j}: {result}")
                                # Call progress callback even for errors
                                if progress_callback:
                                    progress_callback(game_name, {})
                            elif result:
                                results[rom_path] = result
                                logger.info(f"🔧 DEBUG: Successfully processed Steam media for {game_name}: {result}")
                                
                                # Call progress callback for each completed game
                                if progress_callback:
                                    progress_callback(game_name, result)
                            else:
                                # No media downloaded, but still call progress callback
                                logger.info(f"🔧 DEBUG: No media downloaded for {game_name} - result was empty or None")
                                if progress_callback:
                                    progress_callback(game_name, {})
                
                # Small delay between batches to be respectful to the server
                if i + max_concurrent < len(games_data):
                    await asyncio.sleep(0.1)
        
        return results
    
    async def _download_single_media(self, client: httpx.AsyncClient, url: str, 
                                   media_type: str, target_field: str, 
                                   game_name: str, steam_id: int, 
                                   roms_root: str, system_name: str,
                                   overwrite_media_fields: bool = False,
                                   gamelist_path: str = None,
                                   cancellation_event=None,
                                   rom_path: str = None) -> Optional[Dict[str, str]]:
        """Download a single media file"""
        try:
            # Check for cancellation before starting download
            if cancellation_event and cancellation_event.is_set():
                return None
            
            # Check if media already exists and we're not overwriting
            if not overwrite_media_fields and gamelist_path:
                logger.info(f"🔧 DEBUG: Checking if {target_field} already exists for {game_name} (overwrite_media_fields: {overwrite_media_fields})")
                # Check if media already exists in gamelist.xml
                if os.path.exists(gamelist_path):
                    import xml.etree.ElementTree as ET
                    try:
                        tree = ET.parse(gamelist_path)
                        root = tree.getroot()
                        
                        # Find the game entry
                        for game in root.findall('game'):
                            game_name_elem = game.find('name')
                            if game_name_elem is not None and game_name_elem.text == game_name:
                                # Check if this media field already has a value (not empty)
                                media_elem = game.find(target_field)
                                if media_elem is not None and media_elem.text and media_elem.text.strip():
                                    logger.info(f"🔧 DEBUG: Skipping {target_field} for {game_name} - already exists: {media_elem.text}")
                                    return None
                                else:
                                    logger.info(f"🔧 DEBUG: {target_field} for {game_name} is empty or missing - will download")
                                break
                    except Exception as e:
                        logger.error(f"🔧 DEBUG: Error checking existing media: {e}")
                        pass
            
            # Handle screenshots differently - need to parse HTML and extract image URL
            if media_type == 'screenshot':
                screenshot_url = await self._extract_screenshot_url(client, url, steam_id)
                if not screenshot_url:
                    return None
                
                # Download the actual screenshot image
                response = await client.get(screenshot_url)
            else:
                response = await client.get(url)
            
            # If logo gets 404, try fallback URL
            if response.status_code == 404 and media_type == 'logo':
                fallback_url = f"https://shared.steamstatic.com/store_item_assets/steam/apps/{steam_id}/logo.png"
                response = await client.get(fallback_url)
            
            if response.status_code == 200:
                content_length = len(response.content)
                
                # Get media directory and extensions
                media_dir, extensions = get_media_directory_and_extensions(target_field)
                if not media_dir or not extensions:
                    logger.warning(f"No media directory configured for {target_field}")
                    return None
                
                # Create full path
                full_media_dir = os.path.join(roms_root, system_name, "media", media_dir)
                os.makedirs(full_media_dir, exist_ok=True)
                
                # Determine file extension from content type
                content_type = response.headers.get('content-type', '')
                
                if 'jpeg' in content_type or 'jpg' in content_type:
                    ext = '.jpg'
                elif 'png' in content_type:
                    ext = '.png'
                else:
                    ext = '.jpg'  # Default to jpg for Steam images
                
                # Generate filename using common function
                from app import create_media_filename
                filename = create_media_filename(rom_path, ext)
                file_path = os.path.join(full_media_dir, filename)
                
                # Write file
                with open(file_path, 'wb') as f:
                    f.write(response.content)
                
                # Convert image if needed using config-based target extension
                import json
                
                # Load config to get target_extension and resize settings for this field
                try:
                    with open('var/config/config.json', 'r') as f:
                        config = json.load(f)
                except Exception as e:
                    config = {}
                
                # Convert and/or resize image in a single operation (optimized)
                from game_utils import should_process_field, convert_and_resize_image_replace
                should_process, target_extension, target_width, target_height = should_process_field(target_field, config)
                
                if should_process:
                    processed_path, process_status = convert_and_resize_image_replace(
                        file_path, target_extension, target_width, target_height
                    )
                    if process_status in ["converted", "resized", "converted_and_resized"]:
                        file_path = processed_path
                        print(f"✅ Processed Steam {media_type} for {game_name}: {process_status}")
                    elif process_status == "failed":
                        print(f"⚠️ Warning: Failed to process Steam {media_type} for {game_name}")
                else:
                    print(f"✅ No processing needed for Steam {media_type} field: {target_field}")
                
                # Store relative path (forward slashes for gamelist.xml / EmulationStation)
                relative_path = f"./media/{media_dir}/{os.path.basename(file_path)}".replace('//', '/').replace('\\', '/')
                
                logger.info(f"Downloaded Steam {media_type} for {game_name}: {relative_path}")
                
                return {
                    'target_field': target_field,
                    'relative_path': relative_path
                }
            else:
                return None
                
        except Exception as e:
            return None

    async def _extract_screenshot_url(self, client: httpx.AsyncClient, store_page_url: str, steam_id: int) -> Optional[str]:
        """Extract the first screenshot image URL from Steam Store page using BeautifulSoup"""
        try:
            # Set headers to mimic a real browser request
            headers = {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'Accept-Encoding': 'gzip, deflate, br, zstd',
                'Accept-Language': 'en-US,en;q=0.5',
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36',
                'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="140", "Google Chrome";v="140"',
                'Sec-Ch-Ua-Mobile': '?0',
                'Sec-Ch-Ua-Platform': '"Linux"',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Upgrade-Insecure-Requests': '1'
            }
            
            # Fetch the Steam Store page with redirect following
            response = await client.get(store_page_url, headers=headers, follow_redirects=True)
            
            if response.status_code != 200:
                return None
            
            html_content = response.text
            
            # Parse HTML with BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Look for images with alt="Screenshot #1" attribute, filtering out blank.gif
            screenshot_imgs = soup.find_all('img', alt='Screenshot #1')
            
            # Look for the first valid screenshot (not blank.gif)
            for screenshot_img in screenshot_imgs:
                screenshot_url = screenshot_img.get('src', '')
                
                # Skip blank.gif or empty URLs
                if screenshot_url and 'blank.gif' not in screenshot_url.lower():
                    return screenshot_url
            
            return None
                
        except Exception as e:
            return None

    def find_similarity_matches(self, game_name: str, steam_apps: List[Dict], limit: int = 10) -> List[Dict]:
        """Find Steam games using similarity algorithm with global partitioned index"""
        if not game_name or not self._global_similarity_index:
            return []
        
        from game_utils import normalize_game_name, calculate_similarity
        
        # Normalize the search name
        normalized_name = normalize_game_name(game_name, remove_paranthesis=True, remove_articles=True)
        if not normalized_name:
            return []
        
        print(f"🔍 DEBUG: Steam similarity search for '{game_name}' -> normalized: '{normalized_name}'")
        
        # Get the first character to search in the right partition
        first_char = normalized_name[0] if normalized_name else 'other'
        print(f"🔍 DEBUG: Searching Steam partition '{first_char}'")
        
        matches = []
        
        # Search only in the matching partition using global index
        if first_char in self._global_similarity_index:
            partition_items = self._global_similarity_index[first_char]
            print(f"🔍 DEBUG: Found {len(partition_items)} Steam items in partition '{first_char}'")
            
            for i, item in enumerate(partition_items):
                # Calculate similarity using configured algorithm
                similarity = calculate_similarity(normalized_name, item.normalized)
                print(f"🔍 DEBUG: Steam Item {i+1}: '{item.name}' -> similarity: {similarity:.4f}")
            
                # Only include matches with reasonable similarity (threshold of 0.3)
                if similarity >= 0.3:
                    steam_id = item.appid
                    matches.append({
                        'appid': steam_id,
                        'name': item.name,
                        'description': 'Steam game',  # Steam API doesn't provide descriptions in the basic app list
                        'price': 'Unknown',  # Would need additional API call
                        'release_date': 'Unknown',  # Would need additional API call
                        'capsule_image': f"https://shared.steamstatic.com/store_item_assets/steam/apps/{steam_id}/library_600x900_2x.jpg",
                        'capsule_image_fallback': f"https://shared.steamstatic.com/store_item_assets/steam/apps/{steam_id}/library_600x900.jpg",
                        'similarity_score': similarity,
                        'matched_name': item.name
                    })
        else:
            print(f"🔍 DEBUG: No Steam partition found for character '{first_char}'")
        
        print(f"🔍 DEBUG: Found {len(matches)} Steam matches before sorting")
        
        # Sort by similatrity score (highest first) and return top N
        matches.sort(key=lambda x: x['similarity_score'], reverse=True)
        result = matches[:limit]
        
        print(f"🔍 DEBUG: Found {len(result)} Steam matches (requested: {limit})")
        for i, match in enumerate(result[:5]):  # Log top 5 matches
            print(f"🔍 DEBUG: Steam Match {i+1}: '{match['matched_name']}' (score: {match['similarity_score']:.4f})")
        
        return result

    async def parse_steam_game_page(self, steam_id: int) -> Dict[str, Any]:
        """
        Parse Steam game page HTML to extract text fields
        
        Args:
            steam_id: Steam app ID
            
        Returns:
            Dictionary with extracted fields: desc, players, publisher, developer, releasedate, genre
        """
        url = f"https://store.steampowered.com/app/{steam_id}"
        results = {
            'desc': None,
            'players': None,
            'publisher': None,
            'developer': None,
            'releasedate': None,
            'genre': None
        }
        
        try:
            # Prepare headers
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            # Create HTTP client
            limits = httpx.Limits(max_keepalive_connections=10, max_connections=10)
            async with httpx.AsyncClient(
                timeout=30.0,
                limits=limits,
                http2=True,
                headers=headers,
                follow_redirects=True
            ) as client:
                response = await client.get(url)
                response.raise_for_status()
                
                # Store HTML text for debugging
                html_text = response.text
                
                # Parse HTML
                soup = BeautifulSoup(html_text, 'html.parser')
                
                # Extract description
                desc_div = soup.find('div', class_='game_description_snippet')
                if desc_div:
                    desc_text = desc_div.get_text(strip=True)
                    # Convert <br> tags to \n
                    desc_html = str(desc_div)
                    desc_text = desc_html.replace('<br>', '\n').replace('<br/>', '\n').replace('<br />', '\n')
                    # Remove HTML tags
                    desc_soup = BeautifulSoup(desc_text, 'html.parser')
                    results['desc'] = desc_soup.get_text()
                
                # Extract players - ONLY check label divs in game_area_features_list_ctn, no fallbacks
                # Priority: multiplayer modes (2 players) over single-player (1 player)
                logger.info(f"🔍 DEBUG: Starting player extraction for Steam app {steam_id}")
                found_multiplayer = False
                found_single_player = False
                
                # Search ONLY in game_area_features_list_ctn (where features like "Single-player", "Online Co-op" are listed)
                labels = []
                game_area_features = soup.find('div', class_='game_area_features_list_ctn')
                if game_area_features:
                    logger.info(f"🔍 DEBUG: Found game_area_features_list_ctn div")
                    # Find all label divs within this container
                    labels = game_area_features.find_all('div', class_='label')
                    logger.info(f"🔍 DEBUG: Found {len(labels)} label divs in game_area_features_list_ctn")
                else:
                    logger.warning(f"🔍 DEBUG: game_area_features_list_ctn NOT FOUND - no player info will be extracted")
                    
                logger.info(f"🔍 DEBUG: Total label divs found: {len(labels)}")
                    
                if len(labels) > 0:
                    # Log all label texts for debugging
                    for i, label in enumerate(labels):
                        label_text = label.get_text(strip=True)
                        label_html = str(label)[:200]  # First 200 chars of HTML
                        label_classes = label.get('class', [])
                        logger.info(f"🔍 DEBUG: Label {i+1}: classes={label_classes}, text='{label_text}', HTML='{label_html}'")
                    
                    # Also search for "Single-player" text directly in the HTML
                    if 'Single-player' in html_text:
                        logger.info(f"🔍 DEBUG: Found 'Single-player' text in page HTML")
                        # Find the context around it
                        idx = html_text.find('Single-player')
                        context = html_text[max(0, idx-100):min(len(html_text), idx+100)]
                        logger.info(f"🔍 DEBUG: Context around 'Single-player': {context}")
                    else:
                        logger.info(f"🔍 DEBUG: 'Single-player' text NOT found in page HTML")
                    
                    if 'Singleplayer' in html_text:
                        logger.info(f"🔍 DEBUG: Found 'Singleplayer' text in page HTML")
                        idx = html_text.find('Singleplayer')
                        context = html_text[max(0, idx-100):min(len(html_text), idx+100)]
                        logger.info(f"🔍 DEBUG: Context around 'Singleplayer': {context}")
                    
                    # First pass: check for multiplayer modes (priority)
                    logger.info(f"🔍 DEBUG: First pass - checking for multiplayer modes")
                    for i, label in enumerate(labels):
                        label_text = label.get_text(strip=True)
                        logger.info(f"🔍 DEBUG: Checking label {i+1} for multiplayer: '{label_text}'")
                        
                        # Check for multiplayer modes
                        if 'Shared/Split Screen Co-op' in label_text:
                            logger.info(f"🔍 DEBUG: Found 'Shared/Split Screen Co-op' in label {i+1}")
                            found_multiplayer = True
                            break
                        elif 'Split Screen Co-op' in label_text:
                            logger.info(f"🔍 DEBUG: Found 'Split Screen Co-op' in label {i+1}")
                            found_multiplayer = True
                            break
                        elif 'Online Co-op' in label_text:
                            logger.info(f"🔍 DEBUG: Found 'Online Co-op' in label {i+1}")
                            found_multiplayer = True
                            break
                        elif 'Local Co-Op' in label_text:
                            logger.info(f"🔍 DEBUG: Found 'Local Co-Op' in label {i+1}")
                            found_multiplayer = True
                            break
                        elif 'Co-op' in label_text:
                            logger.info(f"🔍 DEBUG: Found 'Co-op' in label {i+1}")
                            found_multiplayer = True
                            break
                        elif 'Multiplayer' in label_text:
                            logger.info(f"🔍 DEBUG: Found 'Multiplayer' in label {i+1}")
                            found_multiplayer = True
                            break
                        else:
                            logger.info(f"🔍 DEBUG: Label {i+1} does not match multiplayer patterns")
                    
                    # Second pass: only check for single-player if no multiplayer found
                    if not found_multiplayer:
                        logger.info(f"🔍 DEBUG: No multiplayer found, checking for single-player")
                        for i, label in enumerate(labels):
                            label_text = label.get_text(strip=True)
                            logger.info(f"🔍 DEBUG: Checking label {i+1} for single-player: '{label_text}'")
                            
                            # Check for single-player
                            if 'Single-player' in label_text:
                                logger.info(f"🔍 DEBUG: Found 'Single-player' in label {i+1}")
                                found_single_player = True
                                break
                            elif 'Singleplayer' in label_text:
                                logger.info(f"🔍 DEBUG: Found 'Singleplayer' in label {i+1}")
                                found_single_player = True
                                break
                            else:
                                logger.info(f"🔍 DEBUG: Label {i+1} does not match single-player patterns")
                    else:
                        logger.info(f"🔍 DEBUG: Multiplayer found, skipping single-player check")
                else:
                    logger.warning(f"🔍 DEBUG: No labels found in game_area_features_list_ctn")
                
                if found_multiplayer:
                    results['players'] = '2'
                    logger.info(f"🔍 DEBUG: Final result: players = '2' (multiplayer detected)")
                elif found_single_player:
                    results['players'] = '1'
                    logger.info(f"🔍 DEBUG: Final result: players = '1' (single-player detected)")
                else:
                    logger.info(f"🔍 DEBUG: Final result: players = None (no player info found)")
                
                # Extract publisher, developer, release date, and genre from details_block
                details_block = soup.find('div', id='genresAndManufacturer')
                if details_block:
                    # Extract developer
                    dev_row = details_block.find('div', class_='dev_row')
                    if dev_row:
                        dev_label = dev_row.find('b', string='Developer:')
                        if dev_label:
                            dev_link = dev_row.find('a')
                            if dev_link:
                                results['developer'] = dev_link.get_text(strip=True)
                    
                    # Extract publisher (look for Publisher: label)
                    publisher_rows = details_block.find_all('div', class_='dev_row')
                    for row in publisher_rows:
                        pub_label = row.find('b', string='Publisher:')
                        if pub_label:
                            pub_link = row.find('a')
                            if pub_link:
                                results['publisher'] = pub_link.get_text(strip=True)
                            break
                    
                    # Extract release date
                    release_date_b = details_block.find('b', string='Release Date:')
                    if release_date_b:
                        release_text = release_date_b.next_sibling
                        if release_text:
                            release_text = release_text.strip()
                            # Remove <br> if present
                            if '<br>' in release_text:
                                release_text = release_text.split('<br>')[0].strip()
                            # Convert to ISO 8601 format (same as other scrapers)
                            try:
                                date_obj = datetime.strptime(release_text, '%d %b, %Y')
                                results['releasedate'] = date_obj.strftime('%Y%m%dT%H%M%S')
                            except ValueError:
                                try:
                                    date_obj = datetime.strptime(release_text, '%b %d, %Y')
                                    results['releasedate'] = date_obj.strftime('%Y%m%dT%H%M%S')
                                except ValueError:
                                    try:
                                        date_obj = datetime.strptime(release_text, '%d %B, %Y')
                                        results['releasedate'] = date_obj.strftime('%Y%m%dT%H%M%S')
                                    except ValueError:
                                        logger.warning(f"Could not parse release date: {release_text}")
                                        results['releasedate'] = release_text
                    
                    # Extract genre
                    genre_b = details_block.find('b', string='Genre:')
                    if genre_b:
                        genre_span = genre_b.find_next('span')
                        if genre_span:
                            genre_links = genre_span.find_all('a')
                            genres = []
                            for link in genre_links:
                                genre_text = link.get_text(strip=True)
                                if genre_text:
                                    # Apply genre mapping
                                    mapped_genre = self._map_steam_genre(genre_text)
                                    if mapped_genre:
                                        genres.append(mapped_genre)
                                    else:
                                        genres.append(genre_text)  # Use original if no mapping
                            if genres:
                                results['genre'] = ', '.join(genres)
                
        except Exception as e:
            logger.error(f"Error parsing Steam game page for app {steam_id}: {e}")
        
        return results
    
    def _map_steam_genre(self, genre_text: str) -> str:
        """Map Steam genre to standardized genre name"""
        try:
            with open('var/config/scrapper_genre_mapping.json', 'r') as f:
                genre_mapping = json.load(f)
            
            steam_mapping = genre_mapping.get('steam', {}).get('map', {})
            return steam_mapping.get(genre_text, genre_text)
        except Exception as e:
            logger.error(f"Error mapping Steam genre: {e}")
            return genre_text
    
    def get_steam_capsule_images(self, steam_id: int) -> Dict[str, Optional[str]]:
        """Get capsule image URLs for a specific Steam app ID"""
        if not steam_id:
            return {
                'capsule_image': None,
                'capsule_image_fallback': None
            }
        
        return {
            'capsule_image': f"https://shared.steamstatic.com/store_item_assets/steam/apps/{steam_id}/library_600x900_2x.jpg",
            'capsule_image_fallback': f"https://shared.steamstatic.com/store_item_assets/steam/apps/{steam_id}/library_600x900.jpg"
        }


def get_media_directory_and_extensions(gamelist_field: str) -> Tuple[Optional[str], Optional[List[str]]]:
    """Get media directory and extensions for a gamelist field"""
    try:
        with open('var/config/config.json', 'r') as f:
            config = json.load(f)
        
        media_fields = config.get('media_fields', {})
        field_config = media_fields.get(gamelist_field, {})
        
        directory = field_config.get('directory', '')
        extensions = field_config.get('extensions', [])
        
        return directory, extensions
        
    except Exception as e:
        logger.error(f"Error getting media directory for {gamelist_field}: {e}")
        return None, None
