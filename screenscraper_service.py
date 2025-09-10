import asyncio
import httpx
import json
import os
import logging
import re
import aiofiles
import time
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from urllib.parse import urlparse
from datetime import datetime, timedelta

# Global httpx client for ScreenScraper API
_screenscraper_async_client = None

# Region mapping for ScreenScraper - based on official API regionsListe.php
# Maps ScreenScraper region codes (nomcourt) to English names (nom_en)
REGION_MAPPING = {
    'za': 'South Africa',
    'de': 'Germany',
    'asi': 'Asia',
    'au': 'Australia',
    'br': 'Brazil',
    'bg': 'Bulgaria',
    'ca': 'Canada',
    'cl': 'Chile',
    'cn': 'China',
    'kr': 'Korea',
    'cus': 'Custom',
    'dk': 'Denmark',
    'ae': 'United Arab Emirates',
    'sp': 'Spain',
    'eu': 'Europe',
    'fi': 'Finland',
    'fr': 'France',
    'gr': 'Greece',
    'hu': 'Hungary',
    'il': 'Israel',
    'it': 'Italy',
    'jp': 'Japan',
    'kw': 'Kuwait',
    'mex': 'Mexico',
    'wor': 'World',
    'mor': 'Middle East',
    'no': 'Norway',
    'nz': 'New Zealand',
    'nl': 'Netherlands',
    'pe': 'Peru',
    'pl': 'Poland',
    'pt': 'Portugal',
    'cz': 'Czech republic',
    'uk': 'United Kingdom',
    'ru': 'Russia',
    'ss': 'ScreenScraper',
    'sk': 'Slovakia',
    'se': 'Sweden',
    'tw': 'Taiwan',
    'tr': 'Turkey',
    'us': 'USA',
    'ame': 'American Continent',
    'oce': 'Oceania',
    'afr': 'African Continent'
}

def extract_country_from_filename(filename: str) -> Optional[str]:
    """Extract country information from ROM filename in parentheses"""
    # Look for country code in parentheses at the end of filename (before extension)
    pattern = r'\(([^)]+)\)\.(?:zip|7z|rar|iso|bin|cue|img|mdf|mds|nrg|gdi|cdi|gcm|wbfs|ciso|wud|wux|nsp|xci|pkg|xvc|xex|xbe|v64|z64|n64|nes|sfc|smc|gb|gbc|gba|gg|sms|md|gen|32x|pce|pcecd|ngp|ngc|ws|wsc|vb|lnx|a26|a52|a78|j64|jag|vec|int|col|o2|dsk|tap|adf|ipf|st|msa|rom|mx1|mx2|d64|t64|prg|stx|dsk|do|po|mgw|zip|ZIP|7z|7Z|rar|RAR|iso|ISO|bin|BIN|cue|CUE|img|IMG|mdf|MDF|mds|MDS|nrg|NRG|gdi|GDI|cdi|CDI|gcm|GCM|wbfs|WBFS|ciso|CISO|wud|WUD|wux|WUX|nsp|NSP|xci|XCI|pkg|PKG|xvc|XVC|xex|XEX|xbe|XBE|v64|V64|z64|Z64|n64|N64|nes|NES|sfc|SFC|smc|SMC|gb|GB|gbc|GBC|gba|GBA|gg|GG|sms|SMS|md|MD|gen|GEN|32x|32X|pce|PCE|pcecd|PCECD|ngp|NGP|ngc|NGC|ws|WS|wsc|WSC|vb|VB|lnx|LNX|a26|A26|a52|A52|a78|A78|j64|J64|jag|JAG|vec|VEC|int|INT|col|COL|o2|O2|dsk|DSK|tap|TAP|adf|ADF|ipf|IPF|st|ST|msa|MSA|rom|ROM|mx1|MX1|mx2|MX2|d64|D64|t64|T64|prg|PRG|stx|STX|dsk|DSK|do|DO|po|PO|mgw|MGW)$'
    
    match = re.search(pattern, filename)
    if match:
        country_code = match.group(1).lower().strip()
        # Map ScreenScraper region code to English name
        return REGION_MAPPING.get(country_code, country_code.title())
    
    return None

