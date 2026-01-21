#!/usr/bin/env python3
"""
LemonAmiga Web Scraper
Scrapes game data from https://www.lemonamiga.com/games/list.php
Creates a JSON database with game information
"""

import requests
from bs4 import BeautifulSoup
import json
import time
import re
from urllib.parse import urljoin, urlparse
import sys
import random
import os
from typing import Dict, List, Optional, Tuple

class LemonAmigaScraper:
    def __init__(self):
        self.base_url = "https://www.lemonamiga.com"
        self.games_db = {}
        self.session = requests.Session()
        
        # Progress tracking
        self.progress_file = "scraper_progress.json"
        self.db_file = "lemonamiga_db.json"
        self.progress_data = {
            "current_offset": 0,
            "processed_games": set(),
            "total_games_collected": 0,
            "last_run_timestamp": None,
            "status": "not_started"  # not_started, running, completed, interrupted
        }
        
        # Realistic browser user agents - comprehensive list with real user agents
        self.user_agents = [
            # Chrome on Windows
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
            # Chrome 129.0.0.0 removed - consistently getting 403 errors
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
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
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
                    print(f"✅ Loaded progress: {len(self.progress_data['processed_games'])} games already processed, current offset: {self.progress_data.get('current_offset', 0)}")
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
    
    def get_page(self, url: str, rotate_ua: bool = True, retry_on_403: bool = True) -> Optional[BeautifulSoup]:
        """Fetch a page and return BeautifulSoup object"""
        max_retries = 3 if retry_on_403 else 1
        
        for attempt in range(max_retries):
            try:
                # Rotate user agent before each request
                current_ua = None
                if rotate_ua:
                    current_ua = self._rotate_user_agent()
                    if random.random() < 0.1:  # 10% chance to log user agent rotation
                        print(f"🔄 Using User-Agent: {current_ua[:60]}...")
                else:
                    current_ua = self.session.headers.get('User-Agent', 'Unknown')
                
                print(f"📄 Fetching: {url}")
                response = self.session.get(url, timeout=30)
                
                # Handle 403 errors specifically
                if response.status_code == 403:
                    print(f"⚠️  403 Forbidden for {url}")
                    print(f"   User-Agent: {current_ua}")
                    if retry_on_403 and attempt < max_retries - 1:
                        print(f"   Retrying with different User-Agent (attempt {attempt + 1}/{max_retries})...")
                        # Rotate to next user agent
                        if rotate_ua:
                            self._rotate_user_agent()
                        time.sleep(2)  # Wait before retry
                        continue
                    else:
                        return None
                
                response.raise_for_status()
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'html.parser')
                    return soup
                else:
                    print(f"⚠️  Unexpected status code: {response.status_code}")
                    return None
                    
            except requests.exceptions.HTTPError as e:
                if e.response and e.response.status_code == 403:
                    current_ua = self.session.headers.get('User-Agent', 'Unknown')
                    print(f"❌ HTTP 403 Error fetching {url}: {e}")
                    print(f"   User-Agent: {current_ua}")
                    if retry_on_403 and attempt < max_retries - 1:
                        print(f"   Retrying with different User-Agent (attempt {attempt + 1}/{max_retries})...")
                        # Rotate to next user agent
                        if rotate_ua:
                            self._rotate_user_agent()
                        time.sleep(2)  # Wait before retry
                        continue
                    else:
                        return None
                else:
                    current_ua = self.session.headers.get('User-Agent', 'Unknown')
                    print(f"❌ HTTP Error fetching {url}: {e}")
                    print(f"   User-Agent: {current_ua}")
                    return None
                    
            except requests.exceptions.RequestException as e:
                current_ua = self.session.headers.get('User-Agent', 'Unknown')
                print(f"❌ Error fetching {url}: {e}")
                print(f"   User-Agent: {current_ua}")
                # Rotate user agent on error
                if rotate_ua:
                    self._rotate_user_agent()
                # Don't retry on other errors (connection, timeout, etc.)
                return None
        
        return None
    
    def get_game_links_from_page(self, soup: BeautifulSoup) -> Dict[str, Dict]:
        """Extract game data from list page
        Returns a dictionary mapping game URLs to game data (gameid, name, release_date, genre)
        """
        game_data = {}  # {url: {gameid, name, release_date, genre}}
        
        # Find all game cards: <div class="col-6 col-md-3 game-col game-col-1" id="game-1366">
        game_cards = soup.find_all('div', class_=lambda x: x and 'game-col' in x and 'col-6' in x)
        
        for card in game_cards:
            # Extract gameid from id attribute (e.g., "game-1366" -> 1366)
            game_id = None
            card_id = card.get('id', '')
            if card_id.startswith('game-'):
                try:
                    game_id = int(card_id.replace('game-', ''))
                except ValueError:
                    pass
            
            # Extract game name from .game-grid-title link
            name = None
            title_div = card.find('div', class_='game-grid-title')
            if title_div:
                link = title_div.find('a', href=True)
                if link:
                    name = link.get_text(strip=True)
                    
                    # Check for chipset icon (CD32, AGA, etc.) next to the name
                    # Look for chipset icon after the link
                    chipset_icon = title_div.find('a', href=re.compile(r'list_hardware='))
                    if chipset_icon:
                        # Extract chipset name from the icon's alt text or href
                        chipset_img = chipset_icon.find('img', class_='chipset-icon')
                        if chipset_img:
                            chipset_name = chipset_img.get('alt', '')
                            if chipset_name:
                                # Append chipset variant to name, e.g., " (CD32)" or " (AGA)"
                                name = f"{name} ({chipset_name})"
            
            # Extract release_date from .grid-credits (first link is year)
            release_date = None
            credits_div = card.find('div', class_='grid-credits')
            if credits_div:
                year_link = credits_div.find('a', href=True)
                if year_link:
                    year_text = year_link.get_text(strip=True)
                    # Convert year to "01-01-YYYY" format
                    if year_text and year_text.isdigit():
                        release_date = f"01-01-{year_text}"
            
            # Extract genre from .grid-category link (take first part before " - ")
            genre = None
            category_div = card.find('div', class_='grid-category')
            if category_div:
                genre_link = category_div.find('a', href=True)
                if genre_link:
                    genre_text = genre_link.get_text(strip=True)
                    # Extract main genre before " - "
                    if ' - ' in genre_text:
                        genre = genre_text.split(' - ')[0].strip()
                    else:
                        genre = genre_text.strip()
            
            # Extract game URL from the main link
            game_url = None
            # Look for link in .game-grid-title or in screenshot container
            title_link = card.find('div', class_='game-grid-title')
            if title_link:
                link = title_link.find('a', href=True)
                if link:
                    href = link.get('href', '').strip()
                    if href:
                        if href.startswith('/game/'):
                            game_url = urljoin(self.base_url, href)
                        elif href.startswith('http'):
                            game_url = href
            
            # Also check screenshot container for link
            if not game_url:
                screenshot_container = card.find('div', class_='grid-screenshot-container')
                if screenshot_container:
                    link = screenshot_container.find('a', href=True)
                    if link:
                        href = link.get('href', '').strip()
                        if href and '/game/' in href:
                            if href.startswith('/game/'):
                                game_url = urljoin(self.base_url, href)
                            elif href.startswith('http'):
                                game_url = href
            
            if game_url and game_id:
                game_data[game_url] = {
                    'gameid': game_id,
                    'name': name,
                    'release_date': release_date,
                    'genre': genre
                }
        
        return game_data
    
    def parse_rating_from_images(self, soup: BeautifulSoup) -> Optional[float]:
        """Parse rating from score images in .votes-score div
        Images like 7.png, dot.png, 6.png, 3.png represent digits
        Returns rating normalized to /5 scale (divide by 2)
        """
        votes_score_div = soup.find('div', class_='votes-score')
        if not votes_score_div:
            return None
        
        # Find all img tags in the votes-score div
        images = votes_score_div.find_all('img')
        if not images:
            return None
        
        score_string = ""
        for img in images:
            src = img.get('src', '')
            if not src:
                continue
            
            # Extract filename from src (e.g., "/assets/amiga/images/score/7.png" -> "7.png")
            filename = src.split('/')[-1]
            
            # Map filename to digit or decimal point
            if filename == 'dot.png':
                score_string += "."
            elif filename.endswith('.png'):
                # Extract digit from filename (e.g., "7.png" -> "7")
                digit_match = re.search(r'(\d+)\.png', filename)
                if digit_match:
                    score_string += digit_match.group(1)
        
        if score_string:
            try:
                # Convert to float and normalize from /10 to /5
                rating = float(score_string) / 2.0
                return rating
            except ValueError:
                return None
        
        return None
    
    def extract_nbvote(self, soup: BeautifulSoup) -> Optional[int]:
        """Extract number of votes from text like 'from a total of **8** votes'"""
        # Look for paragraph with "from a total of" text
        paragraphs = soup.find_all('p')
        for p in paragraphs:
            text = p.get_text()
            if 'from a total of' in text.lower():
                # Extract number using regex (handles whitespace and HTML tags via get_text())
                # Pattern: "from a total of" followed by optional whitespace and a number
                match = re.search(r'from a total of\s+(\d+)', text, re.IGNORECASE)
                if match:
                    try:
                        return int(match.group(1))
                    except ValueError:
                        pass
                # Alternative pattern if the above doesn't match
                match = re.search(r'from a total of.*?(\d+)', text, re.IGNORECASE)
                if match:
                    try:
                        return int(match.group(1))
                    except ValueError:
                        pass
        
        return None
    
    def extract_game_info(self, soup: BeautifulSoup, game_url: str, list_data: Optional[Dict] = None) -> Optional[Dict]:
        """Extract game information from detail page"""
        game_info = {
            'url': game_url,
            'gameid': None,
            'name': None,
            'developer': None,
            'genre': None,
            'release_date': None,
            'publisher': None,
            'rating': None,
            'nbvote': None,
            'boxfront': None,
            'boxback': None,
            'titleshot': None,
            'screenshot': None,
            'youtubeurl': None,
        }
        
        # Use data from list page if available
        if list_data:
            game_info['gameid'] = list_data.get('gameid')
            game_info['name'] = list_data.get('name')
            game_info['release_date'] = list_data.get('release_date')
            game_info['genre'] = list_data.get('genre')
        
        # Extract game name - try h1 first, then title tag
        # If name from list page doesn't have variant, check h1 for chipset icon
        h1 = soup.find('h1')
        if h1:
            # Get text from h1 (this will include any chipset info if present as text)
            h1_text = h1.get_text(strip=True)
            
            # Check for chipset icon inside h1
            chipset_icon = h1.find('img', class_='chipset-icon')
            if chipset_icon:
                chipset_name = chipset_icon.get('alt', '')
                if chipset_name:
                    # If name from list page doesn't already have variant, add it
                    if not game_info.get('name') or f"({chipset_name})" not in game_info.get('name', ''):
                        # Use h1 text and append chipset if not already there
                        if chipset_name not in h1_text:
                            game_info['name'] = f"{h1_text} ({chipset_name})"
                        else:
                            game_info['name'] = h1_text
                    else:
                        # Name from list page already has variant, use it
                        pass
            else:
                # No chipset icon, use h1 text or list page name
                if not game_info.get('name'):
                    game_info['name'] = h1_text
        
        # Fallback to title tag if still no name
        if not game_info.get('name'):
            title_tag = soup.find('title')
            if title_tag:
                title_text = title_tag.get_text(strip=True)
                # Remove common suffixes
                game_info['name'] = re.sub(r'\s*-\s*Lemon Amiga.*$', '', title_text, flags=re.I).strip()
        
        # Extract release_date from table row with "Released:" text
        if not game_info['release_date']:
            rows = soup.find_all('tr')
            for row in rows:
                td_label = row.find('td', class_='text-nowrap')
                if td_label and 'Released:' in td_label.get_text():
                    td_data = row.find('td', class_='credits-data')
                    if td_data:
                        year_link = td_data.find('a', href=True)
                        if year_link:
                            year_text = year_link.get_text(strip=True)
                            if year_text and year_text.isdigit():
                                game_info['release_date'] = f"01-01-{year_text}"
                                break
        
        # Extract publisher from table row with "Publisher:" text
        rows = soup.find_all('tr')
        for row in rows:
            td_label = row.find('td', class_='text-nowrap')
            if td_label and 'Publisher:' in td_label.get_text():
                td_data = row.find('td', class_='credits-data')
                if td_data:
                    publisher_link = td_data.find('a', href=True)
                    if publisher_link:
                        game_info['publisher'] = publisher_link.get_text(strip=True)
                        break
        
        # Extract developer from table row with "Developer:" text
        for row in rows:
            td_label = row.find('td', class_='text-nowrap')
            if td_label and 'Developer:' in td_label.get_text():
                td_data = row.find('td', class_='credits-data')
                if td_data:
                    developer_link = td_data.find('a', href=True)
                    if developer_link:
                        game_info['developer'] = developer_link.get_text(strip=True)
                        break
        
        # Extract rating from images
        game_info['rating'] = self.parse_rating_from_images(soup)
        
        # Extract number of votes
        game_info['nbvote'] = self.extract_nbvote(soup)
        
        # Extract screenshots (titleshot and screenshot)
        # First image in screenshot gallery is titleshot, second is screenshot
        # The gallery has class "screenshot-gallery" (may have additional classes like "gallery cS-hidden")
        screenshot_gallery = soup.find('div', class_=lambda x: x and 'screenshot-gallery' in x)
        if screenshot_gallery:
            # Find all direct <a> children (screenshots are direct <a> tags with <img> inside)
            screenshot_links = screenshot_gallery.find_all('a', href=True, recursive=False)
            # Also try finding all <a> tags if direct children don't work
            if not screenshot_links:
                screenshot_links = screenshot_gallery.find_all('a', href=True)
            
            if len(screenshot_links) > 0:
                # First link is titleshot
                first_link = screenshot_links[0]
                img = first_link.find('img')
                if img and img.get('src'):
                    src = img.get('src')
                    if src.startswith('/'):
                        game_info['titleshot'] = urljoin(self.base_url, src)
                    elif src.startswith('http'):
                        game_info['titleshot'] = src
                    else:
                        # Relative path without leading slash
                        game_info['titleshot'] = urljoin(self.base_url, '/' + src.lstrip('/'))
                
                # Second link is screenshot
                if len(screenshot_links) > 1:
                    second_link = screenshot_links[1]
                    img = second_link.find('img')
                    if img and img.get('src'):
                        src = img.get('src')
                        if src.startswith('/'):
                            game_info['screenshot'] = urljoin(self.base_url, src)
                        elif src.startswith('http'):
                            game_info['screenshot'] = src
                        else:
                            # Relative path without leading slash
                            game_info['screenshot'] = urljoin(self.base_url, '/' + src.lstrip('/'))
        
        # Extract box scans (boxfront and boxback) from scan carousel
        scan_slider = soup.find('ul', class_='scan-slider')
        if scan_slider:
            # Find all list items with covers (may or may not have lslide class)
            # First try to find items with lslide class (excluding clones)
            scan_items = scan_slider.find_all('li', class_=lambda x: x and 'lslide' in x and 'clone' not in x)
            # If no items found, try all <li> elements
            if not scan_items:
                scan_items = scan_slider.find_all('li')
            
            for item in scan_items:
                # Skip clone items - check if class list contains 'clone'
                item_classes = item.get('class', [])
                if item_classes and any('clone' in str(cls).lower() for cls in item_classes):
                    continue
                
                # Check the label to determine if it's front or back cover
                label_div = item.find('div', class_='scan-label')
                if label_div:
                    # Get text from label (handles <strong> tags and HTML entities)
                    label_text = label_div.get_text(strip=True)
                    # Check for strong tag text first (more reliable)
                    strong_tag = label_div.find('strong')
                    cover_type = None
                    if strong_tag:
                        strong_text = strong_tag.get_text(strip=True)
                        if 'Front Cover' in strong_text:
                            cover_type = 'front'
                        elif 'Back Cover' in strong_text:
                            cover_type = 'back'
                    # Fallback to label text if strong tag didn't match
                    if not cover_type:
                        if 'Front Cover' in label_text:
                            cover_type = 'front'
                        elif 'Back Cover' in label_text:
                            cover_type = 'back'
                    
                    # If we found a cover type, extract the URL
                    if cover_type:
                        link = item.find('a', href=True)
                        if link:
                            href = link.get('href', '').strip()
                            # Only extract if it's a cover image (not magazine)
                            if href and '/covers/large/' in href:
                                full_url = None
                                if href.startswith('/'):
                                    full_url = urljoin(self.base_url, href)
                                elif href.startswith('http'):
                                    full_url = href
                                
                                if full_url:
                                    if cover_type == 'front' and not game_info.get('boxfront'):
                                        game_info['boxfront'] = full_url
                                    elif cover_type == 'back' and not game_info.get('boxback'):
                                        game_info['boxback'] = full_url
        
        # Extract YouTube URL
        # First, try to find YouTube embed links
        youtube_links = soup.find_all('a', href=re.compile(r'youtube\.com/embed'))
        for link in youtube_links:
            href = link.get('href', '')
            # Extract video ID from embed URL
            match = re.search(r'youtube\.com/embed/([^/?]+)', href)
            if match:
                video_id = match.group(1)
                game_info['youtubeurl'] = f"https://www.youtube.com/watch?v={video_id}"
                break
        
        # If no embed link found, look for direct YouTube watch links in YouTube Links section
        if not game_info['youtubeurl']:
            # Find the YouTube Links table row
            youtube_header = soup.find('td', string=re.compile(r'YouTube Links', re.I))
            if youtube_header:
                # Find the parent table and look for YouTube watch links
                parent_table = youtube_header.find_parent('table')
                if parent_table:
                    # Find all YouTube watch links in this section
                    watch_links = parent_table.find_all('a', href=re.compile(r'youtube\.com/watch\?v='))
                    if watch_links:
                        # Take the first YouTube watch link
                        href = watch_links[0].get('href', '')
                        if href:
                            game_info['youtubeurl'] = href
        
        # Final cleanup: ensure all fields are null if empty
        for key in game_info:
            value = game_info.get(key)
            if value == '' or value == []:
                game_info[key] = None
        
        return game_info
    
    def scrape_game(self, game_url: str, list_data: Optional[Dict] = None) -> Optional[Dict]:
        """Scrape a single game page"""
        # Check if already processed
        if game_url in self.progress_data['processed_games']:
            print(f"⏭️  Skipping already processed: {game_url}")
            return None
        
        soup = self.get_page(game_url)
        if not soup:
            return None
        
        game_info = self.extract_game_info(soup, game_url, list_data)
        
        if game_info:
            # Use game slug as key (extract from URL)
            game_slug = game_url.split('/game/')[-1].split('?')[0].split('#')[0].strip()
            if game_slug:
                self.games_db[game_slug] = game_info
                self.progress_data['processed_games'].add(game_url)
                self.progress_data['total_games_collected'] = len(self.games_db)
                
                # Save after each game
                self.save_database()
                self.save_progress()
                
                game_name = game_info.get('name', game_slug)
                print(f"✅ Scraped: {game_name} - ID: {game_info.get('gameid', 'N/A')} - Dev: {game_info.get('developer', 'N/A')} - Pub: {game_info.get('publisher', 'N/A')} - Year: {game_info.get('release_date', 'N/A')} - Rating: {game_info.get('rating', 'N/A')}")
                return game_info
        
        return None
    
    def scrape_offset_pages(self):
        """Scrape all pages from offset 0 to 5000 (increment 40)"""
        games_scraped = 0
        start_offset = self.progress_data.get('current_offset', 0)
        max_offset = 5000
        
        print(f"\n📖 Starting to scrape from offset {start_offset} to {max_offset}")
        
        for offset in range(start_offset, max_offset + 1, 40):
            url = f"{self.base_url}/games/list.php?lineoffset={offset}"
            
            print(f"\n{'='*60}")
            print(f"📌 Processing offset: {offset}")
            print(f"{'='*60}")
            
            soup = self.get_page(url)
            if not soup:
                print(f"⚠️  Failed to fetch page at offset {offset}")
                # Update progress and continue
                self.progress_data['current_offset'] = offset
                self.save_progress()
                time.sleep(2)
                continue
            
            # Extract game links and data from list page
            game_data = self.get_game_links_from_page(soup)
            
            if not game_data:
                print(f"ℹ️  No games found at offset {offset}")
                # Check if we've reached the end
                # If no games found, we might have reached the end
                self.progress_data['current_offset'] = offset + 40
                self.save_progress()
                time.sleep(1)
                continue
            
            print(f"📋 Found {len(game_data)} games at offset {offset}")
            
            # Scrape each game
            for game_url, list_info in game_data.items():
                self.scrape_game(game_url, list_data=list_info)
                games_scraped += 1
                time.sleep(0.5)  # Rate limiting between games
            
            # Update progress
            self.progress_data['current_offset'] = offset + 40
            self.save_progress()
            
            time.sleep(1)  # Rate limiting between pages
        
        return games_scraped
    
    def run_scraper(self, resume: bool = True):
        """Run the scraper"""
        print("🚀 Starting LemonAmiga scraper...")
        
        # Load existing data
        self.load_database()
        if resume:
            self.load_progress()
        
        self.progress_data['status'] = 'running'
        self.save_progress()
        
        try:
            games_count = self.scrape_offset_pages()
            
            self.progress_data['status'] = 'completed'
            print(f"\n🎉 Scraping completed! Total games: {games_count}")
            
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
    scraper = LemonAmigaScraper()
    
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
            print(f"   Current offset: {scraper.progress_data.get('current_offset', 0)}")
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
