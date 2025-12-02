#!/usr/bin/env python3
"""
Atari Legend Web Scraper
Scrapes game data from https://www.atarilegend.com/games
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

class AtariLegendScraper:
    def __init__(self):
        self.base_url = "https://www.atarilegend.com"
        self.games_db = {}
        self.session = requests.Session()
        
        # Progress tracking
        self.progress_file = "scraper_progress.json"
        self.db_file = "atarilegend_db.json"
        self.progress_data = {
            "current_letter": None,
            "current_page": 1,
            "processed_games": set(),
            "total_games_collected": 0,
            "last_run_timestamp": None,
            "status": "not_started"  # not_started, running, completed, interrupted
        }
        
        # Letters to process: A-Z and 0-9
        self.letters = [chr(i) for i in range(ord('A'), ord('Z')+1)] + ['0-9']
        
        # Realistic browser user agents - comprehensive list with real user agents
        self.user_agents = [
            # Chrome on Windows
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36',
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
                soup = BeautifulSoup(response.content, 'html.parser')
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
    
    def get_game_links_from_page(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract game detail page links and names from a list page
        Returns a dictionary mapping game URLs to game names
        """
        game_data = {}  # {url: name}
        
        # Games are in div blocks with classes "col-4 text-center p-3 align-self-top"
        # Find divs that have "col-4" and "text-center" classes
        game_blocks = soup.find_all('div', class_=lambda x: x and 'col-4' in x and 'text-center' in x)
        
        for block in game_blocks:
            # Find the game link - can be relative (/games/game-slug) or absolute (https://.../games/game-slug)
            # Look for links that point to game detail pages
            links = block.find_all('a', href=True)
            game_url = None
            game_name = None
            
            for link in links:
                href = link.get('href', '').strip()
                if not href:
                    continue
                
                # Handle both relative and absolute URLs
                # Game detail pages have pattern /games/game-slug or https://.../games/game-slug
                # Skip search links and pagination
                is_game_link = False
                full_url = None
                
                if href.startswith('/games/'):
                    # Relative URL
                    if (not href.startswith('/games/search') and
                        href != '/games' and
                        '/games/release/' not in href):
                        full_url = urljoin(self.base_url, href)
                        is_game_link = True
                elif '/games/' in href and href.startswith('http'):
                    # Absolute URL
                    if ('/games/search' not in href and
                        '/games/release/' not in href):
                        full_url = href
                        is_game_link = True
                
                if is_game_link:
                    # Extract game slug to validate (e.g., "a-320" from "/games/a-320")
                    if '/games/' in full_url:
                        game_slug = full_url.split('/games/')[-1].split('?')[0].split('#')[0].strip()
                        # Only add if it looks like a game slug (not empty, not just numbers)
                        if game_slug and not game_slug.isdigit() and 'search' not in game_slug:
                            if game_url is None:
                                game_url = full_url
                                # Extract game name from the link text
                                link_text = link.get_text(strip=True)
                                # The link text should be the game name (e.g., "A 320")
                                if link_text and link_text != game_slug:
                                    game_name = link_text
            
            # Also try to find the game name from other links in the block pointing to the same URL
            if game_url and not game_name:
                # Extract game slug for comparison
                game_slug = game_url.split('/games/')[-1].split('?')[0].split('#')[0].strip() if '/games/' in game_url else None
                
                # Look for all links pointing to the same game URL
                text_links = block.find_all('a', href=True)
                for text_link in text_links:
                    href = text_link.get('href', '').strip()
                    # Normalize href for comparison
                    if href.startswith('/games/'):
                        href = urljoin(self.base_url, href)
                    elif not href.startswith('http'):
                        continue
                    
                    # Check if this link points to the same game
                    if href == game_url:
                        text = text_link.get_text(strip=True)
                        # Use the text if it looks like a game name (not empty, not just the slug)
                        if text and (not game_slug or text != game_slug):
                            game_name = text
                            break
            
            if game_url:
                game_data[game_url] = game_name or None
        
        return game_data
    
    def has_next_page(self, soup: BeautifulSoup) -> bool:
        """Check if there's a next page"""
        # Look for pagination nav structure
        pagination_nav = soup.find('nav')
        if pagination_nav:
            pagination = pagination_nav.find('ul', class_=re.compile(r'pagination', re.I))
            if pagination:
                # Look for next link (›) that's not disabled
                next_link = pagination.find('a', attrs={'aria-label': re.compile(r'Next', re.I)})
                if next_link:
                    # Check if it's not disabled (should have href attribute)
                    if next_link.get('href'):
                        return True
                
                # Also check for the › character in links
                next_links = pagination.find_all('a', string=re.compile(r'›|Next', re.I))
                for link in next_links:
                    # Check if parent li doesn't have disabled class
                    parent_li = link.find_parent('li')
                    if parent_li and 'disabled' not in parent_li.get('class', []):
                        if link.get('href'):
                            return True
        
        return False
    
    def get_next_page_url(self, current_url: str, current_page: int) -> Optional[str]:
        """Get URL for next page"""
        # Try to find next page link in the HTML
        soup = self.get_page(current_url)
        if not soup:
            return None
        
        # Look for pagination
        pagination = soup.find('ul', class_=re.compile(r'pagination', re.I))
        if pagination:
            next_link = pagination.find('a', string=re.compile(r'Next|»|>', re.I))
            if next_link and 'href' in next_link.attrs:
                href = next_link['href']
                if href.startswith('http'):
                    return href
                else:
                    return urljoin(self.base_url, href)
        
        # Fallback: try to construct next page URL
        if '?' in current_url:
            if 'page=' in current_url:
                next_url = re.sub(r'page=\d+', f'page={current_page + 1}', current_url)
            else:
                next_url = f"{current_url}&page={current_page + 1}"
        else:
            next_url = f"{current_url}?page={current_page + 1}"
        
        return next_url
    
    def extract_game_info(self, soup: BeautifulSoup, game_url: str) -> Optional[Dict]:
        """Extract game information from detail page"""
        game_info = {
            'url': game_url,
            'name': None,
            'developer': None,
            'genre': None,
            'release_date': None,
            'publisher': None,
            'boxfront': None,
            'boxback': None,
            'titleshot': None,
            'screenshot': None,
        }
        
        # Extract game name - typically in h1 or page title
        # Try h1 first
        h1 = soup.find('h1')
        if h1:
            game_info['name'] = h1.get_text(strip=True)
        else:
            # Fallback to page title
            title_tag = soup.find('title')
            if title_tag:
                title_text = title_tag.get_text(strip=True)
                # Remove common suffixes like " - Atari Legend"
                game_info['name'] = re.sub(r'\s*-\s*Atari Legend.*$', '', title_text, flags=re.I).strip()
        
        # Extract developer
        dev_link = soup.find('a', href=re.compile(r'developer_id=\d+'))
        if dev_link:
            game_info['developer'] = dev_link.get_text(strip=True)
        
        # Extract genre
        genre_link = soup.find('a', href=re.compile(r'genre_id=\d+'))
        if genre_link:
            game_info['genre'] = genre_link.get_text(strip=True)
        
        # Extract release date and publisher from Releases section
        # Find the Releases card
        releases_card = None
        cards = soup.find_all('div', class_=lambda x: x and 'card' in x and 'card-game' in x)
        for card in cards:
            header = card.find('div', class_='card-header')
            if header and 'Releases' in header.get_text():
                releases_card = card
                break
        
        if releases_card:
            # Find all release entries (all card-body divs)
            all_releases = releases_card.find_all('div', class_='card-body')
            
            # Filter out unofficial releases (those with fa-skull-crossbones icon)
            official_releases = []
            for release in all_releases:
                # Check if this release has the skull-crossbones icon (unofficial release)
                skull_icon = release.find('i', class_=lambda x: x and 'fa-skull-crossbones' in x)
                if not skull_icon:
                    official_releases.append(release)
            
            # If no official releases, use all releases as fallback
            releases_to_check = official_releases if official_releases else all_releases
            
            # Try to find release date from first release, then next ones if no date found
            release_date_found = False
            for release in releases_to_check:
                # Extract release date (link with /games/release/)
                release_date_link = release.find('a', href=re.compile(r'/games/release/\d+'))
                if release_date_link:
                    year = release_date_link.get_text(strip=True)
                    # Skip "[no date]" entries and empty strings
                    if year and year.lower() != '[no date]' and year.strip():
                        # Convert year to "01-01-<year>" format
                        if year.isdigit():
                            game_info['release_date'] = f"01-01-{year}"
                            release_date_found = True
                            break  # Found a valid date, stop searching
                        else:
                            # Non-digit date, use as-is
                            game_info['release_date'] = year
                            release_date_found = True
                            break
            
            # If no date found in any release, use the last official release (or last release if no official ones)
            if not release_date_found and releases_to_check:
                last_release = releases_to_check[-1]
                release_date_link = last_release.find('a', href=re.compile(r'/games/release/\d+'))
                if release_date_link:
                    year = release_date_link.get_text(strip=True)
                    # Skip "[no date]" entries and empty strings
                    if year and year.lower() != '[no date]' and year.strip():
                        if year.isdigit():
                            game_info['release_date'] = f"01-01-{year}"
                        else:
                            game_info['release_date'] = year
            
            # Set to null if still no date found
            if not game_info['release_date']:
                game_info['release_date'] = None
            
            # Extract publisher from first release
            if all_releases:
                first_release = all_releases[0]
                # Extract publisher - it's in a span with "by" text
                # Format: <span class="ms-2 text-muted"><span class="text-muted">by</span> Publisher</span>
                publisher_span = first_release.find('span', class_='ms-2')
                if publisher_span:
                    # Try to find the nested "by" span first
                    by_span = publisher_span.find('span', string=re.compile(r'by', re.I))
                    if by_span:
                        # Get all text from the parent span
                        publisher_text = publisher_span.get_text(strip=True)
                        # Remove "by" and any leading/trailing whitespace
                        publisher_text = re.sub(r'^by\s+', '', publisher_text, flags=re.I).strip()
                        # Also remove "by" if it appears anywhere in the text
                        publisher_text = re.sub(r'\s*by\s*', '', publisher_text, flags=re.I).strip()
                        game_info['publisher'] = publisher_text
                    else:
                        # No nested "by" span, get text and clean it
                        publisher_text = publisher_span.get_text(strip=True)
                        # Remove "by" prefix if present
                        publisher_text = re.sub(r'^by\s+', '', publisher_text, flags=re.I).strip()
                        # Also remove "by" if it appears anywhere in the text
                        publisher_text = re.sub(r'\s*by\s*', '', publisher_text, flags=re.I).strip()
                        # Set to null if empty
                        game_info['publisher'] = publisher_text if publisher_text else None
            
            # Set publisher to null if not found
            if not game_info.get('publisher'):
                game_info['publisher'] = None
        
        # Fallback: try to extract release date from anywhere if not found in Releases section
        if not game_info['release_date']:
            release_link = soup.find('a', href=re.compile(r'/games/release/\d+'))
            if release_link:
                year = release_link.get_text(strip=True)
                # Skip "[no date]" entries and empty strings
                if year and year.lower() != '[no date]' and year.strip():
                    # Convert year to "01-01-<year>" format
                    if year.isdigit():
                        game_info['release_date'] = f"01-01-{year}"
                    else:
                        game_info['release_date'] = year
                else:
                    game_info['release_date'] = None
            else:
                game_info['release_date'] = None
        
        # Extract box scans (boxfront and boxback) from carousel
        box_carousel = soup.find('div', id='carousel-boxscans')
        if box_carousel:
            carousel_items = box_carousel.find_all('div', class_='carousel-item')
            if len(carousel_items) > 0:
                # First item is boxfront
                first_item = carousel_items[0]
                img_link = first_item.find('a', class_='lightbox-link')
                if img_link and img_link.get('href'):
                    game_info['boxfront'] = urljoin(self.base_url, img_link['href'])
                
                # Second item is boxback (if exists)
                if len(carousel_items) > 1:
                    second_item = carousel_items[1]
                    img_link = second_item.find('a', class_='lightbox-link')
                    if img_link and img_link.get('href'):
                        game_info['boxback'] = urljoin(self.base_url, img_link['href'])
        
        # Extract screenshots (titleshot and screenshot) from carousel
        # First check thumbnail area - titleshot is first (data-bs-slide-to="0"), screenshot is second (data-bs-slide-to="1")
        screenshot_thumbnails = soup.find('div', class_='carousel-thumbnails', attrs={'data-bs-carousel': 'carousel-screenshots'})
        if screenshot_thumbnails:
            thumb_links = screenshot_thumbnails.find_all('a', href=True)
            if len(thumb_links) > 0:
                # First thumbnail (titleshot) - data-bs-slide-to="0"
                first_thumb = thumb_links[0]
                img = first_thumb.find('img')
                if img and img.get('src'):
                    src = img['src']
                    # Screenshot URLs are like /games/game-name/screenshot-3577.png
                    # Convert to full URL
                    if src and 'screenshot-' in src and src.endswith('.png'):
                        game_info['titleshot'] = urljoin(self.base_url, src)
                
                # Second thumbnail (screenshot) - data-bs-slide-to="1"
                if len(thumb_links) > 1:
                    second_thumb = thumb_links[1]
                    img = second_thumb.find('img')
                    if img and img.get('src'):
                        src = img['src']
                        if src and 'screenshot-' in src and src.endswith('.png'):
                            game_info['screenshot'] = urljoin(self.base_url, src)
        
        # Also check the main carousel items as fallback
        screenshot_carousel = soup.find('div', id='carousel-screenshots')
        if screenshot_carousel:
            carousel_items = screenshot_carousel.find_all('div', class_='carousel-item')
            if len(carousel_items) > 0 and not game_info['titleshot']:
                # First item is titleshot
                first_item = carousel_items[0]
                img = first_item.find('img')
                if img and img.get('src'):
                    src = img['src']
                    if 'screenshot-' in src and src.endswith('.png'):
                        game_info['titleshot'] = urljoin(self.base_url, src)
                    else:
                        # Try to find full resolution link
                        img_link = first_item.find('a')
                        if img_link and img_link.get('href'):
                            game_info['titleshot'] = urljoin(self.base_url, img_link['href'])
                
                # Second item is screenshot (if exists)
                if len(carousel_items) > 1 and not game_info['screenshot']:
                    second_item = carousel_items[1]
                    img = second_item.find('img')
                    if img and img.get('src'):
                        src = img['src']
                        if 'screenshot-' in src and src.endswith('.png'):
                            game_info['screenshot'] = urljoin(self.base_url, src)
                        else:
                            img_link = second_item.find('a')
                            if img_link and img_link.get('href'):
                                game_info['screenshot'] = urljoin(self.base_url, img_link['href'])
        
        # Final cleanup: ensure all fields are null if empty or "[no date]"
        for key in ['name', 'developer', 'genre', 'release_date', 'publisher', 'boxfront', 'boxback', 'titleshot', 'screenshot']:
            value = game_info.get(key)
            if not value or value == '' or value == '[no date]' or (isinstance(value, str) and value.lower() == '[no date]'):
                game_info[key] = None
        
        return game_info
    
    def scrape_game(self, game_url: str, game_name_from_list: Optional[str] = None) -> Optional[Dict]:
        """Scrape a single game page"""
        # Check if already processed
        if game_url in self.progress_data['processed_games']:
            print(f"⏭️  Skipping already processed: {game_url}")
            return None
        
        soup = self.get_page(game_url)
        if not soup:
            return None
        
        game_info = self.extract_game_info(soup, game_url)
        
        # Use name from list page if detail page doesn't have it
        if game_info and not game_info.get('name') and game_name_from_list:
            game_info['name'] = game_name_from_list
        if game_info:
            # Use game URL as key (or extract game slug)
            game_slug = game_url.split('/')[-1]
            self.games_db[game_slug] = game_info
            self.progress_data['processed_games'].add(game_url)
            self.progress_data['total_games_collected'] = len(self.games_db)
            
            # Save after each game
            self.save_database()
            self.save_progress()
            
            game_name = game_info.get('name', game_slug)
            print(f"✅ Scraped: {game_name} - Dev: {game_info.get('developer', 'N/A')} - Pub: {game_info.get('publisher', 'N/A')} - Year: {game_info.get('release_date', 'N/A')}")
            return game_info
        
        return None
    
    def scrape_letter_pages(self, letter: str) -> int:
        """Scrape all pages for a given letter"""
        games_scraped = 0
        page = 1
        
        # Determine starting page if resuming
        if self.progress_data['current_letter'] == letter:
            page = self.progress_data.get('current_page', 1)
            print(f"🔄 Resuming from page {page} for letter {letter}")
        else:
            self.progress_data['current_letter'] = letter
            self.progress_data['current_page'] = 1
        
        while True:
            # Construct URL
            if letter == '0-9':
                url = f"{self.base_url}/games/search?titleAZ=0-9"
            else:
                url = f"{self.base_url}/games/search?titleAZ={letter}"
            
            # Add page parameter if not first page
            if page > 1:
                if '?' in url:
                    url = f"{url}&page={page}"
                else:
                    url = f"{url}?page={page}"
            
            print(f"\n📖 Processing letter '{letter}', page {page}")
            
            soup = self.get_page(url)
            if not soup:
                print(f"⚠️  Failed to fetch page {page} for letter {letter}")
                break
            
            # Extract game links and names
            game_data = self.get_game_links_from_page(soup)
            
            if not game_data:
                print(f"ℹ️  No games found on page {page} for letter {letter}")
                # Debug: check if we found any col-4 divs
                game_blocks = soup.find_all('div', class_=lambda x: x and 'col-4' in x and 'text-center' in x)
                print(f"🔍 Debug: Found {len(game_blocks)} game blocks with col-4 class")
                # Debug: show first few hrefs found
                if game_blocks:
                    first_block = game_blocks[0]
                    links = first_block.find_all('a', href=True)
                    print(f"🔍 Debug: First block has {len(links)} links")
                    for i, link in enumerate(links[:3]):
                        print(f"🔍 Debug: Link {i+1}: {link.get('href', 'N/A')}")
                
                # Check if there's a next page indicator before stopping
                if self.has_next_page(soup):
                    print(f"ℹ️  Next page indicator found, trying page {page + 1}...")
                    page += 1
                    self.progress_data['current_page'] = page
                    self.save_progress()
                    time.sleep(1)
                    continue
                else:
                    # No more pages
                    break
            
            print(f"📋 Found {len(game_data)} games on page {page}")
            
            # Scrape each game
            for game_url, game_name in game_data.items():
                self.scrape_game(game_url, game_name_from_list=game_name)
                games_scraped += 1
                time.sleep(0.5)  # Rate limiting between games
            
            # Update progress
            self.progress_data['current_page'] = page
            
            # Check for next page
            if self.has_next_page(soup):
                page += 1
                self.save_progress()
                time.sleep(1)  # Rate limiting between pages
            else:
                # No next page indicator, but try one more page to be sure
                page += 1
                # Will be checked in next iteration
        
        # Reset for next letter
        self.progress_data['current_letter'] = None
        self.progress_data['current_page'] = 1
        self.save_progress()
        
        return games_scraped
    
    def run_scraper(self, resume: bool = True):
        """Run the scraper"""
        print("🚀 Starting Atari Legend scraper...")
        
        # Load existing data
        self.load_database()
        if resume:
            self.load_progress()
        
        self.progress_data['status'] = 'running'
        self.save_progress()
        
        total_games = 0
        
        try:
            # Determine starting letter
            start_idx = 0
            if resume and self.progress_data['current_letter']:
                try:
                    start_idx = self.letters.index(self.progress_data['current_letter'])
                except ValueError:
                    start_idx = 0
            
            # Process each letter
            for idx, letter in enumerate(self.letters[start_idx:], start=start_idx):
                print(f"\n{'='*60}")
                print(f"📌 Processing letter: {letter} ({idx+1}/{len(self.letters)})")
                print(f"{'='*60}")
                
                games_count = self.scrape_letter_pages(letter)
                total_games += games_count
                
                print(f"✅ Completed letter '{letter}': {games_count} games scraped")
                time.sleep(2)  # Rate limiting between letters
            
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
    scraper = AtariLegendScraper()
    
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
            print(f"   Current letter: {scraper.progress_data.get('current_letter', 'None')}")
            print(f"   Current page: {scraper.progress_data.get('current_page', 1)}")
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

