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
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from PIL import Image
import io


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
        # Create httpx client with HTTP/2 and connection pooling
        user_agent = self._get_random_user_agent()
        self.client = httpx.AsyncClient(
            http2=True,
            limits=httpx.Limits(max_connections=1, max_keepalive_connections=1),
            timeout=30.0,
            headers={
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
            },
            follow_redirects=True
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.client:
            await self.client.aclose()
    
    async def load_platform_mapping(self) -> Dict[str, str]:
        """Load platform mapping from MobyGames platform page or fallback to static file"""
        if self.platform_mapping:
            return self.platform_mapping
            
        # Try to load from static file first
        static_mapping_path = 'var/db/mobygames/platform_mapping.json'
        if os.path.exists(static_mapping_path):
            try:
                with open(static_mapping_path, 'r', encoding='utf-8') as f:
                    self.platform_mapping = json.load(f)
                print(f"✅ Loaded {len(self.platform_mapping)} platform mappings from static file")
                return self.platform_mapping
            except Exception as e:
                print(f"❌ Error loading static platform mapping: {e}")
        
        # Fallback to web scraping
        try:
            print("🌐 Loading MobyGames platform mapping from website...")
            # Add random delay to be respectful to the website
            await asyncio.sleep(random.uniform(1.0, 3.0))
            response = await self.client.get(f"{self.base_url}/platform/")
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            self.platform_mapping = {}
            
            # Find all platform links
            platform_links = soup.find_all('a', href=re.compile(r'^/platform/[^/]+/$'))
            
            for link in platform_links:
                href = link.get('href', '')
                platform_name = link.get_text(strip=True)
                
                # Extract short platform name from href (e.g., /platform/cpc/ -> cpc)
                match = re.search(r'/platform/([^/]+)/$', href)
                if match:
                    short_name = match.group(1)
                    # Convert platform name to MobyGames format (replace spaces with underscores)
                    formatted_name = platform_name.replace(' ', '_')
                    self.platform_mapping[formatted_name] = short_name
                    print(f"  📋 {formatted_name} -> {short_name}")
            
            print(f"✅ Loaded {len(self.platform_mapping)} platform mappings from website")
            return self.platform_mapping
            
        except Exception as e:
            print(f"❌ Error loading platform mapping from website: {e}")
            # Return empty dict if both static and web loading fail
            return {}
    
    def get_platform_short_name(self, system_name: str) -> Optional[str]:
        """Get short platform name for a system"""
        return self.platform_mapping.get(system_name)
    
    async def get_game_covers(self, game_url: str, platform_short: str) -> List[Dict[str, str]]:
        """Get cover images for a game on a specific platform"""
        if not game_url or not platform_short:
            return []
        
        try:
            # Construct cover page URL
            cover_url = f"{game_url}/cover/{platform_short}"
            print(f"🔍 Fetching covers from: {cover_url}")
            
            # Add random delay to be respectful to the website
            await asyncio.sleep(random.uniform(1.0, 3.0))
            response = await self.client.get(cover_url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            covers = []
            
            # Find all cover links
            cover_links = soup.find_all('a', href=re.compile(r'/game/\d+/[^/]+/cover/group-\d+/cover-\d+/'))
            
            for link in cover_links:
                cover_page_url = urljoin(self.base_url, link.get('href', ''))
                cover_type = link.get_text(strip=True)
                
                # Get the actual cover image from the cover page
                cover_data = await self.get_cover_image(cover_page_url, cover_type)
                if cover_data:
                    covers.append(cover_data)
            
            print(f"✅ Found {len(covers)} covers for platform {platform_short}")
            return covers
            
        except Exception as e:
            print(f"❌ Error fetching covers for {game_url}: {e}")
            return []
    
    async def get_cover_image(self, cover_page_url: str, cover_type: str) -> Optional[Dict[str, str]]:
        """Get cover image data from a cover page"""
        try:
            # Add random delay to be respectful to the website
            await asyncio.sleep(random.uniform(0.5, 1.5))
            response = await self.client.get(cover_page_url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find the cover image
            img_tag = soup.find('figure').find('img') if soup.find('figure') else None
            if not img_tag:
                return None
            
            img_url = img_tag.get('src')
            if not img_url:
                return None
            
            # Make URL absolute
            if img_url.startswith('//'):
                img_url = f"https:{img_url}"
            elif img_url.startswith('/'):
                img_url = urljoin(self.base_url, img_url)
            
            return {
                'url': img_url,
                'type': cover_type,
                'alt': img_tag.get('alt', '')
            }
            
        except Exception as e:
            print(f"❌ Error fetching cover image from {cover_page_url}: {e}")
            return None
    
    async def download_image(self, img_url: str, target_path: str, target_extension: str = 'jpg') -> bool:
        """Download and convert image to target format"""
        try:
            print(f"📥 Downloading image: {img_url}")
            # Add random delay to be respectful to the website
            await asyncio.sleep(random.uniform(0.5, 1.5))
            response = await self.client.get(img_url)
            response.raise_for_status()
            
            # Open image with PIL
            img = Image.open(io.BytesIO(response.content))
            
            # Convert to RGB if necessary (for JPEG output)
            if target_extension.lower() in ['jpg', 'jpeg'] and img.mode in ['RGBA', 'LA', 'P']:
                # Create white background for transparent images
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = background
            elif target_extension.lower() == 'png' and img.mode != 'RGBA':
                img = img.convert('RGBA')
            
            # Save with target extension
            img.save(target_path, format=target_extension.upper())
            print(f"✅ Saved image: {target_path}")
            return True
            
        except Exception as e:
            print(f"❌ Error downloading image {img_url}: {e}")
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
