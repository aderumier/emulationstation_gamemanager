#!/usr/bin/env python3
"""
EmuMovies Service - media scraping via the gamesdbase.com backend.

As of 2025, the EmuMovies media API moved from api3.emumovies.com (a Bearer-token
JSON API, now dead) to https://api.gamesdbase.com — the same backend used by the
official "EmuMovies Sync" Windows tool and the Jellyfin/Emby EmuMovies plugin.

This client talks to that API. It does LIVE per-game searches (no local index /
database build): every scrape or modal search hits search.aspx directly and gets
back a ready-to-download media URL.

The previous api3.emumovies.com implementation is preserved as
emumovies_service_api3.py in case that host is brought back online.

API flow (form / query encoded, TLS 1.2, User-Agent matching the Sync tool):
  1. login.aspx?user=<u>&api=<password>&product=<PRODUCT_ID>  -> Session="<id>"
  2. getsystems.aspx?sessionid=<id>   -> <System Name Maker Lookup Media MediaUpdated>
  3. getmedias.aspx?sessionid=<id>    -> <Media Name Extensions>
  4. search.aspx?search=<name>&system=<Lookup>&media=<Type>&sessionid=<id>
        -> <Results><Result Found="True" URL="..." CRC="..."/></Results>
     The returned URL is a direct, standalone download (no auth needed to fetch).
"""

import os
import re
import json
import time
import logging
import urllib.parse
from typing import Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


