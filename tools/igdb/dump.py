#!/usr/bin/env python3
"""
IGDB Database Dump Script

This script dumps data from the IGDB database using direct API calls.
It fetches games, platforms, genres, and other related data and saves them to JSON files.

Based on the GameCompendium implementation:
https://github.com/SnowyCoder/gamecompendium/blob/main/gamecompendium/igdb.py
"""

import os
import sys
import json
import asyncio
import httpx
import time
import signal
import argparse
import pickle
from datetime import datetime
from typing import Dict, List, Any, Optional

# Import normalization function from game_utils
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from game_utils import normalize_game_name

class IGDBDumper:
    def __init__(self, force=False):
        # Load credentials from credentials.json
        self.client_id = None
        self.client_secret = None
        self.access_token = None
        self.async_client = None
        self.dump_dir = "var/db/igdb/dump"
        self.force = force
        
        # Create dump directory
        os.makedirs(self.dump_dir, exist_ok=True)
        
        # Rate limiting
        self.request_delay = 0.1  # 100ms between requests
        self.last_request_time = 0
        
        # Stop/resume functionality
        self.should_stop = False
        self.progress_file = os.path.join(self.dump_dir, 'dump_progress.json')
        self.setup_signal_handlers()
    
    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            print(f"\n🛑 Received signal {signum}. Stopping gracefully...")
            self.should_stop = True
        
        signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C
        signal.signal(signal.SIGTERM, signal_handler)  # Termination signal
    
    def file_exists_and_valid(self, filename: str) -> bool:
        """Check if a dump file exists and contains valid data"""
        if self.force:
            return False
        
        filepath = os.path.join(self.dump_dir, filename)
        if not os.path.exists(filepath):
            return False
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Check if it's a non-empty list or dict
                if isinstance(data, list) and len(data) > 0:
                    return True
                elif isinstance(data, dict) and len(data) > 0:
                    return True
                return False
        except (json.JSONDecodeError, IOError):
            return False
    
    def save_progress(self, progress_data: Dict[str, Any]):
        """Save current progress to file"""
        try:
            with open(self.progress_file, 'w', encoding='utf-8') as f:
                json.dump(progress_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"⚠️ Warning: Could not save progress: {e}")
    
    def load_progress(self) -> Dict[str, Any]:
        """Load progress from file"""
        try:
            if os.path.exists(self.progress_file):
                with open(self.progress_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"⚠️ Warning: Could not load progress: {e}")
        return {}
    
    def clear_progress(self):
        """Clear progress file"""
        try:
            if os.path.exists(self.progress_file):
                os.remove(self.progress_file)
        except Exception as e:
            print(f"⚠️ Warning: Could not clear progress: {e}")
        
    def load_credentials(self):
        """Load IGDB credentials from credentials.json"""
        credentials_path = 'var/config/credentials.json'
        
        if not os.path.exists(credentials_path):
            raise FileNotFoundError(f"Credentials file not found: {credentials_path}")
        
        try:
            with open(credentials_path, 'r', encoding='utf-8') as f:
                credentials = json.load(f)
            
            igdb_config = credentials.get('igdb', {})
            self.client_id = igdb_config.get('client_id')
            self.client_secret = igdb_config.get('client_secret')
            
            if not self.client_id or not self.client_secret:
                raise ValueError("IGDB client_id and client_secret must be configured in var/config/credentials.json")
                
        except Exception as e:
            raise ValueError(f"Error loading credentials: {e}")
    
    async def get_access_token(self):
        """Get IGDB access token"""
        token_url = "https://id.twitch.tv/oauth2/token"
        token_data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'grant_type': 'client_credentials'
        }
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(token_url, data=token_data)
            
            if response.status_code != 200:
                raise Exception(f"Failed to get access token: {response.status_code} - {response.text}")
            
            token_response = response.json()
            return token_response['access_token']
    
    async def initialize(self):
        """Initialize the IGDB client and get access token"""
        print("🔧 Initializing IGDB dumper...")
        
        # Load credentials
        self.load_credentials()
        print(f"✅ Loaded IGDB credentials")
        
        # Get access token
        self.access_token = await self.get_access_token()
        print(f"✅ Got IGDB access token")
        
        # Initialize async client
        self.async_client = httpx.AsyncClient(
            http2=True,
            limits=httpx.Limits(
                max_connections=8,
                max_keepalive_connections=8,
                keepalive_expiry=30.0
            ),
            timeout=httpx.Timeout(
                connect=5.0,
                read=10.0,
                write=5.0,
                pool=3.0
            )
        )
        print(f"✅ Initialized IGDB async client")
        
    async def rate_limit(self):
        """Simple rate limiting"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.request_delay:
            await asyncio.sleep(self.request_delay - time_since_last)
        self.last_request_time = time.time()
        
    async def make_request(self, endpoint: str, query: str) -> List[Dict]:
        """Make a request to IGDB API with rate limiting"""
        # Check if we should stop
        if self.should_stop:
            raise KeyboardInterrupt("Stop requested")
        
        await self.rate_limit()
        
        # Check again after rate limiting
        if self.should_stop:
            raise KeyboardInterrupt("Stop requested")
        
        url = f"https://api.igdb.com/v4/{endpoint}"
        headers = {
            'Client-ID': self.client_id,
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'text/plain'
        }
        
        try:
            response = await self.async_client.post(url, headers=headers, content=query, timeout=10.0)
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ HTTP {response.status_code} error for {endpoint}: {response.text}")
                return []
                
        except Exception as e:
            print(f"❌ Error making request to {endpoint}: {e}")
            return []
    
    async def dump_platforms(self) -> List[Dict]:
        """Dump all platforms from IGDB"""
        if self.file_exists_and_valid('platforms.json'):
            print("📱 Platforms already dumped, loading from file...")
            filename = os.path.join(self.dump_dir, 'platforms.json')
            with open(filename, 'r', encoding='utf-8') as f:
                platforms = json.load(f)
            print(f"✅ Loaded {len(platforms)} platforms from {filename}")
            return platforms
        
        print("📱 Dumping platforms...")
        
        query = """
        fields id,name,slug,abbreviation,alternative_name,category,generation,platform_family,summary,url,versions,websites;
        limit 500;
        """
        
        platforms = await self.make_request('platforms', query)
        
        # Save to file
        filename = os.path.join(self.dump_dir, 'platforms.json')
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(platforms, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Dumped {len(platforms)} platforms to {filename}")
        return platforms
    
    async def dump_genres(self) -> List[Dict]:
        """Dump all genres from IGDB"""
        if self.file_exists_and_valid('genres.json'):
            print("🎭 Genres already dumped, loading from file...")
            filename = os.path.join(self.dump_dir, 'genres.json')
            with open(filename, 'r', encoding='utf-8') as f:
                genres = json.load(f)
            print(f"✅ Loaded {len(genres)} genres from {filename}")
            return genres
        
        print("🎭 Dumping genres...")
        
        query = """
        fields id,name,slug,url;
        limit 500;
        """
        
        genres = await self.make_request('genres', query)
        
        # Save to file
        filename = os.path.join(self.dump_dir, 'genres.json')
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(genres, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Dumped {len(genres)} genres to {filename}")
        return genres
    
    async def dump_game_modes(self) -> List[Dict]:
        """Dump all game modes from IGDB"""
        if self.file_exists_and_valid('game_modes.json'):
            print("🎮 Game modes already dumped, loading from file...")
            filename = os.path.join(self.dump_dir, 'game_modes.json')
            with open(filename, 'r', encoding='utf-8') as f:
                game_modes = json.load(f)
            print(f"✅ Loaded {len(game_modes)} game modes from {filename}")
            return game_modes
        
        print("🎮 Dumping game modes...")
        
        query = """
        fields id,name,slug,url;
        limit 500;
        """
        
        game_modes = await self.make_request('game_modes', query)
        
        # Save to file
        filename = os.path.join(self.dump_dir, 'game_modes.json')
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(game_modes, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Dumped {len(game_modes)} game modes to {filename}")
        return game_modes
    
    async def dump_player_perspectives(self) -> List[Dict]:
        """Dump all player perspectives from IGDB"""
        if self.file_exists_and_valid('player_perspectives.json'):
            print("👁️ Player perspectives already dumped, loading from file...")
            filename = os.path.join(self.dump_dir, 'player_perspectives.json')
            with open(filename, 'r', encoding='utf-8') as f:
                perspectives = json.load(f)
            print(f"✅ Loaded {len(perspectives)} player perspectives from {filename}")
            return perspectives
        
        print("👁️ Dumping player perspectives...")
        
        query = """
        fields id,name,slug,url;
        limit 500;
        """
        
        perspectives = await self.make_request('player_perspectives', query)
        
        # Save to file
        filename = os.path.join(self.dump_dir, 'player_perspectives.json')
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(perspectives, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Dumped {len(perspectives)} player perspectives to {filename}")
        return perspectives
    
    async def dump_companies(self) -> List[Dict]:
        """Dump all companies from IGDB (with pagination)"""
        if self.file_exists_and_valid('companies.json'):
            print("🏢 Companies already dumped, loading from file...")
            filename = os.path.join(self.dump_dir, 'companies.json')
            with open(filename, 'r', encoding='utf-8') as f:
                companies = json.load(f)
            print(f"✅ Loaded {len(companies)} companies from {filename}")
            return companies
        
        print("🏢 Dumping companies...")
        
        all_companies = []
        offset = 0
        batch_size = 500
        
        try:
            while True:
                # Check if we should stop
                if self.should_stop:
                    print(f"🛑 Stopping at {len(all_companies)} companies (offset: {offset})")
                    break
                
                print(f"📦 Fetching companies batch: offset={offset}, limit={batch_size}")
                
                query = f"""
                fields id,name,slug,description,country,start_date,logo,url,websites,published,developed;
                limit {batch_size};
                offset {offset};
                """
                
                companies_batch = await self.make_request('companies', query)
                
                if not companies_batch:
                    print("📭 No more companies to fetch")
                    break
                
                all_companies.extend(companies_batch)
                offset += batch_size
                
                print(f"✅ Fetched {len(companies_batch)} companies (total: {len(all_companies)})")
                
                # If we got fewer companies than requested, we've reached the end
                if len(companies_batch) < batch_size:
                    print("📭 Reached end of companies")
                    break
        
        except KeyboardInterrupt:
            print(f"🛑 Interrupted at {len(all_companies)} companies (offset: {offset})")
            raise
        
        # Save to file
        filename = os.path.join(self.dump_dir, 'companies.json')
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(all_companies, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Dumped {len(all_companies)} companies to {filename}")
        return all_companies
    
    async def dump_games_batch(self, offset: int = 0, limit: int = 500) -> List[Dict]:
        """Dump a batch of games from IGDB"""
        query = f"""
        fields id,name,slug,summary,storyline,first_release_date,rating,rating_count,total_rating,total_rating_count,aggregated_rating,aggregated_rating_count,genres,platforms,game_modes,player_perspectives,cover,screenshots,artworks,websites,url,collection,franchise,game_engines,age_ratings,release_dates,alternative_names,external_games,dlcs,expansions,standalone_expansions,remakes,remasters,similar_games,version_parent,game_localizations,involved_companies;
        limit {limit};
        offset {offset};
        """
        
        games = await self.make_request('games', query)
        return games
    
    async def dump_games(self, max_games: Optional[int] = None) -> List[Dict]:
        """Dump all games from IGDB (with pagination and resume support)"""
        if self.file_exists_and_valid('games.json'):
            print("🎯 Games already dumped, loading from file...")
            filename = os.path.join(self.dump_dir, 'games.json')
            with open(filename, 'r', encoding='utf-8') as f:
                all_games = json.load(f)
            print(f"✅ Loaded {len(all_games)} games from {filename}")
            return all_games
        
        print("🎯 Dumping games...")
        
        # Load existing progress
        progress = self.load_progress()
        all_games = progress.get('games', [])
        offset = progress.get('games_offset', 0)
        total_dumped = len(all_games)
        
        if total_dumped > 0:
            print(f"🔄 Resuming from {total_dumped} games (offset: {offset})")
        
        batch_size = 500
        
        try:
            while True:
                # Check if we should stop
                if self.should_stop:
                    print(f"🛑 Stopping at {total_dumped} games (offset: {offset})")
                    break
                
                print(f"📦 Fetching games batch: offset={offset}, limit={batch_size}")
                
                games_batch = await self.dump_games_batch(offset, batch_size)
                
                if not games_batch:
                    print("📭 No more games to fetch")
                    break
                
                all_games.extend(games_batch)
                total_dumped += len(games_batch)
                offset += batch_size
                
                print(f"✅ Fetched {len(games_batch)} games (total: {total_dumped})")
                
                # Save progress
                self.save_progress({
                    'games': all_games,
                    'games_offset': offset,
                    'total_games': total_dumped,
                    'last_updated': datetime.now().isoformat()
                })
                
                # Check if we've reached the maximum
                if max_games and total_dumped >= max_games:
                    print(f"🛑 Reached maximum games limit: {max_games}")
                    break
                
                # If we got fewer games than requested, we've reached the end
                if len(games_batch) < batch_size:
                    print("📭 Reached end of games")
                    break
        
        except KeyboardInterrupt:
            print(f"🛑 Interrupted at {total_dumped} games (offset: {offset})")
            # Save current progress before exiting
            self.save_progress({
                'games': all_games,
                'games_offset': offset,
                'total_games': total_dumped,
                'last_updated': datetime.now().isoformat(),
                'interrupted': True
            })
            raise
        
        # Save final results
        filename = os.path.join(self.dump_dir, 'games.json')
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(all_games, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Dumped {len(all_games)} games to {filename}")
        return all_games
    
    async def dump_covers(self, game_ids: List[int]) -> List[Dict]:
        """Dump covers for specific games"""
        if self.file_exists_and_valid('covers.json'):
            print("🖼️ Covers already dumped, loading from file...")
            filename = os.path.join(self.dump_dir, 'covers.json')
            with open(filename, 'r', encoding='utf-8') as f:
                all_covers = json.load(f)
            print(f"✅ Loaded {len(all_covers)} covers from {filename}")
            return all_covers
        
        print(f"🖼️ Dumping covers for {len(game_ids)} games...")
        
        # Process in batches to avoid query length limits
        batch_size = 100
        all_covers = []
        
        for i in range(0, len(game_ids), batch_size):
            batch_ids = game_ids[i:i + batch_size]
            ids_str = ','.join(map(str, batch_ids))
            
            query = f"""
            fields id,image_id,width,height,url,game_localization;
            where game = ({ids_str});
            limit 500;
            """
            
            covers = await self.make_request('covers', query)
            all_covers.extend(covers)
            
            print(f"✅ Fetched {len(covers)} covers (batch {i//batch_size + 1})")
        
        # Save to file
        filename = os.path.join(self.dump_dir, 'covers.json')
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(all_covers, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Dumped {len(all_covers)} covers to {filename}")
        return all_covers
    
    async def dump_screenshots(self, game_ids: List[int]) -> List[Dict]:
        """Dump screenshots for specific games"""
        if self.file_exists_and_valid('screenshots.json'):
            print("📸 Screenshots already dumped, loading from file...")
            filename = os.path.join(self.dump_dir, 'screenshots.json')
            with open(filename, 'r', encoding='utf-8') as f:
                all_screenshots = json.load(f)
            print(f"✅ Loaded {len(all_screenshots)} screenshots from {filename}")
            return all_screenshots
        
        print(f"📸 Dumping screenshots for {len(game_ids)} games...")
        
        # Process in batches
        batch_size = 100
        all_screenshots = []
        
        for i in range(0, len(game_ids), batch_size):
            batch_ids = game_ids[i:i + batch_size]
            ids_str = ','.join(map(str, batch_ids))
            
            query = f"""
            fields id,image_id,width,height,url;
            where game = ({ids_str});
            limit 500;
            """
            
            screenshots = await self.make_request('screenshots', query)
            all_screenshots.extend(screenshots)
            
            print(f"✅ Fetched {len(screenshots)} screenshots (batch {i//batch_size + 1})")
        
        # Save to file
        filename = os.path.join(self.dump_dir, 'screenshots.json')
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(all_screenshots, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Dumped {len(all_screenshots)} screenshots to {filename}")
        return all_screenshots
    
    async def dump_artworks(self, game_ids: List[int]) -> List[Dict]:
        """Dump artworks for specific games"""
        if self.file_exists_and_valid('artworks.json'):
            print("🎨 Artworks already dumped, loading from file...")
            filename = os.path.join(self.dump_dir, 'artworks.json')
            with open(filename, 'r', encoding='utf-8') as f:
                all_artworks = json.load(f)
            print(f"✅ Loaded {len(all_artworks)} artworks from {filename}")
            return all_artworks
        
        print(f"🎨 Dumping artworks for {len(game_ids)} games...")
        
        # Process in batches
        batch_size = 100
        all_artworks = []
        
        for i in range(0, len(game_ids), batch_size):
            batch_ids = game_ids[i:i + batch_size]
            ids_str = ','.join(map(str, batch_ids))
            
            query = f"""
            fields id,image_id,width,height,url,artwork_type;
            where game = ({ids_str});
            limit 500;
            """
            
            artworks = await self.make_request('artworks', query)
            all_artworks.extend(artworks)
            
            print(f"✅ Fetched {len(artworks)} artworks (batch {i//batch_size + 1})")
        
        # Save to file
        filename = os.path.join(self.dump_dir, 'artworks.json')
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(all_artworks, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Dumped {len(all_artworks)} artworks to {filename}")
        return all_artworks
    
    async def dump_alternative_names(self, game_ids: List[int]) -> List[Dict]:
        """Dump alternative names for specific games"""
        if self.file_exists_and_valid('alternative_names.json'):
            print("📝 Alternative names already dumped, loading from file...")
            filename = os.path.join(self.dump_dir, 'alternative_names.json')
            with open(filename, 'r', encoding='utf-8') as f:
                all_alternative_names = json.load(f)
            print(f"✅ Loaded {len(all_alternative_names)} alternative names from {filename}")
            return all_alternative_names
        
        print(f"📝 Dumping alternative names for {len(game_ids)} games...")
        
        # Process in batches
        batch_size = 100
        all_alternative_names = []
        
        for i in range(0, len(game_ids), batch_size):
            batch_ids = game_ids[i:i + batch_size]
            ids_str = ','.join(map(str, batch_ids))
            
            query = f"""
            fields id,name,comment,game;
            where game = ({ids_str});
            limit 500;
            """
            
            alternative_names = await self.make_request('alternative_names', query)
            all_alternative_names.extend(alternative_names)
            
            print(f"✅ Fetched {len(alternative_names)} alternative names (batch {i//batch_size + 1})")
        
        # Save to file
        filename = os.path.join(self.dump_dir, 'alternative_names.json')
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(all_alternative_names, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Dumped {len(all_alternative_names)} alternative names to {filename}")
        return all_alternative_names
    
    async def dump_all_alternative_names(self) -> List[Dict]:
        """Dump all alternative names from IGDB (with pagination)"""
        if self.file_exists_and_valid('all_alternative_names.json'):
            print("📝 All alternative names already dumped, loading from file...")
            filename = os.path.join(self.dump_dir, 'all_alternative_names.json')
            with open(filename, 'r', encoding='utf-8') as f:
                all_alternative_names = json.load(f)
            print(f"✅ Loaded {len(all_alternative_names)} alternative names from {filename}")
            return all_alternative_names
        
        print("📝 Dumping all alternative names...")
        
        all_alternative_names = []
        offset = 0
        batch_size = 500
        
        try:
            while True:
                # Check if we should stop
                if self.should_stop:
                    print(f"🛑 Stopping at {len(all_alternative_names)} alternative names (offset: {offset})")
                    break
                
                print(f"📦 Fetching alternative names batch: offset={offset}, limit={batch_size}")
                
                query = f"""
                fields id,name,comment,game;
                limit {batch_size};
                offset {offset};
                """
                
                alternative_names_batch = await self.make_request('alternative_names', query)
                
                if not alternative_names_batch:
                    print("📭 No more alternative names to fetch")
                    break
                
                all_alternative_names.extend(alternative_names_batch)
                offset += batch_size
                
                print(f"✅ Fetched {len(alternative_names_batch)} alternative names (total: {len(all_alternative_names)})")
                
                # If we got fewer alternative names than requested, we've reached the end
                if len(alternative_names_batch) < batch_size:
                    print("📭 Reached end of alternative names")
                    break
        
        except KeyboardInterrupt:
            print(f"🛑 Interrupted at {len(all_alternative_names)} alternative names (offset: {offset})")
            raise
        
        # Save to file
        filename = os.path.join(self.dump_dir, 'all_alternative_names.json')
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(all_alternative_names, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Dumped {len(all_alternative_names)} alternative names to {filename}")
        return all_alternative_names
    
    async def dump_all_covers(self) -> List[Dict]:
        """Dump all covers from IGDB (with pagination)"""
        if self.file_exists_and_valid('all_covers.json'):
            print("🖼️ All covers already dumped, loading from file...")
            filename = os.path.join(self.dump_dir, 'all_covers.json')
            with open(filename, 'r', encoding='utf-8') as f:
                all_covers = json.load(f)
            print(f"✅ Loaded {len(all_covers)} covers from {filename}")
            return all_covers
        
        print("🖼️ Dumping all covers...")
        
        all_covers = []
        offset = 0
        batch_size = 500
        
        try:
            while True:
                # Check if we should stop
                if self.should_stop:
                    print(f"🛑 Stopping at {len(all_covers)} covers (offset: {offset})")
                    break
                
                print(f"📦 Fetching covers batch: offset={offset}, limit={batch_size}")
                
                query = f"""
                fields id,image_id,width,height,url,game_localization;
                limit {batch_size};
                offset {offset};
                """
                
                covers_batch = await self.make_request('covers', query)
                
                if not covers_batch:
                    print("📭 No more covers to fetch")
                    break
                
                all_covers.extend(covers_batch)
                offset += batch_size
                
                print(f"✅ Fetched {len(covers_batch)} covers (total: {len(all_covers)})")
                
                # If we got fewer covers than requested, we've reached the end
                if len(covers_batch) < batch_size:
                    print("📭 Reached end of covers")
                    break
        
        except KeyboardInterrupt:
            print(f"🛑 Interrupted at {len(all_covers)} covers (offset: {offset})")
            raise
        
        # Save to file
        filename = os.path.join(self.dump_dir, 'all_covers.json')
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(all_covers, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Dumped {len(all_covers)} covers to {filename}")
        return all_covers
    
    async def dump_all_screenshots(self) -> List[Dict]:
        """Dump all screenshots from IGDB (with pagination)"""
        if self.file_exists_and_valid('all_screenshots.json'):
            print("📸 All screenshots already dumped, loading from file...")
            filename = os.path.join(self.dump_dir, 'all_screenshots.json')
            with open(filename, 'r', encoding='utf-8') as f:
                all_screenshots = json.load(f)
            print(f"✅ Loaded {len(all_screenshots)} screenshots from {filename}")
            return all_screenshots
        
        print("📸 Dumping all screenshots...")
        
        all_screenshots = []
        offset = 0
        batch_size = 500
        
        try:
            while True:
                # Check if we should stop
                if self.should_stop:
                    print(f"🛑 Stopping at {len(all_screenshots)} screenshots (offset: {offset})")
                    break
                
                print(f"📦 Fetching screenshots batch: offset={offset}, limit={batch_size}")
                
                query = f"""
                fields id,image_id,width,height,url;
                limit {batch_size};
                offset {offset};
                """
                
                screenshots_batch = await self.make_request('screenshots', query)
                
                if not screenshots_batch:
                    print("📭 No more screenshots to fetch")
                    break
                
                all_screenshots.extend(screenshots_batch)
                offset += batch_size
                
                print(f"✅ Fetched {len(screenshots_batch)} screenshots (total: {len(all_screenshots)})")
                
                # If we got fewer screenshots than requested, we've reached the end
                if len(screenshots_batch) < batch_size:
                    print("📭 Reached end of screenshots")
                    break
        
        except KeyboardInterrupt:
            print(f"🛑 Interrupted at {len(all_screenshots)} screenshots (offset: {offset})")
            raise
        
        # Save to file
        filename = os.path.join(self.dump_dir, 'all_screenshots.json')
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(all_screenshots, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Dumped {len(all_screenshots)} screenshots to {filename}")
        return all_screenshots
    
    async def dump_all_artworks(self) -> List[Dict]:
        """Dump all artworks from IGDB (with pagination)"""
        if self.file_exists_and_valid('all_artworks.json'):
            print("🎨 All artworks already dumped, loading from file...")
            filename = os.path.join(self.dump_dir, 'all_artworks.json')
            with open(filename, 'r', encoding='utf-8') as f:
                all_artworks = json.load(f)
            print(f"✅ Loaded {len(all_artworks)} artworks from {filename}")
            return all_artworks
        
        print("🎨 Dumping all artworks...")
        
        all_artworks = []
        offset = 0
        batch_size = 500
        
        try:
            while True:
                # Check if we should stop
                if self.should_stop:
                    print(f"🛑 Stopping at {len(all_artworks)} artworks (offset: {offset})")
                    break
                
                print(f"📦 Fetching artworks batch: offset={offset}, limit={batch_size}")
                
                query = f"""
                fields id,image_id,width,height,url,artwork_type;
                limit {batch_size};
                offset {offset};
                """
                
                artworks_batch = await self.make_request('artworks', query)
                
                if not artworks_batch:
                    print("📭 No more artworks to fetch")
                    break
                
                all_artworks.extend(artworks_batch)
                offset += batch_size
                
                print(f"✅ Fetched {len(artworks_batch)} artworks (total: {len(all_artworks)})")
                
                # If we got fewer artworks than requested, we've reached the end
                if len(artworks_batch) < batch_size:
                    print("📭 Reached end of artworks")
                    break
        
        except KeyboardInterrupt:
            print(f"🛑 Interrupted at {len(all_artworks)} artworks (offset: {offset})")
            raise
        
        # Save to file
        filename = os.path.join(self.dump_dir, 'all_artworks.json')
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(all_artworks, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Dumped {len(all_artworks)} artworks to {filename}")
        return all_artworks

    async def dump_videos(self, game_ids: List[int]) -> List[Dict]:
        """Dump videos for specific games"""
        if not game_ids:
            return []
        
        print(f"🎬 Dumping videos for {len(game_ids)} games...")
        
        all_videos = []
        batch_size = 500
        
        try:
            for i in range(0, len(game_ids), batch_size):
                # Check if we should stop
                if self.should_stop:
                    print(f"🛑 Stopping at {len(all_videos)} videos")
                    break
                
                batch_ids = game_ids[i:i + batch_size]
                print(f"📦 Fetching videos for games batch: {len(batch_ids)} games")
                
                query = f"""
                fields id,game,name,video_id;
                where game = ({','.join(map(str, batch_ids))});
                limit 500;
                """
                
                videos_batch = await self.make_request('game_videos', query)
                
                if videos_batch:
                    all_videos.extend(videos_batch)
                    print(f"✅ Fetched {len(videos_batch)} videos (total: {len(all_videos)})")
        
        except KeyboardInterrupt:
            print(f"🛑 Interrupted at {len(all_videos)} videos")
            raise
        
        return all_videos

    async def dump_all_videos(self) -> List[Dict]:
        """Dump all videos from IGDB (with pagination)"""
        if self.file_exists_and_valid('all_videos.json'):
            print("🎬 All videos already dumped, loading from file...")
            filename = os.path.join(self.dump_dir, 'all_videos.json')
            with open(filename, 'r', encoding='utf-8') as f:
                all_videos = json.load(f)
            print(f"✅ Loaded {len(all_videos)} videos from {filename}")
            return all_videos
        
        print("🎬 Dumping all videos...")
        
        all_videos = []
        offset = 0
        batch_size = 500
        
        try:
            while True:
                # Check if we should stop
                if self.should_stop:
                    print(f"🛑 Stopping at {len(all_videos)} videos (offset: {offset})")
                    break
                
                print(f"📦 Fetching videos batch: offset={offset}, limit={batch_size}")
                
                query = f"""
                fields id,game,name,video_id;
                limit {batch_size};
                offset {offset};
                """
                
                videos_batch = await self.make_request('game_videos', query)
                
                if not videos_batch:
                    print("📭 No more videos to fetch")
                    break
                
                all_videos.extend(videos_batch)
                offset += batch_size
                
                print(f"✅ Fetched {len(videos_batch)} videos (total: {len(all_videos)})")
                
                # If we got fewer videos than requested, we've reached the end
                if len(videos_batch) < batch_size:
                    print("📭 Reached end of videos")
                    break
        
        except KeyboardInterrupt:
            print(f"🛑 Interrupted at {len(all_videos)} videos (offset: {offset})")
            raise
        
        # Save to file
        filename = os.path.join(self.dump_dir, 'all_videos.json')
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(all_videos, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Dumped {len(all_videos)} videos to {filename}")
        return all_videos
    
    async def build_igdb_json(self, games: List[Dict], covers: List[Dict], screenshots: List[Dict], artworks: List[Dict], videos: List[Dict], companies: List[Dict], genres: List[Dict]) -> Dict[int, Dict]:
        """Build consolidated igdb.json with game ID as key and resolved media references"""
        print("🔧 Building consolidated igdb.json...")
        
        # Create lookup dictionaries for media
        covers_lookup = {cover['id']: cover['image_id'] for cover in covers if 'id' in cover and 'image_id' in cover}
        screenshots_lookup = {screenshot['id']: screenshot['image_id'] for screenshot in screenshots if 'id' in screenshot and 'image_id' in screenshot}
        artworks_lookup = {artwork['id']: artwork['image_id'] for artwork in artworks if 'id' in artwork and 'image_id' in artwork}
        
        # Create separate lookup for logos (artwork_type = 7 only) and fanart (all other types)
        # Keep full artwork data including height and width
        logos_lookup = {artwork['id']: artwork for artwork in artworks if 'id' in artwork and 'image_id' in artwork and artwork.get('artwork_type') == 7}
        fanart_lookup = {artwork['id']: artwork for artwork in artworks if 'id' in artwork and 'image_id' in artwork and artwork.get('artwork_type') != 7 and artwork.get('width', 0) > artwork.get('height', 0)}
        
        # Create videos lookup by game ID
        videos_lookup = {}
        for video in videos:
            if 'game' in video and 'video_id' in video:
                game_id = video['game']
                if game_id not in videos_lookup:
                    videos_lookup[game_id] = []
                videos_lookup[game_id].append({
                    'name': video.get('name', ''),
                    'video_id': video['video_id']
                })
        
        # Create companies lookup (id => name)
        companies_lookup = {company['id']: company['name'] for company in companies if 'id' in company and 'name' in company}
        
        # Create genres lookup (id => name)
        genres_lookup = {genre['id']: genre['name'] for genre in genres if 'id' in genre and 'name' in genre}
        
        # Create reverse mapping from companies to games
        # published: [game_id1, game_id2, ...] -> game_id1: [company_id], game_id2: [company_id]
        publishers_by_game = {}
        developers_by_game = {}
        
        for company in companies:
            company_id = company.get('id')
            if not company_id:
                continue
                
            # Map published games to this company
            if 'published' in company and company['published']:
                for game_id in company['published']:
                    if game_id not in publishers_by_game:
                        publishers_by_game[game_id] = []
                    publishers_by_game[game_id].append(company_id)
            
            # Map developed games to this company
            if 'developed' in company and company['developed']:
                for game_id in company['developed']:
                    if game_id not in developers_by_game:
                        developers_by_game[game_id] = []
                    developers_by_game[game_id].append(company_id)
        
        print(f"📊 Created lookups: {len(covers_lookup)} covers, {len(screenshots_lookup)} screenshots, {len(artworks_lookup)} total artworks ({len(fanart_lookup)} fanart landscape, {len(logos_lookup)} logos type 7), {len(videos_lookup)} games with videos, {len(companies_lookup)} companies, {len(genres_lookup)} genres")
        print(f"📊 Created reverse mappings: {len(publishers_by_game)} games with publishers, {len(developers_by_game)} games with developers")
        
        # Build consolidated games dictionary
        igdb_data = {}
        
        for game in games:
            if 'id' not in game:
                continue
                
            game_id = game['id']
            
            # Create game entry without unnecessary fields
            excluded_fields = ['similar_games', 'websites', 'age_ratings', 'external_games', 'url', 'player_perspectives', 'game_modes', 'game_engines', 'release_dates', 'alternative_names', 'id', 'involved_companies']
            game_entry = {k: v for k, v in game.items() if k not in excluded_fields}
            
            # Resolve cover reference
            if 'cover' in game_entry and game_entry['cover']:
                cover_id = game_entry['cover']
                if cover_id in covers_lookup:
                    game_entry['cover'] = covers_lookup[cover_id]
                else:
                    # Keep original ID if not found in lookup
                    pass
            
            # Resolve screenshots references
            if 'screenshots' in game_entry and game_entry['screenshots']:
                resolved_screenshots = []
                for screenshot_id in game_entry['screenshots']:
                    if screenshot_id in screenshots_lookup:
                        resolved_screenshots.append(screenshots_lookup[screenshot_id])
                    else:
                        # Keep original ID if not found in lookup
                        resolved_screenshots.append(screenshot_id)
                game_entry['screenshots'] = resolved_screenshots
            
            # Resolve artworks references and separate logos from fanart
            if 'artworks' in game_entry and game_entry['artworks']:
                resolved_artworks = []
                resolved_logos = []
                
                # Process each artwork and separate logos from fanart
                for artwork_id in game_entry['artworks']:
                    if artwork_id in logos_lookup:
                        # This is a logo - add full logo data to logos list
                        logo_data = logos_lookup[artwork_id]
                        resolved_logos.append({
                            'image_id': logo_data['image_id'],
                            'width': logo_data.get('width'),
                            'height': logo_data.get('height'),
                            'artwork_type': logo_data.get('artwork_type')
                        })
                    elif artwork_id in fanart_lookup:
                        # This is fanart (landscape only) - add full fanart data to artworks list
                        fanart_data = fanart_lookup[artwork_id]
                        resolved_artworks.append({
                            'image_id': fanart_data['image_id'],
                            'width': fanart_data.get('width'),
                            'height': fanart_data.get('height'),
                            'artwork_type': fanart_data.get('artwork_type')
                        })
                    elif artwork_id in artworks_lookup:
                        # Fallback: if not in specific lookups, add to artworks (just image_id)
                        resolved_artworks.append(artworks_lookup[artwork_id])
                    else:
                        # Keep original ID if not found in lookup
                        resolved_artworks.append(artwork_id)
                
                # Update the game entry with separated media
                game_entry['artworks'] = resolved_artworks
                if resolved_logos:
                    game_entry['logos'] = resolved_logos
            
            # Add videos for this game
            if game_id in videos_lookup:
                game_entry['videos'] = videos_lookup[game_id]
            
            # Add publisher and developer IDs using reverse mapping from companies
            if game_id in publishers_by_game:
                publishers = publishers_by_game[game_id]
                game_entry['publisher'] = publishers[0] if len(publishers) == 1 else publishers
            
            if game_id in developers_by_game:
                developers = developers_by_game[game_id]
                game_entry['developer'] = developers[0] if len(developers) == 1 else developers
            
            igdb_data[game_id] = game_entry
        
        # Save consolidated file in the same directory as other dump files
        output_file = os.path.join(self.dump_dir, 'igdb.json')
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(igdb_data, f, indent=2, ensure_ascii=False)
        
        # Also save as pickle for faster loading (in parent directory)
        pickle_file = os.path.join(os.path.dirname(self.dump_dir), 'igdb_db.pkl')
        with open(pickle_file, 'wb') as f:
            pickle.dump(igdb_data, f)
        
        # Save companies lookup as pickle for faster loading
        companies_pickle_file = os.path.join(os.path.dirname(self.dump_dir), 'igdb_companies.pkl')
        with open(companies_pickle_file, 'wb') as f:
            pickle.dump(companies_lookup, f)
        
        # Save genres lookup as pickle for faster loading
        genres_pickle_file = os.path.join(os.path.dirname(self.dump_dir), 'igdb_genres.pkl')
        with open(genres_pickle_file, 'wb') as f:
            pickle.dump(genres_lookup, f)
        
        print(f"✅ Built consolidated igdb.json with {len(igdb_data)} games at {output_file}")
        print(f"✅ Saved pickle version at {pickle_file}")
        print(f"✅ Saved companies pickle at {companies_pickle_file}")
        print(f"✅ Saved genres pickle at {genres_pickle_file}")
        return igdb_data

    async def build_platform_partition_index(self, games: List[Dict], alternative_names: List[Dict]) -> Dict:
        """Build platform-partitioned index: [platformid][firstletter][normalizedname] = gameid"""
        print("🔧 Building platform-partitioned index...")
        
        # Create lookup for alternative names by game_id
        alt_names_lookup = {}
        for alt_name in alternative_names:
            game_id = alt_name.get('game')
            if game_id:
                if game_id not in alt_names_lookup:
                    alt_names_lookup[game_id] = []
                alt_names_lookup[game_id].append(alt_name.get('name', ''))
        
        print(f"📊 Created alternative names lookup for {len(alt_names_lookup)} games")
        
        # Build platform partition index
        platform_index = {}
        processed_games = 0
        
        for game in games:
            if 'id' not in game:
                continue
                
            game_id = game['id']
            game_name = game.get('name', '')
            platforms = game.get('platforms', [])
            
            # Skip games without platforms or name
            if not platforms or not game_name:
                continue
            
            # Get all names for this game (main name + alternative names)
            all_names = [game_name]
            if game_id in alt_names_lookup:
                all_names.extend(alt_names_lookup[game_id])
            
            # Process each platform
            for platform_id in platforms:
                if platform_id not in platform_index:
                    platform_index[platform_id] = {}
                
                # Process each name (main + alternatives)
                for name in all_names:
                    if not name or not name.strip():
                        continue
                    
                    # Normalize the name
                    normalized_name = normalize_game_name(name, remove_paranthesis=True, remove_articles=True)
                    if not normalized_name:
                        continue
                    
                    # Get first character for partitioning
                    first_char = normalized_name[0] if normalized_name else 'other'
                    if first_char not in platform_index[platform_id]:
                        platform_index[platform_id][first_char] = {}
                    
                    # Store the mapping: normalized_name -> game_id
                    platform_index[platform_id][first_char][normalized_name] = game_id
            
            processed_games += 1
            if processed_games % 1000 == 0:
                print(f"📊 Processed {processed_games} games for platform index...")
        
        # Save the platform partition index
        output_file = os.path.join(self.dump_dir, 'platform_partition_index.json')
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(platform_index, f, indent=2, ensure_ascii=False)
        
        # Also save as pickle for faster loading (in parent directory)
        pickle_file = os.path.join(os.path.dirname(self.dump_dir), 'igdb_platform_partition_index.pkl')
        with open(pickle_file, 'wb') as f:
            pickle.dump(platform_index, f)
        
        # Calculate statistics
        total_platforms = len(platform_index)
        total_partitions = sum(len(platform_data) for platform_data in platform_index.values())
        total_entries = sum(
            len(partition_data) 
            for platform_data in platform_index.values() 
            for partition_data in platform_data.values()
        )
        
        print(f"✅ Built platform partition index:")
        print(f"   📊 {total_platforms} platforms")
        print(f"   📊 {total_partitions} partitions")
        print(f"   📊 {total_entries} total entries")
        print(f"   📁 Saved JSON to: {output_file}")
        print(f"   📁 Saved pickle to: {pickle_file}")
        
        return platform_index
    
    async def create_dump_summary(self, stats: Dict[str, Any]):
        """Create a summary file with dump statistics"""
        summary = {
            'dump_timestamp': datetime.now().isoformat(),
            'igdb_client_id': self.client_id,
            'statistics': stats,
            'files_created': [
                'platforms.json',
                'genres.json', 
                'game_modes.json',
                'player_perspectives.json',
                'companies.json',
                'games.json',
                'covers.json',
                'screenshots.json',
                'artworks.json'
            ]
        }
        
        filename = os.path.join(self.dump_dir, 'dump_summary.json')
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Created dump summary: {filename}")
    
    async def close(self):
        """Close the async client"""
        if self.async_client:
            await self.async_client.aclose()

async def main():
    """Main function to run the IGDB dump"""
    parser = argparse.ArgumentParser(description='Dump IGDB database to local JSON files')
    parser.add_argument('--force', action='store_true', 
                       help='Force redump of existing files')
    args = parser.parse_args()
    
    dumper = IGDBDumper(force=args.force)
    
    try:
        await dumper.initialize()
        
        # Dump basic data (will skip if files already exist unless --force is used)
        platforms = await dumper.dump_platforms()
        genres = await dumper.dump_genres()
        game_modes = await dumper.dump_game_modes()
        player_perspectives = await dumper.dump_player_perspectives()
        companies = await dumper.dump_companies()
        
        # Dump all games from IGDB database (with resume support)
        games = await dumper.dump_games()
        
        # Extract game IDs for media
        game_ids = [game['id'] for game in games if 'id' in game]
        
        # Dump all media from IGDB database (only if games are complete)
        if not dumper.should_stop:
            covers = await dumper.dump_all_covers()
            screenshots = await dumper.dump_all_screenshots()
            artworks = await dumper.dump_all_artworks()
            videos = await dumper.dump_all_videos()
            all_alternative_names = await dumper.dump_all_alternative_names()
            
            # Build consolidated igdb.json
            if not dumper.should_stop:
                igdb_data = await dumper.build_igdb_json(games, covers, screenshots, artworks, videos, companies, genres)
                
                # Build platform partition index
                if not dumper.should_stop:
                    platform_index = await dumper.build_platform_partition_index(games, all_alternative_names)
        else:
            print("🛑 Skipping media dump due to stop signal")
            covers, screenshots, artworks, videos, all_alternative_names = [], [], [], [], []
        
        # Create summary
        stats = {
            'platforms': len(platforms),
            'genres': len(genres),
            'game_modes': len(game_modes),
            'player_perspectives': len(player_perspectives),
            'companies': len(companies),
            'games': len(games),
            'covers': len(covers),
            'screenshots': len(screenshots),
            'artworks': len(artworks),
            'videos': len(videos),
            'alternative_names': len(all_alternative_names),
            'consolidated_games': len(igdb_data) if 'igdb_data' in locals() else 0,
            'platform_index_platforms': len(platform_index) if 'platform_index' in locals() else 0,
            'platform_index_entries': sum(
                len(partition_data) 
                for platform_data in platform_index.values() 
                for partition_data in platform_data.values()
            ) if 'platform_index' in locals() else 0
        }
        
        await dumper.create_dump_summary(stats)
        
        if dumper.should_stop:
            print("\n🛑 IGDB dump stopped by user")
            print("💡 To resume, run the script again - it will continue from where it left off")
        else:
            print("\n🎉 IGDB dump completed successfully!")
            dumper.clear_progress()  # Clear progress file on successful completion
        
        print(f"📊 Statistics:")
        for key, value in stats.items():
            print(f"   {key}: {value}")
        print(f"📁 Files saved to: {dumper.dump_dir}")
        
    except KeyboardInterrupt:
        print("\n🛑 IGDB dump interrupted by user")
        print("💡 To resume, run the script again - it will continue from where it left off")
    except Exception as e:
        print(f"❌ Error during dump: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await dumper.close()

if __name__ == '__main__':
    asyncio.run(main())
