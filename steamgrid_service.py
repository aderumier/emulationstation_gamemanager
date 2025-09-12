#!/usr/bin/env python3
"""
SteamGrid Service - Handles Steam API interactions for game matching
"""

import os
import json
import time
import httpx
import asyncio
import re
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import logging
from game_utils import normalize_game_name, convert_image_replace, should_convert_field, needs_conversion

logger = logging.getLogger(__name__)

class SteamGridService:
    """Service for interacting with Steam API and managing app index cache"""
    
    def __init__(self, cache_dir: str = "var/db/steamgrid"):
        self.cache_dir = cache_dir
        self.app_index_file = os.path.join(cache_dir, "appindex.json")
        self.steam_api_url = "https://api.steampowered.com/ISteamApps/GetAppList/v0002/"
        self.cache_retention_hours = 24
        
        # Indexing cache for performance
        self._unified_index = None
        self._cached_steam_apps = None
        
        # Ensure cache directory exists
        os.makedirs(cache_dir, exist_ok=True)
    
    def close(self):
        """Close any open connections or resources"""
        # Clear cached data to free memory
        self._unified_index = None
        self._cached_steam_apps = None
    
    
    def load_app_index(self) -> Optional[List[Dict]]:
        """Load Steam app index from cache if valid"""
        if not os.path.exists(self.app_index_file):
            return None
        
        try:
            with open(self.app_index_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Check if cache is still valid
            cache_time = datetime.fromisoformat(data.get('cached_at', '1970-01-01T00:00:00'))
            if datetime.now() - cache_time > timedelta(hours=self.cache_retention_hours):
                logger.info("Steam app index cache expired, will refresh")
                return None
            
            # Return the pre-built flat list
            steam_apps = data.get('steam_apps', [])
            logger.info(f"Loaded Steam app index from cache ({len(steam_apps)} apps)")
            return steam_apps
            
        except Exception as e:
            logger.error(f"Failed to load Steam app index cache: {e}")
            return None
    
    def save_app_index(self, steam_apps: List[Dict]) -> None:
        """Save Steam app index to cache"""
        try:
            data = {
                'cached_at': datetime.now().isoformat(),
                'steam_apps': steam_apps
            }
            
            with open(self.app_index_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved Steam app index to cache ({len(steam_apps)} apps)")
            
        except Exception as e:
            logger.error(f"Failed to save Steam app index cache: {e}")
    
    async def fetch_steam_apps(self) -> List[Dict]:
        """Fetch Steam app list from API"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                logger.info("Fetching Steam app list from API...")
                response = await client.get(self.steam_api_url)
                response.raise_for_status()
                
                data = response.json()
                apps = data.get('applist', {}).get('apps', [])
                
                logger.info(f"Fetched {len(apps)} Steam apps from API")
                return apps
                
        except Exception as e:
            logger.error(f"Failed to fetch Steam app list: {e}")
            return []
    
    async def get_app_index(self) -> List[Dict]:
        """Get Steam app index, loading from cache or fetching from API"""
        # Try to load from cache first
        cached_steam_apps = self.load_app_index()
        if cached_steam_apps:
            return cached_steam_apps
        
        # Fetch from API if cache is invalid or missing
        apps = await self.fetch_steam_apps()
        if not apps:
            return []
        
        # Build the flat list
        steam_apps = self._build_index(apps)
        
        # Save to cache
        self.save_app_index(steam_apps)
        
        return steam_apps
    
    def _build_index(self, apps: List[Dict]) -> List[Dict]:
        """Build flat list of Steam apps with normalized names for efficient matching"""
        steam_apps = []
        
        for app in apps:
            appid = app.get('appid')
            name = app.get('name', '')
            
            if not appid or not name:
                continue
            
            # Normalize the name
            normalized = normalize_game_name(name)
            if not normalized:
                continue
            
            # Add to flat list
            steam_apps.append({
                'appid': appid,
                'name': name,
                'normalized': normalized
            })
        
        logger.info(f"Built Steam app index with {len(steam_apps)} apps")
        return steam_apps
    
    def find_best_match(self, game_name: str, steam_apps: List[Dict]) -> Optional[Dict]:
        """
        Find best matching Steam app for a game name
        Uses the same sophisticated matching logic as LaunchBox but adapted for Steam data
        Returns a dict with match info including whether it's a perfect match and similarity score
        """
        if not game_name or not steam_apps:
            return None
        
        # Create indexed lookups for O(1) exact matches instead of O(n) linear searches
        # Apply the same normalization as used in the index building
        
        normalized_search = normalize_game_name(game_name)
        
        # Fallback version removes parentheses and brackets after normalization (including nested)
        normalized_search_no_parens = re.sub(r'\s*[\(\[][^()\[\]]*(?:[\(\[][^()\[\]]*[\)\]][^()\[\]]*)*[\)\]]', '', game_name)
        normalized_search_no_parens = normalize_game_name(normalized_search_no_parens)
        
        # Build unified index on first call or when steam_apps changes (cached for subsequent calls)
        if self._unified_index is None or self._cached_steam_apps is not steam_apps:
            logger.debug(f"Building unified Steam index for {len(steam_apps)} apps...")
            self._unified_index = {}
            self._cached_steam_apps = steam_apps
            
            # Build unified index for Steam app names
            indexed_count = 0
            for i, app in enumerate(steam_apps):
                # Index normalized name
                normalized_name = app.get('normalized', '')
                if normalized_name:
                    if normalized_name not in self._unified_index:
                        self._unified_index[normalized_name] = []
                    self._unified_index[normalized_name].append(i)
                    indexed_count += 1
            
            logger.debug(f"Indexed {indexed_count} Steam app names")
        
        # Try exact match using unified index (O(1) lookup)
        # First try with normalized search (with parentheses removed)
        if normalized_search in self._unified_index:
            for app_idx in self._unified_index[normalized_search]:
                app = steam_apps[app_idx]
                logger.debug(f"Found exact Steam match for '{game_name}' → '{app['name']}' (appid: {app['appid']})")
                return {
                    'app': app,
                    'match_type': 'perfect',
                    'score': 1.0,
                    'matched_name': app['name']
                }
        
        # If no match found with normalized search, try with no_parens version
        if normalized_search != normalized_search_no_parens and normalized_search_no_parens in self._unified_index:
            for app_idx in self._unified_index[normalized_search_no_parens]:
                app = steam_apps[app_idx]
                logger.debug(f"Found exact Steam match for '{game_name}' → '{app['name']}' (appid: {app['appid']}, no parens)")
                return {
                    'app': app,
                    'match_type': 'perfect',
                    'score': 1.0,
                    'matched_name': app['name']
                }
        
        # No similarity matching - only exact matches are accepted
        return None
    
    
    async def find_steam_app(self, game_name: str) -> Optional[Dict]:
        """Find Steam app for a game name"""
        steam_apps = await self.get_app_index()
        return self.find_best_match(game_name, steam_apps)
    
    async def get_steamgrid_media(self, steamgrid_id: int, media_types: List[str] = None, api_key: str = None) -> Dict[str, List[Dict]]:
        """
        Get media from SteamGridDB API for a SteamGridDB game ID
        
        Args:
            steamgrid_id: SteamGridDB game ID
            media_types: List of media types to fetch (grids, heroes, logos)
            api_key: SteamGridDB API key for authentication
            
        Returns:
            Dict with media types as keys and lists of media objects as values
        """
        if media_types is None:
            media_types = ['grids', 'heroes', 'logos']
        
        base_url = "https://www.steamgriddb.com/api/v2"
        results = {}
        
        # Prepare headers
        headers = {}
        if api_key:
            headers['Authorization'] = f'Bearer {api_key}'
            logger.debug(f"Using SteamGridDB API key: {api_key[:8]}...{api_key[-4:] if len(api_key) > 12 else '***'}")
        else:
            logger.warning("No SteamGridDB API key provided - requests may be rate limited")
        
        # Create HTTP client with connection pool and HTTP/2
        limits = httpx.Limits(max_connections=50, max_keepalive_connections=50)
        async with httpx.AsyncClient(
            limits=limits,
            http2=True,
            timeout=30.0,
            headers=headers
        ) as client:
            
            for media_type in media_types:
                try:
                    url = f"{base_url}/{media_type}/game/{steamgrid_id}"
                    logger.debug(f"Fetching {media_type} for SteamGridDB ID {steamgrid_id}: {url}")
                    
                    response = await client.get(url)
                    
                    if response.status_code == 401:
                        logger.error(f"SteamGridDB API authentication failed for {media_type} (SteamGridDB ID {steamgrid_id}). Check your API key.")
                        if api_key:
                            logger.error(f"API key being used: {api_key[:8]}...{api_key[-4:] if len(api_key) > 12 else '***'}")
                        else:
                            logger.error("No API key provided")
                    elif response.status_code == 429:
                        logger.warning(f"SteamGridDB API rate limited for {media_type} (SteamGridDB ID {steamgrid_id})")
                    else:
                        response.raise_for_status()
                    
                    data = response.json()
                    print(f"    📊 SteamGridDB {media_type} API Response for ID {steamgrid_id}:")
                    print(f"      - Success: {data.get('success', 'N/A')}")
                    print(f"      - Data count: {len(data.get('data', []))}")
                    if data.get('data') and len(data['data']) > 0:
                        print(f"      - First item: {data['data'][0] if data['data'] else 'N/A'}")
                    logger.debug(f"SteamGridDB {media_type} API Response for ID {steamgrid_id}: {data}")
                    
                    if data.get('success') and 'data' in data:
                        results[media_type] = data['data']
                        print(f"    ✅ Found {len(data['data'])} {media_type} items")
                        logger.debug(f"Found {len(data['data'])} {media_type} for SteamGridDB ID {steamgrid_id}")
                    else:
                        results[media_type] = []
                        print(f"    ❌ No {media_type} found")
                        logger.debug(f"No {media_type} found for SteamGridDB ID {steamgrid_id}")
                        
                except Exception as e:
                    logger.error(f"Failed to fetch {media_type} for SteamGridDB ID {steamgrid_id}: {e}")
                    results[media_type] = []
        
        return results
    
    def select_best_media(self, media_list: List[Dict], media_type: str) -> Optional[Dict]:
        """
        Select the best media from a list based on score
        
        Args:
            media_list: List of media objects from SteamGridDB API
            media_type: Type of media (grids, heroes, logos)
            
        Returns:
            Best media object or None if no media available
        """
        if not media_list:
            return None
        
        # For grids, select the one with the highest score
        if media_type == 'grids':
            best_media = max(media_list, key=lambda x: x.get('score', 0))
            logger.debug(f"Selected best grid with score {best_media.get('score', 0)}")
            return best_media
        
        # For other types, just return the first one
        return media_list[0]
    
    async def download_steamgrid_media(self, steamgrid_id: int, game_name: str, 
                                     roms_root: str, system_name: str, 
                                     selected_fields: List[str] = None,
                                     image_type_mappings: Dict[str, str] = None,
                                     api_key: str = None) -> Dict[str, str]:
        """
        Download media from SteamGridDB for a SteamGridDB game ID
        
        Args:
            steamgrid_id: SteamGridDB game ID
            game_name: Name of the game
            roms_root: Root directory for ROMs
            system_name: Name of the system
            selected_fields: List of selected media fields to download
            image_type_mappings: Mapping of SteamGridDB types to local media fields
            api_key: SteamGridDB API key for authentication
            
        Returns:
            Dict with media field names as keys and relative file paths as values
        """
        if image_type_mappings is None:
            image_type_mappings = {
                'grids': 'boxart',
                'logos': 'marquee', 
                'heroes': 'fanart'
            }
        
        # Get all media types if no specific fields selected
        if selected_fields is None or not selected_fields:
            media_types = list(image_type_mappings.keys())
        else:
            # Only get media types that are mapped to selected fields
            media_types = [sg_type for sg_type, local_field in image_type_mappings.items() 
                          if local_field in selected_fields]
        
        if not media_types:
            logger.debug(f"No media types to download for SteamGridDB ID {steamgrid_id}")
            return {}
        
        # Fetch media from SteamGridDB API
        print(f"  🔍 Fetching SteamGridDB media for SteamGridDB ID {steamgrid_id} with API key: {'Yes' if api_key else 'No'}")
        logger.debug(f"Downloading SteamGridDB media for SteamGridDB ID {steamgrid_id} with API key: {'Yes' if api_key else 'No'}")
        media_data = await self.get_steamgrid_media(steamgrid_id, media_types, api_key)
        
        # Log what was found
        total_media = sum(len(media_list) for media_list in media_data.values())
        print(f"  📈 Found {total_media} total media items across all types")
        for media_type, media_list in media_data.items():
            print(f"    - {media_type}: {len(media_list)} items")
            if media_list:
                print(f"      Sample {media_type} item: {media_list[0]}")
        
        print(f"  🔍 Full media data structure: {media_data}")
        logger.debug(f"Full media data structure: {media_data}")
        
        downloaded_media = {}
        
        # Create HTTP client for downloading images
        limits = httpx.Limits(max_connections=50, max_keepalive_connections=50)
        async with httpx.AsyncClient(
            limits=limits,
            http2=True,
            timeout=30.0
        ) as client:
            
            for sg_type, local_field in image_type_mappings.items():
                print(f"  🎯 Processing {sg_type} -> {local_field}")
                
                if sg_type not in media_data or not media_data[sg_type]:
                    print(f"    ❌ No {sg_type} media available")
                    continue
                
                print(f"    📦 Found {len(media_data[sg_type])} {sg_type} items")
                
                # Select best media for this type
                print(f"    🎯 Selecting best {sg_type} from {len(media_data[sg_type])} options...")
                for i, media_item in enumerate(media_data[sg_type]):
                    print(f"      Option {i+1}: {media_item}")
                
                best_media = self.select_best_media(media_data[sg_type], sg_type)
                if not best_media or 'url' not in best_media:
                    print(f"    ❌ No valid {sg_type} media selected")
                    continue
                
                print(f"    ⭐ Selected best {sg_type} (score: {best_media.get('score', 'N/A')})")
                print(f"    🔗 URL: {best_media['url']}")
                print(f"    📋 Full selected media: {best_media}")
                
                # Download the image
                try:
                    print(f"    ⬇️ Downloading {sg_type} image...")
                    relative_path = await self._download_steamgrid_image(
                        client, best_media['url'], local_field, 
                        game_name, roms_root, system_name
                    )
                    
                    if relative_path:
                        downloaded_media[local_field] = relative_path
                        print(f"    ✅ Downloaded {sg_type} as {local_field}: {relative_path}")
                        logger.debug(f"Downloaded {sg_type} as {local_field}: {relative_path}")
                    else:
                        print(f"    ❌ Failed to download {sg_type} image")
                
                except Exception as e:
                    print(f"    ❌ Error downloading {sg_type}: {e}")
                    logger.error(f"Failed to download {sg_type} for {game_name}: {e}")
        
        print(f"  🎯 Final download results: {downloaded_media}")
        logger.debug(f"Final download results: {downloaded_media}")
        return downloaded_media
    
    async def _download_steamgrid_image(self, client: httpx.AsyncClient, image_url: str, 
                                      media_field: str, game_name: str, 
                                      roms_root: str, system_name: str) -> Optional[str]:
        """
        Download a single image from SteamGridDB
        
        Args:
            client: HTTP client
            image_url: URL of the image to download
            media_field: Local media field name
            game_name: Name of the game
            roms_root: Root directory for ROMs
            system_name: Name of the system
            
        Returns:
            Relative path to downloaded image or None if failed
        """
        try:
            print(f"      📁 Setting up download for {media_field}")
            
            # Get media field configuration
            with open('var/config/config.json', 'r') as f:
                config = json.load(f)
            
            media_fields = config.get('media_fields', {})
            if media_field not in media_fields:
                print(f"      ❌ Media field {media_field} not found in config")
                logger.warning(f"Media field {media_field} not found in config")
                return None
            
            field_config = media_fields[media_field]
            directory = field_config.get('directory', media_field)
            target_extension = field_config.get('target_extension', '.png')
            
            print(f"      📂 Directory: {directory}, Extension: {target_extension}")
            
            # Create media directory
            media_dir = os.path.join(roms_root, system_name, 'media', directory)
            os.makedirs(media_dir, exist_ok=True)
            
            # Create safe filename
            safe_name = re.sub(r'[<>:"/\\|?*]', '_', game_name)
            filename = f"{safe_name}{target_extension}"
            file_path = os.path.join(media_dir, filename)
            
            print(f"      💾 Saving to: {file_path}")
            
            # Download image
            print(f"      🌐 Downloading from: {image_url}")
            logger.debug(f"Downloading {image_url} to {file_path}")
            response = await client.get(image_url)
            response.raise_for_status()
            
            print(f"      ✅ Download successful, size: {len(response.content)} bytes")
            print(f"      📊 Response headers: {dict(response.headers)}")
            print(f"      🎨 Content type: {response.headers.get('content-type', 'Unknown')}")
            
            # Write image to file
            with open(file_path, 'wb') as f:
                f.write(response.content)
            
            # Convert image if needed
            if needs_conversion(file_path, target_extension):
                print(f"      🔄 Converting image to {target_extension}")
                converted_path = convert_image_replace(file_path, target_extension)
                if converted_path:
                    file_path = converted_path
                    filename = os.path.basename(converted_path)
                    print(f"      ✅ Converted to: {filename}")
            
            # Return relative path
            relative_path = f"./media/{directory}/{filename}"
            print(f"      🎯 Final path: {relative_path}")
            logger.debug(f"Successfully downloaded SteamGridDB image: {relative_path}")
            return relative_path
            
        except Exception as e:
            logger.error(f"Failed to download SteamGridDB image from {image_url}: {e}")
            return None
    
    def load_credentials(self) -> Dict[str, str]:
        """Load SteamGridDB credentials from credentials.json"""
        credentials_file = 'var/config/credentials.json'
        try:
            if os.path.exists(credentials_file):
                with open(credentials_file, 'r') as f:
                    credentials = json.load(f)
                    return credentials.get('steamgriddb', {})
            return {}
        except Exception as e:
            logger.error(f"Failed to load SteamGridDB credentials: {e}")
            return {}
    
    def save_credentials(self, api_key: str) -> bool:
        """Save SteamGridDB credentials to credentials.json"""
        credentials_file = 'var/config/credentials.json'
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(credentials_file), exist_ok=True)
            
            # Load existing credentials
            credentials = {}
            if os.path.exists(credentials_file):
                with open(credentials_file, 'r') as f:
                    credentials = json.load(f)
            
            # Update SteamGridDB credentials
            if 'steamgriddb' not in credentials:
                credentials['steamgriddb'] = {}
            credentials['steamgriddb']['api_key'] = api_key
            
            # Save credentials
            with open(credentials_file, 'w') as f:
                json.dump(credentials, f, indent=4)
            
            logger.info("SteamGridDB credentials saved successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save SteamGridDB credentials: {e}")
            return False
    
    def get_api_key(self) -> Optional[str]:
        """Get SteamGridDB API key from credentials"""
        credentials = self.load_credentials()
        return credentials.get('api_key')
    
    async def get_steamgrid_id_by_steam_id(self, steam_id: int, api_key: str = None) -> Optional[int]:
        """
        Get SteamGridDB game ID by Steam ID using getGameById API
        
        Args:
            steam_id: Steam app ID
            api_key: SteamGridDB API key for authentication
            
        Returns:
            SteamGridDB game ID or None if not found
        """
        try:
            base_url = "https://www.steamgriddb.com/api/v2"
            
            # Prepare headers
            headers = {}
            if api_key:
                headers['Authorization'] = f'Bearer {api_key}'
            
            # Create HTTP client
            limits = httpx.Limits(max_connections=50, max_keepalive_connections=50)
            async with httpx.AsyncClient(
                limits=limits,
                http2=True,
                timeout=30.0,
                headers=headers
            ) as client:
                url = f"{base_url}/games/steam/{steam_id}"
                print(f"  🔍 Looking up SteamGridDB ID for Steam ID {steam_id}")
                logger.debug(f"Looking up SteamGridDB ID for Steam ID {steam_id}: {url}")
                
                response = await client.get(url)
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"  📊 SteamGridDB API Response for Steam ID {steam_id}:")
                    print(f"    - Success: {data.get('success', 'N/A')}")
                    print(f"    - Data: {data.get('data', 'N/A')}")
                    logger.debug(f"SteamGridDB API Response for Steam ID {steam_id}: {data}")
                    
                    if data.get('success') and 'data' in data and data['data']:
                        steamgrid_id = data['data']['id']
                        print(f"  ✅ Found SteamGridDB ID: {steamgrid_id}")
                        logger.debug(f"Found SteamGridDB ID {steamgrid_id} for Steam ID {steam_id}")
                        return steamgrid_id
                    else:
                        print(f"  ❌ No SteamGridDB game found for Steam ID {steam_id}")
                        logger.debug(f"No SteamGridDB game found for Steam ID {steam_id}")
                        return None
                elif response.status_code == 401:
                    print(f"  ❌ SteamGridDB API authentication failed for Steam ID {steam_id}")
                    logger.error(f"SteamGridDB API authentication failed for Steam ID {steam_id}")
                    return None
                else:
                    print(f"  ❌ Failed to lookup SteamGridDB ID for Steam ID {steam_id}: HTTP {response.status_code}")
                    logger.error(f"Failed to lookup SteamGridDB ID for Steam ID {steam_id}: HTTP {response.status_code}")
                    return None
                    
        except Exception as e:
            print(f"  ❌ Error looking up SteamGridDB ID for Steam ID {steam_id}: {e}")
            logger.error(f"Error looking up SteamGridDB ID for Steam ID {steam_id}: {e}")
            return None
    
    async def get_steamgrid_id_by_name(self, game_name: str, api_key: str = None) -> Optional[int]:
        """
        Get SteamGridDB game ID by game name using searchGrids API
        
        Args:
            game_name: Name of the game
            api_key: SteamGridDB API key for authentication
            
        Returns:
            SteamGridDB game ID or None if not found
        """
        try:
            # Clean game name - remove text between parentheses
            import re
            clean_name = re.sub(r'\s*\([^)]*\)', '', game_name).strip()
            if not clean_name:
                clean_name = game_name
            
            base_url = "https://www.steamgriddb.com/api/v2"
            
            # Prepare headers
            headers = {}
            if api_key:
                headers['Authorization'] = f'Bearer {api_key}'
            
            # Create HTTP client
            limits = httpx.Limits(max_connections=50, max_keepalive_connections=50)
            async with httpx.AsyncClient(
                limits=limits,
                http2=True,
                timeout=30.0,
                headers=headers
            ) as client:
                # Search for grids (which includes game info)
                url = f"{base_url}/search/grids/{clean_name}"
                print(f"  🔍 Searching SteamGridDB for game: '{clean_name}' (original: '{game_name}')")
                logger.debug(f"Searching SteamGridDB for game: '{clean_name}' (original: '{game_name}'): {url}")
                
                response = await client.get(url)
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"  📊 SteamGridDB Search API Response for '{clean_name}':")
                    print(f"    - Success: {data.get('success', 'N/A')}")
                    print(f"    - Results count: {len(data.get('data', []))}")
                    if data.get('data'):
                        print(f"    - First result: {data['data'][0] if data['data'] else 'N/A'}")
                    logger.debug(f"SteamGridDB Search API Response for '{clean_name}': {data}")
                    
                    if data.get('success') and 'data' in data and data['data']:
                        # Get the first result (most relevant)
                        first_result = data['data'][0]
                        print(f"  🔍 Analyzing first result: {first_result}")
                        if 'game' in first_result and 'id' in first_result['game']:
                            steamgrid_id = first_result['game']['id']
                            game_title = first_result['game'].get('name', 'Unknown')
                            print(f"  ✅ Found SteamGridDB ID: {steamgrid_id} for game: '{game_title}'")
                            logger.debug(f"Found SteamGridDB ID {steamgrid_id} for game '{game_title}'")
                            return steamgrid_id
                        else:
                            print(f"  ❌ First result doesn't contain game ID: {first_result}")
                            logger.debug(f"First result doesn't contain game ID: {first_result}")
                    else:
                        print(f"  ❌ No SteamGridDB games found for: '{clean_name}'")
                        logger.debug(f"No SteamGridDB games found for: '{clean_name}'")
                        return None
                elif response.status_code == 401:
                    print(f"  ❌ SteamGridDB API authentication failed for game: '{clean_name}'")
                    logger.error(f"SteamGridDB API authentication failed for game: '{clean_name}'")
                    return None
                else:
                    print(f"  ❌ Failed to search SteamGridDB for game: '{clean_name}': HTTP {response.status_code}")
                    logger.error(f"Failed to search SteamGridDB for game: '{clean_name}': HTTP {response.status_code}")
                    return None
                    
        except Exception as e:
            print(f"  ❌ Error searching SteamGridDB for game: '{game_name}': {e}")
            logger.error(f"Error searching SteamGridDB for game: '{game_name}': {e}")
            return None
    
    async def get_steamgrid_id(self, steam_id: int = None, game_name: str = None, api_key: str = None) -> Optional[int]:
        """
        Get SteamGridDB game ID by Steam ID or game name
        
        Args:
            steam_id: Steam app ID (preferred method)
            game_name: Name of the game (fallback method)
            api_key: SteamGridDB API key for authentication
            
        Returns:
            SteamGridDB game ID or None if not found
        """
        # Try Steam ID first if available
        if steam_id:
            steamgrid_id = await self.get_steamgrid_id_by_steam_id(steam_id, api_key)
            if steamgrid_id:
                return steamgrid_id
        
        # Fallback to game name search
        if game_name:
            print(f"  🔄 Falling back to name search for: '{game_name}'")
            return await self.get_steamgrid_id_by_name(game_name, api_key)
        
        return None
