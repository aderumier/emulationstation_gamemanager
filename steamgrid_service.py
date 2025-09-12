#!/usr/bin/env python3
"""
SteamGridDB Service - Handles SteamGridDB API interactions for media scraping
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
    """Service for interacting with SteamGridDB API for media downloads"""
    
    def __init__(self, cache_dir: str = "var/db/steamgrid"):
        self.cache_dir = cache_dir
        
        # Ensure cache directory exists
        os.makedirs(cache_dir, exist_ok=True)
    
    def close(self):
        """Close any open connections or resources"""
        # No persistent connections to close
        pass
    
    def get_api_key(self) -> Optional[str]:
        """Get SteamGridDB API key from credentials"""
        try:
            credentials_path = 'var/config/credentials.json'
            if os.path.exists(credentials_path):
                with open(credentials_path, 'r') as f:
                    credentials = json.load(f)
                return credentials.get('steamgriddb_api_key')
            return None
        except Exception as e:
            logger.error(f"Error loading SteamGridDB API key: {e}")
            return None
        
    def save_api_key(self, api_key: str) -> bool:
        """Save SteamGridDB API key to credentials"""
        try:
            credentials_path = 'var/config/credentials.json'
            os.makedirs(os.path.dirname(credentials_path), exist_ok=True)
            
            credentials = {}
            if os.path.exists(credentials_path):
                with open(credentials_path, 'r') as f:
                    credentials = json.load(f)
            
            credentials['steamgriddb_api_key'] = api_key
            
            with open(credentials_path, 'w') as f:
                json.dump(credentials, f, indent=2)
            
            return True
        except Exception as e:
            logger.error(f"Error saving SteamGridDB API key: {e}")
            return False
    
    async def get_steamgrid_id_by_steam_id(self, steam_id: int, api_key: str = None) -> Optional[int]:
        """Get SteamGridDB ID using Steam ID"""
        if not steam_id:
            return None
    
        try:
            base_url = "https://www.steamgriddb.com/api/v2"
            url = f"{base_url}/games/steam/{steam_id}"
            
            headers = {}
            if api_key:
                headers['Authorization'] = f'Bearer {api_key}'
                logger.debug(f"Using SteamGridDB API key: {api_key[:8]}...{api_key[-4:] if len(api_key) > 12 else '***'}")
            else:
                logger.warning("No SteamGridDB API key provided - requests may be rate limited")
            
            limits = httpx.Limits(max_connections=50, max_keepalive_connections=50)
            async with httpx.AsyncClient(
                limits=limits,
                http2=True,
                timeout=30.0,
                headers=headers
            ) as client:
                logger.debug(f"Fetching SteamGridDB ID for Steam ID {steam_id}: {url}")
                
                response = await client.get(url)
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"🔍 SteamGridDB Steam ID lookup response for Steam ID {steam_id}:")
                    print(f"   📊 Full response data: {json.dumps(data, indent=2)}")
                    
                    if data.get('success') and data.get('data'):
                        steamgrid_id = data['data'].get('id')
                        game_name = data['data'].get('name', 'Unknown')
                        verified = data['data'].get('verified', False)
                        print(f"   ✅ Found SteamGridDB ID: {steamgrid_id}, Name: '{game_name}', Verified: {verified}")
                        return steamgrid_id
                    else:
                        print(f"   ❌ No SteamGridDB ID found for Steam ID {steam_id} (success={data.get('success')}, data={data.get('data')})")
                        return None
                elif response.status_code == 401:
                    logger.error("SteamGridDB API authentication failed - check API key")
                    return None
                elif response.status_code == 429:
                    logger.warning("SteamGridDB API rate limit exceeded")
                    return None
                else:
                    logger.warning(f"SteamGridDB API error for Steam ID {steam_id}: HTTP {response.status_code}")
                    return None
            
        except Exception as e:
            logger.error(f"Error fetching SteamGridDB ID for Steam ID {steam_id}: {e}")
            return None
    
    async def get_steamgrid_id_by_name(self, game_name: str, api_key: str = None) -> Optional[int]:
        """Get SteamGridDB ID by searching game name"""
        if not game_name:
            return None
        
        try:
            # Clean game name by removing text in parentheses
            clean_name = re.sub(r'\s*\([^)]*\)', '', game_name).strip()
            
            # URL encode the game name
            import urllib.parse
            encoded_name = urllib.parse.quote(clean_name)
            
            base_url = "https://www.steamgriddb.com/api/v2"
            url = f"{base_url}/search/autocomplete/{encoded_name}"
            
            headers = {}
            if api_key:
                headers['Authorization'] = f'Bearer {api_key}'
                logger.debug(f"Using SteamGridDB API key: {api_key[:8]}...{api_key[-4:] if len(api_key) > 12 else '***'}")
            else:
                logger.warning("No SteamGridDB API key provided - requests may be rate limited")
            
            limits = httpx.Limits(max_connections=50, max_keepalive_connections=50)
            async with httpx.AsyncClient(
                limits=limits,
                http2=True,
                timeout=30.0,
                headers=headers
            ) as client:
                logger.debug(f"Searching SteamGridDB for game '{clean_name}': {url}")
                
                response = await client.get(url)
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"🔍 SteamGridDB search response for '{clean_name}':")
                    print(f"   📊 Full response data: {json.dumps(data, indent=2)}")
                    
                    if data.get('success') and data.get('data'):
                        games = data['data']
                        print(f"   🎮 Found {len(games)} games in SteamGridDB search results:")
                        for i, game in enumerate(games):
                            print(f"      [{i+1}] ID: {game.get('id')}, Name: '{game.get('name')}', Verified: {game.get('verified', False)}")
                        
                        if games:
                            # Return the first game's ID
                            steamgrid_id = games[0].get('id')
                            game_name = games[0].get('name', 'Unknown')
                            print(f"   ✅ Selected first game: ID={steamgrid_id}, Name='{game_name}'")
                            return steamgrid_id
                    else:
                        print(f"   ❌ No SteamGridDB games found for '{clean_name}' (success={data.get('success')}, data={data.get('data')})")
                        return None
                elif response.status_code == 401:
                    logger.error("SteamGridDB API authentication failed - check API key")
                    return None
                elif response.status_code == 429:
                    logger.warning("SteamGridDB API rate limit exceeded")
                    return None
                else:
                    logger.warning(f"SteamGridDB API error for '{clean_name}': HTTP {response.status_code}")
                    return None
                
        except Exception as e:
            logger.error(f"Error searching SteamGridDB for '{game_name}': {e}")
            return None
    
    async def get_steamgrid_id(self, steam_id: int = None, game_name: str = None, api_key: str = None) -> Optional[int]:
        """Get SteamGridDB ID by Steam ID or game name"""
        # Try Steam ID first if available
        if steam_id:
            steamgrid_id = await self.get_steamgrid_id_by_steam_id(steam_id, api_key)
            if steamgrid_id:
                return steamgrid_id
        
        # Fall back to name search if Steam ID didn't work
        if game_name:
            return await self.get_steamgrid_id_by_name(game_name, api_key)
        
        return None
    
    async def get_steamgrid_media(self, steamgrid_id: int, media_types: List[str] = None, api_key: str = None) -> Dict[str, List[Dict]]:
        """Get media from SteamGridDB for a specific game"""
        if not steamgrid_id:
            return {}
        
        if not media_types:
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
                        logger.error("SteamGridDB API authentication failed - check API key")
                        continue
                    elif response.status_code == 429:
                        logger.warning("SteamGridDB API rate limit exceeded")
                        continue
                    elif response.status_code != 200:
                        logger.warning(f"SteamGridDB API error for {media_type}: HTTP {response.status_code}")
                        continue
                    
                    data = response.json()
#                    print(f"🔍 SteamGridDB {media_type} API response for ID {steamgrid_id}:")
#                    print(f"   📊 Full response data: {json.dumps(data, indent=2)}")
                    
                    if data.get('success') and data.get('data'):
                        media_items = data['data']
                        results[media_type] = media_items
                        print(f"   ✅ Found {len(media_items)} {media_type} items for SteamGridDB ID {steamgrid_id}")
                        for i, item in enumerate(media_items[:3]):  # Show first 3 items
                            print(f"      [{i+1}] ID: {item.get('id')}, URL: {item.get('url', 'N/A')[:50]}..., Score: {item.get('score', 'N/A')}")
                        if len(media_items) > 3:
                            print(f"      ... and {len(media_items) - 3} more items")
                    else:
                        print(f"   ❌ No {media_type} found for SteamGridDB ID {steamgrid_id} (success={data.get('success')}, data={data.get('data')})")
                        results[media_type] = []
                        
                except Exception as e:
                    logger.error(f"Error fetching {media_type} for SteamGridDB ID {steamgrid_id}: {e}")
                    results[media_type] = []
        
        return results
    
    async def download_steamgrid_media(self, steamgrid_id: int, game_name: str, 
                                     roms_root: str, system_name: str,
                                     selected_fields: List[str] = None,
                                     image_type_mappings: Dict[str, str] = None,
                                     api_key: str = None,
                                     overwrite_media_fields: bool = False,
                                     gamelist_path: str = None) -> Dict[str, str]:
        """Download media from SteamGridDB for a specific game"""
        if not steamgrid_id or not game_name:
            return {}
        
        if not image_type_mappings:
            image_type_mappings = {
                'grids': 'boxart',
                'logos': 'marquee',
                'heroes': 'fanart'
            }
        
        if not selected_fields:
            selected_fields = list(image_type_mappings.keys())
        
        # Get media from SteamGridDB
        media_data = await self.get_steamgrid_media(steamgrid_id, selected_fields, api_key)
        
        if not media_data:
            logger.warning(f"No media data received from SteamGridDB for {game_name}")
            return {}
        
        results = {}
        
        # First, check which fields need to be downloaded
        fields_to_download = {}
        
        for media_type, media_list in media_data.items():
            if not media_list or media_type not in image_type_mappings:
                continue
            
            # Check if this field is selected
            if selected_fields and media_type not in selected_fields:
                logger.debug(f"Skipping {media_type} -> {image_type_mappings[media_type]} (not selected)")
                continue
            
            # Get the target field name
            target_field = image_type_mappings[media_type]
            
            # Check if we should skip this media field based on overwrite setting
            should_download = True
            if not overwrite_media_fields and gamelist_path:
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
                                # Use the mapped field name (target_field) which is the actual gamelist field
                                media_elem = game.find(target_field)
                                if media_elem is not None and media_elem.text and media_elem.text.strip():
                                    logger.debug(f"Media field {target_field} (mapped from {media_type}) is not empty for {game_name}, skipping download")
                                    should_download = False
                                else:
                                    logger.debug(f"Media field {target_field} (mapped from {media_type}) is empty for {game_name}, will download")
                                break
                    except Exception as e:
                        logger.warning(f"Error reading gamelist.xml: {e}")
            
            if should_download:
                fields_to_download[media_type] = {
                    'media_list': media_list,
                    'target_field': target_field
                }
        
        # Now process only the fields that need to be downloaded
        for media_type, field_data in fields_to_download.items():
            media_list = field_data['media_list']
            target_field = field_data['target_field']
            
            # Get media directory and extensions
            media_dir, extensions = get_media_directory_and_extensions(target_field)
            if not media_dir or not extensions:
                logger.warning(f"No media directory configured for {target_field}")
                continue
            
            # Create full path
            full_media_dir = os.path.join(roms_root, system_name, "media", media_dir)
            os.makedirs(full_media_dir, exist_ok=True)
            
            # Select best media (for grids, use highest score)
            if media_type == 'grids' and media_list:
                # Sort by score descending and take the first one
                best_media = max(media_list, key=lambda x: x.get('score', 0))
            else:
                # For other types, just take the first one
                best_media = media_list[0] if media_list else None
            
            if not best_media:
                continue
            
            # Get image URL
            image_url = best_media.get('url')
            if not image_url:
                logger.warning(f"No URL found for {media_type} media")
                continue
            
            logger.debug(f"Selected {media_type} media: {best_media}")
            
            # Download the image
            try:
                downloaded_path = await self._download_steamgrid_image(
                    image_url, game_name, full_media_dir, target_field, extensions
                )
                
                if downloaded_path:
                    relative_path = os.path.join('.', 'media', media_dir, os.path.basename(downloaded_path))
                    results[target_field] = relative_path
                    logger.debug(f"Downloaded {media_type} for {game_name}: {relative_path}")
                
            except Exception as e:
                logger.error(f"Error downloading {media_type} image for {game_name}: {e}")
        
        logger.debug(f"Downloaded SteamGridDB media for {game_name}: {results}")
        return results
    
    async def _download_steamgrid_image(self, image_url: str, game_name: str, 
                                      media_dir: str, target_field: str, 
                                      extensions: List[str]) -> Optional[str]:
        """Download a single image from SteamGridDB"""
        try:
            # Generate safe filename
            safe_filename = re.sub(r'[<>:"/\\|?*]', '_', game_name)
            safe_filename = safe_filename.strip()
            
            # Determine file extension from URL
            if image_url.lower().endswith('.png'):
                ext = '.png'
            elif image_url.lower().endswith('.jpg') or image_url.lower().endswith('.jpeg'):
                ext = '.jpg'
            else:
                ext = '.png'  # Default to PNG
            
            filename = f"{safe_filename}{ext}"
            file_path = os.path.join(media_dir, filename)
            
            # Download image
            async with httpx.AsyncClient(timeout=30.0) as client:
                logger.debug(f"Downloading image from {image_url}")
                response = await client.get(image_url)
                response.raise_for_status()
                
                # Write file
                with open(file_path, 'wb') as f:
                    f.write(response.content)
                
                # Convert image if needed
                should_convert, target_extension = should_convert_field(target_field, {})
                if should_convert and needs_conversion(file_path, target_extension):
                    new_path, status = convert_image_replace(file_path, target_extension)
                    if status == "converted":
                        file_path = new_path
                
                return file_path
                
        except Exception as e:
            logger.error(f"Error downloading image from {image_url}: {e}")
            return None


    async def download_steamgrid_media_batch(self, games_data: List[Dict], 
                                           roms_root: str, system_name: str,
                                           selected_fields: List[str] = None,
                                           image_type_mappings: Dict[str, str] = None,
                                           max_concurrent: int = 10,
                                           progress_callback=None,
                                           overwrite_media_fields: bool = False,
                                           gamelist_path: str = None,
                                           api_key: str = None,
                                           cancellation_event=None) -> Dict[str, Dict[str, str]]:
        """Download SteamGridDB media for multiple games in parallel"""
        if not games_data:
            return {}
        
        if not image_type_mappings:
            image_type_mappings = {
                'grids': 'boxart',
                'logos': 'marquee', 
                'heroes': 'fanart'
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
                    logger.info(f"🔧 DEBUG: SteamGridDB batch processing cancelled at batch {i//max_concurrent + 1}")
                    break
                
                batch = games_data[i:i + max_concurrent]
                logger.info(f"🔧 DEBUG: Processing SteamGridDB batch {i//max_concurrent + 1} with {len(batch)} games")
                
                # Create tasks for this batch
                batch_tasks = []
                for game_data in batch:
                    steamgrid_id = game_data.get('steamgrid_id')
                    game_name = game_data.get('name', 'Unknown')
                    
                    if steamgrid_id:
                        batch_tasks.append(self.download_steamgrid_media(
                            steamgrid_id, game_name, roms_root, system_name,
                            selected_fields, image_type_mappings, api_key, overwrite_media_fields, gamelist_path
                        ))
                    else:
                        logger.warning(f"🔧 DEBUG: No SteamGridDB ID for game: {game_name}")
                        batch_tasks.append(asyncio.create_task(asyncio.sleep(0)))  # Dummy task
                
                # Execute batch in parallel
                if batch_tasks:
                    logger.info(f"🔧 DEBUG: Executing {len(batch_tasks)} parallel SteamGridDB download tasks")
                    batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
                    
                    # Process batch results
                    for j, result in enumerate(batch_results):
                        if j < len(batch):
                            game_name = batch[j].get('name', f'Game_{j}')
                            
                            if isinstance(result, Exception):
                                logger.error(f"🔧 DEBUG: Error in SteamGridDB batch task {j}: {result}")
                                # Call progress callback even for errors
                                if progress_callback:
                                    progress_callback(game_name, {})
                            elif result:
                                results[game_name] = result
                                logger.info(f"🔧 DEBUG: Successfully processed SteamGridDB media for {game_name}")
                                
                                # Call progress callback for each completed game
                                if progress_callback:
                                    progress_callback(game_name, result)
                            else:
                                # No media downloaded, but still call progress callback
                                logger.info(f"🔧 DEBUG: No media downloaded for {game_name}")
                                if progress_callback:
                                    progress_callback(game_name, {})
                
                # Small delay between batches to be respectful to the server
                if i + max_concurrent < len(games_data):
                    await asyncio.sleep(0.1)
        
        return results


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
