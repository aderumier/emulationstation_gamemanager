#!/usr/bin/env python3
"""
ArcadeDB Scraper
Scrapes game data from ArcadeItalia API by parsing .dat XML files
Creates a JSON database with game information
"""

import requests
import json
import time
import re
import sys
import random
import os
import glob
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Set

class ArcadeDBScraper:
    def __init__(self):
        self.api_base_url = "http://adb.arcadeitalia.net/service_scraper.php"
        self.games_db = {}
        self.session = requests.Session()
        self.dat_directory = os.path.dirname(os.path.abspath(__file__))
        
        # Progress tracking
        self.progress_file = "scraper_progress.json"
        self.db_file = "arcadedb_db.json"
        self.progress_data = {
            "processed_games": set(),
            "processed_files": set(),
            "total_games_collected": 0,
            "last_run_timestamp": None,
            "status": "not_started"  # not_started, running, completed, interrupted
        }
        
        # Realistic browser user agents - comprehensive list with real user agents
        self.user_agents = [
            # Chrome on Windows
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 11.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            
            # Chrome on macOS
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            
            # Chrome on Linux
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
            
            # Firefox on Windows
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:132.0) Gecko/20100101 Firefox/132.0',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:131.0) Gecko/20100101 Firefox/131.0',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:130.0) Gecko/20100101 Firefox/130.0',
            'Mozilla/5.0 (Windows NT 11.0; Win64; x64; rv:132.0) Gecko/20100101 Firefox/132.0',
            
            # Firefox on macOS
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:132.0) Gecko/20100101 Firefox/132.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:131.0) Gecko/20100101 Firefox/131.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 13.6; rv:132.0) Gecko/20100101 Firefox/132.0',
            
            # Firefox on Linux
            'Mozilla/5.0 (X11; Linux x86_64; rv:132.0) Gecko/20100101 Firefox/132.0',
            'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:132.0) Gecko/20100101 Firefox/132.0',
            
            # Safari on macOS
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Safari/605.1.15',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Safari/605.1.15',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Safari/605.1.15',
            
            # Edge on Windows
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0',
            'Mozilla/5.0 (Windows NT 11.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0',
        ]
        
        self.current_user_agent_index = 0
        self._setup_browser_headers()
    
    def _setup_browser_headers(self):
        """Set up realistic browser headers"""
        # Rotate user agent
        user_agent = self.user_agents[self.current_user_agent_index]
        self.current_user_agent_index = (self.current_user_agent_index + 1) % len(self.user_agents)
        
        self.session.headers.update({
            'User-Agent': user_agent,
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate',
            'Content-Type': 'application/x-www-form-urlencoded',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Cache-Control': 'max-age=0',
        })
        self.session.timeout = 30
    
    def _rotate_user_agent(self):
        """Rotate to the next user agent"""
        user_agent = self.user_agents[self.current_user_agent_index]
        self.current_user_agent_index = (self.current_user_agent_index + 1) % len(self.user_agents)
        self.session.headers.update({'User-Agent': user_agent})
        return user_agent
    
    def load_progress(self) -> bool:
        """Load progress from file"""
        if os.path.exists(self.progress_file):
            try:
                with open(self.progress_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.progress_data.update(data)
                    # Convert processed_games list back to set
                    if isinstance(self.progress_data.get('processed_games'), list):
                        self.progress_data['processed_games'] = set(self.progress_data['processed_games'])
                    # Convert processed_files list back to set
                    if isinstance(self.progress_data.get('processed_files'), list):
                        self.progress_data['processed_files'] = set(self.progress_data['processed_files'])
                    print(f"✅ Loaded progress: {len(self.progress_data['processed_games'])} games already processed, {len(self.progress_data['processed_files'])} files processed")
                    return True
            except Exception as e:
                print(f"⚠️  Error loading progress: {e}")
                return False
        return False
    
    def save_progress(self):
        """Save progress to file"""
        try:
            # Convert set to list for JSON serialization
            progress_to_save = self.progress_data.copy()
            progress_to_save['processed_games'] = list(self.progress_data['processed_games'])
            progress_to_save['processed_files'] = list(self.progress_data['processed_files'])
            progress_to_save['last_run_timestamp'] = time.time()
            
            with open(self.progress_file, 'w', encoding='utf-8') as f:
                json.dump(progress_to_save, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"⚠️  Error saving progress: {e}")
    
    def load_database(self):
        """Load existing database"""
        if os.path.exists(self.db_file):
            try:
                with open(self.db_file, 'r', encoding='utf-8') as f:
                    self.games_db = json.load(f)
                    print(f"✅ Loaded database: {len(self.games_db)} games")
            except Exception as e:
                print(f"⚠️  Error loading database: {e}")
                self.games_db = {}
        else:
            self.games_db = {}
    
    def save_database(self):
        """Save database to file"""
        try:
            with open(self.db_file, 'w', encoding='utf-8') as f:
                json.dump(self.games_db, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"⚠️  Error saving database: {e}")
    
    def parse_dat_files(self) -> List[str]:
        """Find all .dat files in the directory and extract machine names
        Returns a list of game IDs (machine names)
        """
        game_ids = []
        
        # Find all .dat files in the directory
        dat_pattern = os.path.join(self.dat_directory, "*.dat")
        dat_files = glob.glob(dat_pattern)
        
        if not dat_files:
            print(f"⚠️  No .dat files found in {self.dat_directory}")
            return game_ids
        
        print(f"📁 Found {len(dat_files)} .dat file(s)")
        
        for dat_file in dat_files:
            file_basename = os.path.basename(dat_file)
            
            # Check if file already processed
            if dat_file in self.progress_data['processed_files']:
                print(f"⏭️  Skipping already processed file: {file_basename}")
                continue
            
            print(f"📄 Parsing: {file_basename}")
            
            try:
                # Parse XML file
                tree = ET.parse(dat_file)
                root = tree.getroot()
                
                # Find all machine elements
                machines = root.findall('.//machine')
                print(f"   Found {len(machines)} machine(s) in {file_basename}")
                
                for machine in machines:
                    machine_name = machine.get('name')
                    if machine_name:
                        game_ids.append(machine_name)
                
                # Mark file as processed
                self.progress_data['processed_files'].add(dat_file)
                self.save_progress()
                
            except ET.ParseError as e:
                print(f"❌ XML parsing error in {file_basename}: {e}")
                continue
            except Exception as e:
                print(f"❌ Error processing {file_basename}: {e}")
                continue
        
        print(f"✅ Extracted {len(game_ids)} game IDs from .dat files")
        return game_ids
    
    def query_api_batch(self, game_ids: List[str], retry_on_error: bool = True) -> Optional[Dict]:
        """Query the ArcadeItalia API for multiple game IDs (up to 800) using POST
        Returns the JSON response data with a 'result' array or None on error
        """
        if not game_ids:
            return None
        
        # Limit to 800 games per batch
        if len(game_ids) > 800:
            game_ids = game_ids[:800]
        
        max_retries = 3 if retry_on_error else 1
        # Join game IDs with semicolon
        game_names = ';'.join(game_ids)
        
        for attempt in range(max_retries):
            try:
                # Rotate user agent before each request
                current_ua = self._rotate_user_agent()
                if random.random() < 0.1:  # 10% chance to log user agent rotation
                    print(f"🔄 Using User-Agent: {current_ua[:60]}...")
                
                print(f"📡 Querying API (POST) for batch of {len(game_ids)} games")
                
                # Use POST with form data
                payload = {
                    'ajax': 'query_mame',
                    'game_name': game_names
                }
                response = self.session.post(self.api_base_url, data=payload, timeout=60)  # Longer timeout for batch requests
                
                # Handle HTTP errors
                if response.status_code != 200:
                    print(f"⚠️  HTTP {response.status_code} for batch query")
                    if retry_on_error and attempt < max_retries - 1:
                        print(f"   Retrying (attempt {attempt + 1}/{max_retries})...")
                        time.sleep(2)
                        continue
                    else:
                        return None
                
                # Try to parse JSON response
                try:
                    data = response.json()
                    # Check if response has data
                    if not data or not isinstance(data, dict):
                        print(f"⚠️  Invalid response format for batch query")
                        return None
                    
                    # Check if we have results
                    if 'result' in data and isinstance(data['result'], list):
                        print(f"✅ Received {len(data['result'])} results from batch query")
                        return data
                    else:
                        print(f"⚠️  No results array in batch response")
                        return None
                        
                except json.JSONDecodeError as e:
                    print(f"❌ JSON decode error for batch query: {e}")
                    print(f"   Response text: {response.text[:500]}")
                    return None
                    
            except requests.exceptions.RequestException as e:
                print(f"❌ Request error for batch query: {e}")
                if retry_on_error and attempt < max_retries - 1:
                    print(f"   Retrying (attempt {attempt + 1}/{max_retries})...")
                    time.sleep(2)
                    continue
                else:
                    return None
        
        return None
    
    def query_api(self, game_id: str, retry_on_error: bool = True) -> Optional[Dict]:
        """Query the ArcadeItalia API for a single game ID
        Returns the JSON response data or None on error
        Note: For better performance, use query_api_batch() for multiple games
        """
        max_retries = 3 if retry_on_error else 1
        url = f"{self.api_base_url}?ajax=query_mame&game_name={game_id}"
        
        for attempt in range(max_retries):
            try:
                # Rotate user agent before each request
                current_ua = self._rotate_user_agent()
                if random.random() < 0.1:  # 10% chance to log user agent rotation
                    print(f"🔄 Using User-Agent: {current_ua[:60]}...")
                
                print(f"📡 Querying API for: {game_id}")
                response = self.session.get(url, timeout=30)
                
                # Handle HTTP errors
                if response.status_code != 200:
                    print(f"⚠️  HTTP {response.status_code} for {game_id}")
                    if retry_on_error and attempt < max_retries - 1:
                        print(f"   Retrying (attempt {attempt + 1}/{max_retries})...")
                        time.sleep(2)
                        continue
                    else:
                        return None
                
                # Try to parse JSON response
                try:
                    data = response.json()
                    # Check if response has data
                    # For single queries, the response might be a dict with 'result' array or direct fields
                    if not data:
                        print(f"⚠️  No data returned for {game_id}")
                        return None
                    
                    # If response has 'result' array, extract first item
                    if isinstance(data, dict) and 'result' in data and isinstance(data['result'], list):
                        if len(data['result']) > 0:
                            return data['result'][0]
                        else:
                            print(f"⚠️  Empty result array for {game_id}")
                            return None
                    # If response has direct fields (title, etc.), return as-is
                    elif isinstance(data, dict) and data.get('title'):
                        return data
                    else:
                        print(f"⚠️  No valid data for {game_id}")
                        return None
                        
                except json.JSONDecodeError as e:
                    print(f"❌ JSON decode error for {game_id}: {e}")
                    print(f"   Response text: {response.text[:200]}")
                    return None
                    
            except requests.exceptions.RequestException as e:
                print(f"❌ Request error for {game_id}: {e}")
                if retry_on_error and attempt < max_retries - 1:
                    print(f"   Retrying (attempt {attempt + 1}/{max_retries})...")
                    time.sleep(2)
                    continue
                else:
                    return None
        
        return None
    
    def extract_game_info(self, api_data: Dict, game_id: str) -> Dict:
        """Extract and normalize game information from API response"""
        game_info = {
            'id': game_id,
            'name': None,
            'genre': None,
            'release_date': None,
            'publisher': None,
            'nbplayers': None,
            'rating': None,
            'description': None,
            'boxfront': None,
            'titleshot': None,
            'screenshot': None,
            'cartridge': None,
            'video': None,
            'youtubeurl': None,
        }
        
        # Extract name from "title" field
        if api_data.get('title'):
            game_info['name'] = api_data['title'].strip()
        
        # Extract genre from "genre" field
        if api_data.get('genre'):
            game_info['genre'] = api_data['genre'].strip()
        
        # Extract release_date from "year" field, convert to "01-01-{year}" format
        if api_data.get('year'):
            year = str(api_data['year']).strip()
            if year and year.isdigit():
                game_info['release_date'] = f"01-01-{year}"
        
        # Extract publisher from "manufacturer" field
        if api_data.get('manufacturer'):
            game_info['publisher'] = api_data['manufacturer'].strip()
        
        # Extract nbplayers from "players" field
        if api_data.get('players'):
            game_info['nbplayers'] = str(api_data['players']).strip()
        
        # Extract rating from "rate" field (value /100), normalize to /5 by dividing by 20
        if api_data.get('rate') is not None:
            try:
                rate_value = float(api_data['rate'])
                # Normalize from /100 to /5 by dividing by 20
                game_info['rating'] = rate_value / 20.0
            except (ValueError, TypeError):
                pass
        
        # Extract description from "history" field
        if api_data.get('history'):
            description = api_data['history'].strip()
            
            # Replace \r\n with \n
            description = description.replace('\r\n', '\n')
            
            # Remove any line containing "published X years ago", "(c)", or "Arcade Video game:"
            lines = description.split('\n')
            filtered_lines = [
                line for line in lines 
                if not re.search(r'published \d+ years ago', line, re.IGNORECASE)
                and '(c)' not in line
                and 'Arcade Video game:' not in line
            ]
            description = '\n'.join(filtered_lines)
            
            # Remove everything after "- CONTRIBUTE -\n\n" including this line
            contribute_index = description.find('- CONTRIBUTE -\n\n')
            if contribute_index != -1:
                description = description[:contribute_index].rstrip()
            
            # Remove everything after "- TECHNICAL -\r\n" or "- TECHNICAL -\n"
            technical_index = description.find('- TECHNICAL -')
            if technical_index != -1:
                description = description[:technical_index].rstrip()
            
            # Remove leading newlines from description
            description = description.lstrip('\n')
            
            # Set description to None if it only contains newline characters or is empty
            if description.strip('\n') == '':
                description = None
            
            game_info['description'] = description
        
        # Extract boxfront from "url_image_flyer" field
        if api_data.get('url_image_flyer'):
            url = api_data['url_image_flyer'].strip()
            if url:
                game_info['boxfront'] = url
        
        # Extract titleshot from "url_image_title" field
        if api_data.get('url_image_title'):
            url = api_data['url_image_title'].strip()
            if url:
                game_info['titleshot'] = url
        
        # Extract screenshot from "url_image_ingame" field
        if api_data.get('url_image_ingame'):
            url = api_data['url_image_ingame'].strip()
            if url:
                game_info['screenshot'] = url
        
        # Extract cartridge from "url_image_cabinet" field
        if api_data.get('url_image_cabinet'):
            url = api_data['url_image_cabinet'].strip()
            if url:
                game_info['cartridge'] = url
        
        # Extract video from "url_video_shortplay_hd" or "url_video_shortplay" field
        # Prefer HD version, fall back to standard if HD not available
        if api_data.get('url_video_shortplay_hd'):
            url = api_data['url_video_shortplay_hd'].strip()
            if url:
                game_info['video'] = url
        elif api_data.get('url_video_shortplay'):
            url = api_data['url_video_shortplay'].strip()
            if url:
                game_info['video'] = url
        
        # Extract youtubeurl from youtube_video_id field, construct full URL
        if api_data.get('youtube_video_id'):
            video_id = str(api_data['youtube_video_id']).strip()
            if video_id:
                game_info['youtubeurl'] = f"https://www.youtube.com/watch?v={video_id}"
        
        # Final cleanup: ensure all fields are None if empty
        for key in game_info:
            value = game_info.get(key)
            if value == '' or value == []:
                game_info[key] = None
        
        return game_info
    
    def scrape_game(self, game_id: str) -> Optional[Dict]:
        """Scrape a single game by querying the API"""
        # Check if already processed
        if game_id in self.progress_data['processed_games']:
            print(f"⏭️  Skipping already processed: {game_id}")
            return None
        
        # Query API
        api_data = self.query_api(game_id)
        if not api_data:
            print(f"⚠️  No data returned for {game_id}, skipping")
            # Mark as processed even if no data (to avoid retrying)
            self.progress_data['processed_games'].add(game_id)
            self.save_progress()
            return None
        
        # Extract game info
        game_info = self.extract_game_info(api_data, game_id)
        
        if game_info:
            # Save to database using game_id as key
            self.games_db[game_id] = game_info
            self.progress_data['processed_games'].add(game_id)
            self.progress_data['total_games_collected'] = len(self.games_db)
            
            # Save after each game
            self.save_database()
            self.save_progress()
            
            game_name = game_info.get('name', game_id)
            print(f"✅ Scraped: {game_name} (ID: {game_id}) - Pub: {game_info.get('publisher', 'N/A')} - Year: {game_info.get('release_date', 'N/A')} - Rating: {game_info.get('rating', 'N/A')}")
            return game_info
        
        return None
    
    def run_scraper(self, resume: bool = True):
        """Run the scraper"""
        print("🚀 Starting ArcadeDB scraper...")
        
        # Load existing data
        self.load_database()
        if resume:
            self.load_progress()
        
        self.progress_data['status'] = 'running'
        self.save_progress()
        
        try:
            # Parse all .dat files to get game IDs
            game_ids = self.parse_dat_files()
            
            if not game_ids:
                print("⚠️  No game IDs found to scrape")
                return
            
            # Filter out already processed games
            games_to_process = [gid for gid in game_ids if gid not in self.progress_data['processed_games']]
            
            if not games_to_process:
                print("✅ All games have already been processed!")
                return
            
            total_games = len(games_to_process)
            games_scraped = 0
            games_skipped = 0
            
            print(f"\n{'='*60}")
            print(f"📌 Processing {total_games} games (in batches of up to 800)")
            print(f"{'='*60}\n")
            
            # Process games in batches of 800
            batch_size = 800
            for batch_start in range(0, total_games, batch_size):
                batch_end = min(batch_start + batch_size, total_games)
                batch_ids = games_to_process[batch_start:batch_end]
                batch_num = (batch_start // batch_size) + 1
                total_batches = (total_games + batch_size - 1) // batch_size
                
                print(f"\n📦 Batch {batch_num}/{total_batches}: Processing {len(batch_ids)} games")
                
                # Query API for batch
                batch_response = self.query_api_batch(batch_ids)
                
                if not batch_response or 'result' not in batch_response:
                    print(f"⚠️  No data returned for batch {batch_num}, marking all as processed")
                    # Mark all games in batch as processed to avoid retrying
                    for game_id in batch_ids:
                        self.progress_data['processed_games'].add(game_id)
                    self.save_progress()
                    games_skipped += len(batch_ids)
                    time.sleep(1)  # Rate limiting between batches
                    continue
                
                # Create a mapping of game_name to result data for quick lookup
                results_map = {}
                for result_item in batch_response['result']:
                    game_name = result_item.get('game_name')
                    if game_name:
                        results_map[game_name] = result_item
                
                # Process each game in the batch
                for game_id in batch_ids:
                    # Check if already processed (double-check)
                    if game_id in self.progress_data['processed_games']:
                        continue
                    
                    # Get result data for this game
                    api_data = results_map.get(game_id)
                    
                    if not api_data:
                        print(f"⚠️  No data in batch response for {game_id}, skipping")
                        self.progress_data['processed_games'].add(game_id)
                        games_skipped += 1
                        self.save_progress()
                        continue
                    
                    # Extract game info
                    game_info = self.extract_game_info(api_data, game_id)
                    
                    if game_info:
                        # Save to database using game_id as key
                        self.games_db[game_id] = game_info
                        self.progress_data['processed_games'].add(game_id)
                        self.progress_data['total_games_collected'] = len(self.games_db)
                        
                        games_scraped += 1
                        
                        game_name = game_info.get('name', game_id)
                        print(f"✅ [{games_scraped + games_skipped}/{total_games}] {game_name} (ID: {game_id})")
                    else:
                        games_skipped += 1
                        self.progress_data['processed_games'].add(game_id)
                
                # Save after each batch
                self.save_database()
                self.save_progress()
                
                # Rate limiting: 1 second delay between batches
                if batch_end < total_games:
                    time.sleep(1)
            
            self.progress_data['status'] = 'completed'
            print(f"\n🎉 Scraping completed!")
            print(f"   Total games: {total_games}")
            print(f"   Scraped: {games_scraped}")
            print(f"   Skipped: {games_skipped}")
            
        except KeyboardInterrupt:
            print("\n⚠️  Scraping interrupted by user")
            self.progress_data['status'] = 'interrupted'
            self.save_progress()
            print(f"💾 Progress saved. Resume with: python {sys.argv[0]} --resume")
        except Exception as e:
            print(f"\n❌ Error during scraping: {e}")
            import traceback
            traceback.print_exc()
            self.progress_data['status'] = 'interrupted'
            self.save_progress()
            raise
        finally:
            self.save_database()
            self.save_progress()

def main():
    scraper = ArcadeDBScraper()
    
    # Parse command line arguments
    resume = True
    if len(sys.argv) > 1:
        if sys.argv[1] == '--fresh':
            resume = False
            print("🆕 Starting fresh (clearing progress)")
            if os.path.exists(scraper.progress_file):
                os.remove(scraper.progress_file)
        elif sys.argv[1] == '--resume':
            resume = True
        elif sys.argv[1] == '--status':
            scraper.load_progress()
            scraper.load_database()
            print("\n📊 Scraper Status:")
            print(f"   Status: {scraper.progress_data['status']}")
            print(f"   Games processed: {len(scraper.progress_data.get('processed_games', []))}")
            print(f"   Files processed: {len(scraper.progress_data.get('processed_files', []))}")
            print(f"   Total games in DB: {len(scraper.games_db)}")
            if scraper.progress_data.get('last_run_timestamp'):
                import datetime
                last_run = datetime.datetime.fromtimestamp(scraper.progress_data['last_run_timestamp'])
                print(f"   Last run: {last_run}")
            return
    
    scraper.run_scraper(resume=resume)

if __name__ == "__main__":
    main()
