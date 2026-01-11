#!/usr/bin/env python3
"""
Myrient Directory Scraper
Scrapes directory listings from https://myrient.erista.me/files/Redump/ and No-Intro/
Creates JSON database files indexed by filename
"""

import requests
from bs4 import BeautifulSoup
import json
import time
import re
from urllib.parse import urljoin, quote, unquote
import sys
import random
import os
from typing import Dict, List, Optional, Tuple, Set
from collections import defaultdict

class MyrientScraper:
    def __init__(self):
        self.base_url = "https://myrient.erista.me"
        self.redump_base = f"{self.base_url}/files/Redump/"
        self.nointro_base = f"{self.base_url}/files/No-Intro/"
        
        self.session = requests.Session()
        
        # Progress tracking
        self.progress_file = "scraper_progress.json"
        self.progress_data = {
            "processed_directories": set(),
            "processed_urls": set(),
            "current_source": None,
            "last_run_timestamp": None,
            "status": "not_started"  # not_started, running, completed, interrupted
        }
        
        # Store grouped directory data: {normalized_name: {filename: file_data}}
        self.directory_data = defaultdict(dict)
        
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
    
    def normalize_directory_name(self, directory_name: str) -> str:
        """
        Normalize directory name by removing (Aftermarket) and (Private) suffixes.
        Examples:
        - 'Nintendo - Gameboy' -> 'Nintendo - Gameboy'
        - 'Nintendo - Gameboy (Aftermarket)' -> 'Nintendo - Gameboy'
        - 'Nintendo - Gameboy (Private)' -> 'Nintendo - Gameboy'
        - 'Nintendo - NES (Headered) (Aftermarket)' -> 'Nintendo - NES (Headered)'
        """
        if not directory_name:
            return directory_name
        
        # Remove (Aftermarket) and (Private) suffixes (with optional parentheses handling)
        normalized = directory_name.strip()
        
        # Pattern to match (Aftermarket) or (Private) at the end
        patterns = [
            r'\s*\(Aftermarket\)\s*$',
            r'\s*\(Private\)\s*$',
            r'\s*\(aftermarket\)\s*$',
            r'\s*\(private\)\s*$',
        ]
        
        for pattern in patterns:
            normalized = re.sub(pattern, '', normalized, flags=re.IGNORECASE)
        
        return normalized.strip()
    
    def sanitize_filename(self, filename: str) -> str:
        """
        Sanitize directory name for use in JSON filename.
        Replace special characters that might cause filesystem issues.
        """
        # Replace problematic characters
        sanitized = filename.replace('/', '_')
        sanitized = sanitized.replace('\\', '_')
        sanitized = sanitized.replace(':', '_')
        sanitized = sanitized.replace('*', '_')
        sanitized = sanitized.replace('?', '_')
        sanitized = sanitized.replace('"', '_')
        sanitized = sanitized.replace('<', '_')
        sanitized = sanitized.replace('>', '_')
        sanitized = sanitized.replace('|', '_')
        # Replace multiple underscores with single
        sanitized = re.sub(r'_+', '_', sanitized)
        return sanitized
    
    def load_progress(self) -> bool:
        """Load progress from file"""
        if os.path.exists(self.progress_file):
            try:
                with open(self.progress_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.progress_data.update(data)
                    # Convert processed lists back to sets
                    if isinstance(self.progress_data.get('processed_directories'), list):
                        self.progress_data['processed_directories'] = set(self.progress_data['processed_directories'])
                    if isinstance(self.progress_data.get('processed_urls'), list):
                        self.progress_data['processed_urls'] = set(self.progress_data['processed_urls'])
                    print(f"✅ Loaded progress: {len(self.progress_data['processed_directories'])} directories, {len(self.progress_data['processed_urls'])} URLs already processed")
                    return True
            except Exception as e:
                print(f"⚠️  Error loading progress: {e}")
                return False
        return False
    
    def save_progress(self):
        """Save progress to file"""
        try:
            progress_to_save = self.progress_data.copy()
            progress_to_save['processed_directories'] = list(self.progress_data['processed_directories'])
            progress_to_save['processed_urls'] = list(self.progress_data['processed_urls'])
            progress_to_save['last_run_timestamp'] = time.time()
            
            with open(self.progress_file, 'w', encoding='utf-8') as f:
                json.dump(progress_to_save, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"⚠️  Error saving progress: {e}")
    
    def get_page(self, url: str, rotate_ua: bool = True) -> Optional[BeautifulSoup]:
        """Fetch a page and return BeautifulSoup object"""
        try:
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
            if rotate_ua:
                self._rotate_user_agent()
            return None
    
    def parse_directory_listing(self, soup: BeautifulSoup, base_url: str) -> Tuple[List[Dict[str, str]], List[Dict[str, str]]]:
        """
        Parse directory listing HTML and extract directories and files.
        Returns: (directories, files)
        Each directory/file is a dict with: name, url, date, size (for files)
        """
        directories = []
        files = []
        
        # Myrient uses an Apache-style directory listing
        # Look for table rows (tr) in the directory listing
        # Skip header row and parent directory link
        
        # Find the main table
        table = soup.find('table')
        if not table:
            # Try alternative structure - sometimes directories are in pre or other elements
            print("⚠️  No table found, trying alternative parsing...")
            return directories, files
        
        rows = table.find_all('tr')
        
        for row in rows[1:]:  # Skip header row
            cells = row.find_all(['td', 'th'])
            if len(cells) < 3:
                continue
            
            # Find links in the row
            link = row.find('a')
            if not link:
                continue
            
            href = link.get('href', '')
            name = link.get_text(strip=True)
            
            # Skip parent directory - check both name and href
            if name in ['Parent directory/', '../', '..', '.'] or href in ['../', '..', '.', './']:
                continue
            
            # Skip any href that contains parent directory references
            if '../' in href or href.startswith('./') and href != './':
                continue
            
            # Skip self-referential links (current directory)
            if href == '.' or href == './':
                continue
            
            # Remove trailing slash from directory names
            if name.endswith('/'):
                name = name[:-1]
            
            # Clean up name if it's a parent/current directory indicator
            if name in ['..', '.', '../', './']:
                continue
            
            # Parse date and size
            date_str = ''
            size_str = ''
            
            if len(cells) >= 2:
                # Date is typically in the second or third cell
                for i, cell in enumerate(cells[1:], start=1):
                    text = cell.get_text(strip=True)
                    # Date format is usually like "18-Feb-2025 11:50"
                    if re.match(r'\d{2}-\w{3}-\d{4}', text):
                        date_str = text
                    # Size might be a number or "-" for directories
                    elif text and text != '-' and (text.isdigit() or re.match(r'[\d,]+', text.replace(',', ''))):
                        size_str = text.replace(',', '')
            
            # Construct full URL
            if href.startswith('http'):
                full_url = href
            else:
                # Skip parent directory references entirely
                if '../' in href or href in ['../', '..']:
                    continue
                
                # Skip current directory references
                if href == '.' or href == './' or href.startswith('./') and href != './':
                    continue
                
                # Normalize the URL - remove leading ./ if present
                href_clean = href.strip()
                href_clean = href_clean.lstrip('./')
                href_clean = href_clean.rstrip('/')
                
                # Ensure base_url ends with / and href doesn't start with /
                base = base_url.rstrip('/')
                
                # Skip if href is empty or just .
                if not href_clean or href_clean == '.' or href_clean == './':
                    continue
                
                # Skip if href still contains ./
                if './' in href_clean or href_clean.startswith('.'):
                    continue
                
                # Build full URL
                if href_clean.startswith('/'):
                    # Absolute path from base domain
                    full_url = f"{self.base_url}{href_clean}"
                else:
                    # Relative path - ensure we don't create ./ patterns
                    if not base.endswith('/'):
                        base = base + '/'
                    full_url = f"{base}{href_clean}"
                
                # Ensure trailing slash for directories (check if it's likely a directory)
                if href.endswith('/') or name.endswith('/'):
                    full_url = full_url.rstrip('/') + '/'
                else:
                    # For files, don't add trailing slash
                    full_url = full_url.rstrip('/')
            
            # Normalize the full_url before adding
            if '../' in full_url or '/./' in full_url:
                # Skip URLs with parent directory references
                continue
            
            if name.endswith('/') or href.endswith('/'):
                # It's a directory
                # Normalize the URL to prevent loops
                normalized_url = self.normalize_url(full_url)
                if '../' in normalized_url:
                    print(f"⚠️  Skipping directory with parent reference: {full_url}")
                    continue
                
                directories.append({
                    'name': name.rstrip('/'),
                    'url': normalized_url
                })
            else:
                # It's a file
                files.append({
                    'name': name,
                    'url': full_url,
                    'date': date_str,
                    'size': size_str
                })
        
        return directories, files
    
    def normalize_url(self, url: str) -> str:
        """Normalize URL by removing parent directory references and duplicate slashes"""
        original_url = url
        
        # Skip if URL contains parent directory references - don't try to resolve them
        if '../' in url:
            return url  # Return as-is, will be filtered out by caller
        
        # Remove /./ patterns
        url = url.replace('/./', '/')
        url = url.replace('./', '')
        
        # Remove duplicate slashes (except after http:)
        url = re.sub(r'([^:])//+', r'\1/', url)
        
        # Ensure URL ends with / for directories (not files)
        if url.endswith('/'):
            pass  # Already has trailing slash
        elif url.split('/')[-1].split('.')[-1].lower() not in ['zip', '7z', 'rar', 'iso', 'bin', 'cue', 'gdi', 'chd', 'wbfs', 'rvz', 'wux', 'nkit']:
            # Likely a directory, add trailing slash
            url = url + '/'
        
        return url
    
    def scrape_directory(self, url: str, source_type: str, is_root: bool = False) -> None:
        """
        Scrape a directory and its files. Only go one level deep from root.
        source_type: 'redump' or 'nointro'
        is_root: True if this is the root directory (we want to process its subdirectories)
        """
        # Normalize URL first
        url_original = url
        url = self.normalize_url(url)
        
        # Skip if URL contains parent directory references
        if '../' in url:
            print(f"⚠️  Skipping parent directory reference: {url_original}")
            return
        
        # Skip if normalized URL looks suspicious (too many ./ patterns)
        if url.count('./') > 3:
            print(f"⚠️  Skipping suspicious URL pattern: {url_original}")
            return
        
        # Check if already processed
        if url in self.progress_data['processed_urls']:
            print(f"⏭️  Skipping already processed: {url}")
            return
        
        print(f"\n{'='*60}")
        print(f"📁 Processing: {url}")
        print(f"{'='*60}")
        
        soup = self.get_page(url)
        if not soup:
            print(f"⚠️  Failed to fetch directory: {url}")
            return
        
        directories, files = self.parse_directory_listing(soup, url)
        
        # Extract current directory name from URL
        current_dir_name = url.rstrip('/').split('/')[-1]
        if not current_dir_name:
            current_dir_name = source_type.capitalize()
        
        # Decode URL-encoded directory name
        try:
            current_dir_name = unquote(current_dir_name)
        except:
            pass
        
        # Normalize directory name for grouping
        normalized_dir_name = self.normalize_directory_name(current_dir_name)
        
        print(f"📂 Directory: {current_dir_name} (normalized: {normalized_dir_name})")
        print(f"   Found {len(files)} files, {len(directories)} subdirectories")
        
        if is_root:
            # If this is the root, process each subdirectory (one level deep only)
            print(f"\n🔍 Processing {len(directories)} top-level directories...")
            for directory in directories:
                dir_url = directory['url']
                dir_name = directory['name']
                
                # Process this subdirectory (not as root, so we only get its files)
                print(f"\n📂 Entering subdirectory: {dir_name}")
                time.sleep(0.5)  # Rate limiting
                self.scrape_directory(dir_url, source_type, is_root=False)
        else:
            # This is a subdirectory - only process files in this directory
            # Add files to the grouped directory data
            for file_info in files:
                filename = file_info['name']
                # Use filename as key
                self.directory_data[normalized_dir_name][filename] = {
                    'filename': filename,
                    'date': file_info.get('date', ''),
                    'size': file_info.get('size', ''),
                    'url': file_info['url']
                }
            
            print(f"✅ Added {len(files)} files to group '{normalized_dir_name}'")
        
        # Mark this directory as processed
        self.progress_data['processed_urls'].add(url)
        if not is_root:
            self.progress_data['processed_directories'].add(current_dir_name)
        
        # Save progress after each directory
        self.save_progress()
    
    def save_directory_json(self, directory_name: str, files_dict: Dict, source_type: str):
        """
        Save directory data to JSON file.
        directory_name: normalized directory name
        files_dict: dictionary of files (filename -> file_data)
        source_type: 'redump' or 'nointro'
        """
        if not files_dict:
            print(f"⚠️  No files to save for {directory_name}")
            return
        
        # Sanitize directory name for filename
        sanitized_name = self.sanitize_filename(directory_name)
        
        # Create JSON filename with prefix
        json_filename = f"{source_type}_{sanitized_name}.json"
        
        # Load existing JSON if it exists (to merge with other variants)
        existing_data = {}
        if os.path.exists(json_filename):
            try:
                with open(json_filename, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
                print(f"📂 Merging with existing data in {json_filename} ({len(existing_data)} files)")
            except Exception as e:
                print(f"⚠️  Error loading existing JSON: {e}")
                existing_data = {}
        
        # Merge files (newer files overwrite older ones with same filename)
        existing_data.update(files_dict)
        
        # Save JSON file
        try:
            with open(json_filename, 'w', encoding='utf-8') as f:
                json.dump(existing_data, f, indent=2, ensure_ascii=False)
            print(f"💾 Saved {json_filename}: {len(existing_data)} files")
        except Exception as e:
            print(f"❌ Error saving JSON {json_filename}: {e}")
    
    def process_source(self, base_url: str, source_type: str):
        """Process a source (Redump or No-Intro)"""
        print(f"\n{'='*80}")
        print(f"🚀 Starting {source_type.upper()} scraping from {base_url}")
        print(f"{'='*80}\n")
        
        self.progress_data['current_source'] = source_type
        self.save_progress()
        
        # Start scraping from root directory (is_root=True to process subdirectories)
        self.scrape_directory(base_url, source_type, is_root=True)
        
        # After scraping, save all grouped directory data to JSON files
        print(f"\n{'='*80}")
        print(f"💾 Saving {source_type.upper()} JSON files...")
        print(f"{'='*80}\n")
        
        for normalized_name, files_dict in self.directory_data.items():
            self.save_directory_json(normalized_name, files_dict, source_type)
        
        # Clear directory data for next source
        self.directory_data.clear()
        
        print(f"\n✅ Completed {source_type.upper()} scraping")
    
    def run_scraper(self, resume: bool = True):
        """Run the scraper"""
        print("🚀 Starting Myrient scraper...")
        
        # Load existing progress
        if resume:
            self.load_progress()
        
        self.progress_data['status'] = 'running'
        self.save_progress()
        
        try:
            # Process Redump first
            current_source = self.progress_data.get('current_source')
            if not current_source or current_source == 'redump':
                self.process_source(self.redump_base, 'redump')
                # After Redump completes, set current_source to 'nointro' to trigger No-Intro processing
                self.progress_data['current_source'] = 'nointro'
                self.save_progress()
            
            # Process No-Intro (will run if current_source is 'nointro' or None on fresh start)
            current_source = self.progress_data.get('current_source')
            if not current_source or current_source == 'nointro':
                self.process_source(self.nointro_base, 'nointro')
            
            self.progress_data['status'] = 'completed'
            print(f"\n🎉 Scraping completed!")
            
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
            self.save_progress()

def main():
    scraper = MyrientScraper()
    
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
            print("\n📊 Scraper Status:")
            print(f"   Status: {scraper.progress_data['status']}")
            print(f"   Current source: {scraper.progress_data.get('current_source', 'None')}")
            print(f"   Directories processed: {len(scraper.progress_data.get('processed_directories', []))}")
            print(f"   URLs processed: {len(scraper.progress_data.get('processed_urls', []))}")
            if scraper.progress_data.get('last_run_timestamp'):
                import datetime
                last_run = datetime.datetime.fromtimestamp(scraper.progress_data['last_run_timestamp'])
                print(f"   Last run: {last_run}")
            return
    
    scraper.run_scraper(resume=resume)

if __name__ == "__main__":
    main()

