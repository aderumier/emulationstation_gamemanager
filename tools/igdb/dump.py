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
from datetime import datetime
from typing import Dict, List, Any, Optional

class IGDBDumper:
    def __init__(self):
        # Load credentials from credentials.json
        self.client_id = None
        self.client_secret = None
        self.access_token = None
        self.async_client = None
        self.dump_dir = "var/db/igdb/dump"
        
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
        """Dump all companies from IGDB"""
        print("🏢 Dumping companies...")
        
        query = """
        fields id,name,slug,description,country,start_date,logo,url,websites;
        limit 500;
        """
        
        companies = await self.make_request('companies', query)
        
        # Save to file
        filename = os.path.join(self.dump_dir, 'companies.json')
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(companies, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Dumped {len(companies)} companies to {filename}")
        return companies
    
    async def dump_games_batch(self, offset: int = 0, limit: int = 500) -> List[Dict]:
        """Dump a batch of games from IGDB"""
        query = f"""
        fields id,name,slug,summary,storyline,first_release_date,rating,rating_count,total_rating,total_rating_count,aggregated_rating,aggregated_rating_count,genres,platforms,game_modes,player_perspectives,cover,screenshots,artworks,websites,url,collection,franchise,game_engines,age_ratings,release_dates,alternative_names,external_games,dlcs,expansions,standalone_expansions,remakes,remasters,similar_games,version_parent,game_localizations;
        limit {limit};
        offset {offset};
        """
        
        games = await self.make_request('games', query)
        return games
    
    async def dump_games(self, max_games: Optional[int] = None) -> List[Dict]:
        """Dump all games from IGDB (with pagination and resume support)"""
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
        print(f"🎨 Dumping artworks for {len(game_ids)} games...")
        
        # Process in batches
        batch_size = 100
        all_artworks = []
        
        for i in range(0, len(game_ids), batch_size):
            batch_ids = game_ids[i:i + batch_size]
            ids_str = ','.join(map(str, batch_ids))
            
            query = f"""
            fields id,image_id,width,height,url;
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
    dumper = IGDBDumper()
    
    try:
        await dumper.initialize()
        
        # Check if we're resuming
        progress = dumper.load_progress()
        if progress.get('interrupted'):
            print("🔄 Resuming interrupted dump...")
        
        # Dump basic data (only if not already done)
        if not progress.get('platforms_done'):
            platforms = await dumper.dump_platforms()
            dumper.save_progress({**progress, 'platforms_done': True})
        else:
            print("📱 Platforms already dumped, skipping...")
            platforms = []
        
        if not progress.get('genres_done'):
            genres = await dumper.dump_genres()
            dumper.save_progress({**progress, 'genres_done': True})
        else:
            print("🎭 Genres already dumped, skipping...")
            genres = []
        
        if not progress.get('game_modes_done'):
            game_modes = await dumper.dump_game_modes()
            dumper.save_progress({**progress, 'game_modes_done': True})
        else:
            print("🎮 Game modes already dumped, skipping...")
            game_modes = []
        
        if not progress.get('player_perspectives_done'):
            player_perspectives = await dumper.dump_player_perspectives()
            dumper.save_progress({**progress, 'player_perspectives_done': True})
        else:
            print("👁️ Player perspectives already dumped, skipping...")
            player_perspectives = []
        
        if not progress.get('companies_done'):
            companies = await dumper.dump_companies()
            dumper.save_progress({**progress, 'companies_done': True})
        else:
            print("🏢 Companies already dumped, skipping...")
            companies = []
        
        # Dump all games from IGDB database (with resume support)
        games = await dumper.dump_games()
        
        # Extract game IDs for media
        game_ids = [game['id'] for game in games if 'id' in game]
        
        # Dump media for games (only if games are complete)
        if not dumper.should_stop:
            covers = await dumper.dump_covers(game_ids)
            screenshots = await dumper.dump_screenshots(game_ids)
            artworks = await dumper.dump_artworks(game_ids)
        else:
            print("🛑 Skipping media dump due to stop signal")
            covers, screenshots, artworks = [], [], []
        
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
            'artworks': len(artworks)
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
