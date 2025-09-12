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
                    if data.get('success') and data.get('data'):
                        steamgrid_id = data['data'].get('id')
                        logger.debug(f"SteamGridDB API response for Steam ID {steam_id}: {data}")
                        return steamgrid_id
                    else:
                        logger.debug(f"No SteamGridDB ID found for Steam ID {steam_id}")
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
            
            base_url = "https://www.steamgriddb.com/api/v2"
            url = f"{base_url}/search/grids/{clean_name}"
            
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
                    logger.debug(f"SteamGridDB search response for '{clean_name}': {data}")
                    
                    if data.get('success') and data.get('data'):
                        games = data['data']
                        if games:
                            # Return the first game's ID
                            steamgrid_id = games[0].get('id')
                            logger.debug(f"Found SteamGridDB ID {steamgrid_id} for '{clean_name}'")
                            return steamgrid_id
                    else:
                        logger.debug(f"No SteamGridDB games found for '{clean_name}'")
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
                    logger.debug(f"SteamGridDB API response for {media_type}: {data}")
                    
                    if data.get('success') and data.get('data'):
                        results[media_type] = data['data']
                        logger.debug(f"Found {len(data['data'])} {media_type} for SteamGridDB ID {steamgrid_id}")
                    else:
                        logger.debug(f"No {media_type} found for SteamGridDB ID {steamgrid_id}")
                        results[media_type] = []
                        
                except Exception as e:
                    logger.error(f"Error fetching {media_type} for SteamGridDB ID {steamgrid_id}: {e}")
                    results[media_type] = []
        
        return results
    
    async def download_steamgrid_media(self, steamgrid_id: int, game_name: str, 
                                     roms_root: str, system_name: str,
                                     selected_fields: List[str] = None,
                                     image_type_mappings: Dict[str, str] = None,
                                     api_key: str = None) -> Dict[str, str]:
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
        
        # Process each media type
        for media_type, media_list in media_data.items():
            if not media_list or media_type not in image_type_mappings:
                continue
            
            # Get the target field name
            target_field = image_type_mappings[media_type]
            
            # Get media directory and extensions
            media_dir, extensions = get_media_directory_and_extensions(target_field)
            if not media_dir or not extensions:
                logger.warning(f"No media directory configured for {target_field}")
                continue
            
            # Create full path
            full_media_dir = os.path.join(roms_root, system_name, media_dir)
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
                    relative_path = os.path.join('.', media_dir, os.path.basename(downloaded_path))
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
                if needs_conversion(target_field):
                    converted_path = convert_image_replace(file_path, target_field)
                    if converted_path:
                        file_path = converted_path
                
                return file_path
                
        except Exception as e:
            logger.error(f"Error downloading image from {image_url}: {e}")
            return None


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
