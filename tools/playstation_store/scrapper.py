#!/usr/bin/env python3
"""
PlayStation Store Scraper
Builds a JSON database of games from the PlayStation Store.

The store browse pages are rendered client-side, so the game listing is pulled
from the same GraphQL endpoint the website itself calls. Individual game pages
are still server-rendered, so details are parsed from their HTML.
"""

import requests
from bs4 import BeautifulSoup
import json
import time
import re
from urllib.parse import urlparse
import sys
import random
import os
import argparse
from typing import Dict, List, Optional
from datetime import datetime

# GraphQL endpoint used by store.playstation.com (see appProps.service.gqlBrowser.host)
GRAPHQL_URL = "https://web.np.playstation.com/api/graphql/v1/op"

# The endpoint only accepts registered "persisted query" operations: the query
# text itself is rejected, and requests must reference an operation by the
# sha256 hash of the document the web client sends. These are lifted from the
# store's own network traffic and must be refreshed if the site changes them.
PERSISTED_QUERIES = {
    "categoryGridRetrieve": "88c0b9a1273c6d320c51cd73e390924e21ae28bf09f01cde8b84b1034b16cd03",
    "getExperience": "b5078800ed1bdebee9800979f9306abeadc5169030263f7095fe573b12e52270",
}

# Identifies the web storefront when resolving the "Browse" experience.
EMS_CLIENT_ID = "b6de8d4d-bf9b-11ee-ad2a-aea73dc1ea43"

# "All Games" grid. Resolved dynamically at runtime; this is the fallback.
DEFAULT_CATEGORY_ID = "28c9c2b2-cecc-415c-9a08-482a605cb104"

# The backend refuses offset + size beyond this, so the catalogue is only
# reachable 10k concepts deep no matter what totalCount reports.
MAX_CATALOGUE_DEPTH = 10000

# Concepts per GraphQL call. The API accepts up to 500.
PAGE_SIZE = 100


