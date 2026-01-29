#!/usr/bin/env python3
"""
Hall of Light (HOL) Web Scraper
Scrapes game data from https://amiga.abime.net/games/list/
Creates a JSON database with game information

Each game can have multiple versions (ECS/OCS, AGA, CD32, etc.)
Each version is stored as a separate entry in the database

Note: This site uses Anubis bot protection. You need to either:
1. Provide cookies from an authenticated browser session (cookies.txt)
2. Use Selenium/Playwright for browser automation
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
from http.cookiejar import MozillaCookieJar

# Try to import cloudscraper for JavaScript challenge bypass
try:
    import cloudscraper
    HAS_CLOUDSCRAPER = True
except ImportError:
    HAS_CLOUDSCRAPER = False

# Try to import selenium for browser automation
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    HAS_SELENIUM = True
except ImportError:
    HAS_SELENIUM = False

def _sanitize_text(s: str) -> str:
    """Remove NULL bytes and control characters so text is safe for JSON/XML.
    Keeps tab, newline, carriage return and printable Unicode (XML 1.0 compatible)."""
    if s is None or not isinstance(s, str):
        return s if s is not None else ''
    result = []
    for c in s:
        code = ord(c)
        if code == 0x9 or code == 0xA or code == 0xD:
            result.append(c)
        elif 0x20 <= code <= 0xD7FF or 0xE000 <= code <= 0xFFFD or (0x10000 <= code <= 0x10FFFF):
            result.append(c)
    return ''.join(result)


def _sanitize_dict_strings(obj):
    """Recursively sanitize all string values in a dict/list (in place)."""
    if isinstance(obj, dict):
        for k, v in list(obj.items()):
            obj[k] = _sanitize_dict_strings(v)
        return obj
    if isinstance(obj, list):
        for i, v in enumerate(obj):
            obj[i] = _sanitize_dict_strings(v)
        return obj
    if isinstance(obj, str):
        return _sanitize_text(obj)
    return obj


class HOLScraper:
    def __init__(self, use_selenium: bool = False, cookies_file: str = None):
        self.base_url = "https://amiga.abime.net"
        self.games_db = {}
        self.use_selenium = use_selenium and HAS_SELENIUM
        self.driver = None
        self.cookies_file = cookies_file or "cookies.txt"
        
        # Initialize session
        if HAS_CLOUDSCRAPER:
            print("ℹ️  Using cloudscraper for JavaScript challenge bypass")
            self.session = cloudscraper.create_scraper(
                browser={
                    'browser': 'chrome',
                    'platform': 'windows',
                    'desktop': True
                }
            )
        else:
            self.session = requests.Session()
        
        # Load cookies if available
        self._load_cookies()
        
        # Progress tracking
        self.progress_file = "scraper_progress.json"
        self.db_file = "hol_db.json"
        self.progress_data = {
            "current_page": 1,
            "max_page": 227,
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
    
    def _load_cookies(self):
        """Load cookies from Netscape/Mozilla format cookies.txt file"""
        if os.path.exists(self.cookies_file):
            try:
                cookie_jar = MozillaCookieJar(self.cookies_file)
                cookie_jar.load(ignore_discard=True, ignore_expires=True)
                self.session.cookies.update(cookie_jar)
                print(f"✅ Loaded cookies from {self.cookies_file}")
            except Exception as e:
                print(f"⚠️  Error loading cookies: {e}")
        else:
            print(f"ℹ️  No cookies file found at {self.cookies_file}")
    
    def _init_selenium(self):
        """Initialize Selenium WebDriver"""
        if not HAS_SELENIUM:
            print("❌ Selenium not installed. Run: pip install selenium")
            return False
        
        if self.driver:
            return True
        
        try:
            options = Options()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument(f'user-agent={self.user_agents[0]}')
            
            self.driver = webdriver.Chrome(options=options)
            self.driver.set_page_load_timeout(30)
            print("✅ Selenium WebDriver initialized")
            return True
        except Exception as e:
            print(f"❌ Failed to initialize Selenium: {e}")
            return False
    
    def _get_page_selenium(self, url: str) -> Optional[BeautifulSoup]:
        """Fetch a page using Selenium (handles JavaScript challenges)"""
        if not self._init_selenium():
            return None
        
        try:
            print(f"📄 Fetching with Selenium: {url}")
            self.driver.get(url)
            
            # Wait for the page to load (wait for body to have content)
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Check if we hit the bot protection page
            if "Making sure you're not a bot" in self.driver.page_source:
                print("⏳ Bot protection detected, waiting for challenge to complete...")
                # Wait for the challenge to complete (up to 30 seconds)
                for _ in range(30):
                    time.sleep(1)
                    if "Making sure you're not a bot" not in self.driver.page_source:
                        break
                else:
                    print("❌ Bot challenge did not complete")
                    return None
            
            # Additional wait for dynamic content
            time.sleep(2)
            
            html = self.driver.page_source
            soup = BeautifulSoup(html, 'html.parser')
            return soup
            
        except Exception as e:
            print(f"❌ Selenium error: {e}")
            return None
    
    def _setup_browser_headers(self):
        """Set up realistic browser headers"""
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
                    print(f"✅ Loaded progress: {len(self.progress_data['processed_games'])} games already processed, current page: {self.progress_data.get('current_page', 1)}")
                    return True
            except Exception as e:
                print(f"⚠️  Error loading progress: {e}")
                return False
        return False
    
    def save_progress(self):
        """Save progress to file"""
        try:
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
                    print(f"✅ Loaded database: {len(self.games_db)} entries")
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
        # Use Selenium if enabled
        if self.use_selenium:
            return self._get_page_selenium(url)
        
        max_retries = 3 if retry_on_403 else 1
        
        for attempt in range(max_retries):
            try:
                current_ua = None
                if rotate_ua:
                    current_ua = self._rotate_user_agent()
                    if random.random() < 0.1:
                        print(f"🔄 Using User-Agent: {current_ua[:60]}...")
                else:
                    current_ua = self.session.headers.get('User-Agent', 'Unknown')
                
                print(f"📄 Fetching: {url}")
                response = self.session.get(url, timeout=30)
                
                if response.status_code == 403:
                    print(f"⚠️  403 Forbidden for {url}")
                    print(f"   User-Agent: {current_ua}")
                    if retry_on_403 and attempt < max_retries - 1:
                        print(f"   Retrying with different User-Agent (attempt {attempt + 1}/{max_retries})...")
                        if rotate_ua:
                            self._rotate_user_agent()
                        time.sleep(2)
                        continue
                    else:
                        # Try Selenium as fallback if available
                        if HAS_SELENIUM and not self.use_selenium:
                            print("🔄 Trying Selenium as fallback...")
                            self.use_selenium = True
                            result = self._get_page_selenium(url)
                            self.use_selenium = False
                            return result
                        return None
                
                response.raise_for_status()
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'html.parser')
                    
                    # Check for bot protection page
                    if self._is_bot_protection_page(soup):
                        print("⚠️  Bot protection page detected")
                        if HAS_SELENIUM and not self.use_selenium:
                            print("🔄 Trying Selenium to bypass bot protection...")
                            self.use_selenium = True
                            result = self._get_page_selenium(url)
                            self.use_selenium = False
                            return result
                        else:
                            print("❌ Cannot bypass bot protection. Please provide valid cookies.")
                            return None
                    
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
                        if rotate_ua:
                            self._rotate_user_agent()
                        time.sleep(2)
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
                if rotate_ua:
                    self._rotate_user_agent()
                return None
        
        return None
    
    def _is_bot_protection_page(self, soup: BeautifulSoup) -> bool:
        """Check if the page is a bot protection challenge page"""
        # Check for common Anubis bot protection indicators
        title = soup.find('title')
        if title and "Making sure you're not a bot" in title.get_text():
            return True
        
        h1 = soup.find('h1')
        if h1 and "Making sure you're not a bot" in h1.get_text():
            return True
        
        # Check for Anubis text anywhere in the page
        body = soup.find('body')
        if body:
            body_text = body.get_text()
            if "Making sure you're not a bot" in body_text or "Protected by Anubis" in body_text:
                return True
        
        return False
    
    def get_game_links_from_page(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract game links and names from grid list page
        Returns a dictionary mapping game URLs to game names
        """
        game_data = {}  # {url: name}
        
        # Find all game name divs: <div class="gamecolumn_name col-12"><a href="/games/view/turrican"><h4>Turrican</h4></a></div>
        game_name_divs = soup.find_all('div', class_='gamecolumn_name')
        
        for name_div in game_name_divs:
            link = name_div.find('a', href=True)
            if link:
                href = link.get('href', '').strip()
                # Links are like /games/view/turrican
                if href.startswith('/games/view/'):
                    game_url = urljoin(self.base_url, href)
                    # Extract game name from h4
                    h4 = link.find('h4')
                    if h4:
                        game_name = h4.get_text(strip=True)
                    else:
                        game_name = link.get_text(strip=True)
                    
                    if game_url and game_name:
                        game_data[game_url] = game_name
        
        return game_data
    
    def slugify_version(self, version_name: str) -> str:
        """Convert version name to a slug for use in gameid
        E.g., "ECS / OCS" -> "ecs-ocs", "CD32" -> "cd32"
        """
        # Convert to lowercase
        slug = version_name.lower()
        # Replace " / " with "-"
        slug = slug.replace(' / ', '-')
        # Replace spaces with "-"
        slug = slug.replace(' ', '-')
        # Remove any other special characters
        slug = re.sub(r'[^a-z0-9-]', '', slug)
        # Remove duplicate dashes
        slug = re.sub(r'-+', '-', slug)
        # Remove leading/trailing dashes
        slug = slug.strip('-')
        return slug
    
    def _get_version_variants(self, version_name: str) -> List[str]:
        """Build version name variants to match in data-title attributes
        For "ECS / OCS", returns ["ECS / OCS", "ECS", "OCS", "ECS/OCS"]
        """
        version_variants = [version_name]
        if ' / ' in version_name:
            parts = version_name.split(' / ')
            version_variants.extend(parts)
        # Also try without spaces
        version_variants.append(version_name.replace(' ', ''))
        return version_variants
    
    def _matches_version(self, data_title: str, version_variants: List[str]) -> bool:
        """Check if data_title matches any of the version variants"""
        for variant in version_variants:
            if data_title.lower().startswith(variant.lower()):
                return True
        return False
    
    def _to_absolute_url(self, url: str, strip_query: bool = True) -> str:
        """Convert relative URL to absolute URL and optionally strip query parameters"""
        if url.startswith('/'):
            full_url = urljoin(self.base_url, url)
        elif url.startswith('http'):
            full_url = url
        else:
            full_url = urljoin(self.base_url, '/' + url)
        
        # Strip query parameters (e.g., ?v=1234)
        if strip_query and '?' in full_url:
            full_url = full_url.split('?')[0]
        
        return full_url
    
    def _is_generic_label(self, label: str) -> bool:
        """Check if label is generic (no version prefix), like 'no. 1' or 'Box scan no. 1'"""
        label_lower = label.lower().strip()
        # Generic labels start with "no." or contain "scan no."
        if label_lower.startswith('no.'):
            return True
        if re.match(r'^(box|disk|screen)\s+scan\s+no\.', label_lower):
            return True
        return False
    
    def extract_version_images(self, soup: BeautifulSoup, version_name: str) -> Tuple[Optional[str], Optional[str]]:
        """Extract titleshot and screenshot for a specific version from the image carousel
        
        Images have data-title like "ECS no. 1", "AGA no. 2", "CD32 no. 1"
        - "no. 1" = titleshot
        - "no. 2" = screenshot
        
        For versions like "ECS / OCS", images might be labeled just "ECS"
        For compilations/single-version games, images may be labeled just "no. 1", "no. 2"
        """
        titleshot = None
        screenshot = None
        
        version_variants = self._get_version_variants(version_name)
        is_standard = version_name == "Standard"
        
        # Find the screenshot carousel
        dbs_screens = soup.find('div', id='dbs_screens')
        
        screen_links = []
        if dbs_screens:
            # Get all screen divs with links
            screen_divs = dbs_screens.find_all('div', class_='screen')
            for screen_div in screen_divs:
                link = screen_div.find('a', {'data-title': True})
                if not link:
                    link = screen_div.find('a', href=True)
                if link:
                    screen_links.append(link)
        
        # Fallback: find links by href pattern /screen/
        if not screen_links:
            screen_links = soup.find_all('a', href=re.compile(r'/screen/.*\.(png|jpg)'))
        
        for link in screen_links:
            img = link.find('img')
            if not img:
                continue
            
            # Get label from data-title or img alt
            label = link.get('data-title', '')
            if not label:
                label = img.get('alt', '')
            
            img_src = img.get('src', '')
            if not img_src:
                # Try href as image source
                href = link.get('href', '')
                if href:
                    img_src = href
            
            if not img_src:
                continue
            
            img_url = self._to_absolute_url(img_src)
            
            # Check if this image matches our version
            # For "Standard" version, also accept generic labels without version prefix
            matches = self._matches_version(label, version_variants)
            if not matches and is_standard and self._is_generic_label(label):
                matches = True
            
            if matches:
                # Check if it's titleshot (no. 1) or screenshot (no. 2)
                if 'no. 1' in label.lower():
                    if not titleshot:
                        titleshot = img_url
                elif 'no. 2' in label.lower():
                    if not screenshot:
                        screenshot = img_url
        
        return titleshot, screenshot
    
    def extract_version_media(self, soup: BeautifulSoup, version_name: str) -> Dict[str, List[str]]:
        """Extract boxfront, boxback, and cartridge media for a specific version
        
        Box images:
        - data-title like "ECS no. 1", data-footer contains "(front)" or "(back)"
        - href points to full resolution: /box/1501-1600/1535_box0.jpg
        - For compilations: img alt like "Box scan no. 1" (no version prefix)
        
        Disk/Cartridge images:
        - alt contains "Disk scan VERSION" or just "Disk scan no. X" for compilations
        - href points to full resolution: /disk/1501-1600/1535_disk0.jpg
        
        Returns dict with lists: {'boxfront': [...], 'boxback': [...], 'cartridge': [...], 'manual': [...], 'map': [...]}
        """
        media = {
            'boxfront': [],
            'boxback': [],
            'cartridge': [],
            'manual': [],
            'map': []
        }
        
        version_variants = self._get_version_variants(version_name)
        is_standard = version_name == "Standard"
        
        # Extract box scans (boxfront and boxback)
        # First try: Look for links in box-gallery with data-title matching version
        box_links = soup.find_all('a', {'data-gallery': 'box-gallery', 'data-title': True})
        
        # Fallback: Look for links by href pattern /box/
        if not box_links:
            box_links = soup.find_all('a', href=re.compile(r'/box/.*\.(jpg|png)'))
        
        # Track if we found explicit front/back labels
        has_explicit_labels = False
        boxfront_no_label = None  # First image without label (no. 1)
        boxback_no_label = None   # Second image without label (no. 2)
        
        for link in box_links:
            data_title = link.get('data-title', '')
            data_footer = link.get('data-footer', '')
            href = link.get('href', '')
            
            if not href:
                continue
            
            # Get label from data-title or img alt
            label = data_title
            if not label:
                img = link.find('img')
                if img:
                    label = img.get('alt', '')
            
            # Check if this matches our version
            matches = self._matches_version(label, version_variants)
            # For "Standard" version, also accept generic labels
            if not matches and is_standard and self._is_generic_label(label):
                matches = True
            
            if not matches:
                continue
            
            # Get full resolution URL from href (not the preview thumbnail)
            full_url = self._to_absolute_url(href)
            
            # Determine if front or back based on data-footer first
            if '(front)' in data_footer.lower():
                has_explicit_labels = True
                if full_url not in media['boxfront']:
                    media['boxfront'].append(full_url)
            elif '(back)' in data_footer.lower():
                has_explicit_labels = True
                if full_url not in media['boxback']:
                    media['boxback'].append(full_url)
            else:
                # No explicit front/back in footer - track first two by number
                # Only use these if no explicit labels are found
                match = re.search(r'no\.\s*(\d+)', label.lower())
                if match:
                    num = int(match.group(1))
                    if num == 1 and boxfront_no_label is None:
                        boxfront_no_label = full_url
                    elif num == 2 and boxback_no_label is None:
                        boxback_no_label = full_url
        
        # If no explicit labels were found, use the first two images
        if not has_explicit_labels:
            if boxfront_no_label and boxfront_no_label not in media['boxfront']:
                media['boxfront'].append(boxfront_no_label)
            if boxback_no_label and boxback_no_label not in media['boxback']:
                media['boxback'].append(boxback_no_label)
        
        # Extract disk/cartridge scans
        # First try: Look for links in disk-gallery with data-title matching version
        disk_links = soup.find_all('a', {'data-gallery': 'disk-gallery', 'data-title': True})
        
        # Fallback: Look for links by href pattern /disk/
        if not disk_links:
            disk_links = soup.find_all('a', href=re.compile(r'/disk/.*\.(jpg|png)'))
        
        for link in disk_links:
            data_title = link.get('data-title', '')
            href = link.get('href', '')
            
            if not href:
                continue
            
            # Get label from data-title or img alt
            label = data_title
            img = link.find('img')
            if img:
                alt = img.get('alt', '')
                if not label:
                    label = alt
            
            # Check if this matches our version
            matches = self._matches_version(label, version_variants)
            # For "Standard" version, also accept generic labels like "Disk scan no. 1"
            if not matches and is_standard:
                if self._is_generic_label(label) or 'disk scan' in label.lower():
                    matches = True
            
            if not matches:
                continue
            
            # Get full resolution URL from href
            full_url = self._to_absolute_url(href)
            if full_url not in media['cartridge']:
                media['cartridge'].append(full_url)
        
        # Extract manuals
        # Look for links to /manual/.../*.pdf with img alt matching version
        manual_links = soup.find_all('a', href=re.compile(r'/manual/.*\.pdf'))
        for link in manual_links:
            href = link.get('href', '')
            if not href:
                continue
            
            # Check if this matches our version by looking at the img alt text
            img = link.find('img')
            label = ''
            if img:
                label = img.get('alt', '')
            
            # Check version match
            matches = self._matches_version(label, version_variants)
            # For "Standard" version, also accept generic labels
            if not matches and is_standard and (self._is_generic_label(label) or not label):
                matches = True
            
            if not matches:
                continue
            
            # Get full resolution URL from href
            full_url = self._to_absolute_url(href)
            if full_url not in media['manual']:
                media['manual'].append(full_url)
        
        # Extract maps
        # Look for links to /map/.../*.png with img alt matching version
        map_links = soup.find_all('a', href=re.compile(r'/map/.*\.(png|jpg)'))
        for link in map_links:
            href = link.get('href', '')
            if not href:
                continue
            
            # Check if this matches our version by looking at the img alt text
            img = link.find('img')
            label = ''
            if img:
                label = img.get('alt', '')
            
            # Check version match
            matches = self._matches_version(label, version_variants)
            # For "Standard" version, also accept generic labels
            if not matches and is_standard and (self._is_generic_label(label) or not label):
                matches = True
            
            if not matches:
                continue
            
            # Get full resolution URL from href
            full_url = self._to_absolute_url(href)
            if full_url not in media['map']:
                media['map'].append(full_url)
        
        return media
    
    def extract_version_rating(self, soup: BeautifulSoup, version_name: str) -> Optional[float]:
        """Extract rating for a specific version from the score_list section
        
        Score format: "Lore Score: 87%" in a card with version name header
        Returns rating normalized to /5 scale (divide percentage by 20)
        """
        version_variants = self._get_version_variants(version_name)
        
        # Find the score_list div
        score_list = soup.find('div', id='score_list')
        if not score_list:
            return None
        
        # Find all score cards
        score_cards = score_list.find_all('div', class_='card')
        
        for card in score_cards:
            # Find version name in card header
            card_header = card.find('div', class_='card-header')
            if not card_header:
                continue
            
            header_h3 = card_header.find('h3')
            if not header_h3:
                continue
            
            card_version = header_h3.get_text(strip=True)
            
            # Check if this card matches our version
            matches = False
            for variant in version_variants:
                if card_version.lower() == variant.lower():
                    matches = True
                    break
            
            if not matches:
                continue
            
            # Find the Lore Score in card body
            card_body = card.find('div', class_='card-body')
            if not card_body:
                continue
            
            # Look for h3 containing "Lore Score:"
            score_elements = card_body.find_all('h3')
            for score_el in score_elements:
                score_text = score_el.get_text(strip=True)
                if 'Lore Score:' in score_text:
                    # Extract percentage: "Lore Score: 87%" -> 87
                    match = re.search(r'Lore Score:\s*(\d+)%', score_text)
                    if match:
                        percentage = int(match.group(1))
                        # Normalize to /5 scale
                        rating = percentage / 20.0
                        return rating
        
        return None
    
    def extract_version_cheats(self, soup: BeautifulSoup, version_name: str) -> Optional[str]:
        """Extract cheats for a specific version from the cheat_list section
        
        Cheats are in divs with class 'cheat_version_list', with version name in h5
        Returns the cheat text as a string
        """
        version_variants = self._get_version_variants(version_name)
        
        # Find the cheat_list div
        cheat_list = soup.find('div', id='cheat_list')
        if not cheat_list:
            return None
        
        # Find all cheat version blocks
        cheat_blocks = cheat_list.find_all('div', class_='cheat_version_list')
        
        for block in cheat_blocks:
            # Find version name in header (h5)
            header = block.find('div', class_='cheat_version_header')
            if not header:
                continue
            
            version_h5 = header.find('h5')
            if not version_h5:
                continue
            
            block_version = version_h5.get_text(strip=True)
            
            # Check if this block matches our version
            matches = False
            for variant in version_variants:
                if block_version.lower() == variant.lower():
                    matches = True
                    break
            
            if not matches:
                continue
            
            # Find the cheat text div
            cheat_div = block.find('div', class_='cheat')
            if not cheat_div:
                continue
            
            # Extract all paragraph text, join with newlines
            paragraphs = cheat_div.find_all('p')
            if paragraphs:
                cheat_texts = []
                for p in paragraphs:
                    text = p.get_text(strip=True)
                    # Skip empty paragraphs (like &nbsp;)
                    if text and text != '\xa0':
                        cheat_texts.append(text)
                if cheat_texts:
                    return '\n'.join(cheat_texts)
            else:
                # Fallback to getting all text from cheat div
                text = cheat_div.get_text(strip=True)
                if text:
                    return text
        
        return None
    
    def extract_version_info(self, version_block, soup: BeautifulSoup, base_game_id: str, base_game_name: str, game_url: str) -> Optional[Dict]:
        """Extract information for a single version block"""
        game_info = {
            'url': game_url,
            'gameid': None,
            'name': None,
            'developer': None,
            'genre': None,
            'release_date': None,
            'publisher': None,
            'description': None,
            'titleshot': None,
            'screenshot': None,
            'boxfront': [],
            'boxback': [],
            'cartridge': [],
            'manual': [],
            'map': [],
            'rating': None,
            'cheats': None,
        }
        
        # Extract version name (e.g., "ECS / OCS", "AGA", "CD32")
        version_name = None
        version_header = version_block.find('div', class_='version_header_hardware')
        if version_header:
            h3 = version_header.find('h3')
            if h3:
                span = h3.find('span')
                if span:
                    version_name = span.get_text(strip=True)
        
        if not version_name:
            # Try to get version name from the version_header div
            version_header_div = version_block.find('div', class_='version_header')
            if version_header_div:
                h3 = version_header_div.find('h3')
                if h3:
                    span = h3.find('span')
                    if span:
                        version_name = span.get_text(strip=True)
        
        if not version_name:
            # Fallback: try to get version name directly from h3 text (without span)
            version_header = version_block.find('div', class_='version_header_hardware')
            if version_header:
                h3 = version_header.find('h3')
                if h3:
                    version_name = h3.get_text(strip=True)
            
            if not version_name:
                version_header_div = version_block.find('div', class_='version_header')
                if version_header_div:
                    h3 = version_header_div.find('h3')
                    if h3:
                        version_name = h3.get_text(strip=True)
        
        if not version_name:
            # Last resort: use "Standard" as default version name
            print(f"⚠️  Could not extract version name for {base_game_name}, using default")
            version_name = "Standard"
        
        # Build gameid and name
        version_slug = self.slugify_version(version_name)
        game_info['gameid'] = f"{base_game_id}-{version_slug}"
        game_info['name'] = f"{base_game_name} ({version_name})"
        
        # Extract developer from version info section
        version_info_div = version_block.find('div', class_='content_version_info')
        if version_info_div:
            rows = version_info_div.find_all('div', class_='row')
            for row in rows:
                label = row.find('label')
                if label and 'Developers' in label.get_text():
                    # Find developer link
                    dev_link = row.find('a', href=re.compile(r'/developers/view/'))
                    if dev_link:
                        game_info['developer'] = dev_link.get_text(strip=True)
                        # Skip "Unknown" as developer
                        if game_info['developer'] and game_info['developer'].lower() == 'unknown':
                            game_info['developer'] = None
                    break
        
        
        # Extract release date and publisher from release list
        release_list = version_block.find('div', class_='release_list')
        if release_list:
            # Find first release item
            first_release = release_list.find('div', class_='release_list_item')
            if first_release:
                # Extract year
                divs = first_release.find_all('div', class_='my-auto')
                # The pattern is: label, value, label, value, ...
                # Year is after "Year" label, Publisher is after "Publisher" label
                labels = first_release.find_all('label')
                for i, label in enumerate(labels):
                    label_text = label.get_text(strip=True)
                    # Find the next sibling div with class my-auto
                    next_div = label.find_next_sibling('div', class_='my-auto')
                    if next_div:
                        value = next_div.get_text(strip=True)
                        
                        if label_text == 'Year' and value:
                            # Convert year to "01-01-YYYY" format
                            if value.isdigit():
                                game_info['release_date'] = f"01-01-{value}"
                            elif value.strip() == '?':
                                # Set to None for unknown dates (will be null in JSON)
                                game_info['release_date'] = None
                            else:
                                game_info['release_date'] = value
                        
                        elif label_text == 'Publisher':
                            # Publisher might be a link
                            pub_link = next_div.find('a')
                            if pub_link:
                                game_info['publisher'] = pub_link.get_text(strip=True)
                            elif value:
                                game_info['publisher'] = value
        
        # Extract description/notes
        notes_div = version_block.find('div', class_='notes')
        if notes_div:
            content_notes = notes_div.find('div', class_='content_notes')
            if content_notes:
                # Get all text, but clean it up
                description = content_notes.get_text(strip=True)
                # Remove "Notes:" prefix if present
                description = re.sub(r'^Notes:\s*', '', description, flags=re.I)
                if description:
                    game_info['description'] = description
        
        # Extract images for this version
        titleshot, screenshot = self.extract_version_images(soup, version_name)
        game_info['titleshot'] = titleshot
        game_info['screenshot'] = screenshot
        
        # Extract media (boxfront, boxback, cartridge, manual, map) for this version
        media = self.extract_version_media(soup, version_name)
        game_info['boxfront'] = media['boxfront']
        game_info['boxback'] = media['boxback']
        game_info['cartridge'] = media['cartridge']
        game_info['manual'] = media['manual']
        game_info['map'] = media['map']
        
        # Extract rating for this version
        game_info['rating'] = self.extract_version_rating(soup, version_name)
        
        # Extract cheats for this version
        game_info['cheats'] = self.extract_version_cheats(soup, version_name)
        
        # Final cleanup - convert empty lists to None, empty strings to None
        for key in game_info:
            value = game_info.get(key)
            if value == '' or value == []:
                game_info[key] = None
        
        return game_info
    
    def extract_game_info(self, soup: BeautifulSoup, game_url: str, game_name_from_list: str) -> List[Dict]:
        """Extract game information from detail page
        Returns a list of game entries (one per version)
        """
        game_entries = []
        
        # Extract base game ID from URL (e.g., "turrican" from "/games/view/turrican")
        base_game_id = game_url.split('/games/view/')[-1].split('?')[0].split('#')[0].strip()
        
        # Get game name from page (may differ from list)
        base_game_name = game_name_from_list
        h1 = soup.find('h1')
        if h1:
            page_name = h1.get_text(strip=True)
            if page_name:
                base_game_name = page_name
        
        # Extract genre/category at game level (shared by all versions)
        # Located in content_genre div: <label>Category</label> -> <a href="/games/list/?category-id=...">Genre</a>
        game_genre = None
        content_genre = soup.find('div', id='content_genre')
        if content_genre:
            category_link = content_genre.find('a', href=re.compile(r'/games/list/\?category-id='))
            if category_link:
                game_genre = category_link.get_text(strip=True)
        
        # Fallback: search anywhere for Category label
        if not game_genre:
            all_labels = soup.find_all('label')
            for label in all_labels:
                if 'Category' in label.get_text():
                    parent_row = label.find_parent('div', class_='row')
                    if parent_row:
                        category_link = parent_row.find('a', href=re.compile(r'/games/list/\?category-id='))
                        if category_link:
                            game_genre = category_link.get_text(strip=True)
                    break
        
        # Find all version blocks
        # Version blocks have id like "version_list_171" and class "version_list"
        version_blocks = soup.find_all('div', class_='version_list', id=re.compile(r'version_list_\d+'))
        
        if not version_blocks:
            # No versions found - create single entry with base info
            print(f"ℹ️  No version blocks found for {base_game_name}")
            game_info = {
                'url': game_url,
                'gameid': base_game_id,
                'name': base_game_name,
                'developer': None,
                'genre': game_genre,
                'release_date': None,
                'publisher': None,
                'description': None,
                'titleshot': None,
                'screenshot': None,
                'boxfront': None,
                'boxback': None,
                'cartridge': None,
                'manual': None,
                'map': None,
                'rating': None,
                'cheats': None,
            }
            
            # Try to extract basic info from page
            # Extract first screenshot as titleshot
            dbs_screens = soup.find('div', id='dbs_screens')
            if dbs_screens:
                first_img = dbs_screens.find('img')
                if first_img and first_img.get('src'):
                    src = first_img['src']
                    if src.startswith('/'):
                        game_info['titleshot'] = urljoin(self.base_url, src)
                    elif src.startswith('http'):
                        game_info['titleshot'] = src
            
            game_entries.append(game_info)
            return game_entries
        
        # Handle single vs multiple versions
        if len(version_blocks) == 1:
            # Single version - use base gameid without version suffix
            version_block = version_blocks[0]
            game_info = self.extract_version_info(version_block, soup, base_game_id, base_game_name, game_url)
            if game_info:
                # For single version, keep original gameid and name
                game_info['gameid'] = base_game_id
                game_info['name'] = base_game_name
                # Apply game-level genre
                game_info['genre'] = game_genre
                game_entries.append(game_info)
            else:
                print(f"⚠️  Failed to extract version info for single-version game: {base_game_name}")
        else:
            # Multiple versions - create entry for each with version suffix
            extracted_count = 0
            for version_block in version_blocks:
                game_info = self.extract_version_info(version_block, soup, base_game_id, base_game_name, game_url)
                if game_info:
                    # Apply game-level genre to each version
                    game_info['genre'] = game_genre
                    game_entries.append(game_info)
                    extracted_count += 1
            
            if extracted_count == 0:
                print(f"⚠️  Failed to extract any version info for multi-version game: {base_game_name} ({len(version_blocks)} blocks found)")
        
        return game_entries
    
    def scrape_game(self, game_url: str, game_name_from_list: str) -> List[Dict]:
        """Scrape a single game page
        Returns list of game entries (one per version)
        """
        # Check if already processed
        if game_url in self.progress_data['processed_games']:
            print(f"⏭️  Skipping already processed: {game_url}")
            return []
        
        soup = self.get_page(game_url)
        if not soup:
            return []
        
        game_entries = self.extract_game_info(soup, game_url, game_name_from_list)
        
        if game_entries:
            # Add all entries to database (sanitize strings to remove control chars / NULL)
            for game_info in game_entries:
                _sanitize_dict_strings(game_info)
                gameid = game_info.get('gameid')
                if gameid:
                    self.games_db[gameid] = game_info
                    game_name = game_info.get('name', gameid)
                    print(f"✅ Scraped: {game_name} - Dev: {game_info.get('developer', 'N/A')} - Pub: {game_info.get('publisher', 'N/A')} - Year: {game_info.get('release_date', 'N/A')}")
            
            # Mark as processed
            self.progress_data['processed_games'].add(game_url)
            self.progress_data['total_games_collected'] = len(self.games_db)
            
            # Save after each game
            self.save_database()
            self.save_progress()
        else:
            # No entries could be extracted - log this and still mark as processed to avoid retrying
            print(f"⚠️  No game entries could be extracted from: {game_url}")
            self.progress_data['processed_games'].add(game_url)
            self.save_progress()
        
        return game_entries
    
    def scrape_all_pages(self):
        """Scrape all list pages"""
        games_scraped = 0
        start_page = self.progress_data.get('current_page', 1)
        max_page = self.progress_data.get('max_page', 227)
        
        print(f"\n📖 Starting to scrape from page {start_page} to {max_page}")
        
        for page in range(start_page, max_page + 1):
            url = f"{self.base_url}/games/list/?view=grid&page={page}"
            
            print(f"\n{'='*60}")
            print(f"📌 Processing page: {page}/{max_page}")
            print(f"{'='*60}")
            
            soup = self.get_page(url)
            if not soup:
                print(f"⚠️  Failed to fetch page {page}")
                self.progress_data['current_page'] = page
                self.save_progress()
                time.sleep(2)
                continue
            
            # Extract game links and names from list page
            game_data = self.get_game_links_from_page(soup)
            
            if not game_data:
                print(f"ℹ️  No games found on page {page}")
                self.progress_data['current_page'] = page + 1
                self.save_progress()
                time.sleep(1)
                continue
            
            print(f"📋 Found {len(game_data)} games on page {page}")
            
            # Scrape each game
            for game_url, game_name in game_data.items():
                entries = self.scrape_game(game_url, game_name)
                games_scraped += len(entries)
                time.sleep(0.5)  # Rate limiting between games
            
            # Update progress
            self.progress_data['current_page'] = page + 1
            self.save_progress()
            
            time.sleep(1)  # Rate limiting between pages
        
        return games_scraped
    
    def run_scraper(self, resume: bool = True):
        """Run the scraper"""
        print("🚀 Starting Hall of Light (HOL) scraper...")
        
        # Load existing data
        self.load_database()
        if resume:
            self.load_progress()
        
        self.progress_data['status'] = 'running'
        self.save_progress()
        
        try:
            games_count = self.scrape_all_pages()
            
            self.progress_data['status'] = 'completed'
            print(f"\n🎉 Scraping completed! Total entries: {games_count}")
            
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
            # Cleanup Selenium if used
            if self.driver:
                try:
                    self.driver.quit()
                except:
                    pass

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Hall of Light (HOL) Amiga Database Scraper')
    parser.add_argument('--fresh', action='store_true', help='Start fresh (clear progress)')
    parser.add_argument('--resume', action='store_true', help='Resume from last position')
    parser.add_argument('--status', action='store_true', help='Show current scraper status')
    parser.add_argument('--selenium', action='store_true', default=True, help='Use Selenium for browser automation (default: True)')
    parser.add_argument('--no-selenium', action='store_true', help='Disable Selenium, use requests only')
    parser.add_argument('--cookies', type=str, default='cookies.txt', help='Path to cookies.txt file')
    
    args = parser.parse_args()
    
    # Initialize scraper - Selenium is default due to Anubis bot protection
    use_selenium = not args.no_selenium
    if use_selenium and not HAS_SELENIUM:
        print("⚠️  Selenium not installed. Install with: pip install selenium")
        print("    Also need ChromeDriver installed.")
        print("    Falling back to requests (may not work due to bot protection).")
        use_selenium = False
    
    scraper = HOLScraper(use_selenium=use_selenium, cookies_file=args.cookies)
    
    if args.status:
        scraper.load_progress()
        scraper.load_database()
        print("\n📊 Scraper Status:")
        print(f"   Status: {scraper.progress_data['status']}")
        print(f"   Current page: {scraper.progress_data.get('current_page', 1)}/{scraper.progress_data.get('max_page', 227)}")
        print(f"   Games processed: {len(scraper.progress_data.get('processed_games', []))}")
        print(f"   Total entries in DB: {len(scraper.games_db)}")
        if scraper.progress_data.get('last_run_timestamp'):
            import datetime
            last_run = datetime.datetime.fromtimestamp(scraper.progress_data['last_run_timestamp'])
            print(f"   Last run: {last_run}")
        print(f"\n📦 Dependencies:")
        print(f"   cloudscraper: {'✅ Available' if HAS_CLOUDSCRAPER else '❌ Not installed'}")
        print(f"   selenium: {'✅ Available' if HAS_SELENIUM else '❌ Not installed'}")
        return
    
    resume = not args.fresh
    if args.fresh:
        print("🆕 Starting fresh (clearing progress)")
        if os.path.exists(scraper.progress_file):
            os.remove(scraper.progress_file)
    
    scraper.run_scraper(resume=resume)

if __name__ == "__main__":
    main()