def get_region_priority_for_game(filename: str, default_priority: List[str]) -> List[str]:
    """Get region priority list for a specific game based on filename and default priority"""
    country = extract_country_from_filename(filename)
    
    if country:
        # If country found in filename, prioritize it
        priority = [country] + [region for region in default_priority if region != country]
        return priority
    
    return default_priority

def select_best_media_by_region(media_list: List[Dict], region_priority: List[str]) -> Optional[Dict]:
    """Select the best media from a list based on region priority"""
    if not media_list:
        return None
    
    if len(media_list) == 1:
        return media_list[0]
    
    # Try to find media by region priority
    for region in region_priority:
        for media in media_list:
            media_region = media.get('region', '').lower()
            # Map English region names to ScreenScraper region codes
            region_mapping = {
                'world': 'wor',
                'usa': 'us',
                'europe': 'eu',
                'japan': 'jp',
                'france': 'fr',
                'germany': 'de',
                'united kingdom': 'uk',
                'italy': 'it',
                'spain': 'sp',
                'netherlands': 'nl',
                'denmark': 'dk',
                'finland': 'fi',
                'sweden': 'se',
                'norway': 'no',
                'poland': 'pl',
                'portugal': 'pt',
                'czech republic': 'cz',
                'hungary': 'hu',
                'greece': 'gr',
                'bulgaria': 'bg',
                'slovakia': 'sk',
                'china': 'cn',
                'korea': 'kr',
                'taiwan': 'tw',
                'asia': 'asi',
                'canada': 'ca',
                'brazil': 'br',
                'mexico': 'mex',
                'chile': 'cl',
                'peru': 'pe',
                'american continent': 'ame',
                'australia': 'au',
                'new zealand': 'nz',
                'oceania': 'oce',
                'israel': 'il',
                'united arab emirates': 'ae',
                'kuwait': 'kw',
                'turkey': 'tr',
                'middle east': 'mor',
                'south africa': 'za',
                'african continent': 'afr',
                'russia': 'ru',
                'custom': 'cus',
                'screenscraper': 'ss'
            }
            expected_region_code = region_mapping.get(region.lower(), region.lower())
            if media_region == expected_region_code:
                return media
    
    # If no region match found, return the first media
    return media_list[0]


