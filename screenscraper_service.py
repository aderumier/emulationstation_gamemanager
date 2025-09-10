import asyncio
import httpx
import json
import os
import logging
import aiofiles
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from urllib.parse import urlparse

# Global httpx client for ScreenScraper API
_screenscraper_async_client = None

async def get_screenscraper_async_client(max_connections: int = 2):
    """Get or create global httpx async client for ScreenScraper API with connection pooling"""
    global _screenscraper_async_client
    if _screenscraper_async_client is None:
        # Create async client with HTTP/2 and connection pooling
        _screenscraper_async_client = httpx.AsyncClient(
            http2=True,  # Enable HTTP/2 for better performance
            limits=httpx.Limits(
                max_connections=max_connections,           # Maximum connections from config
                max_keepalive_connections=max_connections, # Keep connections alive
                keepalive_expiry=30.0                      # Keep connections alive for 30 seconds
            ),
            timeout=httpx.Timeout(
                connect=10.0,  # 10 seconds to establish connection
                read=30.0,     # 30 seconds to read response
                write=10.0,    # 10 seconds to write request
                pool=5.0       # 5 seconds to get connection from pool
            )
        )
    
    return _screenscraper_async_client

async def close_screenscraper_async_client():
    """Close the global httpx async client"""
    global _screenscraper_async_client
    if _screenscraper_async_client is not None:
        await _screenscraper_async_client.aclose()
        _screenscraper_async_client = None

