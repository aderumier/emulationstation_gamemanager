#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Myrient Scraper Service - Match ROM filenames to Myrient JSON database entries
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
import logging
from typing import Dict, Optional

class MyrientScraperService:
    def __init__(self, config: Dict, scrappers_config: Dict = None, systems_config: Dict = None):
        self.config = config
        self.scrappers_config = scrappers_config or {}
        self.systems_config = systems_config or {}
        self.logger = logging.getLogger(__name__)
        
        # Myrient database path
        self.db_path = 'var/db/myrient'
        
        # In-memory databases: {db_name: {filename: {filename, date, size, url}}}
        # db_name is the JSON filename without extension
        self.databases = {}
        
        # Load all Myrient databases
        self._load_databases()
    
    def _load_databases(self):
        """Load all Myrient JSON databases into memory"""
        try:
            if not os.path.exists(self.db_path):
                self.logger.warning(f"Myrient database path not found: {self.db_path}")
                os.makedirs(self.db_path, exist_ok=True)
                return
            
            # Get all JSON files in the myrient directory
            json_files = [f for f in os.listdir(self.db_path) if f.endswith('.json')]
            
            for json_file in json_files:
                db_name = os.path.splitext(json_file)[0]
                file_path = os.path.join(self.db_path, json_file)
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        games_data = json.load(f)
                    
                    # Myrient JSON structure: {filename: {filename, date, size, url}}
                    # filename is the key, so we can use it directly
                    self.databases[db_name] = games_data
                    
                    self.logger.info(f"Loaded {len(self.databases[db_name])} entries for Myrient database: {db_name}")
                    
                except Exception as e:
                    self.logger.error(f"Error loading {json_file}: {e}")
                    continue
            
            self.logger.info(f"Loaded {len(self.databases)} Myrient databases")
            
        except Exception as e:
            self.logger.error(f"Error loading Myrient databases: {e}")
    
    def get_entry_by_filename(self, db_name: str, filename: str) -> Optional[Dict]:
        """
        Get Myrient entry by exact filename match.
        
        Args:
            db_name: Name of the Myrient database (JSON filename without extension)
            filename: ROM filename to match (can be with or without path)
        
        Returns:
            Myrient entry dict with {filename, date, size, url} or None if not found
        """
        if db_name not in self.databases:
            return None
        
        db = self.databases[db_name]
        
        # Extract just the filename if path is provided
        if os.path.sep in filename or os.path.altsep and os.path.altsep in filename:
            filename = os.path.basename(filename)
        
        # Try exact match (case-sensitive first)
        if filename in db:
            return db[filename]
        
        # Try case-insensitive match
        filename_lower = filename.lower()
        for key, value in db.items():
            if key.lower() == filename_lower:
                return value
        
        return None
    
    def find_match(self, db_name: str, rom_path: str) -> Optional[Dict]:
        """
        Find Myrient entry matching a ROM file path.
        
        Args:
            db_name: Name of the Myrient database
            rom_path: Full or relative path to ROM file
        
        Returns:
            Myrient entry dict or None if not found
        """
        if not db_name or db_name not in self.databases:
            return None
        
        # Extract filename from path
        filename = os.path.basename(rom_path)
        
        # Get entry by filename
        return self.get_entry_by_filename(db_name, filename)