class EmuMoviesService:
    """Client for the gamesdbase.com media API (EmuMovies backend)."""

    # Product/client id used by the official EmuMovies Sync tool.
    PRODUCT_ID = "D42BE62CA8E3A4BDB9CEBDD328D7E726D0E6"
    # User-Agent used by the official Sync tool's download requests.
    USER_AGENT = "EmuMovies Download Service"

    def __init__(self, cache_dir: str = "var/db/emumovies", config: Dict = None, credentials: Dict = None):
        self.cache_dir = cache_dir
        self.config = config or {}
        self.credentials = credentials or {}
        # login also works on api2/api3.gamesdbase.com; api handles everything.
        self.base_url = "https://api.gamesdbase.com"

        # Session (login) cache
        self._session_id: Optional[str] = None
        self._session_created_at: float = 0.0
        self._user_type: Optional[str] = None
        # Sessions are re-established cheaply; refresh well within the server TTL.
        self._session_ttl_seconds = 30 * 60

        os.makedirs(cache_dir, exist_ok=True)
        self._load_session_cache()

    def close(self):
        """No persistent connections to close."""
        pass

    # ------------------------------------------------------------------ #
    # Credentials
    # ------------------------------------------------------------------ #
    def _get_credentials(self) -> Dict[str, str]:
        """Load EmuMovies credentials (same source as credential_manager)."""
        # Explicit credentials passed to the constructor win.
        if self.credentials.get('username') and self.credentials.get('password'):
            return {
                'username': self.credentials['username'],
                'password': self.credentials['password'],
            }
        try:
            credentials_path = 'var/config/credentials.json'
            if os.path.exists(credentials_path):
                with open(credentials_path, 'r') as f:
                    credentials = json.load(f)
                creds = credentials.get('emumovies', {})
                username = creds.get('username', '') or ''
                password = creds.get('password', '') or ''
                # Ignore masked/placeholder values from the settings UI
                if '•' in username:
                    username = ''
                if '•' in password:
                    password = ''
                return {'username': username, 'password': password}
        except Exception as e:
            logger.error(f"Error loading EmuMovies credentials: {e}")
        return {}

    def save_credentials(self, username: str, password: str) -> bool:
        """Save EmuMovies credentials to var/config/credentials.json."""
        try:
            credentials_path = 'var/config/credentials.json'
            os.makedirs(os.path.dirname(credentials_path), exist_ok=True)
            credentials = {}
            if os.path.exists(credentials_path):
                with open(credentials_path, 'r') as f:
                    credentials = json.load(f)
            credentials['emumovies'] = {'username': username, 'password': password}
            with open(credentials_path, 'w') as f:
                json.dump(credentials, f, indent=2)
            logger.info("EmuMovies credentials saved successfully")
            return True
        except Exception as e:
            logger.error(f"Error saving EmuMovies credentials: {e}")
            return False

    # ------------------------------------------------------------------ #
    # Session cache
    # ------------------------------------------------------------------ #
    def _session_cache_path(self) -> str:
        cache_dir = 'var/temp'
        os.makedirs(cache_dir, exist_ok=True)
        return os.path.join(cache_dir, 'emumovies_session_cache.json')

    def _load_session_cache(self):
        try:
            path = self._session_cache_path()
            if os.path.exists(path):
                with open(path, 'r') as f:
                    data = json.load(f)
                self._session_id = data.get('session_id')
                self._session_created_at = float(data.get('created_at', 0) or 0)
                self._user_type = data.get('user_type')
        except Exception as e:
            logger.warning(f"Error loading EmuMovies session cache: {e}")

    def _save_session_cache(self):
        try:
            with open(self._session_cache_path(), 'w') as f:
                json.dump({
                    'session_id': self._session_id,
                    'created_at': self._session_created_at,
                    'user_type': self._user_type,
                }, f)
        except Exception as e:
            logger.warning(f"Error saving EmuMovies session cache: {e}")

    def _is_session_valid(self) -> bool:
        return bool(self._session_id) and (time.time() - self._session_created_at) < self._session_ttl_seconds

    def _client(self, timeout: float = 30.0) -> httpx.AsyncClient:
        """An httpx client configured like the Sync tool (UA + TLS 1.2 default)."""
        return httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=True,
            headers={'User-Agent': self.USER_AGENT},
        )

    # ------------------------------------------------------------------ #
    # Authentication
    # ------------------------------------------------------------------ #
    async def authenticate(self, username: str = None, password: str = None) -> Optional[str]:
        """Log in and return the session id (cached). Returns None on failure."""
        if not username or not password:
            creds = self._get_credentials()
            username = username or creds.get('username', '')
            password = password or creds.get('password', '')

        if not username or not password:
            logger.error("EmuMovies credentials not provided")
            return None

        # Reuse a still-valid cached session
        if self._is_session_valid():
            return self._session_id

        url = (
            f"{self.base_url}/login.aspx"
            f"?user={urllib.parse.quote(username)}"
            f"&api={urllib.parse.quote(password)}"
            f"&product={self.PRODUCT_ID}"
        )
        try:
            async with self._client() as client:
                resp = await client.get(url)
        except Exception as e:
            logger.error(f"Error authenticating with EmuMovies (gamesdbase) API: {e}")
            return None

        if resp.status_code != 200:
            logger.error(f"EmuMovies login returned HTTP {resp.status_code}")
            return None

        m = re.search(r'Session\s*=\s*"([^"]*)"', resp.text)
        session_id = m.group(1) if m else None
        if not session_id:
            logger.error("EmuMovies login failed - no session in response (bad credentials?)")
            return None

        ut = re.search(r'UserType\s*=\s*"([^"]*)"', resp.text)
        self._session_id = session_id
        self._user_type = ut.group(1) if ut else None
        self._session_created_at = time.time()
        self._save_session_cache()
        logger.info("Authenticated with EmuMovies (gamesdbase) API")
        return session_id

    async def _ensure_session(self, force: bool = False) -> Optional[str]:
        if force:
            self._session_id = None
        if self._is_session_valid():
            return self._session_id
        return await self.authenticate()

    # ------------------------------------------------------------------ #
    # Systems & media types (for mappings / modals)
    # ------------------------------------------------------------------ #
    @staticmethod
    def _parse_attrs(fragment: str) -> Dict[str, str]:
        """Parse `Key = "value"` pairs (gamesdbase uses spaces around '=')."""
        return {k: v for k, v in re.findall(r'(\w+)\s*=\s*"([^"]*)"', fragment)}

    async def get_systems(self, max_retries: int = 2) -> List[Dict]:
        """Return the list of systems: {name, maker, lookup, media[], media_updated}."""
        for attempt in range(max_retries):
            sid = await self._ensure_session(force=attempt > 0)
            if not sid:
                return []
            try:
                async with self._client() as client:
                    resp = await client.get(f"{self.base_url}/getsystems.aspx?sessionid={sid}")
            except Exception as e:
                logger.error(f"EmuMovies get_systems error: {e}")
                continue
            if resp.status_code != 200:
                continue
            if self._looks_like_session_error(resp.text):
                self._session_id = None
                continue
            systems = []
            for frag in re.findall(r'<System\b([^>]*?)/?>', resp.text):
                attrs = self._parse_attrs(frag)
                name = attrs.get('Name')
                if not name:
                    continue
                systems.append({
                    'name': name,
                    'maker': attrs.get('Maker', ''),
                    'lookup': attrs.get('Lookup', ''),
                    'media': [m for m in attrs.get('Media', '').split(',') if m],
                    'media_updated': attrs.get('MediaUpdated', ''),
                })
            return systems
        return []

    async def get_media_types(self, system_identifier: str = None, max_retries: int = 2) -> List[Dict]:
        """Return available media types: {name, extensions[]}.

        The gamesdbase media-type list is global; `system_identifier` is accepted
        for signature compatibility but ignored.
        """
        for attempt in range(max_retries):
            sid = await self._ensure_session(force=attempt > 0)
            if not sid:
                return []
            try:
                async with self._client() as client:
                    resp = await client.get(f"{self.base_url}/getmedias.aspx?sessionid={sid}")
            except Exception as e:
                logger.error(f"EmuMovies get_media_types error: {e}")
                continue
            if resp.status_code != 200:
                continue
            if self._looks_like_session_error(resp.text):
                self._session_id = None
                continue
            media_types = []
            for frag in re.findall(r'<Media\b([^>]*?)/?>', resp.text):
                attrs = self._parse_attrs(frag)
                name = attrs.get('Name')
                if not name:
                    continue
                media_types.append({
                    'name': name,
                    'extensions': [e for e in attrs.get('Extensions', '').split(',') if e],
                })
            return media_types
        return []

    # ------------------------------------------------------------------ #
    # Live search (the core of scraping / modal lookups)
    # ------------------------------------------------------------------ #
    @staticmethod
    def _looks_like_session_error(text: str) -> bool:
        low = text.lower()
        return ('invalid session' in low) or ('session expired' in low) or ('not logged in' in low) or ('invalid sessionid' in low)

    async def search(self, game_name: str, system_lookup: str, media_type: str,
                     max_retries: int = 2) -> List[Dict]:
        """Live search for one game's media of a single type.

        Returns a list of {url, crc, media_type, system}. `url` is a direct,
        standalone download link (no auth required to fetch it). Empty list if
        the game/system/media has no match.
        """
        if not game_name or not system_lookup or not media_type:
            return []

        for attempt in range(max_retries):
            sid = await self._ensure_session(force=attempt > 0)
            if not sid:
                return []
            url = (
                f"{self.base_url}/search.aspx"
                f"?search={urllib.parse.quote(game_name)}"
                f"&system={urllib.parse.quote(system_lookup)}"
                f"&media={urllib.parse.quote(media_type)}"
                f"&sessionid={sid}"
            )
            try:
                async with self._client() as client:
                    resp = await client.get(url)
            except Exception as e:
                logger.error(f"EmuMovies search error ({game_name}/{system_lookup}/{media_type}): {e}")
                continue
            if resp.status_code != 200:
                continue
            if self._looks_like_session_error(resp.text):
                self._session_id = None
                continue

            results = []
            for frag in re.findall(r'<Result\b([^>]*?)/?>', resp.text):
                attrs = self._parse_attrs(frag)
                if attrs.get('Found', '').lower() != 'true':
                    continue
                media_url = attrs.get('URL', '').strip()
                if not media_url:
                    continue
                results.append({
                    'url': media_url,
                    'crc': attrs.get('CRC', ''),
                    'media_type': media_type,
                    'system': system_lookup,
                })
            return results
        return []

    async def search_media_types(self, game_name: str, system_lookup: str,
                                 media_types: List[str]) -> List[Dict]:
        """Live search across several media types; returns a flat result list."""
        if isinstance(media_types, str):
            media_types = [media_types]
        found = []
        seen = set()
        for mt in media_types:
            for r in await self.search(game_name, system_lookup, mt):
                if r['url'] not in seen:
                    seen.add(r['url'])
                    found.append(r)
        return found

    async def search_bulk(self, game_names: List[str], system_lookup: str, media_type: str,
                          max_retries: int = 2) -> Dict[str, Dict]:
        """Match several game names in one call via searchbulk.aspx.

        Returns {lowercased_name: {url, crc, size}} for each match. Useful when a
        modal offers several name candidates; not used for full-system indexing.
        """
        names = [n for n in (game_names or []) if n]
        if not names or not system_lookup or not media_type:
            return {}
        import random
        for attempt in range(max_retries):
            sid = await self._ensure_session(force=attempt > 0)
            if not sid:
                return {}
            url = (
                f"{self.base_url}/searchbulk.aspx"
                f"?testnorecords=1&teststruct=1&biggertimeout=1&txt=1&more2=1"
                f"&system={urllib.parse.quote(system_lookup)}"
                f"&media={urllib.parse.quote(media_type)}"
                f"&sessionid={sid}&rnd={random.randint(0, 600000)}"
            )
            body = "FileNames=" + urllib.parse.quote("\r\n".join(names))
            try:
                async with self._client(timeout=60.0) as client:
                    resp = await client.post(
                        url, content=body,
                        headers={'Content-Type': 'application/x-www-form-urlencoded'},
                    )
            except Exception as e:
                logger.error(f"EmuMovies search_bulk error: {e}")
                continue
            if resp.status_code != 200:
                continue
            if self._looks_like_session_error(resp.text):
                self._session_id = None
                continue
            out = {}
            # txt=1 mode: one line per match -> name||url||crc||size
            for line in resp.text.splitlines():
                parts = line.split('||')
                if len(parts) >= 2 and parts[1].strip():
                    out[parts[0].strip().lower()] = {
                        'url': parts[1].strip(),
                        'crc': parts[2].strip() if len(parts) > 2 else '',
                        'size': parts[3].strip() if len(parts) > 3 else '',
                    }
            return out
        return {}

    # ------------------------------------------------------------------ #
    # Indexing endpoints — intentionally disabled (live search only)
    # ------------------------------------------------------------------ #
    _INDEX_DISABLED_MSG = (
        "Local EmuMovies indexing/database build is no longer supported: the "
        "gamesdbase API has no bulk enumeration endpoint. Media is now fetched "
        "with live per-game searches during scraping."
    )

    async def build_local_database(self, progress_callback=None, target_system: str = None) -> Dict:
        logger.warning(self._INDEX_DISABLED_MSG)
        return {'success': False, 'error': self._INDEX_DISABLED_MSG, 'indexing_disabled': True}

    def get_database_index(self) -> Dict:
        return {}

    def generate_normalized_index(self) -> Dict:
        return {'success': False, 'error': self._INDEX_DISABLED_MSG, 'indexing_disabled': True}

    async def get_media_sets(self, system_identifier, media_type_id: str = None, max_retries: int = 2) -> List[str]:
        # gamesdbase has no media-set concept; kept for signature compatibility.
        return []

    async def get_media_list(self, system_identifier, media_type: str = None, media_set_id: str = None, max_retries: int = 2) -> List[str]:
        logger.warning(self._INDEX_DISABLED_MSG)
        return []

    def get_system_media(self, system_id: int, media_type_id: int = None) -> List[Dict]:
        return []
