#!/usr/bin/env python3
"""
MobyGames Web Scraper Service

This service handles web scraping from MobyGames website to retrieve cover images
and platform mappings. It uses httpx with HTTP/2 and connection pooling.
"""

import os
import re
import json
import httpx
import asyncio
import time
import random
import logging
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from PIL import Image
import io

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class MobyGamesWebService:
    """Service for web scraping MobyGames website for media and platform data"""
    
    def __init__(self):
        self.base_url = "https://www.mobygames.com"
        self.platform_mapping = {}
        self.client = None
        
    def _get_random_user_agent(self) -> str:
        """Get a random realistic user agent"""
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:132.0) Gecko/20100101 Firefox/132.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:132.0) Gecko/20100101 Firefox/132.0',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:132.0) Gecko/20100101 Firefox/132.0'
        ]
        return random.choice(user_agents)
        
    async def __aenter__(self):
        """Async context manager entry"""
        logger.debug("🔧 Initializing MobyGames web service...")
        
        # Create httpx client with HTTP/2 and connection pooling
        user_agent = self._get_random_user_agent()
        logger.debug(f"🔧 Selected user agent: {user_agent}")
        
        headers = {
            'User-Agent': user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'sec-ch-ua': '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'Cache-Control': 'max-age=0'
        }
        
        logger.debug(f"🔧 HTTP headers: {headers}")
        
        self.client = httpx.AsyncClient(
            http2=True,
            limits=httpx.Limits(max_connections=1, max_keepalive_connections=1),
            timeout=30.0,
            headers=headers,
            follow_redirects=True
        )
        
        logger.debug("✅ MobyGames web service initialized successfully")
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        logger.debug("🔧 Closing MobyGames web service...")
        if self.client:
            await self.client.aclose()
            logger.debug("✅ MobyGames web service closed")
    
    async def load_platform_mapping(self) -> Dict[str, str]:
        """Load platform mapping from MobyGames platform page or fallback to static file"""
        logger.debug("🔧 Loading platform mapping...")
        
        if self.platform_mapping:
            logger.debug(f"✅ Platform mapping already loaded: {len(self.platform_mapping)} entries")
            return self.platform_mapping
            
        # Try to load from static file first
        static_mapping_path = 'var/db/mobygames/platform_mapping.json'
        logger.debug(f"🔧 Checking for static mapping file: {static_mapping_path}")
        
        if os.path.exists(static_mapping_path):
            try:
                logger.debug("🔧 Loading platform mapping from static file...")
                with open(static_mapping_path, 'r', encoding='utf-8') as f:
                    self.platform_mapping = json.load(f)
                logger.info(f"✅ Loaded {len(self.platform_mapping)} platform mappings from static file")
                return self.platform_mapping
            except Exception as e:
                logger.error(f"❌ Error loading static platform mapping: {e}")
        else:
            logger.debug("❌ Static mapping file not found, will try web scraping")
        
        # Fallback to web scraping
        try:
            logger.info("🌐 Loading MobyGames platform mapping from website...")
            platform_url = f"{self.base_url}/platform/"
            logger.debug(f"🔧 Requesting URL: {platform_url}")
            
            # Add random delay to be respectful to the website
            delay = random.uniform(1.0, 3.0)
            logger.debug(f"🔧 Waiting {delay:.2f} seconds before request...")
            await asyncio.sleep(delay)
            
            logger.debug("🔧 Sending HTTP request...")
            response = await self.client.get(platform_url)
            logger.debug(f"🔧 Response status: {response.status_code}")
            logger.debug(f"🔧 Response headers: {dict(response.headers)}")
            
            response.raise_for_status()
            
            logger.debug("🔧 Parsing HTML response...")
            soup = BeautifulSoup(response.text, 'html.parser')
            self.platform_mapping = {}
            
            # Find all platform links
            platform_links = soup.find_all('a', href=re.compile(r'^/platform/[^/]+/$'))
            logger.debug(f"🔧 Found {len(platform_links)} platform links")
            
            for i, link in enumerate(platform_links):
                href = link.get('href', '')
                platform_name = link.get_text(strip=True)
                logger.debug(f"🔧 Link {i+1}: {platform_name} -> {href}")
                
                # Extract short platform name from href (e.g., /platform/cpc/ -> cpc)
                match = re.search(r'/platform/([^/]+)/$', href)
                if match:
                    short_name = match.group(1)
                    # Convert platform name to MobyGames format (replace spaces with underscores)
                    formatted_name = platform_name.replace(' ', '_')
                    self.platform_mapping[formatted_name] = short_name
                    logger.debug(f"  📋 {formatted_name} -> {short_name}")
                else:
                    logger.debug(f"  ❌ Could not extract short name from: {href}")
            
            logger.info(f"✅ Loaded {len(self.platform_mapping)} platform mappings from website")
            return self.platform_mapping
            
        except httpx.HTTPStatusError as e:
            logger.error(f"❌ HTTP error loading platform mapping: {e.response.status_code} - {e.response.text[:200]}")
            return {}
        except httpx.RequestError as e:
            logger.error(f"❌ Request error loading platform mapping: {e}")
            return {}
        except Exception as e:
            logger.error(f"❌ Unexpected error loading platform mapping: {e}")
            return {}
    
    def get_platform_short_name(self, system_name: str) -> Optional[str]:
        """Get short platform name for a system"""
        return self.platform_mapping.get(system_name)
    
    async def get_game_covers(self, game_url: str, platform_short: str) -> List[Dict[str, str]]:
        """Get cover images for a game on a specific platform"""
        logger.debug(f"🔧 Getting game covers for URL: {game_url}, platform: {platform_short}")
        
        if not game_url or not platform_short:
            logger.warning("❌ Missing game_url or platform_short")
            return []
        
        try:
            # Construct cover page URL
            cover_url = f"{game_url}/cover/{platform_short}"
            logger.info(f"🔍 Fetching covers from: {cover_url}")
            
            # Add random delay to be respectful to the website
            delay = random.uniform(1.0, 3.0)
            logger.debug(f"🔧 Waiting {delay:.2f} seconds before request...")
            await asyncio.sleep(delay)
            
            logger.debug("🔧 Sending HTTP request for covers...")
            response = await self.client.get(cover_url)
            logger.debug(f"🔧 Response status: {response.status_code}")
            logger.debug(f"🔧 Response headers: {dict(response.headers)}")
            
            response.raise_for_status()
            
            logger.debug("🔧 Parsing HTML response for cover links...")
            soup = BeautifulSoup(response.text, 'html.parser')
            covers = []
            
            # Find all cover links
            cover_links = soup.find_all('a', href=re.compile(r'/game/\d+/[^/]+/cover/group-\d+/cover-\d+/'))
            logger.debug(f"🔧 Found {len(cover_links)} cover links")
            
            for i, link in enumerate(cover_links):
                href = link.get('href', '')
                cover_type = link.get_text(strip=True)
                logger.debug(f"🔧 Cover link {i+1}: {cover_type} -> {href}")
                
                cover_page_url = urljoin(self.base_url, href)
                logger.debug(f"🔧 Full cover page URL: {cover_page_url}")
                
                # Get the actual cover image from the cover page
                cover_data = await self.get_cover_image(cover_page_url, cover_type)
                if cover_data:
                    covers.append(cover_data)
                    logger.debug(f"✅ Added cover: {cover_type}")
                else:
                    logger.debug(f"❌ Failed to get cover data for: {cover_type}")
            
            logger.info(f"✅ Found {len(covers)} covers for platform {platform_short}")
            return covers
            
        except httpx.HTTPStatusError as e:
            logger.error(f"❌ HTTP error fetching covers for {game_url}: {e.response.status_code} - {e.response.text[:200]}")
            return []
        except httpx.RequestError as e:
            logger.error(f"❌ Request error fetching covers for {game_url}: {e}")
            return []
        except Exception as e:
            logger.error(f"❌ Unexpected error fetching covers for {game_url}: {e}")
            return []
    
    async def get_cover_image(self, cover_page_url: str, cover_type: str) -> Optional[Dict[str, str]]:
        """Get cover image data from a cover page"""
        logger.debug(f"🔧 Getting cover image from: {cover_page_url}")
        
        try:
            # Add random delay to be respectful to the website
            delay = random.uniform(0.5, 1.5)
            logger.debug(f"🔧 Waiting {delay:.2f} seconds before cover image request...")
            await asyncio.sleep(delay)
            
            logger.debug("🔧 Sending HTTP request for cover image...")
            response = await self.client.get(cover_page_url)
            logger.debug(f"🔧 Response status: {response.status_code}")
            logger.debug(f"🔧 Response headers: {dict(response.headers)}")
            
            response.raise_for_status()
            
            logger.debug("🔧 Parsing HTML response for cover image...")
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find the cover image
            figure_tag = soup.find('figure')
            if not figure_tag:
                logger.debug("❌ No figure tag found in cover page")
                return None
            
            img_tag = figure_tag.find('img')
            if not img_tag:
                logger.debug("❌ No img tag found in figure")
                return None
            
            img_url = img_tag.get('src')
            if not img_url:
                logger.debug("❌ No src attribute found in img tag")
                return None
            
            logger.debug(f"🔧 Found image URL: {img_url}")
            
            # Make URL absolute
            if img_url.startswith('//'):
                img_url = f"https:{img_url}"
            elif img_url.startswith('/'):
                img_url = urljoin(self.base_url, img_url)
            
            logger.debug(f"🔧 Absolute image URL: {img_url}")
            
            cover_data = {
                'url': img_url,
                'type': cover_type,
                'alt': img_tag.get('alt', '')
            }
            
            logger.debug(f"✅ Cover data: {cover_data}")
            return cover_data
            
        except httpx.HTTPStatusError as e:
            logger.error(f"❌ HTTP error fetching cover image from {cover_page_url}: {e.response.status_code} - {e.response.text[:200]}")
            return None
        except httpx.RequestError as e:
            logger.error(f"❌ Request error fetching cover image from {cover_page_url}: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Unexpected error fetching cover image from {cover_page_url}: {e}")
            return None
    
    async def download_image(self, img_url: str, target_path: str, target_extension: str = 'jpg') -> bool:
        """Download and convert image to target format"""
        logger.debug(f"🔧 Downloading image: {img_url} -> {target_path}")
        
        try:
            logger.info(f"📥 Downloading image: {img_url}")
            
            # Add random delay to be respectful to the website
            delay = random.uniform(0.5, 1.5)
            logger.debug(f"🔧 Waiting {delay:.2f} seconds before image download...")
            await asyncio.sleep(delay)
            
            logger.debug("🔧 Sending HTTP request for image...")
            response = await self.client.get(img_url)
            logger.debug(f"🔧 Response status: {response.status_code}")
            logger.debug(f"🔧 Response headers: {dict(response.headers)}")
            logger.debug(f"🔧 Image size: {len(response.content)} bytes")
            
            response.raise_for_status()
            
            logger.debug("🔧 Processing image with PIL...")
            # Open image with PIL
            img = Image.open(io.BytesIO(response.content))
            logger.debug(f"🔧 Original image mode: {img.mode}, size: {img.size}")
            
            # Convert to RGB if necessary (for JPEG output)
            if target_extension.lower() in ['jpg', 'jpeg'] and img.mode in ['RGBA', 'LA', 'P']:
                logger.debug("🔧 Converting image to RGB for JPEG output...")
                # Create white background for transparent images
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = background
            elif target_extension.lower() == 'png' and img.mode != 'RGBA':
                logger.debug("🔧 Converting image to RGBA for PNG output...")
                img = img.convert('RGBA')
            
            logger.debug(f"🔧 Final image mode: {img.mode}, size: {img.size}")
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            logger.debug(f"🔧 Created directory: {os.path.dirname(target_path)}")
            
            # Save with target extension
            logger.debug(f"🔧 Saving image as {target_extension.upper()}...")
            if target_extension.upper() == 'JPG':
                img.save(target_path, format='JPEG')
            else:
                img.save(target_path, format=target_extension.upper())
            
            # Verify file was created
            if os.path.exists(target_path):
                file_size = os.path.getsize(target_path)
                logger.info(f"✅ Saved image: {target_path} ({file_size} bytes)")
                return True
            else:
                logger.error(f"❌ File was not created: {target_path}")
                return False
            
        except httpx.HTTPStatusError as e:
            logger.error(f"❌ HTTP error downloading image {img_url}: {e.response.status_code} - {e.response.text[:200]}")
            return False
        except httpx.RequestError as e:
            logger.error(f"❌ Request error downloading image {img_url}: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected error downloading image {img_url}: {e}")
            return False


# Synchronous wrapper for use in Flask app
class MobyGamesWebServiceSync:
    """Synchronous wrapper for MobyGamesWebService"""
    
    def __init__(self):
        self.service = MobyGamesWebService()
    
    def load_platform_mapping(self) -> Dict[str, str]:
        """Load platform mapping synchronously"""
        return asyncio.run(self.service.load_platform_mapping())
    
    def get_platform_short_name(self, system_name: str) -> Optional[str]:
        """Get short platform name for a system"""
        return self.service.get_platform_short_name(system_name)
    
    def get_game_covers(self, game_url: str, platform_short: str) -> List[Dict[str, str]]:
        """Get cover images for a game synchronously"""
        return asyncio.run(self.service.get_game_covers(game_url, platform_short))
    
    def download_image(self, img_url: str, target_path: str, target_extension: str = 'jpg') -> bool:
        """Download image synchronously"""
        return asyncio.run(self.service.download_image(img_url, target_path, target_extension))
