import asyncio
import httpx
import json
import os
import logging
import re
import aiofiles
import time
import hashlib
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


def extract_text_info_from_game_data(game_data: Dict, rom_filename: str = None, selected_fields: List[str] = None, familles_cache: Dict[str, str] = None) -> Dict[str, str]:
    """
    Extract text information from ScreenScraper game data.
    
    Args:
        game_data: Game data dictionary from ScreenScraper API
        rom_filename: Original ROM filename to preserve parentheses text
        selected_fields: List of selected fields to extract (if None, extract all)
        familles_cache: Dictionary mapping famille ID to nom (for family field extraction)
        
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
            # Use common function to process genres (deduplicate and map)
            try:
                from app import process_screenscraper_genres
                text_info['genre'] = process_screenscraper_genres(genre_names)
            except ImportError:
                # If import fails (circular import), just join genres without processing
                text_info['genre'] = '/'.join(genre_names)
    
    # Extract rating from note.text (ScreenScraper uses 0-20 scale)
    if 'note' in game_data and isinstance(game_data['note'], dict):
        if 'text' in game_data['note']:
            note_text = game_data['note']['text']
            # Normalize rating from 0-20 scale to 0-5 scale
            from app import normalize_rating
            text_info['rating'] = normalize_rating(note_text, 20)
    
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
    
    # Extract family from familles if 'family' is in selected_fields
    if (selected_fields is None or 'family' in selected_fields) and familles_cache is not None:
        # Check for familles structure: familles { familles_id [famille_id] }
        if 'familles' in game_data:
            familles_data = game_data['familles']
            famille_id = None
            
            # Handle different possible structures
            if isinstance(familles_data, dict):
                # Check for familles_id key (which might be a list)
                if 'familles_id' in familles_data:
                    familles_id_value = familles_data['familles_id']
                    if isinstance(familles_id_value, list) and len(familles_id_value) > 0:
                        famille_id = familles_id_value[0]
                    else:
                        famille_id = familles_id_value
                # Check for famille_id key (which might be a list)
                elif 'famille_id' in familles_data:
                    famille_id_value = familles_data['famille_id']
                    if isinstance(famille_id_value, list) and len(famille_id_value) > 0:
                        famille_id = famille_id_value[0]
                    else:
                        famille_id = famille_id_value
            elif isinstance(familles_data, list) and len(familles_data) > 0:
                # If it's a list, get the first item (take first family from array)
                first_item = familles_data[0]
                if isinstance(first_item, dict):
                    # Try famille_id first, then id
                    famille_id = first_item.get('famille_id')
                    if not famille_id:
                        famille_id = first_item.get('id')
                    print(f"🔍 DEBUG: Extracting family from list, first item: {first_item}, extracted id: {famille_id}")
                elif isinstance(first_item, str):
                    famille_id = first_item
            
            # Map famille_id to nom using cache
            if famille_id:
                famille_id_str = str(famille_id)
                if famille_id_str in familles_cache:
                    text_info['family'] = familles_cache[famille_id_str]
                    print(f"📝 Extracted family: {text_info['family']} (from famille_id: {famille_id})")
                else:
                    print(f"⚠️ Famille ID {famille_id} not found in cache")
            else:
                print(f"⚠️ Could not extract famille_id from familles data: {type(familles_data)}")
    
    return text_info


def get_screenscraper_familles(devid: str, devpassword: str, ssid: str = 'test', sspassword: str = 'test', force_refresh: bool = False) -> Dict[str, str]:
    """
    Get ScreenScraper familles mapping (id -> nom) with caching
    
    Args:
        devid: ScreenScraper developer ID
        devpassword: ScreenScraper developer password
        ssid: ScreenScraper user ID (default: 'test')
        sspassword: ScreenScraper user password (default: 'test')
        force_refresh: Force refresh cache even if valid
        
    Returns:
        Dictionary mapping famille ID to nom
    """
    import requests
    import xml.etree.ElementTree as ET
    
    cache_dir = "var/db/screenscraper"
    os.makedirs(cache_dir, exist_ok=True)
    cache_file = os.path.join(cache_dir, "familles.json")
    
    # Check if cache is valid (24 hours)
    if not force_refresh and os.path.exists(cache_file):
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            cache_time = datetime.fromisoformat(cache_data.get('timestamp', ''))
            if datetime.now() - cache_time < timedelta(hours=24):
                print(f"📋 Using cached ScreenScraper familles (count: {len(cache_data.get('familles', {}))})")
                return cache_data.get('familles', {})
        except Exception as e:
            print(f"⚠️ Error reading ScreenScraper familles cache: {e}")
    
    # Check if credentials are provided
    if not devid or not devpassword:
        print("⚠️ ScreenScraper credentials not provided, using expired cache if available")
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                print(f"📋 Using expired cache due to missing credentials (count: {len(cache_data.get('familles', {}))})")
                return cache_data.get('familles', {})
            except Exception as e:
                print(f"⚠️ Error reading expired cache: {e}")
        return {}
    
    try:
        api_url = f"https://api.screenscraper.fr/api2/famillesListe.php?devid={devid}&devpassword={devpassword}&softname=cursorscraper&output=xml&ssid={ssid}&sspassword={sspassword}"
        print(f"🌐 Fetching ScreenScraper familles from API...")
        response = requests.get(api_url, timeout=30)
        response.raise_for_status()
        
        # Parse XML response
        root = ET.fromstring(response.content)
        familles = {}
        
        # Find all famille elements
        for famille in root.findall('.//famille'):
            famille_id_elem = famille.find('id')
            nom_elem = famille.find('nom')
            if famille_id_elem is not None and nom_elem is not None:
                famille_id = famille_id_elem.text
                nom = nom_elem.text
                if famille_id and nom:
                    familles[famille_id] = nom
        
        # Cache the results
        cache_data = {
            'familles': familles,
            'timestamp': datetime.now().isoformat()
        }
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ ScreenScraper familles cached (count: {len(familles)})")
        return familles
        
    except Exception as e:
        print(f"❌ Error fetching ScreenScraper familles: {e}")
        # Try to return cached data even if expired
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                print(f"⚠️ Using expired cache due to API error (count: {len(cache_data.get('familles', {}))})")
                return cache_data.get('familles', {})
            except Exception as e2:
                print(f"⚠️ Error reading expired cache: {e2}")
        return {}


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
            'timestamp': datetime.now().isoformat()
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
    def __init__(self, config: Dict, credentials: Dict, scrappers_config: Dict = None, systems_config: Dict = None, max_connections: int = 2):
        self.config = config
        self.credentials = credentials
        self.scrappers_config = scrappers_config or {}
        self.systems_config = systems_config or {}
        self.logger = logging.getLogger(__name__)
        # Static ScreenScraper configuration
        self.api_url = 'https://api.screenscraper.fr/api2/jeuInfos.php'
        self.max_connections = max_connections  # Dynamic max_connections from user info
        # Use httpx.Timeout for better timeout control (connect, read, write, pool timeouts)
        self.timeout = httpx.Timeout(30.0, connect=10.0)  # 30s total, 10s connect
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
        main_systems_config = self.systems_config
        system_config = main_systems_config.get(system_name, {})
        screenscraper_system_id = system_config.get('screenscraper')
        
        if not screenscraper_system_id:
            print(f"No ScreenScraper system ID found for {system_name}")
            return None
        
        # Convert to string if it's an integer
        if isinstance(screenscraper_system_id, int):
            screenscraper_system_id = str(screenscraper_system_id)
        
        print(f"Found ScreenScraper system ID {screenscraper_system_id} for {system_name}")
        return screenscraper_system_id
    
    async def search_games_by_name(self, game_name: str, system_name: str, limit: int = 10, search_all_systems: bool = False) -> List[Dict]:
        """
        Search for games by name using ScreenScraper API jeuRecherche.php endpoint.
        
        Args:
            game_name: The game name to search for
            system_name: The system name
            limit: Maximum number of results to return
            search_all_systems: If True, search across all systems (no systemeid parameter)
            
        Returns:
            List of dictionaries with game data
        """
        print(f"Searching ScreenScraper for game name: {game_name}, System: {system_name}, All systems: {search_all_systems}")
        
        if not all([self.devid, self.devpassword, self.ssid, self.sspassword]):
            print("ScreenScraper credentials not configured")
            return []
        
        # Get ScreenScraper system ID (only if not searching all systems)
        systemeid = None
        if not search_all_systems:
            systemeid = self.get_system_id(system_name)
            if not systemeid:
                print(f"No ScreenScraper system ID found for {system_name}")
                return []
        
        # Clean the game name by removing text between parentheses (including parentheses)
        import re
        cleaned_game_name = re.sub(r'\s*\([^)]*\)', '', game_name).strip()
        print(f"Original game name: '{game_name}' -> Cleaned: '{cleaned_game_name}'")
        
        # Use the jeuRecherche.php endpoint for searching by game name
        search_api_url = 'https://api.screenscraper.fr/api2/jeuRecherche.php'
        
        params = {
            'devid': self.devid,
            'devpassword': self.devpassword,
            'softname': 'cursorscraper',
            'output': 'json',  # Use JSON for easier parsing
            'ssid': self.ssid,
            'sspassword': self.sspassword,
            'recherche': cleaned_game_name
        }
        
        # Only add systemeid if not searching all systems
        if systemeid:
            params['systemeid'] = systemeid
        
        # Only try once - no retries
        for attempt in range(1):
            try:
                print(f"🔍 Searching ScreenScraper for '{cleaned_game_name}' (attempt {attempt + 1})")
                print(f"🌐 API URL: {search_api_url}")
                
                # Build the full URL for logging with obfuscated credentials
                from urllib.parse import urlencode
                full_url = f"{search_api_url}?{urlencode(params)}"
                obfuscated_url = full_url.replace(f"devid={self.devid}", "devid=***").replace(f"devpassword={self.devpassword}", "devpassword=***").replace(f"ssid={self.ssid}", "ssid=***").replace(f"sspassword={self.sspassword}", "sspassword=***")
                print(f"🔗 Full URL: {obfuscated_url}")
                
                # Use asyncio.wait_for to ensure request times out even if httpx timeout doesn't work
                async def make_request():
                    async with httpx.AsyncClient(http2=True, timeout=self.timeout) as client:
                        return await client.get(search_api_url, params=params)
                
                try:
                    # Wrap with asyncio.wait_for for additional timeout protection (35 seconds total)
                    response = await asyncio.wait_for(make_request(), timeout=35.0)
                except asyncio.TimeoutError:
                    print(f"⏱️ ScreenScraper API request timed out after 35 seconds")
                    return []
                except httpx.TimeoutException as e:
                    print(f"⏱️ ScreenScraper API request timed out: {e}")
                    return []
                
                print(f"📡 ScreenScraper API Response: {response.status_code}")
                
                if response.status_code == 200:
                    # Parse JSON response
                    try:
                        data = response.json()
                    except json.JSONDecodeError as e:
                        print(f"Failed to parse JSON response: {e}")
                        print(f"Response content: {response.text[:500]}...")
                        return []
                    
                    # Check for errors
                    if 'header' in data and 'erreur' in data['header'] and data['header']['erreur']:
                        error_msg = data['header']['erreur']
                        print(f"ScreenScraper API error: {error_msg}")
                        return []
                    
                    # Extract games from response
                    games = []
                    if 'response' in data and 'jeux' in data['response']:
                        jeux = data['response']['jeux']
                        for jeu in jeux:
                            if 'id' in jeu:
                                # Get the game name from noms array (prefer 'wor' region, fallback to first available)
                                game_name = 'Unknown'
                                if 'noms' in jeu and isinstance(jeu['noms'], list) and len(jeu['noms']) > 0:
                                    # Look for 'wor' (world) region first, then use first available
                                    for nom in jeu['noms']:
                                        if nom.get('region') == 'wor':
                                            game_name = nom.get('text', 'Unknown')
                                            break
                                    if game_name == 'Unknown':
                                        game_name = jeu['noms'][0].get('text', 'Unknown')
                                
                                # Get system name (convert to lowercase to match config)
                                system_name_result = system_name.lower()
                                if 'systeme' in jeu and isinstance(jeu['systeme'], dict):
                                    system_name_result = jeu['systeme'].get('text', system_name).lower()
                                
                                # Get publisher
                                publisher = 'Unknown'
                                if 'editeur' in jeu and isinstance(jeu['editeur'], dict):
                                    publisher = jeu['editeur'].get('text', 'Unknown')
                                
                                # Get developer
                                developer = 'Unknown'
                                if 'developpeur' in jeu and isinstance(jeu['developpeur'], dict):
                                    developer = jeu['developpeur'].get('text', 'Unknown')
                                
                                # Get release date (prefer 'wor' region, fallback to first available)
                                release_date = 'Unknown'
                                if 'dates' in jeu and isinstance(jeu['dates'], list) and len(jeu['dates']) > 0:
                                    for date in jeu['dates']:
                                        if date.get('region') == 'wor':
                                            release_date = date.get('text', 'Unknown')
                                            break
                                    if release_date == 'Unknown':
                                        release_date = jeu['dates'][0].get('text', 'Unknown')
                                
                                # Get genre (first primary genre)
                                genre = 'Unknown'
                                if 'genres' in jeu and isinstance(jeu['genres'], list) and len(jeu['genres']) > 0:
                                    for g in jeu['genres']:
                                        if g.get('principale') == '1' and 'noms' in g and isinstance(g['noms'], list) and len(g['noms']) > 0:
                                            # Look for English name first, then use first available
                                            for genre_nom in g['noms']:
                                                if genre_nom.get('langue') == 'en':
                                                    genre = genre_nom.get('text', 'Unknown')
                                                    break
                                            if genre == 'Unknown':
                                                genre = g['noms'][0].get('text', 'Unknown')
                                            break
                                
                                # Get description (prefer English, fallback to first available)
                                description = 'ScreenScraper game'
                                if 'synopsis' in jeu and isinstance(jeu['synopsis'], list) and len(jeu['synopsis']) > 0:
                                    for synopsis in jeu['synopsis']:
                                        if synopsis.get('langue') == 'en':
                                            description = synopsis.get('text', 'ScreenScraper game')
                                            break
                                    if description == 'ScreenScraper game':
                                        description = jeu['synopsis'][0].get('text', 'ScreenScraper game')
                                
                                # Get players
                                players = 'Unknown'
                                if 'joueurs' in jeu and isinstance(jeu['joueurs'], dict):
                                    players = jeu['joueurs'].get('text', 'Unknown')
                                
                                # Get rating
                                rating = 'Unknown'
                                if 'note' in jeu and isinstance(jeu['note'], dict):
                                    rating = jeu['note'].get('text', 'Unknown')
                                
                                # Get box-2D image URL (prefer 'wor' region, fallback to first available)
                                box_image = None
                                if 'medias' in jeu and isinstance(jeu['medias'], list):
                                    # First pass: look for 'wor' region
                                    for media in jeu['medias']:
                                        if media.get('type') == 'box-2D' and media.get('region') == 'wor':
                                            box_image = media.get('url')
                                            break
                                    
                                    # Second pass: if no 'wor' region found, take first available
                                    if not box_image:
                                        for media in jeu['medias']:
                                            if media.get('type') == 'box-2D':
                                                box_image = media.get('url')
                                                break
                                
                                game_data = {
                                    'jeu_id': str(jeu['id']),
                                    'name': game_name,
                                    'system': system_name_result,
                                    'description': description,
                                    'region': 'Unknown',
                                    'developer': developer,
                                    'publisher': publisher,
                                    'release_date': release_date,
                                    'genre': genre,
                                    'players': players,
                                    'rating': rating,
                                    'box_image': box_image
                                }
                                games.append(game_data)
                    
                    # Limit results
                    result = games[:limit]
                    print(f"Found {len(result)} ScreenScraper games for '{cleaned_game_name}'")
                    return result
                    
                elif response.status_code == 429:
                    print(f"Rate limited by ScreenScraper API (attempt {attempt + 1})")
                    if attempt < self.retry_attempts - 1:
                        wait_time = (2 ** attempt) * 2  # Exponential backoff
                        print(f"Waiting {wait_time} seconds before retry...")
                        await asyncio.sleep(wait_time)
                        continue
                else:
                    print(f"ScreenScraper API returned status {response.status_code}")
                    print(f"Response content: {response.text[:500]}...")  # Log first 500 chars of response
                    return []
                        
            except Exception as e:
                print(f"Error searching ScreenScraper games: {e}")
                print(f"Exception type: {type(e)}")
                import traceback
                traceback.print_exc()
                return []
        
        print(f"Failed to search ScreenScraper games after 1 attempt")
        return []
    
    def compute_rom_md5(self, rom_path: str) -> Optional[str]:
        """
        Compute MD5 hash of a ROM file.
        
        Args:
            rom_path: Full path to the ROM file
            
        Returns:
            MD5 hash as hexadecimal string, or None if file doesn't exist or error occurs
        """
        try:
            if not os.path.exists(rom_path):
                print(f"⚠️ ROM file not found: {rom_path}")
                return None
            
            md5_hash = hashlib.md5()
            with open(rom_path, 'rb') as f:
                # Read file in chunks to handle large files efficiently
                for chunk in iter(lambda: f.read(4096), b''):
                    md5_hash.update(chunk)
            
            md5_hex = md5_hash.hexdigest()
            print(f"🔐 Computed MD5 for {os.path.basename(rom_path)}: {md5_hex}")
            return md5_hex
        except Exception as e:
            print(f"❌ Error computing MD5 for {rom_path}: {e}")
            return None
    
    async def search_game_by_rom_name(self, rom_filename: str, system_name: str, md5: Optional[str] = None) -> Optional[Dict]:
        """
        Search for a game using ScreenScraper API and return game data if found.
        
        Args:
            rom_filename: The ROM filename (without path)
            system_name: The system name
            md5: Optional MD5 hash of the ROM file
            
        Returns:
            Dictionary with 'jeu_id' and 'game_data' if found, None otherwise
        """
        print(f"Searching ScreenScraper for ROM: {rom_filename}, System: {system_name}")
        if md5:
            print(f"Using MD5 hash: {md5}")
        
        if not all([self.devid, self.devpassword, self.ssid, self.sspassword]):
            print("ScreenScraper credentials not configured")
            return None
        
        # Get ScreenScraper system ID
        systemeid = self.get_system_id(system_name)
        if not systemeid:
            print(f"No ScreenScraper system ID found for {system_name}")
            return None
        
        # Use the ROM filename as-is (with extension)
        rom_name = rom_filename
        
        params = {
            'devid': self.devid,
            'devpassword': self.devpassword,
            'ssid': self.ssid,
            'sspassword': self.sspassword,
            'romnom': rom_name,
            'systemeid': systemeid,
            'output': 'json'
        }
        
        # Add MD5 parameter if provided
        if md5:
            params['md5'] = md5
        
        for attempt in range(self.retry_attempts):
            try:
                print(f"🔍 Searching ScreenScraper for '{rom_name}' (attempt {attempt + 1}/{self.retry_attempts})")
                print(f"🌐 API URL: {self.api_url}")
                print(f"⏱️ Timeout: {self.timeout}s")
                
                # Log full URL with obfuscated credentials
                from urllib.parse import urlencode
                full_url = f"{self.api_url}?{urlencode(params)}"
                obfuscated_url = full_url.replace(f"devid={self.devid}", "devid=***").replace(f"devpassword={self.devpassword}", "devpassword=***").replace(f"ssid={self.ssid}", "ssid=***").replace(f"sspassword={self.sspassword}", "sspassword=***")
                print(f"🔗 Full URL: {obfuscated_url}")
                
                import time
                start_time = time.time()
                
                # Use asyncio.wait_for to ensure request times out even if httpx timeout doesn't work
                async def make_request():
                    async with httpx.AsyncClient(http2=True, timeout=self.timeout) as client:
                        return await client.get(self.api_url, params=params)
                
                try:
                    # Wrap with asyncio.wait_for for additional timeout protection (35 seconds total)
                    response = await asyncio.wait_for(make_request(), timeout=35.0)
                except asyncio.TimeoutError:
                    print(f"⏱️ ScreenScraper API request timed out after 35 seconds")
                    return None
                except httpx.TimeoutException as e:
                    print(f"⏱️ ScreenScraper API request timed out: {e}")
                    return None
                
                request_duration = time.time() - start_time
                
                print(f"📡 Response received in {request_duration:.2f}s")
                print(f"📊 Status Code: {response.status_code}")
                print(f"📏 Response Size: {len(response.content)} bytes")
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        print(f"✅ JSON parsed successfully")
                        print(f"📄 Response keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
                        
                        if 'response' in data and 'jeu' in data['response']:
                            jeu = data['response']['jeu']
                            print(f"🎮 Found jeu data: {type(jeu)}")
                            print(f"📝 Jeu data: {jeu}")
                            
                            if isinstance(jeu, list) and len(jeu) > 0:
                                # Take the first result
                                jeu_data = jeu[0]
                                jeu_id = jeu_data.get('id')
                                print(f"📋 List jeu[0]: {jeu_data}")
                                print(f"🎯 Extracted jeu_id: {jeu_id}")
                                if jeu_id:
                                    print(f"✅ Found ScreenScraper ID {jeu_id} for '{rom_name}'")
                                    return {'jeu_id': str(jeu_id), 'game_data': jeu_data}
                            elif isinstance(jeu, dict) and 'id' in jeu:
                                jeu_id = jeu['id']
                                print(f"📋 Dict jeu: {jeu}")
                                print(f"🎯 Extracted jeu_id: {jeu_id}")
                                if jeu_id:
                                    print(f"✅ Found ScreenScraper ID {jeu_id} for '{rom_name}'")
                                    return {'jeu_id': str(jeu_id), 'game_data': jeu}
                            
                            print(f"❌ No ScreenScraper ID found for '{rom_name}'")
                            print(f"📄 Response structure: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
                            if 'response' in data:
                                print(f"📄 Response keys: {list(data['response'].keys()) if isinstance(data['response'], dict) else 'Response not a dict'}")
                            return None
                        else:
                            print(f"❌ No jeu found in response for '{rom_name}'")
                            print(f"📄 Response structure: {data}")
                            return None
                    except Exception as json_error:
                        print(f"❌ JSON parsing failed: {json_error}")
                        print(f"📄 Raw response (first 500 chars): {response.text[:500]}")
                        return None
                
                elif response.status_code == 429:
                    # Rate limited, wait before retry
                    wait_time = 2 ** attempt
                    print(f"🚫 Rate limited by ScreenScraper API (attempt {attempt + 1})")
                    print(f"⏳ Waiting {wait_time}s before retry...")
                    await asyncio.sleep(wait_time)
                    continue
                
                else:
                    print(f"❌ ScreenScraper API returned status {response.status_code}")
                    print(f"📄 Response text (first 500 chars): {response.text[:500]}")
                    
                    # Check for specific error types
                    if response.status_code >= 500:
                        print(f"🔥 Server error from ScreenScraper")
                    elif response.status_code == 404:
                        print(f"🔍 Game not found on ScreenScraper")
                        return None  # Don't retry for 404
                    
                    return None
                    
            except httpx.TimeoutException:
                print(f"⏰ Timeout searching ScreenScraper for '{rom_name}' (attempt {attempt + 1})")
                print(f"⏱️ Request exceeded {self.timeout}s timeout")
                if attempt < self.retry_attempts - 1:
                    wait_time = 2 ** attempt
                    print(f"⏳ Waiting {wait_time}s before retry...")
                    await asyncio.sleep(wait_time)
                    continue
                return None
            
            except Exception as e:
                print(f"❌ Error searching ScreenScraper for '{rom_name}': {e}")
                print(f"🔍 Exception type: {type(e)}")
                import traceback
                traceback.print_exc()
                if attempt < self.retry_attempts - 1:
                    wait_time = 2 ** attempt
                    print(f"⏳ Waiting {wait_time}s before retry...")
                    await asyncio.sleep(wait_time)
                    continue
                return None
        
        return None
    
    async def search_game_by_name_with_exact_match(self, game_name: str, system_name: str) -> Optional[Dict]:
        """
        Search for a game by name using jeuRecherche.php and return the first result with 100% match
        on normalized name without parentheses.
        
        Args:
            game_name: The game name to search for
            system_name: The system name
            
        Returns:
            Dictionary with 'jeu_id' and 'game_data' if exact match found, None otherwise
        """
        from game_utils import normalize_game_name
        
        print(f"🔍 Searching ScreenScraper by name (slow) for: {game_name}, System: {system_name}")
        
        if not all([self.devid, self.devpassword, self.ssid, self.sspassword]):
            print("ScreenScraper credentials not configured")
            return None
        
        # Get ScreenScraper system ID
        systemeid = self.get_system_id(system_name)
        if not systemeid:
            print(f"No ScreenScraper system ID found for {system_name}")
            return None
        
        # Clean the game name by removing text between parentheses (including parentheses)
        import re
        cleaned_game_name = re.sub(r'\s*\([^)]*\)', '', game_name).strip()
        print(f"Original game name: '{game_name}' -> Cleaned: '{cleaned_game_name}'")
        
        # Normalize the cleaned game name for comparison (remove parentheses and articles)
        normalized_search_name = normalize_game_name(cleaned_game_name, remove_paranthesis=True, remove_articles=True)
        print(f"Normalized search name: '{normalized_search_name}'")
        
        # Use the jeuRecherche.php endpoint for searching by game name
        search_api_url = 'https://api.screenscraper.fr/api2/jeuRecherche.php'
        
        params = {
            'devid': self.devid,
            'devpassword': self.devpassword,
            'softname': 'cursorscraper',
            'output': 'json',
            'ssid': self.ssid,
            'sspassword': self.sspassword,
            'recherche': cleaned_game_name,
            'systemeid': systemeid
        }
        
        try:
            print(f"🔍 Searching ScreenScraper for '{cleaned_game_name}' using jeuRecherche.php")
            
            # Use asyncio.wait_for to ensure request times out
            async def make_request():
                async with httpx.AsyncClient(http2=True, timeout=self.timeout) as client:
                    return await client.get(search_api_url, params=params)
            
            try:
                response = await asyncio.wait_for(make_request(), timeout=35.0)
            except asyncio.TimeoutError:
                print(f"⏱️ ScreenScraper API request timed out after 35 seconds")
                return None
            except httpx.TimeoutException as e:
                print(f"⏱️ ScreenScraper API request timed out: {e}")
                return None
            
            print(f"📡 ScreenScraper API Response: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                except json.JSONDecodeError as e:
                    print(f"Failed to parse JSON response: {e}")
                    print(f"Response content: {response.text[:500]}...")
                    return None
                
                # Check for errors
                if 'header' in data and 'erreur' in data['header'] and data['header']['erreur']:
                    error_msg = data['header']['erreur']
                    print(f"ScreenScraper API error: {error_msg}")
                    return None
                
                # Extract games from response
                if 'response' in data and 'jeux' in data['response']:
                    jeux = data['response']['jeux']
                    print(f"Found {len(jeux)} results from jeuRecherche.php")
                    
                    # Search for exact match on normalized name without parentheses
                    for jeu in jeux:
                        if 'id' not in jeu:
                            continue
                        
                        # Get the game name from noms array (prefer 'wor' region, fallback to first available)
                        result_game_name = 'Unknown'
                        if 'noms' in jeu and isinstance(jeu['noms'], list) and len(jeu['noms']) > 0:
                            # Look for 'wor' (world) region first, then use first available
                            for nom in jeu['noms']:
                                if nom.get('region') == 'wor':
                                    result_game_name = nom.get('text', 'Unknown')
                                    break
                            if result_game_name == 'Unknown':
                                result_game_name = jeu['noms'][0].get('text', 'Unknown')
                        
                        # Remove parentheses from result name and normalize
                        cleaned_result_name = re.sub(r'\s*\([^)]*\)', '', result_game_name).strip()
                        normalized_result_name = normalize_game_name(cleaned_result_name, remove_paranthesis=True, remove_articles=True)
                        
                        print(f"  Comparing: '{normalized_search_name}' with '{normalized_result_name}' (from '{result_game_name}')")
                        
                        # Check for 100% match
                        if normalized_search_name == normalized_result_name:
                            jeu_id = str(jeu['id'])
                            print(f"✅ Found 100% match: ID={jeu_id}, Name='{result_game_name}'")
                            
                            # Get full game data using jeuInfos.php
                            game_data = await self.get_game_by_id(jeu_id, system_name)
                            if game_data:
                                return {'jeu_id': jeu_id, 'game_data': game_data}
                            else:
                                # If we can't get full data, return basic structure
                                return {'jeu_id': jeu_id, 'game_data': jeu}
                    
                    print(f"❌ No 100% match found for '{game_name}' (normalized: '{normalized_search_name}')")
                    return None
                else:
                    print(f"❌ No jeux found in response")
                    return None
            else:
                print(f"❌ ScreenScraper API returned status {response.status_code}")
                print(f"📄 Response text (first 500 chars): {response.text[:500]}")
                return None
                
        except Exception as e:
            print(f"❌ Error searching ScreenScraper by name for '{game_name}': {e}")
            import traceback
            traceback.print_exc()
            return None
    
    async def get_game_by_id(self, gameid: str, system_name: str) -> Optional[Dict]:
        """
        Fetch a ScreenScraper game's data directly by its ScreenScraper jeu ID.

        Args:
            gameid: ScreenScraper game ID (gameid)
            system_name: The system name (needed to resolve systemeid and region/media policies)

        Returns:
            The 'game' dictionary from ScreenScraper if found, else None
        """
        if not all([self.devid, self.devpassword, self.ssid, self.sspassword]):
            print("ScreenScraper credentials not configured")
            return None

        # Resolve ScreenScraper system ID from main config
        systemeid = self.get_system_id(system_name)
        if not systemeid:
            print(f"No ScreenScraper system ID found for {system_name}")
            return None

        params = {
            'devid': self.devid,
            'devpassword': self.devpassword,
            'ssid': self.ssid,
            'sspassword': self.sspassword,
            # Use 'gameid' for jeuInfos.php when fetching by ID
            'gameid': str(gameid),
            'systemeid': systemeid,
            'output': 'json'
        }

        for attempt in range(self.retry_attempts):
            try:
                print(f"🔍 Fetching ScreenScraper by ID: {gameid} (attempt {attempt + 1}/{self.retry_attempts})")
                print(f"🌐 API URL: {self.api_url}")
                print(f"⏱️ Timeout: {self.timeout}s")
                
                # Log full URL with obfuscated credentials
                from urllib.parse import urlencode
                full_url = f"{self.api_url}?{urlencode(params)}"
                obfuscated_url = full_url.replace(f"devid={self.devid}", "devid=***").replace(f"devpassword={self.devpassword}", "devpassword=***").replace(f"ssid={self.ssid}", "ssid=***").replace(f"sspassword={self.sspassword}", "sspassword=***")
                print(f"🔗 Full URL: {obfuscated_url}")
                
                import time
                start_time = time.time()
                
                # Use asyncio.wait_for to ensure request times out even if httpx timeout doesn't work
                async def make_request():
                    async with httpx.AsyncClient(http2=True, timeout=self.timeout) as client:
                        return await client.get(self.api_url, params=params)
                
                try:
                    # Wrap with asyncio.wait_for for additional timeout protection (35 seconds total)
                    response = await asyncio.wait_for(make_request(), timeout=35.0)
                except asyncio.TimeoutError:
                    print(f"⏱️ ScreenScraper API request timed out after 35 seconds")
                    return None
                except httpx.TimeoutException as e:
                    print(f"⏱️ ScreenScraper API request timed out: {e}")
                    return None
                
                request_duration = time.time() - start_time
                
                print(f"📡 Response received in {request_duration:.2f}s")
                print(f"📊 Status Code: {response.status_code}")
                print(f"📏 Response Size: {len(response.content)} bytes")
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        print(f"✅ JSON parsed successfully")
                        print(f"📄 ID fetch response: {data}")
                        
                        if 'response' in data and 'jeu' in data['response']:
                            jeu = data['response']['jeu']
                            print(f"🎮 Found jeu data by ID: {type(jeu)}")
                            
                            # API may return a dict or list; normalize to dict
                            if isinstance(jeu, list) and len(jeu) > 0:
                                jeu = jeu[0]
                                print(f"📝 Normalized from list to dict")
                                return jeu
                            if isinstance(jeu, dict):
                                print(f"📝 Already a dict")
                                return jeu
                            print(f"❌ Unexpected jeu format: {type(jeu)}")
                            return None
                        else:
                            print(f"❌ No jeu found in response for ID {gameid}")
                            print(f"📄 Response structure: {data}")
                            return None
                    except Exception as json_error:
                        print(f"❌ JSON parsing failed: {json_error}")
                        print(f"📄 Raw response (first 500 chars): {response.text[:500]}")
                        return None
                        
                elif response.status_code == 429:
                    wait_time = 2 ** attempt
                    print(f"🚫 Rate limited by ScreenScraper API (attempt {attempt + 1})")
                    print(f"⏳ Waiting {wait_time}s before retry...")
                    await asyncio.sleep(wait_time)
                    continue
                    
                else:
                    print(f"❌ ScreenScraper API returned status {response.status_code}")
                    print(f"📄 Response text (first 500 chars): {response.text[:500]}")
                    
                    # Check for specific error types
                    if response.status_code >= 500:
                        print(f"🔥 Server error from ScreenScraper")
                    elif response.status_code == 404:
                        print(f"🔍 Game ID not found on ScreenScraper")
                        return None  # Don't retry for 404
                    
                    return None
                    
            except httpx.TimeoutException:
                print(f"⏰ Timeout fetching ScreenScraper by ID {gameid} (attempt {attempt + 1})")
                print(f"⏱️ Request exceeded {self.timeout}s timeout")
                if attempt < self.retry_attempts - 1:
                    wait_time = 2 ** attempt
                    print(f"⏳ Waiting {wait_time}s before retry...")
                    await asyncio.sleep(wait_time)
                    continue
                return None
            except Exception as e:
                print(f"❌ Error fetching ScreenScraper game by id '{gameid}': {e}")
                print(f"🔍 Exception type: {type(e)}")
                import traceback
                traceback.print_exc()
                if attempt < self.retry_attempts - 1:
                    wait_time = 2 ** attempt
                    print(f"⏳ Waiting {wait_time}s before retry...")
                    await asyncio.sleep(wait_time)
                    continue
                return None

        return None
    
    async def process_games_batch(self, games: List[Dict], system_name: str, progress_callback=None, selected_fields: List[str] = None, overwrite_media_fields: bool = False, detailed_progress_callback=None, is_cancelled_callback=None, search_by_name: bool = False) -> Dict[str, str]:
        """
        Process a batch of games to find their ScreenScraper IDs.
        
        Args:
            games: List of game dictionaries
            system_name: The system name for ScreenScraper system ID resolution
            progress_callback: Optional callback for progress updates
            selected_fields: List of selected fields to process
            overwrite_media_fields: Whether to overwrite existing media fields
            detailed_progress_callback: Optional callback for detailed progress messages
            is_cancelled_callback: Optional callback to check if task is cancelled
            search_by_name: If True, use jeuRecherche.php to search by game name when screenscraperid is empty
            
        Returns:
            Dictionary mapping game paths to ScreenScraper IDs
        """
        print(f"ScreenScraper service processing {len(games)} games for system: {system_name}")
        if games:
            print(f"First game structure: {games[0]}")
        
        # Load familles cache if 'family' is in selected_fields
        familles_cache = None
        if selected_fields and 'family' in selected_fields:
            print(f"📋 Loading ScreenScraper familles cache for family field extraction...")
            familles_cache = get_screenscraper_familles(
                self.devid,
                self.devpassword,
                self.ssid,
                self.sspassword
            )
            if familles_cache:
                print(f"✅ Loaded {len(familles_cache)} familles from cache")
            else:
                print(f"⚠️ No familles cache available")
        
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
                
                # Check if game already has a ScreenScraper ID
                existing_screenscraper_id = game.get('screenscraperid')
                existing_md5 = game.get('md5', '').strip()
                rom_md5 = None
                
                # Compute MD5 only if the md5 field is empty (to store it in gamelist)
                if not existing_md5:
                    # Construct full ROM path
                    # game_path is typically like "./manny.zip" or "./roms/nes/Mega Man (USA).nes" or "roms/nes/Mega Man (USA).nes"
                    # ROM files are stored in roms/<system_name>/ directory
                    if game_path.startswith('./'):
                        # Remove leading ./ to get relative path
                        relative_path = game_path[2:]
                    else:
                        relative_path = game_path
                    
                    # If path doesn't start with 'roms/', it's relative to the system directory
                    if not relative_path.startswith('roms/'):
                        # Path is relative to roms/<system_name>/, e.g., "manny.zip" -> "roms/vsmile/manny.zip"
                        rom_full_path = os.path.join('roms', system_name, relative_path)
                    else:
                        # Path already includes roms/, use as-is
                        rom_full_path = relative_path
                    
                    # Ensure path is absolute
                    if not os.path.isabs(rom_full_path):
                        rom_full_path = os.path.abspath(rom_full_path)
                    
                    # Compute MD5
                    rom_md5 = self.compute_rom_md5(rom_full_path)
                    if rom_md5:
                        # Store MD5 in game dict for later saving to gamelist
                        game['md5'] = rom_md5
                        print(f"💾 Stored MD5 {rom_md5} for {game_name}")
                        if detailed_progress_callback:
                            detailed_progress_callback(f"Computed MD5 for {game_name}")
                else:
                    rom_md5 = existing_md5
                    print(f"♻️ Using existing MD5 {rom_md5} for {game_name}")
                
                if existing_screenscraper_id and str(existing_screenscraper_id).strip() and str(existing_screenscraper_id) != '0':
                    # Use existing ScreenScraper ID directly
                    jeu_id = str(existing_screenscraper_id)
                    print(f"🔄 Using existing ScreenScraper ID {jeu_id} for {game_name}")
                    if detailed_progress_callback:
                        detailed_progress_callback(f"Using existing ScreenScraper ID {jeu_id} for {game_name}")
                    
                    # If no fields are selected, skip processing entirely
                    if not selected_fields:
                        print(f"⚡ No fields selected - skipping processing for existing ScreenScraper ID {jeu_id}")
                        if detailed_progress_callback:
                            detailed_progress_callback(f"No fields selected - skipping processing for {game_name}")
                        
                        # Store only the jeu_id
                        results[game_path] = {
                            'jeu_id': jeu_id,
                            'downloaded_media': {},
                            'text_info': {},
                            'md5': rom_md5 if rom_md5 else None
                        }
                        print(f"✅ ScreenScraper ID found for {game_name}: {jeu_id}")
                        if detailed_progress_callback:
                            detailed_progress_callback(f"ScreenScraper ID found for {game_name}: {jeu_id}")
                        return None
                    
                    # Get game data using jeuInfos.php API (only if fields are selected)
                    game_data = await self.get_game_by_id(jeu_id, system_name)
                    if not game_data:
                        print(f"❌ Failed to get game data for existing ID {jeu_id}")
                        if detailed_progress_callback:
                            detailed_progress_callback(f"Failed to get game data for existing ID {jeu_id}")
                        return None
                    
                    print(f"✅ Retrieved game data for existing ScreenScraper ID {jeu_id}")
                    if detailed_progress_callback:
                        detailed_progress_callback(f"Retrieved game data for existing ScreenScraper ID {jeu_id}")
                    
                    # Create search_result structure for consistency
                    search_result = {
                        'jeu_id': jeu_id,
                        'game_data': game_data
                    }
                else:
                    # Always search for ScreenScraper ID (even if no fields selected)
                    print(f"🔍 Searching ScreenScraper for: {game_name}")
                    if detailed_progress_callback:
                        detailed_progress_callback(f"Searching ScreenScraper for: {game_name}")
                    
                    # Use search by name if enabled, otherwise use ROM filename search
                    if search_by_name:
                        print(f"🔍 Using search by name (slow) for: {game_name}")
                        if detailed_progress_callback:
                            detailed_progress_callback(f"Using search by name (slow) for: {game_name}")
                        search_result = await self.search_game_by_name_with_exact_match(game_name, system_name)
                    else:
                        # Pass MD5 to search function when no screenscraperid exists
                        search_result = await self.search_game_by_rom_name(rom_filename, system_name, md5=rom_md5)
                    if search_result:
                        jeu_id = search_result['jeu_id']
                        game_data = search_result['game_data']
                        print(f"✅ Found ScreenScraper ID {jeu_id} for {game_name}")
                        if detailed_progress_callback:
                            detailed_progress_callback(f"Found ScreenScraper ID {jeu_id} for {game_name}")
                        
                        # If no fields are selected, skip processing and just store the ID
                        if not selected_fields:
                            print(f"⚡ No fields selected - skipping processing for ScreenScraper ID {jeu_id}")
                            if detailed_progress_callback:
                                detailed_progress_callback(f"No fields selected - skipping processing for {game_name}")
                            
                            # Store only the jeu_id
                            results[game_path] = {
                                'jeu_id': jeu_id,
                                'downloaded_media': {},
                                'text_info': {},
                                'md5': rom_md5 if rom_md5 else None
                            }
                            print(f"✅ ScreenScraper ID found for {game_name}: {jeu_id}")
                            if detailed_progress_callback:
                                detailed_progress_callback(f"ScreenScraper ID found for {game_name}: {jeu_id}")
                            return None
                    else:
                        print(f"❌ No ScreenScraper ID found for {game_name}")
                        if detailed_progress_callback:
                            detailed_progress_callback(f"No ScreenScraper ID found for {game_name}")
                        return None
                
                if game_data:
                    
                    # Add path to game data for media processing
                    game_data['path'] = game_path
                    
                    # Extract text information from game data
                    print(f"📝 Extracting text information for {game_name}...")
                    if detailed_progress_callback:
                        detailed_progress_callback(f"Extracting text information for {game_name}")
                    
                    text_info = extract_text_info_from_game_data(game_data, rom_filename, selected_fields, familles_cache)
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
                    
                    # Store jeu_id, downloaded media, text information, and MD5
                    results[game_path] = {
                        'jeu_id': jeu_id,
                        'downloaded_media': downloaded_media,
                        'text_info': text_info,
                        'md5': rom_md5 if rom_md5 else None
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
                        'text_info': {},
                        'md5': rom_md5 if rom_md5 else None
                    }
                
                return search_result
        
        # Process all games concurrently with progress tracking
        completed_count = 0
        
        async def process_single_game_with_progress(game):
            nonlocal completed_count
            result = await process_single_game(game)
            completed_count += 1
            if progress_callback:
                progress_callback(completed_count, total_games)
            return result
        
        tasks = [process_single_game_with_progress(game) for game in games]
        results_list = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Log any exceptions
        for i, result in enumerate(results_list):
            if isinstance(result, Exception):
                print(f"Error processing game {i}: {result}")
                print(f"Game was: {games[i] if i < len(games) else 'Unknown'}")
        
        # Close the connection pool when done
        await close_screenscraper_async_client()
        
        return results
    
    async def download_media(self, media_url: str, file_path: str, client: httpx.AsyncClient, media_type: str = None, media_item: Dict = None) -> bool:
        """
        Download a media file from URL to local path.
        
        Args:
            media_url: URL to download from
            file_path: Local path to save the file (without extension)
            client: httpx client for downloading
            media_type: ScreenScraper media type (e.g., 'manuel', 'ss', 'wheel')
            media_item: Optional media item dict containing metadata like 'format' field
            
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
                    
                    # Try to get extension from Content-Disposition header first
                    extension = None
                    content_disposition = response.headers.get('content-disposition', '')
                    if content_disposition:
                        # Extract filename from Content-Disposition: attachment; filename="Road Blaster-themehb.zip"
                        import re
                        filename_match = re.search(r'filename[^;=\n]*=(([\'"]).*?\2|[^\s;]+)', content_disposition, re.IGNORECASE)
                        if filename_match:
                            filename = filename_match.group(1).strip('"\'')
                            extension = os.path.splitext(filename)[1]
                            if extension:
                                print(f"Using extension from Content-Disposition: {extension}")
                    
                    # If not found, try to get extension from content type
                    if not extension:
                        extension = self.get_extension_from_content_type(content_type)
                        if extension:
                            print(f"Using extension from Content-Type: {extension}")
                    
                    # If still not found, try to use format field from media metadata
                    if not extension and media_item and media_item.get('format'):
                        format_value = media_item.get('format', '').lower()
                        if format_value:
                            extension = f'.{format_value}' if not format_value.startswith('.') else format_value
                            print(f"Using extension from media format field: {extension}")
                    
                    # Special case: manual files are always PDF
                    if not extension and media_type == 'manuel':
                        extension = '.pdf'
                        print(f"Using PDF extension for manual file")
                    
                    # Fallback to URL extension if content type is not recognized
                    if not extension:
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
                    
                    # Check if this is a video file - skip image processing for videos
                    is_video = content_type.startswith('video/') or media_type == 'video'
                    
                    if is_video:
                        print(f"✅ Downloaded video file: {os.path.basename(final_file_path)} (no processing needed for videos)")
                    else:
                        # Convert and/or resize image in a single operation (optimized)
                        # Check the target field name by looking up the mapping
                        local_field = self.get_media_type_mapping(media_type)
                        from game_utils import should_process_field, convert_and_resize_image_replace
                        
                        should_process, target_extension, target_width, target_height = should_process_field(local_field, self.config)
                        
                        if should_process:
                            processed_path, process_status = convert_and_resize_image_replace(
                                final_file_path, target_extension, target_width, target_height
                            )
                            if process_status in ["converted", "resized", "converted_and_resized"]:
                                final_file_path = processed_path
                                print(f"✅ Processed ScreenScraper {media_type}: {process_status} - {os.path.basename(final_file_path)}")
                            elif process_status == "failed":
                                print(f"⚠️ Warning: Failed to process ScreenScraper {media_type}: {os.path.basename(final_file_path)}")
                        else:
                            print(f"✅ No processing needed for ScreenScraper field: {local_field}")
                    
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
    
    # convert_image_to_png function moved to game_utils.py
    
    def get_media_type_mapping(self, media_type: str) -> Optional[str]:
        """
        Get the local media field name for a ScreenScraper media type.
        
        Args:
            media_type: ScreenScraper media type (e.g., 'wheel', 'box-2D')
            
        Returns:
            Local media field name (e.g., 'marquee', 'thumbnail') or None if not mapped
        """
        screenscraper_config = self.scrappers_config.get('screenscraper', {})
        image_mappings = screenscraper_config.get('image_type_mappings', {})
        
        # New structure: image_mappings[gamelist_field] = [list of screenscraper_types]
        for gamelist_field, screenscraper_types in image_mappings.items():
            if media_type in screenscraper_types:
                return gamelist_field
        
        return None
    
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
        media_fields = self.config.get('media_fields', {})
        
        # Find the media directory for this field using new structure
        field_data = media_fields.get(media_field)
        if field_data:
            directory_name = field_data['directory']
            # Get ROMs root directory from config
            roms_root = self.config.get('roms_root_directory', 'roms')
            # Create full path: roms/{system_name}/media/{directory_name}
            full_path = os.path.join(roms_root, system_name, 'media', directory_name)
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
            from lxml import etree as ET
            
            # Construct path to gamelist.xml
            gamelist_path = os.path.join('var', 'gamelists', system_name, 'gamelist.xml')
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
        
        # Get ScreenScraper configuration for priority-based selection
        screenscraper_config = self.scrappers_config.get('screenscraper', {})
        image_type_mappings = screenscraper_config.get('image_type_mappings', {})
        
        # Process each gamelist field in priority order
        for local_field in selected_fields:
            if local_field not in image_type_mappings:
                continue
                
            screenscraper_types = image_type_mappings[local_field]
            if not isinstance(screenscraper_types, list):
                screenscraper_types = [screenscraper_types]
            
            print(f"🔍 Processing field '{local_field}' with types: {screenscraper_types}")
            
            # Try each ScreenScraper type in priority order, stop at first match
            media_found = False
            for media_type in screenscraper_types:
                if media_type not in media_by_type:
                    continue
                    
                media_list = media_by_type[media_type]
                print(f"📋 Found {len(media_list)} media items for type '{media_type}'")
                
                # Process this media type
                media_found = await self.process_media_type_for_field(
                    media_type, media_list, local_field, game_data, system_name, 
                    overwrite_media_fields, downloaded_media, detailed_progress_callback
                )
                
                if media_found:
                    print(f"✅ Successfully processed {media_type} for field {local_field}")
                    break  # Stop at first successful match
                else:
                    print(f"❌ No media processed for type {media_type}")
            
            if not media_found:
                print(f"⚠️ No media found for field '{local_field}' with any of the configured types")
        
        return downloaded_media
    
    async def process_media_type_for_field(self, media_type: str, media_list: List[Dict], local_field: str, 
                                         game_data: Dict, system_name: str, overwrite_media_fields: bool, 
                                         downloaded_media: Dict, detailed_progress_callback=None) -> bool:
        """Process a specific media type for a field"""
        try:
            # Check if we should skip this media field based on overwrite setting
            if not overwrite_media_fields:
                # Get the current game data to check if the field already has a value
                current_value = self.get_current_media_field_value(game_data.get('path', ''), local_field, system_name)
                
                # Skip download if the media field in gamelist is not empty
                if current_value and current_value.strip():
                    print(f"⏸️ Skipping {media_type} -> {local_field} (field already has value: {current_value})")
                    return False
            
            # Get the media directory
            media_dir = self.get_media_directory(local_field, system_name)
            if not media_dir:
                print(f"❌ No media directory found for field: {local_field}")
                return False
            
            print(f"📁 Media directory for {local_field}: {media_dir}")
            print(f"📁 Directory exists: {os.path.exists(media_dir)}")
            
            # Select the best media by region priority
            region_priority = self.scrappers_config.get('screenscraper', {}).get('region_priority', ['World', 'USA', 'Europe', 'Japan'])
            game_filename = os.path.basename(game_data.get('path', ''))
            game_region_priority = get_region_priority_for_game(game_filename, region_priority)
            
            media = select_best_media_by_region(media_list, game_region_priority)
            if not media:
                print(f"❌ No media selected for type: {media_type}")
                return False
            
            # Log the selected media region
            selected_region = media.get('region', 'Unknown')
            print(f"🌍 Selected {media_type} from region: {selected_region}")
            
            media_url = media.get('url')
            if not media_url:
                print(f"❌ No URL found for media type: {media_type}")
                return False
            
            # Generate filename (without extension - will be determined from content-type)
            from app import create_media_filename
            rom_path = game_data.get('path', 'unknown')
            # Get the base filename without extension using the common function
            filename_base = create_media_filename(rom_path, '')  # Empty extension, function handles this correctly
            file_path_base = os.path.join(media_dir, filename_base)
            
            print(f"🖼️ Downloading {media_type} -> {local_field}...")
            print(f"📁 Base file path: {file_path_base}")
            print(f"🌐 Media URL: {media_url}")
            
            # Send detailed progress to task log
            if detailed_progress_callback:
                detailed_progress_callback(f"Downloading {media_type} -> {local_field}")
            
            # Create client for downloading
            import httpx
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Download the media (extension will be added based on content-type, Content-Disposition, or format field)
                if await self.download_media(media_url, file_path_base, client, media_type, media_item=media):
                    # Find the actual downloaded file (with correct extension)
                    actual_file_path = self.find_downloaded_file(file_path_base)
                    if actual_file_path:
                        actual_filename = os.path.basename(actual_file_path)
                        # Convert to relative path for gamelist.xml (forward slashes for EmulationStation)
                        # media_dir is like "roms/vectrex/media/screenshot", so we need to get the relative path from the system root
                        relative_path = f"./media/{os.path.basename(media_dir)}/{actual_filename}".replace('//', '/')
                        downloaded_media[local_field] = relative_path
                        print(f"✅ Downloaded {media_type} -> {local_field}: {relative_path}")
                        if detailed_progress_callback:
                            detailed_progress_callback(f"Downloaded {media_type} -> {local_field}: {relative_path}")
                        return True
                    else:
                        print(f"❌ Could not find downloaded file for {media_type}")
                        if detailed_progress_callback:
                            detailed_progress_callback(f"Could not find downloaded file for {media_type}")
                        return False
                else:
                    print(f"❌ Failed to download {media_type} -> {local_field}")
                    if detailed_progress_callback:
                        detailed_progress_callback(f"Failed to download {media_type} -> {local_field}")
                    return False
                    
        except Exception as e:
            print(f"❌ Error processing {media_type} for field {local_field}: {e}")
            if detailed_progress_callback:
                detailed_progress_callback(f"Error processing {media_type} for field {local_field}: {e}")
            return False
    
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
