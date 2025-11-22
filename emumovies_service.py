#!/usr/bin/env python3
"""
EmuMovies Service - Handles EmuMovies API interactions for media scraping
API Documentation: https://api3.emumovies.com/index.html
"""

import os
import json
import pickle
import time
import httpx
import asyncio
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

class EmuMoviesService:
    """Service for interacting with EmuMovies API for media downloads"""
    
    def __init__(self, cache_dir: str = "var/db/emumovies", config: Dict = None, credentials: Dict = None):
        self.cache_dir = cache_dir
        self.config = config or {}
        self.credentials = credentials or {}
        self.base_url = "https://api3.emumovies.com"
        
        # Bearer token cache
        self._bearer_token = None
        self._token_expires_at = None
        
        # Ensure cache directory exists
        os.makedirs(cache_dir, exist_ok=True)
        
        # Load token cache if exists
        self._load_token_cache()
    
    def close(self):
        """Close any open connections or resources"""
        # No persistent connections to close
        pass
    
    def _get_credentials(self) -> Dict[str, str]:
        """Get EmuMovies credentials from credentials file"""
        try:
            credentials_path = 'var/config/credentials.json'
            if os.path.exists(credentials_path):
                with open(credentials_path, 'r') as f:
                    credentials = json.load(f)
                    if 'emumovies' in credentials:
                        creds = credentials['emumovies']
                        username = creds.get('username', '')
                        password = creds.get('password', '')
                        # Sanitize placeholder characters or masked values
                        if username and '•' in username:
                            username = ''
                        if password and '•' in password:
                            password = ''
                        return {
                            'username': username,
                            'password': password
                        }
            return {}
        except Exception as e:
            logger.error(f"Error loading EmuMovies credentials: {e}")
            return {}
    
    def save_credentials(self, username: str, password: str) -> bool:
        """Save EmuMovies credentials to credentials file"""
        try:
            credentials_path = 'var/config/credentials.json'
            os.makedirs(os.path.dirname(credentials_path), exist_ok=True)
            
            credentials = {}
            if os.path.exists(credentials_path):
                with open(credentials_path, 'r') as f:
                    credentials = json.load(f)
            
            credentials['emumovies'] = {
                'username': username,
                'password': password
            }
            
            with open(credentials_path, 'w') as f:
                json.dump(credentials, f, indent=2)
            
            logger.info("EmuMovies credentials saved successfully")
            return True
        except Exception as e:
            logger.error(f"Error saving EmuMovies credentials: {e}")
            return False
    
    def _load_token_cache(self):
        """Load bearer token from cache file"""
        cache_dir = 'var/temp'
        os.makedirs(cache_dir, exist_ok=True)
        token_cache_path = os.path.join(cache_dir, 'emumovies_token_cache')
        if os.path.exists(token_cache_path):
            try:
                with open(token_cache_path, 'r') as f:
                    cache_data = json.load(f)
                    self._bearer_token = cache_data.get('bearer_token')
                    expires_at_str = cache_data.get('expires_at')
                    if expires_at_str:
                        self._token_expires_at = datetime.fromisoformat(expires_at_str)
            except Exception as e:
                logger.warning(f"Error loading token cache: {e}")
    
    def _save_token_cache(self, bearer_token: str, expires_in: int = 3600):
        """Save bearer token to cache file"""
        cache_dir = 'var/temp'
        os.makedirs(cache_dir, exist_ok=True)
        token_cache_path = os.path.join(cache_dir, 'emumovies_token_cache')
        try:
            expires_at = datetime.now() + timedelta(seconds=expires_in - 60)  # Subtract 60s for safety margin
            cache_data = {
                'bearer_token': bearer_token,
                'expires_at': expires_at.isoformat()
            }
            with open(token_cache_path, 'w') as f:
                json.dump(cache_data, f, indent=2)
            self._bearer_token = bearer_token
            self._token_expires_at = expires_at
            logger.info(f"Bearer token cached until {expires_at}")
        except Exception as e:
            logger.error(f"Error saving token cache: {e}")
    
    def _is_token_valid(self) -> bool:
        """Check if cached bearer token is still valid"""
        if not self._bearer_token or not self._token_expires_at:
            return False
        return datetime.now() < self._token_expires_at
    
    async def authenticate(self, username: str = None, password: str = None) -> Optional[str]:
        """Authenticate with EmuMovies API and get bearer token"""
        # Use provided credentials or load from file
        if not username or not password:
            creds = self._get_credentials()
            username = username or creds.get('username', '')
            password = password or creds.get('password', '')
        
        if not username or not password:
            logger.error("EmuMovies credentials not provided")
            return None
        
        # Check if we have a valid cached token
        if self._is_token_valid():
            logger.debug("Using cached bearer token")
            return self._bearer_token
        
        try:
            url = f"{self.base_url}/api/User/authenticate"
            payload = {
                'username': username,
                'userName': username,  # Some APIs expect camel case
                'password': password,
                'rememberMe': True
            }
            
            try:
                safe_payload = {'username': username, 'rememberMe': True}
                logger.debug(f"EmuMovies auth request payload: {json.dumps(safe_payload, indent=2)}")
            except Exception:
                logger.debug("EmuMovies auth request payload: <failed to serialize>")
            
            limits = httpx.Limits(max_connections=10, max_keepalive_connections=5)
            async with httpx.AsyncClient(
                limits=limits,
                http2=True,
                timeout=30.0
            ) as client:
                logger.debug(f"Authenticating with EmuMovies API: {url}")
                
                # Try JSON payload first
                response = await client.post(url, json=payload, headers={'Content-Type': 'application/json'})
                
                # If token missing, try form-encoded payload (some APIs expect form data)
                result = {}
                if response.status_code == 200:
                    result = response.json()
                    bearer_token = result.get('token') or result.get('bearerToken') or result.get('accessToken')
                    if not bearer_token:
                        # Some responses nest token inside data or misspell keys (e.g., acessToken)
                        data_block = result.get('data', {})
                        bearer_token = (
                            data_block.get('accessToken') or
                            data_block.get('acessToken') or
                            data_block.get('token') or
                            data_block.get('bearerToken')
                        )
                    expires_in = (
                        result.get('expiresIn') or
                        (result.get('data') or {}).get('expiresIn') or
                        3600
                    )
                    
                    if not bearer_token:
                        logger.warning("Authentication response missing token using JSON payload, retrying with form data...")
                        form_headers = {'Content-Type': 'application/x-www-form-urlencoded'}
                        response = await client.post(url, data=payload, headers=form_headers)
                        if response.status_code == 200:
                            result = response.json()
                            bearer_token = result.get('token') or result.get('bearerToken') or result.get('accessToken')
                            expires_in = result.get('expiresIn', 3600)
                else:
                    logger.warning(f"EmuMovies auth returned HTTP {response.status_code} - retrying with form data")
                    form_headers = {'Content-Type': 'application/x-www-form-urlencoded'}
                    response = await client.post(url, data=payload, headers=form_headers)
                    if response.status_code == 200:
                        result = response.json()
                        bearer_token = result.get('token') or result.get('bearerToken') or result.get('accessToken')
                        expires_in = result.get('expiresIn', 3600)
                    else:
                        bearer_token = None
                
                if response.status_code == 200 and result:
                    bearer_token = (
                        result.get('token') or
                        result.get('bearerToken') or
                        result.get('accessToken')
                    )
                    expires_in = (
                        result.get('expiresIn') or
                        (result.get('data') or {}).get('expiresIn') or
                        3600
                    )
                    
                    if not bearer_token:
                        data_block = result.get('data', {})
                        bearer_token = (
                            data_block.get('accessToken') or
                            data_block.get('acessToken') or
                            data_block.get('token') or
                            data_block.get('bearerToken')
                        )
                        expires_in = data_block.get('expiresIn', expires_in)
                    
                    if bearer_token:
                        self._save_token_cache(bearer_token, expires_in)
                        logger.info("Successfully authenticated with EmuMovies API")
                        return bearer_token
                    else:
                        logger.error("Authentication response missing token after retries")
                        logger.debug(f"Authentication response payload: {result}")
                        return None
                elif response.status_code == 401:
                    logger.error("EmuMovies API authentication failed - invalid credentials")
                    return None
                else:
                    logger.error(f"EmuMovies API authentication error: HTTP {response.status_code}")
                    try:
                        error_text = response.text
                        logger.error(f"Error response: {error_text}")
                    except:
                        pass
                    return None
        except Exception as e:
            logger.error(f"Error authenticating with EmuMovies API: {e}")
            return None
    
    async def _get_authenticated_headers(self) -> Dict[str, str]:
        """Get headers with bearer token, authenticating if necessary"""
        if not self._is_token_valid():
            await self.authenticate()
        
        if not self._bearer_token:
            return {}
        
        return {
            'Authorization': f'Bearer {self._bearer_token}',
            'Content-Type': 'application/json'
        }
    
    async def get_systems(self, max_retries: int = 3) -> List[Dict]:
        """Get list of all systems from EmuMovies API with retry logic"""
        headers = await self._get_authenticated_headers()
        if not headers:
            logger.error("Cannot get systems: not authenticated")
            return []
        
        url = f"{self.base_url}/api/Systems"
        
        for attempt in range(max_retries):
            try:
                limits = httpx.Limits(max_connections=10, max_keepalive_connections=5)
                async with httpx.AsyncClient(
                    limits=limits,
                    http2=True,
                    timeout=30.0,
                    headers=headers
                ) as client:
                    logger.debug(f"Fetching systems from EmuMovies API: {url} (attempt {attempt + 1}/{max_retries})")
                    
                    response = await client.get(url)
                    
                    if response.status_code == 200:
                        systems_response = response.json()
                        if isinstance(systems_response, dict) and 'data' in systems_response:
                            systems = systems_response['data']
                        else:
                            systems = systems_response
                        
                        systems_list = systems if isinstance(systems, list) else []
                        logger.info(f"Retrieved {len(systems_list)} systems from EmuMovies")
                        return systems_list
                    elif response.status_code == 401:
                        logger.warning("EmuMovies API authentication expired, re-authenticating...")
                        await self.authenticate()
                        headers = await self._get_authenticated_headers()
                        if headers:
                            continue  # Retry immediately after re-authentication
                        return []
                    elif response.status_code == 429:
                        wait_time = (2 ** attempt) + (attempt * 0.5)
                        logger.warning(f"Rate limited (429), waiting {wait_time:.1f}s before retry (attempt {attempt + 1}/{max_retries})...")
                        await asyncio.sleep(wait_time)
                        continue
                    elif response.status_code >= 500:
                        if attempt < max_retries - 1:
                            wait_time = (2 ** attempt) + (attempt * 0.5)
                            logger.warning(f"Server error {response.status_code}, waiting {wait_time:.1f}s before retry (attempt {attempt + 1}/{max_retries})...")
                            await asyncio.sleep(wait_time)
                            continue
                        else:
                            logger.error(f"Error fetching systems: HTTP {response.status_code} (max retries reached)")
                            return []
                    else:
                        logger.error(f"Error fetching systems: HTTP {response.status_code}")
                        return []
                        
            except (httpx.TimeoutException, httpx.ConnectError, httpx.NetworkError) as e:
                if attempt < max_retries - 1:
                    wait_time = (2 ** attempt) + (attempt * 0.5)
                    error_type = type(e).__name__
                    logger.warning(f"Network error ({error_type}): {e}, waiting {wait_time:.1f}s before retry (attempt {attempt + 1}/{max_retries})...")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    logger.error(f"Network error after {max_retries} attempts: {e}")
                    return []
            except Exception as e:
                logger.error(f"Unexpected error fetching systems: {e}")
                if attempt < max_retries - 1:
                    wait_time = (2 ** attempt) + (attempt * 0.5)
                    logger.warning(f"Waiting {wait_time:.1f}s before retry (attempt {attempt + 1}/{max_retries})...")
                    await asyncio.sleep(wait_time)
                    continue
                return []
        
        return []
    
    def _build_system_query(self, system_identifier):
        """
        Build query parameters for system-based endpoints.
        EmuMovies APIs expect systemName (string). Some responses only return strings.
        """
        if isinstance(system_identifier, dict):
            system_name = (
                system_identifier.get('systemName') or
                system_identifier.get('name') or
                system_identifier.get('displayName') or
                system_identifier.get('system')
            )
        else:
            system_name = str(system_identifier)
        
        return {'systemName': system_name} if system_name else {}

    def _extract_media_type(self, media_type):
        """
        Returns (type_key, type_name_display)
        """
        if isinstance(media_type, dict):
            type_key = (
                media_type.get('name') or
                media_type.get('mediaTypeName') or
                media_type.get('shortName') or
                str(media_type.get('id') or media_type.get('mediaTypeId') or '')
            )
            type_label = (
                media_type.get('displayName') or
                media_type.get('mediaTypeDisplayName') or
                type_key
            )
        else:
            type_key = str(media_type)
            type_label = type_key
        
        type_key = type_key.strip() if type_key else None
        type_label = type_label.strip() if type_label else type_key
        return type_key, type_label

    async def get_media_types(self, system_identifier, max_retries: int = 3) -> List[str]:
        """Get media types for a specific system with retry logic"""
        headers = await self._get_authenticated_headers()
        if not headers:
            logger.error("Cannot get media types: not authenticated")
            return []
        
        url = f"{self.base_url}/api/media/mediaTypes"
        params = self._build_system_query(system_identifier)
        system_id_or_name = params.get('systemName') or params.get('systemId')
        
        for attempt in range(max_retries):
            try:
                limits = httpx.Limits(max_connections=10, max_keepalive_connections=5)
                async with httpx.AsyncClient(
                    limits=limits,
                    http2=True,
                    timeout=30.0,
                    headers=headers
                ) as client:
                    logger.debug(f"Fetching media types for system {system_id_or_name}: {url} (attempt {attempt + 1}/{max_retries})")
                    
                    response = await client.get(url, params=params)
                    
                    if response.status_code == 200:
                        result = response.json()
                        if isinstance(result, dict) and 'data' in result:
                            return result['data']
                        return result if isinstance(result, list) else []
                    elif response.status_code == 401:
                        logger.warning("EmuMovies API authentication expired, re-authenticating...")
                        await self.authenticate()
                        headers = await self._get_authenticated_headers()
                        if headers:
                            continue  # Retry immediately after re-authentication
                        return []
                    elif response.status_code == 429:
                        wait_time = (2 ** attempt) + (attempt * 0.5)
                        logger.warning(f"Rate limited (429), waiting {wait_time:.1f}s before retry (attempt {attempt + 1}/{max_retries})...")
                        await asyncio.sleep(wait_time)
                        continue
                    elif response.status_code >= 500:
                        if attempt < max_retries - 1:
                            wait_time = (2 ** attempt) + (attempt * 0.5)
                            logger.warning(f"Server error {response.status_code}, waiting {wait_time:.1f}s before retry (attempt {attempt + 1}/{max_retries})...")
                            await asyncio.sleep(wait_time)
                            continue
                        else:
                            logger.error(f"Error fetching media types: HTTP {response.status_code} (max retries reached)")
                            return []
                    else:
                        logger.error(f"Error fetching media types: HTTP {response.status_code}")
                        return []
                        
            except (httpx.TimeoutException, httpx.ConnectError, httpx.NetworkError) as e:
                if attempt < max_retries - 1:
                    wait_time = (2 ** attempt) + (attempt * 0.5)
                    error_type = type(e).__name__
                    logger.warning(f"Network error ({error_type}): {e}, waiting {wait_time:.1f}s before retry (attempt {attempt + 1}/{max_retries})...")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    logger.error(f"Network error after {max_retries} attempts: {e}")
                    return []
            except Exception as e:
                logger.error(f"Unexpected error fetching media types: {e}")
                if attempt < max_retries - 1:
                    wait_time = (2 ** attempt) + (attempt * 0.5)
                    logger.warning(f"Waiting {wait_time:.1f}s before retry (attempt {attempt + 1}/{max_retries})...")
                    await asyncio.sleep(wait_time)
                    continue
                return []
        
        return []
    
    async def get_media_sets(self, system_identifier, media_type_id: str = None, max_retries: int = 3) -> List[str]:
        """Get media sets for a specific system and media type (required by API) with retry logic"""
        headers = await self._get_authenticated_headers()
        if not headers:
            logger.error("Cannot get media sets: not authenticated")
            return []
        
        url = f"{self.base_url}/api/media/MediaSets"
        params = self._build_system_query(system_identifier)
        system_id_or_name = params.get('systemName') or params.get('systemId')
        
        if media_type_id is not None:
            params['mediaType'] = media_type_id
        else:
            # MediaSets endpoint requires a media type name per docs
            logger.debug(f"MediaSets request requires media type - skipping (system: {system_id_or_name})")
            return []
        
        for attempt in range(max_retries):
            try:
                limits = httpx.Limits(max_connections=10, max_keepalive_connections=5)
                async with httpx.AsyncClient(
                    limits=limits,
                    http2=True,
                    timeout=30.0,
                    headers=headers
                ) as client:
                    logger.debug(f"Fetching media sets for system {system_id_or_name}: {url} (attempt {attempt + 1}/{max_retries})")
                    
                    response = await client.get(url, params=params)
                    
                    if response.status_code == 200:
                        result = response.json()
                        if isinstance(result, dict) and 'data' in result:
                            return result['data']
                        return result if isinstance(result, list) else []
                    elif response.status_code == 401:
                        logger.warning("EmuMovies API authentication expired, re-authenticating...")
                        await self.authenticate()
                        headers = await self._get_authenticated_headers()
                        if headers:
                            continue  # Retry immediately after re-authentication
                        return []
                    elif response.status_code == 429:
                        wait_time = (2 ** attempt) + (attempt * 0.5)
                        logger.warning(f"Rate limited (429), waiting {wait_time:.1f}s before retry (attempt {attempt + 1}/{max_retries})...")
                        await asyncio.sleep(wait_time)
                        continue
                    elif response.status_code >= 500:
                        if attempt < max_retries - 1:
                            wait_time = (2 ** attempt) + (attempt * 0.5)
                            logger.warning(f"Server error {response.status_code}, waiting {wait_time:.1f}s before retry (attempt {attempt + 1}/{max_retries})...")
                            await asyncio.sleep(wait_time)
                            continue
                        else:
                            logger.error(f"Error fetching media sets: HTTP {response.status_code} (max retries reached)")
                            return []
                    else:
                        logger.error(f"Error fetching media sets: HTTP {response.status_code}")
                        return []
                        
            except (httpx.TimeoutException, httpx.ConnectError, httpx.NetworkError) as e:
                if attempt < max_retries - 1:
                    wait_time = (2 ** attempt) + (attempt * 0.5)
                    error_type = type(e).__name__
                    logger.warning(f"Network error ({error_type}): {e}, waiting {wait_time:.1f}s before retry (attempt {attempt + 1}/{max_retries})...")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    logger.error(f"Network error after {max_retries} attempts: {e}")
                    return []
            except Exception as e:
                logger.error(f"Unexpected error fetching media sets: {e}")
                if attempt < max_retries - 1:
                    wait_time = (2 ** attempt) + (attempt * 0.5)
                    logger.warning(f"Waiting {wait_time:.1f}s before retry (attempt {attempt + 1}/{max_retries})...")
                    await asyncio.sleep(wait_time)
                    continue
                return []
        
        return []
    
    async def get_media_list(self, system_identifier, media_type: str = None, media_set_id: str = None, max_retries: int = 3) -> List[str]:
        """Get media list for a specific system and optionally media type/set with retry logic"""
        headers = await self._get_authenticated_headers()
        if not headers:
            logger.error("Cannot get media list: not authenticated")
            return []
        
        url = f"{self.base_url}/api/Media/MediaList"
        params = self._build_system_query(system_identifier)
        system_id_or_name = params.get('systemName') or params.get('systemId')
        
        if media_type is not None:
            params['mediaType'] = media_type
        if media_set_id is not None:
            params['mediaSet'] = media_set_id
        
        for attempt in range(max_retries):
            try:
                limits = httpx.Limits(max_connections=10, max_keepalive_connections=5)
                async with httpx.AsyncClient(
                    limits=limits,
                    http2=True,
                    timeout=120.0,  # Longer timeout for full media list
                    headers=headers
                ) as client:
                    logger.debug(f"Fetching media list for system {system_id_or_name}, type {media_type}, set {media_set_id}: {url} (attempt {attempt + 1}/{max_retries})")
                    
                    response = await client.get(url, params=params)
                    
                    if response.status_code == 200:
                        result = response.json()
                        if isinstance(result, dict) and 'data' in result:
                            return result['data']
                        return result if isinstance(result, list) else []
                    elif response.status_code == 401:
                        logger.warning("EmuMovies API authentication expired, re-authenticating...")
                        await self.authenticate()
                        headers = await self._get_authenticated_headers()
                        if headers:
                            # Retry immediately after re-authentication
                            continue
                        return []
                    elif response.status_code == 429:
                        # Rate limited - wait and retry
                        wait_time = (2 ** attempt) + (attempt * 0.5)  # Exponential backoff with jitter
                        logger.warning(f"Rate limited (429), waiting {wait_time:.1f}s before retry (attempt {attempt + 1}/{max_retries})...")
                        await asyncio.sleep(wait_time)
                        continue
                    elif response.status_code >= 500:
                        # Server error - retry with backoff
                        if attempt < max_retries - 1:
                            wait_time = (2 ** attempt) + (attempt * 0.5)
                            logger.warning(f"Server error {response.status_code}, waiting {wait_time:.1f}s before retry (attempt {attempt + 1}/{max_retries})...")
                            await asyncio.sleep(wait_time)
                            continue
                        else:
                            logger.error(f"Error fetching media list: HTTP {response.status_code} (max retries reached)")
                            return []
                    else:
                        # Client error (4xx except 401, 429) - don't retry
                        logger.error(f"Error fetching media list: HTTP {response.status_code}")
                        return []
                        
            except (httpx.TimeoutException, httpx.ConnectError, httpx.NetworkError) as e:
                if attempt < max_retries - 1:
                    wait_time = (2 ** attempt) + (attempt * 0.5)
                    error_type = type(e).__name__
                    logger.warning(f"Network error ({error_type}): {e}, waiting {wait_time:.1f}s before retry (attempt {attempt + 1}/{max_retries})...")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    logger.error(f"Network error after {max_retries} attempts: {e}")
                    return []
            except Exception as e:
                logger.error(f"Unexpected error fetching media list: {e}")
                if attempt < max_retries - 1:
                    wait_time = (2 ** attempt) + (attempt * 0.5)
                    logger.warning(f"Waiting {wait_time:.1f}s before retry (attempt {attempt + 1}/{max_retries})...")
                    await asyncio.sleep(wait_time)
                    continue
                return []
        
        return []
    
    async def build_local_database(self, progress_callback=None, target_system: str = None) -> Dict:
        """
        Build local database with all media for each system.
        This will:
        1. Get all systems
        2. For each system, get media types and media sets
        3. For each system/media type combination, get all media
        4. Save to var/db/emumovies/
        """
        logger.info("Starting EmuMovies local database build...")
        
        # Authenticate first
        token = await self.authenticate()
        if not token:
            logger.error("Failed to authenticate with EmuMovies API")
            return {'success': False, 'error': 'Authentication failed'}
        
        try:
            # Get all systems
            if progress_callback:
                if asyncio.iscoroutinefunction(progress_callback):
                    await progress_callback("Fetching systems list...", 0)
                else:
                    progress_callback("Fetching systems list...", 0)
            
            systems = await self.get_systems()
            if not systems:
                logger.error("No systems retrieved from EmuMovies API")
                return {'success': False, 'error': 'No systems found'}
            
            # Consolidate structure: [systemname][mediatype][mediafile] = 1
            db_file = os.path.join(self.cache_dir, 'emumovies.json')
            consolidated_db = {}
            
            # Load existing database if available
            if os.path.exists(db_file):
                try:
                    with open(db_file, 'r', encoding='utf-8') as f:
                        consolidated_db = json.load(f)
                    logger.info(f"Loaded existing database with {len(consolidated_db)} systems")
                except Exception as e:
                    logger.warning(f"Could not load existing database: {e}")
            
            # Get ALL systems from API first (before filtering) to check completeness
            all_api_systems = await self.get_systems()
            all_api_system_names = set()
            for system in all_api_systems:
                if isinstance(system, dict):
                    system_name = (
                        system.get('name') or 
                        system.get('systemName') or 
                        system.get('displayName') or 
                        str(system.get('id') or system.get('systemId') or system.get('systemID') or system.get('system'))
                    )
                else:
                    system_name = str(system)
                if system_name:
                    all_api_system_names.add(system_name)
            
            # Filter to target system if specified
            if target_system:
                target_lower = target_system.lower()
                systems = [
                    system for system in systems
                    if (isinstance(system, dict) and (
                        str(system.get('systemName', '')).lower() == target_lower or
                        str(system.get('name', '')).lower() == target_lower or
                        str(system.get('displayName', '')).lower() == target_lower or
                        str(system.get('system', '')).lower() == target_lower
                    )) or (isinstance(system, str) and system.lower() == target_lower)
                ]
                if not systems:
                    return {'success': False, 'error': f'System "{target_system}" not found in EmuMovies'}
            
            logger.info(f"Found {len(systems)} systems to process")
            
            # Determine which systems to process (from filtered list)
            api_system_names = set()
            for system in systems:
                if isinstance(system, dict):
                    system_name = (
                        system.get('name') or 
                        system.get('systemName') or 
                        system.get('displayName') or 
                        str(system.get('id') or system.get('systemId') or system.get('systemID') or system.get('system'))
                    )
                else:
                    system_name = str(system)
                if system_name:
                    api_system_names.add(system_name)
            
            # Check if all systems are already in the database
            # Use all_api_system_names (not filtered) to check completeness
            db_system_names = set(consolidated_db.keys())
            all_systems_present = all_api_system_names.issubset(db_system_names) and len(all_api_system_names) == len(db_system_names)
            
            if all_systems_present and not target_system:
                logger.info("All systems are already in database. Regenerating all systems...")
                # Clear the database to force regeneration of all systems
                consolidated_db = {}
            else:
                if target_system:
                    logger.info(f"Building/updating system: {target_system} (preserving other systems)")
                else:
                    logger.info(f"Database is incomplete. {len(db_system_names)}/{len(all_api_system_names)} systems present. Building missing systems only...")
            
            total_systems = len(systems)
            processed_count = 0
            for idx, system in enumerate(systems):
                if isinstance(system, dict):
                    system_id = system.get('id') or system.get('systemId') or system.get('systemID') or system.get('system')
                    system_name = system.get('name') or system.get('systemName') or system.get('displayName') or f'System_{system_id}'
                else:
                    # Handle string or numeric entries by treating them as both ID and name
                    system_id = system
                    system_name = str(system)
                
                if not system_id:
                    logger.warning(f"Skipping system without ID: {system}")
                    continue
                
                # Skip if system is already in DB and we're not regenerating everything
                # Only skip if: not targeting specific system, not regenerating all, and system exists with content
                if not target_system and not all_systems_present and system_name in consolidated_db and consolidated_db[system_name]:
                    logger.info(f"Skipping existing system {idx + 1}/{total_systems}: {system_name}")
                    continue
                
                logger.info(f"Processing system {idx + 1}/{total_systems}: {system_name} (ID: {system_id})")
                processed_count += 1
                
                if progress_callback:
                    progress_msg = f"Processing {system_name}... ({idx + 1}/{total_systems})"
                    progress_pct = int((idx / total_systems) * 100)
                    if asyncio.iscoroutinefunction(progress_callback):
                        await progress_callback(progress_msg, progress_pct)
                    else:
                        progress_callback(progress_msg, progress_pct)
                
                # Ensure system entry exists in consolidated DB (overwrite if re-processing)
                consolidated_db[system_name] = {}
                
                # Get media types for this system
                try:
                    media_types = await self.get_media_types(system)
                except Exception as e:
                    logger.error(f"Error getting media types for {system_name}: {e}")
                    # Continue with next system
                    continue
                
                if not media_types:
                    logger.warning(f"No media types found for {system_name}, skipping...")
                    continue
                
                # Get media for each media type
                for media_type in media_types:
                    media_type_key, media_type_label = self._extract_media_type(media_type)
                    
                    if not media_type_key:
                        continue
                    
                    logger.info(f"  Fetching media for type: {media_type_label} (Key: {media_type_key})")
                    
                    # Ensure media type entry exists
                    if media_type_key not in consolidated_db[system_name]:
                        consolidated_db[system_name][media_type_key] = {}
                    
                    try:
                        media_sets = await self.get_media_sets(system, media_type_id=media_type_key)
                    except Exception as e:
                        logger.error(f"Error getting media sets for {system_name}/{media_type_key}: {e}")
                        # Continue with next media type
                        continue
                    
                    if not media_sets:
                        logger.warning(f"No media sets found for {system_name}/{media_type_key}, skipping...")
                        continue
                    
                    all_media = []
                    
                    # Iterate through media sets for this media type
                    for media_set in media_sets:
                        media_set_name = str(media_set).strip()
                        
                        logger.info(f"    Fetching media for set: {media_set_name}")
                        
                        try:
                            # Fetch all media for this system, media type, and media set
                            # Note: API returns full list without pagination support
                            media_batch = await self.get_media_list(
                                system_identifier=system,
                                media_type=media_type_key,
                                media_set_id=media_set_name
                            )
                            
                            if media_batch:
                                all_media.extend(media_batch)
                        except Exception as e:
                            logger.error(f"Error fetching media for {media_type_label} set {media_set_name}: {e}")
                            # Continue with next media set instead of failing entire system
                            continue
                        
                        # Small delay to avoid rate limiting
                        await asyncio.sleep(0.5)
                    
                    # Add media files to consolidated DB structure
                    for media_file in all_media:
                        if isinstance(media_file, str):
                            consolidated_db[system_name][media_type_key][media_file] = 1
                        elif isinstance(media_file, dict):
                            # Handle case where media list returns dicts (though simplified API usually returns strings)
                            filename = media_file.get('filename') or media_file.get('name') or str(media_file)
                            consolidated_db[system_name][media_type_key][filename] = 1
                    
                    logger.info(f"    Found {len(all_media)} media items for {media_type_label}")
                
                # Save database incrementally after each system
                with open(db_file, 'w', encoding='utf-8') as f:
                    json.dump(consolidated_db, f, indent=2, ensure_ascii=False)
            
            logger.info("EmuMovies local database build completed successfully")
            
            # Automatically generate normalized index after database build
            if progress_callback:
                if asyncio.iscoroutinefunction(progress_callback):
                    await progress_callback("Generating normalized index...", 100)
                else:
                    progress_callback("Generating normalized index...", 100)
            
            try:
                index_result = self.generate_normalized_index()
                if index_result.get('success'):
                    logger.info(f"Normalized index generated automatically: {index_result.get('index_path')}")
                else:
                    logger.warning(f"Failed to auto-generate index: {index_result.get('error')}")
            except Exception as e:
                logger.warning(f"Error auto-generating index: {e}")
            
            if progress_callback:
                if asyncio.iscoroutinefunction(progress_callback):
                    await progress_callback("Database build completed!", 100)
                else:
                    progress_callback("Database build completed!", 100)
            
            return {
                'success': True,
                'systems_count': processed_count,
                'total_systems': total_systems,
                'database_path': self.cache_dir
            }
            
        except Exception as e:
            logger.error(f"Error building local database: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}
    
    def get_system_media(self, system_id: int, media_type_id: int = None) -> List[Dict]:
        """Get media for a system from local database"""
        try:
            system_file = os.path.join(self.cache_dir, f'system_{system_id}.json')
            if not os.path.exists(system_file):
                logger.warning(f"System file not found: {system_file}")
                return []
            
            with open(system_file, 'r', encoding='utf-8') as f:
                system_data = json.load(f)
            
            if media_type_id is not None:
                media_type_key = str(media_type_id)
                if media_type_key in system_data.get('media', {}):
                    return system_data['media'][media_type_key].get('items', [])
                return []
            else:
                # Return all media from all types
                all_media = []
                for media_type_data in system_data.get('media', {}).values():
                    all_media.extend(media_type_data.get('items', []))
                return all_media
        except Exception as e:
            logger.error(f"Error loading system media from database: {e}")
            return []
    
    def get_database_index(self) -> Dict:
        """Get database index"""
        try:
            index_file = os.path.join(self.cache_dir, 'database_index.json')
            if not os.path.exists(index_file):
                return {}
            
            with open(index_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading database index: {e}")
            return {}

    def generate_normalized_index(self) -> Dict:
        """
        Generate a normalized index from the EmuMovies database.
        Format: [system][media_type][normalized_filename] = original_filename or [filename1, filename2, ...]
        If multiple files normalize to the same key, they are stored in an array.
        """
        try:
            # Import normalization function
            from game_utils import normalize_game_name
            
            db_file = os.path.join(self.cache_dir, 'emumovies.json')
            if not os.path.exists(db_file):
                logger.error("EmuMovies database not found. Please build it first.")
                return {'success': False, 'error': 'Database not found'}
            
            with open(db_file, 'r', encoding='utf-8') as f:
                db_data = json.load(f)
            
            index_data = {}
            
            total_systems = len(db_data)
            logger.info(f"Generating normalized index for {total_systems} systems...")
            
            for system_name, media_types in db_data.items():
                index_data[system_name] = {}
                
                for media_type, media_files in media_types.items():
                    index_data[system_name][media_type] = {}
                    
                    for filename in media_files.keys():
                        # Normalize filename: remove extension and use standard game name normalization
                        # Use remove_paranthesis=True to match how the scraper searches
                        name_without_ext = os.path.splitext(filename)[0]
                        normalized_name = normalize_game_name(name_without_ext, remove_paranthesis=True)
                        
                        if normalized_name:
                            # Store mapping - if multiple files normalize to same key, store in array
                            if normalized_name in index_data[system_name][media_type]:
                                # Key already exists - convert to array if needed
                                existing = index_data[system_name][media_type][normalized_name]
                                if isinstance(existing, list):
                                    existing.append(filename)
                                else:
                                    # Convert single value to array
                                    index_data[system_name][media_type][normalized_name] = [existing, filename]
                            else:
                                # First file for this normalized name
                                index_data[system_name][media_type][normalized_name] = filename
            
            # Save index to var/db/emumovies/emumovies_index.pkl
            os.makedirs(self.cache_dir, exist_ok=True)
            index_file = os.path.join(self.cache_dir, 'emumovies_index.pkl')
            
            with open(index_file, 'wb') as f:
                pickle.dump(index_data, f)
            
            logger.info(f"Normalized index generated successfully: {index_file}")
            
            return {
                'success': True,
                'index_path': index_file,
                'systems_count': len(index_data)
            }
            
        except Exception as e:
            logger.error(f"Error generating normalized index: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}