def extract_text_info_from_game_data(game_data: Dict, rom_filename: str = None) -> Dict[str, str]:
    """
    Extract text information from ScreenScraper game data.
    
    Args:
        game_data: Game data dictionary from ScreenScraper API
        rom_filename: Original ROM filename to preserve parentheses text
        
    Returns:
        Dictionary with extracted text information
    """
    text_info = {}
    
    # Extract game name from noms[text] with region='wor', fallback to first available
    if 'noms' in game_data and isinstance(game_data['noms'], list):
        screenscraper_name = None
        
        # First try to find 'wor' region
        for nom in game_data['noms']:
            if isinstance(nom, dict) and nom.get('region') == 'wor' and 'text' in nom:
                screenscraper_name = nom['text']
                break
        
        # If no 'wor' region found, use the first available name
        if not screenscraper_name:
            for nom in game_data['noms']:
                if isinstance(nom, dict) and 'text' in nom:
                    screenscraper_name = nom['text']
                    break
        
        if screenscraper_name:
            # Preserve parentheses text from ROM filename if present
            if rom_filename:
                import re
                # Extract all text in parentheses from ROM filename
                parentheses_matches = re.findall(r'\(([^)]+)\)', rom_filename)
                if parentheses_matches:
                    # Join all parentheses text with spaces
                    parentheses_text = ' '.join(f"({match})" for match in parentheses_matches)
                    # Append parentheses text to ScreenScraper name
                    text_info['name'] = f"{screenscraper_name} {parentheses_text}"
                else:
                    text_info['name'] = screenscraper_name
            else:
                text_info['name'] = screenscraper_name
    
    # Extract publisher from editeur.text
    if 'editeur' in game_data and isinstance(game_data['editeur'], dict):
        if 'text' in game_data['editeur']:
            text_info['publisher'] = game_data['editeur']['text']
    
    # Extract developer from developpeur.text
    if 'developpeur' in game_data and isinstance(game_data['developpeur'], dict):
        if 'text' in game_data['developpeur']:
            text_info['developer'] = game_data['developpeur']['text']
    
    # Extract description from synopsis[text] with langue='en', fallback to first available
    if 'synopsis' in game_data and isinstance(game_data['synopsis'], list):
        description_text = None
        
        # First try to find English synopsis
        for synopsis in game_data['synopsis']:
            if isinstance(synopsis, dict) and synopsis.get('langue') == 'en' and 'text' in synopsis:
                description_text = synopsis['text']
                break
        
        # If no English synopsis found, use the first available
        if not description_text:
            for synopsis in game_data['synopsis']:
                if isinstance(synopsis, dict) and 'text' in synopsis:
                    description_text = synopsis['text']
                    break
        
        if description_text:
            text_info['description'] = description_text
    
    # Extract genres from genres[noms[text]] with langue='en', concatenate with '/'
    if 'genres' in game_data and isinstance(game_data['genres'], list):
        genre_names = []
        for genre in game_data['genres']:
            if isinstance(genre, dict) and 'noms' in genre and isinstance(genre['noms'], list):
                for nom in genre['noms']:
                    if isinstance(nom, dict) and nom.get('langue') == 'en' and 'text' in nom:
                        genre_names.append(nom['text'])
                        break
        if genre_names:
            text_info['genre'] = '/'.join(genre_names)
    
    # Extract players from joueurs.text, handle range values like '1-2'
    if 'joueurs' in game_data and isinstance(game_data['joueurs'], dict):
        if 'text' in game_data['joueurs']:
            players_text = game_data['joueurs']['text']
            # Handle range values like '1-2' by taking the biggest number
            if '-' in players_text:
                try:
                    # Split by '-' and take the maximum value
                    range_parts = players_text.split('-')
                    if len(range_parts) == 2:
                        min_players = int(range_parts[0].strip())
                        max_players = int(range_parts[1].strip())
                        text_info['players'] = str(max_players)
                    else:
                        text_info['players'] = players_text
                except (ValueError, IndexError):
                    # If parsing fails, use the original text
                    text_info['players'] = players_text
            else:
                text_info['players'] = players_text
    
    return text_info


