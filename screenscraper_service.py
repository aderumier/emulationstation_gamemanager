import asyncio
import httpx
import json
import os
import logging
from typing import Dict, List, Optional, Tuple
from pathlib import Path

class ScreenScraperService:
    def __init__(self, config: Dict, credentials: Dict):
        self.config = config
        self.credentials = credentials
        self.logger = logging.getLogger(__name__)
        self.api_url = config.get('api_url', 'https://api.screenscraper.fr/api2/jeuInfos.php')
        self.max_connections = config.get('max_connections', 2)
        self.timeout = config.get('timeout', 30)
        self.retry_attempts = config.get('retry_attempts', 3)
        
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
    
    async def search_game(self, rom_filename: str, system_name: str) -> Optional[str]:
        """
        Search for a game using ScreenScraper API and return the jeuId if found.
        
        Args:
            rom_filename: The ROM filename (without path)
            system_name: The system name
            
        Returns:
            The jeuId if found, None otherwise
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
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
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
                                jeu_id = jeu[0].get('id')
                                print(f"List jeu[0]: {jeu[0]}")
                                print(f"Extracted jeu_id: {jeu_id}")
                                if jeu_id:
                                    print(f"Found ScreenScraper ID {jeu_id} for '{rom_name}'")
                                    return str(jeu_id)
                            elif isinstance(jeu, dict) and 'id' in jeu:
                                jeu_id = jeu['id']
                                print(f"Dict jeu: {jeu}")
                                print(f"Extracted jeu_id: {jeu_id}")
                                if jeu_id:
                                    print(f"Found ScreenScraper ID {jeu_id} for '{rom_name}'")
                                    return str(jeu_id)
                        
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
    
    async def process_games_batch(self, games: List[Dict], system_name: str, progress_callback=None) -> Dict[str, str]:
        """
        Process a batch of games to find their ScreenScraper IDs.
        
        Args:
            games: List of game dictionaries
            system_name: The system name for ScreenScraper system ID resolution
            progress_callback: Optional callback for progress updates
            
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
                print(f"Processing game: {game}")
                print(f"Game type: {type(game)}")
                
                if not isinstance(game, dict):
                    print(f"Error: game is not a dictionary, it's {type(game)}: {game}")
                    return None
                
                rom_filename = os.path.basename(game.get('path', ''))
                print(f"ROM filename: {rom_filename}")
                if not rom_filename:
                    print("No ROM filename found")
                    return None
                
                jeu_id = await self.search_game(rom_filename, system_name)
                if jeu_id:
                    results[game['path']] = jeu_id
                    print(f"Found ScreenScraper ID {jeu_id} for {rom_filename}")
                
                if progress_callback:
                    progress_callback(len(results), total_games)
                
                return jeu_id
        
        # Process all games concurrently
        tasks = [process_single_game(game) for game in games]
        results_list = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Log any exceptions
        for i, result in enumerate(results_list):
            if isinstance(result, Exception):
                print(f"Error processing game {i}: {result}")
                print(f"Game was: {games[i] if i < len(games) else 'Unknown'}")
        
        return results
