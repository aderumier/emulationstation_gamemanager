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
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import logging
from game_utils import normalize_game_name, convert_image_replace, should_convert_field, needs_conversion

logger = logging.getLogger(__name__)

class SteamService:
    """Service for interacting with Steam API and managing app index cache"""
    
    def __init__(self, cache_dir: str = "var/db/steam"):
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
        """Fetch Steam app index from API"""
        try:
            logger.info("Fetching Steam app index from API...")
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(self.steam_api_url)
                response.raise_for_status()
                
                data = response.json()
                apps = data.get('applist', {}).get('apps', [])
                
                logger.info(f"Fetched {len(apps)} Steam apps from API")
                return apps
                
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
            
            # Also store variations (without common words)
            words = normalized_name.split()
            if len(words) > 1:
                # Try without first word (often "the", "a", etc.)
                if words[0].lower() in ['the', 'a', 'an']:
                    variation = ' '.join(words[1:])
                    if variation not in unified_index:
                        unified_index[variation] = []
                    unified_index[variation].append(app)
        
        self._unified_index = unified_index
        logger.info(f"Built unified index with {len(unified_index)} search terms")
        return unified_index
    
    def find_best_match(self, game_name: str, apps: List[Dict]) -> Optional[Dict]:
        """Find the best Steam app match for a game name"""
        if not game_name or not apps:
            return None
        
        # Build unified index if not already built
        unified_index = self._build_unified_index(apps)
        
        # Normalize the search name
        normalized_search = normalize_game_name(game_name)
        
        # Debug logging
        print(f"🔧 DEBUG: Searching for '{game_name}' -> normalized: '{normalized_search}'")
        print(f"🔧 DEBUG: Unified index has {len(unified_index)} entries")
        
        # Try exact match first
        if normalized_search in unified_index:
            candidates = unified_index[normalized_search]
            print(f"🔧 DEBUG: Found exact match with {len(candidates)} candidates")
            if len(candidates) == 1:
                return {
                    'app': candidates[0],
                    'matched_name': candidates[0]['name'],
                    'confidence': 1.0
                }
            elif len(candidates) > 1:
                # Multiple exact matches, return the first one
                return {
                    'app': candidates[0],
                    'matched_name': candidates[0]['name'],
                    'confidence': 0.9
                }
        
        # Try partial matches
        best_match = None
        best_score = 0.0
        partial_matches = []
        
        for index_name, candidates in unified_index.items():
            if normalized_search in index_name or index_name in normalized_search:
                # Calculate similarity score
                score = len(set(normalized_search.split()) & set(index_name.split())) / max(len(normalized_search.split()), len(index_name.split()))
                partial_matches.append((index_name, score, candidates[0]['name']))
                
                if score > best_score and score > 0.3:  # Minimum threshold
                    best_match = candidates[0]  # Take first candidate
                    best_score = score
        
        # Debug logging for partial matches
        if partial_matches:
            print(f"🔧 DEBUG: Found {len(partial_matches)} partial matches:")
            for match_name, score, app_name in sorted(partial_matches, key=lambda x: x[1], reverse=True)[:5]:  # Top 5
                print(f"🔧 DEBUG:   '{match_name}' -> '{app_name}' (score: {score:.2f})")
        else:
            print(f"🔧 DEBUG: No partial matches found")
        
        if best_match:
            print(f"🔧 DEBUG: Best match: '{best_match['name']}' (score: {best_score:.2f})")
            return {
                'app': best_match,
                'matched_name': best_match['name'],
                'confidence': best_score
            }
        
        print(f"🔧 DEBUG: No match found for '{game_name}'")
        return None
    
    async def download_steam_media(self, steam_id: int, game_name: str, 
                                 roms_root: str, system_name: str,
                                 selected_fields: List[str] = None,
                                 image_type_mappings: Dict[str, str] = None,
                                 cancellation_event=None) -> Dict[str, str]:
        """Download media from Steam CDN"""
        if not steam_id or not game_name:
            return {}
        
        if not image_type_mappings:
            image_type_mappings = {
                'capsule': 'boxart',
                'logo': 'marquee', 
                'hero': 'fanart'
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
            'logo': f"https://shared.steamstatic.com/store_item_assets/steam/apps/{steam_id}/logo_2x.png",
            'hero': f"https://shared.steamstatic.com/store_item_assets/steam/apps/{steam_id}/library_hero.jpg"
        }
        
        logger.info(f"🔧 DEBUG: Steam URLs for {game_name} (Steam ID: {steam_id}):")
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
            for media_type in selected_fields:
                # Check for cancellation before each download task
                if cancellation_event and cancellation_event.is_set():
                    logger.info(f"🔧 DEBUG: Steam media download cancelled for {game_name} at {media_type}")
                    return results
                
                if media_type not in steam_urls:
                    continue
                
                url = steam_urls[media_type]
                target_field = image_type_mappings.get(media_type, media_type)
                download_tasks.append(self._download_single_media(
                    client, url, media_type, target_field, game_name, 
                    steam_id, roms_root, system_name, cancellation_event
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
                                       cancellation_event=None) -> Dict[str, Dict[str, str]]:
        """Download Steam media for multiple games in parallel"""
        if not games_data:
            return {}
        
        if not image_type_mappings:
            image_type_mappings = {
                'capsule': 'boxart',
                'logo': 'marquee', 
                'hero': 'fanart'
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
                    
                    if steam_id:
                        batch_tasks.append(self.download_steam_media(
                            steam_id, game_name, roms_root, system_name,
                            selected_fields, image_type_mappings
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
                            
                            if isinstance(result, Exception):
                                logger.error(f"🔧 DEBUG: Error in batch task {j}: {result}")
                                # Call progress callback even for errors
                                if progress_callback:
                                    progress_callback(game_name, {})
                            elif result:
                                results[game_name] = result
                                logger.info(f"🔧 DEBUG: Successfully processed Steam media for {game_name}")
                                
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
    
    async def _download_single_media(self, client: httpx.AsyncClient, url: str, 
                                   media_type: str, target_field: str, 
                                   game_name: str, steam_id: int, 
                                   roms_root: str, system_name: str,
                                   cancellation_event=None) -> Optional[Dict[str, str]]:
        """Download a single media file"""
        try:
            # Check for cancellation before starting download
            if cancellation_event and cancellation_event.is_set():
                logger.info(f"🔧 DEBUG: Steam {media_type} download cancelled for {game_name}")
                return None
            
            print(f"🔧 DEBUG: Downloading Steam {media_type} for {game_name}: {url}")
            logger.info(f"🔧 DEBUG: Downloading Steam {media_type} for {game_name}: {url}")
            

            response = await client.get(url)
            
            
            if response.status_code == 200:
                content_length = len(response.content)
                print(f"🔧 DEBUG: Successfully downloaded {content_length} bytes from {url}")
                logger.info(f"🔧 DEBUG: Successfully downloaded {content_length} bytes from {url}")
                
                # Get media directory and extensions
                media_dir, extensions = get_media_directory_and_extensions(target_field)
                if not media_dir or not extensions:
                    logger.warning(f"No media directory configured for {target_field}")
                    return None
                
                # Create full path
                full_media_dir = os.path.join(roms_root, system_name, "media", media_dir)
                os.makedirs(full_media_dir, exist_ok=True)
                
                # Generate filename
                safe_filename = re.sub(r'[<>:"/\\|?*]', '_', game_name)
                safe_filename = safe_filename.strip()
                
                # Determine file extension from content type
                content_type = response.headers.get('content-type', '')
                if 'jpeg' in content_type or 'jpg' in content_type:
                    ext = '.jpg'
                elif 'png' in content_type:
                    ext = '.png'
                else:
                    ext = '.jpg'  # Default to jpg for Steam images
                
                filename = f"{safe_filename}{ext}"
                file_path = os.path.join(full_media_dir, filename)
                
                # Write file
                with open(file_path, 'wb') as f:
                    f.write(response.content)
                
                # Convert image if needed using config-based target extension
                from game_utils import should_convert_field
                import json
                
                # Load config to get target_extension for this field
                try:
                    with open('var/config/config.json', 'r') as f:
                        config = json.load(f)
                except Exception as e:
                    logger.warning(f"🔧 DEBUG: Failed to load config for image conversion: {e}")
                    config = {}
                
                should_convert, target_extension = should_convert_field(target_field, config)
                
                if should_convert and needs_conversion(file_path, target_extension):
                    converted_path, status = convert_image_replace(file_path, target_extension)
                    if converted_path and status == 'success':
                        file_path = converted_path
                        logger.info(f"🔧 DEBUG: Converted {target_field} to {target_extension}: {file_path}")
                    else:
                        logger.warning(f"🔧 DEBUG: Failed to convert {target_field} to {target_extension}: {status}")
                elif should_convert:
                    logger.info(f"🔧 DEBUG: Already {target_extension} format for {target_field}: {file_path}")
                else:
                    logger.info(f"🔧 DEBUG: No conversion needed for field: {target_field}")
                
                # Store relative path
                relative_path = os.path.join('.', 'media', media_dir, os.path.basename(file_path))
                
                logger.info(f"Downloaded Steam {media_type} for {game_name}: {relative_path}")
                
                return {
                    'target_field': target_field,
                    'relative_path': relative_path
                }
            else:
                print(f"🔧 DEBUG: Failed to download Steam {media_type} for {game_name}: HTTP {response.status_code} - URL: {url}")
                logger.warning(f"🔧 DEBUG: Failed to download Steam {media_type} for {game_name}: HTTP {response.status_code} - URL: {url}")
                return None
                
        except Exception as e:
            print(f"🔧 DEBUG: Error downloading Steam {media_type} for {game_name}: {e} - URL: {url}")
            logger.error(f"🔧 DEBUG: Error downloading Steam {media_type} for {game_name}: {e} - URL: {url}")
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