class ScreenScraperService:
    def __init__(self, config: Dict, credentials: Dict):
        self.config = config
        self.credentials = credentials
        self.logger = logging.getLogger(__name__)
        # Static ScreenScraper configuration
        self.api_url = 'https://api.screenscraper.fr/api2/jeuInfos.php'
        self.max_connections = 2
        self.timeout = 30
        self.retry_attempts = 3
        
        # Extract credentials
        self.devid = credentials.get('devid', '')
        self.devpassword = credentials.get('devpassword', '')
        self.ssid = credentials.get('ssid', '')
        self.sspassword = credentials.get('sspassword', '')
        
        if not all([self.devid, self.devpassword, self.ssid, self.sspassword]):
            self.logger.warning("ScreenScraper credentials not fully configured")
    
    def get_system_id(self, system_name: str) -> Optional[str]:
        """
        Get ScreenScraper system ID for a given system name.
        
        Args:
            system_name: The system name (e.g., 'vectrex', 'megadrive')
            
        Returns:
            The ScreenScraper system ID if found, None otherwise
        """
        print(f"Looking up system ID for: '{system_name}' (type: {type(system_name)})")
        print(f"System name repr: {repr(system_name)}")
        
        # Debug: Check what's in the config
        print(f"Config keys: {list(self.config.keys())}")
        print(f"Config has 'systems': {'systems' in self.config}")
        
        # Get the ScreenScraper system name from the main systems config
        main_systems_config = self.config.get('systems', {})
        print(f"Main systems available: {list(main_systems_config.keys())}")
        print(f"Looking for exact match: '{system_name}' in {list(main_systems_config.keys())}")
        print(f"Exact match found: {system_name in main_systems_config}")
        
        # Check if we're getting the right section
        if 'vectrex' in main_systems_config:
            print("Found vectrex in main systems config")
        else:
            print("vectrex NOT found in main systems config")
            # Try to find it in the config structure
            for key, value in self.config.items():
                if isinstance(value, dict) and 'vectrex' in value:
                    print(f"Found vectrex in config section: {key}")
                    print(f"Vectrex config: {value.get('vectrex', {})}")
        
        system_config = main_systems_config.get(system_name, {})
        print(f"System config for '{system_name}': {system_config}")
        
        screenscraper_system_name = system_config.get('screenscraper')
        print(f"ScreenScraper system name: '{screenscraper_system_name}'")
        
        if not screenscraper_system_name:
            print(f"No ScreenScraper system name configured for {system_name}")
            return None
        
        # Get the ScreenScraper system ID from static mapping
        screenscraper_config = self.config.get('screenscraper', {})
        screenscraper_systems_mapping = screenscraper_config.get('systems', {})
        print(f"ScreenScraper systems mapping keys: {list(screenscraper_systems_mapping.keys())}")
        system_id = screenscraper_systems_mapping.get(screenscraper_system_name)
        
        if system_id:
            print(f"Found ScreenScraper system ID {system_id} for {system_name} -> {screenscraper_system_name}")
            return system_id
        
        print(f"No ScreenScraper system ID found for {system_name} -> {screenscraper_system_name}")
        return None
    
    async def search_game(self, rom_filename: str, system_name: str) -> Optional[Dict]:
        """
        Search for a game using ScreenScraper API and return game data if found.
        
        Args:
            rom_filename: The ROM filename (without path)
            system_name: The system name
            
        Returns:
            Dictionary with 'jeu_id' and 'game_data' if found, None otherwise
        """
        print(f"Searching ScreenScraper for ROM: {rom_filename}, System: {system_name}")
        
        if not all([self.devid, self.devpassword, self.ssid, self.sspassword]):
            print("ScreenScraper credentials not configured")
            return None
        
        # Get ScreenScraper system ID
        systemeid = self.get_system_id(system_name)
        if not systemeid:
            print(f"No ScreenScraper system ID found for {system_name}")
            return None
        
        # Remove file extension for search
        rom_name = os.path.splitext(rom_filename)[0]
        
        params = {
            'devid': self.devid,
            'devpassword': self.devpassword,
            'ssid': self.ssid,
            'sspassword': self.sspassword,
            'romnom': rom_name,
            'systemeid': systemeid,
            'output': 'json'
        }
        
        # Get the global connection pool client
        client = await get_screenscraper_async_client(self.max_connections)
        
        for attempt in range(self.retry_attempts):
            try:
                print(f"Searching ScreenScraper for '{rom_name}' (attempt {attempt + 1})")
                print(f"API URL: {self.api_url}")
                print(f"Params: {params}")
                response = await client.get(self.api_url, params=params)
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"API response: {data}")
                    
                    if 'response' in data and 'jeu' in data['response']:
                        jeu = data['response']['jeu']
                        print(f"Jeu data type: {type(jeu)}")
                        print(f"Jeu data: {jeu}")
                        
                        if isinstance(jeu, list) and len(jeu) > 0:
                            # Take the first result
                            jeu_data = jeu[0]
                            jeu_id = jeu_data.get('id')
                            print(f"List jeu[0]: {jeu_data}")
                            print(f"Extracted jeu_id: {jeu_id}")
                            if jeu_id:
                                print(f"Found ScreenScraper ID {jeu_id} for '{rom_name}'")
                                return {'jeu_id': str(jeu_id), 'game_data': jeu_data}
                        elif isinstance(jeu, dict) and 'id' in jeu:
                            jeu_id = jeu['id']
                            print(f"Dict jeu: {jeu}")
                            print(f"Extracted jeu_id: {jeu_id}")
                            if jeu_id:
                                print(f"Found ScreenScraper ID {jeu_id} for '{rom_name}'")
                                return {'jeu_id': str(jeu_id), 'game_data': jeu}
                        
                        print(f"No ScreenScraper ID found for '{rom_name}'")
                        print(f"Response structure: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
                        if 'response' in data:
                            print(f"Response keys: {list(data['response'].keys()) if isinstance(data['response'], dict) else 'Response not a dict'}")
                        return None
                    
                    elif response.status_code == 429:
                        # Rate limited, wait before retry
                        wait_time = 2 ** attempt
                        print(f"Rate limited, waiting {wait_time}s before retry")
                        await asyncio.sleep(wait_time)
                        continue
                    
                    else:
                        print(f"ScreenScraper API returned status {response.status_code}")
                        print(f"Response text: {response.text}")
                        return None
                
            except httpx.TimeoutException:
                print(f"Timeout searching ScreenScraper for '{rom_name}' (attempt {attempt + 1})")
                if attempt < self.retry_attempts - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
                return None
            
            except Exception as e:
                print(f"Error searching ScreenScraper for '{rom_name}': {e}")
                print(f"Exception type: {type(e)}")
                import traceback
                traceback.print_exc()
                if attempt < self.retry_attempts - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
                return None
        
        return None
    
    async def process_games_batch(self, games: List[Dict], system_name: str, progress_callback=None, selected_fields: List[str] = None, overwrite_media_fields: bool = False, detailed_progress_callback=None, is_cancelled_callback=None) -> Dict[str, str]:
        """
        Process a batch of games to find their ScreenScraper IDs.
        
        Args:
            games: List of game dictionaries
            system_name: The system name for ScreenScraper system ID resolution
            progress_callback: Optional callback for progress updates
            selected_fields: List of selected fields to process
            overwrite_media_fields: Whether to overwrite existing media fields
            
        Returns:
            Dictionary mapping game paths to ScreenScraper IDs
        """
        print(f"ScreenScraper service processing {len(games)} games for system: {system_name}")
        if games:
            print(f"First game structure: {games[0]}")
        
        results = {}
        total_games = len(games)
        
        # Create semaphore to limit concurrent connections
        semaphore = asyncio.Semaphore(self.max_connections)
        
        async def process_single_game(game):
            async with semaphore:
                # Check for cancellation before processing each game
                if is_cancelled_callback and is_cancelled_callback():
                    print(f"ScreenScraper task was cancelled during game processing")
                    return None
                
                game_name = game.get('name', 'Unknown')
                game_path = game.get('path', 'Unknown path')
                print(f"🎮 Processing game: {game_name} ({game_path})")
                
                # Send detailed progress to task log
                if detailed_progress_callback:
                    detailed_progress_callback(f"Processing game: {game_name}")
                
                if not isinstance(game, dict):
                    print(f"❌ Error: game is not a dictionary, it's {type(game)}: {game}")
                    if detailed_progress_callback:
                        detailed_progress_callback(f"Error: Invalid game data for {game_name}")
                    return None
                
                rom_filename = os.path.basename(game_path)
                print(f"📁 ROM filename: {rom_filename}")
                if not rom_filename:
                    print("❌ No ROM filename found")
                    if detailed_progress_callback:
                        detailed_progress_callback(f"Error: No ROM filename for {game_name}")
                    return None
                
                # Search for game and get full data
                print(f"🔍 Searching ScreenScraper for: {game_name}")
                if detailed_progress_callback:
                    detailed_progress_callback(f"Searching ScreenScraper for: {game_name}")
                
                search_result = await self.search_game(rom_filename, system_name)
                if search_result:
                    jeu_id = search_result['jeu_id']
                    game_data = search_result['game_data']
                    print(f"✅ Found ScreenScraper ID {jeu_id} for {game_name}")
                    if detailed_progress_callback:
                        detailed_progress_callback(f"Found ScreenScraper ID {jeu_id} for {game_name}")
                    
                    # Add path to game data for media processing
                    game_data['path'] = game_path
                    
                    # Create client for media downloads
                    async with httpx.AsyncClient(timeout=30.0) as media_client:
                        # Process media downloads
                        print(f"📥 Starting media downloads for {game_name}...")
                        if detailed_progress_callback:
                            detailed_progress_callback(f"Starting media downloads for {game_name}")
                        
                        downloaded_media = await self.process_media_downloads(game_data, system_name, media_client, selected_fields, overwrite_media_fields, detailed_progress_callback)
                    
                    # Store both jeu_id and downloaded media
                    results[game_path] = {
                        'jeu_id': jeu_id,
                        'downloaded_media': downloaded_media
                    }
                    print(f"✅ Successfully processed {game_name} -> ScreenScraper ID: {jeu_id}")
                    print(f"📁 Downloaded media: {list(downloaded_media.keys())}")
                    if detailed_progress_callback:
                        media_list = list(downloaded_media.keys())
                        if media_list:
                            detailed_progress_callback(f"Downloaded media for {game_name}: {', '.join(media_list)}")
                        else:
                            detailed_progress_callback(f"No media downloaded for {game_name}")
                else:
                    print(f"❌ No ScreenScraper ID found for {game_name}")
                    if detailed_progress_callback:
                        detailed_progress_callback(f"No ScreenScraper ID found for {game_name}")
                    # Store just the jeu_id if no media processing
                    results[game_path] = {
                        'jeu_id': None,
                        'downloaded_media': {}
                    }
                
                if progress_callback:
                    progress_callback(len(results), total_games)
                
                return search_result
        
        # Process all games concurrently
        tasks = [process_single_game(game) for game in games]
        results_list = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Log any exceptions
        for i, result in enumerate(results_list):
            if isinstance(result, Exception):
                print(f"Error processing game {i}: {result}")
                print(f"Game was: {games[i] if i < len(games) else 'Unknown'}")
        
        # Close the connection pool when done
        await close_screenscraper_async_client()
        
        return results
    
    async def download_media(self, media_url: str, file_path: str, client: httpx.AsyncClient, media_type: str = None) -> bool:
        """
        Download a media file from URL to local path.
        
        Args:
            media_url: URL to download from
            file_path: Local path to save the file (without extension)
            client: httpx client for downloading
            media_type: ScreenScraper media type (e.g., 'manuel', 'ss', 'wheel')
            
        Returns:
            True if successful, False otherwise
        """
        try:
            print(f"Downloading media from: {media_url}")
            
            # Download file and get content type first
            async with client.stream('GET', media_url) as response:
                if response.status_code == 200:
                    # Get content type from headers
                    content_type = response.headers.get('content-type', '').lower()
                    print(f"Content-Type: {content_type}")
                    
                    # Determine file extension from content type
                    extension = self.get_extension_from_content_type(content_type)
                    if not extension:
                        # Special case: manual files are always PDF
                        if media_type == 'manuel':
                            extension = '.pdf'
                            print(f"Using PDF extension for manual file")
                        else:
                            # Fallback to URL extension if content type is not recognized
                            extension = os.path.splitext(urlparse(media_url).path)[1] or '.bin'
                            print(f"Using fallback extension from URL: {extension}")
                    
                    # Add extension to file path
                    final_file_path = f"{file_path}{extension}"
                    print(f"Saving to: {final_file_path}")
                    
                    # Ensure directory exists (now that we know the final path)
                    os.makedirs(os.path.dirname(final_file_path), exist_ok=True)
                    print(f"Created directory: {os.path.dirname(final_file_path)}")
                    
                    # Download file
                    async with aiofiles.open(final_file_path, 'wb') as f:
                        async for chunk in response.aiter_bytes():
                            await f.write(chunk)
                    print(f"Successfully downloaded: {final_file_path}")
                    return True
                else:
                    print(f"Failed to download media: HTTP {response.status_code}")
                    return False
                    
        except Exception as e:
            print(f"Error downloading media: {e}")
            return False
    
    def get_extension_from_content_type(self, content_type: str) -> str:
        """
        Get file extension from Content-Type header.
        
        Args:
            content_type: Content-Type header value
            
        Returns:
            File extension (e.g., '.png', '.jpg', '.mp4') or empty string if not recognized
        """
        # Common content type mappings
        content_type_mappings = {
            'image/png': '.png',
            'image/jpeg': '.jpg',
            'image/jpg': '.jpg',
            'image/gif': '.gif',
            'image/bmp': '.bmp',
            'image/tiff': '.tiff',
            'image/webp': '.webp',
            'image/svg+xml': '.svg',
            'video/mp4': '.mp4',
            'video/avi': '.avi',
            'video/mov': '.mov',
            'video/wmv': '.wmv',
            'video/flv': '.flv',
            'video/webm': '.webm',
            'application/pdf': '.pdf',
            'application/zip': '.zip',
            'application/x-rar': '.rar',
            'text/plain': '.txt',
            'application/json': '.json',
            'application/xml': '.xml',
            'text/xml': '.xml',
            'application/octet-stream': '.bin'
        }
        
        # Extract main content type (before semicolon)
        main_type = content_type.split(';')[0].strip()
        return content_type_mappings.get(main_type, '')
    
    def get_media_type_mapping(self, media_type: str) -> Optional[str]:
        """
        Get the local media field name for a ScreenScraper media type.
        
        Args:
            media_type: ScreenScraper media type (e.g., 'wheel', 'box-2D')
            
        Returns:
            Local media field name (e.g., 'marquee', 'extra1') or None if not mapped
        """
        screenscraper_config = self.config.get('screenscraper', {})
        image_mappings = screenscraper_config.get('image_type_mappings', {})
        return image_mappings.get(media_type)
    
    def get_media_directory(self, media_field: str, system_name: str) -> Optional[str]:
        """
        Get the media directory for a given media field and system.
        
        Args:
            media_field: Media field name (e.g., 'marquee', 'boxart')
            system_name: System name (e.g., 'vectrex')
            
        Returns:
            Media directory path or None if not found
        """
        # Get media configuration from main config
        media_config = self.config.get('media', {})
        media_mappings = media_config.get('mappings', {})
        
        # Find the media directory for this field
        if media_field in media_mappings:
            media_dir_name = media_mappings[media_field]
            # Get ROMs root directory from config
            roms_root = self.config.get('roms_root_directory', 'roms')
            # Create full path: roms/{system_name}/media/{media_dir_name}
            full_path = os.path.join(roms_root, system_name, 'media', media_dir_name)
            print(f"Media directory for {media_field}: {full_path}")
            return full_path
        
        print(f"No media directory found for field: {media_field}")
        return None
    
    def get_current_media_field_value(self, game_path: str, field_name: str, system_name: str) -> Optional[str]:
        """
        Get the current value of a media field from gamelist.xml for a specific game.
        
        Args:
            game_path: Path to the game file
            field_name: Name of the media field (e.g., 'screenshot', 'boxart')
            system_name: System name
            
        Returns:
            Current value of the field, or None if not found
        """
        try:
            import xml.etree.ElementTree as ET
            
            # Construct path to gamelist.xml
            gamelist_path = os.path.join('roms', system_name, 'gamelist.xml')
            if not os.path.exists(gamelist_path):
                return None
            
            # Parse the XML
            tree = ET.parse(gamelist_path)
            root = tree.getroot()
            
            # Find the game entry
            for game in root.findall('game'):
                path_elem = game.find('path')
                if path_elem is not None and path_elem.text == game_path:
                    # Found the game, get the media field value
                    field_elem = game.find(field_name)
                    if field_elem is not None and field_elem.text:
                        return field_elem.text.strip()
                    break
            
            return None
            
        except Exception as e:
            print(f"Error reading current media field value: {e}")
            return None
    
    async def process_media_downloads(self, game_data: Dict, system_name: str, client: httpx.AsyncClient, selected_fields: List[str] = None, overwrite_media_fields: bool = False, detailed_progress_callback=None) -> Dict[str, str]:
        """
        Process media downloads for a game.
        
        Args:
            game_data: Game data from ScreenScraper API
            system_name: System name
            client: httpx client for downloading
            selected_fields: List of selected fields to process
            overwrite_media_fields: Whether to overwrite existing media fields
            
        Returns:
            Dictionary mapping media fields to local file paths
        """
        downloaded_media = {}
        
        if 'medias' not in game_data:
            print("No medias found in game data")
            return downloaded_media
        
        medias = game_data['medias']
        if not isinstance(medias, list):
            print("Medias is not a list")
            return downloaded_media
        
        print(f"Processing {len(medias)} media items")
        print(f"Selected fields: {selected_fields}")
        
        # Group medias by type to handle duplicates
        media_by_type = {}
        for media in medias:
            media_type = media.get('type')
            if not media_type:
                continue
                
            if media_type not in media_by_type:
                media_by_type[media_type] = []
            media_by_type[media_type].append(media)
        
        # Process each media type
        for media_type, media_list in media_by_type.items():
            # Get the local media field name
            local_field = self.get_media_type_mapping(media_type)
            if not local_field:
                print(f"⚠️ No mapping found for media type: {media_type}")
                continue
            
            # Check if this field is selected
            if selected_fields and local_field not in selected_fields:
                print(f"⏸️ Skipping {media_type} -> {local_field} (not selected)")
                continue
            
            # Check if we should skip this media field based on overwrite setting
            if not overwrite_media_fields:
                # Get the current game data to check if the field already has a value
                current_value = self.get_current_media_field_value(game_data.get('path', ''), local_field, system_name)
                if current_value and current_value.strip():
                    print(f"⏸️ Skipping {media_type} -> {local_field} (field already has value: {current_value})")
                    continue
            
            # Get the media directory
            media_dir = self.get_media_directory(local_field, system_name)
            if not media_dir:
                print(f"❌ No media directory found for field: {local_field}")
                continue
            
            print(f"📁 Media directory for {local_field}: {media_dir}")
            print(f"📁 Directory exists: {os.path.exists(media_dir)}")
            
            # Use the first media of this type
            media = media_list[0]
            media_url = media.get('url')
            if not media_url:
                print(f"❌ No URL found for media type: {media_type}")
                continue
            
            # Generate filename (without extension - will be determined from content-type)
            rom_name = os.path.splitext(os.path.basename(game_data.get('path', 'unknown')))[0]
            filename_base = rom_name
            file_path_base = os.path.join(media_dir, filename_base)
            
            print(f"🖼️ Downloading {media_type} -> {local_field}...")
            print(f"📁 Base file path: {file_path_base}")
            print(f"🌐 Media URL: {media_url}")
            
            # Send detailed progress to task log
            if detailed_progress_callback:
                detailed_progress_callback(f"Downloading {media_type} -> {local_field}")
            
            # Download the media (extension will be added based on content-type)
            if await self.download_media(media_url, file_path_base, client, media_type):
                # Find the actual downloaded file (with correct extension)
                # We need to check what file was actually created
                actual_file_path = self.find_downloaded_file(file_path_base)
                if actual_file_path:
                    actual_filename = os.path.basename(actual_file_path)
                    # Convert to relative path for gamelist.xml
                    # media_dir is like "roms/vectrex/media/screenshot", so we need to get the relative path from the system root
                    relative_path = os.path.join('.', 'media', os.path.basename(media_dir), actual_filename)
                    downloaded_media[local_field] = relative_path
                    print(f"✅ Downloaded {media_type} -> {local_field}: {relative_path}")
                    if detailed_progress_callback:
                        detailed_progress_callback(f"Downloaded {media_type} -> {local_field}: {relative_path}")
                else:
                    print(f"❌ Could not find downloaded file for {media_type}")
                    if detailed_progress_callback:
                        detailed_progress_callback(f"Could not find downloaded file for {media_type}")
            else:
                print(f"❌ Failed to download {media_type} -> {local_field}")
                if detailed_progress_callback:
                    detailed_progress_callback(f"Failed to download {media_type} -> {local_field}")
        
        return downloaded_media
    
    def find_downloaded_file(self, base_path: str) -> Optional[str]:
        """
        Find the actual downloaded file by looking for files with the base name.
        
        Args:
            base_path: Base file path without extension
            
        Returns:
            Full path to the downloaded file or None if not found
        """
        import glob
        
        # Look for files with the base name and any extension
        pattern = f"{base_path}.*"
        matching_files = glob.glob(pattern)
        
        if matching_files:
            # Return the first match (should be only one)
            return matching_files[0]
        
        return None
