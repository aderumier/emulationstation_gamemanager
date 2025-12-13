#!/usr/bin/env python3
"""
Adventure Game Studio Web Scraper
Scrapes game data from https://www.adventuregamestudio.co.uk/play/search/
Creates a JSON database with game information
"""

import requests
from bs4 import BeautifulSoup
import json
import time
import re
from urllib.parse import urljoin
import sys
import random
import os
from typing import Dict, List, Optional, Tuple
from datetime import datetime

class AGSScraper:
    def __init__(self):
        self.base_url = "https://www.adventuregamestudio.co.uk"
        self.games_db = {}
        self.session = requests.Session()
        
        # Progress tracking
        self.progress_file = "scraper_progress.json"
        self.db_file = "ags_db.json"
        self.progress_data = {
            "current_page": 1,
            "processed_games": set(),
            "total_games_collected": 0,
            "last_run_timestamp": None,
            "status": "not_started"  # not_started, running, completed, interrupted
        }
        
        # Pages to process: 1 to 51
        self.max_page = 51
        
        # Realistic browser user agents
        self.user_agents = [
            # Chrome on Windows
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 11.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            
            # Chrome on macOS
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
            
            # Chrome on Linux
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
            
            # Firefox on Windows
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:132.0) Gecko/20100101 Firefox/132.0',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:131.0) Gecko/20100101 Firefox/131.0',
            
            # Firefox on macOS
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:132.0) Gecko/20100101 Firefox/132.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:131.0) Gecko/20100101 Firefox/131.0',
            
            # Firefox on Linux
            'Mozilla/5.0 (X11; Linux x86_64; rv:132.0) Gecko/20100101 Firefox/132.0',
            'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:132.0) Gecko/20100101 Firefox/132.0',
            
            # Safari on macOS
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Safari/605.1.15',
            
            # Edge on Windows
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0',
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
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Content-Type': 'application/json',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Origin': self.base_url,
            'Referer': f'{self.base_url}/play/search/&q=newest-releases:checked',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
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
                    print(f"✅ Loaded progress: {len(self.progress_data['processed_games'])} games already processed")
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
    
    def normalize_date(self, date_string: str) -> Optional[str]:
        """Convert '2025-03-21 04:02:55' to '21-03-2025'"""
        if not date_string:
            return None
        try:
            # Parse the date string
            dt = datetime.strptime(date_string, "%Y-%m-%d %H:%M:%S")
            # Format as dd-mm-yyyy
            return dt.strftime("%d-%m-%Y")
        except Exception as e:
            print(f"⚠️  Error normalizing date '{date_string}': {e}")
            return None
    
    def normalize_rating(self, rating) -> Optional[float]:
        """Convert 0-5 rating to 0-1 scale (divide by 5). Returns None if negative."""
        if rating is None:
            return None
        try:
            rating_float = float(rating)
            # Return None if rating is negative
            if rating_float < 0:
                return None
            # Normalize from 0-5 to 0-1
            normalized = rating_float / 5.0
            return round(normalized, 2)
        except Exception as e:
            print(f"⚠️  Error normalizing rating '{rating}': {e}")
            return None
    
    def get_game_list(self, page_number: int) -> Optional[List[Dict]]:
        """POST to search endpoint and parse JSON response"""
        search_url = f"{self.base_url}/site/mvc/services/game-search.php"
        
        payload = {
            "page-number": str(page_number),
            "mags-id": "0",
            "title-or-author": "",
            "sort": "5",
            "ags-award-winners": "1"
        }
        
        try:
            # Rotate user agent
            self._rotate_user_agent()
            
            print(f"📄 Fetching page {page_number}...")
            response = self.session.post(search_url, json=payload, timeout=30)
            response.raise_for_status()
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    # The response should contain a list of games
                    # Adjust based on actual response structure
                    if isinstance(data, dict):
                        # Try common keys
                        games = data.get('games', data.get('results', data.get('data', data.get('items', []))))
                        if not games:
                            # Try to find any list in the response
                            for key, value in data.items():
                                if isinstance(value, list):
                                    games = value
                                    break
                    elif isinstance(data, list):
                        games = data
                    else:
                        print(f"⚠️  Unexpected response format: {type(data)}")
                        return None
                    
                    print(f"✅ Found {len(games)} games on page {page_number}")
                    return games
                except json.JSONDecodeError as e:
                    print(f"❌ Error parsing JSON response: {e}")
                    print(f"Response text (first 500 chars): {response.text[:500]}")
                    return None
            else:
                print(f"⚠️  Unexpected status code: {response.status_code}")
                return None
        except requests.exceptions.RequestException as e:
            print(f"❌ Error fetching page {page_number}: {e}")
            # Rotate user agent on error
            self._rotate_user_agent()
            return None
    
    def get_game_details(self, pretty_game_url: str) -> Optional[BeautifulSoup]:
        """Fetch and parse game detail page HTML"""
        game_url = f"{self.base_url}/play/game/{pretty_game_url}"
        
        try:
            # Rotate user agent
            self._rotate_user_agent()
            
            print(f"📄 Fetching game details: {game_url}")
            response = self.session.get(game_url, timeout=30)
            response.raise_for_status()
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                return soup
            else:
                print(f"⚠️  Unexpected status code: {response.status_code}")
                return None
        except requests.exceptions.RequestException as e:
            print(f"❌ Error fetching game details: {e}")
            # Rotate user agent on error
            self._rotate_user_agent()
            return None
    
    def extract_developer(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract developer from HTML (after 'by' in h2)"""
        try:
            # Find h2 with game name and developer
            h2 = soup.find('h2')
            if not h2:
                return None
            
            # Format: <h2><em id="name">Game Name</em> by <a href="...">Developer</a></h2>
            h2_text = h2.get_text()
            if ' by ' not in h2_text.lower():
                return None
            
            # Find all links in h2
            links = h2.find_all('a')
            if not links:
                return None
            
            # Get the full text of h2 to find positions
            full_text = h2.get_text()
            by_pos = full_text.lower().find(' by ')
            
            if by_pos == -1:
                return None
            
            # Find which link comes after "by"
            for link in links:
                link_text = link.get_text(strip=True)
                if not link_text:
                    continue
                
                # Find position of this link's text in the full h2 text
                link_pos = full_text.lower().find(link_text.lower(), by_pos)
                
                # If link text appears after "by", this is likely the developer
                if link_pos > by_pos:
                    return link_text
            
            # Fallback: if no link found after "by", try the last link in h2
            if links:
                last_link = links[-1]
                developer = last_link.get_text(strip=True)
                if developer:
                    return developer
            
            return None
        except Exception as e:
            print(f"⚠️  Error extracting developer: {e}")
            return None
    
    def extract_images(self, soup: BeautifulSoup) -> Tuple[Optional[str], Optional[str]]:
        """Extract titleshot (first) and screenshot (second) from gallery"""
        titleshot = None
        screenshot = None
        
        try:
            # Find gallery container with data-dynamicel attribute
            gallery_container = soup.find('div', class_='inline-gallery-container')
            if not gallery_container:
                return None, None
            
            # Get the data-dynamicel attribute
            data_dynamicel = gallery_container.get('data-dynamicel')
            if not data_dynamicel:
                return None, None
            
            # Parse the JSON string (it's HTML-encoded)
            import html
            decoded = html.unescape(data_dynamicel)
            gallery_data = json.loads(decoded)
            
            # Extract images from the gallery data
            if isinstance(gallery_data, list) and len(gallery_data) > 0:
                # First image is titleshot
                first_image = gallery_data[0]
                if isinstance(first_image, dict) and 'src' in first_image:
                    src = first_image['src']
                    # Convert relative URL to absolute
                    if src.startswith('/'):
                        titleshot = urljoin(self.base_url, src)
                    else:
                        titleshot = src
                
                # Second image is screenshot
                if len(gallery_data) > 1:
                    second_image = gallery_data[1]
                    if isinstance(second_image, dict) and 'src' in second_image:
                        src = second_image['src']
                        # Convert relative URL to absolute
                        if src.startswith('/'):
                            screenshot = urljoin(self.base_url, src)
                        else:
                            screenshot = src
            
            return titleshot, screenshot
        except Exception as e:
            print(f"⚠️  Error extracting images: {e}")
            return None, None
    
    def extract_description(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract description from 'About' section, convert HTML to text"""
        try:
            # Find section with id="about"
            about_section = soup.find('section', id='about')
            if not about_section:
                return None
            
            # Find all <p> tags in the about section
            paragraphs = about_section.find_all('p')
            if not paragraphs:
                return None
            
            # Extract text from all paragraphs
            description_parts = []
            for p in paragraphs:
                # Get text and convert <br> to newlines
                text = p.get_text(separator='\n', strip=True)
                # Also handle <br> tags explicitly
                for br in p.find_all('br'):
                    br.replace_with('\n')
                text = p.get_text(separator='\n', strip=True)
                if text:
                    description_parts.append(text)
            
            # Join all paragraphs with double newlines
            description = '\n\n'.join(description_parts)
            
            # Clean up extra whitespace
            description = re.sub(r'\n{3,}', '\n\n', description)
            description = description.strip()
            
            return description if description else None
        except Exception as e:
            print(f"⚠️  Error extracting description: {e}")
            return None
    
    def scrape_game(self, game_data: Dict) -> Optional[Dict]:
        """Scrape a single game's details"""
        game_id = str(game_data.get('id'))
        if not game_id:
            return None
        
        # Skip if already processed
        if game_id in self.progress_data['processed_games']:
            print(f"⏭️  Skipping game {game_id} (already processed)")
            return None
        
        pretty_game_url = game_data.get('pretty_game_url')
        if not pretty_game_url:
            print(f"⚠️  Game {game_id} has no pretty_game_url, skipping")
            return None
        
        # Fetch game details page
        soup = self.get_game_details(pretty_game_url)
        if not soup:
            print(f"❌ Failed to fetch game details for {game_id}")
            return None
        
        # Extract game information
        game_info = {
            'url': f"{self.base_url}/play/game/{pretty_game_url}",
            'name': game_data.get('name', ''),
            'developer': self.extract_developer(soup),
            'release_date': self.normalize_date(game_data.get('release_date')),
            'rating': self.normalize_rating(game_data.get('player_rating_avg')),
            'description': self.extract_description(soup)
        }
        
        # Extract images
        titleshot, screenshot = self.extract_images(soup)
        game_info['titleshot'] = titleshot
        game_info['screenshot'] = screenshot
        
        # Mark as processed
        self.progress_data['processed_games'].add(game_id)
        
        return game_info
    
    def run_scraper(self, resume: bool = True):
        """Main scraping loop"""
        try:
            # Load existing data
            if resume:
                self.load_progress()
            self.load_database()
            
            self.progress_data['status'] = 'running'
            total_games = 0
            
            # Determine starting page
            start_page = 1
            if resume and self.progress_data['current_page']:
                start_page = self.progress_data['current_page']
            
            # Process each page
            for page_num in range(start_page, self.max_page + 1):
                print(f"\n{'='*60}")
                print(f"📌 Processing page: {page_num}/{self.max_page}")
                print(f"{'='*60}")
                
                self.progress_data['current_page'] = page_num
                self.save_progress()
                
                # Get game list for this page
                games = self.get_game_list(page_num)
                if not games:
                    print(f"⚠️  No games found on page {page_num}, skipping")
                    time.sleep(2)  # Rate limiting
                    continue
                
                # Process each game
                for game_data in games:
                    game_id = str(game_data.get('id'))
                    if not game_id:
                        continue
                    
                    # Skip if already in database
                    if game_id in self.games_db:
                        print(f"⏭️  Skipping game {game_id} (already in database)")
                        self.progress_data['processed_games'].add(game_id)
                        continue
                    
                    # Scrape game details
                    game_info = self.scrape_game(game_data)
                    if game_info:
                        self.games_db[game_id] = game_info
                        total_games += 1
                        self.progress_data['total_games_collected'] = len(self.games_db)
                        
                        # Save after each game
                        self.save_database()
                        self.save_progress()
                        
                        print(f"✅ Scraped game {game_id}: {game_info.get('name', 'Unknown')}")
                    else:
                        print(f"❌ Failed to scrape game {game_id}")
                    
                    # Rate limiting between games
                    time.sleep(1)
                
                # Rate limiting between pages
                time.sleep(2)
            
            self.progress_data['status'] = 'completed'
            print(f"\n🎉 Scraping completed! Total games: {total_games}")
            
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
    scraper = AGSScraper()
    
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
            print(f"   Current page: {scraper.progress_data.get('current_page', 1)}")
            print(f"   Games processed: {len(scraper.progress_data.get('processed_games', []))}")
            print(f"   Total games in DB: {len(scraper.games_db)}")
            if scraper.progress_data.get('last_run_timestamp'):
                last_run = datetime.fromtimestamp(scraper.progress_data['last_run_timestamp'])
                print(f"   Last run: {last_run}")
            return
    
    scraper.run_scraper(resume=resume)

if __name__ == "__main__":
    main()

