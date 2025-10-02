#!/usr/bin/env python3
"""
Lemon64 Web Spider
Scrapes game data from https://www.lemon64.com/games/list.php
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
from typing import Dict, List, Optional

class Lemon64Spider:
    def __init__(self):
        self.base_url = "https://www.lemon64.com"
        self.list_url = "https://www.lemon64.com/games/list.php"
        self.games_db = {}
        self.session = requests.Session()
        
        # Progress tracking
        self.progress_file = "spider_progress.json"
        self.progress_data = {
            "last_page_offset": 0,
            "last_page_count": 0,
            "total_games_collected": 0,
            "last_run_timestamp": None,
            "status": "not_started"  # not_started, running, completed, interrupted
        }
        
        # Realistic browser user agents (rotated randomly)
        self.user_agents = [
            # Chrome on Windows
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
            
            # Chrome on macOS
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            
            # Firefox on Windows
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:119.0) Gecko/20100101 Firefox/119.0',
            
            # Firefox on macOS
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:120.0) Gecko/20100101 Firefox/120.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:119.0) Gecko/20100101 Firefox/119.0',
            
            # Safari on macOS
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15',
            
            # Edge on Windows
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0'
        ]
        
        # Set up realistic browser headers
        self._setup_browser_headers()
    
    def _setup_browser_headers(self):
        """Set up realistic browser headers"""
        # Select a random user agent
        user_agent = random.choice(self.user_agents)
        
        # Set comprehensive browser headers
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
            'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"'
        })
        
        # Set up session with realistic settings
        self.session.max_redirects = 10
        self.session.timeout = 30
        
        print(f"🌐 Using User-Agent: {user_agent[:50]}...")
    
    def _randomize_delay(self):
        """Add delay to maintain 2 pages per second rate"""
        # Fixed delay of 0.5 seconds for exactly 2 pages per second
        delay = 0.5
        time.sleep(delay)
        return delay
    
    def _rotate_user_agent(self):
        """Rotate to a different user agent for variety"""
        new_user_agent = random.choice(self.user_agents)
        self.session.headers.update({'User-Agent': new_user_agent})
        print(f"🔄 Rotated to new User-Agent: {new_user_agent[:50]}...")
        
    def get_page(self, offset: int = 0) -> Optional[BeautifulSoup]:
        """Fetch a single page with the given offset"""
        params = {'lineoffset': offset}
        
        try:
            print(f"📄 Fetching page with offset {offset}...")
            
            # Add referer header for more realistic browsing
            if offset > 0:
                self.session.headers.update({
                    'Referer': f"{self.list_url}?lineoffset={max(0, offset-20)}"
                })
            
            # Make the request with realistic browser behavior
            response = self.session.get(
                self.list_url, 
                params=params, 
                timeout=30,
                allow_redirects=True,
                stream=False
            )
            response.raise_for_status()
            
            # Check if we got a valid response
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                print(f"✅ Successfully loaded page (Status: {response.status_code})")
                return soup
            else:
                print(f"⚠️  Unexpected status code: {response.status_code}")
                return None
            
        except requests.exceptions.Timeout:
            print(f"⏰ Timeout fetching page with offset {offset}")
            return None
        except requests.exceptions.ConnectionError:
            print(f"🔌 Connection error fetching page with offset {offset}")
            return None
        except requests.exceptions.HTTPError as e:
            print(f"🚫 HTTP error fetching page with offset {offset}: {e}")
            return None
        except requests.RequestException as e:
            print(f"❌ Error fetching page with offset {offset}: {e}")
            return None
    
    def has_next_page(self, soup: BeautifulSoup) -> bool:
        """Check if there's a next page available"""
        next_page = soup.find('div', class_='page-next')
        return next_page is not None
    
    def get_next_offset(self, soup: BeautifulSoup) -> Optional[int]:
        """Extract the next page offset from the page"""
        next_page = soup.find('div', class_='page-next')
        if not next_page:
            return None
            
        # Look for the next page link
        next_link = next_page.find('a')
        if not next_link:
            return None
            
        href = next_link.get('href', '')
        # Extract offset from URL like "?lineoffset=20"
        match = re.search(r'lineoffset=(\d+)', href)
        if match:
            return int(match.group(1))
        return None
    
    def extract_game_data(self, game_card) -> Optional[Dict]:
        """Extract game data from a single game card"""
        try:
            # Get game ID from the div id attribute
            game_id = None
            if game_card.get('id'):
                match = re.search(r'game-(\d+)', game_card.get('id', ''))
                if match:
                    game_id = int(match.group(1))
            
            if not game_id:
                print(f"⚠️  Could not extract game ID from: {game_card.get('id', 'no-id')}")
                return None
            
            # Extract game title - try multiple approaches
            title = None
            detail_url = None
            
            # Method 1: Look for game-grid-title div
            title_div = game_card.find('div', class_='game-grid-title')
            if title_div:
                title_link = title_div.find('a')
                if title_link:
                    title = title_link.get_text(strip=True)
                    detail_url = title_link.get('href')
            
            # Method 2: Look for any link with game title
            if not title:
                title_link = game_card.find('a')
                if title_link:
                    title = title_link.get_text(strip=True)
                    detail_url = title_link.get('href')
            
            # Method 3: Look for any text that might be a title
            if not title:
                # Look for text in various elements
                for elem in game_card.find_all(['a', 'div', 'span']):
                    text = elem.get_text(strip=True)
                    if text and len(text) > 3 and not text.isdigit():
                        title = text
                        detail_url = elem.get('href') if elem.name == 'a' else None
                        break
            
            if not title:
                print(f"⚠️  Could not extract title for game ID {game_id}")
                return None
            
            # Process detail URL
            if detail_url:
                detail_url = urljoin(self.base_url, detail_url)
            
            # Extract screenshot URL
            screenshot_url = None
            screenshot_img = game_card.find('img', class_='grid-screenshot')
            if screenshot_img:
                screenshot_src = screenshot_img.get('src')
                if screenshot_src:
                    screenshot_url = urljoin(self.base_url, screenshot_src)
            else:
                # Try to find any img tag
                screenshot_img = game_card.find('img')
                if screenshot_img:
                    screenshot_src = screenshot_img.get('src')
                    if screenshot_src:
                        screenshot_url = urljoin(self.base_url, screenshot_src)
            
            # Extract year and publisher from grid-info
            grid_info = game_card.find('div', class_='grid-info')
            year = None
            publisher = None
            
            if grid_info:
                # Extract year from the first link
                year_link = grid_info.find('a', class_='grid-credits')
                if year_link:
                    year_text = year_link.get_text(strip=True)
                    # Try to extract year (4 digits)
                    year_match = re.search(r'\b(19|20)\d{2}\b', year_text)
                    if year_match:
                        year = int(year_match.group())
                
                # Extract publisher from the second link
                all_links = grid_info.find_all('a', class_='grid-credits')
                if len(all_links) > 1:
                    publisher = all_links[1].get_text(strip=True)
            
            # Extract genre
            genre_div = game_card.find('div', class_='grid-category')
            genre = None
            if genre_div:
                genre_link = genre_div.find('a')
                if genre_link:
                    genre = genre_link.get_text(strip=True)
            
            # Extract rating
            rating = None
            rating_span = game_card.find('span', class_='grid-vote-score')
            if rating_span:
                rating_text = rating_span.get_text(strip=True)
                # Extract numeric rating
                rating_match = re.search(r'(\d+\.?\d*)', rating_text)
                if rating_match:
                    rating = float(rating_match.group(1))
            
            # Extract comment count
            comment_count = None
            comment_span = game_card.find('span', class_='grid-comment')
            if comment_span:
                comment_text = comment_span.get_text(strip=True)
                comment_match = re.search(r'(\d+)', comment_text)
                if comment_match:
                    comment_count = int(comment_match.group(1))
            
            game_data = {
                'id': game_id,
                'title': title,
                'year': year,
                'publisher': publisher,
                'genre': genre,
                'rating': rating,
                'comment_count': comment_count,
                'screenshot_url': screenshot_url,
                'detail_url': detail_url
            }
            
            return game_data
            
        except Exception as e:
            print(f"⚠️  Error extracting game data: {e}")
            return None
    
    def scrape_page(self, soup: BeautifulSoup, detailed_info: bool = True) -> List[Dict]:
        """Scrape all games from a single page"""
        games = []
        
        # Try multiple selectors to find game cards
        game_cards = []
        
        # Primary selector (exact match)
        game_cards = soup.find_all('div', class_='col-6 col-md-3 game-col game-col-4')
        print(f"🎮 Found {len(game_cards)} game cards with exact selector")
        
        # If we don't find enough, try more flexible selectors
        if len(game_cards) < 20:  # Expect around 40 games per page
            print("🔍 Trying more flexible selectors...")
            
            # Try partial class match
            game_cards_flexible = soup.find_all('div', class_=lambda x: x and 'game-col' in x)
            print(f"🎮 Found {len(game_cards_flexible)} game cards with flexible selector")
            
            # Try finding by ID pattern
            game_cards_by_id = soup.find_all('div', id=lambda x: x and x.startswith('game-'))
            print(f"🎮 Found {len(game_cards_by_id)} divs with game- ID pattern")
            
            # Use the one with most results
            if len(game_cards_flexible) > len(game_cards):
                game_cards = game_cards_flexible
                print(f"✅ Using flexible selector: {len(game_cards)} cards")
            elif len(game_cards_by_id) > len(game_cards):
                game_cards = game_cards_by_id
                print(f"✅ Using ID-based selector: {len(game_cards)} cards")
        
        # Debug: Show some sample HTML structure
        if len(game_cards) < 10:
            print("🔍 Debug: Looking for game-related elements...")
            all_divs = soup.find_all('div')
            game_related = [div for div in all_divs if div.get('class') and any('game' in cls.lower() for cls in div.get('class', []))]
            print(f"🔍 Found {len(game_related)} divs with 'game' in class name")
            
            # Show first few examples
            for i, div in enumerate(game_related[:3]):
                print(f"🔍 Example {i+1}: {div.get('class')} - ID: {div.get('id', 'None')}")
        
        for card in game_cards:
            game_data = self.extract_game_data(card)
            if game_data:
                # Extract detailed information if enabled and we have a detail URL
                if detailed_info and game_data.get('detail_url'):
                    print(f"🔍 Fetching detailed info for: {game_data['title']}")
                    detailed_data = self.extract_detailed_game_info(game_data['detail_url'])
                    
                    # Merge detailed info into game data
                    game_data.update(detailed_data)
                    
                    # Add a small delay between detail page requests
                    time.sleep(0.2)
                
                games.append(game_data)
                print(f"✅ Extracted: {game_data['title']} (ID: {game_data['id']})")
                
                # Save database after each game is processed
                self.games_db[str(game_data['id'])] = game_data
                self.save_database(self.output_file, verbose=False)
            else:
                print(f"❌ Failed to extract game data from card: {card.get('id', 'unknown')}")
        
        return games
    
    def extract_detailed_game_info(self, game_url: str) -> Dict:
        """Extract detailed information from a game's detail page"""
        detailed_info = {
            'releasedate': None,
            'publisher': None,
            'developer': None,
            'players': None,
            'language': None,
            'retail_price': None,
            'youtube_links': [],
            'rating': None,
            'nbreview': None,
            'screenshots': [],
            'covers': []
        }
        
        try:
            print(f"🔍 Fetching detailed info from: {game_url}")
            
            # Add referer header for the detail page
            headers = self.session.headers.copy()
            headers['Referer'] = self.base_url + '/games/list.php'
            
            response = self.session.get(game_url, headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # More robust extraction using multiple strategies
            def extract_field_value(field_name, patterns):
                """Extract field value using multiple patterns"""
                for pattern in patterns:
                    # Try different approaches for each pattern
                    for approach in [
                        lambda p: soup.find('span', string=re.compile(p, re.I)),
                        lambda p: soup.find('div', string=re.compile(p, re.I)),
                        lambda p: soup.find('td', string=re.compile(p, re.I)),
                        lambda p: soup.find('th', string=re.compile(p, re.I)),
                        lambda p: soup.find(text=re.compile(p, re.I))
                    ]:
                        try:
                            elem = approach(pattern)
                            if elem:
                                # Try different ways to get the value
                                value = None
                                
                                # Method 1: Next sibling
                                if hasattr(elem, 'find_next_sibling'):
                                    next_sib = elem.find_next_sibling(['span', 'div', 'td'])
                                    if next_sib:
                                        value = next_sib.get_text(strip=True)
                                
                                # Method 2: Parent's next sibling
                                if not value and hasattr(elem, 'parent'):
                                    parent = elem.parent
                                    if parent and hasattr(parent, 'find_next_sibling'):
                                        next_sib = parent.find_next_sibling(['span', 'div', 'td'])
                                        if next_sib:
                                            value = next_sib.get_text(strip=True)
                                
                                # Method 3: Same element text after colon
                                if not value:
                                    text = elem.get_text(strip=True) if hasattr(elem, 'get_text') else str(elem)
                                    if ':' in text:
                                        value = text.split(':', 1)[1].strip()
                                
                                # Method 4: Look for text in same container
                                if not value and hasattr(elem, 'parent'):
                                    parent_text = elem.parent.get_text(strip=True)
                                    if ':' in parent_text:
                                        parts = parent_text.split(':', 1)
                                        if len(parts) > 1:
                                            value = parts[1].strip()
                                
                                if value and value != field_name.lower():
                                    return value
                        except:
                            continue
                return None
            
            # Extract Released date and convert to ISO format
            released_text = extract_field_value('Released', [
                r'Released:',
                r'Release Date:',
                r'Year:',
                r'Date:'
            ])
            
            if released_text:
                # Extract year from the text (e.g., "1987(38 years ago)" -> "1987")
                year_match = re.search(r'\b(19|20)\d{2}\b', released_text)
                if year_match:
                    year = year_match.group()
                    # Convert to ISO format: YYYY-01-01
                    detailed_info['releasedate'] = f"{year}-01-01"
            
            # Extract Publisher
            publisher_text = extract_field_value('Publisher', [
                r'Publisher:',
                r'Published by:',
                r'Company:',
                r'Developer:'
            ])
            
            if publisher_text:
                # Clean up publisher text - remove logo references and extra info
                # Remove patterns like "Info / 2 logos", "Info", etc.
                publisher_clean = re.sub(r'\s*Info.*$', '', publisher_text)
                publisher_clean = re.sub(r'\s*/\s*\d+\s*logos?.*$', '', publisher_clean)
                publisher_clean = publisher_clean.strip()
                detailed_info['publisher'] = publisher_clean if publisher_clean else None
            
            # Extract Developer info (Coder, Design, Graphics, Musician)
            developer_parts = []
            for role in ['Coder', 'Design', 'Graphics', 'Musician']:
                role_value = extract_field_value(role, [f'{role}:', f'{role.lower()}:'])
                if role_value:
                    developer_parts.append(f"{role}: {role_value}")
            
            if developer_parts:
                detailed_info['developer'] = ', '.join(developer_parts)
            
            # Extract Players
            detailed_info['players'] = extract_field_value('Players', [
                r'Players:',
                r'Number of Players:',
                r'Max Players:',
                r'Player Count:'
            ])
            
            # Extract Language
            detailed_info['language'] = extract_field_value('Language', [
                r'Language:',
                r'Languages:',
                r'Localization:'
            ])
            
            # Extract Retail Price
            detailed_info['retail_price'] = extract_field_value('Retail Price', [
                r'Retail Price:',
                r'Price:',
                r'Cost:',
                r'RRP:'
            ])
            
            # Extract YouTube Links
            youtube_links = []
            for link in soup.find_all('a', href=re.compile(r'youtube\.com|youtu\.be')):
                href = link.get('href')
                if href and href not in youtube_links:
                    youtube_links.append(href)
            detailed_info['youtube_links'] = youtube_links
            
            # Extract Rating and Review Count using multiple strategies
            rating_value = None
            review_count = None
            
            # Method 1: Look for JSON-LD structured data (most reliable)
            json_script = soup.find('script', type='application/ld+json')
            if json_script:
                try:
                    import json
                    json_data = json.loads(json_script.string)
                    if 'mainEntity' in json_data and 'aggregateRating' in json_data['mainEntity']:
                        rating_data = json_data['mainEntity']['aggregateRating']
                        rating_value = rating_data.get('ratingValue')
                        review_count = rating_data.get('reviewCount')
                except:
                    pass
            
            # Method 2: Look for rating in vote score area
            if not rating_value:
                vote_elem = soup.find('span', class_='votes-score')
                if vote_elem:
                    rating_text = vote_elem.get_text(strip=True)
                    rating_match = re.search(r'(\d+\.?\d*)', rating_text)
                    if rating_match:
                        rating_value = rating_match.group(1)
            
            # Method 3: Look for rating in any text containing decimal numbers
            if not rating_value:
                rating_elem = soup.find(string=re.compile(r'\d+\.\d+'))
                if rating_elem:
                    rating_match = re.search(r'(\d+\.?\d*)', rating_elem)
                    if rating_match:
                        rating_value = rating_match.group(1)
            
            # Method 4: Look for review count in vote area
            if not review_count:
                vote_area = soup.find('div', class_='vote-ajax-area')
                if vote_area:
                    vote_text = vote_area.get_text(strip=True)
                    review_match = re.search(r'(\d+)', vote_text)
                    if review_match:
                        review_count = review_match.group(1)
            
            # Method 5: Look for review count in any text containing "votes"
            if not review_count:
                vote_elem = soup.find(string=re.compile(r'\d+\s*votes?', re.I))
                if vote_elem:
                    review_match = re.search(r'(\d+)', vote_elem)
                    if review_match:
                        review_count = review_match.group(1)
            
            detailed_info['rating'] = rating_value
            detailed_info['nbreview'] = review_count
            
            # Extract Screenshots (ordered)
            screenshots = []
            for img in soup.find_all('img', src=re.compile(r'/assets/images/games/screens/.*\.png')):
                src = img.get('src')
                if src:
                    full_url = urljoin(self.base_url, src)
                    if full_url not in screenshots:
                        screenshots.append(full_url)
            detailed_info['screenshots'] = screenshots
            
            # Extract Covers (ordered)
            covers = []
            for img in soup.find_all('img', src=re.compile(r'/assets/images/games/covers/.*\.jpg')):
                src = img.get('src')
                if src:
                    full_url = urljoin(self.base_url, src)
                    if full_url not in covers:
                        covers.append(full_url)
            detailed_info['covers'] = covers
            
            # Debug output
            extracted_fields = []
            if detailed_info['releasedate']: extracted_fields.append(f"Release Date: {detailed_info['releasedate']}")
            if detailed_info['publisher']: extracted_fields.append(f"Publisher: {detailed_info['publisher']}")
            if detailed_info['developer']: extracted_fields.append(f"Developer: {detailed_info['developer']}")
            if detailed_info['players']: extracted_fields.append(f"Players: {detailed_info['players']}")
            if detailed_info['language']: extracted_fields.append(f"Language: {detailed_info['language']}")
            if detailed_info['retail_price']: extracted_fields.append(f"Price: {detailed_info['retail_price']}")
            if detailed_info['rating']: extracted_fields.append(f"Rating: {detailed_info['rating']}")
            if detailed_info['nbreview']: extracted_fields.append(f"Reviews: {detailed_info['nbreview']}")
            
            print(f"✅ Extracted detailed info: {len(screenshots)} screenshots, {len(covers)} covers, {len(youtube_links)} YouTube links")
            if extracted_fields:
                print(f"📋 Fields: {', '.join(extracted_fields)}")
            else:
                print("⚠️  No detailed fields extracted - may need HTML structure analysis")
            
        except Exception as e:
            print(f"⚠️  Error extracting detailed info from {game_url}: {e}")
        
        return detailed_info
    
    def load_progress(self):
        """Load progress from file"""
        try:
            if os.path.exists(self.progress_file):
                with open(self.progress_file, 'r', encoding='utf-8') as f:
                    self.progress_data = json.load(f)
                print(f"📊 Loaded progress: {self.progress_data['total_games_collected']} games, page {self.progress_data['last_page_count']}")
                return True
        except Exception as e:
            print(f"⚠️  Error loading progress: {e}")
        return False
    
    def save_progress(self):
        """Save current progress to file"""
        try:
            with open(self.progress_file, 'w', encoding='utf-8') as f:
                json.dump(self.progress_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"⚠️  Error saving progress: {e}")
    
    def update_progress(self, page_offset: int, page_count: int, games_collected: int, status: str = "running"):
        """Update progress tracking"""
        self.progress_data.update({
            "last_page_offset": page_offset,
            "last_page_count": page_count,
            "total_games_collected": games_collected,
            "last_run_timestamp": time.time(),
            "status": status
        })
        self.save_progress()
    
    def clear_progress(self):
        """Clear progress file (start fresh)"""
        try:
            if os.path.exists(self.progress_file):
                os.remove(self.progress_file)
            self.progress_data = {
                "last_page_offset": 0,
                "last_page_count": 0,
                "total_games_collected": 0,
                "last_run_timestamp": None,
                "status": "not_started"
            }
            print("🗑️  Progress cleared - starting fresh")
        except Exception as e:
            print(f"⚠️  Error clearing progress: {e}")
    
    def run_spider(self, max_pages: Optional[int] = None, output_file: str = "lemon64db.json", detailed_info: bool = True, resume: bool = True):
        """Run the spider to collect all game data"""
        print("🕷️  Starting Lemon64 spider with realistic browser simulation...")
        print("🌐 Using randomized user agents and realistic headers")
        print("⏱️  Rate limiting: 2 pages per second (0.5s delay)")
        if detailed_info:
            print("🔍 Detailed info extraction: ENABLED (slower but more complete)")
        else:
            print("🔍 Detailed info extraction: DISABLED (faster but basic info only)")
        print(f"💾 Saving database to: {output_file}")
        
        # Load existing database and progress
        self.output_file = output_file
        self.load_database()
        
        # Handle resume functionality
        start_offset = 0
        start_page_count = 0
        
        if resume and self.load_progress():
            if self.progress_data['status'] == 'running':
                print("🔄 Resuming from previous session...")
                start_offset = self.progress_data['last_page_offset']
                start_page_count = self.progress_data['last_page_count']
                print(f"📍 Resuming from page {start_page_count} (offset {start_offset})")
            elif self.progress_data['status'] == 'completed':
                print("✅ Previous session completed successfully!")
                return
        else:
            print("🆕 Starting fresh session...")
        
        offset = start_offset
        page_count = start_page_count
        
        # Update initial progress
        self.update_progress(offset, page_count, len(self.games_db), "running")
        
        while True:
            # Check if we've reached max pages limit
            if max_pages and page_count >= max_pages:
                print(f"🛑 Reached maximum page limit ({max_pages})")
                self.update_progress(offset, page_count, len(self.games_db), "completed")
                break
            
            # Fetch the page
            soup = self.get_page(offset)
            if not soup:
                print("❌ Failed to fetch page, stopping...")
                self.update_progress(offset, page_count, len(self.games_db), "interrupted")
                break
            
            # Scrape games from this page
            page_games = self.scrape_page(soup, detailed_info)
            
            # Games are already added to database and saved individually
            print(f"📊 Total games collected so far: {len(self.games_db)}")
            
            # Update progress after each page
            self.update_progress(offset, page_count, len(self.games_db), "running")
            
            # Check if there's a next page
            if not self.has_next_page(soup):
                print("🏁 No more pages available")
                self.update_progress(offset, page_count, len(self.games_db), "completed")
                break
            
            # Get next offset
            next_offset = self.get_next_offset(soup)
            if next_offset is None:
                print("❌ Could not determine next page offset")
                self.update_progress(offset, page_count, len(self.games_db), "interrupted")
                break
            
            offset = next_offset
            page_count += 1
            
            # Random delay to simulate human behavior
            if page_count < max_pages if max_pages else True:
                # Occasionally rotate user agent (20% chance)
                if random.random() < 0.2:
                    self._rotate_user_agent()
                
                delay = self._randomize_delay()
                print(f"⏳ Waiting {delay} seconds before next page...")
        
        print(f"🎉 Spider completed! Collected {len(self.games_db)} games from {page_count} pages")
    
    def load_database(self):
        """Load existing database if it exists"""
        try:
            if os.path.exists(self.output_file):
                with open(self.output_file, 'r', encoding='utf-8') as f:
                    self.games_db = json.load(f)
                print(f"📂 Loaded existing database with {len(self.games_db)} games")
        except Exception as e:
            print(f"⚠️  Error loading database: {e}")
            self.games_db = {}
    
    def save_database(self, filename: str = "lemon64db.json", verbose: bool = True):
        """Save the collected data to a JSON file"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.games_db, f, indent=2, ensure_ascii=False)
            if verbose:
                print(f"💾 Database saved to {filename}")
        except Exception as e:
            print(f"❌ Error saving database: {e}")
    

def main():
    spider = Lemon64Spider()
    
    # Check for command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == "--resume":
            # Resume from existing database
            spider.load_database()
        elif sys.argv[1].startswith("--max-pages="):
            # Set maximum pages
            max_pages = int(sys.argv[1].split("=")[1])
            spider.run_spider(max_pages=max_pages)
        else:
            print("Usage: python lemon64_spider.py [--resume] [--max-pages=N]")
            return
    else:
        # Run normally
        spider.run_spider()
    
    # Database is already saved after each game, just print final message
    print(f"💾 Database continuously saved - Final count: {len(spider.games_db)} games")
    
    # Print some statistics
    if spider.games_db:
        print("\n📈 Database Statistics:")
        print(f"   Total games: {len(spider.games_db)}")
        
        # Count games by year
        years = {}
        for game in spider.games_db.values():
            if game.get('year'):
                years[game['year']] = years.get(game['year'], 0) + 1
        
        if years:
            print(f"   Year range: {min(years.keys())} - {max(years.keys())}")
            print(f"   Most common year: {max(years, key=years.get)} ({max(years.values())} games)")
        
        # Count games by publisher
        publishers = {}
        for game in spider.games_db.values():
            if game.get('publisher'):
                publishers[game['publisher']] = publishers.get(game['publisher'], 0) + 1
        
        if publishers:
            top_publisher = max(publishers, key=publishers.get)
            print(f"   Top publisher: {top_publisher} ({publishers[top_publisher]} games)")

if __name__ == "__main__":
    main()