class PlayStationStoreScraper:
    def __init__(self, locale: str = "en-ca", page_size: int = PAGE_SIZE,
                 save_every: int = 25, delay: float = 1.0):
        self.base_url = "https://store.playstation.com"
        self.locale = locale
        self.page_size = max(1, min(page_size, 500))
        self.save_every = max(1, save_every)
        self.delay = delay
        self.games_db = {}
        self.session = requests.Session()
        self.category_id = DEFAULT_CATEGORY_ID
        self._dirty = 0

        # Keep data files next to this script so the scraper works from any cwd.
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.progress_file = os.path.join(script_dir, "scraper_progress.json")
        self.db_file = os.path.join(script_dir, "playstation_store_db.json")

        self.progress_data = {
            "offset": 0,
            "total_count": 0,
            "processed_games": set(),
            "total_games_collected": 0,
            "last_run_timestamp": None,
            "status": "not_started",  # not_started, running, completed, interrupted
        }

        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64; rv:132.0) Gecko/20100101 Firefox/132.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:132.0) Gecko/20100101 Firefox/132.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Safari/605.1.15',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0',
        ]
        self.current_user_agent_index = 0
        self._setup_browser_headers()

    # ------------------------------------------------------------------
    # HTTP plumbing
    # ------------------------------------------------------------------

    def _setup_browser_headers(self):
        """Set up realistic browser headers"""
        self.session.headers.update({
            'User-Agent': self.user_agents[self.current_user_agent_index],
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
        })

    def _rotate_user_agent(self):
        """Rotate to the next user agent"""
        self.current_user_agent_index = (self.current_user_agent_index + 1) % len(self.user_agents)
        user_agent = self.user_agents[self.current_user_agent_index]
        self.session.headers.update({'User-Agent': user_agent})
        return user_agent

    def graphql(self, operation: str, variables: Dict, retries: int = 4) -> Optional[Dict]:
        """Call a persisted GraphQL operation and return its `data` payload."""
        sha256_hash = PERSISTED_QUERIES.get(operation)
        if not sha256_hash:
            print(f"❌ Unknown GraphQL operation: {operation}")
            return None

        params = {
            'operationName': operation,
            'variables': json.dumps(variables, separators=(',', ':')),
            'extensions': json.dumps(
                {"persistedQuery": {"version": 1, "sha256Hash": sha256_hash}},
                separators=(',', ':')),
        }
        headers = {
            # Without an explicit content-type the gateway rejects the call as CSRF.
            'content-type': 'application/json',
            'Accept': 'application/json',
            'Origin': self.base_url,
            'Referer': f"{self.base_url}/{self.locale}/pages/browse",
            'x-psn-store-locale-override': self.locale,
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-site',
        }

        for attempt in range(retries):
            try:
                self._rotate_user_agent()
                response = self.session.get(GRAPHQL_URL, params=params,
                                            headers=headers, timeout=30)

                if response.status_code in (429, 500, 502, 503, 504):
                    wait = min(60, (2 ** attempt) * 3) + random.uniform(0, 2)
                    print(f"⚠️  {operation} HTTP {response.status_code}, retrying in {wait:.1f}s")
                    time.sleep(wait)
                    continue

                payload = response.json()

                if payload.get('errors'):
                    message = payload['errors'][0].get('message', 'unknown error')
                    code = payload['errors'][0].get('extensions', {}).get('code')
                    if code in ('PERSISTED_QUERY_NOT_FOUND', 'PERSISTED_QUERY_ID_REQUIRED'):
                        print(f"❌ The stored query hash for '{operation}' is no longer accepted "
                              f"by the store. It needs to be re-captured from store.playstation.com.")
                        return None
                    print(f"⚠️  {operation} returned an error: {message}")
                    return None

                return payload.get('data')

            except (requests.exceptions.RequestException, ValueError) as e:
                wait = min(60, (2 ** attempt) * 3) + random.uniform(0, 2)
                print(f"❌ {operation} request failed ({e}), retrying in {wait:.1f}s")
                time.sleep(wait)

        print(f"❌ {operation} failed after {retries} attempts")
        return None

    # ------------------------------------------------------------------
    # Progress / database persistence
    # ------------------------------------------------------------------

    def load_progress(self) -> bool:
        """Load progress from file"""
        if not os.path.exists(self.progress_file):
            return False
        try:
            with open(self.progress_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Older progress files tracked browse pages instead of an offset.
            if 'offset' not in data and 'current_page' in data:
                data['offset'] = max(0, (int(data.get('current_page', 1)) - 1) * 24)
                print(f"ℹ️  Migrated legacy page {data.get('current_page')} to offset {data['offset']}")
            data.pop('current_page', None)
            data.pop('max_page', None)

            self.progress_data.update(data)
            if isinstance(self.progress_data.get('processed_games'), list):
                self.progress_data['processed_games'] = set(self.progress_data['processed_games'])

            print(f"✅ Loaded progress: {len(self.progress_data['processed_games'])} games already processed "
                  f"(resuming at offset {self.progress_data.get('offset', 0)})")
            return True
        except Exception as e:
            print(f"⚠️  Error loading progress: {e}")
            return False

    def _atomic_write(self, path: str, payload) -> bool:
        """Write JSON via a temp file so an interrupted run can't truncate the target."""
        tmp_path = f"{path}.tmp"
        try:
            with open(tmp_path, 'w', encoding='utf-8') as f:
                json.dump(payload, f, indent=2, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, path)
            return True
        except Exception as e:
            print(f"⚠️  Error writing {os.path.basename(path)}: {e}")
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass
            return False

    def save_progress(self):
        """Save progress to file"""
        progress_to_save = dict(self.progress_data)
        progress_to_save['processed_games'] = sorted(self.progress_data['processed_games'])
        progress_to_save['last_run_timestamp'] = time.time()
        self._atomic_write(self.progress_file, progress_to_save)

    def load_database(self) -> bool:
        """Load existing database. Returns False if an existing file is unreadable."""
        if not os.path.exists(self.db_file):
            self.games_db = {}
            return True
        try:
            with open(self.db_file, 'r', encoding='utf-8') as f:
                self.games_db = json.load(f)
            print(f"✅ Loaded database: {len(self.games_db)} games")
            return True
        except Exception as e:
            # Refuse to continue rather than overwrite a corrupt-but-present database.
            print(f"❌ Existing database at {self.db_file} could not be read: {e}")
            print("   Move or repair the file before running again so it isn't overwritten.")
            self.games_db = {}
            return False

    def save_database(self):
        """Save database to file"""
        if self._atomic_write(self.db_file, self.games_db):
            self._dirty = 0

    def _maybe_save(self):
        """Flush to disk every `save_every` games instead of on every single one."""
        self._dirty += 1
        if self._dirty >= self.save_every:
            self.save_database()
            self.save_progress()

    # ------------------------------------------------------------------
    # Normalisation helpers
    # ------------------------------------------------------------------

    def clean_image_url(self, url: str) -> Optional[str]:
        """Remove query parameters from image URLs"""
        if not url:
            return None
        try:
            parsed = urlparse(url)
            return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        except Exception as e:
            print(f"⚠️  Error cleaning image URL '{url}': {e}")
            return url

    def normalize_date(self, date_string: str) -> Optional[str]:
        """Convert '9/6/2024' to '06-09-2024' (dd-mm-yyyy)"""
        if not date_string:
            return None
        for fmt in ("%m/%d/%Y", "%d/%m/%Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(date_string.strip(), fmt).strftime("%d-%m-%Y")
            except ValueError:
                continue
        print(f"⚠️  Could not parse date '{date_string}'")
        return None

    def normalize_rating(self, rating) -> Optional[float]:
        """Convert 0-5 rating to 0-1 scale (divide by 5). Returns None if negative."""
        if rating is None:
            return None
        try:
            rating_float = float(rating)
            if rating_float < 0:
                return None
            return round(rating_float / 5.0, 2)
        except Exception as e:
            print(f"⚠️  Error normalizing rating '{rating}': {e}")
            return None

    # ------------------------------------------------------------------
    # Catalogue listing (GraphQL)
    # ------------------------------------------------------------------

    def discover_category_id(self) -> str:
        """Resolve the 'All Games' grid id from the Browse experience."""
        data = self.graphql("getExperience", {"clientId": EMS_CLIENT_ID, "alias": "browse"})
        if not data:
            print(f"⚠️  Could not resolve the browse category, using default {DEFAULT_CATEGORY_ID}")
            return DEFAULT_CATEGORY_ID

        # Walk the view tree for the first GRID component and take its category.
        stack = [data]
        while stack:
            node = stack.pop()
            if isinstance(node, dict):
                if node.get('componentType') == 'GRID' and node.get('categoryId'):
                    print(f"✅ Resolved browse category: {node['categoryId']} ({node.get('name', 'unnamed')})")
                    return node['categoryId']
                stack.extend(node.values())
            elif isinstance(node, list):
                stack.extend(node)

        print(f"⚠️  No grid component found, using default category {DEFAULT_CATEGORY_ID}")
        return DEFAULT_CATEGORY_ID

    def fetch_catalogue_page(self, offset: int) -> Optional[Dict]:
        """Fetch one page of the catalogue. Returns {'concepts': [...], 'total': int}."""
        size = min(self.page_size, MAX_CATALOGUE_DEPTH - offset)
        if size <= 0:
            return {'concepts': [], 'total': self.progress_data.get('total_count', 0)}

        data = self.graphql("categoryGridRetrieve", {
            "id": self.category_id,
            "pageArgs": {"size": size, "offset": offset},
            "sortBy": None,
            "filterBy": [],
            "facetOptions": [],
            "maxResults": None,
        })
        if not data:
            return None

        grid = data.get('categoryGridRetrieve') or {}
        page_info = grid.get('pageInfo') or {}
        concepts = grid.get('concepts') or []

        games = []
        for concept in concepts:
            concept_id = concept.get('id')
            name = concept.get('name')
            if not concept_id or not name:
                continue
            games.append({
                'id': str(concept_id),
                'name': name,
                'url': f"{self.base_url}/{self.locale}/concept/{concept_id}",
                'boxfront': self._pick_media(concept.get('media'), 'MASTER'),
            })

        return {'concepts': games, 'total': page_info.get('totalCount', 0)}

    def _pick_media(self, media: Optional[List[Dict]], role: str) -> Optional[str]:
        """Pick an image URL for the given media role."""
        for item in media or []:
            if item.get('role') == role and item.get('type') == 'IMAGE' and item.get('url'):
                return self.clean_image_url(item['url'])
        return None

    # ------------------------------------------------------------------
    # Game detail pages (HTML)
    # ------------------------------------------------------------------

    def get_game_details(self, game_id: str, retries: int = 3) -> Optional[BeautifulSoup]:
        """Fetch and parse game detail page HTML"""
        game_url = f"{self.base_url}/{self.locale}/concept/{game_id}"

        for attempt in range(retries):
            try:
                self._rotate_user_agent()
                response = self.session.get(game_url, timeout=30)

                if response.status_code == 404:
                    print(f"⚠️  Game {game_id} not found (404)")
                    return None

                if response.status_code in (429, 500, 502, 503, 504):
                    wait = min(60, (2 ** attempt) * 3) + random.uniform(0, 2)
                    print(f"⚠️  HTTP {response.status_code} for {game_id}, retrying in {wait:.1f}s")
                    time.sleep(wait)
                    continue

                response.raise_for_status()
                return BeautifulSoup(response.content, 'html.parser')

            except requests.exceptions.RequestException as e:
                wait = min(60, (2 ** attempt) * 3) + random.uniform(0, 2)
                print(f"❌ Error fetching game {game_id} ({e}), retrying in {wait:.1f}s")
                time.sleep(wait)

        return None

    def extract_fanart(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract fanart from the hero background image"""
        try:
            # The store ships a no-JS <img> with the full-size URL, plus a tiny
            # blurred placeholder; both point at the same asset once the query
            # string is stripped.
            for data_qa in ('gameBackgroundImage#heroImage#image-no-js',
                            'gameBackgroundImage#heroImage#image',
                            'gameBackgroundImage#heroImage#preview'):
                img_elem = soup.find('img', attrs={'data-qa': data_qa})
                if img_elem and img_elem.get('src'):
                    return self.clean_image_url(img_elem['src'])

            # Fall back to any hero/background image, then to the OpenGraph tag.
            img_elem = soup.find('img', attrs={'data-qa': re.compile(r'gameBackgroundImage.*heroImage', re.I)})
            if img_elem:
                src = img_elem.get('src') or ''
                if not src and img_elem.get('srcset'):
                    src = img_elem['srcset'].split(',')[0].strip().split()[0]
                if src:
                    return self.clean_image_url(src)

            og_image = soup.find('meta', attrs={'property': 'og:image'})
            if og_image and og_image.get('content'):
                return self.clean_image_url(og_image['content'])

            return None
        except Exception as e:
            print(f"⚠️  Error extracting fanart: {e}")
            return None

    def extract_rating(self, soup: BeautifulSoup) -> Optional[float]:
        """Extract and normalize rating (3.73/5 -> 0.75)"""
        try:
            for span in soup.find_all('span', class_='psw-sr-only'):
                match = re.search(r'Average rating\s+([\d.]+)\s+stars out of 5',
                                  span.get_text(strip=True), re.I)
                if match:
                    return self.normalize_rating(float(match.group(1)))
            return None
        except Exception as e:
            print(f"⚠️  Error extracting rating: {e}")
            return None

    def extract_publisher(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract publisher from multiple possible locations"""
        try:
            for tag, data_qa in (('div', 'mfe-game-title#publisher'),
                                 ('dd', 'gameInfo#releaseInformation#publisher-value')):
                elem = soup.find(tag, attrs={'data-qa': data_qa})
                if elem:
                    publisher = elem.get_text(strip=True)
                    if publisher:
                        return publisher
            return None
        except Exception as e:
            print(f"⚠️  Error extracting publisher: {e}")
            return None

    def extract_nbplayers(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract number of players (e.g., '1-2')"""
        try:
            # The player-count notice isn't always in the same slot, so scan them all.
            elems = soup.find_all('span', attrs={
                'data-qa': re.compile(r'mfe-compatibility-notices#notices#notice\d+#compatText')})
            for elem in elems:
                text = elem.get_text(strip=True)
                match = re.search(r'(\d+)\s*-\s*(\d+)\s*players', text, re.I)
                if match:
                    return f"{match.group(1)}-{match.group(2)}"
                match = re.search(r'(\d+)\s*players?\b', text, re.I)
                if match:
                    return match.group(1)
            return None
        except Exception as e:
            print(f"⚠️  Error extracting nbplayers: {e}")
            return None

    def extract_release_date(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract and normalize release date"""
        try:
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
            desc_elem = soup.find('p', attrs={'data-qa': 'mfe-game-overview#description'})
            if not desc_elem:
                return None
            for br in desc_elem.find_all('br'):
                br.replace_with('\n')
            description = desc_elem.get_text(separator='\n', strip=True)
            description = re.sub(r'\n{3,}', '\n\n', description).strip()
            return description or None
        except Exception as e:
            print(f"⚠️  Error extracting description: {e}")
            return None

    def scrape_game(self, game_data: Dict) -> Optional[Dict]:
        """Scrape a single game's details"""
        game_id = game_data.get('id')
        if not game_id:
            return None

        soup = self.get_game_details(game_id)
        if not soup:
            return None

        return {
            'url': game_data.get('url', f"{self.base_url}/{self.locale}/concept/{game_id}"),
            'name': game_data.get('name', ''),
            'boxfront': game_data.get('boxfront'),
            'fanart': self.extract_fanart(soup),
            'rating': self.extract_rating(soup),
            'publisher': self.extract_publisher(soup),
            'nbplayers': self.extract_nbplayers(soup),
            'release_date': self.extract_release_date(soup),
            'description': self.extract_description(soup),
        }

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def run_scraper(self, resume: bool = True):
        """Main scraping loop"""
        try:
            if resume:
                self.load_progress()
            if not self.load_database():
                return 1

            self.category_id = self.discover_category_id()

            offset = self.progress_data.get('offset', 0) if resume else 0
            self.progress_data['status'] = 'running'
            new_games = 0

            while offset < MAX_CATALOGUE_DEPTH:
                print(f"\n{'='*60}")
                print(f"📌 Catalogue offset {offset} (+{self.page_size})")
                print(f"{'='*60}")

                page = self.fetch_catalogue_page(offset)
                if page is None:
                    print("❌ Could not fetch the catalogue page; stopping so progress isn't lost.")
                    self.progress_data['status'] = 'interrupted'
                    break

                concepts = page['concepts']
                total = page['total'] or 0
                if total:
                    self.progress_data['total_count'] = total

                if not concepts:
                    print("✅ Reached the end of the catalogue")
                    self.progress_data['status'] = 'completed'
                    offset = MAX_CATALOGUE_DEPTH
                    break

                reachable = min(total, MAX_CATALOGUE_DEPTH) if total else MAX_CATALOGUE_DEPTH
                print(f"✅ {len(concepts)} games in this page ({offset}/{reachable} of catalogue)")

                for game_card in concepts:
                    game_id = game_card['id']

                    if game_id in self.games_db:
                        self.progress_data['processed_games'].add(game_id)
                        continue

                    game_info = self.scrape_game(game_card)
                    if game_info:
                        self.games_db[game_id] = game_info
                        self.progress_data['processed_games'].add(game_id)
                        self.progress_data['total_games_collected'] = len(self.games_db)
                        new_games += 1
                        print(f"✅ [{len(self.games_db)}] {game_info.get('name', 'Unknown')} ({game_id})")
                        self._maybe_save()
                    else:
                        print(f"❌ Failed to scrape game {game_id}")

                    time.sleep(self.delay + random.uniform(0, 0.5))

                offset += self.page_size
                self.progress_data['offset'] = offset
                self.save_database()
                self.save_progress()

                if total and offset >= min(total, MAX_CATALOGUE_DEPTH):
                    print("\n✅ Reached the end of the catalogue")
                    self.progress_data['status'] = 'completed'
                    break

                time.sleep(1)

            self.progress_data['offset'] = min(offset, MAX_CATALOGUE_DEPTH)
            if self.progress_data['status'] == 'running':
                self.progress_data['status'] = 'completed'

            print(f"\n🎉 Done. {new_games} new games this run, {len(self.games_db)} in the database.")
            if self.progress_data.get('total_count', 0) > MAX_CATALOGUE_DEPTH:
                print(f"ℹ️  The store reports {self.progress_data['total_count']} games but only serves "
                      f"the first {MAX_CATALOGUE_DEPTH}; the rest are reachable only via filters.")
            return 0

        except KeyboardInterrupt:
            print("\n⚠️  Scraping interrupted by user")
            self.progress_data['status'] = 'interrupted'
            print(f"💾 Progress saved. Resume with: python {os.path.basename(sys.argv[0])}")
            return 130
        except Exception as e:
            print(f"\n❌ Error during scraping: {e}")
            import traceback
            traceback.print_exc()
            self.progress_data['status'] = 'interrupted'
            return 1
        finally:
            self.save_database()
            self.save_progress()


def main():
    parser = argparse.ArgumentParser(description="Scrape the PlayStation Store into a JSON database.")
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--resume', action='store_true', default=True,
                       help="Resume from saved progress (default)")
    group.add_argument('--fresh', action='store_true',
                       help="Restart the catalogue walk from the beginning "
                            "(keeps the existing database and skips games already in it)")
    group.add_argument('--status', action='store_true', help="Show progress and exit")
    parser.add_argument('--locale', default='en-ca', help="Store locale (default: en-ca)")
    parser.add_argument('--page-size', type=int, default=PAGE_SIZE,
                        help=f"Games fetched per catalogue call, max 500 (default: {PAGE_SIZE})")
    parser.add_argument('--save-every', type=int, default=25,
                        help="Write the database after this many new games (default: 25)")
    parser.add_argument('--delay', type=float, default=1.0,
                        help="Base delay in seconds between game pages (default: 1.0)")
    args = parser.parse_args()

    scraper = PlayStationStoreScraper(locale=args.locale, page_size=args.page_size,
                                      save_every=args.save_every, delay=args.delay)

    if args.status:
        scraper.load_progress()
        scraper.load_database()
        print("\n📊 Scraper Status:")
        print(f"   Status: {scraper.progress_data['status']}")
        print(f"   Catalogue offset: {scraper.progress_data.get('offset', 0)}")
        print(f"   Catalogue size: {scraper.progress_data.get('total_count') or 'unknown'}")
        print(f"   Games processed: {len(scraper.progress_data.get('processed_games', []))}")
        print(f"   Total games in DB: {len(scraper.games_db)}")
        if scraper.progress_data.get('last_run_timestamp'):
            print(f"   Last run: {datetime.fromtimestamp(scraper.progress_data['last_run_timestamp'])}")
        return 0

    if args.fresh:
        print("🆕 Restarting the catalogue walk from offset 0")

    return scraper.run_scraper(resume=not args.fresh)


if __name__ == "__main__":
    sys.exit(main())
