#!/usr/bin/env python3
"""
PlayStation Store Web Scraper
Scrapes game data from https://store.playstation.com/en-ca/pages/browse/
Creates a JSON database with game information
"""

import requests
from bs4 import BeautifulSoup
import json
import time
import re
from urllib.parse import urljoin, urlparse, parse_qs
import sys
import random
import os
from typing import Dict, List, Optional, Tuple
from datetime import datetime

class PlayStationStoreScraper:
    def __init__(self):
        self.base_url = "https://store.playstation.com"
        self.locale = "en-ca"
        self.games_db = {}
        self.session = requests.Session()
        
        # Progress tracking
        self.progress_file = "scraper_progress.json"
        self.db_file = "playstation_store_db.json"
        self.progress_data = {
            "current_page": 1,
            "max_page": 417,  # Default, will be detected dynamically
            "processed_games": set(),
            "total_games_collected": 0,
            "last_run_timestamp": None,
            "status": "not_started"  # not_started, running, completed, interrupted
        }
        
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
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
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
                    if self.progress_data.get('max_page'):
                        print(f"✅ Max page detected: {self.progress_data['max_page']}")
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
    
    def clean_image_url(self, url: str) -> Optional[str]:
        """Remove query parameters from image URLs"""
        if not url:
            return None
        try:
            # Parse URL and remove query parameters
            parsed = urlparse(url)
            # Reconstruct URL without query parameters
            clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            return clean_url
        except Exception as e:
            print(f"⚠️  Error cleaning image URL '{url}': {e}")
            return url  # Return original if cleaning fails
    
    def normalize_date(self, date_string: str) -> Optional[str]:
        """Convert '9/6/2024' to '06-09-2024' (dd-mm-yyyy)"""
        if not date_string:
            return None
        try:
            # Try M/D/YYYY format
            dt = datetime.strptime(date_string.strip(), "%m/%d/%Y")
            # Format as dd-mm-yyyy
            return dt.strftime("%d-%m-%Y")
        except ValueError:
            try:
                # Try D/M/YYYY format
                dt = datetime.strptime(date_string.strip(), "%d/%m/%Y")
                return dt.strftime("%d-%m-%Y")
            except ValueError:
                try:
                    # Try YYYY-MM-DD format
                    dt = datetime.strptime(date_string.strip(), "%Y-%m-%d")
                    return dt.strftime("%d-%m-%Y")
                except ValueError:
                    print(f"⚠️  Could not parse date '{date_string}'")
                    return None
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
    
    def find_max_page(self) -> int:
        """Dynamically find the maximum page number"""
        print("🔍 Detecting maximum page number...")
        
        # Start from a known high page and work backwards, or start from 1 and go up
        # Strategy: Check pagination links on first page, or try pages until 404/empty
        
        # First, try to find pagination on page 1
        browse_url = f"{self.base_url}/{self.locale}/pages/browse/1"
        soup = self.get_browse_page(1)
        if soup:
            # Look for pagination links
            pagination_links = soup.find_all('a', href=re.compile(r'/pages/browse/\d+'))
            max_page_found = 1
            
            for link in pagination_links:
                href = link.get('href', '')
                match = re.search(r'/pages/browse/(\d+)', href)
                if match:
                    page_num = int(match.group(1))
                    if page_num > max_page_found:
                        max_page_found = page_num
            
            if max_page_found > 1:
                print(f"✅ Found max page from pagination: {max_page_found}")
                return max_page_found
        
        # Fallback: Try pages incrementally until we get 404 or empty page
        print("🔍 Pagination not found, trying pages incrementally...")
        test_page = 400  # Start from a reasonable high number
        last_valid = 1
        
        while test_page <= 500:  # Reasonable upper limit
            browse_url = f"{self.base_url}/{self.locale}/pages/browse/{test_page}"
            soup = self.get_browse_page(test_page)
            if soup:
                # Check if page has game cards
                game_cards = self.extract_game_cards(soup)
                if game_cards and len(game_cards) > 0:
                    last_valid = test_page
                    test_page += 50  # Jump by 50
                else:
                    # Empty page, go back and search more carefully
                    break
            else:
                # 404 or error, go back
                break
        
        # Binary search between last_valid and test_page
        if test_page > last_valid + 1:
            low = last_valid
            high = test_page
            while low < high - 1:
                mid = (low + high) // 2
                soup = self.get_browse_page(mid)
                if soup:
                    game_cards = self.extract_game_cards(soup)
                    if game_cards and len(game_cards) > 0:
                        low = mid
                    else:
                        high = mid
                else:
                    high = mid
            last_valid = low
        
        print(f"✅ Detected max page: {last_valid}")
        return last_valid
    
    def get_browse_page(self, page_number: int) -> Optional[BeautifulSoup]:
        """Fetch and parse browse page HTML"""
        browse_url = f"{self.base_url}/{self.locale}/pages/browse/{page_number}"
        
        try:
            # Rotate user agent
            self._rotate_user_agent()
            
            print(f"📄 Fetching browse page {page_number}...")
            response = self.session.get(browse_url, timeout=30)
            
            if response.status_code == 404:
                return None
            
            response.raise_for_status()
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                return soup
            else:
                print(f"⚠️  Unexpected status code: {response.status_code}")
                return None
        except requests.exceptions.RequestException as e:
            print(f"❌ Error fetching browse page {page_number}: {e}")
            # Rotate user agent on error
            self._rotate_user_agent()
            return None
    
    def extract_game_cards(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract game cards from browse page"""
        game_cards = []
        
        try:
            # Find all <li> elements that contain game cards
            # Cards have class containing psw-l-w-1/
            card_elements = soup.find_all('li', class_=re.compile(r'psw-l-w-1/'))
            
            for card in card_elements:
                game_data = {}
                
                # Extract game name
                name_elem = card.find('span', id='product-name')
                if not name_elem:
                    name_elem = card.find('span', attrs={'data-qa': re.compile(r'product-name')})
                if name_elem:
                    game_data['name'] = name_elem.get_text(strip=True)
                
                # Extract game ID and URL from <a> tag
                link_elem = card.find('a', href=re.compile(r'/concept/\d+'))
                if link_elem:
                    href = link_elem.get('href', '')
                    # Extract ID from href like /en-ca/concept/231761
                    match = re.search(r'/concept/(\d+)', href)
                    if match:
                        game_data['id'] = match.group(1)
                        # Build full URL
                        if href.startswith('/'):
                            game_data['url'] = f"{self.base_url}{href}"
                        else:
                            game_data['url'] = href
                
                # Extract boxfront image
                img_elem = card.find('img', attrs={'data-qa': re.compile(r'game-art.*image#image')})
                if img_elem:
                    img_src = img_elem.get('src', '')
                    if img_src:
                        game_data['boxfront'] = self.clean_image_url(img_src)
                
                # Only add if we have at least ID and name
                if game_data.get('id') and game_data.get('name'):
                    game_cards.append(game_data)
            
            return game_cards
        except Exception as e:
            print(f"⚠️  Error extracting game cards: {e}")
            return []
    
    def get_game_details(self, game_id: str) -> Optional[BeautifulSoup]:
        """Fetch and parse game detail page HTML"""
        game_url = f"{self.base_url}/{self.locale}/concept/{game_id}"
        
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
    
    def extract_fanart(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract fanart from hero image"""
        try:
            # Try multiple selectors for the hero image
            # First: exact data-qa match
            img_elem = soup.find('img', attrs={'data-qa': 'gameBackgroundImage#heroImage#image'})
            
            # Second: try with regex for partial match
            if not img_elem:
                img_elem = soup.find('img', attrs={'data-qa': re.compile(r'gameBackgroundImage.*heroImage.*image', re.I)})
            
            # Third: try finding by class or other attributes
            if not img_elem:
                # Look for images with "hero" or "background" in class or data attributes
                all_imgs = soup.find_all('img')
                for img in all_imgs:
                    data_qa = img.get('data-qa', '')
                    if 'hero' in data_qa.lower() or 'background' in data_qa.lower():
                        img_elem = img
                        break
            
            if img_elem:
                # Try src first
                img_src = img_elem.get('src', '')
                # If no src, try srcset
                if not img_src:
                    srcset = img_elem.get('srcset', '')
                    if srcset:
                        # Extract first URL from srcset
                        # Format: "url1 1x, url2 2x" or "url1, url2 2x"
                        first_url = srcset.split(',')[0].strip().split()[0]
                        img_src = first_url
                
                if img_src:
                    return self.clean_image_url(img_src)
                else:
                    print(f"🔧 DEBUG: Found fanart img element but no src/srcset")
            else:
                # Debug: check what images are available
                all_imgs = soup.find_all('img')
                hero_imgs = [img for img in all_imgs if 'hero' in img.get('data-qa', '').lower() or 'background' in img.get('data-qa', '').lower()]
                if hero_imgs:
                    print(f"🔧 DEBUG: Found {len(hero_imgs)} potential hero images but selector didn't match")
                    for img in hero_imgs[:3]:  # Show first 3
                        print(f"🔧 DEBUG:   data-qa: {img.get('data-qa', 'N/A')}, src: {img.get('src', 'N/A')[:80]}")
            
            return None
        except Exception as e:
            print(f"⚠️  Error extracting fanart: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def extract_rating(self, soup: BeautifulSoup) -> Optional[float]:
        """Extract and normalize rating (3.73/5 -> 0.746)"""
        try:
            # Find span with class="psw-sr-only" containing rating text
            rating_spans = soup.find_all('span', class_='psw-sr-only')
            for span in rating_spans:
                text = span.get_text(strip=True)
                # Look for pattern like "Average rating 3.73 stars out of 5 stars"
                match = re.search(r'Average rating\s+([\d.]+)\s+stars out of 5', text, re.I)
                if match:
                    rating_value = float(match.group(1))
                    return self.normalize_rating(rating_value)
            return None
        except Exception as e:
            print(f"⚠️  Error extracting rating: {e}")
            return None
    
    def extract_publisher(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract publisher from multiple possible locations"""
        try:
            # Try first location: <div data-qa="mfe-game-title#publisher">
            publisher_elem = soup.find('div', attrs={'data-qa': 'mfe-game-title#publisher'})
            if publisher_elem:
                publisher = publisher_elem.get_text(strip=True)
                if publisher:
                    return publisher
            
            # Try second location: <dd data-qa="gameInfo#releaseInformation#publisher-value">
            publisher_elem = soup.find('dd', attrs={'data-qa': 'gameInfo#releaseInformation#publisher-value'})
            if publisher_elem:
                publisher = publisher_elem.get_text(strip=True)
                if publisher:
                    return publisher
            
            return None
        except Exception as e:
            print(f"⚠️  Error extracting publisher: {e}")
            return None
    
    def extract_nbplayers(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract number of players (e.g., '1-2')"""
        try:
            # Find span with data-qa="mfe-compatibility-notices#notices#notice3#compatText"
            player_elem = soup.find('span', attrs={'data-qa': 'mfe-compatibility-notices#notices#notice3#compatText'})
            if player_elem:
                text = player_elem.get_text(strip=True)
                # Extract player count pattern like "1 - 2 players" or "1 players"
                match = re.search(r'(\d+)\s*-\s*(\d+)\s*players', text, re.I)
                if match:
                    return f"{match.group(1)}-{match.group(2)}"
                match = re.search(r'(\d+)\s*players?', text, re.I)
                if match:
                    return match.group(1)
            return None
        except Exception as e:
            print(f"⚠️  Error extracting nbplayers: {e}")
            return None
    
    def extract_release_date(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract and normalize release date"""
        try:
            # Find <dd data-qa="gameInfo#releaseInformation#releaseDate-value">
            date_elem = soup.find('dd', attrs={'data-qa': 'gameInfo#releaseInformation#releaseDate-value'})
            if date_elem:
                date_text = date_elem.get_text(strip=True)
                if date_text:
                    return self.normalize_date(date_text)
            return None
        except Exception as e:
            print(f"⚠️  Error extracting release date: {e}")
            return None
    
    def extract_description(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract description and convert HTML to text with newlines"""
        try:
            # Find <p data-qa="mfe-game-overview#description">
            desc_elem = soup.find('p', attrs={'data-qa': 'mfe-game-overview#description'})
            if desc_elem:
                # Convert <br> tags to newlines before getting text
                for br in desc_elem.find_all('br'):
                    br.replace_with('\n')
                
                # Get text with preserved newlines
                description = desc_elem.get_text(separator='\n', strip=True)
                
                # Clean up multiple consecutive newlines
                description = re.sub(r'\n{3,}', '\n\n', description)
                description = description.strip()
                
                return description if description else None
            return None
        except Exception as e:
            print(f"⚠️  Error extracting description: {e}")
            return None
    
    def scrape_game(self, game_data: Dict) -> Optional[Dict]:
        """Scrape a single game's details"""
        game_id = game_data.get('id')
        if not game_id:
            return None
        
        # Skip if already processed
        if game_id in self.progress_data['processed_games']:
            print(f"⏭️  Skipping game {game_id} (already processed)")
            return None
        
        # Fetch game details page
        soup = self.get_game_details(game_id)
        if not soup:
            print(f"❌ Failed to fetch game details for {game_id}")
            return None
        
        # Extract game information
        game_info = {
            'url': game_data.get('url', f"{self.base_url}/{self.locale}/concept/{game_id}"),
            'name': game_data.get('name', ''),
            'boxfront': game_data.get('boxfront'),
            'fanart': self.extract_fanart(soup),
            'rating': self.extract_rating(soup),
            'publisher': self.extract_publisher(soup),
            'nbplayers': self.extract_nbplayers(soup),
            'release_date': self.extract_release_date(soup),
            'description': self.extract_description(soup)
        }
        
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
            
            # Detect max page if not already set or if starting fresh
            if not self.progress_data.get('max_page') or not resume:
                self.progress_data['max_page'] = self.find_max_page()
                self.save_progress()
            
            max_page = self.progress_data['max_page']
            
            self.progress_data['status'] = 'running'
            total_games = 0
            
            # Determine starting page
            start_page = 1
            if resume and self.progress_data['current_page']:
                start_page = self.progress_data['current_page']
            
            # Process each page
            for page_num in range(start_page, max_page + 1):
                print(f"\n{'='*60}")
                print(f"📌 Processing page: {page_num}/{max_page}")
                print(f"{'='*60}")
                
                self.progress_data['current_page'] = page_num
                self.save_progress()
                
                # Get browse page
                soup = self.get_browse_page(page_num)
                if not soup:
                    print(f"⚠️  Failed to fetch page {page_num}, skipping")
                    time.sleep(2)  # Rate limiting
                    continue
                
                # Extract game cards
                game_cards = self.extract_game_cards(soup)
                if not game_cards:
                    print(f"⚠️  No games found on page {page_num}, skipping")
                    time.sleep(2)  # Rate limiting
                    continue
                
                print(f"✅ Found {len(game_cards)} games on page {page_num}")
                
                # Process each game
                for game_card in game_cards:
                    game_id = game_card.get('id')
                    if not game_id:
                        continue
                    
                    # Skip if already in database
                    if game_id in self.games_db:
                        print(f"⏭️  Skipping game {game_id} (already in database)")
                        self.progress_data['processed_games'].add(game_id)
                        continue
                    
                    # Scrape game details
                    game_info = self.scrape_game(game_card)
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
    scraper = PlayStationStoreScraper()
    
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
            print(f"   Max page: {scraper.progress_data.get('max_page', 'Not detected')}")
            print(f"   Games processed: {len(scraper.progress_data.get('processed_games', []))}")
            print(f"   Total games in DB: {len(scraper.games_db)}")
            if scraper.progress_data.get('last_run_timestamp'):
                last_run = datetime.fromtimestamp(scraper.progress_data['last_run_timestamp'])
                print(f"   Last run: {last_run}")
            return
    
    scraper.run_scraper(resume=resume)

if __name__ == "__main__":
    main()