def get_screenscraper_systems(devid: str, devpassword: str, force_refresh: bool = False) -> Dict[int, str]:
    """
    Get ScreenScraper systems mapping (id -> nom_eu) with caching
    
    Args:
        devid: ScreenScraper developer ID
        devpassword: ScreenScraper developer password
        force_refresh: Force refresh cache even if valid
        
    Returns:
        Dictionary mapping ScreenScraper system ID to European name
    """
    import requests
    
    cache_dir = "var/db/screenscraper"
    os.makedirs(cache_dir, exist_ok=True)
    cache_file = os.path.join(cache_dir, "platforms.json")
    
    # Check if cache is valid (24 hours)
    if not force_refresh and os.path.exists(cache_file):
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            cache_time = datetime.fromisoformat(cache_data.get('timestamp', ''))
            if datetime.now() - cache_time < timedelta(hours=24):
                print(f"📋 Using cached ScreenScraper systems (count: {len(cache_data.get('systems', {}))})")
                return cache_data.get('systems', {})
        except Exception as e:
            print(f"⚠️ Error reading ScreenScraper systems cache: {e}")
    
    # Check if credentials are provided
    if not devid or not devpassword:
        print("⚠️ ScreenScraper credentials not provided, using expired cache if available")
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                print(f"📋 Using expired cache due to missing credentials (count: {len(cache_data.get('systems', {}))})")
                return cache_data.get('systems', {})
            except Exception as e:
                print(f"⚠️ Error reading expired cache: {e}")
        return {}
    
    try:
        api_url = f"https://api.screenscraper.fr/api2/systemesListe.php?devid={devid}&devpassword={devpassword}&softname=cursorscraper&output=json&ssid=test&sspassword=test"
        print(f"🌐 Fetching ScreenScraper systems from API...")
        response = requests.get(api_url, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        systems = {}
        
        if 'response' in data and 'systemes' in data['response']:
            for system in data['response']['systemes']:
                system_id = system.get('id')
                nom_eu = system.get('noms', {}).get('nom_eu', '')
                if system_id and nom_eu:
                    systems[system_id] = nom_eu
        
        # Cache the results
        cache_data = {
            'systems': systems,
            'timestamp': datetime.now().isoformat(),
            'raw_response': response.text
        }
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ ScreenScraper systems cached (count: {len(systems)})")
        return systems
        
    except Exception as e:
        print(f"❌ Error fetching ScreenScraper systems: {e}")
        # Try to return cached data even if expired
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                print(f"⚠️ Using expired cache due to API error (count: {len(cache_data.get('systems', {}))})")
                return cache_data.get('systems', {})
            except Exception as e2:
                print(f"⚠️ Error reading expired cache: {e2}")
        return {}

async def get_screenscraper_async_client(max_connections: int = 1):
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
    def __init__(self, config: Dict, credentials: Dict, max_connections: int = 2):
        self.config = config
        self.credentials = credentials
        self.logger = logging.getLogger(__name__)
        # Static ScreenScraper configuration
        self.api_url = 'https://api.screenscraper.fr/api2/jeuInfos.php'
        self.max_connections = max_connections  # Dynamic max_connections from user info
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
        print(f"Looking up system ID for: '{system_name}'")
        
        # Get the ScreenScraper system ID from the main systems config
        main_systems_config = self.config.get('systems', {})
        system_config = main_systems_config.get(system_name, {})
        screenscraper_system_id = system_config.get('screenscraper')
        
        if not screenscraper_system_id:
            print(f"No ScreenScraper system ID configured for {system_name}")
            return None
        
        # Convert to string if it's an integer
        if isinstance(screenscraper_system_id, int):
            screenscraper_system_id = str(screenscraper_system_id)
        
        print(f"Found ScreenScraper system ID {screenscraper_system_id} for {system_name}")
        return screenscraper_system_id
    
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
                    
                    # Extract text information from game data
                    print(f"📝 Extracting text information for {game_name}...")
                    if detailed_progress_callback:
                        detailed_progress_callback(f"Extracting text information for {game_name}")
                    
                    text_info = extract_text_info_from_game_data(game_data, rom_filename)
                    if text_info:
                        print(f"📝 Extracted text info: {text_info}")
                        if detailed_progress_callback:
                            detailed_progress_callback(f"Extracted text info: {', '.join(text_info.keys())}")
                    
                    # Create client for media downloads
                    async with httpx.AsyncClient(timeout=30.0) as media_client:
                        # Process media downloads
                        print(f"📥 Starting media downloads for {game_name}...")
                        if detailed_progress_callback:
                            detailed_progress_callback(f"Starting media downloads for {game_name}")
                        
                        downloaded_media = await self.process_media_downloads(game_data, system_name, media_client, selected_fields, overwrite_media_fields, detailed_progress_callback)
                    
                    # Store jeu_id, downloaded media, and text information
                    results[game_path] = {
                        'jeu_id': jeu_id,
                        'downloaded_media': downloaded_media,
                        'text_info': text_info
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
                        'downloaded_media': {},
                        'text_info': {}
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
            
            # Select the best media by region priority
            region_priority = self.config.get('screenscraper', {}).get('region_priority', ['World', 'USA', 'Europe', 'Japan'])
            game_filename = os.path.basename(game_data.get('path', ''))
            game_region_priority = get_region_priority_for_game(game_filename, region_priority)
            
            media = select_best_media_by_region(media_list, game_region_priority)
            if not media:
                print(f"❌ No media selected for type: {media_type}")
                continue
            
            # Log the selected media region
            selected_region = media.get('region', 'Unknown')
            print(f"🌍 Selected {media_type} from region: {selected_region}")
            
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
