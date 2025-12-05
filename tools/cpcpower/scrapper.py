#!/usr/bin/env python3
"""
CPC Power Web Scraper
Scrapes game data from https://www.cpc-power.com/index.php?page=database
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
import html
from typing import Dict, List, Optional, Tuple

def encode_html_entities(text: str) -> str:
    """Convert Unicode characters to HTML entities"""
    if not text:
        return text
    
    result = []
    for char in text:
        code = ord(char)
        # Handle special HTML characters first
        if char == '<':
            result.append('&lt;')
        elif char == '>':
            result.append('&gt;')
        elif char == '&':
            result.append('&amp;')
        elif char == '"':
            result.append('&quot;')
        elif char == "'":
            result.append('&#x27;')  # Use numeric entity for apostrophe
        # ASCII printable characters (32-126) are kept as-is (except those above)
        elif code < 128:
            result.append(char)
        else:
            # Convert Unicode to HTML entity (numeric entity)
            result.append(f"&#{code};")
    
    return ''.join(result)

class CPCPowerScraper:
    def __init__(self):
        self.base_url = "https://www.cpc-power.com"
        self.games_db = {}
        self.session = requests.Session()
        
        # Progress tracking
        self.progress_file = "scraper_progress.json"
        self.db_file = "cpcpower_db.json"
        self.progress_data = {
            "current_position": 1,
            "processed_games": set(),
            "total_games_collected": 0,
            "last_run_timestamp": None,
            "status": "not_started"  # not_started, running, completed, interrupted
        }
        
        # Positions to process: 1 to 993
        self.max_position = 993
        
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
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9,fr;q=0.8',
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
    
    def get_page(self, url: str, rotate_ua: bool = True) -> Optional[BeautifulSoup]:
        """Fetch a page and return BeautifulSoup object"""
        try:
            # Rotate user agent before each request
            if rotate_ua:
                ua = self._rotate_user_agent()
                if random.random() < 0.1:  # 10% chance to log user agent rotation
                    print(f"🔄 Using User-Agent: {ua[:60]}...")
            
            print(f"📄 Fetching: {url}")
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            if response.status_code == 200:
                # Try to detect encoding from response
                if response.encoding:
                    response.encoding = response.apparent_encoding or 'utf-8'
                soup = BeautifulSoup(response.content, 'html.parser', from_encoding=response.apparent_encoding or 'utf-8')
                return soup
            else:
                print(f"⚠️  Unexpected status code: {response.status_code}")
                return None
        except requests.exceptions.RequestException as e:
            print(f"❌ Error fetching {url}: {e}")
            # Rotate user agent on error
            if rotate_ua:
                self._rotate_user_agent()
            return None
    
    def check_url_exists(self, url: str) -> bool:
        """Check if a URL exists using HEAD request"""
        try:
            response = self.session.head(url, timeout=10, allow_redirects=True)
            # Check if status is OK and content type is an image
            if response.status_code == 200:
                content_type = response.headers.get('Content-Type', '').lower()
                if 'image' in content_type or 'application/octet-stream' in content_type:
                    return True
            return False
        except requests.exceptions.RequestException:
            return False
    
    def get_game_links_from_page(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract game information from a list page
        Returns a list of dictionaries with game data
        """
        games = []
        
        # Games are in div blocks with class "listingcart"
        game_blocks = soup.find_all('div', class_='listingcart')
        
        for block in game_blocks:
            game_data = {}
            
            # Extract game ID and URL from the link
            # Look for link with page=detail&num=<gameid>
            detail_link = block.find('a', href=re.compile(r'page=detail.*num=\d+'))
            if not detail_link:
                continue
            
            href = detail_link.get('href', '')
            # Extract game_id from num parameter
            num_match = re.search(r'num=(\d+)', href)
            if not num_match:
                continue
            
            game_id = num_match.group(1)
            game_data['game_id'] = game_id
            game_data['url'] = urljoin(self.base_url, href)
            
            # Extract game name from the link text within listingcarttitre div
            game_name = None
            title_div = block.find('div', class_='listingcarttitre')
            if title_div:
                title_link = title_div.find('a')
                if title_link:
                    game_name = title_link.get_text(strip=True)
            
            if not game_name:
                continue  # No fallback - skip if name not found
            
            game_data['name'] = game_name
            
            # Extract release_date and publisher from <h2 class="listebdd">
            release_date = None
            publisher = None
            h2 = block.find('h2', class_='listebdd')
            if h2:
                text = h2.get_text(strip=True)
                # Split on © character
                if '©' in text:
                    parts = text.split('©', 1)
                    year_part = parts[0].strip()
                    publisher = parts[1].strip() if len(parts) > 1 else None
                    
                    # Extract year (should be digits)
                    year_match = re.search(r'\d{4}', year_part)
                    if year_match:
                        release_date = f"01-01-{year_match.group(0)}"
            
            game_data['release_date'] = release_date
            game_data['publisher'] = publisher
            
            # Extract titleshot URL from img tag
            titleshot_url = None
            img = block.find('img', src=re.compile(r'extra_lire_fichier\.php'))
            if img:
                src = img.get('src')
                if src:
                    titleshot_url = urljoin(self.base_url, src)
            
            game_data['titleshot'] = titleshot_url
            
            games.append(game_data)
        
        return games
    
    def extract_game_info(self, soup: BeautifulSoup, game_url: str, game_id: str, 
                          release_date: Optional[str] = None, publisher: Optional[str] = None,
                          titleshot_url: Optional[str] = None) -> Optional[Dict]:
        """Extract game information from detail page"""
        game_info = {
            'url': game_url,
            'game_id': game_id,
            'name': None,  # Will be set from list page
            'release_date': release_date,
            'publisher': publisher,
            'genre': None,
            'nbplayer': None,
            'description': None,
            'tricks': None,
            'titleshot': titleshot_url,
            'screenshot': None,
            'map': None,
            'manual': None,
        }
        
        # Extract genre - first one if multiple available
        genre_section = soup.find('div', class_='soustitre', string=re.compile(r'- CATEGORIES -'))
        if genre_section:
            # Find the next sibling or look for links with "GAME ->" pattern
            genre_link = genre_section.find_next('a', href=re.compile(r'page=database.*cats='))
            if genre_link:
                genre_text = genre_link.get_text(strip=True)
                # Look for "GAME -> Genre" pattern
                genre_match = re.search(r'GAME\s*[-&gt;→]+\s*(.+)', genre_text)
                if genre_match:
                    genre = genre_match.group(1).strip()
                    # Remove leading arrows and whitespace
                    genre = re.sub(r'^[-&gt;→\s>]+', '', genre).strip()
                    game_info['genre'] = genre
        
        # Extract nbplayer - first line in paragraphe, only the integer
        nbplayer_section = soup.find('div', class_='soustitre', string=re.compile(r'- NUMBER OF PLAYERS -'))
        if nbplayer_section:
            paragraphe = nbplayer_section.find_next_sibling('div', class_='paragraphe')
            if paragraphe:
                text = paragraphe.get_text(strip=True)
                # Get first line
                first_line = text.split('\n')[0] if '\n' in text else text
                # Extract first number
                number_match = re.search(r'\d+', first_line)
                if number_match:
                    game_info['nbplayer'] = int(number_match.group(0))
        
        # Extract description
        desc_section = soup.find('div', class_='soustitre', string=re.compile(r'- DESCRIPTION -'))
        if desc_section:
            paragraphe = desc_section.find_next_sibling('div', class_='paragraphe')
            if paragraphe:
                # Get text content
                description_text = paragraphe.get_text(separator='\n', strip=True)
                # Encode HTML entities (Unicode to HTML entities)
                description_text = encode_html_entities(description_text)
                # Clean up excessive newlines
                description_text = re.sub(r'\n{3,}', '\n\n', description_text).strip()
                game_info['description'] = description_text if description_text else None
        
        # Extract tricks - keep full HTML
        tricks_section = soup.find('div', class_='soustitre', string=re.compile(r'- TRICKS -'))
        if tricks_section:
            # Look for div.chassefixe.paragraphe or div.paragraphe
            tricks_div = tricks_section.find_next_sibling('div', class_=lambda x: x and ('chassefixe' in x or 'paragraphe' in x))
            if not tricks_div:
                # Try to find any div.paragraphe after tricks section
                tricks_div = tricks_section.find_next('div', class_='paragraphe')
            
            if tricks_div:
                # Get inner HTML content
                tricks_html = tricks_div.decode_contents()
                # Encode HTML entities in the HTML content
                # We need to encode text content but preserve HTML tags
                # Parse the HTML and encode text nodes
                from bs4 import BeautifulSoup as BS
                from bs4 import NavigableString
                temp_soup = BS(tricks_html, 'html.parser')
                
                # Encode all text nodes to HTML entities
                def encode_text_nodes(element):
                    """Recursively encode text nodes to HTML entities"""
                    if not hasattr(element, 'children'):
                        return
                    
                    # Create a copy of children list to avoid modification during iteration
                    children = list(element.children)
                    for child in children:
                        # Check if it's a NavigableString (text node)
                        if isinstance(child, NavigableString):
                            text = str(child)
                            if text.strip():
                                # This is a text node - encode it
                                encoded_text = encode_html_entities(text)
                                # Replace with a new NavigableString that won't be escaped
                                new_node = NavigableString(encoded_text)
                                child.replace_with(new_node)
                        elif hasattr(child, 'children'):
                            # It's a tag - recurse into it
                            encode_text_nodes(child)
                
                encode_text_nodes(temp_soup)
                # Build HTML manually to avoid BeautifulSoup escaping entities
                def build_html(element):
                    """Recursively build HTML string preserving entities"""
                    if isinstance(element, NavigableString):
                        return str(element)
                    elif hasattr(element, 'name') and element.name:
                        # It's a tag
                        attrs_list = []
                        for k, v in element.attrs.items():
                            if isinstance(v, list):
                                v = ' '.join(v)
                            attrs_list.append(f'{k}="{html.escape(str(v))}"')
                        attrs_str = f' {" ".join(attrs_list)}' if attrs_list else ''
                        if element.name in ['br', 'img']:
                            return f'<{element.name}{attrs_str}/>'
                        else:
                            children_html = ''.join([build_html(child) for child in element.children])
                            return f'<{element.name}{attrs_str}>{children_html}</{element.name}>'
                    else:
                        # Skip document/root element, just get children
                        return ''.join([build_html(child) for child in element.children])
                
                # Get the root element (skip document wrapper)
                root = temp_soup if not hasattr(temp_soup, 'name') or temp_soup.name == '[document]' else temp_soup
                tricks_html = ''.join([build_html(child) for child in root.children])
                # Clean up excessive newlines
                tricks_html = re.sub(r'\n{3,}', '\n\n', tricks_html).strip()
                game_info['tricks'] = tricks_html if tricks_html else None
        
        # Extract titleshot and screenshot from carousel
        carousel = soup.find('div', class_='mondiaporama')
        if carousel:
            images = carousel.find_all('img', src=re.compile(r'extra_lire_fichier\.php'))
            if len(images) >= 1:
                first_img = images[0]
                src = first_img.get('src')
                if src:
                    # Only set if not already set from list page
                    if not game_info['titleshot']:
                        game_info['titleshot'] = urljoin(self.base_url, src)
            
            if len(images) >= 2:
                second_img = images[1]
                src = second_img.get('src')
                if src:
                    game_info['screenshot'] = urljoin(self.base_url, src)
        
        # Check for map URL
        map_url = f"{self.base_url}/extra_lire_fichier.php?extra=plan&fiche={game_id}&slot=1&part=A&type=.png"
        if self.check_url_exists(map_url):
            game_info['map'] = map_url
        else:
            game_info['map'] = None
        
        # Check for manual URL
        manual_url = f"{self.base_url}/extra_lire_fichier.php?extra=notice&fiche={game_id}&slot=1&part=A&type=.jpg"
        if self.check_url_exists(manual_url):
            game_info['manual'] = manual_url
        else:
            game_info['manual'] = None
        
        return game_info
    
    def scrape_game(self, game_url: str, game_id: str, game_name_from_list: str,
                   release_date: Optional[str] = None, publisher: Optional[str] = None,
                   titleshot_url: Optional[str] = None) -> Optional[Dict]:
        """Scrape a single game page"""
        # Check if already processed
        if game_url in self.progress_data['processed_games']:
            print(f"⏭️  Skipping already processed: {game_url}")
            return None
        
        soup = self.get_page(game_url)
        if not soup:
            return None
        
        game_info = self.extract_game_info(soup, game_url, game_id, release_date, publisher, titleshot_url)
        
        # Prioritize name from list page
        if game_info:
            game_info['name'] = game_name_from_list
            
            # Use game_id as key
            self.games_db[game_id] = game_info
            self.progress_data['processed_games'].add(game_url)
            self.progress_data['total_games_collected'] = len(self.games_db)
            
            # Save after each game
            self.save_database()
            self.save_progress()
            
            print(f"✅ Scraped: {game_info.get('name', 'N/A')} - Pub: {game_info.get('publisher', 'N/A')} - Year: {game_info.get('release_date', 'N/A')}")
            return game_info
        
        return None
    
    def run_scraper(self, resume: bool = True):
        """Run the scraper"""
        print("🚀 Starting CPC Power scraper...")
        
        # Load existing data
        self.load_database()
        if resume:
            self.load_progress()
        
        self.progress_data['status'] = 'running'
        self.save_progress()
        
        total_games = 0
        
        try:
            # Determine starting position
            start_position = 1
            if resume and self.progress_data.get('current_position'):
                start_position = self.progress_data['current_position']
                print(f"🔄 Resuming from position {start_position}")
            
            # Process each position from start_position to max_position
            for position in range(start_position, self.max_position + 1):
                print(f"\n{'='*60}")
                print(f"📌 Processing position: {position}/{self.max_position}")
                print(f"{'='*60}")
                
                # Construct URL
                url = f"{self.base_url}/index.php?page=database&lettre=all&position={position}"
                
                soup = self.get_page(url)
                if not soup:
                    print(f"⚠️  Failed to fetch position {position}")
                    self.progress_data['current_position'] = position
                    self.save_progress()
                    time.sleep(2)
                    continue
                
                # Extract game links and data from list page
                games = self.get_game_links_from_page(soup)
                
                if not games:
                    print(f"ℹ️  No games found on position {position}")
                    self.progress_data['current_position'] = position + 1
                    self.save_progress()
                    time.sleep(1)
                    continue
                
                print(f"📋 Found {len(games)} games on position {position}")
                
                # Scrape each game
                for game_data in games:
                    self.scrape_game(
                        game_url=game_data['url'],
                        game_id=game_data['game_id'],
                        game_name_from_list=game_data['name'],
                        release_date=game_data.get('release_date'),
                        publisher=game_data.get('publisher'),
                        titleshot_url=game_data.get('titleshot')
                    )
                    total_games += 1
                    time.sleep(0.5)  # Rate limiting between games
                
                # Update progress
                self.progress_data['current_position'] = position + 1
                self.save_progress()
                
                time.sleep(1)  # Rate limiting between positions
            
            self.progress_data['status'] = 'completed'
            print(f"\n🎉 Scraping completed! Total games: {total_games}")
            
        except KeyboardInterrupt:
            print("\n⚠️  Scraping interrupted by user")
            self.progress_data['status'] = 'interrupted'
            self.save_progress()
            print(f"💾 Progress saved. Resume with: python {sys.argv[0]} --resume")
        except Exception as e:
            print(f"\n❌ Error during scraping: {e}")
            self.progress_data['status'] = 'interrupted'
            self.save_progress()
            raise
        finally:
            self.save_database()
            self.save_progress()

def main():
    scraper = CPCPowerScraper()
    
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
            print(f"   Current position: {scraper.progress_data.get('current_position', 1)}")
            print(f"   Games processed: {len(scraper.progress_data.get('processed_games', []))}")
            print(f"   Total games in DB: {len(scraper.games_db)}")
            if scraper.progress_data.get('last_run_timestamp'):
                import datetime
                last_run = datetime.datetime.fromtimestamp(scraper.progress_data['last_run_timestamp'])
                print(f"   Last run: {last_run}")
            return
    
    scraper.run_scraper(resume=resume)

if __name__ == "__main__":
    main()

