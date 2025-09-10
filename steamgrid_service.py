#!/usr/bin/env python3
"""
SteamGrid Service - Handles Steam API interactions for game matching
"""

import os
import json
import time
import httpx
import asyncio
import re
import difflib
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import logging
from game_utils import normalize_game_name

logger = logging.getLogger(__name__)

class SteamGridService:
    """Service for interacting with Steam API and managing app index cache"""
    
    def __init__(self, cache_dir: str = "var/db/steamgrid"):
        self.cache_dir = cache_dir
        self.app_index_file = os.path.join(cache_dir, "appindex.json")
        self.steam_api_url = "https://api.steampowered.com/ISteamApps/GetAppList/v0002/"
        self.cache_retention_hours = 24
        
        # Indexing cache for performance
        self._unified_index = None
        self._cached_steam_apps = None
        
        # Ensure cache directory exists
        os.makedirs(cache_dir, exist_ok=True)
    
    
    def load_app_index(self) -> Optional[List[Dict]]:
        """Load Steam app index from cache if valid"""
        if not os.path.exists(self.app_index_file):
            return None
        
        try:
            with open(self.app_index_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Check if cache is still valid
            cache_time = datetime.fromisoformat(data.get('cached_at', '1970-01-01T00:00:00'))
            if datetime.now() - cache_time > timedelta(hours=self.cache_retention_hours):
                logger.info("Steam app index cache expired, will refresh")
                return None
            
            # Return the pre-built flat list
            steam_apps = data.get('steam_apps', [])
            logger.info(f"Loaded Steam app index from cache ({len(steam_apps)} apps)")
            return steam_apps
            
        except Exception as e:
            logger.error(f"Failed to load Steam app index cache: {e}")
            return None
    
    def save_app_index(self, steam_apps: List[Dict]) -> None:
        """Save Steam app index to cache"""
        try:
            data = {
                'cached_at': datetime.now().isoformat(),
                'steam_apps': steam_apps
            }
            
            with open(self.app_index_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved Steam app index to cache ({len(steam_apps)} apps)")
            
        except Exception as e:
            logger.error(f"Failed to save Steam app index cache: {e}")
    
    async def fetch_steam_apps(self) -> List[Dict]:
        """Fetch Steam app list from API"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                logger.info("Fetching Steam app list from API...")
                response = await client.get(self.steam_api_url)
                response.raise_for_status()
                
                data = response.json()
                apps = data.get('applist', {}).get('apps', [])
                
                logger.info(f"Fetched {len(apps)} Steam apps from API")
                return apps
                
        except Exception as e:
            logger.error(f"Failed to fetch Steam app list: {e}")
            return []
    
    async def get_app_index(self) -> List[Dict]:
        """Get Steam app index, loading from cache or fetching from API"""
        # Try to load from cache first
        cached_steam_apps = self.load_app_index()
        if cached_steam_apps:
            return cached_steam_apps
        
        # Fetch from API if cache is invalid or missing
        apps = await self.fetch_steam_apps()
        if not apps:
            return []
        
        # Build the flat list
        steam_apps = self._build_index(apps)
        
        # Save to cache
        self.save_app_index(steam_apps)
        
        return steam_apps
    
    def _build_index(self, apps: List[Dict]) -> List[Dict]:
        """Build flat list of Steam apps with normalized names for efficient matching"""
        steam_apps = []
        
        for app in apps:
            appid = app.get('appid')
            name = app.get('name', '')
            
            if not appid or not name:
                continue
            
            # Normalize the name
            normalized = normalize_game_name(name)
            if not normalized:
                continue
            
            # Add to flat list
            steam_apps.append({
                'appid': appid,
                'name': name,
                'normalized': normalized
            })
        
        logger.info(f"Built Steam app index with {len(steam_apps)} apps")
        return steam_apps
    
    def find_best_match(self, game_name: str, steam_apps: List[Dict]) -> Optional[Dict]:
        """
        Find best matching Steam app for a game name
        Uses the same sophisticated matching logic as LaunchBox but adapted for Steam data
        """
        if not game_name or not steam_apps:
            return None
        
        # Create indexed lookups for O(1) exact matches instead of O(n) linear searches
        # Apply the same normalization as used in the index building
        
        normalized_search = normalize_game_name(game_name)
        
        # Fallback version removes parentheses and brackets after normalization (including nested)
        normalized_search_no_parens = re.sub(r'\s*[\(\[][^()\[\]]*(?:[\(\[][^()\[\]]*[\)\]][^()\[\]]*)*[\)\]]', '', game_name)
        normalized_search_no_parens = normalize_game_name(normalized_search_no_parens)
        
        # Build unified index on first call or when steam_apps changes (cached for subsequent calls)
        if self._unified_index is None or self._cached_steam_apps is not steam_apps:
            logger.debug(f"Building unified Steam index for {len(steam_apps)} apps...")
            self._unified_index = {}
            self._cached_steam_apps = steam_apps
            
            # Build unified index for Steam app names
            indexed_count = 0
            for i, app in enumerate(steam_apps):
                # Index normalized name
                normalized_name = app.get('normalized', '')
                if normalized_name:
                    if normalized_name not in self._unified_index:
                        self._unified_index[normalized_name] = []
                    self._unified_index[normalized_name].append(i)
                    indexed_count += 1
            
            logger.debug(f"Indexed {indexed_count} Steam app names")
        
        # Try exact match using unified index (O(1) lookup)
        # First try with normalized search (with parentheses removed)
        if normalized_search in self._unified_index:
            for app_idx in self._unified_index[normalized_search]:
                app = steam_apps[app_idx]
                logger.debug(f"Found exact Steam match for '{game_name}' → '{app['name']}' (appid: {app['appid']})")
                return app
        
        # If no match found with normalized search, try with no_parens version
        if normalized_search != normalized_search_no_parens and normalized_search_no_parens in self._unified_index:
            for app_idx in self._unified_index[normalized_search_no_parens]:
                app = steam_apps[app_idx]
                logger.debug(f"Found exact Steam match for '{game_name}' → '{app['name']}' (appid: {app['appid']}, no parens)")
                return app
        
        # Fall back to similarity matching if no exact match found
        # Clean the game name for better matching (same logic as gamelist.xml)
        # Always remove text between parentheses and brackets
        cleaned_name = re.sub(r'\s*[\(\[][^()\[\]]*(?:[\(\[][^()\[\]]*[\)\]][^()\[\]]*)*[\)\]]', '', game_name)
        cleaned_name = cleaned_name.lower().strip()
        
        best_match = None
        best_score = 0.0
        best_matched_name = ""
        
        # Check all Steam apps for similarity matching
        for app in steam_apps:
            steam_name = app.get('name', '')
            if not steam_name:
                continue
            
            # Calculate similarity score
            similarity = difflib.SequenceMatcher(None, cleaned_name, steam_name.lower()).ratio()
            
            # Use the best similarity score
            if similarity > best_score:
                best_score = similarity
                best_match = app
                best_matched_name = steam_name
                
                # Early termination for very good matches (score > 0.99)
                if similarity > 0.99:
                    break
        
        if best_match:
            logger.debug(f"Found Steam similarity match for '{game_name}': {best_matched_name} (appid: {best_match['appid']}, score: {best_score:.2f})")
        
        return best_match
    
    
    async def find_steam_app(self, game_name: str) -> Optional[Dict]:
        """Find Steam app for a game name"""
        steam_apps = await self.get_app_index()
        return self.find_best_match(game_name, steam_apps)
