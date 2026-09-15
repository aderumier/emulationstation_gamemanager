#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Custom Scraper Service - Local database scrapper for custom JSON databases
Copyright (C) 2024 Alexandre Derumier <aderumier@gmail.com>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import json
import os
import re
import time
import logging
from typing import Dict, List, Optional, Any
from difflib import SequenceMatcher
from game_utils import normalize_game_name, calculate_similarity

# Fields a custom database may use to offer extra titles for one game, such as
# localized names. Either a list of names or a single one.
ALT_NAME_FIELDS = ('alt_names', 'alternate_names', 'alternative_names', 'alt_name')

# Normalized alternative titles shorter than this are refused: names are
# stripped to ASCII letters and digits, so a title in a non-Latin script can
# come out as a bare "7", which would match almost every ROM.
MIN_ALT_NAME_LENGTH = 4

# Bumped whenever the index changes shape or gains entries, so an existing
# cache is rebuilt rather than silently kept. The file fingerprint cannot catch
# this on its own: the databases are untouched, only the way they are indexed
# has changed.
CACHE_VERSION = 4

class CustomScraperService:
    def __init__(self, config: Dict, scrappers_config: Dict = None, systems_config: Dict = None):
        self.config = config
        self.scrappers_config = scrappers_config or {}
        self.systems_config = systems_config or {}
        self.logger = logging.getLogger(__name__)
        
        # Custom database path
        self.db_path = 'var/db/custom'
        
        # In-memory databases: {db_name: {game_id: {attributes}}}
        # db_name is the JSON filename without extension
        self.databases = {}
        
        # Global partitioned index: {db_name: {letter: {normalized_name: customid}}}
        self._global_similarity_index = {}
        
        # Load all custom databases
        self._load_databases()
        
        # Try to load partitioned indexes from cache. A cache that is missing,
        # stale or written by an older version is rebuilt in the background --
        # a stale one used to be trusted, leaving any database added since
        # unindexed and matching nothing at all in it.
        if not self._load_partitioned_indexes_from_cache():
            print("🔍 Custom partitioned index cache unusable, rebuilding in background thread...")
            self.logger.info("🔍 Custom partitioned index cache unusable, rebuilding in background thread...")
            import threading
            rebuild_thread = threading.Thread(target=self._rebuild_index_in_background, daemon=True)
            rebuild_thread.start()
    
    def _load_databases(self):
        """Load all custom JSON databases into memory"""
        try:
            if not os.path.exists(self.db_path):
                self.logger.warning(f"Custom database path not found: {self.db_path}")
                os.makedirs(self.db_path, exist_ok=True)
                return
            
            # Get all JSON files in the custom directory
            json_files = [f for f in os.listdir(self.db_path) if f.endswith('.json')]
            
            for json_file in json_files:
                db_name = os.path.splitext(json_file)[0]
                file_path = os.path.join(self.db_path, json_file)
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        games_data = json.load(f)
                    
                    # Handle both dict format {game_id: game_data} and list format [{game_data}]
                    if isinstance(games_data, dict):
                        # Already in dict format with game_id as key
                        self.databases[db_name] = games_data
                    elif isinstance(games_data, list):
                        # Convert list to dict - need to find the key field
                        games_dict = {}
                        for game in games_data:
                            if isinstance(game, dict):
                                # Try to find a unique identifier
                                # Check common fields: 'id', 'name', 'url', or first key
                                game_id = None
                                if 'id' in game:
                                    game_id = str(game['id'])
                                elif 'name' in game:
                                    # Use name as ID if no id field
                                    game_id = game['name']
                                elif 'url' in game:
                                    # Extract ID from URL if available
                                    url = game['url']
                                    # Try to extract slug from URL
                                    game_id = url.split('/')[-1] if '/' in url else url
                                else:
                                    # Use first key as ID
                                    game_id = list(game.keys())[0] if game.keys() else None
                                
                                if game_id:
                                    games_dict[str(game_id)] = game
                        
                        self.databases[db_name] = games_dict
                    
                    self.logger.info(f"Loaded {len(self.databases[db_name])} games for custom database: {db_name}")
                    
                except Exception as e:
                    self.logger.error(f"Error loading {json_file}: {e}")
                    continue
            
            self.logger.info(f"Loaded {len(self.databases)} custom databases")
            
        except Exception as e:
            self.logger.error(f"Error loading custom databases: {e}")
    
    def _rebuild_index_in_background(self):
        """Rebuild partitioned indexes in background thread"""
        try:
            print("🔧 [Background] Building partitioned similarity indexes for all custom databases...")
            self.logger.info("🔧 [Background] Building partitioned similarity indexes for all custom databases...")
            start_time = time.time()
            
            # Build the index
            self._build_all_partitioned_indexes()
            
            # Save to cache after building
            self._save_partitioned_indexes_to_cache()
            
            end_time = time.time()
            print(f"✅ [Background] Custom partitioned index rebuild completed in {end_time - start_time:.2f} seconds!")
            self.logger.info(f"✅ [Background] Custom partitioned index rebuild completed in {end_time - start_time:.2f} seconds!")
            
        except Exception as e:
            print(f"❌ [Background] Error rebuilding partitioned indexes: {e}")
            self.logger.error(f"[Background] Error rebuilding partitioned indexes: {e}")
            import traceback
            traceback.print_exc()
    
    @staticmethod
    def _alternative_names(game_data):
        """Extra titles a game can also be matched by, as a list of strings."""
        names = []
        for field in ALT_NAME_FIELDS:
            value = game_data.get(field)
            if isinstance(value, str):
                value = [value]
            if not isinstance(value, (list, tuple)):
                continue
            for name in value:
                if isinstance(name, str) and name.strip():
                    names.append(name.strip())
        return names

    @staticmethod
    def _article_free_key(name):
        """Index key for a title with its leading or trailing article dropped.

        Titles are indexed article included ("The Rookie Thief"), but
        similarity search normalizes the name it looks for with the article
        removed ("Rookie Thief") -- and it only scans the partition of the
        first letter, so such a game sat in partition "t" while every search
        for it looked in "r", and no ROM could ever match it. Indexing the
        article-free form too puts the game within reach of both lookups,
        including an exact one for a ROM named without the article.

        Returns '' when the key is too short to be worth indexing.
        """
        key = normalize_game_name(name, remove_paranthesis=False, remove_articles=True)
        key = key.strip() if key else ''
        return key if len(key) >= MIN_ALT_NAME_LENGTH else ''

    def _build_all_partitioned_indexes(self):
        """Build partitioned similarity indexes for all loaded databases during startup"""
        try:
            print("🔧 Building partitioned similarity indexes for all custom databases...")
            self.logger.info("🔧 Building partitioned similarity indexes for all custom databases...")
            start_time = time.time()
            
            total_databases = len(self.databases)
            processed_databases = 0
            
            # Create a new index (don't merge with existing - atomic replacement)
            new_index = {}
            
            for db_name, games_dict in self.databases.items():
                print(f"🔧 Building partitioned index for {db_name} ({len(games_dict)} games)...")
                self.logger.info(f"🔧 Building partitioned index for {db_name} ({len(games_dict)} games)...")
                
                # Initialize database index
                new_index[db_name] = {}
                
                # First pass: Group games by their normalized base title
                title_groups = {}
                
                # Alternative titles, indexed after the primary ones so they can
                # never displace them: {normalized_alt: game_id}
                alt_titles = {}

                # Article-free forms of the titles above, indexed last and, like
                # the alternatives, only where they take no key from a game that
                # owns it: {article_free_title: game_id}
                article_free = {}

                # Article-free forms two different games lay claim to, such as a
                # database holding both "The Voleur" and "Le Voleur" but no
                # plain "Voleur". Dropping the article would make them the same
                # game, so the key goes to neither: automatic scraping would
                # otherwise attach one game's media to the other on a coin flip.
                article_free_conflicts = set()

                def claim_article_free(name, game_id):
                    key = self._article_free_key(name)
                    if not key:
                        return
                    if article_free.setdefault(key, game_id) != game_id:
                        article_free_conflicts.add(key)

                for game_id, game_data in games_dict.items():
                    # Try to find game name field (common variations)
                    game_name = None
                    if isinstance(game_data, dict):
                        # Check common name fields
                        for name_field in ['name', 'title', 'game_name', 'gameName', 'Name', 'Title']:
                            if name_field in game_data and game_data[name_field]:
                                game_name = str(game_data[name_field])
                                break

                        for alt in self._alternative_names(game_data):
                            normalized_alt = normalize_game_name(alt, remove_paranthesis=False, remove_articles=False)
                            normalized_alt = normalized_alt.strip() if normalized_alt else ''
                            # Very short keys match far too much to be useful
                            if len(normalized_alt) >= MIN_ALT_NAME_LENGTH:
                                alt_titles.setdefault(normalized_alt, game_id)
                                claim_article_free(alt, game_id)

                    if game_name:
                        # Don't remove parentheses to preserve version info (e.g., "Game (ECS)" vs "Game (AGA)")
                        normalized_title = normalize_game_name(game_name, remove_paranthesis=False, remove_articles=False)
                        if normalized_title:
                            normalized_title = normalized_title.strip()  # Ensure no leading/trailing whitespace
                            if normalized_title not in title_groups:
                                title_groups[normalized_title] = []
                            title_groups[normalized_title].append((game_id, game_data, game_name))
                            
                # Second pass: Build index
                def partition_for(key):
                    first_char = key[0] if key else 'other'
                    return new_index[db_name].setdefault(first_char, {})

                # Titles are placed before the disambiguated variants below, so
                # a game's own name always wins the key it deserves and a
                # variant of some other game can never displace it.
                variants = []

                for normalized_title, group in title_groups.items():
                    if len(group) == 1:
                        # No duplicates, index normally
                        game_id, _, game_name = group[0]
                        partition_for(normalized_title)[normalized_title] = game_id
                        claim_article_free(game_name, game_id)
                        continue

                    # Several games share this title -- different regions or
                    # releases of the same game, mostly. Each gets a key of its
                    # own below, but the plain title must stay indexed too or an
                    # exact lookup for it finds nothing at all and automatic
                    # scraping cannot identify the game. It points at the
                    # fullest entry of the group, which is the one worth
                    # scraping; ties break on id so the choice is stable.
                    best = min(group, key=lambda entry: (
                        -sum(1 for value in entry[1].values() if value) if isinstance(entry[1], dict) else 0,
                        str(entry[0])))
                    partition_for(normalized_title)[normalized_title] = best[0]
                    claim_article_free(best[2], best[0])

                    # Duplicates found, append publisher to the name for each game in the group
                    for game_id, game_data, game_name in group:
                        publisher = None
                        if isinstance(game_data, dict):
                            publisher = game_data.get('publisher')

                        if publisher:
                            title_pub = normalize_game_name(f"{game_name} ({publisher})", remove_paranthesis=False, remove_articles=False)
                        else:
                            # Fallback if no publisher
                            title_pub = normalize_game_name(f"{game_name} ({game_id})", remove_paranthesis=False, remove_articles=False)

                        if title_pub and title_pub.strip():
                            variants.append((title_pub.strip(), game_id, game_name, publisher))

                for title_pub, game_id, game_name, publisher in variants:
                    # Region variants usually share a publisher as well as a
                    # title, so this key collides and one of them used to
                    # overwrite the other, leaving it unreachable. Normalizing
                    # also strips non-Latin text, which collapses a Japanese
                    # publisher to empty parentheses and can collide with an
                    # unrelated game's title. The id always tells them apart.
                    partition = partition_for(title_pub)
                    if partition.get(title_pub, game_id) != game_id:
                        unique = normalize_game_name(f"{game_name} ({publisher} {game_id})", remove_paranthesis=False, remove_articles=False)
                        if not (unique and unique.strip()):
                            continue
                        title_pub = unique.strip()
                        partition = partition_for(title_pub)
                        if partition.get(title_pub, game_id) != game_id:
                            continue

                    partition[title_pub] = game_id

                # Third pass: alternative titles, for databases that carry them
                # (GameTDB ships each game's localized names, so a French dump
                # can match a French title). Only free keys are taken, so a
                # primary title is never shadowed by another game's alias.
                alts_added = 0
                for normalized_alt, game_id in alt_titles.items():
                    first_char = normalized_alt[0] if normalized_alt else 'other'
                    partition = new_index[db_name].setdefault(first_char, {})
                    if normalized_alt not in partition:
                        partition[normalized_alt] = game_id
                        alts_added += 1
                if alts_added:
                    print(f"🔧 Indexed {alts_added} alternative titles for {db_name}")
                    self.logger.info(f"🔧 Indexed {alts_added} alternative titles for {db_name}")

                # Fourth pass: the same titles without their article. Taken
                # last and only where the key is free, so a game actually named
                # "Rookie Thief" keeps that key and "The Rookie Thief" merely
                # becomes reachable by it when nothing else claims it.
                article_free_added = 0
                for article_free_title, game_id in article_free.items():
                    if article_free_title in article_free_conflicts:
                        continue
                    partition = partition_for(article_free_title)
                    if article_free_title not in partition:
                        partition[article_free_title] = game_id
                        article_free_added += 1
                if article_free_added:
                    print(f"🔧 Indexed {article_free_added} article-free titles for {db_name}")
                    self.logger.info(f"🔧 Indexed {article_free_added} article-free titles for {db_name}")

                processed_databases += 1
                partition_count = len(new_index[db_name])
                print(f"✅ Partitioned index built for {db_name} ({partition_count} partitions)")
                self.logger.info(f"✅ Partitioned index built for {db_name} ({partition_count} partitions)")
            
            # Replace the old index with the new one atomically
            self._global_similarity_index = new_index
            
            end_time = time.time()
            print(f"✅ All partitioned similarity indexes built successfully in {end_time - start_time:.2f} seconds!")
            print(f"📊 Processed {processed_databases} custom databases with partitioned indexes")
            self.logger.info(f"✅ All partitioned similarity indexes built successfully in {end_time - start_time:.2f} seconds!")
            self.logger.info(f"📊 Processed {processed_databases} custom databases with partitioned indexes")
            
        except Exception as e:
            print(f"❌ Error building partitioned indexes: {e}")
            self.logger.error(f"Error building partitioned indexes: {e}")
    
    def _databases_signature(self):
        """Fingerprint of the JSON databases on disk: name, size and mtime.

        The cache is only valid for the databases it was built from. Without
        this, dropping a new JSON into var/db/custom leaves it unindexed and
        matching silently finds nothing in it until the cache is deleted.
        """
        signature = []
        try:
            for filename in sorted(os.listdir(self.db_path)):
                if not filename.endswith('.json'):
                    continue
                stat = os.stat(os.path.join(self.db_path, filename))
                signature.append((filename, stat.st_size, int(stat.st_mtime)))
        except OSError as e:
            self.logger.warning(f"Could not fingerprint custom databases: {e}")
            return None
        return signature

    def _save_partitioned_indexes_to_cache(self):
        """Save partitioned indexes to cache file for faster startup"""
        try:
            import pickle
            import os

            cache_dir = 'var/cache'
            os.makedirs(cache_dir, exist_ok=True)
            cache_file = os.path.join(cache_dir, 'custom_partitioned_index.pkl')

            # Convert index to dictionaries for pickling
            cache_data = {}
            for db_name, db_index in self._global_similarity_index.items():
                cache_data[db_name] = {}
                for letter, normalized_dict in db_index.items():
                    cache_data[db_name][letter] = normalized_dict

            cache_data = {
                'version': CACHE_VERSION,
                'signature': self._databases_signature(),
                'databases': cache_data,
            }

            with open(cache_file, 'wb') as f:
                pickle.dump(cache_data, f)
            
            print(f"✅ Saved custom partitioned index to {cache_file}")
            self.logger.info(f"✅ Saved custom partitioned index to {cache_file}")
            
        except Exception as e:
            print(f"⚠️ Warning: Failed to save custom partitioned index cache: {e}")
            self.logger.warning(f"Failed to save custom partitioned index cache: {e}")
    
    def _load_partitioned_indexes_from_cache(self):
        """Load partitioned indexes from cache file"""
        try:
            import pickle
            import os
            
            cache_file = os.path.join('var/cache', 'custom_partitioned_index.pkl')
            if not os.path.exists(cache_file):
                print("🔍 No custom partitioned index cache found, will build from scratch")
                self.logger.info("🔍 No custom partitioned index cache found, will build from scratch")
                return False
            
            with open(cache_file, 'rb') as f:
                cache_data = pickle.load(f)

            # A cache written before the index carried a signature cannot be
            # checked against the databases, so it is discarded rather than
            # trusted -- it also predates alternative-title indexing.
            if not (isinstance(cache_data, dict) and cache_data.get('version') == CACHE_VERSION):
                print("🔍 Custom partitioned index cache is from an older format, rebuilding")
                self.logger.info("🔍 Custom partitioned index cache is from an older format, rebuilding")
                return False

            if cache_data.get('signature') != self._databases_signature():
                print("🔍 Custom databases changed since the index was cached, rebuilding")
                self.logger.info("🔍 Custom databases changed since the index was cached, rebuilding")
                return False

            cache_data = cache_data.get('databases', {})

            # Convert dictionaries back to index structure
            # Handle both old format (list of items) and new format (dict)
            self._global_similarity_index = {}
            for db_name, db_index in cache_data.items():
                self._global_similarity_index[db_name] = {}
                for letter, data in db_index.items():
                    if isinstance(data, dict):
                        # New format: {normalized_name: customid}
                        self._global_similarity_index[db_name][letter] = data
                    elif isinstance(data, list):
                        # Old format: list of items, convert to dict
                        normalized_dict = {}
                        for item in data:
                            if isinstance(item, dict):
                                normalized_dict[item.get('normalized', '')] = item.get('game_id', '')
                            else:
                                # Handle namedtuple format (if present)
                                try:
                                    normalized_dict[item.normalized] = item.game_id
                                except AttributeError:
                                    pass
                        self._global_similarity_index[db_name][letter] = normalized_dict
            
            print(f"✅ Loaded custom partitioned index from cache")
            self.logger.info(f"✅ Loaded custom partitioned index from cache")
            return True
            
        except Exception as e:
            print(f"⚠️ Warning: Failed to load custom partitioned index cache: {e}")
            self.logger.warning(f"Failed to load custom partitioned index cache: {e}")
            return False
    
    def get_available_databases(self) -> List[str]:
        """Get list of available custom database names"""
        return list(self.databases.keys())
    
    def get_game_by_id(self, db_name: str, game_id: str) -> Optional[Dict]:
        """Get game data by database name and game ID"""
        if db_name in self.databases:
            return self.databases[db_name].get(game_id)
        return None
    
    def find_game_exact(self, db_name: str, game_name: str) -> Optional[tuple]:
        """
        Find a game in the custom database by exact title match using partitioned index
        
        Args:
            db_name: Name of the custom database (JSON filename without extension)
            game_name: Game name to search for
        
        Returns:
            Tuple of (game_id, game_data) if exact match found, None otherwise
        """
        if db_name not in self.databases:
            self.logger.warning(f"Database {db_name} not found")
            return None
        
        if db_name not in self._global_similarity_index:
            self.logger.warning(f"No index found for database {db_name}")
            return None
        
        # Normalize the search name (keep parentheses to match versioned games)
        normalized_search = normalize_game_name(game_name, remove_paranthesis=False, remove_articles=False)
        if not normalized_search:
            self.logger.debug(f"Normalized search is empty for '{game_name}'")
            return None
        
        # Search in the appropriate partition for exact match, then for the
        # same title without its article: a ROM named "The Immortal" has to
        # find a database entry named "Immortal" just as the index makes the
        # opposite case work. Articles are decoration on a title, not part of
        # what identifies the game.
        keys = [normalized_search]
        article_free_search = self._article_free_key(game_name)
        if article_free_search and article_free_search != normalized_search:
            keys.append(article_free_search)

        for key in keys:
            partition_dict = self._global_similarity_index[db_name].get(key[0] if key else 'other')
            if partition_dict and key in partition_dict:
                game_id = partition_dict[key]
                game_data = self.databases[db_name].get(game_id, {})
                return (game_id, game_data)

        return None
    
    def find_best_matches(self, db_name: str, game_name: str, max_results: int = 10, min_similarity: float = 0.0) -> List[Dict]:
        """
        Find best matching games in a specific custom database
        
        Args:
            db_name: Name of the custom database (JSON filename without extension)
            game_name: Game name to search for
            max_results: Maximum number of results to return
            min_similarity: Minimum similarity threshold (0.0 to 1.0)
        
        Returns:
            List of dicts with 'game_id', 'name', 'similarity', and 'game_data'
        """
        if db_name not in self.databases:
            self.logger.warning(f"Database {db_name} not found")
            return []
        
        if db_name not in self._global_similarity_index:
            self.logger.warning(f"No index found for database {db_name}")
            return []
        
        # Normalize the search name (keep parentheses to match versioned games)
        normalized_search = normalize_game_name(game_name, remove_paranthesis=False, remove_articles=True)
        if not normalized_search:
            return []
        
        # Get partition based on first character
        first_char = normalized_search[0] if normalized_search else 'other'
        
        # Get candidates from the appropriate partition
        candidates = []
        if first_char in self._global_similarity_index[db_name]:
            partition_dict = self._global_similarity_index[db_name][first_char]
            # Convert dict to list of (normalized_name, game_id) tuples
            candidates = [(norm_name, game_id) for norm_name, game_id in partition_dict.items()]
        else:
            # If partition doesn't exist, search all partitions (fallback)
            for partition_dict in self._global_similarity_index[db_name].values():
                candidates.extend([(norm_name, game_id) for norm_name, game_id in partition_dict.items()])
        
        # Calculate similarity for each candidate, keeping the best score per
        # game: one game can be indexed under several titles (its primary name
        # and its localized ones), and the caller wants distinct games.
        best = {}
        for normalized_name, game_id in candidates:
            similarity = calculate_similarity(normalized_search, normalized_name)
            if similarity < min_similarity:
                continue
            if game_id in best and best[game_id]['similarity'] >= similarity:
                continue
            game_data = self.databases[db_name].get(game_id, {})
            # Get original game name from game_data
            game_name = game_data.get('name', normalized_name)
            best[game_id] = {
                'game_id': game_id,
                'name': game_name,
                'similarity': similarity,
                'game_data': game_data
            }

        # Sort by similarity (descending) and return top results
        matches = sorted(best.values(), key=lambda x: x['similarity'], reverse=True)
        return matches[:max_results]
    
    def get_media_url(self, db_name: str, game_id: str, media_field: str) -> Optional[str]:
        """
        Get media URL for a specific game and media field
        
        Args:
            db_name: Name of the custom database
            game_id: Game ID
            media_field: Media field name (e.g., 'boxfront', 'boxback', 'titleshot', 'screenshot', 'image')
        
        Returns:
            Media URL (first item if array) or None if not found
        """
        game_data = self.get_game_by_id(db_name, game_id)
        if not game_data:
            return None
        
        # Check common field name variations
        field_variations = [
            media_field,
            media_field.lower(),
            media_field.upper(),
            media_field.capitalize(),
        ]
        
        for field in field_variations:
            if field in game_data and game_data[field]:
                value = game_data[field]
                # Handle arrays - return first item for backward compatibility
                if isinstance(value, list):
                    if len(value) > 0:
                        return value[0] if isinstance(value[0], str) else None
                    return None
                # Return single value as-is
                return value if isinstance(value, str) else None
        
        return None
    
    def get_media_urls(self, db_name: str, game_id: str, media_field: str) -> List[str]:
        """
        Get media URLs for a specific game and media field (always returns a list)
        
        Args:
            db_name: Name of the custom database
            game_id: Game ID
            media_field: Media field name (e.g., 'boxfront', 'boxback', 'titleshot', 'screenshot', 'image')
        
        Returns:
            List of media URLs (empty list if not found)
        """
        game_data = self.get_game_by_id(db_name, game_id)
        if not game_data:
            return []
        
        # Check common field name variations
        field_variations = [
            media_field,
            media_field.lower(),
            media_field.upper(),
            media_field.capitalize(),
        ]
        
        for field in field_variations:
            if field in game_data and game_data[field]:
                value = game_data[field]
                # Handle arrays - return as list
                if isinstance(value, list):
                    # Filter to only include string URLs
                    return [url for url in value if isinstance(url, str)]
                # Convert single value to list
                if isinstance(value, str):
                    return [value]
        
        return []

