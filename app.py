#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GameManager - Game Collection Management System
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

from sys import dont_write_bytecode
from flask import Flask, render_template, request, jsonify, send_from_directory, send_file, Response, redirect, url_for, session, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
# from flask_session import Session
# from flask_session.sessions import FileSystemSessionInterface
import asyncio
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room, leave_room
import os
import json
import time
import xml.etree.ElementTree as ET
import threading
import re
import difflib
import shutil
import subprocess
import requests
import httpx
import multiprocessing
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
import hashlib
import secrets
from datetime import datetime
import uuid
import subprocess as sp
from collections import Counter

# FFmpeg cropping functions for auto-cropping black borders
def cropdetect(video_file_path, start_time, duration):
    """Detect crop dimensions for removing black borders"""
    try:
        print(f"cropdetect: Analyzing {video_file_path} from {start_time}s for {duration}s")
        
        proc = sp.Popen([
            "ffmpeg", 
            "-ss", str(start_time), 
            "-i", video_file_path, 
            "-to", str(duration), 
            "-vf", "cropdetect", 
            "-f", "rawvideo", 
            "-y", "/dev/null"
        ], stdout=sp.PIPE, stderr=sp.PIPE)
        
        infos = proc.stderr.read()
        infos = infos.decode()
        print(f"cropdetect: FFmpeg stderr output: {infos}")
        
        match = re.findall(r"crop=(\S+)", infos)
        print(f"cropdetect: Found crop matches: {match}")
        
        if match:
            mostCommonCrop = Counter(match).most_common(1)
            crop_dimensions = mostCommonCrop[0][0]
            crop_count = mostCommonCrop[0][1]
            print(f"cropdetect: Selected crop dimensions: {crop_dimensions} (appeared {crop_count} times)")
            
            # Check if crop is needed (if crop dimensions are different from full video)
            # Get video dimensions first
            video_info_proc = sp.Popen([
                "ffprobe", 
                "-v", "quiet",
                "-print_format", "json",
                "-show_streams",
                video_file_path
            ], stdout=sp.PIPE, stderr=sp.PIPE)
            
            video_info = video_info_proc.stdout.read().decode()
            import json
            try:
                video_data = json.loads(video_info)
                for stream in video_data.get('streams', []):
                    if stream.get('codec_type') == 'video':
                        video_width = stream.get('width', 0)
                        video_height = stream.get('height', 0)
                        print(f"cropdetect: Video dimensions: {video_width}x{video_height}")
                        
                        # Parse crop dimensions (format: width:height:x:y)
                        crop_parts = crop_dimensions.split(':')
                        if len(crop_parts) >= 2:
                            crop_width = int(crop_parts[0])
                            crop_height = int(crop_parts[1])
                            print(f"cropdetect: Crop dimensions: {crop_width}x{crop_height}")
                            
                            if crop_width == video_width and crop_height == video_height:
                                print(f"cropdetect: No cropping needed - crop dimensions match video dimensions")
                                return None  # No cropping needed
                            else:
                                print(f"cropdetect: Cropping needed - dimensions differ from original")
                                return crop_dimensions
                        break
            except Exception as e:
                print(f"cropdetect: Could not parse video info: {e}")
                return crop_dimensions  # Default to cropping if we can't determine
            
            return crop_dimensions
        
        print(f"cropdetect: No crop dimensions found in FFmpeg output")
        raise Exception("Can't find crop dimensions")
        
    except Exception as e:
        print(f"Error in cropdetect: {e}")
        raise

def crop_video(video_file_path, newfile, start_time, duration):
    """Apply crop to remove black borders"""
    try:
        print(f"crop_video: Starting crop process for {video_file_path}")
        crop_dimensions = cropdetect(video_file_path, start_time, duration)
        
        # Check if cropping is actually needed
        if crop_dimensions is None:
            print(f"crop_video: No cropping needed - copying original file to {newfile}")
            import shutil
            shutil.copy2(video_file_path, newfile)
            print(f"crop_video: File copied successfully")
            return True
        
        print(f"crop_video: Cropping needed - applying crop {crop_dimensions} to create {newfile}")
        
        # Log the exact FFmpeg command that will be executed
        ffmpeg_cmd = [
            "ffmpeg", 
            "-ss", str(start_time), 
            "-i", video_file_path,
            "-to", str(duration), 
            "-filter:v", f"crop={crop_dimensions}", 
            newfile
        ]
        print(f"crop_video: Executing FFmpeg command: {' '.join(ffmpeg_cmd)}")
        
        pipe = sp.Popen(ffmpeg_cmd, stdout=sp.PIPE, stderr=sp.PIPE)
        stdout, stderr = pipe.communicate()
        
        print(f"crop_video: FFmpeg stdout: {stdout.decode()}")
        print(f"crop_video: FFmpeg stderr: {stderr.decode()}")
        print(f"crop_video: Crop process completed, return code: {pipe.returncode}")
        
        if pipe.returncode != 0:
            raise Exception(f"FFmpeg crop failed with return code {pipe.returncode}")
        
        print(f"crop_video: Cropping completed successfully")
        return True
        
    except Exception as e:
        print(f"Error in crop_video: {e}")
        raise

# User model for authentication
class User(UserMixin):
    def __init__(self, user_id, username, email=None, discord_id=None, is_active=True, is_validated=False, created_at=None, last_login=None):
        self.id = user_id
        self.username = username
        self.email = email
        self.discord_id = discord_id
        self._is_active = is_active
        self.is_validated = is_validated
        self.created_at = created_at or datetime.now().isoformat()
        self.last_login = last_login
    
    @property
    def is_active(self):
        return self._is_active
    
    @is_active.setter
    def is_active(self, value):
        self._is_active = value

# Authentication functions
def hash_password(password):
    """Hash a password using SHA-256 with salt"""
    salt = secrets.token_hex(16)
    password_hash = hashlib.sha256((password + salt).encode()).hexdigest()
    return f"{salt}:{password_hash}"

def verify_password(password, hashed_password):
    """Verify a password against its hash"""
    try:
        salt, password_hash = hashed_password.split(':')
        return hashlib.sha256((password + salt).encode()).hexdigest() == password_hash
    except:
        return False

def load_json_with_comments(file_path):
    """Load JSON file with support for # comments"""
    if not os.path.exists(file_path):
        return {}
    
    with open(file_path, 'r') as f:
        # Read file content and remove comments (lines starting with #)
        content = f.read()
        lines = content.split('\n')
        cleaned_lines = []
        for line in lines:
            # Remove inline comments (but preserve strings that contain #)
            if '#' in line:
                # Simple approach: remove everything after # if it's not in quotes
                in_quotes = False
                escape_next = False
                comment_start = -1
                for i, char in enumerate(line):
                    if escape_next:
                        escape_next = False
                        continue
                    if char == '\\':
                        escape_next = True
                        continue
                    if char in ['"', "'"]:
                        in_quotes = not in_quotes
                    elif char == '#' and not in_quotes:
                        comment_start = i
                        break
                if comment_start >= 0:
                    line = line[:comment_start].rstrip()
            cleaned_lines.append(line)
        cleaned_content = '\n'.join(cleaned_lines)
        return json.loads(cleaned_content)

def load_users():
    """Load users from user.cfg file"""
    return load_json_with_comments('var/config/user.cfg')

def save_users(users):
    """Save users to user.cfg file"""
    with open('var/config/user.cfg', 'w') as f:
        json.dump(users, f, indent=4)

def get_user_by_id(user_id):
    """Get user by ID"""
    users = load_users()
    user_data = users.get(user_id)
    if user_data:
        return User(
            user_id=user_id,
            username=user_data['username'],
            email=user_data.get('email'),
            discord_id=user_data.get('discord_id'),
            is_active=user_data.get('is_active', True),
            is_validated=user_data.get('is_validated', False),
            created_at=user_data.get('created_at'),
            last_login=user_data.get('last_login')
        )
    return None

def get_user_by_username(username):
    """Get user by username"""
    users = load_users()
    for user_id, user_data in users.items():
        if user_data['username'] == username:
            return User(
                user_id=user_id,
                username=user_data['username'],
                email=user_data.get('email'),
                discord_id=user_data.get('discord_id'),
                is_active=user_data.get('is_active', True),
                is_validated=user_data.get('is_validated', False),
                created_at=user_data.get('created_at'),
                last_login=user_data.get('last_login')
            )
    return None

def get_user_by_discord_id(discord_id):
    """Get user by Discord ID"""
    users = load_users()
    for user_id, user_data in users.items():
        if user_data.get('discord_id') == discord_id:
            return User(
                user_id=user_id,
                username=user_data['username'],
                email=user_data.get('email'),
                discord_id=user_data.get('discord_id'),
                is_active=user_data.get('is_active', True),
                is_validated=user_data.get('is_validated', False),
                created_at=user_data.get('created_at'),
                last_login=user_data.get('last_login')
            )
    return None

def create_user(username, password, email=None, discord_id=None):
    """Create a new user"""
    users = load_users()
    user_id = str(uuid.uuid4())
    
    # Check if username already exists
    for existing_user in users.values():
        if existing_user['username'] == username:
            return None, "Username already exists"
    
    # Check if Discord ID already exists
    if discord_id:
        for existing_user in users.values():
            if existing_user.get('discord_id') == discord_id:
                return None, "Discord account already linked"
    
    user_data = {
        'username': username,
        'password_hash': hash_password(password),
        'email': email,
        'discord_id': discord_id,
        'is_active': True,
        'is_validated': False,  # New users need validation
        'created_at': datetime.now().isoformat(),
        'last_login': None
    }
    
    users[user_id] = user_data
    save_users(users)
    
    return User(
        user_id=user_id,
        username=username,
        email=email,
        discord_id=discord_id,
        is_active=True,
        is_validated=False,
        created_at=user_data['created_at']
    ), None

def update_user_last_login(user_id):
    """Update user's last login time"""
    users = load_users()
    if user_id in users:
        users[user_id]['last_login'] = datetime.now().isoformat()
        save_users(users)

def initialize_default_admin():
    """Initialize default admin user if no users exist"""
    users = load_users()
    if not users:
        # Create default admin user
        admin_user, error = create_user('admin', 'admin123', 'admin@cursorscraper.local')
        if admin_user:
            # Validate the admin user immediately
            users = load_users()
            if admin_user.id in users:
                users[admin_user.id]['is_validated'] = True
                save_users(users)
                print("✅ Default admin user created: username='admin', password='admin123'")
                print("⚠️  Please change the default password after first login!")
            else:
                print("❌ Failed to validate default admin user")
        else:
            print(f"❌ Failed to create default admin user: {error}")
    else:
        print(f"✅ Found {len(users)} existing users")

# Configuration loading function
def load_config():
    """Load configuration from config.json file"""
    config_file = 'var/config/config.json'
    default_config = {
        'roms_root_directory': 'roms',
        'task_logs_directory': 'var/task_logs',
        'max_tasks_to_keep': 30,
        'server': {
            'host': '0.0.0.0',
            'port': 5000,
            'debug': False
        },
        'logging': {
            'level': 'INFO',
            'file': 'app.log'
        }
    }
    
    try:
        if os.path.exists(config_file):
            user_config = load_json_with_comments(config_file)
            # Merge user config with defaults
            for key, value in user_config.items():
                if isinstance(value, dict) and key in default_config:
                    default_config[key].update(value)
                else:
                    default_config[key] = value
                print(f"✅ Configuration loaded from {config_file}")
        else:
            print(f"⚠️  No {config_file} found, using default configuration")
            # Create default config file
            with open(config_file, 'w') as f:
                json.dump(default_config, f, indent=4)
            print(f"📝 Created default {config_file}")
    except Exception as e:
        print(f"❌ Error loading configuration: {e}, using defaults")
    
    return default_config

# Load configuration
config = load_config()

# yt-dlp management functions
def ensure_yt_dlp_binary():
    """Ensure we have the latest yt-dlp binary in tools/ directory"""
    tools_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tools')
    yt_dlp_path = os.path.join(tools_dir, 'yt-dlp')
    
    # Create tools directory if it doesn't exist
    os.makedirs(tools_dir, exist_ok=True)
    
    # Check if yt-dlp binary exists
    if not os.path.exists(yt_dlp_path):
        print("Downloading latest yt-dlp binary...")
        try:
            # Download the latest yt-dlp binary
            response = requests.get('https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp', timeout=30)
            response.raise_for_status()
            
            # Save the binary
            with open(yt_dlp_path, 'wb') as f:
                f.write(response.content)
            
            # Make it executable
            os.chmod(yt_dlp_path, 0o755)
            print(f"Downloaded yt-dlp to {yt_dlp_path}")
            
        except Exception as e:
            print(f"Failed to download yt-dlp: {e}")
            return None
    else:
        # Binary exists, update it in background
        def update_yt_dlp():
            try:
                print("Updating yt-dlp in background...")
                result = subprocess.run([yt_dlp_path, '-U'], capture_output=True, text=True, timeout=60)
                if result.returncode == 0:
                    print("yt-dlp updated successfully")
                else:
                    print(f"yt-dlp update failed: {result.stderr}")
            except Exception as e:
                print(f"Failed to update yt-dlp: {e}")
        
        # Start update in background thread
        threading.Thread(target=update_yt_dlp, daemon=True).start()
    
    return yt_dlp_path

def get_yt_dlp_path():
    """Get the path to the yt-dlp binary, ensuring it exists"""
    tools_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tools')
    yt_dlp_path = os.path.join(tools_dir, 'yt-dlp')
    
    if os.path.exists(yt_dlp_path):
        return yt_dlp_path
    else:
        # Fallback to system yt-dlp if tools version doesn't exist
        return 'yt-dlp'

app = Flask(__name__)

# Use a fixed secret key for persistent sessions (in production, use environment variable)
app.secret_key = 'cursorscraper-secret-key-2024-persistent-sessions'

# Configure Flask sessions (using built-in session management)
# Ensure Flask-Session is completely disabled
app.config['SESSION_TYPE'] = None  # Disable Flask-Session
app.config['SESSION_COOKIE_SECURE'] = False  # Set to True in production with HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_NAME'] = 'cursorscraper_session'
app.config['PERMANENT_SESSION_LIFETIME'] = 86400 * 7  # 7 days

# Debug: Check if Flask-Session is being used
print(f"Flask-Session disabled. Session type: {app.config.get('SESSION_TYPE', 'None')}")
print(f"Session interface type: {type(app.session_interface)}")

# Initialize Flask-Login with session configuration
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'
login_manager.session_protection = 'strong'  # Use strong session protection

@login_manager.user_loader
def load_user(user_id):
    return get_user_by_id(user_id)

CORS(app, supports_credentials=True)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

@app.before_request
def log_request_info():
    print(f"DEBUG REQUEST: {request.method} {request.path} - Endpoint: {request.endpoint}")

# Disable Flask's default HTTP request logging to reduce console spam
import logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

# Configuration
ROMS_FOLDER = config['roms_root_directory']
GAMELISTS_FOLDER = 'var/gamelists'

app.config['ROMS_FOLDER'] = ROMS_FOLDER
app.config['GAMELISTS_FOLDER'] = GAMELISTS_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Create directories if they don't exist
os.makedirs(ROMS_FOLDER, exist_ok=True)
os.makedirs(GAMELISTS_FOLDER, exist_ok=True)

def get_gamelist_path(system_name):
    """Get the gamelist path for a system, ensuring the directory exists"""
    gamelist_dir = os.path.join(GAMELISTS_FOLDER, system_name)
    os.makedirs(gamelist_dir, exist_ok=True)
    return os.path.join(gamelist_dir, 'gamelist.xml')

def ensure_gamelist_exists(system_name):
    """Ensure gamelist exists in var/gamelists (does not auto-copy from roms/)"""
    gamelist_path = get_gamelist_path(system_name)
    
    # Just return the path - don't auto-copy from roms/
    return gamelist_path

def ensure_gamelist_exists_for_scan(system_name):
    """Ensure gamelist exists in var/gamelists for ROM scan, copying from roms/ if needed"""
    gamelist_path = get_gamelist_path(system_name)
    
    # If gamelist already exists in var/gamelists, return it
    if os.path.exists(gamelist_path):
        return gamelist_path
    
    # Check if gamelist exists in roms/ and copy it (only during scan)
    roms_gamelist_path = os.path.join(ROMS_FOLDER, system_name, 'gamelist.xml')
    if os.path.exists(roms_gamelist_path):
        try:
            shutil.copy2(roms_gamelist_path, gamelist_path)
            print(f"Copied gamelist from {roms_gamelist_path} to {gamelist_path} for ROM scan")
            return gamelist_path
        except Exception as e:
            print(f"Error copying gamelist: {e}")
            return gamelist_path
    
    # If no gamelist exists anywhere, return the path for creating a new one
    return gamelist_path

def compare_gamelist_files(system_name):
    """Compare gamelist files between var/gamelists and roms directories"""
    gamelist_path = get_gamelist_path(system_name)
    roms_gamelist_path = os.path.join(ROMS_FOLDER, system_name, 'gamelist.xml')
    
    if not os.path.exists(gamelist_path):
        return {'success': False, 'error': f'Gamelist not found in var/gamelists/{system_name}/gamelist.xml'}
    
    try:
        # Parse both gamelist files
        var_games = parse_gamelist_xml(gamelist_path)
        roms_games = parse_gamelist_xml(roms_gamelist_path) if os.path.exists(roms_gamelist_path) else []
        
        # Create dictionaries for easier comparison (using path as key)
        var_games_dict = {game.get('path', ''): game for game in var_games}
        roms_games_dict = {game.get('path', ''): game for game in roms_games}
        
        # Find added and removed games
        var_paths = set(var_games_dict.keys())
        roms_paths = set(roms_games_dict.keys())
        
        added_games = var_paths - roms_paths
        removed_games = roms_paths - var_paths
        
        # Get added and removed game details
        added_games_list = [var_games_dict[path] for path in added_games]
        removed_games_list = [roms_games_dict[path] for path in removed_games]
        
        # Count media changes
        media_fields = ['image', 'thumbnail', 'video', 'marquee', 'manual', 'boxfront', 'boxback', 'boxside', 'cartridge', 'logo', 'bezel', 'fanart', 'banner', 'screenshot', 'titlescreen']
        
        media_added = 0
        media_removed = 0
        
        # Count media in added games
        for game in added_games_list:
            for field in media_fields:
                if game.get(field):
                    media_added += 1
        
        # Count media in removed games
        for game in removed_games_list:
            for field in media_fields:
                if game.get(field):
                    media_removed += 1
        
        # Count total media in var gamelist
        total_media = 0
        for game in var_games:
            for field in media_fields:
                if game.get(field):
                    total_media += 1
        
        return {
            'success': True,
            'system_name': system_name,
            'games_added': len(added_games_list),
            'games_removed': len(removed_games_list),
            'games_added_list': [{'name': game.get('name', 'Unknown'), 'path': game.get('path', '')} for game in added_games_list],
            'games_removed_list': [{'name': game.get('name', 'Unknown'), 'path': game.get('path', '')} for game in removed_games_list],
            'media_added': media_added,
            'media_removed': media_removed,
            'total_games': len(var_games),
            'total_media': total_media
        }
    except Exception as e:
        return {'success': False, 'error': f'Error comparing gamelist files: {str(e)}'}

def save_gamelist_to_roms(system_name):
    """Copy gamelist from var/gamelists to roms/ directory"""
    gamelist_path = get_gamelist_path(system_name)
    roms_gamelist_path = os.path.join(ROMS_FOLDER, system_name, 'gamelist.xml')
    
    if not os.path.exists(gamelist_path):
        return {'success': False, 'error': f'Gamelist not found in var/gamelists/{system_name}/gamelist.xml'}
    
    try:
        # Ensure the roms directory exists
        os.makedirs(os.path.dirname(roms_gamelist_path), exist_ok=True)
        
        # Create backup of existing roms gamelist if it exists
        if os.path.exists(roms_gamelist_path):
            backup_path = f"{roms_gamelist_path}.backup.{int(time.time())}"
            shutil.copy2(roms_gamelist_path, backup_path)
            print(f"Created backup: {backup_path}")
        
        # Copy the gamelist
        shutil.copy2(gamelist_path, roms_gamelist_path)
        print(f"Copied gamelist from {gamelist_path} to {roms_gamelist_path}")
        
        return {'success': True, 'message': f'Gamelist saved to roms/{system_name}/gamelist.xml'}
    except Exception as e:
        return {'success': False, 'error': f'Error saving gamelist: {str(e)}'}

# Launchbox scraping configuration
LAUNCHBOX_METADATA_PATH = 'var/db/launchbox/Metadata.xml'

# Global variables for scraping
scraping_in_progress = False
scraping_progress = []
scraping_stats = {
    'total_games': 0,
    'processed_games': 0,
    'matched_games': 0,
    'updated_games': 0
}

# Global stop event for tasks
task_stop_event = threading.Event()

# Client tracking for system-specific notifications
client_systems = {}  # {client_sid: system_name}
system_clients = {}  # {system_name: set(client_sids)}
system_clients_lock = threading.Lock()  # Thread safety for system_clients operations

# Single scraping worker process (producer-consumer)
_worker_process = None
_worker_task_queue = None
_worker_result_queue = None
_worker_manager = None
_worker_cancel_map = None  # dict-like shared across processes: {task_id: True}
_igdb_cancel_maps = {}  # dict of {task_id: cancel_map} for IGDB tasks

def _ensure_worker_started():
    """Start the single scraping worker process and the result listener thread."""
    import multiprocessing as _mp
    global _worker_process, _worker_task_queue, _worker_result_queue
    if _worker_process is not None and _worker_process.is_alive():
        return _worker_process
    _worker_task_queue = _mp.Queue()
    _worker_result_queue = _mp.Queue()
    # shared manager for cancellation flags
    try:
        global _worker_manager, _worker_cancel_map
        _worker_manager = _mp.Manager()
        _worker_cancel_map = _worker_manager.dict()
    except Exception:
        _worker_manager = None
        _worker_cancel_map = None
    _worker_process = _mp.Process(target=_scraping_worker_main, args=(_worker_task_queue, _worker_result_queue, _worker_cancel_map))
    _worker_process.daemon = True
    _worker_process.start()
    threading.Thread(target=_scraping_result_listener, args=(_worker_result_queue,), daemon=True).start()
    print(f"✅ Started scraping worker process (PID={_worker_process.pid})")
    return _worker_process

def _scraping_worker_main(task_q, result_q, cancel_map):
    """Worker loop: sequentially process scraping tasks from the queue."""
    try:
        from queue import Empty as _QueueEmpty
    except Exception:
        class _QueueEmpty(Exception):
            pass
    try:
        while True:
            try:
                task = task_q.get(timeout=1.0)
            except _QueueEmpty:
                time.sleep(0.05)
                continue
            if task is None:
                break
            try:
                if task.get('type') != 'scraping':
                    result_q.put({'task_id': task.get('task_id'), 'ok': False, 'error': 'Unsupported task type'})
                    continue
                # stream: the worker subroutine will emit incremental progress via result_q
                r = _run_scraping_task_worker_in_subprocess(task, result_q, cancel_map)
                result_q.put({'task_id': task.get('task_id'), 'ok': r.get('success', False), 'data': r})
            except Exception as e:
                result_q.put({'task_id': task.get('task_id'), 'ok': False, 'error': str(e)})
    except KeyboardInterrupt:
        pass

def _run_scraping_task_worker_in_subprocess(task, result_q, cancel_map):
    """Logic executed inside worker process to perform scraping."""
    system_name = task['system_name']
    selected_games = task.get('selected_games')
    enable_partial_match_modal = task.get('enable_partial_match_modal', False)
    force_download = task.get('force_download', False)
    selected_fields = task.get('selected_fields', None)
    overwrite_text_fields = task.get('overwrite_text_fields', False)

    mapping_config, system_platform_mapping = load_launchbox_config()
    current_system_platform = system_platform_mapping.get(system_name, {}).get('launchbox', 'Arcade')
    
    # Ensure gamelist exists in var/gamelists, copying from roms/ if needed
    gamelist_path = ensure_gamelist_exists(system_name)
    if not os.path.exists(gamelist_path):
        return {'success': False, 'error': f'Gamelist not found at {gamelist_path}'}
    # early cancellation
    if cancel_map and cancel_map.get(task.get('task_id')):
        result_q.put({'type': 'progress', 'task_id': task.get('task_id'), 'message': '🛑 Task stopped by user (before start)'} )
        return {'success': False, 'error': 'Task stopped by user', 'stopped': True}
    all_games = parse_gamelist_xml(gamelist_path)
    if not all_games:
        return {'success': False, 'error': 'No games found in gamelist.xml'}
    # Select games to process without losing the full list used for saving
    games = all_games
    if selected_games and len(selected_games) > 0:
        games = [g for g in all_games if g.get('path') in selected_games]

    stats = {'total_games': len(games), 'processed_games': 0, 'matched_games': 0, 'updated_games': 0}
    # Announce totals and initialize progress bar in main process
    result_q.put({
        'type': 'progress',
        'task_id': task.get('task_id'),
        'message': f"Parsed gamelist.xml, found {len(all_games)} games",
        'current_step': 0,
        'total_steps': len(games),
        'progress_percentage': 0,
        'stats': stats,
    })
    result_q.put({
        'type': 'progress',
        'task_id': task.get('task_id'),
        'message': f"Processing {len(games)} selected game(s)...",
        'current_step': 0,
        'total_steps': len(games),
        'progress_percentage': 0,
        'stats': stats,
    })
    if not os.path.exists(LAUNCHBOX_METADATA_PATH):
        return {'success': False, 'error': 'Metadata.xml not found'}
    
    # Load only platform-specific metadata cache (games + alternate names, no images)
    platform_cache = load_platform_metadata_cache(current_system_platform, mapping_config=mapping_config)
    games_cache = platform_cache['games_cache']
    alternate_names_cache = platform_cache['alternate_names_cache']
    
    if not games_cache:
        return {'success': False, 'error': f'No metadata for platform {current_system_platform}'}
    
    # Convert platform cache to metadata_games format for compatibility
    metadata_games = []
    
    # Get the fields to load from mapping configuration
    fields_to_load = set(['Name', 'Platform', 'DatabaseID'])  # Always load these core fields
    if mapping_config:
        # Add all LaunchBox fields from the mapping configuration
        fields_to_load.update(mapping_config.keys())
    
    for db_id, game_elem in games_cache.items():
        if game_elem is not None:
            game_data = {}
            for child in game_elem:
                tag = child.tag
                text = child.text.strip() if child.text else ''
                if tag in fields_to_load:
                    game_data[tag] = text
            
            # Add alternate names
            alt_names = []
            for alt_elem in alternate_names_cache.get(db_id, []):
                alt_name = alt_elem.find('AlternateName')
                if alt_name is not None and alt_name.text:
                    alt_names.append(alt_name.text.strip())
            game_data['AlternateNames'] = alt_names
            
            metadata_games.append(game_data)

    original_games = all_games.copy()
    matched_rom_paths = []
    for i, game_data in enumerate(games):
        # cooperative cancellation point
        if cancel_map and cancel_map.get(task.get('task_id')):
            # save partial work before exiting
            try:
                result_q.put({'type': 'progress', 'task_id': task.get('task_id'), 'message': 'Saving partial gamelist.xml before stopping...'})
                try:
                    backup_path = f"{gamelist_path}.backup.{int(time.time())}"
                    shutil.copy2(gamelist_path, backup_path)
                except Exception:
                    pass
                write_gamelist_xml(original_games, gamelist_path)
            except Exception as _e:
                result_q.put({'type': 'progress', 'task_id': task.get('task_id'), 'message': f"⚠️  Failed to save partial gamelist: {_e}"})
            result_q.put({'type': 'progress', 'task_id': task.get('task_id'), 'message': f"🛑 Task stopped by user after processing {stats['processed_games']} game(s)"})
            return {'success': False, 'error': 'Task stopped by user', 'stopped': True, 'stats': stats, 'gamelist_path': gamelist_path, 'rom_paths': matched_rom_paths, 'force_download': force_download, 'system_name': system_name}
        result = process_single_game_worker((game_data, metadata_games, current_system_platform, mapping_config, enable_partial_match_modal, i, len(games), platform_cache, selected_fields, overwrite_text_fields))
        stats['processed_games'] += 1
        # compute progress
        try:
            pct = int((stats['processed_games'] / stats['total_games']) * 100) if stats['total_games'] else 0
        except Exception:
            pct = 0
        # stream per game progress
        try:
            game_name = result.get('game_name', 'Unknown')
            status = result.get('status')
            if status == 'matched':
                matched_name = result.get('matched_name', '')
                # Determine match source for logging using match_source directly
                match_source = (result.get('match_source') or 'main').lower()
                try:
                    print(f"DEBUG: Match source for '{game_name}' → '{matched_name}': {match_source}")
                except Exception:
                    pass
                via = 'launchboxid' if match_source == 'launchboxid' else ('alternatename' if match_source == 'alternate' else 'name')
                result_q.put({
                    'type': 'progress',
                    'task_id': task.get('task_id'),
                    'message': f"✓ {game_name} → {matched_name} (perfect via {via})",
                    'current_step': stats['processed_games'],
                    'total_steps': stats['total_games'],
                    'progress_percentage': pct,
                    'stats': stats
                })
            elif status == 'partial_match':
                score = result.get('score', 0.0)
                matched_name = result.get('matched_name', 'Unknown')
                result_q.put({'type': 'progress', 'task_id': task.get('task_id'), 'message': f"⚠ {game_name} → {matched_name} (partial match, score: {score:.2f})", 'current_step': stats['processed_games'], 'total_steps': stats['total_games'], 'progress_percentage': pct, 'stats': stats})
                
                # Send partial match request back to main process via result queue
                if enable_partial_match_modal and result.get('partial_match_request'):
                    partial_match_request = result['partial_match_request'].copy()
                    partial_match_request['system_name'] = system_name
                    partial_match_request['task_id'] = task.get('task_id')
                    result_q.put({
                        'type': 'partial_match_request',
                        'task_id': task.get('task_id'),
                        'partial_match_request': partial_match_request
                    })
                    print(f"DEBUG: Sent partial match request to main process: {game_name} (score: {score:.2f})")
            elif status == 'no_match':
                result_q.put({'type': 'progress', 'task_id': task.get('task_id'), 'message': f"· {game_name} - no match", 'current_step': stats['processed_games'], 'total_steps': stats['total_games'], 'progress_percentage': pct, 'stats': stats})
            elif status == 'skipped':
                result_q.put({'type': 'progress', 'task_id': task.get('task_id'), 'message': f"· {game_name} - skipped", 'current_step': stats['processed_games'], 'total_steps': stats['total_games'], 'progress_percentage': pct, 'stats': stats})
        except Exception:
            pass
        if result['status'] == 'matched':
            stats['matched_games'] += 1
            original_name = result.get('original_name', result['game_name'])
            for j, og in enumerate(original_games):
                # Prefer matching by ROM path if available for reliability
                if result.get('game_path') and og.get('path') == result.get('game_path'):
                    original_games[j] = result['game_data'].copy()
                    stats['updated_games'] += 1
                    break
                if og.get('name') == original_name:
                    original_games[j] = result['game_data'].copy()
                    stats['updated_games'] += 1
                    break
            # collect rom path for image download
            rp = result.get('game_path')
            if rp:
                matched_rom_paths.append(rp)
    # Compute diff of removed games (by ROM path) before saving
    try:
        # Final list that will effectively be written (write_gamelist_xml dedupes by path)
        try:
            final_games_to_write = _dedupe_games_by_path(original_games)
        except Exception:
            final_games_to_write = original_games
        original_paths = set(((g.get('path') or '').strip() for g in all_games if g.get('path')))
        final_paths = set(((g.get('path') or '').strip() for g in final_games_to_write if g.get('path')))
        removed_paths = [p for p in original_paths if p and p not in final_paths]
        # Map for friendly names
        path_to_name = {}
        for g in all_games:
            p = (g.get('path') or '').strip()
            if p and p not in path_to_name:
                path_to_name[p] = g.get('name') or 'Unknown'
        if removed_paths:
            stats['removed_games'] = len(removed_paths)
            preview = removed_paths[:20]
            details_lines = [f"   - {path_to_name.get(p, 'Unknown')} ({p})" for p in preview]
            more = len(removed_paths) - len(preview)
            extra_line = f"   … and {more} more" if more > 0 else ""
            msg = "\n".join([f"🧾 Removed {len(removed_paths)} game(s) from final gamelist", *details_lines] + ([extra_line] if extra_line else []))
            result_q.put({'type': 'progress', 'task_id': task.get('task_id'), 'message': msg, 'current_step': stats['processed_games'], 'total_steps': stats['total_games'], 'progress_percentage': pct, 'stats': stats})
    except Exception:
        pass

    try:
        backup_path = f"{gamelist_path}.backup.{int(time.time())}"
        shutil.copy2(gamelist_path, backup_path)
    except Exception:
        pass
    try:
        write_gamelist_xml(original_games, gamelist_path)
    except Exception as e:
        return {'success': False, 'error': f'Error saving gamelist: {e}'}
    # Final 100% update before finishing
    result_q.put({
        'type': 'progress',
        'task_id': task.get('task_id'),
        'message': "Saving updated gamelist.xml...",
        'current_step': stats['processed_games'],
        'total_steps': stats['total_games'],
        'progress_percentage': 100,
        'stats': stats,
    })
    return {'success': True, 'stats': stats, 'gamelist_path': gamelist_path, 'rom_paths': matched_rom_paths, 'force_download': force_download, 'system_name': system_name}

def _scraping_result_listener(result_q):
    """Receive results from worker and finalize tasks and notify clients."""
    while True:
        try:
            res = result_q.get()
            if res is None:
                break
            # Streamed progress update from worker
            if isinstance(res, dict) and res.get('type') == 'progress':
                msg_task_id = res.get('task_id')
                message = res.get('message', '')
                curr = res.get('current_step')
                total = res.get('total_steps')
                pct = res.get('progress_percentage')
                stats_update = res.get('stats') or {}
                if msg_task_id and msg_task_id in tasks:
                    try:
                        t = tasks[msg_task_id]
                        if t.status == TASK_STATUS_RUNNING:
                            # keep stats in sync for UI counters
                            if stats_update:
                                t.update_stats(stats_update)
                            t.update_progress(message, progress_percentage=pct, current_step=curr, total_steps=total)
                    except Exception:
                        pass
                # Do NOT finalize or advance queue for progress updates
                continue
            
            # Handle partial match requests from worker
            if isinstance(res, dict) and res.get('type') == 'partial_match_request':
                partial_match_request = res.get('partial_match_request')
                if partial_match_request:
                    try:
                        # Add to global partial match queue
                        partial_match_queue.append(partial_match_request)
                        print(f"DEBUG: Added partial match request to queue from worker: {partial_match_request.get('game_name', 'Unknown')}")
                    except Exception as e:
                        print(f"DEBUG: Failed to add partial match request to queue: {e}")
                continue

            # Final result from worker
            task_id = res.get('task_id')
            ok = res.get('ok', False)
            data = res.get('data', {})
            if task_id and task_id in tasks:
                if ok:
                    stats = data.get('stats', {})
                    tasks[task_id].update_stats(stats)
                    tasks[task_id].complete(True)
                    gl = data.get('gamelist_path')
                    if gl:
                        system_name = os.path.basename(os.path.dirname(gl))
                        notify_gamelist_updated(system_name, stats.get('total_games', 0), 0, stats.get('updated_games', 0))
                    # create image download task if any
                    rom_paths = data.get('rom_paths') or []
                    if gl and rom_paths:
                        try:
                            # Get username from the original scraping task
                            original_task = tasks[task_id]
                            username = getattr(original_task, 'username', 'Unknown')
                            
                            add_task_to_queue('image_download', {
                                'system_name': os.path.basename(os.path.dirname(gl)),
                                'data': {
                                    'selected_games': rom_paths,
                                    'force_download': data.get('force_download', False)
                                }
                            }, username=username)
                            tasks[task_id].update_progress(f"🖼️  Image download task created for {len(rom_paths)} matched games")
                        except Exception as _e:
                            print(f"Failed to enqueue image task: {_e}")
                else:
                    # If worker reports a cooperative stop and provided a saved gamelist, still notify and mark as stopped
                    if data.get('stopped') and data.get('gamelist_path'):
                        stats = data.get('stats', {})
                        tasks[task_id].update_stats(stats)
                        gl = data.get('gamelist_path')
                        system_name = os.path.basename(os.path.dirname(gl)) if gl else None
                        if system_name:
                            notify_gamelist_updated(system_name, stats.get('total_games', 0), 0, stats.get('updated_games', 0))
                        # mark as completed (stopped by user) so UI can refresh
                        tasks[task_id].complete(True, "Task stopped by user (partial save)")
                    else:
                        tasks[task_id].complete(False, res.get('error', 'Unknown error'))

            # Now that current task is finalized, advance the queue
            process_next_queued_task()
        except Exception as e:
            print(f"Result listener error: {e}")
            continue

def is_task_stopped():
    """Check if the current task has been stopped by the user"""
    global current_task_id, task_stop_event
    # Check both the global stop event and the task status
    if task_stop_event.is_set():
        return True
    if current_task_id and current_task_id in tasks:
        return tasks[current_task_id].status != TASK_STATUS_RUNNING
    return False

def reset_task_stop_event():
    """Reset the global task stop event"""
    global task_stop_event
    task_stop_event.clear()

def process_single_game_worker(args):
    """Worker function to process a single game in multiprocessing context"""
    try:
        game_data, metadata_games, current_system_platform, mapping_config, enable_partial_match_modal, i, total_games, platform_cache, selected_fields, overwrite_text_fields = args
        
        game_name = game_data.get('name', '')
        if not game_name:
            return {
                'index': i,
                'game_name': 'Unknown',
                'game_path': game_data.get('path', ''),  # Include ROM file path for reliable identification
                'status': 'skipped',
                'reason': 'No name',
                'updated': False,
                'changes': [],
                'best_match': None,
                'score': 0.0,
                'match_type': '',
                'matched_name': '',
                'match_source': '',
                'partial_match_request': None
            }
        
        # CRITICAL: Preserve the original game name before any changes
        # This is needed to find the game in original_games later
        original_game_name = game_name
        
        # Find best match in Launchbox metadata
        existing_launchboxid = game_data.get('launchboxid', '')
        best_match, score = find_best_match(game_name, metadata_games, current_system_platform, existing_launchboxid, platform_cache, mapping_config)
        
        # Generate detailed progress message
        game_name_clean = game_name
        
        if best_match and score >= 1.0:  # Only accept perfect matches (score >= 1.0)
            # Update game data with Launchbox information
            updated = False
            changes = []
            # If the original gamelist name (sans parentheses) exactly matches one of the
            # LaunchBox AlternateNames, treat as alternate-name match ONLY if not a DBID-based match
            try:
                import re as _re
                original_clean = _re.sub(r'\s*\([^)]*\)', '', original_game_name).strip()
                alt_list = best_match.get('AlternateNames', []) or []
                exact_alt = next((a for a in alt_list if a and a.lower() == original_clean.lower()), None)
                # Do not override when the source is launchboxid
                if exact_alt and best_match.get('_match_type') != 'launchboxid':
                    best_match['_match_type'] = 'alternate'
                    # Preserve the exact alt spelling from metadata
                    best_match['_matched_name'] = exact_alt
            except Exception:
                pass
            
            # CRITICAL: Always update launchboxid when we have a perfect match, regardless of match type
            if best_match.get('DatabaseID'):
                old_launchboxid = game_data.get('launchboxid', '')
                new_launchboxid = best_match.get('DatabaseID')
                # Always update launchboxid for perfect matches, even if it's the same value
                # This ensures the field is properly set in the gamelist
                game_data['launchboxid'] = new_launchboxid
                
                # Debug logging for launchboxid updates
                print(f"DEBUG: Worker processing '{game_name_clean}' - Old launchboxid: '{old_launchboxid}', New: '{new_launchboxid}', Match type: {best_match.get('_match_type', 'main')}")
                
                if old_launchboxid != new_launchboxid:
                    updated = True
                    changes.append(f"launchboxid: '{old_launchboxid}' → '{new_launchboxid}'")
                else:
                    # Even if the value is the same, we need to ensure it's properly set
                    # This handles cases where the field might be missing or None
                    if old_launchboxid != new_launchboxid or old_launchboxid == '' or old_launchboxid is None:
                        updated = True
                        changes.append(f"launchboxid: '{old_launchboxid or 'None'}' → '{new_launchboxid}'")
            
            for launchbox_field, gamelist_field in mapping_config.items():
                # Skip field if not in selected fields (except launchboxid which is always processed)
                if selected_fields and launchbox_field not in selected_fields and launchbox_field != 'launchboxid':
                    continue
                    
                if launchbox_field in best_match and best_match[launchbox_field]:
                    old_value = game_data.get(gamelist_field, '')
                    new_value = best_match[launchbox_field]
                    
                    # Special handling for name field: use alternate name directly when matching via alternate name
                    if launchbox_field == 'Name' and gamelist_field == 'name':
                        # Check if this was an alternate name match
                        match_source = best_match.get('_match_type', 'main')
                        if match_source == 'alternate':
                            # Use the exact alternate name that was matched, not the main name
                            alternate_name = best_match.get('_matched_name', old_value)
                            # Preserve original parentheses text when using alternate name
                            import re
                            parentheses_match = re.search(r'\([^)]*\)', old_value)
                            if parentheses_match:
                                parentheses_text = parentheses_match.group(0)
                                # Append parentheses text to alternate name if it's not already there
                                if parentheses_text not in alternate_name:
                                    new_value = f"{alternate_name} {parentheses_text}"
                                else:
                                    new_value = alternate_name
                            else:
                                new_value = alternate_name
                        else:
                            # For main name matches, preserve original parentheses text
                            import re
                            parentheses_match = re.search(r'\([^)]*\)', old_value)
                            if parentheses_match:
                                parentheses_text = parentheses_match.group(0)
                                # Append parentheses text to new name if it's not already there
                                if parentheses_text not in new_value:
                                    new_value = f"{new_value} {parentheses_text}"
                    
                    # Check if we should update this field based on overwrite_text_fields setting
                    should_update = False
                    if overwrite_text_fields:
                        # If overwrite is enabled, always update if values are different
                        should_update = (old_value != new_value)
                    else:
                        # If overwrite is disabled, only update if old value is empty
                        should_update = (old_value == '' or old_value is None) and new_value
                    
                    if should_update:
                        game_data[gamelist_field] = new_value
                        updated = True
                        changes.append(f"{gamelist_field}: '{old_value}' → '{new_value}'")
            
            # Since we only accept perfect matches (score >= 1.0), all matches will be perfect
            match_type = "🎯 PERFECT MATCH"
            score_display = f"{score:.2f}"
            
            # Check if this was an alternate name match
            match_source = best_match.get('_match_type', 'main')
            matched_name = best_match.get('_matched_name', best_match.get('Name', 'Unknown'))
            
            if match_source == 'alternate':
                match_type = "🎯 PERFECT MATCH (via alternate name)"
            elif existing_launchboxid and best_match.get('DatabaseID') == existing_launchboxid:
                match_type = "🎯 PERFECT MATCH (via launchboxid)"
            
            # Download LaunchBox images for this game (regardless of whether other fields were updated)
            if best_match.get('DatabaseID'):
                # Note: Image download is handled separately to avoid multiprocessing issues
                pass
            
            return {
                'index': i,
                'game_name': game_name_clean,
                'original_name': original_game_name,  # CRITICAL: Preserve original name
                'game_path': game_data.get('path', ''),  # Include ROM file path for reliable identification
                'status': 'matched',
                'updated': updated,
                'changes': changes,
                'best_match': best_match,
                'score': score,
                'match_type': match_type,
                'matched_name': matched_name,
                'match_source': match_source,
                'partial_match_request': None,
                'game_data': game_data
            }
        else:
            # Handle partial matches
            if best_match:
                best_match_name = best_match.get('Name', 'Unknown')
                matched_name = best_match.get('_matched_name', best_match_name)
                match_source = best_match.get('_match_type', 'main')
                
                # Build the base message
                if score >= 0.9:
                    match_type = f"✗ Best match: '{matched_name}' (score: {score:.2f} - close but not perfect)"
                elif score >= 0.7:
                    match_type = f"✗ Best match: '{matched_name}' (score: {score:.2f} - partial match)"
                elif score >= 0.5:
                    match_type = f"✗ Best match: '{matched_name}' (score: {score:.2f} - weak match)"
                else:
                    match_type = f"✗ Best match: '{matched_name}' (score: {score:.2f} - no similarity)"
                
                # If partial match modal is enabled, add to queue for user review
                partial_match_request = None
                if enable_partial_match_modal:
                    # Get top matches for the modal instead of just the best match
                    top_matches = get_top_matches(game_name_clean, metadata_games, current_system_platform, top_n=20, mapping_config=mapping_config)
                    partial_match_request = {
                        'game_name': game_name_clean,
                        'game_data': game_data,
                        'top_matches': top_matches,
                        'best_match': best_match,
                        'score': score,
                        'match_source': match_source,
                        'matched_name': matched_name,
                        'system_name': 'unknown'  # Will be set by main process
                    }
                
                return {
                    'index': i,
                    'game_name': game_name_clean,
                    'original_name': original_game_name,  # CRITICAL: Preserve original name
                    'game_path': game_data.get('path', ''),  # Include ROM file path for reliable identification
                    'status': 'partial_match',
                    'updated': False,
                    'changes': [],
                    'best_match': best_match,
                    'score': score,
                    'match_type': match_type,
                    'matched_name': matched_name,
                    'match_source': match_source,
                    'partial_match_request': partial_match_request,
                    'game_data': game_data
                }
            else:
                return {
                    'index': i,
                    'game_name': game_name_clean,
                    'original_name': original_game_name,  # CRITICAL: Preserve original name
                    'game_path': game_data.get('path', ''),  # Include ROM file path for reliable identification
                    'status': 'no_match',
                    'updated': False,
                    'changes': [],
                    'best_match': None,
                    'score': 0.0,
                    'match_type': "✗ No matches found in metadata",
                    'matched_name': '',
                    'match_source': '',
                    'partial_match_request': None,
                    'game_data': game_data
                }
                
    except Exception as e:
        return {
            'index': i,
            'game_name': game_data.get('name', 'Unknown'),
            'original_name': original_game_name,  # CRITICAL: Preserve original name
            'game_path': game_data.get('path', ''),  # Include ROM file path for reliable identification
            'status': 'error',
            'error': str(e),
            'updated': False,
            'changes': [],
            'best_match': None,
            'score': 0.0,
            'match_type': f"✗ Error: {e}",
            'matched_name': '',
            'match_source': '',
            'partial_match_request': None,
            'game_data': game_data
        }


# Task management system with file-based logging
import uuid
import json
from datetime import datetime
import html

def fix_over_escaped_xml_entities(text):
    """Fix over-escaped XML entities like &amp;amp;amp; -> &"""
    if not isinstance(text, str):
        return text
    
    # Keep applying html.unescape until no more changes
    original = text
    while True:
        unescaped = html.unescape(original)
        if unescaped == original:
            break
        original = unescaped
    
    return original

# Task storage and management
tasks = {}  # task_id -> task_info
task_queue = []
current_task_id = None

def load_existing_tasks_from_logs():
    """Load existing tasks from log files on server startup"""
    global tasks
    
    if not os.path.exists(LOGS_DIR):
        return
    
    print(f"🔄 Loading existing tasks from log files in {LOGS_DIR}...")
    
    for filename in os.listdir(LOGS_DIR):
        if filename.endswith('.log'):
            task_id = filename.replace('.log', '')
            
            # Skip if task already exists in memory
            if task_id in tasks:
                continue
            
            log_file_path = os.path.join(LOGS_DIR, filename)
            try:
                # Create a Task object from the log file
                task = Task.__new__(Task)  # Create instance without calling __init__
                task.id = task_id
                task.log_file = log_file_path
                
                # Read the log file to extract task information
                with open(log_file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Parse task type and username from log content
                task.type = 'unknown'
                task.username = 'Unknown'
                for line in content.split('\n'):
                    if line.startswith('Type: '):
                        task.type = line.replace('Type: ', '').strip()
                    elif line.startswith('User: '):
                        task.username = line.replace('User: ', '').strip()
                # Parse task data (including system_name) from header
                try:
                    for line in content.split('\n'):
                        if line.startswith('Data: '):
                            data_str = line.replace('Data: ', '').strip()
                            task.data = json.loads(data_str) if data_str and data_str != 'None' else {}
                            break
                except Exception:
                    task.data = {}
                
                # Parse start time from log content
                task.start_time = None
                for line in content.split('\n'):
                    if line.startswith('Task started: '):
                        try:
                            start_str = line.replace('Task started: ', '').strip()
                            task.start_time = datetime.fromisoformat(start_str).timestamp()
                        except:
                            pass
                        break
                
                # Parse end time and status from log content
                task.end_time = None
                task.status = TASK_STATUS_IDLE
                task.error_message = None
                
                for line in content.split('\n'):
                    if line.startswith('Task ended: '):
                        try:
                            end_str = line.replace('Task ended: ', '').strip()
                            task.end_time = datetime.fromisoformat(end_str).timestamp()
                        except:
                            pass
                    elif line.startswith('Task stopped: '):
                        try:
                            end_str = line.replace('Task stopped: ', '').strip()
                            task.end_time = datetime.fromisoformat(end_str).timestamp()
                            task.status = TASK_STATUS_ERROR
                            task.error_message = "Task stopped by user"
                        except:
                            pass
                    elif line.startswith('Status: '):
                        status_str = line.replace('Status: ', '').strip()
                        if status_str in [TASK_STATUS_COMPLETED, TASK_STATUS_ERROR, TASK_STATUS_STOPPED, TASK_STATUS_IDLE]:
                            task.status = status_str
                        elif 'stopped' in status_str.lower():
                            task.status = TASK_STATUS_STOPPED
                        elif 'completed' in status_str.lower():
                            task.status = TASK_STATUS_COMPLETED
                
                # Parse progress data from JSON lines in log file
                task.progress = []
                task.stats = {}
                task.progress_percentage = 0
                task.total_steps = 0
                task.current_step = 0
                task.data = task.data or {}
                
                # Parse final task data from log file
                try:
                    with open(log_file_path, 'r', encoding='utf-8') as f:
                        for line in f:
                            line = line.strip()
                            if line.startswith('Final Status: '):
                                task.status = line.replace('Final Status: ', '').strip()
                            elif line.startswith('Progress: '):
                                progress_str = line.replace('Progress: ', '').replace('%', '').strip()
                                try:
                                    task.progress_percentage = int(progress_str)
                                except ValueError:
                                    pass
                            elif line.startswith('Current Step: '):
                                try:
                                    task.current_step = int(line.replace('Current Step: ', '').strip())
                                except ValueError:
                                    pass
                            elif line.startswith('Total Steps: '):
                                try:
                                    task.total_steps = int(line.replace('Total Steps: ', '').strip())
                                except ValueError:
                                    pass
                            elif line.startswith('System: '):
                                system_name = line.replace('System: ', '').strip()
                                if system_name != 'N/A':
                                    task.data['system_name'] = system_name
                            elif line.startswith('User: '):
                                task.username = line.replace('User: ', '').strip()
                            elif line.startswith('Stats: '):
                                stats_str = line.replace('Stats: ', '').strip()
                                try:
                                    task.stats = json.loads(stats_str)
                                except Exception:
                                    pass
                except Exception:
                    pass
                
                # Calculate duration if both times are available
                if task.start_time and task.end_time:
                    task.duration = task.end_time - task.start_time
                else:
                    task.duration = 0
                
                # Add to tasks dictionary
                tasks[task_id] = task
                print(f"  ✅ Loaded task {task_id} ({task.type}) - {task.status}")
                
            except Exception as e:
                print(f"  ❌ Error loading task {task_id}: {e}")
    
    print(f"✅ Loaded {len(tasks)} existing tasks from log files")

# Task status constants
TASK_STATUS_IDLE = 'idle'
TASK_STATUS_RUNNING = 'running'
TASK_STATUS_COMPLETED = 'completed'
TASK_STATUS_ERROR = 'error'
TASK_STATUS_STOPPED = 'stopped'
TASK_STATUS_QUEUED = 'queued'

# Logs directory
LOGS_DIR = 'var/task_logs'
os.makedirs(LOGS_DIR, exist_ok=True)

class Task:
    def __init__(self, task_type, task_data=None, username=None):
        self.id = str(uuid.uuid4())
        self.type = task_type
        self.status = TASK_STATUS_IDLE
        self.progress = []
        self.stats = {}
        self.start_time = None
        self.end_time = None
        self.error_message = None
        self.data = task_data or {}
        self.username = username or 'Unknown'
        self.progress_percentage = 0
        self.total_steps = 0
        self.current_step = 0
        self.grid_refresh_needed = False
        self.log_file = os.path.join(LOGS_DIR, f"{self.id}.log")

        
        # Initialize log file
        with open(self.log_file, 'w') as f:
            f.write(f"Task started: {datetime.now().isoformat()}\n")
            f.write(f"Type: {task_type}\n")
            f.write(f"User: {self.username}\n")
            f.write(f"Data: {json.dumps(task_data, indent=2) if task_data else 'None'}\n")
            f.write("-" * 80 + "\n\n")



    
    def update_progress(self, message, progress_percentage=None, current_step=None, total_steps=None):
        """Update task progress and write to log file"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        log_entry = f"[{timestamp}] {message}"
        
        self.progress.append(log_entry)
        
        # Update progress tracking
        if progress_percentage is not None:
            self.progress_percentage = progress_percentage
        if current_step is not None:
            self.current_step = current_step
        if total_steps is not None:
            self.total_steps = total_steps
        
        # Write to log file
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(log_entry + '\n')
                    
        except Exception as e:
            print(f"Error writing to log file {self.log_file}: {e}")

        
        # Keep only last 1000 messages in memory
        if len(self.progress) > 1000:
            self.progress = self.progress[-1000:]
    
    def update_stats(self, stats):
        """Update task statistics"""
        self.stats.update(stats)
    
    def start(self):
        """Start the task"""
        global task_stop_event
        # Reset the global stop event when starting a new task
        task_stop_event.clear()
        self.status = TASK_STATUS_RUNNING
        self.start_time = time.time()
        # Prune old tasks (keep last 30)
        try:
            cleanup_old_tasks(max_tasks=30)
        except Exception as e:
            print(f"Task cleanup error: {e}")
        self.update_progress("Task started")
    
    def stop(self):
        """Stop the task"""
        self.status = TASK_STATUS_STOPPED
        self.end_time = time.time()
        self.error_message = "Task stopped by user"
        self.update_progress("Task stopped by user")
        
        # Write final status to log file
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(f"\nTask stopped: {datetime.now().isoformat()}\n")
                f.write(f"Status: {self.status}\n")
                f.write(f"Duration: {self.end_time - self.start_time:.2f} seconds\n")
        except Exception as e:
            print(f"Error writing final status to log file {self.log_file}: {e}")

    
    def complete(self, success=True, error_message=None):
        """Complete the task"""
        self.end_time = time.time()
        if success:
            self.status = TASK_STATUS_COMPLETED
            self.progress_percentage = 100
            self.update_progress("Task completed successfully")
        else:
            self.status = TASK_STATUS_ERROR
            self.error_message = error_message
            self.update_progress(f"Task failed: {error_message}")
        
        # Write final status to log file
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(f"\nTask ended: {datetime.now().isoformat()}\n")
                f.write(f"Status: {self.status}\n")
                f.write(f"Duration: {self.end_time - self.start_time:.2f} seconds\n")
                
                # Write final task data for persistence
                f.write(f"Final Status: {self.status}\n")
                f.write(f"Progress: {self.progress_percentage}%\n")
                f.write(f"Current Step: {self.current_step}\n")
                f.write(f"Total Steps: {self.total_steps}\n")
                f.write(f"System: {self.data.get('system_name') if self.data else 'N/A'}\n")
                f.write(f"User: {self.username}\n")
                f.write(f"Stats: {json.dumps(self.stats)}\n")
                
        except Exception as e:
            print(f"Error writing final status to log file {self.log_file}: {e}")
        
        # Mark that grid refresh is needed for this task type
        if self.type in ['scraping', 'media_scan', 'image_download', 'youtube_download', 'rom_scan', '2d_box_generation']:
            self.grid_refresh_needed = True

    
    def to_dict(self):
        """Convert task to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'type': self.type,
            'status': self.status,
            'progress': self.progress,
            'stats': self.stats,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'error_message': self.error_message,
            'data': self.data,
            'username': self.username,
            'progress_percentage': self.progress_percentage,
            'total_steps': self.total_steps,
            'current_step': self.current_step,
            'grid_refresh_needed': getattr(self, 'grid_refresh_needed', False),
            'duration': self.end_time - self.start_time if self.end_time and self.start_time else None
        }

def create_task(task_type, task_data=None):
    """Create a new task"""
    # Get current user from Flask-Login
    username = 'Unknown'
    try:
        from flask_login import current_user
        if current_user and current_user.is_authenticated:
            username = current_user.username
    except Exception:
        pass
    
    task = Task(task_type, task_data, username)
    tasks[task.id] = task
    return task

def get_task(task_id):
    """Get a task by ID"""
    return tasks.get(task_id)

def get_all_tasks():
    """Get all tasks"""
    return {task_id: task.to_dict() for task_id, task in tasks.items()}

def get_task_log(task_id):
    """Get the log content for a specific task"""
    task = get_task(task_id)
    if not task:
        return None
    
    try:
        with open(task.log_file, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"Error reading log file: {e}"

def get_task_log_file_path(task_id):
    """Get the log file path for a specific task"""
    task = get_task(task_id)
    if not task:
        return None
    return task.log_file

def cleanup_old_tasks(max_tasks=100):
    """Clean up old completed/error tasks to prevent memory bloat"""
    if len(tasks) <= max_tasks:
        return
    
    # Sort tasks by start time (oldest first)
    sorted_tasks = sorted(tasks.items(), key=lambda x: x[1].start_time or 0)
    
    # Remove oldest completed/error tasks
    for task_id, task in sorted_tasks:
        if task.status in [TASK_STATUS_COMPLETED, TASK_STATUS_ERROR, TASK_STATUS_STOPPED] and len(tasks) > max_tasks:
            # Remove log file
            try:
                if os.path.exists(task.log_file):
                    os.remove(task.log_file)
            except Exception as e:
                print(f"Error removing log file {task.log_file}: {e}")
            
            # Remove from tasks dict
            del tasks[task_id]

def is_task_running():
    """Check if any task is currently running"""
    global current_task_id
    if current_task_id and current_task_id in tasks:
        return tasks[current_task_id].status == TASK_STATUS_RUNNING
    return False

def can_start_task(task_type):
    """Check if a new task can be started"""
    if is_task_running():
        current_task_type = tasks[current_task_id].type if current_task_id else 'unknown'
        return False, f"Another task ({current_task_type}) is already running"
    return True, None

def queue_task(task_type, task_data=None):
    """Add a task to the queue if it can't start immediately"""
    if can_start_task(task_type)[0]:
        return True, "Task can start immediately"
    
    # Create a queued task
    task = create_task(task_type, task_data)
    task.status = TASK_STATUS_QUEUED
    
    # Add to queue
    task_info = {
        'task_id': task.id,
        'type': task_type,
        'data': task_data,
        'timestamp': time.time()
    }
    task_queue.append(task_info)
    return False, f"Task queued. Position: {len(task_queue)}"

def get_queue_status():
    """Get current queue status"""
    global current_task_id
    current_task = tasks.get(current_task_id) if current_task_id else None
    
    return {
        'current_task': current_task.to_dict() if current_task else None,
        'queue_length': len(task_queue),
        'queued_tasks': task_queue
    }

def update_task_progress(message, progress_percentage=None, current_step=None, total_steps=None):
    """Update the current task progress and keep it synchronized"""
    global current_task_id
    if current_task_id and current_task_id in tasks:
        task = tasks[current_task_id]
        if task.status == TASK_STATUS_RUNNING:
            task.update_progress(message, progress_percentage, current_step, total_steps)
            # Add console logging for debugging
            print(f"DEBUG: {message}")

def update_task_stats():
    """Update the current task stats to keep them synchronized"""
    global current_task_id, scraping_stats
    if current_task_id and current_task_id in tasks:
        task = tasks[current_task_id]
        if task.status == TASK_STATUS_RUNNING:
            task.update_stats(scraping_stats.copy())



def cleanup_stuck_tasks():
    """Clean up tasks that are stuck in idle status for too long"""
    global tasks, current_task_id
    
    current_time = time.time()
    stuck_tasks = []
    
    for task_id, task in list(tasks.items()):
        # If task has been idle for more than 5 minutes, mark it as completed
        if (task.status == TASK_STATUS_IDLE and 
            task.start_time and 
            current_time - task.start_time > 300):  # 5 minutes
            
            print(f"Cleaning up stuck idle task: {task_id} (type: {task.type})")
            task.complete(success=False, error_message="Task stuck in idle state - cleaned up")
            stuck_tasks.append(task_id)
    
    if stuck_tasks:
        print(f"Cleaned up {len(stuck_tasks)} stuck tasks")
    
    return stuck_tasks

def add_task_to_queue(task_type, task_data, username=None):
    """Add a task to the queue for later processing"""
    global task_queue
    
    # Create a queued task with specific username if provided
    if username:
        task = Task(task_type, task_data, username)
        tasks[task.id] = task
    else:
        task = create_task(task_type, task_data)
    task.status = TASK_STATUS_QUEUED
    
    # Add to queue
    task_info = {
        'task_id': task.id,
        'type': task_type,
        'data': task_data,
        'timestamp': time.time()
    }
    task_queue.append(task_info)
    print(f"DEBUG: Added {task_type} task to queue. Position: {len(task_queue)}")
    
    # Process the next queued task immediately
    process_next_queued_task()
    
    return task

def process_next_queued_task():
    """Process the next task in the queue"""
    global current_task_id, task_queue
    
    # Clean up any stuck tasks first
    cleanup_stuck_tasks()
    
    if not task_queue:
        return
    
    next_task = task_queue.pop(0)
    task_type = next_task['type']
    task_data = next_task.get('data', {})
    
    print(f"DEBUG: Processing next queued task: {task_type}")
    
    # Start the next task based on its type
    if task_type == 'media_scan':
        # Start media scan task
        system_name = task_data.get('system_name')
        if system_name:
            # Use the existing queued task instead of creating a new one
            task_id = next_task.get('task_id')
            if task_id and task_id in tasks:
                task = tasks[task_id]
                current_task_id = task.id
                task.start()
            else:
                # Fallback: create new task if existing one not found
                task = create_task('media_scan', task_data)
                current_task_id = task.id
                task.start()
            # Start media scan in background thread
            thread = threading.Thread(target=run_media_scan_task, args=(system_name,))
            thread.daemon = True
            thread.start()
    elif task_type == 'image_download':
        # Start image download task
        system_name = task_data.get('system_name')
        data = task_data.get('data', {})
        if system_name:
            # Use the existing queued task instead of creating a new one
            task_id = next_task.get('task_id')
            if task_id and task_id in tasks:
                task = tasks[task_id]
                current_task_id = task.id
                task.start()
            else:
                # Fallback: create new task if existing one not found
                task = create_task('image_download', task_data)
                current_task_id = task.id
                task.start()
            # Start image download in background thread
            thread = threading.Thread(target=run_image_download_task, args=(system_name, data))
            thread.daemon = True
            thread.start()
    elif task_type == 'scraping':
        # Start scraping task via single worker process (sequential)
        system_name = task_data.get('system_name')
        method = task_data.get('method', 'GET')
        data = task_data.get('data', {})
        if system_name:
            # Use the existing queued task instead of creating a new one
            task_id = next_task.get('task_id')
            if task_id and task_id in tasks:
                task = tasks[task_id]
                current_task_id = task.id
                task.start()
            else:
                # Fallback: create new task if existing one not found
                task = create_task('scraping', task_data)
                current_task_id = task.id
                task.start()
            # Ensure worker is running and enqueue the task
            _ensure_worker_started()
            # Build payload for worker
            payload = {
                'type': 'scraping',
                'task_id': task.id,
                'system_name': system_name,
                'selected_games': (data.get('selected_games') if data else None),
                'enable_partial_match_modal': (data.get('enable_partial_match_modal', False) if data else False),
                'force_download': (data.get('force_download', False) if data else False),
                'selected_fields': (data.get('selected_fields') if data else None),
                'overwrite_text_fields': (data.get('overwrite_text_fields', False) if data else False),
            }
            _worker_task_queue.put(payload)
    elif task_type == 'rom_scan':
        # Start ROM scan task
        system_name = task_data.get('system_name')
        if system_name:
            # Use the existing queued task instead of creating a new one
            task_id = next_task.get('task_id')
            if task_id and task_id in tasks:
                task = tasks[task_id]
                current_task_id = task.id
                task.start()
            else:
                # Fallback: create new task if existing one not found
                task = create_task('rom_scan', task_data)
                current_task_id = task.id
                task.start()
            # Start ROM scan in background thread
            thread = threading.Thread(target=run_rom_scan_task, args=(system_name,))
            thread.daemon = True
            thread.start()
    elif task_type == 'youtube_download':
        # Start YouTube download task
        data = task_data.get('data', {})
        if data:
            # Use the existing queued task instead of creating a new one
            task_id = next_task.get('task_id')
            if task_id and task_id in tasks:
                task = tasks[task_id]
                current_task_id = task.id
                task.start()
            else:
                # Fallback: create new task if existing one not found
                task = create_task('youtube_download', task_data)
                current_task_id = task.id
                task.start()
            # Start YouTube download in background thread
            thread = threading.Thread(target=run_youtube_download_task, args=(data,))
            thread.daemon = True
            thread.start()
    elif task_type == '2d_box_generation':
        # Start 2D box generation task
        system_name = task_data.get('system_name')
        selected_games = task_data.get('selected_games', [])
        if system_name and selected_games:
            # Use the existing queued task instead of creating a new one
            task_id = next_task.get('task_id')
            if task_id and task_id in tasks:
                task = tasks[task_id]
                current_task_id = task.id
                task.start()
            else:
                # Fallback: create new task if existing one not found
                task = create_task('2d_box_generation', task_data)
                current_task_id = task.id
                task.start()
            # Start 2D box generation in background thread
            thread = threading.Thread(target=run_2d_box_generation_task, args=(system_name, selected_games))
            thread.daemon = True
            thread.start()
    else:
        print(f"Unknown task type: {task_type}")
        return

def run_media_scan_task(system_name):
    """Run media scan task in background thread"""
    global current_task_id
    
    try:
        if not current_task_id or current_task_id not in tasks:
            print("Error: No active task found")
            return
        
        task = tasks[current_task_id]
        
        # Run the media scan
        result = scan_media_files(system_name)
        
        # Mark task as completed
        task.complete(True)
        
        # Process next task in queue if any
        process_next_queued_task()
        
    except Exception as e:
        if current_task_id and current_task_id in tasks:
            tasks[current_task_id].complete(False, str(e))
        print(f"Error in media scan task: {e}")

def run_image_download_task(system_name, data):
    """Run image download task in background thread"""
    global current_task_id
    
    try:
        if not current_task_id or current_task_id not in tasks:
            print("Error: No active task found")
            return
        
        task = tasks[current_task_id]
        
        # Extract parameters from data
        game_name = data.get('game_name') if data else None
        selected_games = data.get('selected_games') if data else None
        force_download = data.get('force_download', False) if data else False
        selected_fields = data.get('selected_fields', None) if data else None
        
        # Load gamelist
        gamelist_path = ensure_gamelist_exists(system_name)
        if not os.path.exists(gamelist_path):
            task.complete(False, 'Gamelist not found')
            return
        
        games = parse_gamelist_xml(gamelist_path)
        if not games:
            task.complete(False, 'No games found in gamelist')
            return
        
        # Filter games based on parameters
        games_to_process = games
        if selected_games and len(selected_games) > 0:
            # Filter to only selected games by ROM file path (more reliable than game names)
            games_to_process = [g for g in games if g.get('path') in selected_games]
            if not games_to_process:
                task.complete(False, f'None of the selected ROM files found in gamelist')
                return
            task.update_progress(f"🎯 Processing {len(games_to_process)} selected games out of {len(games)} total games")
        elif game_name:
            # Filter to single game if specified (legacy support)
            games_to_process = [g for g in games if g.get('name') == game_name]
            if not games_to_process:
                task.complete(False, f'Game "{game_name}" not found')
                return
            task.update_progress(f"🎯 Processing single game: {game_name}")
        else:
            # Process all games if no selection specified
            task.update_progress(f"🎯 Processing all {len(games)} games")
        
        # Load image mappings
        image_config = load_image_mappings()
        if not image_config:
            task.complete(False, 'Failed to load image mappings')
            return
        
        # Load metadata cache once at the beginning of the task
        task.update_progress(f"📚 Loading metadata cache...")
        load_metadata_cache()
        task.update_progress(f"✅ Metadata cache loaded successfully")
        
        # Load media config once at the beginning of the task
        task.update_progress(f"📁 Loading media config...")
        media_config = load_media_config()
        if not media_config:
            task.complete(False, 'Failed to load media config')
            return
        task.update_progress(f"✅ Media config loaded successfully")
        
        # Load region config once at the beginning of the task
        task.update_progress(f"🌍 Loading region config...")
        region_config = load_region_config()
        task.update_progress(f"✅ Region config loaded successfully")
        
        
        system_path = os.path.join(ROMS_FOLDER, system_name)
        results = []
        
        # Set total steps for progress tracking
        task.total_steps = len(games_to_process)
        task.current_step = 0
        
        # Start timing for overall download process
        overall_start_time = time.time()
        task.update_progress(f"⏱️  Starting bulk image download for {len(games_to_process)} games")
        
        # Prepare game processing tasks for parallel execution
        game_tasks = []
        skipped_count = 0
        
        for i, game in enumerate(games_to_process):
            # Check if task has been stopped during preparation
            if task.status != TASK_STATUS_RUNNING:
                task.update_progress(f"🛑 Task stopped by user during preparation")
                break
                
            game_name = game.get('name', 'Unknown')
            launchbox_id = game.get('launchboxid', '')
            
            if not launchbox_id:
                skipped_count += 1
                current_step = i + 1
                progress_percent = int((current_step / len(games_to_process)) * 100)
                task.update_progress(f"⏭️  Skipping {game_name} - no launchboxid", progress_percentage=progress_percent, current_step=current_step)
                results.append({
                    'game': game_name,
                    'status': 'skipped',
                    'reason': 'No launchboxid found'
                })
                continue
            
            # EARLY OPTIMIZATION: Check if any fields need downloads before starting
            if not force_download:
                # Check which fields need images based on current gamelist data
                fields_to_download = []
                for field_name in image_config.get('image_type_mappings', {}).values():
                    current_value = game.get(field_name)
                    # Consider field empty if it's None, empty string, or just whitespace
                    if not current_value or (isinstance(current_value, str) and current_value.strip() == ''):
                        fields_to_download.append(field_name)
                
                if not fields_to_download:
                    skipped_count += 1
                    current_step = i + 1
                    progress_percent = int((current_step / len(games_to_process)) * 100)
                    task.update_progress(f"⏭️  Skipping {game_name} - all media fields already populated", progress_percentage=progress_percent, current_step=current_step)
                    results.append({
                        'game': game_name,
                        'status': 'skipped',
                        'reason': 'All media fields already populated'
                    })
                    continue
            
            # Add game task to the list
            game_tasks.append({
                'index': i,
                'game': game,
                'game_name': game_name,
                'launchbox_id': launchbox_id,
                'force_download': force_download,
                'image_config': image_config,
                'media_config': media_config,
                'region_config': region_config,
                'selected_fields': selected_fields
            })
        
        # Execute game processing in parallel
        task.update_progress(f"🚀 Starting parallel processing of {len(game_tasks)} games...", progress_percentage=0)
        
        from concurrent.futures import ThreadPoolExecutor, as_completed
        import threading
        
        # Use a thread-safe way to update progress and counters
        progress_lock = threading.Lock()
        results_lock = threading.Lock()
        counters = {'downloaded': 0, 'failed': 0, 'early_skipped': 0}
        
        def process_single_game(task_data):
            """Process a single game with image downloads"""
            i = task_data['index']
            game = task_data['game']
            game_name = task_data['game_name']
            launchbox_id = task_data['launchbox_id']
            force_download = task_data['force_download']
            image_config = task_data['image_config']
            media_config = task_data['media_config']
            region_config = task_data['region_config']
            selected_fields = task_data['selected_fields']
            
            # Check if task has been stopped before processing
            if task.status != TASK_STATUS_RUNNING:
                return {
                    'game': game_name,
                    'status': 'stopped',
                    'reason': 'Task stopped by user'
                }
            
            # Calculate and show progress percentage for each game
            progress_percent = int((i / len(games_to_process)) * 100)
            with progress_lock:
                task.update_progress(f"📊 Progress: {progress_percent}% ({i+1}/{len(games_to_process)})", progress_percentage=progress_percent, current_step=i+1)
            
            try:
                # Start timing for this specific game
                game_start_time = time.time()
                
                
                

                
                # Get ROM filename from game data
                rom_filename = os.path.splitext(os.path.basename(game.get('path', '')))[0]
                if not rom_filename:
                    rom_filename = os.path.splitext(game.get('name', ''))[0]
             
                downloaded_images = get_game_images_from_launchbox(launchbox_id, image_config, system_path, rom_filename, game_name=game_name, current_game_data=game, force_download=force_download, media_config=media_config, region_config=region_config, selected_fields=selected_fields)
                
                
                if downloaded_images:
                    # Count downloaded images (no need to track changes, will scan files at end)
                    updated_fields = []
                    
                    for img in downloaded_images:
                        current_value = game.get(img['field'])
                        if force_download or not current_value:  # Update if force download or field is empty
                            updated_fields.append(img['field'])
                    
                    if updated_fields:
                        with results_lock:
                            counters['downloaded'] += len(updated_fields)
                        
                        return {
                            'game': game_name,
                            'status': 'success',
                            'downloaded': len(updated_fields),
                            'images': updated_fields
                        }
                    else:
                        
                        return {
                            'game': game_name,
                            'status': 'skipped',
                            'reason': 'All fields already populated and force download disabled'
                        }
                else:
                    
                    return {
                        'game': game_name,
                        'status': 'no_images',
                        'reason': 'No images available or download failed'
                    }
                    
            except Exception as e:
                with results_lock:
                    counters['failed'] += 1
                with progress_lock:
                    task.update_progress(f"❌ Error processing {game_name}: {e}")
                
                return {
                    'game': game_name,
                    'status': 'error',
                    'error': str(e)
                }
        
        # Check if task has been stopped before starting ThreadPoolExecutor
        if task.status != TASK_STATUS_RUNNING:
            task.update_progress(f"🛑 Task stopped by user before starting downloads")
            return
        
        # Execute game processing with ThreadPoolExecutor
        max_game_workers = min(20, len(game_tasks))  # Limit concurrent games to avoid overwhelming the system
        task.update_progress(f"🔧 Using {max_game_workers} parallel game processors")
        
        with ThreadPoolExecutor(max_workers=max_game_workers) as executor:
            # Submit all game processing tasks
            future_to_game = {executor.submit(process_single_game, task_data): task_data for task_data in game_tasks}
            
            # Process completed games as they finish
            for future in as_completed(future_to_game):
                # Check if task has been stopped
                if task.status != TASK_STATUS_RUNNING:
                    task.update_progress(f"🛑 Task stopped by user - cancelling remaining downloads")
                    # Cancel all remaining futures that haven't started yet
                    for f, task_data in future_to_game.items():
                        if not f.done():
                            f.cancel()
                    
                    # Stop the download manager to cancel active downloads
                    try:
                        from download_manager import get_download_manager
                        download_manager = get_download_manager()
                        if download_manager:
                            task.update_progress(f"🛑 Stopping download manager to cancel active downloads")
                            download_manager.stop()
                    except Exception as e:
                        task.update_progress(f"⚠️  Warning: Could not stop download manager: {e}")
                    
                    break
                
                result = future.result()
                if result:
                    results.append(result)
        
        # CRITICAL: Wait for ALL downloads to complete before scanning media files
        # The download manager is shared across all parallel tasks, so we need to ensure
        # all downloads are truly finished before scanning the file system
        task.update_progress(f"⏳ Waiting for all downloads to complete...", progress_percentage=85, current_step=len(games_to_process))
        
        try:
            from download_manager import get_download_manager
            download_manager = get_download_manager()
            if download_manager and download_manager.is_running:
                # Wait for all pending downloads to complete
                task.update_progress(f"⏳ Ensuring all downloads are finished...", progress_percentage=87, current_step=len(games_to_process))
                
                # Give a small delay to ensure all async operations complete
                time.sleep(2)
                
                # Check if download manager is still processing
                if hasattr(download_manager, 'active_tasks') and download_manager.active_tasks:
                    task.update_progress(f"⏳ Waiting for {len(download_manager.active_tasks)} active downloads...", progress_percentage=88, current_step=len(games_to_process))
                    # Wait a bit more for active tasks to complete
                    time.sleep(3)
                
                print(f"DEBUG: Download manager status - running: {download_manager.is_running}, active_tasks: {len(getattr(download_manager, 'active_tasks', []))}")
        except Exception as e:
            print(f"DEBUG: Error checking download manager status: {e}")
            task.update_progress(f"⚠️  Warning: Could not verify download completion: {e}")
        
        # After all downloads complete, scan media files and update gamelist.xml
        print(f"DEBUG: Download counters - downloaded: {counters['downloaded']}, failed: {counters['failed']}, early_skipped: {counters['early_skipped']}")
        
        # Always run media scan to ensure gamelist is up to date with actual files
        try:
            task.update_progress(f"🔍 Scanning media files to update gamelist.xml...", progress_percentage=90, current_step=len(games_to_process))
            
            # Use the existing media scan logic to populate gamelist based on actual files
            print(f"DEBUG: Starting media scan to update gamelist after processing {len(results)} games")
            
            # Get media config for mappings
            media_config = load_media_config()
            if not media_config:
                task.update_progress(f"❌ Failed to load media config for scan")
                return
            
            media_mappings = media_config.get('mappings', {})
            updated_games = 0
            
            # Scan each game's media files
            for game in games:
                game_updated = False
                rom_path = game.get('path', '')
                if not rom_path:
                    continue
                
                # Get ROM filename without extension
                rom_filename = os.path.splitext(os.path.basename(rom_path))[0]
                if not rom_filename:
                    continue
                
                # Check each media type
                for media_type, gamelist_field in media_mappings.items():
                    if media_type in ['videos', 'manuals']:  # Skip non-image types
                        continue
                        
                    # Get media directory for this type
                    media_dir = os.path.join(system_path, 'media', media_type)
                    if not os.path.exists(media_dir):
                        continue
                    
                    # Look for media files matching the ROM filename
                    extensions = media_config.get('extensions', {}).get(media_type, ['.png', '.jpg', '.jpeg'])
                    found_file = None
                    
                    for ext in extensions:
                        potential_file = os.path.join(media_dir, f"{rom_filename}{ext}")
                        if os.path.exists(potential_file):
                            found_file = f"./media/{media_type}/{os.path.basename(potential_file)}"
                            break
                    
                    # Update gamelist field if file exists
                    if found_file:
                        current_value = game.get(gamelist_field, '')
                        if current_value != found_file:
                            game[gamelist_field] = found_file
                            game_updated = True
                            print(f"DEBUG: Updated {game.get('name', 'Unknown')} - {gamelist_field}: {found_file}")
                
                if game_updated:
                    updated_games += 1
            
            # Save the updated gamelist
            print(f"DEBUG: Saving gamelist with {updated_games} updated games")
            write_gamelist_xml(games, gamelist_path)
            print(f"DEBUG: Gamelist saved successfully")
            task.update_progress(f"💾 Gamelist updated with {updated_games} games", progress_percentage=95, current_step=len(games_to_process))
            
        except Exception as e:
            print(f"DEBUG: Failed to scan media files and update gamelist: {e}")
            import traceback
            traceback.print_exc()
            task.update_progress(f"❌ Failed to update gamelist: {e}", progress_percentage=95, current_step=len(games_to_process))
        
        # Calculate overall time
        overall_total_time = time.time() - overall_start_time
        
        
        # Show detailed results for each game
        if results:
            task.update_progress(f"📋 === DETAILED RESULTS ===")
            for i, result in enumerate(results, 1):
                game_name = result.get('game', 'Unknown')
                status = result.get('status', 'unknown')
                
                # Update progress percentage based on completed games
                completed_progress = int((i / len(results)) * 100)
                
                if status == 'success':
                    downloaded = result.get('downloaded', 0)
                    images = result.get('images', [])
                    task.update_progress(f"   {i}. {game_name}: ✅ Downloaded {downloaded} images", progress_percentage=completed_progress, current_step=i)
                elif status == 'early_skipped':
                    reason = result.get('reason', 'Unknown reason')
                    saved_time = result.get('saved_time', 0)
                    task.update_progress(f"   {i}. {game_name}: 🚀 Early-skipped - {reason} (saved {saved_time:.2f}s)", progress_percentage=completed_progress, current_step=i)
                elif status == 'skipped':
                    reason = result.get('reason', 'Unknown reason')
                    task.update_progress(f"   {i}. {game_name}: ⏭️  Skipped - {reason}", progress_percentage=completed_progress, current_step=i)
                elif status == 'error':
                    error = result.get('error', 'Unknown error')
                    task.update_progress(f"   {i}. {game_name}: ❌ Error - {error}", progress_percentage=completed_progress, current_step=i)
                elif status == 'no_images':
                    reason = result.get('reason', 'No images available')
                    task.update_progress(f"   {i}. {game_name}: ⚠️  {reason}", progress_percentage=completed_progress, current_step=i)
        
        # Complete task
        task.complete(True)
        
        # Process next task in queue if any
        process_next_queued_task()
        
    except Exception as e:
        if current_task_id and current_task_id in tasks:
            tasks[current_task_id].complete(False, str(e))
        print(f"Error in image download task: {e}")

# Partial match modal queue for scraping
partial_match_queue = []

# Platform-specific metadata cache
platform_metadata_cache = {}
current_system_platform = None

# Global metadata cache for faster lookups (consolidated per DatabaseID)
# global_metadata_cache[DatabaseID] = {
#   'game': <Game element>,
#   'images': [<GameImage elements>],
#   'alternate_names': [<GameAlternateName elements>]
# }
global_metadata_cache = {}
global_metadata_cache_loaded = False

def load_metadata_cache():
    """Load and cache all metadata from Metadata.xml for faster lookups"""
    global global_metadata_cache, global_metadata_cache_loaded
    
    if global_metadata_cache_loaded:
        # Return a derived view for any legacy callers
        return {
            'gameimage_cache': {k: v.get('images', []) for k, v in global_metadata_cache.items()},
            'games_cache': {k: v.get('game') for k, v in global_metadata_cache.items()},
            'alternate_names_cache': {k: v.get('alternate_names', []) for k, v in global_metadata_cache.items()}
        }
    
    try:
        print("DEBUG: Loading comprehensive metadata cache from Metadata.xml...")
        start_time = time.time()
        
        if not os.path.exists(LAUNCHBOX_METADATA_PATH):
            print(f"DEBUG: Metadata.xml not found at {LAUNCHBOX_METADATA_PATH}")
            global_metadata_cache = {}
            global_metadata_cache_loaded = True
            return {
                'gameimage_cache': {},
                'games_cache': {},
                'alternate_names_cache': {}
            }
        
        # Parse the Metadata.xml
        tree = ET.parse(LAUNCHBOX_METADATA_PATH)
        root = tree.getroot()
        
        # Initialize temporary consolidated cache
        consolidated = {}
        all_game_images = root.findall('.//GameImage')
        print(f"DEBUG: Found {len(all_game_images)} GameImage entries in Metadata.xml")
        
        for game_image in all_game_images:
            db_id = game_image.find('DatabaseID')
            if db_id is not None and db_id.text:
                db_id_text = db_id.text
                entry = consolidated.setdefault(db_id_text, {'game': None, 'images': [], 'alternate_names': []})
                entry['images'].append(game_image)
        
        all_games = root.findall('.//Game')
        print(f"DEBUG: Found {len(all_games)} Game entries in Metadata.xml")
        
        for game in all_games:
            db_id = game.find('DatabaseID')
            if db_id is not None and db_id.text:
                db_id_text = db_id.text
                entry = consolidated.setdefault(db_id_text, {'game': None, 'images': [], 'alternate_names': []})
                entry['game'] = game
        
        all_alternate_names = root.findall('.//GameAlternateName')
        print(f"DEBUG: Found {len(all_alternate_names)} GameAlternateName entries in Metadata.xml")
        
        for alt_name in all_alternate_names:
            db_id = alt_name.find('DatabaseID')
            if db_id is not None and db_id.text:
                db_id_text = db_id.text
                entry = consolidated.setdefault(db_id_text, {'game': None, 'images': [], 'alternate_names': []})
                entry['alternate_names'].append(alt_name)
        
        # Update global consolidated cache
        global_metadata_cache = consolidated
        global_metadata_cache_loaded = True
        
        # Generate LaunchBox platforms cache from Game elements
        global _launchbox_platforms_cache
        platforms = set()
        for game in all_games:
            platform_elem = game.find('Platform')
            if platform_elem is not None and platform_elem.text:
                platforms.add(platform_elem.text.strip())
        
        _launchbox_platforms_cache = sorted(list(platforms))
        print(f"DEBUG: Cached {len(_launchbox_platforms_cache)} unique LaunchBox platforms")
        
        load_time = time.time() - start_time
        
        # Count total images across all games
        total_images = sum(len(entry.get('images', [])) for entry in consolidated.values())
        
        print(f"DEBUG: Comprehensive metadata cache loaded in {load_time:.2f} seconds")
        print(f"DEBUG: Found {total_images} total GameImage files across {len(consolidated)} games")
        print(f"DEBUG: Cached {len(consolidated)} total games")
        print(f"DEBUG: Cached {sum(1 for e in consolidated.values() if e.get('alternate_names'))} games with alternate names")
        
        return {
            'gameimage_cache': {k: v.get('images', []) for k, v in global_metadata_cache.items()},
            'games_cache': {k: v.get('game') for k, v in global_metadata_cache.items()},
            'alternate_names_cache': {k: v.get('alternate_names', []) for k, v in global_metadata_cache.items()}
        }
        
    except Exception as e:
        print(f"ERROR: Failed to load metadata cache: {e}")
        import traceback
        traceback.print_exc()
        global_metadata_cache = {}
        global_metadata_cache_loaded = True
        return {
            'gameimage_cache': {},
            'games_cache': {},
            'alternate_names_cache': {}
        }

def get_cached_game_data(database_id):
    """Get cached game data including alternate names"""
    if not global_metadata_cache_loaded:
        load_metadata_cache()
    
    entry = global_metadata_cache.get(database_id) or {}
    game_data = {
        'game': entry.get('game'),
        'alternate_names': entry.get('alternate_names', []),
        'images': entry.get('images', [])
    }
    
    return game_data

def get_cached_games_by_platform(platform):
    """Get all cached games for a specific platform"""
    if not global_metadata_cache_loaded:
        load_metadata_cache()
    
    platform_games = []
    for db_id, entry in global_metadata_cache.items():
        game = entry.get('game')
        if game is None:
            continue
        game_platform = game.find('Platform')
        if game_platform is not None and game_platform.text == platform:
            platform_games.append(game)
    
    return platform_games

def load_platform_metadata_cache(platform, use_global_cache=False, mapping_config=None):
    """Load only games and alternate names cache for a specific platform (no images)"""
    try:
        print(f"DEBUG: Loading platform-specific metadata cache for {platform}...")
        start_time = time.time()
        
        # Use global cache only if explicitly requested (for non-worker processes)
        if use_global_cache and global_metadata_cache_loaded and global_metadata_cache:
            print(f"DEBUG: Using global cache to build platform-specific cache for {platform}...")
            platform_cache = {}
            
            # Filter global cache for this platform
            for db_id, entry in global_metadata_cache.items():
                game_elem = entry.get('game')
                if game_elem is None:
                    continue
                
                # Check if this game is for the target platform
                game_platform = game_elem.find('Platform')
                if game_platform is not None and game_platform.text == platform:
                    platform_cache[db_id] = {
                        'game': game_elem,
                        'alternate_names': entry.get('alternate_names', [])
                    }
            
            platform_games_count = len(platform_cache)
            platform_alt_names_count = sum(len(entry.get('alternate_names', [])) for entry in platform_cache.values())
            
            print(f"DEBUG: Found {platform_games_count} games for platform {platform} from global cache")
            print(f"DEBUG: Found {platform_alt_names_count} alternate names for platform {platform} from global cache")
            
            load_time = time.time() - start_time
            print(f"DEBUG: Platform-specific metadata cache loaded in {load_time:.2f} seconds from global cache")
            
            return {
                'games_cache': {k: v.get('game') for k, v in platform_cache.items()},
                'alternate_names_cache': {k: v.get('alternate_names', []) for k, v in platform_cache.items()}
            }
        
        # Default behavior: parse XML file directly (for worker processes)
        print(f"DEBUG: Parsing XML file for platform {platform}...")
        
        if not os.path.exists(LAUNCHBOX_METADATA_PATH):
            print(f"DEBUG: Metadata.xml not found at {LAUNCHBOX_METADATA_PATH}")
            return {
                'games_cache': {},
                'alternate_names_cache': {}
            }
        
        # Parse the Metadata.xml
        tree = ET.parse(LAUNCHBOX_METADATA_PATH)
        root = tree.getroot()
        
        # Initialize platform-specific cache
        platform_cache = {}
        
        # Load games for the specific platform
        all_games = root.findall('.//Game')
        print(f"DEBUG: Found {len(all_games)} total Game entries in Metadata.xml")
        
        platform_games_count = 0
        for game in all_games:
            db_id = game.find('DatabaseID')
            game_platform = game.find('Platform')
            
            if (db_id is not None and db_id.text and 
                game_platform is not None and game_platform.text == platform):
                db_id_text = db_id.text
                entry = platform_cache.setdefault(db_id_text, {'game': None, 'alternate_names': []})
                entry['game'] = game
                platform_games_count += 1
        
        # Load alternate names for games in this platform
        all_alternate_names = root.findall('.//GameAlternateName')
        print(f"DEBUG: Found {len(all_alternate_names)} total GameAlternateName entries in Metadata.xml")
        
        platform_alt_names_count = 0
        for alt_name in all_alternate_names:
            db_id = alt_name.find('DatabaseID')
            if db_id is not None and db_id.text:
                db_id_text = db_id.text
                # Only add if we have a game for this platform
                if db_id_text in platform_cache:
                    entry = platform_cache[db_id_text]
                    entry['alternate_names'].append(alt_name)
                    platform_alt_names_count += 1
        
        load_time = time.time() - start_time
        
        print(f"DEBUG: Platform-specific metadata cache loaded in {load_time:.2f} seconds")
        print(f"DEBUG: Found {platform_games_count} games for platform {platform}")
        print(f"DEBUG: Found {platform_alt_names_count} alternate names for platform {platform}")
        print(f"DEBUG: Cached {sum(1 for e in platform_cache.values() if e.get('alternate_names'))} games with alternate names")
        
        return {
            'games_cache': {k: v.get('game') for k, v in platform_cache.items()},
            'alternate_names_cache': {k: v.get('alternate_names', []) for k, v in platform_cache.items()}
        }
        
    except Exception as e:
        print(f"ERROR: Failed to load platform metadata cache: {e}")
        import traceback
        traceback.print_exc()
        return {
            'games_cache': {},
            'alternate_names_cache': {}
        }

def get_cache_statistics():
    """Get statistics about the current metadata cache"""
    if not global_metadata_cache_loaded:
        return {
            'status': 'not_loaded',
            'games_with_images': 0,
            'total_games': 0,
            'games_with_alternate_names': 0
        }
    
    # Count total images across all games
    total_images = sum(len(entry.get('images', [])) for entry in global_metadata_cache.values())
    
    return {
        'status': 'loaded',
        'games_with_images': sum(1 for entry in global_metadata_cache.values() if entry.get('images')),
        'total_games': len(global_metadata_cache),
        'games_with_alternate_names': sum(1 for entry in global_metadata_cache.values() if entry.get('alternate_names')),
        'total_images': total_images,
        'total_database_ids': len(global_metadata_cache)
    }

def parse_gamelist_xml(file_path):
    """Parse gamelist.xml file and return list of games"""
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        games = []
        
        for game in root.findall('game'):
            game_data = {}
            
            # Parse each field
            for field in game:
                tag = field.tag
                raw_text = field.text.strip() if field.text else ''
                # Fix over-escaped entities and decode to get original text for storage
                text = fix_over_escaped_xml_entities(raw_text) if raw_text else ''
                
                if tag == 'id':
                    game_data['id'] = int(text) if text.isdigit() else 0
                elif tag == 'path':
                    game_data['path'] = text
                elif tag == 'name':
                    game_data['name'] = text
                elif tag == 'desc':
                    game_data['desc'] = text
                elif tag == 'genre':
                    game_data['genre'] = text
                elif tag == 'developer':
                    game_data['developer'] = text
                elif tag == 'publisher':
                    game_data['publisher'] = text
                elif tag == 'rating':
                    game_data['rating'] = text
                elif tag == 'players':
                    game_data['players'] = text
                elif tag == 'image':
                    game_data['image'] = text
                elif tag == 'video':
                    game_data['video'] = text
                elif tag == 'marquee':
                    game_data['marquee'] = text
                elif tag == 'wheel':
                    game_data['wheel'] = text
                elif tag == 'boxart':
                    game_data['boxart'] = text
                elif tag == 'thumbnail':
                    game_data['thumbnail'] = text
                elif tag == 'screenshot':
                    game_data['screenshot'] = text
                elif tag == 'cartridge':
                    game_data['cartridge'] = text
                elif tag == 'fanart':
                    game_data['fanart'] = text
                elif tag == 'titleshot':
                    game_data['titleshot'] = text
                elif tag == 'manual':
                    game_data['manual'] = text
                elif tag == 'boxback':
                    game_data['boxback'] = text
                elif tag == 'extra1':
                    game_data['extra1'] = text
                elif tag == 'launchboxid':
                    game_data['launchboxid'] = text
                elif tag == 'igdbid':
                    game_data['igdbid'] = text
            
            # Ensure required fields exist
            if 'id' not in game_data:
                game_data['id'] = len(games) + 1
            if 'name' not in game_data:
                game_data['name'] = 'Unknown Game'
            if 'path' not in game_data:
                game_data['path'] = './unknown.zip'
            if 'desc' not in game_data:
                game_data['desc'] = ''
            
            games.append(game_data)
        
        return games
    except Exception as e:
        print(f"Error parsing gamelist.xml: {e}")
        return []

@app.route('/test-session')
def test_session():
    """Test route to check session persistence"""
    if 'test_counter' not in session:
        session['test_counter'] = 0
    session['test_counter'] += 1
    return jsonify({
        'test_counter': session['test_counter'],
        'session_id': session.get('_id', 'no-id'),
        'user_logged_in': current_user.is_authenticated if current_user else False
    })

@app.route('/')
@login_required
def index():
    """Serve the main application page"""
    return render_template('index.html')

@app.route('/roms/<path:filename>')
def serve_rom_file(filename):
    """Serve ROM files and media"""
    return send_from_directory(ROMS_FOLDER, filename)

@app.route('/api/rom-systems')
@login_required
def list_rom_systems():
    """List all available ROM systems"""
    systems = []
    try:
        for system_name in os.listdir(ROMS_FOLDER):
            system_path = os.path.join(ROMS_FOLDER, system_name)
            if os.path.isdir(system_path):
                # Count games from var/<system>/gamelist.xml instead of roms/<system>/gamelist.xml
                gamelist_path = get_gamelist_path(system_name)
                rom_count = 0
                if os.path.exists(gamelist_path):
                    # Parse the actual gamelist.xml to get real count
                    games = parse_gamelist_xml(gamelist_path)
                    rom_count = len(games)
                
                systems.append({
                    'name': system_name,
                    'rom_count': rom_count,
                    'path': system_path
                })
    except Exception as e:
        print(f"Error listing ROM systems: {e}")
    
    return jsonify(systems)

@app.route('/api/config', methods=['GET', 'PUT'])
@login_required
def get_config():
    """Get or update application configuration"""
    if request.method == 'GET':
        return jsonify(config)
    elif request.method == 'PUT':
        try:
            new_config = request.get_json()
            if not new_config:
                return jsonify({'error': 'No configuration data provided'}), 400
            
            # Update config with new values
            for key, value in new_config.items():
                if key in config:
                    if isinstance(value, dict) and isinstance(config[key], dict):
                        config[key].update(value)
                    else:
                        config[key] = value
            
            # Save updated config to file
            with open('var/config/config.json', 'w') as f:
                json.dump(config, f, indent=4)
            
            # Update global variables
            global ROMS_FOLDER
            ROMS_FOLDER = config['roms_root_directory']
            
            return jsonify({'success': True, 'message': 'Configuration updated', 'config': config})
        except Exception as e:
            return jsonify({'error': f'Failed to update configuration: {str(e)}'}), 500

@app.route('/api/systems', methods=['GET', 'POST', 'PUT', 'DELETE'])
@login_required
def manage_systems():
    """Manage systems configuration"""
    try:
        if request.method == 'GET':
            # Return all systems
            systems = config.get('systems', {})
            return jsonify({'success': True, 'systems': systems})
        
        elif request.method == 'POST':
            # Add new system
            data = request.get_json()
            if not data or 'system_name' not in data:
                return jsonify({'error': 'System name is required'}), 400
            
            system_name = data['system_name']
            launchbox_platform = data.get('launchbox_platform', '')
            extensions = data.get('extensions', [])
            
            # Validate system name (lowercase, no spaces)
            if not system_name.islower() or ' ' in system_name:
                return jsonify({'error': 'System name must be lowercase with no spaces'}), 400
            
            # Check if system already exists
            if system_name in config.get('systems', {}):
                return jsonify({'error': 'System already exists'}), 400
            
            # Add new system
            if 'systems' not in config:
                config['systems'] = {}
            
            config['systems'][system_name] = {
                'launchbox': launchbox_platform,
                'extensions': extensions
            }
            
            # Save to file
            with open('var/config/config.json', 'w') as f:
                json.dump(config, f, indent=4)
            
            return jsonify({'success': True, 'message': 'System added successfully'})
        
        elif request.method == 'PUT':
            # Update existing system
            data = request.get_json()
            if not data or 'system_name' not in data:
                return jsonify({'error': 'System name is required'}), 400
            
            system_name = data['system_name']
            launchbox_platform = data.get('launchbox_platform', '')
            extensions = data.get('extensions', [])
            
            # Check if system exists
            if system_name not in config.get('systems', {}):
                return jsonify({'error': 'System not found'}), 404
            
            # Update system
            config['systems'][system_name] = {
                'launchbox': launchbox_platform,
                'extensions': extensions
            }
            
            # Save to file
            with open('var/config/config.json', 'w') as f:
                json.dump(config, f, indent=4)
            
            return jsonify({'success': True, 'message': 'System updated successfully'})
        
        elif request.method == 'DELETE':
            # Delete system
            system_name = request.args.get('system_name')
            if not system_name:
                return jsonify({'error': 'System name is required'}), 400
            
            # Check if system exists
            if system_name not in config.get('systems', {}):
                return jsonify({'error': 'System not found'}), 404
            
            # Delete system
            del config['systems'][system_name]
            
            # Save to file
            with open('var/config/config.json', 'w') as f:
                json.dump(config, f, indent=4)
            
            return jsonify({'success': True, 'message': 'System deleted successfully'})
    
    except Exception as e:
        return jsonify({'error': f'Failed to manage systems: {str(e)}'}), 500

# Cache for LaunchBox platforms (generated at startup)
_launchbox_platforms_cache = None

@app.route('/api/launchbox-platforms', methods=['GET'])
@login_required
def get_launchbox_platforms():
    """Get list of LaunchBox platforms from pre-generated cache"""
    global _launchbox_platforms_cache
    
    try:
        # Check if cache exists (should be generated at startup)
        if _launchbox_platforms_cache is not None:
            return jsonify({'success': True, 'platforms': _launchbox_platforms_cache})
        
        # If cache doesn't exist, try to load metadata cache which will generate it
        if not global_metadata_cache_loaded:
            load_metadata_cache()
        
        # Return the cache if it was generated
        if _launchbox_platforms_cache is not None:
            return jsonify({'success': True, 'platforms': _launchbox_platforms_cache})
        
        # Fallback: return empty list if metadata.xml is not available
        return jsonify({'success': True, 'platforms': []})
    
    except Exception as e:
        return jsonify({'error': f'Failed to load LaunchBox platforms: {str(e)}'}), 500

def clear_launchbox_platforms_cache():
    """Clear the LaunchBox platforms cache"""
    global _launchbox_platforms_cache
    _launchbox_platforms_cache = None

@app.route('/api/rom-system/<system_name>/gamelist', methods=['GET', 'PUT'])
@login_required
def rom_system_gamelist(system_name):
    """Get or update gamelist for a specific ROM system"""
    try:
        system_path = os.path.join(ROMS_FOLDER, system_name)
        if not os.path.exists(system_path):
            return jsonify({'error': 'System not found'}), 404
        
        # Ensure gamelist exists in var/gamelists, copying from roms/ if needed
        gamelist_path = ensure_gamelist_exists(system_name)
        if not os.path.exists(gamelist_path):
            # Return empty games array instead of 404 for systems without gamelist
            return jsonify({
                'success': True,
                'system': system_name,
                'games': [],
                'count': 0
            })
        
        if request.method == 'GET':
            # Parse the actual gamelist.xml file
            games = parse_gamelist_xml(gamelist_path)
            

            
            # Sort games by name for consistent ordering
            games.sort(key=lambda x: x.get('name', '').lower())
            
            return jsonify({
                'success': True,
                'system': system_name,
                'games': games,
                'count': len(games)
            })
        elif request.method == 'PUT':
            # Update the gamelist.xml file
            data = request.get_json()
            if not data or 'games' not in data:
                return jsonify({'error': 'Invalid request data'}), 400
            
            print(f"🔔 PUT request received for system: {system_name}")
            print(f"🔔 Request data: {data}")
            
            games = data['games']
            delete_rom_paths = data.get('delete_rom_paths', [])
            
            # Log the deletion operation
            if delete_rom_paths:
                app.logger.info(f'Deleting {len(delete_rom_paths)} games from {system_name} gamelist using ROM file paths')
                app.logger.info(f'Received delete_rom_paths: {delete_rom_paths}')
                
                # Delete associated files for each deleted game
                deleted_files = []
                failed_deletions = []
                
                for rom_path in delete_rom_paths:
                    app.logger.info(f'Processing ROM path: "{rom_path}"')
                    try:
                        # Convert relative path to absolute path relative to ROMS_FOLDER
                        if not os.path.isabs(rom_path):
                            # Ensure clean path construction without double slashes
                            rom_path = os.path.normpath(os.path.join(ROMS_FOLDER, rom_path))
                        
                        rom_abs_path = os.path.abspath(rom_path)
                        
                        # Security check: ensure the ROM path is within the allowed directories
                        allowed_dirs = [
                            os.path.abspath(os.path.join(app.root_path, 'roms')),
                            os.path.abspath(os.path.join(app.root_path, 'media'))
                        ]
                        
                        is_allowed = False
                        for allowed_dir in allowed_dirs:
                            if rom_abs_path.startswith(allowed_dir):
                                is_allowed = True
                                break
                        
                        if not is_allowed:
                            failed_deletions.append({'path': rom_path, 'error': 'Access denied'})
                            continue
                        
                        # Delete ROM file
                        app.logger.info(f'Checking if ROM file exists: {rom_abs_path}')
                        if os.path.exists(rom_abs_path):
                            os.remove(rom_abs_path)
                            deleted_files.append(f"ROM: {rom_path}")
                            app.logger.info(f'Deleted ROM file: {rom_abs_path}')
                        else:
                            app.logger.warning(f'ROM file not found: {rom_abs_path}')
                            failed_deletions.append({'path': rom_path, 'error': 'ROM file not found'})
                        
                        # Find and delete associated media files
                        rom_filename = os.path.splitext(os.path.basename(rom_path))[0]
                        app.logger.info(f'Looking for media files with ROM filename: {rom_filename}')
                        media_dir = os.path.join(system_path, 'media')
                        
                        if os.path.exists(media_dir):
                            # Check all media subdirectories for files with matching name
                            media_fields = ['boxart', 'screenshot', 'marquee', 'wheel', 'video', 'thumbnail', 'cartridge', 'fanart', 'title', 'manual', 'boxback', 'box2d']
                            
                            for field in media_fields:
                                field_dir = os.path.join(media_dir, field)
                                if os.path.exists(field_dir):
                                    # Look for files that start with the ROM filename
                                    for file in os.listdir(field_dir):
                                        if file.startswith(rom_filename):
                                            file_path = os.path.join(field_dir, file)
                                            try:
                                                os.remove(file_path)
                                                deleted_files.append(f"{field}: {file}")
                                                app.logger.info(f'Deleted media file: {file_path}')
                                            except Exception as e:
                                                failed_deletions.append({'path': file_path, 'error': str(e)})
                                                app.logger.error(f'Failed to delete media file {file_path}: {e}')
                        
                    except Exception as e:
                        failed_deletions.append({'path': rom_path, 'error': str(e)})
                        app.logger.error(f'Error deleting files for ROM {rom_path}: {e}')
                
                app.logger.info(f'File deletion completed: {len(deleted_files)} files deleted, {len(failed_deletions)} failed')
            
            # Write the updated games back to gamelist.xml
            write_gamelist_xml(games, gamelist_path)
            
            # Get changed games data before notifications
            changed_games = data.get('changed_games', [])
            print(f"🔔 Changed games data: {changed_games}")
            
            # Notify all connected clients about the gamelist update
            if delete_rom_paths:
                print(f"🔔 Notifying about gamelist update with deletions")
                notify_gamelist_updated(system_name, len(games), len(delete_rom_paths), len(changed_games))
                notify_game_deleted(system_name, deleted_files)
            else:
                print(f"🔔 Notifying about gamelist update without deletions")
                notify_gamelist_updated(system_name, len(games), 0, len(changed_games))
                
            # Notify about individual game changes if provided
            print(f"🔔 Processing {len(changed_games)} changed games for individual notifications")
            for changed_game in changed_games:
                if changed_game.get('changed_fields'):
                    print(f"🔔 Notifying about game update: {changed_game['game_name']} with fields: {changed_game['changed_fields']}")
                    notify_game_updated(system_name, changed_game['game_name'], changed_game['changed_fields'])
                else:
                    print(f"⚠️  Changed game missing changed_fields: {changed_game}")
            
            return jsonify({
                'success': True,
                'message': f'Successfully saved {len(games)} games to {system_name}',
                'count': len(games),
                'deleted_count': len(delete_rom_paths),
                'deleted_files': deleted_files if delete_rom_paths else [],
                'failed_deletions': failed_deletions if delete_rom_paths else []
            })
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/rom-system/<system_name>/gamelist-diff', methods=['GET'])
@login_required
def gamelist_diff_endpoint(system_name):
    """Get differences between var/gamelists and roms gamelist files"""
    try:
        result = compare_gamelist_files(system_name)
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
    except Exception as e:
        return jsonify({'error': f'Failed to compare gamelist files: {str(e)}'}), 500

@app.route('/api/rom-system/<system_name>/save-gamelist', methods=['POST'])
@login_required
def save_gamelist_endpoint(system_name):
    """Save gamelist from var/gamelists to roms/ directory"""
    try:
        result = save_gamelist_to_roms(system_name)
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
    except Exception as e:
        return jsonify({'error': f'Failed to save gamelist: {str(e)}'}), 500

def load_launchbox_config():
    """Load Launchbox configuration from consolidated config.json"""
    global platform_metadata_cache, current_system_platform
    
    # Load from consolidated config
    mapping_config = config.get('launchbox', {}).get('mapping', {})
    system_platform_mapping = config.get('systems', {})
    
    return mapping_config, system_platform_mapping


def parse_launchbox_metadata(metadata_path, target_platform, skip_global_cache=False):
    """Parse Launchbox Metadata.xml file using cached data"""
    global platform_metadata_cache
    
    # Check if we need to re-parse (system changed)
    if target_platform in platform_metadata_cache:
        print(f"Using cached metadata for platform: {target_platform}")
        return platform_metadata_cache[target_platform]
    
    print(f"Building metadata for platform: {target_platform} from cache...")
    
    try:
        # Use the comprehensive cache instead of parsing XML (unless skipped for worker processes)
        if not skip_global_cache and not global_metadata_cache_loaded:
            load_metadata_cache()
        
        games = []
        
        # Build games list from consolidated cache for the target platform
        for db_id, entry in global_metadata_cache.items():
            game_elem = entry.get('game')
            if game_elem is None:
                continue
            game_data = {}
            
            # Parse basic game fields from cached element
            # Get the fields to load from mapping configuration
            fields_to_load = set(['Name', 'Platform', 'DatabaseID'])  # Always load these core fields
            mapping_config = config.get('launchbox', {}).get('mapping', {})
            if mapping_config:
                # Add all LaunchBox fields from the mapping configuration
                fields_to_load.update(mapping_config.keys())
            
            for child in game_elem:
                tag = child.tag
                text = child.text.strip() if child.text else ''
                
                if tag in fields_to_load:
                    game_data[tag] = text
            
            # Only include games for the current platform
            if game_data.get('Platform') == target_platform:
                # Link alternate names to this game from cache
                alt_names = []
                for alt_elem in entry.get('alternate_names', []) or []:
                    alt_name = alt_elem.find('AlternateName')
                    if alt_name is not None and alt_name.text:
                        alt_names.append(alt_name.text.strip())
                game_data['AlternateNames'] = alt_names
                if alt_names:
                    print(f"DEBUG: Game '{game_data.get('Name')}' has alternate names: {alt_names}")
                games.append(game_data)
        
        # Cache the results
        platform_metadata_cache[target_platform] = games
        print(f"Cached {len(games)} games for platform: {target_platform}")
        
        # Log alternate names statistics
        total_alternate_names = sum(len(game.get('AlternateNames', [])) for game in games)
        print(f"Found {total_alternate_names} alternate names across {len(games)} games")
        
        return games
        
    except Exception as e:
        print(f"Error building metadata from cache: {e}")
        import traceback
        traceback.print_exc()
        return []

def normalize_game_name(name):
    """Normalize game name for consistent matching across the application"""
    if not name:
        return ""

    # Remove 
    normalized = name.replace(' III','3').replace(' II', ' 2').replace(" IV", '4').lower()

    
    # Remove specific characters: dash, colon, underscore, apostrophe
    for char in ['-', ':', '_', '/', '\\', '|', '!', '*', "'", '"', ',', '.',' ']:
        normalized = normalized.replace(char, '')
    return normalized

def find_best_match(game_name, metadata_games, target_platform, existing_launchboxid=None, platform_cache=None, mapping_config=None):
    """Find the best matching game in Launchbox metadata"""
    if not metadata_games:
        return None, 0
    
    # If we have a launchboxid, try to find the exact match first via cache
    if existing_launchboxid:
        try:
            # Use platform-specific cache if provided, otherwise fall back to global cache
            if platform_cache:
                games_cache = platform_cache.get('games_cache', {})
                alternate_names_cache = platform_cache.get('alternate_names_cache', {})
                game_elem = games_cache.get(existing_launchboxid)
                alt_names_elements = alternate_names_cache.get(existing_launchboxid, [])
   
            
            if game_elem is not None:
                # Build a minimal game dict consistent with metadata_games entries
                game_data = {}
                
                # Get the fields to load from mapping configuration
                fields_to_load = set(['Name', 'Platform', 'DatabaseID'])  # Always load these core fields
                if mapping_config:
                    # Add all LaunchBox fields from the mapping configuration
                    fields_to_load.update(mapping_config.keys())
                
                for child in game_elem:
                    tag = child.tag
                    text = child.text.strip() if child.text else ''
                    if tag in fields_to_load:
                        game_data[tag] = text
                # Attach alternate names from cache (platform check not required for unique DBIDs)
                alt_names = []
                for alt_elem in alt_names_elements:
                    alt_name = alt_elem.find('AlternateName')
                    if alt_name is not None and alt_name.text:
                        alt_names.append(alt_name.text.strip())
                game_data['AlternateNames'] = alt_names
                # Annotate match info for downstream logic
                game_data['_match_type'] = 'launchboxid'
                game_data['_matched_name'] = game_data.get('Name', '')
                return game_data, 1.0
        except Exception:
            # Fall back to scanning metadata_games on any issue
            pass
    
    # Create indexed lookups for O(1) exact matches instead of O(n) linear searches
    # Apply the same normalization as used later in the function
    
    normalized_search = normalize_game_name(game_name)
    
    # Fallback version removes parentheses and brackets after normalization (including nested)
    normalized_search_no_parens = re.sub(r'\s*[\(\[][^()\[\]]*(?:[\(\[][^()\[\]]*[\)\]][^()\[\]]*)*[\)\]]', '', game_name)
    normalized_search_no_parens = normalize_game_name(normalized_search_no_parens)
    
    # Build unified index on first call or when metadata_games changes (cached for subsequent calls)
    if not hasattr(find_best_match, '_unified_index') or find_best_match._metadata_games is not metadata_games:
        print(f"DEBUG: Building unified index for {len(metadata_games)} games...")
        find_best_match._unified_index = {}
        find_best_match._metadata_games = metadata_games
        
        # Build unified index for both main names and alternate names
        main_name_count = 0
        alt_name_count = 0
        for i, game in enumerate(metadata_games):
            # Index main name with consistent normalization
            name = normalize_game_name(game.get('Name', ''))
            if name:
                if name not in find_best_match._unified_index:
                    find_best_match._unified_index[name] = []
                find_best_match._unified_index[name].append(('main', i))
                main_name_count += 1
            
            # Index alternate names with consistent normalization
            alternate_names = game.get('AlternateNames', [])
            for alt_name in alternate_names:
                alt_name_normalized = normalize_game_name(alt_name)
                if alt_name_normalized not in find_best_match._unified_index:
                    find_best_match._unified_index[alt_name_normalized] = []
                find_best_match._unified_index[alt_name_normalized].append(('alternate', i))
                alt_name_count += 1
        
        print(f"DEBUG: Indexed {main_name_count} main names and {alt_name_count} alternate names")
    
    # Try exact match using unified index (O(1) lookup)
    # First try with normalized search (with parentheses removed)
    if normalized_search in find_best_match._unified_index:
        for match_type, game_idx in find_best_match._unified_index[normalized_search]:
            game = metadata_games[game_idx]
            if match_type == 'main':
                game['_match_type'] = 'main'
                game['_matched_name'] = game.get('Name', '')
                return game, 1.0
            elif match_type == 'alternate':
                # Find the exact alternate name that matched
                for alt_name in game.get('AlternateNames', []):
                    if normalize_game_name(alt_name) == normalized_search:
                        game['_match_type'] = 'alternate'
                        game['_matched_name'] = alt_name
                        print(f"DEBUG: Found alternate name match for '{game_name}' → '{alt_name}' (via unified index)")
                        return game, 1.0
    # If no match found with normalized search, try with no_parens version
    if normalized_search != normalized_search_no_parens and normalized_search_no_parens in find_best_match._unified_index:
        for match_type, game_idx in find_best_match._unified_index[normalized_search_no_parens]:
            game = metadata_games[game_idx]
            if match_type == 'main':
                game['_match_type'] = 'main'
                game['_matched_name'] = game.get('Name', '')
                return game, 1.0
            elif match_type == 'alternate':
                # Find the exact alternate name that matched
                for alt_name in game.get('AlternateNames', []):
                    if normalize_game_name(alt_name) == normalized_search_no_parens:
                        game['_match_type'] = 'alternate'
                        game['_matched_name'] = alt_name
                        print(f"DEBUG: Found alternate name match for '{game_name}' → '{alt_name}' (via unified index, no parens)")
                        return game, 1.0
    
    # Clean the game name for better matching (same logic as gamelist.xml)
    cleaned_name = re.sub(r'\s*[\(\[][^()\[\]]*(?:[\(\[][^()\[\]]*[\)\]][^()\[\]]*)*[\)\]]', '', game_name)  # Remove text in parentheses and brackets (including nested)
    cleaned_name = cleaned_name.lower().strip()
    #cleaned_name = normalize_game_name(cleaned_name)
    
    # Also try matching with parentheses and brackets removed from both sides (including nested)
    game_name_no_parens = re.sub(r'\s*[\(\[][^()\[\]]*(?:[\(\[][^()\[\]]*[\)\]][^()\[\]]*)*[\)\]]', '', game_name).strip()
    game_name_no_parens = game_name_no_parens.lower().strip()

    best_match = None
    best_score = 0
    best_match_type = 'main'  # Track whether match was from main name or alternate name
    
    # Check all games for similarity matching
    for i, game in enumerate(metadata_games):
        metadata_name = game.get('Name', '')
        if not metadata_name:
            continue
        
        # Calculate similarity score for main name (with and without parentheses)
        main_similarity = difflib.SequenceMatcher(None, cleaned_name, metadata_name.lower()).ratio()
        main_similarity_no_parens = difflib.SequenceMatcher(None, game_name_no_parens, metadata_name.lower()).ratio()
        main_similarity = max(main_similarity, main_similarity_no_parens)
        
        # Check alternate names for better matches
        alternate_names = game.get('AlternateNames', [])
        best_alt_similarity = 0
        best_alt_name = None
        
        for alt_name in alternate_names:
            # Check both cleaned and no-parentheses versions
            alt_similarity = difflib.SequenceMatcher(None, cleaned_name, alt_name.lower()).ratio()
            alt_similarity_no_parens = difflib.SequenceMatcher(None, game_name_no_parens, alt_name.lower()).ratio()
            alt_similarity = max(alt_similarity, alt_similarity_no_parens)
            
            if alt_similarity > best_alt_similarity:
                best_alt_similarity = alt_similarity
                best_alt_name = alt_name
        
        # Use the best similarity score (main name or alternate name)
        if best_alt_similarity > main_similarity:
            similarity = best_alt_similarity
            match_type = 'alternate'
            matched_name = best_alt_name
        else:
            similarity = main_similarity
            match_type = 'main'
            matched_name = metadata_name
        
          
        # Bonus for publisher match (if we have publisher info)
        metadata_publisher = game.get('Publisher', '').lower().strip()
        if metadata_publisher:
            # Check if any search variation matches publisher
            if cleaned_name == metadata_publisher:
                similarity += 0.15  # Significant bonus for publisher match
            elif cleaned_name in metadata_publisher or metadata_publisher in cleaned_name:
                similarity += 0.08  # Partial publisher match bonus
            elif game_name_no_parens == metadata_publisher:
                similarity += 0.15  # Significant bonus for publisher match
            elif game_name_no_parens in metadata_publisher or metadata_publisher in game_name_no_parens:
                similarity += 0.08  # Partial publisher match bonus
        
        # Bonus for developer match (if we have developer info)
        metadata_developer = game.get('Developer', '').lower().strip()
        if metadata_developer:
            # Check if any search variation matches developer
            if cleaned_name == metadata_developer:
                similarity += 0.12  # Bonus for developer match
            elif cleaned_name in metadata_developer or metadata_developer in cleaned_name:
                similarity += 0.06  # Partial developer match bonus
            elif game_name_no_parens == metadata_developer:
                similarity += 0.12  # Bonus for developer match
            elif game_name_no_parens in metadata_developer or metadata_developer in game_name_no_parens:
                similarity += 0.06  # Partial developer match bonus
        
        if similarity > best_score:
            best_score = similarity
            best_match = game
            best_match_type = match_type
            best_matched_name = matched_name
            
            # Early termination for very good matches (score > 0.9)
            if similarity > 0.9:
                break
    
    # Add match information to the best match for logging purposes
    if best_match:
        best_match['_match_type'] = best_match_type
        best_match['_matched_name'] = best_matched_name
    
    return best_match, best_score


def get_top_matches(game_name, metadata_games, target_platform, top_n=20, mapping_config=None):
    """Get top N matches for a game name, sorted by similarity score"""
    if not metadata_games:
        return []
    
    # Clean the game name for better matching
    cleaned_name = re.sub(r'\s*\([^)]*\)', '', game_name)  # Remove text in parentheses
    cleaned_name = normalize_game_name(cleaned_name)
    
    # Also try matching with parentheses removed from both sides
    game_name_no_parens = re.sub(r'\s*\([^)]*\)', '', game_name).strip()
    
    matches = []
    
    for game in metadata_games:
        metadata_name = game.get('Name', '')
        if not metadata_name:
            continue
        
        # Calculate similarity score for main name (with and without parentheses)
        main_similarity = difflib.SequenceMatcher(None, cleaned_name.lower(), metadata_name.lower()).ratio()
        main_similarity_no_parens = difflib.SequenceMatcher(None, game_name_no_parens.lower(), metadata_name.lower()).ratio()
        main_similarity = max(main_similarity, main_similarity_no_parens)
        
        # Check alternate names for better matches
        alternate_names = game.get('AlternateNames', [])
        best_alt_similarity = 0
        best_alt_name = None
        
        for alt_name in alternate_names:
            # Check both cleaned and no-parentheses versions
            alt_similarity = difflib.SequenceMatcher(None, cleaned_name.lower(), alt_name.lower()).ratio()
            alt_similarity_no_parens = difflib.SequenceMatcher(None, game_name_no_parens.lower(), alt_name.lower()).ratio()
            alt_similarity = max(alt_similarity, alt_similarity_no_parens)
            
            if alt_similarity > best_alt_similarity:
                best_alt_similarity = alt_similarity
                best_alt_name = alt_name
        
        # Use the best similarity score (main name or alternate name)
        if best_alt_similarity > main_similarity:
            similarity = best_alt_similarity
            match_type = 'alternate'
            matched_name = best_alt_name
        else:
            similarity = main_similarity
            match_type = 'main'
            matched_name = metadata_name
        
        # Bonus for platform match
        if game.get('Platform') == target_platform:
            similarity += 0.1
        
        # Bonus for publisher match (if we have publisher info)
        metadata_publisher = game.get('Publisher', '').lower().strip()
        if metadata_publisher:
            # Check if any search variation matches publisher
            if cleaned_name.lower().strip() == metadata_publisher:
                similarity += 0.15  # Significant bonus for publisher match
            elif cleaned_name.lower().strip() in metadata_publisher or metadata_publisher in cleaned_name.lower().strip():
                similarity += 0.08  # Partial publisher match bonus
            elif game_name_no_parens.lower().strip() == metadata_publisher:
                similarity += 0.15  # Significant bonus for publisher match
            elif game_name_no_parens.lower().strip() in metadata_publisher or metadata_publisher in game_name_no_parens.lower().strip():
                similarity += 0.08  # Partial publisher match bonus
        
        # Bonus for developer match (if we have developer info)
        metadata_developer = game.get('Developer', '').lower().strip()
        if metadata_developer:
            # Check if any search variation matches developer
            if cleaned_name.lower().strip() == metadata_developer:
                similarity += 0.12  # Bonus for developer match
            elif cleaned_name.lower().strip() in metadata_developer or metadata_developer in cleaned_name.lower().strip():
                similarity += 0.06  # Partial developer match bonus
            elif game_name_no_parens.lower().strip() == metadata_developer:
                similarity += 0.12  # Bonus for developer match
            elif game_name_no_parens.lower().strip() in metadata_developer or metadata_developer in game_name_no_parens.lower().strip():
                similarity += 0.06  # Partial developer match bonus
        
        # Create match info
        match_info = {
            'game': game,
            'score': similarity,
            'match_type': match_type,
            'matched_name': matched_name,
            'database_id': game.get('DatabaseID', ''),
            'name': game.get('Name', ''),
            'overview': game.get('Overview', ''),
            'developer': game.get('Developer', ''),
            'publisher': game.get('Publisher', '')
        }
        
        # Add mapped fields dynamically based on mapping configuration
        if mapping_config:
            for launchbox_field, gamelist_field in mapping_config.items():
                match_info[gamelist_field] = game.get(launchbox_field, '')
        
        matches.append(match_info)
    
    # Sort by score (highest first) and return top N
    matches.sort(key=lambda x: x['score'], reverse=True)
    return matches[:top_n]

def _dedupe_games_by_path(games):
    """Return a new list with duplicates removed by 'path' (first occurrence wins)."""
    seen_paths = set()
    deduped = []
    for game in games:
        raw_path = (game.get('path') or '').strip()
        key = raw_path if raw_path else f"__no_path__::{(game.get('name') or '').strip().lower()}"
        if key in seen_paths:
            continue
        seen_paths.add(key)
        deduped.append(game)
    removed_count = max(0, len(games) - len(deduped))
    if removed_count:
        print(f"🧹 Deduped games by path: removed {removed_count} duplicate entries (kept first occurrence)")
    return deduped

def write_gamelist_xml(games, file_path):
    """Write games list to gamelist.xml file (deduped by path)."""
    try:
        games_to_write = _dedupe_games_by_path(games)
        root = ET.Element('gameList')
        
        for game in games_to_write:
            game_elem = ET.SubElement(root, 'game')
            
            # Add all game fields
            for field, value in game.items():
                if value is not None and value != '':
                    field_elem = ET.SubElement(game_elem, field)
                    # Write raw text as-is; XML writer will handle escaping (& -> &amp;)
                    field_elem.text = str(value)
        
        # Write to file
        tree = ET.ElementTree(root)
        tree.write(file_path, encoding='utf-8', xml_declaration=True)
        
    except Exception as e:
        print(f"Error writing gamelist.xml: {e}")

@app.route('/api/scrap-launchbox', methods=['POST'])
@login_required
def scrap_launchbox():
    """Start Launchbox scraping process"""
    global current_task_id
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        system_name = data.get('system')
        selected_games = data.get('selectedGames', [])
        force_download = data.get('force_download', False)  # Add force download option
        enable_partial_match_modal = data.get('enable_partial_match_modal', False)  # Add partial match modal option
        
        if not system_name:
            return jsonify({'error': 'System name required'}), 400
        
        # Create and start new task
        task = create_task('scraping', {
            'system_name': system_name,
            'selected_games': selected_games,
            'force_download': force_download,
            'enable_partial_match_modal': enable_partial_match_modal
        })
        current_task_id = task.id
        task.start()
        
        # Enqueue scraping in single worker process (sequential)
        _ensure_worker_started()
        payload = {
            'type': 'scraping',
            'task_id': task.id,
            'system_name': system_name,
            'selected_games': selected_games,
            'enable_partial_match_modal': enable_partial_match_modal,
            'force_download': force_download,
            'selected_fields': selected_fields,
            'overwrite_text_fields': overwrite_text_fields,
        }
        _worker_task_queue.put(payload)
        
        return jsonify({
            'success': True,
            'message': 'Scraping started',
            'system': system_name
        })
        
    except Exception as e:
        if current_task_id and current_task_id in tasks:
            tasks[current_task_id].complete(False, str(e))
        print(f"Error in scrap_launchbox endpoint: {e}")
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500

@app.route('/api/scrap-launchbox/<system_name>', methods=['GET', 'POST'])
@login_required
def scrap_launchbox_simple(system_name):
    """Start Launchbox scraping process with system name in URL (for easier testing)"""
    global current_task_id, scraping_in_progress, scraping_progress, scraping_stats
    
    # Check if another task is already running
    can_start, message = can_start_task('scraping')
    if not can_start:
        # Queue the task if it can't start immediately
        queued, queue_message = queue_task('scraping', {
            'system_name': system_name,
            'method': request.method,
            'data': request.get_json() if request.method == 'POST' else None
        })
        return jsonify({
            'error': message,
            'queued': queued,
            'queue_message': queue_message
        }), 409  # Conflict status
    
    try:
        if not system_name:
            return jsonify({'error': 'System name required'}), 400
        
        # Get selected games and partial match modal setting from POST body if available
        selected_games = None
        enable_partial_match_modal = False
        force_download = False  # Default force download to False
        selected_fields = None
        overwrite_text_fields = False  # Default overwrite text fields to False
        
        if request.method == 'POST':
            try:
                data = request.get_json()
                if data:
                    if 'selected_games' in data:
                        selected_games = data['selected_games']
                        scraping_progress.append(f"Processing {len(selected_games)} selected games")
                    else:
                        scraping_progress.append("Processing all games")
                    
                    if 'enable_partial_match_modal' in data:
                        enable_partial_match_modal = data['enable_partial_match_modal']
                        print(f"DEBUG: Received enable_partial_match_modal: {enable_partial_match_modal} (type: {type(enable_partial_match_modal)})")
                        if enable_partial_match_modal:
                            scraping_progress.append("Partial match modal enabled - will show modal for non-perfect matches")
                        else:
                            scraping_progress.append("Partial match modal disabled - only perfect matches will be applied")
                    
                    if 'force_download' in data:
                        force_download = data['force_download']
                        if force_download:
                            scraping_progress.append("Force download enabled - will overwrite existing media fields")
                        else:
                            scraping_progress.append("Force download disabled - will only update empty media fields")
                    
                    if 'selected_fields' in data:
                        selected_fields = data['selected_fields']
                        if selected_fields:
                            scraping_progress.append(f"Field selection enabled - will only scrape: {', '.join(selected_fields)}")
                        else:
                            scraping_progress.append("No fields selected - will scrape all fields")
                    
                    if 'overwrite_text_fields' in data:
                        overwrite_text_fields = data['overwrite_text_fields']
                        if overwrite_text_fields:
                            scraping_progress.append("Overwrite text fields enabled - will overwrite existing text fields")
                        else:
                            scraping_progress.append("Overwrite text fields disabled - will only update empty text fields")
            except Exception as e:
                scraping_progress.append(f"Error parsing POST data: {e}")
                pass  # Ignore JSON parsing errors
        
        # Create and start new task (after parsing POST data)
        task = create_task('scraping', {
            'system_name': system_name,
            'selected_games': selected_games,
            'enable_partial_match_modal': enable_partial_match_modal,
            'force_download': force_download,
            'selected_fields': selected_fields,
            'overwrite_text_fields': overwrite_text_fields
        })
        current_task_id = task.id
        task.start()
        
        # Enqueue scraping in single worker process (sequential)
        _ensure_worker_started()
        payload = {
            'type': 'scraping',
            'task_id': task.id,
            'system_name': system_name,
            'selected_games': selected_games,
            'enable_partial_match_modal': enable_partial_match_modal,
            'force_download': force_download,
            'selected_fields': selected_fields,
            'overwrite_text_fields': overwrite_text_fields,
        }
        _worker_task_queue.put(payload)
        
        return jsonify({
            'success': True,
            'message': 'Scraping started',
            'system': system_name
        })
        
    except Exception as e:
        if current_task_id and current_task_id in tasks:
            tasks[current_task_id].complete(False, str(e))
        print(f"Error in scrap_launchbox_simple endpoint: {e}")
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500

@app.route('/api/scrap-launchbox-progress')
@login_required
def get_scraping_progress():
    """Get current scraping progress"""
    try:
        global scraping_in_progress, scraping_progress, scraping_stats
        
        return jsonify({
            'in_progress': scraping_in_progress,
            'progress': scraping_progress,
            'stats': scraping_stats
        })
    except Exception as e:
        print(f"Error in get_scraping_progress endpoint: {e}")
        return jsonify({
            'error': 'Internal server error',
            'in_progress': False,
            'progress': [],
            'stats': {}
        })

@app.route('/api/find-best-matches', methods=['POST'])
@login_required
def find_best_matches_endpoint():
    """Find best matches for selected games without creating a scraping task"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        system_name = data.get('system_name')
        selected_games = data.get('selected_games', [])
        
        if not system_name:
            return jsonify({'error': 'System name required'}), 400
        
        if not selected_games:
            return jsonify({'error': 'No games selected'}), 400
        
        # Load LaunchBox metadata
        mapping_config, system_platform_mapping = load_launchbox_config()
        current_system_platform = system_platform_mapping.get(system_name, {}).get('launchbox', 'Arcade')
        
        if not os.path.exists(LAUNCHBOX_METADATA_PATH):
            return jsonify({'error': 'Metadata.xml not found'}), 404
        
        # Load global metadata cache and filter by platform
        global_cache = load_metadata_cache()
        all_games_cache = global_cache['games_cache']
        all_alternate_names_cache = global_cache['alternate_names_cache']
        
        # Filter games by platform from global cache
        platform_games = {}
        platform_alternate_names = {}
        
        for db_id, game_elem in all_games_cache.items():
            if game_elem is not None:
                # Check if this game belongs to the target platform
                platform_elem = game_elem.find('Platform')
                if platform_elem is not None and platform_elem.text:
                    game_platform = platform_elem.text.strip()
                    if game_platform == current_system_platform:
                        platform_games[db_id] = game_elem
                        platform_alternate_names[db_id] = all_alternate_names_cache.get(db_id, [])
        
        if not platform_games:
            return jsonify({'error': f'No metadata for platform {current_system_platform}'}), 404
        
        # Convert filtered platform cache to metadata_games format for compatibility
        metadata_games = []
        for db_id, game_elem in platform_games.items():
            if game_elem is not None:
                game_data = {}
                # Get the fields to load from mapping configuration
                fields_to_load = set(['Name', 'Platform', 'DatabaseID'])  # Always load these core fields
                if mapping_config:
                    # Add all LaunchBox fields from the mapping configuration
                    fields_to_load.update(mapping_config.keys())
                
                for child in game_elem:
                    tag = child.tag
                    text = child.text.strip() if child.text else ''
                    if tag in fields_to_load:
                        game_data[tag] = text
                
                # Add alternate names
                alt_names = []
                for alt_elem in platform_alternate_names.get(db_id, []):
                    alt_name = alt_elem.find('AlternateName')
                    if alt_name is not None and alt_name.text:
                        alt_names.append(alt_name.text.strip())
                game_data['AlternateNames'] = alt_names
                
                metadata_games.append(game_data)
        
        # Create platform_cache object for compatibility with find_best_match
        platform_cache = {
            'games_cache': platform_games,
            'alternate_names_cache': platform_alternate_names
        }
        
        # Load gamelist to get game details
        gamelist_path = ensure_gamelist_exists(system_name)
        if not os.path.exists(gamelist_path):
            return jsonify({'error': 'Gamelist not found'}), 404
        
        all_games = parse_gamelist_xml(gamelist_path)
        if not all_games:
            return jsonify({'error': 'No games found in gamelist'}), 400
        
        # Find selected games in gamelist
        games_to_process = [g for g in all_games if g.get('path') in selected_games]
        
        if not games_to_process:
            return jsonify({'error': 'No selected games found in gamelist'}), 404
        
        results = []
        for game_data in games_to_process:
            game_name = game_data.get('name', 'Unknown')
            existing_launchboxid = game_data.get('launchboxid')
            
            # Find best match
            best_match, score = find_best_match(game_name, metadata_games, current_system_platform, existing_launchboxid, platform_cache, mapping_config)
            
            if best_match and score > 0.5:  # Only include games with reasonable matches
                # Get top matches for the modal
                top_matches = get_top_matches(game_name, metadata_games, current_system_platform, top_n=20, mapping_config=mapping_config)
                
                result = {
                    'game_name': game_name,
                    'game_data': game_data,
                    'best_match': best_match,
                    'score': score,
                    'top_matches': top_matches,
                    'match_type': best_match.get('_match_type', 'main'),
                    'matched_name': best_match.get('_matched_name', best_match.get('Name', 'Unknown'))
                }
                results.append(result)
        
        return jsonify({
            'success': True,
            'results': results,
            'total_games': len(games_to_process),
            'matched_games': len(results)
        })
        
    except Exception as e:
        print(f"Error in find_best_matches endpoint: {e}")
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500

@app.route('/api/check-partial-match-requests', methods=['GET'])
@login_required
def check_partial_match_requests():
    """Check for pending partial match requests during scraping"""
    try:
        global partial_match_queue
        
        print(f"DEBUG: Checking partial match queue, size: {len(partial_match_queue)}")
        
        if partial_match_queue:
            # Return the first pending request
            request_data = partial_match_queue.pop(0)
            print(f"DEBUG: Returning partial match request: {request_data['game_name']}")
            return jsonify({
                'has_request': True,
                'request': request_data
            })
        else:
            print("DEBUG: No partial match requests in queue")
            return jsonify({
                'has_request': False
            })
    except Exception as e:
        print(f"Error in check_partial_match_requests endpoint: {e}")
        return jsonify({
            'error': f'Internal server error: {str(e)}',
            'has_request': False
        }), 500

@app.route('/api/apply-partial-match', methods=['POST'])
@login_required
def apply_partial_match():
    """Apply a partial match from the queue to update game data"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        game_name = data.get('game_name')
        match_data = data.get('match_data')
        system_name = data.get('system_name')
        
        if not all([game_name, match_data, system_name]):
            return jsonify({'error': 'Missing required fields'}), 400
        
        # Load the current gamelist
        gamelist_path = f'roms/{system_name}/gamelist.xml'
        if not os.path.exists(gamelist_path):
            return jsonify({'error': 'Gamelist not found'}), 404
        
        games = parse_gamelist_xml(gamelist_path)
        
        # Find and update the game
        game_updated = False
        for i, game in enumerate(games):
            if game.get('name') == game_name:
                # Apply the match data
                for field, value in match_data.items():
                    if field in game and value:
                        game[field] = value
                game_updated = True
                break
        
        if not game_updated:
            return jsonify({'error': 'Game not found in gamelist'}), 404
        
        # Save the updated gamelist
        write_gamelist_xml(games, gamelist_path)
        
        # Notify all connected clients about the gamelist update
        # Use the system_name parameter directly (it was already validated)
        notify_gamelist_updated(system_name, len(games))
        notify_game_updated(system_name, game_name, list(match_data.keys()))
        
        return jsonify({
            'success': True,
            'message': f'Game "{game_name}" updated successfully'
        })
        
    except Exception as e:
        print(f"Error in apply_partial_match endpoint: {e}")
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500

@app.route('/api/scrap-launchbox-stop', methods=['POST'])
@login_required
def stop_scraping():
    """Stop the current scraping process"""
    global scraping_in_progress
    
    if not scraping_in_progress:
        return jsonify({'error': 'No scraping in progress'}), 400
    
    scraping_in_progress = False
    return jsonify({'success': True, 'message': 'Scraping stopped'})

@app.route('/api/scrap-launchbox-stream')
@login_required
def stream_scraping_progress():
    """Stream scraping progress using Server-Sent Events (SSE)"""
    def generate():
        global scraping_progress, scraping_stats, scraping_in_progress
        
        # Send initial connection message
        yield f"data: {json.dumps({'type': 'connected', 'message': 'SSE connection established'})}\n\n"
        
        last_progress_length = 0
        
        while scraping_in_progress:
            try:
                current_progress_length = len(scraping_progress)
                
                # Send new progress entries
                if current_progress_length > last_progress_length:
                    print(f"SSE: Sending {current_progress_length - last_progress_length} new progress entries")
                    for i in range(last_progress_length, current_progress_length):
                        progress_data = {
                            'type': 'progress',
                            'message': scraping_progress[i],
                            'total': scraping_stats['total_games'],
                            'current': scraping_stats['processed_games'],
                            'matched': scraping_stats['matched_games'],
                            'updated': scraping_stats['updated_games']
                        }
                        print(f"SSE: Sending progress: {scraping_progress[i][:100]}...")
                        yield f"data: {json.dumps(progress_data)}\n\n"
                    
                    last_progress_length = current_progress_length
                
                # Send stats update
                stats_data = {
                    'type': 'stats',
                    'total': scraping_stats['total_games'],
                    'current': scraping_stats['processed_games'],
                    'matched': scraping_stats['matched_games'],
                    'updated': scraping_stats['updated_games']
                }
                yield f"data: {json.dumps(stats_data)}\n\n"
                
                # Wait a bit before next update
                time.sleep(0.5)
                
            except Exception as e:
                error_data = {
                    'type': 'error',
                    'message': f'SSE Error: {str(e)}'
                }
                yield f"data: {json.dumps(error_data)}\n\n"
                break
        
        # Send completion message
        if not scraping_in_progress:
            print(f"SSE: Scraping completed, checking for remaining progress entries...")
            # Send any remaining progress entries that might have been added
            current_progress_length = len(scraping_progress)
            if current_progress_length > last_progress_length:
                print(f"SSE: Found {current_progress_length - last_progress_length} remaining progress entries")
                for i in range(last_progress_length, current_progress_length):
                    progress_data = {
                        'type': 'progress',
                        'message': scraping_progress[i],
                        'total': scraping_stats['total_games'],
                        'current': scraping_stats['processed_games'],
                        'matched': scraping_stats['matched_games'],
                        'updated': scraping_stats['updated_games']
                    }
                    print(f"SSE: Sending remaining progress: {scraping_progress[i][:100]}...")
                    yield f"data: {json.dumps(progress_data)}\n\n"
            
            completion_data = {
                'type': 'completed',
                'message': 'Scraping completed',
                'total': scraping_stats['total_games'],
                'current': scraping_stats['processed_games'],
                'matched': scraping_stats['matched_games'],
                'updated': scraping_stats['updated_games']
            }
            print(f"SSE: Sending completion message")
            yield f"data: {json.dumps(completion_data)}\n\n"
    
    # Set SSE headers
    response = Response(generate(), mimetype='text/event-stream')
    response.headers['Cache-Control'] = 'no-cache'
    response.headers['Connection'] = 'keep-alive'
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Cache-Control'
    
    return response

@app.route('/api/scrap-launchbox-export-log')
@login_required
def export_scraping_log():
    """Export the complete scraping log"""
    global scraping_progress
    
    log_content = '\n'.join(scraping_progress)
    return Response(log_content, mimetype='text/plain', headers={
        'Content-Disposition': 'attachment; filename=scraping_log.txt'
    })

@app.route('/api/get-top-matches', methods=['POST'])
@login_required
def get_top_matches_endpoint():
    """Get top matches for a specific game name"""
    try:
        data = request.get_json()
        game_name = data.get('game_name')
        system_name = data.get('system_name')
        
        if not game_name or not system_name:
            return jsonify({'error': 'Missing game_name or system_name'}), 400
        
        # Load configuration to get platform mapping
        mapping_config, system_platform_mapping = load_launchbox_config()
        target_platform = system_platform_mapping.get(system_name, {}).get('launchbox', 'Arcade')
        
        # Load Launchbox metadata
        if not os.path.exists(LAUNCHBOX_METADATA_PATH):
            return jsonify({'error': 'Metadata.xml not found'}), 404
        
        metadata_games = parse_launchbox_metadata(LAUNCHBOX_METADATA_PATH, target_platform)
        if not metadata_games:
            return jsonify({'error': 'No metadata found for current platform'}), 404
        
        # Get top matches
        top_matches = get_top_matches(game_name, metadata_games, target_platform, top_n=20, mapping_config=mapping_config)
        
        return jsonify({
            'success': True,
            'game_name': game_name,
            'platform': target_platform,
            'matches': top_matches
        })
        
    except Exception as e:
        print(f"Error in get_top_matches endpoint: {e}")
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500

def load_media_config():
    """Load media configuration from consolidated config.json"""
    return config.get('media', {})

def load_image_mappings():
    """Load image type mappings from consolidated config.json"""
    return {
        'image_type_mappings': config.get('launchbox', {}).get('image_type_mappings', {}),
        'launchbox_image_base_url': config.get('launchbox', {}).get('image_base_url', 'https://images.launchbox-app.com/'),
        'download_settings': config.get('download', {})
    }

def load_region_config():
    """Load region priority configuration from consolidated config.json"""
    return config.get('launchbox', {}).get('region', {})

async def download_launchbox_image_httpx(image_url, local_path, media_type=None, timeout=30, retry_attempts=10, client=None, game_name=None):
    """Download a single image from LaunchBox using HTTPX with HTTP/2 support"""
    import time
    import aiofiles
    
    headers = {
        'accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
        'accept-language': 'fr,en;q=0.9',
        'cache-control': 'no-cache',
        'dnt': '1',
        'pragma': 'no-cache',
        'priority': 'i',
        'referer': 'https://gamesdb.launchbox-app.com/',
        'sec-ch-ua': '"Not;A=Brand";v="99", "Google Chrome";v="139", "Chromium";v="139"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Linux"',
        'sec-fetch-dest': 'image',
        'sec-fetch-mode': 'no-cors',
        'sec-fetch-site': 'same-site',
        'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36'
    }
    
    filename = os.path.basename(local_path)
    media_info = f" [{media_type}]" if media_type else ""
    
    # Create prefix for logging with game name and media type
    prefix_parts = []
    if game_name:
        prefix_parts.append(game_name)
    if media_type:
        prefix_parts.append(media_type)
    
    log_prefix = f"[{' | '.join(prefix_parts)}]" if prefix_parts else ""
    
    print(f"DEBUG: {log_prefix} Starting download: {image_url} -> {local_path}")
    
    for attempt in range(retry_attempts):
        try:
            if attempt > 0:
                import threading
                threading.Thread(target=update_task_progress, args=(f"{log_prefix} 🔄 Retry {attempt + 1}/{retry_attempts}",), daemon=True).start()
            
            # Ensure directory exists
            print(f"DEBUG: {log_prefix} Creating directory: {os.path.dirname(local_path)}")
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            # Start timing for HTTP request with detailed metrics
            http_start_time = time.time()
            import threading
            threading.Thread(target=update_task_progress, args=(f"{log_prefix} ⏱️  Starting HTTPX HTTP/2 request to: {os.path.basename(image_url)} (attempt {attempt + 1}/{retry_attempts})",), daemon=True).start()
            
            print(f"DEBUG: {log_prefix} Making HTTP request to: {image_url}")
            # Use HTTPX client for async download with HTTP/2
            response = await client.get(image_url, headers=headers)
            print(f"DEBUG: {log_prefix} HTTP response status: {response.status_code}")
            response.raise_for_status()
            
            # Get file size from response headers if available
            content_length = response.headers.get('content-length')
            if content_length:
                print(f"DEBUG: {log_prefix} Content-Length: {content_length} bytes")
            
            print(f"DEBUG: {log_prefix} Starting file write to: {local_path}")
            # Download the file
            bytes_written = 0
            async with aiofiles.open(local_path, 'wb') as f:
                async for chunk in response.aiter_bytes(chunk_size=8192):
                    await f.write(chunk)
                    bytes_written += len(chunk)
            
            print(f"DEBUG: {log_prefix} File write completed. Bytes written: {bytes_written}")
            
            # Verify file was created and has content
            if os.path.exists(local_path):
                file_size = os.path.getsize(local_path)
                print(f"DEBUG: {log_prefix} File verification: exists={True}, size={file_size} bytes")
                if file_size > 0:
                    print(f"DEBUG: {log_prefix} ✅ Download successful: {filename} ({file_size} bytes)")
                    return True, f"Downloaded {filename} ({file_size} bytes)"
                else:
                    print(f"DEBUG: {log_prefix} ❌ File created but empty: {local_path}")
                    return False, f"File created but empty: {filename}"
            else:
                print(f"DEBUG: {log_prefix} ❌ File not created: {local_path}")
                return False, f"File not created: {filename}"
            
        except httpx.RequestError as e:
            print(f"DEBUG: {log_prefix} HTTP request error: {e}")
            if attempt < retry_attempts - 1:
                # Exponential backoff: 1s, 2s, 4s, 8s, etc. (capped at 10s)
                retry_delay = min(2 ** attempt, 10)
                import threading
                threading.Thread(target=update_task_progress, args=(f"{log_prefix} ⏳ Waiting {retry_delay}s before retry {attempt + 1}/{retry_attempts}",), daemon=True).start()
                await asyncio.sleep(retry_delay)
            else:
                print(f"DEBUG: {log_prefix} ❌ Connection failed after {retry_attempts} attempts: {e}")
                return False, f"Connection failed after {retry_attempts} attempts: {e}"
        except Exception as e:
            print(f"DEBUG: {log_prefix} ❌ Unexpected error: {e}")
            import traceback
            traceback.print_exc()
            return False, f"Error: {e}"
    
    print(f"DEBUG: {log_prefix} ❌ Failed after {retry_attempts} attempts")
    return False, f"Failed after {retry_attempts} attempts"

def get_region_priority_from_game_name(game_name, default_priority):
    """
    Extract region information from game name (in parentheses) and adjust priority.
    If no region is found or doesn't match known regions, return default priority.
    
    Args:
        game_name: The game name to analyze
        default_priority: Default region priority list from config
    
    Returns:
        List of regions in priority order, with detected region moved to front
    """
    if not game_name:
        return default_priority
    
    import re
    
    # Common region mappings
    region_mappings = {
        # North America variations
        'usa': 'North America',
        'us': 'North America', 
        'america': 'North America',
        'north america': 'North America',
        'na': 'North America',
        'canada': 'North America',
        'canadian': 'North America',
        
        # Europe variations
        'europe': 'Europe',
        'eu': 'Europe',
        'european': 'Europe',
        'uk': 'Europe',
        'england': 'Europe',
        'france': 'Europe',
        'french': 'Europe',
        'germany': 'Europe',
        'german': 'Europe',
        'italy': 'Europe',
        'italian': 'Europe',
        'spain': 'Europe',
        'spanish': 'Europe',
        'netherlands': 'Europe',
        'dutch': 'Europe',
        'sweden': 'Europe',
        'swedish': 'Europe',
        'norway': 'Europe',
        'norwegian': 'Europe',
        'denmark': 'Europe',
        'danish': 'Europe',
        'finland': 'Europe',
        'finnish': 'Europe',
        'poland': 'Europe',
        'polish': 'Europe',
        'russia': 'Europe',
        'russian': 'Europe',
        
        # Japan variations
        'japan': 'Japan',
        'japanese': 'Japan',
        'jp': 'Japan',
        'jpn': 'Japan',
        
        # World variations
        'world': 'World',
        'international': 'World',
        'intl': 'World',
        'global': 'World'
    }
    
    # Look for text in parentheses
    parentheses_match = re.search(r'\(([^)]+)\)', game_name)
    if not parentheses_match:
        return default_priority
    
    region_text = parentheses_match.group(1).lower().strip()
    
    # Try to find a matching region
    detected_region = None
    for key, region in region_mappings.items():
        if key in region_text:
            detected_region = region
            break
    
    # If no region detected, return default priority
    if not detected_region:
        return default_priority
    
    # Create new priority list with detected region moved to front
    new_priority = [detected_region]
    
    # Add other regions in their original order, excluding the detected one
    for region in default_priority:
        if region != detected_region:
            new_priority.append(region)
    
    return new_priority

async def get_game_images_from_launchbox_async(game_launchbox_id, image_config, system_path, rom_filename, game_name=None, current_game_data=None, force_download=False, media_config=None, region_config=None, selected_fields=None):
    """Get available images for a game from LaunchBox metadata and download them using aiohttp"""
    import time
    
    # Create game name prefix for logging
    game_prefix = f"[{game_name or rom_filename}]" if game_name or rom_filename else ""
    

    
    downloaded_images = []
    # Use passed configs (already validated at task start)
    media_mappings = media_config.get('mappings', {})

    
    # Check which fields need images based on current gamelist data
    fields_to_download = []
    if current_game_data and not force_download:

        for field_name in image_config.get('image_type_mappings', {}).values():
            current_value = current_game_data.get(field_name)
            # Consider field empty if it's None, empty string, or just whitespace
            if not current_value or (isinstance(current_value, str) and current_value.strip() == ''):
                fields_to_download.append(field_name)
        
        if not fields_to_download:
            return []
        
    else:

        fields_to_download = list(image_config.get('image_type_mappings', {}).values())
    
    # Filter fields based on selected_fields
    if selected_fields:
        # Create reverse mapping from gamelist field to LaunchBox image type
        field_to_launchbox_type = {}
        for launchbox_type, gamelist_field in image_config.get('image_type_mappings', {}).items():
            field_to_launchbox_type[gamelist_field] = launchbox_type
        
        # Filter fields_to_download to only include selected media fields
        selected_media_fields = [field for field in selected_fields if field in field_to_launchbox_type.values()]
        fields_to_download = [field for field in fields_to_download if field_to_launchbox_type.get(field) in selected_media_fields]
    
    try:
        # Get GameImage entries from consolidated cache (already loaded)
        all_game_images = (global_metadata_cache.get(game_launchbox_id) or {}).get('images', [])
        
        # Use region configuration (already loaded at task start)
        default_region_priority = region_config.get('priority', ['World', 'North America', 'Europe', 'Japan'])
        
        # Try to extract region from game name and adjust priority
        region_priority = get_region_priority_from_game_name(game_name, default_region_priority)
        
        # Log region priority adjustment if it changed
        if region_priority != default_region_priority:
            print(f"{game_prefix} 🌍 Region priority adjusted based on game name: {region_priority}")
        else:
            print(f"{game_prefix} 🌍 Using default region priority: {region_priority}")
        
        # Filter GameImage entries to only include types that map to fields we need
        image_type_mappings = image_config.get('image_type_mappings', {})
        needed_image_types = set()
        
        # Create reverse mapping from gamelist field to LaunchBox image type
        field_to_launchbox_type = {}
        for launchbox_type, gamelist_field in image_type_mappings.items():
            if gamelist_field in fields_to_download:
                needed_image_types.add(launchbox_type)
                field_to_launchbox_type[gamelist_field] = launchbox_type
        
        
        # Filter and group only the needed images by type
        images_by_type = {}
        filtered_count = 0
        
        for game_image in all_game_images:
            image_type = game_image.find('Type')
            if image_type is None or not image_type.text:
                continue
                
            image_type_text = image_type.text.strip()
            
            # Only process image types that map to fields we need
            if image_type_text not in needed_image_types:
                continue
                
            filename = game_image.find('FileName')
            region = game_image.find('Region')
            
            if filename is not None and filename.text:
                filename_text = filename.text.strip()
                region_text = region.text.strip() if region is not None and region.text else 'Unknown'
                
                if image_type_text not in images_by_type:
                    images_by_type[image_type_text] = []
                
                images_by_type[image_type_text].append({
                    'filename': filename_text,
                    'region': region_text,
                    'element': game_image
                })
                filtered_count += 1
        
        
        # Prepare download tasks for parallel execution
        download_tasks = []
        
        for i, (image_type_text, type_images) in enumerate(images_by_type.items()):
            # Map image type to gamelist field (we already know this mapping exists)
            gamelist_field = image_type_mappings.get(image_type_text)
            
            # Sort images by region priority
            sorted_images = []
            for img in type_images:
                try:
                    region_index = region_priority.index(img['region'])
                except ValueError:
                    region_index = len(region_priority)  # Unknown regions go last
                sorted_images.append((region_index, img))
            
            sorted_images.sort(key=lambda x: x[0])  # Sort by region priority index
            
            # Select the best image (first in priority order)
            best_image = sorted_images[0][1]
            
            # Map gamelist field to media directory using media_mappings
            media_directory = None
            for directory, field in media_mappings.items():
                if field == gamelist_field:
                    media_directory = directory
                    break
            
            if not media_directory:
                media_directory = gamelist_field  # fallback to field name if no mapping found
            
            # Construct download URL and local path
            base_url = image_config.get('launchbox_image_base_url', 'https://images.launchbox-app.com/')
            download_url = base_url + best_image['filename']
            file_extension = os.path.splitext(best_image['filename'])[1]
            local_filename = f"{rom_filename}{file_extension}"
            local_path = os.path.join(system_path, 'media', media_directory, local_filename)
            
            # Create media directory if it doesn't exist
            media_dir = os.path.join(system_path, 'media', media_directory)
            os.makedirs(media_dir, exist_ok=True)
            
            # Add download task to the list
            download_tasks.append({
                'gamelist_field': gamelist_field,
                'download_url': download_url,
                'local_path': local_path,
                'media_type': image_type_text,
                'region': best_image['region'],
                'filename': best_image['filename'],
                'media_directory': media_directory,
                'local_filename': local_filename,
                'game_name': game_name or rom_filename
            })
        
        
        import threading
        import queue
        
        # Create thread-safe queues for producer-consumer pattern
        download_queue = queue.Queue()  # Producer fills this with download tasks
        result_queue = queue.Queue()    # Consumer puts results here
        shutdown_event = threading.Event()  # Signal to shutdown consumer thread
        
        # Create HTTPX client configuration with HTTP/2 support
        limits = httpx.Limits(
            max_connections=20,  # Total connection pool size
            max_keepalive_connections=20,  # Max keepalive connections
            keepalive_expiry=30.0  # Keepalive expiry in seconds
        )
        
        timeout = httpx.Timeout(
            timeout=60.0,  # Total timeout
            connect=10.0,  # Connect timeout
            read=30.0      # Read timeout
        )
        
        # Create HTTPX headers for image downloads
        headers = {
            'accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
            'accept-language': 'fr,en;q=0.9',
            'cache-control': 'no-cache',
            'dnt': '1',
            'pragma': 'no-cache',
            'priority': 'i',
            'referer': 'https://gamesdb.launchbox-app.com/',
            'sec-ch-ua': '"Not;A=Brand";v="99", "Google Chrome";v="139", "Chromium";v="139"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Linux"',
            'sec-fetch-dest': 'image',
            'sec-fetch-mode': 'no-cors',
            'sec-fetch-site': 'same-site',
            'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36'
        }
        
        # No authentication - use unauthenticated session
        cookies = None
        
        # Use global download manager instead of creating new consumer threads
        from download_manager import get_download_manager
        
        download_manager = get_download_manager()
        # Start the download manager with cookies if this is the first time
        if cookies:
            download_manager.start(cookies)

        
        # Add tasks to the global download manager
        for task in download_tasks:
            # Log download attempt asynchronously (non-blocking)
            gamelist_field = task.get('gamelist_field', 'unknown')
            region = task.get('region', 'unknown')
            filename = task.get('filename', 'unknown')
            # Use threading for non-blocking logging
            import threading
            log_message = f"{game_prefix} Downloading {gamelist_field} ('{region}')"
            threading.Thread(target=update_task_progress, args=(log_message,), daemon=True).start()
            download_manager.add_task(task)
        
        
        # Collect results from the global download manager with stop checking
        results = []
        try:
            results = download_manager.wait_for_completion(len(download_tasks))
        except Exception as e:
            if is_task_stopped():
                import threading
                threading.Thread(target=update_task_progress, args=("🛑 Task stopped by user - stopping download manager",), daemon=True).start()
                download_manager.stop()
                return []
            else:
                raise e
        
        # Process results
        for result in results:
            if result and result.get('success'):
                # Log success message
#                gamelist_field = result.get('gamelist_field', 'unknown')
#                local_filename = result.get('local_path', '').split('/')[-1] if result.get('local_path') else 'unknown'
#                update_task_progress(f"{game_prefix} ✅ Success: {gamelist_field} → {local_filename}")
                
                downloaded_images.append({
                    'field': result['gamelist_field'],
                    'local_path': result['local_path'],
                    'message': result['message']
                })
            elif result:
                # Log failure message asynchronously (non-blocking)
                gamelist_field = result.get('gamelist_field', 'unknown')
                error_message = result.get('message', 'Unknown error')
                # Use threading for non-blocking logging
                import threading
                log_message = f"{game_prefix} ❌ Failed: {error_message}"
                threading.Thread(target=update_task_progress, args=(log_message,), daemon=True).start()
        
        return downloaded_images
        
    except Exception as e:
        print(f"Error processing LaunchBox images for game {game_launchbox_id}: {e}")
        if game_name or rom_filename:
            game_prefix = f"[{game_name or rom_filename}]"
            import threading
            threading.Thread(target=update_task_progress, args=(f"{game_prefix} ❌ Error: {e}",), daemon=True).start()
        return downloaded_images

def get_game_images_from_launchbox(game_launchbox_id, image_config, system_path, rom_filename, game_name=None, current_game_data=None, force_download=False, media_config=None, region_config=None, selected_fields=None):
    """Synchronous wrapper for get_game_images_from_launchbox_async"""
    import asyncio
    
    # Create a new event loop for this thread if needed
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    # Run the async function in the event loop
    return loop.run_until_complete(
        get_game_images_from_launchbox_async(
            game_launchbox_id, image_config, system_path, rom_filename, 
            game_name, current_game_data, force_download, media_config, region_config, selected_fields
        )
    )

def scan_media_files(system_name):
    """Scan media files for a specific system and update gamelist.xml"""
    global current_task_id
    
    try:
        if not current_task_id or current_task_id not in tasks:
            print("Error: No active task found for media scan")
            return {'error': 'No active task found'}
        
        task = tasks[current_task_id]
        
        # Initialize task state
        task.update_progress("Starting media scan")
        
        media_config = load_media_config()
        if not media_config:
            task.update_progress("Failed to load media configuration")
            return {'error': 'Failed to load media configuration'}
        
        system_path = os.path.join(ROMS_FOLDER, system_name)
        task.update_progress(f"System path: {system_path}")
        if not os.path.exists(system_path):
            task.update_progress(f"System path does not exist: {system_path}")
            return {'error': 'System not found'}
        
        # Ensure gamelist exists in var/gamelists, copying from roms/ if needed
        gamelist_path = ensure_gamelist_exists(system_name)
        task.update_progress(f"Gamelist path: {gamelist_path}")
        if not os.path.exists(gamelist_path):
            task.update_progress(f"Gamelist does not exist: {gamelist_path}")
            return {'error': 'Gamelist not found'}
        
        # Parse existing gamelist
        games = parse_gamelist_xml(gamelist_path)
        if not games:
            task.update_progress("No games found in gamelist")
            return {'error': 'No games found in gamelist'}
        
        task.update_progress(f"Found {len(games)} games in gamelist")
        
        # Load media mappings
        media_mappings = media_config.get('mappings', {})
        media_extensions = media_config.get('extensions', {})
        task.update_progress(f"Media mappings: {media_mappings}")
        task.update_progress(f"Media extensions: {media_extensions}")
        
        # Track changes
        updated_games = 0
        removed_media = 0
        
        # Check media directory structure
        media_base_dir = os.path.join(system_path, 'media')
        task.update_progress(f"Media base directory: {media_base_dir}")
        if os.path.exists(media_base_dir):
            task.update_progress(f"Media base directory exists, contents: {os.listdir(media_base_dir)}")
        else:
            task.update_progress(f"Media base directory does not exist: {media_base_dir}")
        
        # Process each game
        for i, game in enumerate(games):
            game_updated = False
            rom_path = game.get('path', '')
            
            if not rom_path:
                continue
            
            # Extract ROM filename without extension
            rom_filename = os.path.splitext(os.path.basename(rom_path))[0]
            
            # Ensure all expected media fields exist in the game data
            # Use the same field names that the scraper expects (from consolidated config.json)
            scraper_media_fields = ['image', 'video', 'marquee', 'wheel', 'boxart', 'thumbnail', 'screenshot', 'cartridge', 'fanart', 'titleshot', 'manual', 'boxback', 'extra1', 'mix']
            task.update_progress(f"Checking media fields for '{game.get('name', 'Unknown')}': {list(game.keys())}")
            for field in scraper_media_fields:
                if field not in game:
                    game[field] = ''  # Initialize missing media fields as empty
                    game_updated = True
                    task.update_progress(f"Added missing media field '{field}' for '{game.get('name', 'Unknown')}'")
                elif game[field] is None:
                    game[field] = ''  # Convert None to empty string
                    game_updated = True
                    task.update_progress(f"Converted None to empty string for field '{field}' in '{game.get('name', 'Unknown')}'")
            
            # Check each media type
            for media_type, gamelist_field in media_mappings.items():
                media_dir = os.path.join(system_path, 'media', media_type)
                
                # Look for media files with matching name
                found_media = None
                if os.path.exists(media_dir):
                    for ext in media_extensions.get(media_type, []):
                        media_file = os.path.join(media_dir, rom_filename + ext)
                        if os.path.exists(media_file):
                            found_media = f'./media/{media_type}/{rom_filename}{ext}'
                            break
                
                # Update gamelist field - only update if the path actually changes
                current_media = game.get(gamelist_field, '')
                if found_media:
                    # Only update if the media path is different from current
                    if current_media != found_media:
                        game[gamelist_field] = found_media
                        game_updated = True
                        # Always log media updates, regardless of game number
                        task.update_progress(f"Updated {gamelist_field} for '{game.get('name', 'Unknown')}': {found_media}")
                elif current_media:
                    # Remove media reference if file doesn't exist (regardless of whether directory exists)
                    game[gamelist_field] = ''  # Set to empty string to preserve the field
                    game_updated = True
                    removed_media += 1
                    # Always log media removals, regardless of game number
                    task.update_progress(f"Removed {gamelist_field} for '{game.get('name', 'Unknown')}': {current_media}")
            
            # Also check for orphaned media entries that might not be in the media_mappings
            # This handles cases where the gamelist has media fields that aren't in the current config
            orphaned_media_fields = ['image', 'video', 'marquee', 'wheel', 'boxart', 'thumbnail', 'screenshot', 'cartridge', 'fanart', 'titleshot', 'manual', 'boxback', 'extra1', 'mix']
            
            for field in orphaned_media_fields:
                if field in game and game[field]:
                    # Check if this media file actually exists
                    media_path = game[field]
                    if media_path.startswith('./media/'):
                        # Extract the relative path and check if file exists
                        relative_path = media_path[2:]  # Remove './'
                        full_path = os.path.join(system_path, relative_path)
                        if not os.path.exists(full_path):
                            # Media file doesn't exist, remove the reference
                            game[field] = ''
                            game_updated = True
                            removed_media += 1
                            task.update_progress(f"Removed orphaned {field} for '{game.get('name', 'Unknown')}': {media_path}")
            
            if game_updated:
                updated_games += 1
            
            # Add progress indicator every 100 games
            if (i + 1) % 100 == 0:
                task.update_progress(f"Processed {i + 1} / {len(games)} games...")
        
        task.update_progress(f"Scan completed. Updated {updated_games} games, removed {removed_media} invalid media references.")
        
        # Always save the gamelist (even if no updates, to ensure consistency)
        try:
            write_gamelist_xml(games, gamelist_path)
            task.update_progress("Gamelist saved successfully")
            
            # Notify all connected clients about the gamelist update
            notify_gamelist_updated(system_name, len(games))
            
        except Exception as e:
            task.update_progress(f"ERROR saving gamelist: {e}")
            return {'error': f'Failed to save gamelist: {str(e)}'}
        
        return {
            'success': True,
            'message': f'Media scan completed. Updated {updated_games} games, removed {removed_media} invalid media references.',
            'updated_games': updated_games,
            'removed_media': removed_media,
            'total_games': len(games)
        }
        
    except Exception as e:
        print(f"Error scanning media files: {e}")
        import traceback
        traceback.print_exc()
        
        return {'error': f'Media scan failed: {str(e)}'}

def save_gamelist_xml(file_path, games):
    """Save games list to gamelist.xml file"""
    try:
        print(f"Saving gamelist.xml to {file_path} with {len(games)} games")
        
        # Deduplicate by path before saving to avoid duplicate entries
        games = _dedupe_games_by_path(games)

        # Create root element
        root = ET.Element('gameList')
        
        # Add each game
        for i, game in enumerate(games):
            game_elem = ET.SubElement(root, 'game')
            
            # Add all fields - include empty values for media fields to ensure they're saved
            for field, value in game.items():
                # Always include media-related fields, even if empty
                if field in ['image', 'video', 'marquee', 'wheel', 'boxart', 'thumbnail', 'screenshot', 'cartridge', 'fanart', 'titleshot', 'manual', 'boxback', 'extra1', 'mix']:
                    elem = ET.SubElement(game_elem, field)
                    elem.text = str(value) if value else ''
                elif value:  # For non-media fields, only add if they have values
                    elem = ET.SubElement(game_elem, field)
                    elem.text = str(value)
        
        # Create XML tree and save
        tree = ET.ElementTree(root)
        
        # Create backup before saving
        backup_path = file_path + '.backup.' + str(int(time.time()))
        if os.path.exists(file_path):
            import shutil
            shutil.copy2(file_path, backup_path)
            print(f"Created backup: {backup_path}")
        
        # Save the file with proper formatting
        # First write to a temporary string to get the raw XML
        import io
        xml_string = io.StringIO()
        tree.write(xml_string, encoding='unicode', xml_declaration=True)
        xml_content = xml_string.getvalue()
        
        # Format the XML content for better readability
        formatted_xml = format_xml_for_readability(xml_content)
        
        # Write the formatted XML to file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(formatted_xml)
        print(f"Successfully saved gamelist.xml with {len(games)} games")
        
        # Verify the file was written
        if os.path.exists(file_path):
            file_size = os.path.getsize(file_path)
            print(f"File saved successfully. Size: {file_size} bytes")
        else:
            print("ERROR: File was not created!")
            
    except Exception as e:
        print(f"Error saving gamelist.xml: {e}")
        import traceback
        traceback.print_exc()
        raise

def format_xml_for_readability(xml_content):
    """Format XML content to be more human-readable with proper line breaks and indentation"""
    try:
        # Parse the XML content
        root = ET.fromstring(xml_content)
        
        # Create a new formatted XML string
        formatted_lines = ['<?xml version="1.0" encoding="utf-8"?>', '']
        
        def escape_xml_text(text):
            """Properly escape XML special characters in text content"""
            if not text:
                return text
            # Convert to string and let ElementTree handle XML escaping
            return str(text)
        
        def format_element(element, indent_level=0):
            indent = '  ' * indent_level
            tag = element.tag
            
            # Handle text content
            if element.text and element.text.strip():
                text = element.text.strip()
                escaped_text = escape_xml_text(text)
                
                # If text is long, add line breaks for readability
                if len(text) > 80:
                    # Split long text at word boundaries
                    words = text.split()
                    lines = []
                    current_line = ''
                    for word in words:
                        if len(current_line + word) > 80:
                            if current_line:
                                lines.append(current_line.strip())
                            current_line = word
                        else:
                            current_line += ' ' + word if current_line else word
                    if current_line:
                        lines.append(current_line.strip())
                    
                    # Format multi-line text with proper escaping
                    formatted_lines.append(f'{indent}<{tag}>')
                    for line in lines:
                        escaped_line = escape_xml_text(line)
                        formatted_lines.append(f'{indent}  {escaped_line}')
                    formatted_lines.append(f'{indent}</{tag}>')
                else:
                    formatted_lines.append(f'{indent}<{tag}>{escaped_text}</{tag}>')
            else:
                # Empty element or element with children
                if len(element) == 0:
                    formatted_lines.append(f'{indent}<{tag} />')
                else:
                    formatted_lines.append(f'{indent}<{tag}>')
                    for child in element:
                        format_element(child, indent_level + 1)
                    formatted_lines.append(f'{indent}</{tag}>')
        
        # Format the root element
        format_element(root)
        
        return '\n'.join(formatted_lines)
        
    except Exception as e:
        print(f"Error formatting XML: {e}")
        # Return original content if formatting fails
        return xml_content



@app.route('/api/rom-system/<system_name>/scan-media', methods=['POST'])
@login_required
def scan_media_endpoint(system_name):
    """Scan media files for a specific system"""
    global current_task_id
    
    # Check if another task is already running
    can_start, message = can_start_task('media_scan')
    if not can_start:
        # Queue the task if it can't start immediately
        queued, queue_message = queue_task('media_scan', {
            'system_name': system_name
        })
        return jsonify({
            'error': message,
            'queued': queued,
            'queue_message': queue_message
        }), 409  # Conflict status
    
    try:
        # Create and start new task
        task = create_task('media_scan', {
            'system_name': system_name
        })
        current_task_id = task.id
        task.start()
        
        # Start task in background thread
        thread = threading.Thread(target=run_media_scan_task, args=(system_name,))
        thread.daemon = True
        thread.start()
        
        return jsonify({'success': True, 'message': 'Media scan started'})
    except Exception as e:
        return jsonify({'error': f'Media scan failed: {str(e)}'}), 500

@app.route('/api/cache/statistics')
@login_required
def cache_statistics_endpoint():
    """Get metadata cache statistics"""
    try:
        if not global_metadata_cache_loaded:
            return jsonify({
                'status': 'loading',
                'message': 'Cache is currently loading in background...',
                'total_database_ids': 0,
                'total_games': 0,
                'total_images': 0,
                'games_with_images': 0,
                'games_with_alternate_names': 0
            })
        
        stats = get_cache_statistics()
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': f'Failed to get cache statistics: {str(e)}'}), 500

@app.route('/api/cache/reload', methods=['POST'])
@login_required
def reload_cache_endpoint():
    """Reload the metadata cache"""
    global global_metadata_cache_loaded, global_metadata_cache
    
    try:
        # Clear the cache
        global_metadata_cache_loaded = False
        global_metadata_cache = {}
        
        # Reload the cache
        result = load_metadata_cache()
        
        return jsonify({
            'message': 'Cache reloaded successfully',
            'statistics': get_cache_statistics()
        })
    except Exception as e:
        return jsonify({'error': f'Failed to reload cache: {str(e)}'}), 500

@app.route('/api/cache/metadata-info')
@login_required
def metadata_info_endpoint():
    """Get metadata.xml file information"""
    try:
        metadata_path = LAUNCHBOX_METADATA_PATH
        
        if not os.path.exists(metadata_path):
            return jsonify({
                'success': False,
                'error': 'Metadata.xml file not found',
                'metadata_date': None
            })
        
        # Get file modification time
        file_stat = os.stat(metadata_path)
        modification_time = time.ctime(file_stat.st_mtime)
        
        # Ensure cache is loaded before getting statistics
        if not global_metadata_cache_loaded:
            print(f"DEBUG: Loading metadata cache...")
            cache_data = load_metadata_cache()
            print(f"DEBUG: Cache loaded. global_metadata_cache_loaded: {global_metadata_cache_loaded}")
        else:
            # Get current cache data derived from consolidated cache
            cache_data = {
                'gameimage_cache': {k: v.get('images', []) for k, v in global_metadata_cache.items()},
                'games_cache': {k: v.get('game') for k, v in global_metadata_cache.items()},
                'alternate_names_cache': {k: v.get('alternate_names', []) for k, v in global_metadata_cache.items()}
            }
        
        # Get cache statistics from cache data
        games_count = len(cache_data['games_cache']) if cache_data['games_cache'] else 0
        alt_names_count = len(cache_data['alternate_names_cache']) if cache_data['alternate_names_cache'] else 0
        
        # Count total individual images across all games (not just games with images)
        if cache_data['gameimage_cache']:
            game_images_count = sum(len(images) for images in cache_data['gameimage_cache'].values())
        else:
            game_images_count = 0
        
        print(f"DEBUG: Cache stats - games: {games_count}, alt_names: {alt_names_count}, images: {game_images_count}")
        print(f"DEBUG: Cache data keys: {list(cache_data.keys())}")
        print(f"DEBUG: Games cache type: {type(cache_data['games_cache'])}, length: {len(cache_data['games_cache']) if cache_data['games_cache'] else 'None'}")
        
        return jsonify({
            'success': True,
            'metadata_date': modification_time,
            'file_size': file_stat.st_size,
            'cache_stats': {
                'games_count': games_count,
                'alt_names_count': alt_names_count,
                'game_images_count': game_images_count
            }
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to get metadata info: {str(e)}'}), 500

@app.route('/api/cache/update-metadata', methods=['POST'])
@login_required
def update_metadata_endpoint():
    """Update metadata.xml to the latest version from Launchbox"""
    try:
        import zipfile
        import tempfile
        
        # Download the latest metadata
        metadata_url = 'http://gamesdb.launchbox-app.com/Metadata.zip'
        
        # Create temporary directory for download
        with tempfile.TemporaryDirectory() as temp_dir:
            zip_path = os.path.join(temp_dir, 'Metadata.zip')
            
            # Download the zip file
            response = requests.get(metadata_url, stream=True)
            response.raise_for_status()
            
            with open(zip_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # Extract the zip file
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                print(f"DEBUG: Zip contents: {zip_ref.namelist()}")
                zip_ref.extractall(temp_dir)
                print(f"DEBUG: Extracted files in temp_dir: {os.listdir(temp_dir)}")
            
            # Look specifically for Metadata.xml file
            metadata_xml_path = os.path.join(temp_dir, 'Metadata.xml')
            if not os.path.exists(metadata_xml_path):
                # Fallback: look for any XML file if Metadata.xml not found
                metadata_files = [f for f in os.listdir(temp_dir) if f.endswith('.xml')]
                if not metadata_files:
                    return jsonify({'error': 'No Metadata.xml or XML file found in downloaded zip'}), 400
                extracted_metadata = os.path.join(temp_dir, metadata_files[0])
                print(f"DEBUG: Using fallback XML file: {metadata_files[0]}")
            else:
                extracted_metadata = metadata_xml_path
                print(f"DEBUG: Found Metadata.xml file")
            
            # Backup existing metadata if it exists
            if os.path.exists(LAUNCHBOX_METADATA_PATH):
                backup_path = f"{LAUNCHBOX_METADATA_PATH}.backup.{int(time.time())}"
                shutil.copy2(LAUNCHBOX_METADATA_PATH, backup_path)
            
            # Copy the new metadata file
            print(f"DEBUG: Copying {extracted_metadata} to {LAUNCHBOX_METADATA_PATH}")
            print(f"DEBUG: Source file size: {os.path.getsize(extracted_metadata)} bytes")
            shutil.copy2(extracted_metadata, LAUNCHBOX_METADATA_PATH)
            print(f"DEBUG: Destination file size: {os.path.getsize(LAUNCHBOX_METADATA_PATH)} bytes")
            
            # Clear the cache to force reload
            global global_metadata_cache_loaded, global_metadata_cache
            global_metadata_cache_loaded = False
            global_metadata_cache = {}
            
            # Clear the LaunchBox platforms cache since metadata was updated
            clear_launchbox_platforms_cache()
            
            return jsonify({
                'success': True,
                'message': 'Metadata.xml updated successfully',
                'backup_created': os.path.exists(backup_path) if 'backup_path' in locals() else False
            })
            
    except Exception as e:
        app.logger.error(f'Error updating metadata: {str(e)}')
        return jsonify({'error': f'Failed to update metadata: {str(e)}'}), 500

@app.route('/api/delete-file', methods=['POST'])
@login_required
def delete_file():
    """Delete a file from the filesystem"""
    app.logger.info(f'Delete file endpoint called with data: {request.get_json()}')
    try:
        data = request.get_json()
        if not data or 'file_path' not in data:
            return jsonify({'error': 'file_path is required'}), 400
        
        file_path = data['file_path']
        
        # Convert relative path to absolute path relative to app root
        if not os.path.isabs(file_path):
            file_path = os.path.join(app.root_path, file_path)
        
        # Security check: ensure the file path is within the allowed directories
        allowed_dirs = [
            os.path.abspath(os.path.join(app.root_path, 'roms')),
            os.path.abspath(os.path.join(app.root_path, 'media'))
        ]
        
        file_abs_path = os.path.abspath(file_path)
        is_allowed = False
        
        for allowed_dir in allowed_dirs:
            if file_abs_path.startswith(allowed_dir):
                is_allowed = True
                break
        
        if not is_allowed:
            return jsonify({'error': 'Access denied: file path not in allowed directories'}), 403
        
        # Check if file exists using the absolute path
        if not os.path.exists(file_abs_path):
            return jsonify({'error': f'File not found: {file_abs_path}'}), 404
        
        # Delete the file using the absolute path
        os.remove(file_abs_path)
        
        # Log the deletion
        app.logger.info(f'Deleted file: {file_abs_path}')
        
        return jsonify({'success': True, 'message': f'File deleted: {file_abs_path}'})
        
    except Exception as e:
        app.logger.error(f'Error deleting file: {str(e)}')
        return jsonify({'error': f'Failed to delete file: {str(e)}'}), 500



@app.route('/api/rom-system/<system_name>/game/<game_id>/upload-media', methods=['POST'])
@login_required
def upload_game_media(system_name, game_id):
    """Upload a media file for a specific game"""
    try:
        # Check if system exists
        system_path = os.path.join(ROMS_FOLDER, system_name)
        if not os.path.exists(system_path):
            return jsonify({'error': 'System not found'}), 404
        
        # Check if game exists in gamelist
        gamelist_path = os.path.join(system_path, 'gamelist.xml')
        if not os.path.exists(gamelist_path):
            return jsonify({'error': 'Gamelist not found'}), 404
        
        # Parse gamelist to find the game
        games = parse_gamelist_xml(gamelist_path)
        # Convert game_id to int for comparison since URL parameters are strings
        try:
            game_id_int = int(game_id)
        except ValueError:
            return jsonify({'error': 'Invalid game ID format'}), 400
        
        game = next((g for g in games if g.get('id') == game_id_int), None)
        if not game:
            return jsonify({'error': f'Game not found with ID {game_id_int}'}), 404
        
        # Check if file was uploaded
        if 'media_file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['media_file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Get media field from form data
        media_field = request.form.get('media_field')
        if not media_field:
            return jsonify({'error': 'Media field not specified'}), 400
        
        # Validate media field
        valid_media_fields = ['boxart', 'screenshot', 'marquee', 'wheel', 'video', 'thumbnail', 'cartridge', 'fanart', 'title', 'manual', 'boxback', 'box2d']
        if media_field not in valid_media_fields:
            return jsonify({'error': 'Invalid media field'}), 400
        
        # Get the ROM filename without extension for use as media filename
        rom_path = game.get('path', '')
        rom_filename = os.path.splitext(os.path.basename(rom_path))[0] if rom_path else game.get('name', 'unknown')
        
        # Create category-specific media directory
        category_dir = os.path.join(system_path, 'media', media_field)
        if not os.path.exists(category_dir):
            os.makedirs(category_dir)
        
        # Generate filename using ROM name and original extension
        file_extension = os.path.splitext(file.filename)[1].lower()
        new_filename = f"{rom_filename}{file_extension}"
        file_path = os.path.join(category_dir, new_filename)
        
        # Check if file already exists and handle conflicts
        counter = 1
        original_file_path = file_path
        while os.path.exists(file_path):
            name_part = os.path.splitext(rom_filename)[0]
            new_filename = f"{name_part}_{counter}{file_extension}"
            file_path = os.path.join(category_dir, new_filename)
            counter += 1
        
        # Save the uploaded file
        file.save(file_path)
        
        # Update the game object in memory with relative path
        relative_path = os.path.relpath(file_path, system_path)
        game[media_field] = relative_path
        
        # Update the gamelist.xml file
        write_gamelist_xml(games, gamelist_path)
        
        # Notify all connected clients about the gamelist update
        notify_gamelist_updated(system_name, len(games))
        notify_game_updated(system_name, game.get('name', 'Unknown'), [media_field])
        
        # Log the upload
        app.logger.info(f'Uploaded media file: {file_path} for game {game_id} field {media_field}')
        
        return jsonify({
            'success': True,
            'message': f'Media uploaded successfully for {media_field}',
            'media_path': relative_path,
            'filename': new_filename
        })
        
    except Exception as e:
        app.logger.error(f'Error uploading media: {str(e)}')
        return jsonify({'error': f'Failed to upload media: {str(e)}'}), 500

@app.route('/api/extract-first-frame', methods=['POST'])
@login_required
def extract_first_frame():
    """Extract first frame from video for manual cropping"""
    try:
        data = request.get_json()
        video_path = data.get('video_path')
        
        if not video_path:
            return jsonify({'error': 'Video path is required'}), 400
        
        # Convert web path to file system path if needed
        if video_path.startswith('/roms/'):
            # Convert /roms/system/path to actual file system path
            video_path = os.path.join(ROMS_FOLDER, video_path[6:])  # Remove '/roms/' prefix
        
        print(f"Extracting frame from video path: {video_path}")
        
        # Check if video file exists
        if not os.path.exists(video_path):
            return jsonify({'error': f'Video file not found: {video_path}'}), 404
        
        # Create frames directory if it doesn't exist
        frames_dir = os.path.join(os.path.dirname(video_path), 'frames')
        os.makedirs(frames_dir, exist_ok=True)
        
        # Generate frame filename
        video_basename = os.path.splitext(os.path.basename(video_path))[0]
        frame_filename = f"{video_basename}_frame.jpg"
        frame_path = os.path.join(frames_dir, frame_filename)
        
        # Extract first frame using ffmpeg
        cmd = [
            'ffmpeg',
            '-i', video_path,
            '-vframes', '1',
            '-q:v', '2',  # High quality
            '-y',  # Overwrite output file
            frame_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode != 0:
            return jsonify({'error': f'Failed to extract frame: {result.stderr}'}), 500
        
        if not os.path.exists(frame_path):
            return jsonify({'error': 'Frame extraction failed - no output file'}), 500
        
        # Return relative path for web access
        relative_frame_path = os.path.relpath(frame_path, ROMS_FOLDER)
        
        return jsonify({
            'success': True,
            'frame_path': relative_frame_path
        })
        
    except subprocess.TimeoutExpired:
        return jsonify({'error': 'Frame extraction timed out'}), 500
    except Exception as e:
        print(f"Error extracting first frame: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/delete-frame-image', methods=['POST'])
@login_required
def delete_frame_image():
    """Delete extracted frame image file"""
    try:
        data = request.get_json()
        frame_path = data.get('frame_path')
        
        print(f"Delete frame image request data: {data}")
        print(f"Original frame_path: {frame_path}")
        
        if not frame_path:
            return jsonify({'error': 'Missing frame_path parameter'}), 400
        
        # Convert relative path to absolute file system path
        original_path = frame_path
        if frame_path.startswith('/roms/'):
            # Convert /roms/system/path to actual file system path
            frame_path = os.path.join(ROMS_FOLDER, frame_path[6:])  # Remove '/roms/' prefix
        else:
            # If it's already a relative path (from extract-first-frame), just join with ROMS_FOLDER
            frame_path = os.path.join(ROMS_FOLDER, frame_path)
        
        print(f"Converted frame_path: {frame_path}")
        print(f"ROMS_FOLDER: {ROMS_FOLDER}")
        
        # Check if file exists and delete it
        if os.path.exists(frame_path):
            os.remove(frame_path)
            print(f"Deleted frame image: {frame_path}")
            return jsonify({'success': True, 'message': 'Frame image deleted successfully'})
        else:
            print(f"Frame image not found: {frame_path}")
            print(f"File exists check failed for: {frame_path}")
            return jsonify({'success': True, 'message': 'Frame image not found (already deleted)'})
            
    except Exception as e:
        print(f"Error deleting frame image: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/apply-manual-crop', methods=['POST'])
@login_required
def apply_manual_crop():
    """Apply manual crop to video"""
    try:
        data = request.get_json()
        video_path = data.get('video_path')
        crop_dimensions = data.get('crop_dimensions')
        game_id = data.get('game_id')
        system_name = data.get('system_name')
        rom_file = data.get('rom_file')
        
        # Debug: Log received parameters
        print(f"Manual crop API received data: {data}")
        print(f"video_path: {video_path}")
        print(f"crop_dimensions: {crop_dimensions}")
        print(f"game_id: {game_id}")
        print(f"system_name: {system_name}")
        print(f"rom_file: {rom_file}")
        
        if not all([video_path, crop_dimensions, game_id, system_name, rom_file]):
            missing_params = []
            if not video_path: missing_params.append('video_path')
            if not crop_dimensions: missing_params.append('crop_dimensions')
            if not game_id: missing_params.append('game_id')
            if not system_name: missing_params.append('system_name')
            if not rom_file: missing_params.append('rom_file')
            return jsonify({'error': f'Missing required parameters: {missing_params}'}), 400
        
        # Convert web path to file system path if needed
        if video_path.startswith('/roms/'):
            # Convert /roms/system/path to actual file system path
            video_path = os.path.join(ROMS_FOLDER, video_path[6:])  # Remove '/roms/' prefix
        
        print(f"Applying manual crop to video path: {video_path}")
        
        # Check if video file exists
        if not os.path.exists(video_path):
            return jsonify({'error': f'Video file not found: {video_path}'}), 404
        
        # Create and start the crop task
        task_data = {
            'video_path': video_path,
            'crop_dimensions': crop_dimensions,
            'game_id': game_id,
            'system_name': system_name,
            'rom_file': rom_file
        }
        
        task = create_task('manual_crop', task_data)
        current_task_id = task.id
        task.start()
        
        # Start manual crop in background thread
        thread = threading.Thread(target=run_manual_crop_task, args=(task.id, task_data))
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True,
            'message': 'Manual crop started',
            'task_id': task.id,
            'status': 'running'
        })
        
    except Exception as e:
        print(f"Manual crop error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/rom-system/<system_name>/game/<game_id>/delete-media', methods=['POST'])
@login_required
def delete_game_media(system_name, game_id):
    """Delete a media file for a specific game"""
    try:
        # Check if system exists
        system_path = os.path.join(ROMS_FOLDER, system_name)
        if not os.path.exists(system_path):
            return jsonify({'error': 'System not found'}), 404
        
        # Check if game exists in gamelist
        gamelist_path = os.path.join(system_path, 'gamelist.xml')
        if not os.path.exists(gamelist_path):
            return jsonify({'error': 'Gamelist not found'}), 404
        
        # Parse gamelist to find the game
        games = parse_gamelist_xml(gamelist_path)
        # Convert game_id to int for comparison since URL parameters are strings
        try:
            game_id_int = int(game_id)
        except ValueError:
            return jsonify({'error': 'Invalid game ID format'}), 400
        
        game = next((g for g in games if g.get('id') == game_id_int), None)
        if not game:
            return jsonify({'error': f'Game not found with ID {game_id_int}'}), 404
        
        # Get media field from request data
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        media_field = data.get('media_field')
        if not media_field:
            return jsonify({'error': 'Media field not specified'}), 400
        
        # Validate media field
        valid_media_fields = ['boxart', 'screenshot', 'marquee', 'wheel', 'video', 'thumbnail', 'cartridge', 'fanart', 'title', 'manual', 'boxback', 'box2d']
        if media_field not in valid_media_fields:
            return jsonify({'error': 'Invalid media field'}), 400
        
        # Check if the media field exists for this game
        if media_field not in game or not game[media_field]:
            return jsonify({'error': f'No {media_field} media found for this game'}), 404
        
        # Get the current media path
        media_path = game[media_field]
        
        # Construct full path to the media file
        full_media_path = os.path.join(system_path, media_path)
        
        # Delete the physical file if it exists
        if os.path.exists(full_media_path):
            try:
                os.remove(full_media_path)
                app.logger.info(f'Deleted media file: {full_media_path}')
            except Exception as e:
                app.logger.warning(f'Could not delete physical file {full_media_path}: {str(e)}')
        
        # Clear the media field in the game object
        game[media_field] = ''
        
        # Update the gamelist.xml file
        write_gamelist_xml(games, gamelist_path)
        
        # Notify all connected clients about the gamelist update
        notify_gamelist_updated(system_name, len(games))
        notify_game_updated(system_name, game.get('name', 'Unknown'), [media_field])
        
        # Log the deletion
        app.logger.info(f'Deleted media field {media_field} for game {game_id}')
        
        return jsonify({
            'success': True,
            'message': f'Media deleted successfully for {media_field}'
        })
        
    except Exception as e:
        app.logger.error(f'Error deleting media: {str(e)}')
        return jsonify({'error': f'Failed to delete media: {str(e)}'}), 500

@app.route('/api/task/status')
@login_required
def get_task_status():
    """Get the current task status for persistence across browser refreshes"""
    global current_task_id
    if current_task_id and current_task_id in tasks:
        task = tasks[current_task_id]
        return jsonify(task.to_dict())
    else:
        return jsonify({
            'status': 'idle',
            'type': None,
            'progress': [],
            'stats': {},
            'start_time': None,
            'end_time': None,
            'error_message': None
        })

@app.route('/api/task/queue')
@login_required
def get_task_queue():
    """Get the current task queue status"""
    return jsonify(get_queue_status())

@app.route('/api/tasks')
@login_required
def get_tasks():
    """Get all tasks"""
    return jsonify(get_all_tasks())

@app.route('/api/tasks/<task_id>')
@login_required
def get_task_by_id(task_id):
    """Get a specific task by ID"""
    task = get_task(task_id)
    if task:
        return jsonify(task.to_dict())
    return jsonify({'error': 'Task not found'}), 404

@app.route('/api/tasks/<task_id>/log')
@login_required
def get_task_log_by_id(task_id):
    """Get the log content for a specific task"""
    log_content = get_task_log(task_id)
    if log_content is not None:
        return jsonify({'log': log_content})
    return jsonify({'error': 'Task or log not found'}), 404

@app.route('/api/tasks/<task_id>/log/stream')
@login_required
def stream_task_log(task_id):
    """Stream live log updates for a running task with rate limiting and batching"""
    def generate():
        task = tasks.get(task_id)
        if not task:
            yield f"data: {json.dumps({'error': 'Task not found'})}\n\n"
            return
        
        if task.status != TASK_STATUS_RUNNING:
            yield f"data: {json.dumps({'error': 'Task is not running'})}\n\n"
            return
        
        # Send initial log content
        initial_log = get_task_log(task_id)
        if initial_log:
            yield f"data: {json.dumps({'log': initial_log, 'type': 'initial'})}\n\n"
        
        # Stream live updates with rate limiting and batching
        last_log_length = len(initial_log) if initial_log else 0
        last_update_time = time.time()
        min_update_interval = 0.2  # Minimum 200ms between updates
        
        try:
            while task.status == TASK_STATUS_RUNNING:
                current_time = time.time()
                current_log = get_task_log(task_id)
                
                if current_log and len(current_log) > last_log_length:
                    # Check if enough time has passed since last update
                    if current_time - last_update_time >= min_update_interval:
                        # New log content available - send update
                        new_content = current_log[last_log_length:]
                        yield f"data: {json.dumps({'log': new_content, 'type': 'update'})}\n\n"
                        last_log_length = len(current_log)
                        last_update_time = current_time
                
                time.sleep(0.1)  # Check every 100ms for responsiveness
        except GeneratorExit:
            # Client disconnected
            return
        
        # Send final log content
        final_log = get_task_log(task_id)
        if final_log:
            yield f"data: {json.dumps({'log': final_log, 'type': 'final'})}\n\n"
    
    return Response(generate(), mimetype='text/event-stream')

@app.route('/api/tasks/<task_id>/log/download')
@login_required
def download_task_log(task_id):
    """Download the task log file directly"""
    task = tasks.get(task_id)
    if not task:
        return jsonify({'error': 'Task not found'}), 404
    
    # Get the log file path
    log_file_path = get_task_log_file_path(task_id)
    if not log_file_path or not os.path.exists(log_file_path):
        return jsonify({'error': 'Log file not found'}), 404
    
    # Get task details for filename
    task_type = getattr(task, 'type', 'unknown')
    task_start_time = getattr(task, 'start_time', None)
    
    # Create a descriptive filename
    if task_start_time:
        timestamp = datetime.fromtimestamp(task_start_time).strftime('%Y%m%d_%H%M%S')
        filename = f"task-{task_type}-{task_id}-{timestamp}.log"
    else:
        filename = f"task-{task_type}-{task_id}.log"
    
    # Send the file directly
    return send_file(
        log_file_path,
        as_attachment=True,
        download_name=filename,
        mimetype='text/plain'
    )

@app.route('/api/tasks/cleanup', methods=['POST'])
@login_required
def cleanup_tasks_endpoint():
    """Clean up stuck tasks"""
    try:
        stuck_tasks = cleanup_stuck_tasks()
        return jsonify({
            'success': True,
            'message': f'Cleaned up {len(stuck_tasks)} stuck tasks',
            'cleaned_tasks': stuck_tasks
        })
    except Exception as e:
        return jsonify({'error': f'Failed to cleanup tasks: {str(e)}'}), 500

@app.route('/api/tasks/<task_id>/ack-refresh', methods=['POST'])
@login_required
def ack_task_refresh(task_id):
    """Acknowledge that a client has processed the grid refresh for a completed task.
    This clears grid_refresh_needed to avoid repeated auto-refreshes in new sessions."""
    try:
        task = tasks.get(task_id)
        if not task:
            return jsonify({'error': 'Task not found'}), 404
        # Only clear for completed/error/idle tasks
        if task.status in [TASK_STATUS_COMPLETED, TASK_STATUS_ERROR, TASK_STATUS_STOPPED, TASK_STATUS_IDLE]:
            task.grid_refresh_needed = False
        return jsonify({'success': True, 'task_id': task_id, 'grid_refresh_needed': task.grid_refresh_needed})
    except Exception as e:
        return jsonify({'error': f'Failed to acknowledge task refresh: {str(e)}'}), 500

@app.route('/api/tasks/<task_id>/reconstruct', methods=['GET'])
@login_required
def reconstruct_task_from_log(task_id):
    """Reconstruct key task fields (system, steps, progress) from its log file."""
    try:
        log_path = os.path.join(LOGS_DIR, f"{task_id}.log")
        if not os.path.exists(log_path):
            return jsonify({'error': 'Log file not found'}), 404
        system_name = None
        progress_percentage = 0
        current_step = 0
        total_steps = 0
        stats = {}
        status = None
        with open(log_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line.startswith('JSON: '):
                    continue
                try:
                    obj = json.loads(line[6:])
                except Exception:
                    continue
                system_name = obj.get('system_name') or system_name
                progress_percentage = obj.get('progress_percentage', progress_percentage)
                current_step = obj.get('current_step', current_step)
                total_steps = obj.get('total_steps', total_steps)
                if obj.get('stats'):
                    stats.update(obj['stats'])
                status = obj.get('status', status)
        return jsonify({
            'success': True,
            'task_id': task_id,
            'system_name': system_name,
            'progress_percentage': progress_percentage,
            'current_step': current_step,
            'total_steps': total_steps,
            'stats': stats,
            'status': status,
        })
    except Exception as e:
        return jsonify({'error': f'Failed to reconstruct task: {str(e)}'}), 500

@app.route('/api/tasks/history', methods=['GET'])
@login_required
def get_task_history():
    """Return reconstructed summaries for all tasks found in task_logs to repopulate the task grid after restart."""
    try:
        results = {}
        if not os.path.exists(LOGS_DIR):
            return jsonify(results)
        for fname in os.listdir(LOGS_DIR):
            if not fname.endswith('.log'):
                continue
            task_id = fname[:-4]
            log_path = os.path.join(LOGS_DIR, fname)
            type_hint = None
            system_name = None
            progress_percentage = 0
            current_step = 0
            total_steps = 0
            stats = {}
            status = None
            start_ts = None
            end_ts = None
            try:
                with open(log_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.startswith('Type: '):
                            type_hint = line.split('Type: ', 1)[1].strip()
                        if not line.startswith('JSON: '):
                            continue
                        try:
                            obj = json.loads(line[6:])
                        except Exception:
                            continue
                        # times
                        ts = obj.get('ts')
                        if ts:
                            if start_ts is None:
                                start_ts = ts
                            end_ts = ts
                        # core fields
                        system_name = obj.get('system_name') or system_name
                        progress_percentage = obj.get('progress_percentage', progress_percentage)
                        current_step = obj.get('current_step', current_step)
                        total_steps = obj.get('total_steps', total_steps)
                        if obj.get('stats'):
                            try:
                                stats.update(obj['stats'])
                            except Exception:
                                pass
                        status = obj.get('status', status)
                results[task_id] = {
                    'id': task_id,
                    'type': type_hint,
                    'status': status or 'completed',
                    'data': {'system_name': system_name} if system_name else {},
                    'progress_percentage': progress_percentage,
                    'current_step': current_step,
                    'total_steps': total_steps,
                    'stats': stats,
                    'start_time': start_ts,
                    'end_time': end_ts,
                }
            except Exception:
                continue
        return jsonify(results)
    except Exception as e:
        return jsonify({'error': f'Failed to read task history: {str(e)}'}), 500

@app.route('/api/tasks/<task_id>/stop', methods=['POST'])
@login_required
def stop_task_endpoint(task_id):
    """Stop a running task"""
    global tasks, current_task_id
    
    if task_id not in tasks:
        return jsonify({'error': 'Task not found'}), 404
    
    task = tasks[task_id]
    
    if task.status != TASK_STATUS_RUNNING:
        return jsonify({'error': 'Task is not running'}), 400
    
    try:
        # Do not write from the main process; the worker will flush partial changes
        task.update_progress("🛑 Stop requested - worker will save partial changes if needed")

        # Set the global stop event to signal all running tasks
        task_stop_event.set()
        # Also signal the worker process cooperatively via shared cancel map
        try:
            if '_worker_cancel_map' in globals() and _worker_cancel_map is not None:
                _worker_cancel_map[task_id] = True
        except Exception as _e:
            print(f"Warning: could not set worker cancel flag: {_e}")
        
        # For image download tasks, immediately stop the download manager
        if task.type == 'image_download':
            try:
                from download_manager import get_download_manager
                download_manager = get_download_manager()
                if download_manager:
                    task.update_progress("🛑 Stopping download manager immediately")
                    download_manager.stop()
            except Exception as e:
                task.update_progress(f"⚠️  Warning: Could not stop download manager: {e}")
        
        # For IGDB scraping tasks, we need to handle cancellation differently
        # since they use their own separate process and cancel map
        if task.type == 'igdb_scraping':
            task.update_progress("🛑 IGDB scraping task stop requested - worker will save gamelist and exit")
            # Set the cancel flag in the IGDB-specific cancel map
            try:
                global _igdb_cancel_maps
                if task_id in _igdb_cancel_maps:
                    _igdb_cancel_maps[task_id][task_id] = True
                    print(f"DEBUG: Set IGDB cancel flag for task {task_id}")
                else:
                    print(f"DEBUG: IGDB cancel map not found for task {task_id}")
            except Exception as e:
                print(f"Warning: could not set IGDB cancel flag: {e}")
        
        # Stop the task
        task.stop()
        
        # If this was the current running task, clear it
        if current_task_id == task_id:
            current_task_id = None
        
        # Clean up any stuck tasks
        cleanup_stuck_tasks()
        
        # Process next queued task if any
        process_next_queued_task()
        
        # Indicate that the grid should be reloaded if gamelist was saved
        grid_reload_needed = False
        if task.type in ['scraping', 'media_scan', 'image_download', 'youtube_download'] and task.data:
            system_name = task.data.get('system_name')
            if system_name:
                # For these task types, always indicate grid reload is needed
                # because they modify gamelist data, even if stopped prematurely
                grid_reload_needed = True
        
        return jsonify({
            'success': True, 
            'message': 'Task stopped successfully',
            'grid_reload_needed': grid_reload_needed,
            'system_name': task.data.get('system_name') if task.data else None
        })
    except Exception as e:
        return jsonify({'error': f'Failed to stop task: {str(e)}'}), 500

@app.route('/api/youtube/search', methods=['POST'])
@login_required
def youtube_search():
    """Search YouTube directly for videos"""
    try:
        data = request.get_json()
        search_query = data.get('query', '').strip()
        
        if not search_query:
            return jsonify({'error': 'Search query is required'}), 400
        
        print(f"Searching YouTube for: {search_query}")
        
        # Search directly on YouTube
        search_url = f"https://www.youtube.com/results?search_query={search_query}+gameplay"
        
        # Use a realistic user agent to avoid being blocked
        headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
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
        }
        
        try:
            print(f"Making request to: {search_url}")
            response = requests.get(search_url, headers=headers, timeout=15)
            response.raise_for_status()
            
            print(f"Response status: {response.status_code}")
            print(f"Response length: {len(response.text)} characters")
            
            # Parse the HTML response
            soup = BeautifulSoup(response.text, 'html.parser')
            print(f"BeautifulSoup created successfully")
            
            # Method 1: Try to extract from ytInitialData (most reliable)
            print("Attempting to extract video data from ytInitialData...")
            videos = extract_from_yt_initial_data(response.text)
            
            if videos:
                print(f"Successfully extracted {len(videos)} videos from ytInitialData")
                # Sort videos by recency and limit to 10 results
                sorted_videos = sort_videos_by_recency(videos[:10])
                return jsonify({
                    'success': True,
                    'results': sorted_videos,
                    'query': search_query
                })
            
            # Method 2: Try to extract from ytInitialData alternative format
            print("Attempting to extract from alternative ytInitialData format...")
            videos = extract_from_yt_initial_data_alt(response.text)
            
            if videos:
                print(f"Successfully extracted {len(videos)} videos from alternative format")
                # Sort videos by recency and limit to 10 results
                sorted_videos = sort_videos_by_recency(videos[:10])
                return jsonify({
                    'success': True,
                    'results': sorted_videos,
                    'query': search_query
                })
            
            # Method 3: Try to extract from embedded JSON data
            print("Attempting to extract from embedded JSON data...")
            videos = extract_from_embedded_json(response.text)
            
            if videos:
                print(f"Successfully extracted {len(videos)} videos from embedded JSON")
                # Sort videos by recency and limit to 10 results
                sorted_videos = sort_videos_by_recency(videos[:10])
                return jsonify({
                    'success': True,
                    'results': sorted_videos,
                    'query': search_query
                })
            
            # Method 4: Fallback to HTML parsing with better selectors
            print("Falling back to HTML parsing with enhanced selectors...")
            videos = extract_from_html_enhanced(soup)
            
            if videos:
                print(f"Successfully extracted {len(videos)} videos from HTML parsing")
                # Sort videos by recency and limit to 10 results
                sorted_videos = sort_videos_by_recency(videos[:10])
                return jsonify({
                    'success': True,
                    'results': sorted_videos,
                    'query': search_query
                })
            
            # If all methods fail, use mock data
            print("All extraction methods failed, using mock data")
            return generate_mock_videos(search_query)
                
        except requests.RequestException as e:
            print(f"Request error: {e}")
            return generate_mock_videos(search_query)
        except Exception as e:
            print(f"Unexpected error during scraping: {e}")
            import traceback
            traceback.print_exc()
            return generate_mock_videos(search_query)
            
    except Exception as e:
        print(f"YouTube search error: {e}")
        return jsonify({'error': str(e)}), 500

def extract_from_yt_initial_data(html_text):
    """Extract video data from ytInitialData (most reliable method)"""
    try:
        # Look for ytInitialData in the HTML
        start_marker = 'var ytInitialData = '
        end_marker = ';</script>'
        
        start_idx = html_text.find(start_marker)
        if start_idx == -1:
            return []
        
        start_idx += len(start_marker)
        end_idx = html_text.find(end_marker, start_idx)
        if end_idx == -1:
            end_idx = html_text.find(';', start_idx)
        
        if end_idx == -1:
            return []
        
        json_str = html_text[start_idx:end_idx]
        yt_data = json.loads(json_str)
        
        videos = []
        
        # Navigate through the ytInitialData structure
        if 'contents' in yt_data:
            contents = yt_data['contents']
            if 'twoColumnSearchResultsRenderer' in contents:
                search_results = contents['twoColumnSearchResultsRenderer']
                if 'primaryContents' in search_results:
                    primary = search_results['primaryContents']
                    if 'sectionListRenderer' in primary:
                        sections = primary['sectionListRenderer']['contents']
                        for section in sections:
                            if 'itemSectionRenderer' in section:
                                items = section['itemSectionRenderer']['contents']
                                for item in items:
                                    if 'videoRenderer' in item:
                                        video_data = extract_video_from_renderer(item['videoRenderer'])
                                        if video_data:
                                            videos.append(video_data)
                                            if len(videos) >= 10:
                                                break
                                    elif 'compactVideoRenderer' in item:
                                        video_data = extract_video_from_compact_renderer(item['compactVideoRenderer'])
                                        if video_data:
                                            videos.append(video_data)
                                            if len(videos) >= 10:
                                                break
        
        return videos
        
    except Exception as e:
        print(f"Error extracting from ytInitialData: {e}")
        return []

def extract_from_yt_initial_data_alt(html_text):
    """Extract video data from alternative ytInitialData format"""
    try:
        # Look for ytInitialData in different script tags
        import re
        
        # Pattern to find ytInitialData in various formats
        patterns = [
            r'var ytInitialData = ({.*?});',
            r'ytInitialData = ({.*?});',
            r'window\["ytInitialData"\] = ({.*?});'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, html_text, re.DOTALL)
            if matches:
                try:
                    yt_data = json.loads(matches[0])
                    videos = extract_videos_from_yt_data(yt_data)
                    if videos:
                        return videos
                except:
                    continue
        
        return []
        
    except Exception as e:
        print(f"Error extracting from ytInitialData alt: {e}")
        return []

def extract_from_embedded_json(html_text):
    """Extract video data from embedded JSON in script tags"""
    try:
        import re
        
        # Look for various JSON patterns that might contain video data
        patterns = [
            r'"videoId":"([^"]{11})"',
            r'"title":"([^"]+?)"',
            r'"channelName":"([^"]+?)"',
            r'"thumbnail":"([^"]+?)"'
        ]
        
        video_ids = re.findall(r'"videoId":"([^"]{11})"', html_text)
        titles = re.findall(r'"title":"([^"]+?)"', html_text)
        channels = re.findall(r'"channelName":"([^"]+?)"', html_text)
        thumbnails = re.findall(r'"thumbnail":"([^"]+?)"', html_text)
        
        videos = []
        for i, video_id in enumerate(video_ids[:10]):
            if len(video_id) == 11:  # Valid YouTube ID
                title = titles[i] if i < len(titles) else f"Video {i+1}"
                channel = channels[i] if i < len(channels) else "Unknown Channel"
                thumbnail = thumbnails[i] if i < len(thumbnails) else f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"
                
                videos.append({
                    'id': video_id,
                    'title': title[:100] + '...' if len(title) > 100 else title,
                    'thumbnail': thumbnail,
                    'duration': 'Unknown',
                    'channel': channel[:50] + '...' if len(channel) > 50 else channel,
                    'url': f"https://www.youtube.com/watch?v={video_id}"
                })
        
        return videos
        
    except Exception as e:
        print(f"Error extracting from embedded JSON: {e}")
        return []

def extract_from_html_enhanced(soup):
    """Extract video data from HTML using enhanced selectors"""
    try:
        videos = []
        
        # Try multiple selector strategies
        selectors = [
            'ytd-video-renderer',
            'div[data-context-item-id]',
            '.yt-lockup-content',
            '[data-video-id]',
            'div[class*="video"]'
        ]
        
        video_elements = []
        for selector in selectors:
            video_elements = soup.select(selector)
            if video_elements:
                print(f"Found {len(video_elements)} videos using selector: {selector}")
                break
        
        if not video_elements:
            # Fallback: look for any element with video-related attributes
            video_elements = soup.find_all(attrs={'data-context-item-id': True})
            if not video_elements:
                video_elements = soup.find_all(attrs={'data-video-id': True})
        
        count = 0
        for element in video_elements:
            if count >= 10:
                break
                
            try:
                # Extract video ID
                video_id = None
                if element.get('data-context-item-id'):
                    video_id = element['data-context-item-id']
                elif element.get('data-video-id'):
                    video_id = element['data-video-id']
                
                # Try to find video ID in links
                if not video_id:
                    links = element.find_all('a', href=True)
                    for link in links:
                        if 'watch?v=' in link['href']:
                            video_id = link['href'].split('watch?v=')[1].split('&')[0]
                            break
                
                if not video_id or len(video_id) != 11:
                    continue
                
                # Extract title
                title = "Unknown Title"
                title_elem = element.find('a', {'title': True})
                if title_elem:
                    title = title_elem['title']
                else:
                    title_elem = element.find('h3') or element.find('h2') or element.find('h1')
                    if title_elem:
                        title = title_elem.get_text(strip=True)
                
                # Extract thumbnail
                thumbnail = None
                img_elem = element.find('img')
                if img_elem:
                    thumbnail = img_elem.get('src') or img_elem.get('data-src') or img_elem.get('data-thumb')
                
                if not thumbnail:
                    thumbnail = f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"
                
                # Extract channel
                channel = "Unknown Channel"
                channel_selectors = [
                    'a[class*="channel"]',
                    '.yt-lockup-byline a',
                    '.yt-lockup-meta-info a',
                    '[class*="byline"]'
                ]
                
                for selector in channel_selectors:
                    channel_elem = element.select_one(selector)
                    if channel_elem:
                        channel = channel_elem.get_text(strip=True)
                        break
                
                videos.append({
                    'id': video_id,
                    'title': title[:100] + '...' if len(title) > 100 else title,
                    'thumbnail': thumbnail,
                    'duration': 'Unknown',
                    'channel': channel[:50] + '...' if len(channel) > 50 else channel,
                    'url': f"https://www.youtube.com/watch?v={video_id}"
                })
                
                count += 1
                
            except Exception as e:
                print(f"Error extracting video from element: {e}")
                continue
        
        return videos
        
    except Exception as e:
        print(f"Error in HTML enhanced extraction: {e}")
        return []

def extract_videos_from_yt_data(yt_data):
    """Extract video information from YouTube's embedded JavaScript data"""
    videos = []
    
    try:
        # Navigate through the ytInitialData structure to find video results
        # This structure can change, so we'll try multiple paths
        
        # Path 1: Try to find contents in search results
        if 'contents' in yt_data:
            contents = yt_data['contents']
            if 'twoColumnSearchResultsRenderer' in contents:
                search_results = contents['twoColumnSearchResultsRenderer']
                if 'primaryContents' in search_results:
                    primary = search_results['primaryContents']
                    if 'sectionListRenderer' in primary:
                        sections = primary['sectionListRenderer']['contents']
                        for section in sections:
                            if 'itemSectionRenderer' in section:
                                items = section['itemSectionRenderer']['contents']
                                for item in items:
                                    if 'videoRenderer' in item:
                                        video_data = extract_video_from_renderer(item['videoRenderer'])
                                        if video_data:
                                            videos.append(video_data)
                                            if len(videos) >= 10:
                                                break
                                    elif 'compactVideoRenderer' in item:
                                        video_data = extract_video_from_compact_renderer(item['compactVideoRenderer'])
                                        if video_data:
                                            videos.append(video_data)
                                            if len(videos) >= 10:
                                                break
        
        # Path 2: Try alternative structure
        if not videos and 'onResponseReceivedCommands' in yt_data:
            commands = yt_data['onResponseReceivedCommands']
            for command in commands:
                if 'appendContinuationItemsAction' in command:
                    items = command['appendContinuationItemsAction']['continuationItems']
                    for item in items:
                        if 'videoRenderer' in item:
                            video_data = extract_video_from_renderer(item['videoRenderer'])
                            if video_data:
                                videos.append(video_data)
                                if len(videos) >= 10:
                                    break
                        elif 'compactVideoRenderer' in item:
                            video_data = extract_video_from_compact_renderer(item['compactVideoRenderer'])
                            if video_data:
                                videos.append(video_data)
                                if len(videos) >= 10:
                                    break
        
        print(f"Extracted {len(videos)} videos from ytInitialData")
        return videos
        
    except Exception as e:
        print(f"Error extracting videos from ytInitialData: {e}")
        return []

def extract_video_from_renderer(renderer):
    """Extract video data from a videoRenderer object"""
    try:
        video_id = renderer.get('videoId', '')
        if not video_id:
            return None
            
        title = renderer.get('title', {}).get('runs', [{}])[0].get('text', 'Unknown Title')
        thumbnail = renderer.get('thumbnail', {}).get('thumbnails', [{}])[-1].get('url', '')
        channel = renderer.get('ownerText', {}).get('runs', [{}])[0].get('text', 'Unknown Channel')
        
        # Extract duration from lengthText
        duration = 'Unknown'
        length_text = renderer.get('lengthText', {})
        if length_text and 'simpleText' in length_text:
            duration = length_text['simpleText']
        
        # Extract view count and resolution info
        view_count = 'Unknown'
        view_count_text = renderer.get('viewCountText', {})
        if view_count_text and 'simpleText' in view_count_text:
            view_count = view_count_text['simpleText']
        
        # Extract publication date
        published_time = 'Unknown'
        published_text = renderer.get('publishedTimeText', {})
        if published_text and 'simpleText' in published_text:
            published_time = published_text['simpleText']
        
        # Get thumbnail from YouTube's service if not available
        if not thumbnail:
            thumbnail = f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"
        
        return {
            'id': video_id,
            'title': title[:100] + '...' if len(title) > 100 else title,
            'thumbnail': thumbnail,
            'duration': duration,
            'channel': channel[:50] + '...' if len(channel) > 50 else channel,
            'view_count': view_count,
            'published_time': published_time,
            'url': f"https://www.youtube.com/watch?v={video_id}"
        }
    except Exception as e:
        print(f"Error extracting video from renderer: {e}")
        return None

def extract_video_from_compact_renderer(renderer):
    """Extract video data from a compactVideoRenderer object"""
    try:
        video_id = renderer.get('videoId', '')
        if not video_id:
            return None
            
        title = renderer.get('title', {}).get('simpleText', 'Unknown Title')
        thumbnail = renderer.get('thumbnail', {}).get('thumbnails', [{}])[-1].get('url', '')
        channel = renderer.get('shortBylineText', {}).get('runs', [{}])[0].get('text', 'Unknown Channel')
        
        # Extract duration from lengthText
        duration = 'Unknown'
        length_text = renderer.get('lengthText', {})
        if length_text and 'simpleText' in length_text:
            duration = length_text['simpleText']
        
        # Extract view count info
        view_count = 'Unknown'
        view_count_text = renderer.get('viewCountText', {})
        if view_count_text and 'simpleText' in view_count_text:
            view_count = view_count_text['simpleText']
        
        # Extract publication date
        published_time = 'Unknown'
        published_text = renderer.get('publishedTimeText', {})
        if published_text and 'simpleText' in published_text:
            published_time = published_text['simpleText']
        
        # Get thumbnail from YouTube's service if not available
        if not thumbnail:
            thumbnail = f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"
        
        return {
            'id': video_id,
            'title': title[:100] + '...' if len(title) > 100 else title,
            'thumbnail': thumbnail,
            'duration': duration,
            'channel': channel[:50] + '...' if len(channel) > 50 else channel,
            'view_count': view_count,
            'published_time': published_time,
            'url': f"https://www.youtube.com/watch?v={video_id}"
        }
    except Exception as e:
        print(f"Error extracting video from compact renderer: {e}")
        return None

def sort_videos_by_recency(videos):
    """Sort videos by recency (most recent first)"""
    def parse_time_ago(time_str):
        if not time_str or time_str == 'Unknown':
            return float('inf')  # Put unknown dates at the end
        
        time_str = time_str.lower()
        
        # Parse common YouTube time formats
        if 'just now' in time_str or 'today' in time_str:
            return 0
        elif 'hour' in time_str:
            hours = int(''.join(filter(str.isdigit, time_str)))
            return hours
        elif 'day' in time_str:
            days = int(''.join(filter(str.isdigit, time_str)))
            return days * 24
        elif 'week' in time_str:
            weeks = int(''.join(filter(str.isdigit, time_str)))
            return weeks * 7 * 24
        elif 'month' in time_str:
            months = int(''.join(filter(str.isdigit, time_str)))
            return months * 30 * 24
        elif 'year' in time_str:
            years = int(''.join(filter(str.isdigit, time_str)))
            return years * 365 * 24
        else:
            return float('inf')  # Unknown format
    
    # Sort by recency (lowest time value first)
    return sorted(videos, key=lambda x: parse_time_ago(x.get('published_time', 'Unknown')))

def generate_mock_videos(search_query):
    """Generate mock video data as fallback"""
    mock_videos = []
    for i in range(1, 11):
        mock_videos.append({
            'id': f'mock{i}',
            'title': f'{search_query} - {"Gameplay" if i % 3 == 0 else "Review" if i % 3 == 1 else "Demo"} Video {i}',
            'thumbnail': f'https://picsum.photos/120/90?random={i}',  # Use Picsum for working thumbnails
            'duration': f'{2 + (i % 3):02d}:{30 + (i % 30):02d}',
            'channel': f'{"Game Channel" if i % 2 == 0 else "Retro Gaming" if i % 3 == 0 else "Arcade Zone"}',
            'view_count': f'{1000 + (i * 500):,} views',
            'published_time': f'{i + 1} {"day" if i == 0 else "days"} ago',
            'url': f'https://www.youtube.com/watch?v=mock{i}'
        })
    
    # Sort mock videos by recency
    sorted_videos = sort_videos_by_recency(mock_videos)
    
    return jsonify({
        'success': True,
        'results': sorted_videos,
        'query': search_query
    })

@app.route('/api/youtube/download', methods=['POST'])
@login_required
def youtube_download():
    """Download YouTube video and extract 30-second clip (asynchronous)"""
    try:
        data = request.get_json()
        video_url = data.get('video_url')
        start_time = data.get('start_time', 0)
        auto_crop = data.get('auto_crop', False)
        output_filename = data.get('output_filename')
        system_name = data.get('system_name')
        
        if not all([video_url, output_filename, system_name]):
            return jsonify({'error': 'Missing required parameters'}), 400
        
        # Validate system exists
        system_path = os.path.join(ROMS_FOLDER, system_name)
        if not os.path.exists(system_path):
            return jsonify({'error': 'System not found'}), 404
        
        # Check if yt-dlp is available
        try:
            import subprocess
            yt_dlp_path = get_yt_dlp_path()
            result = subprocess.run([yt_dlp_path, '--version'], capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                return jsonify({'error': 'yt-dlp is not installed or not available'}), 500
        except FileNotFoundError:
            return jsonify({'error': 'yt-dlp is not installed'}), 500
        except subprocess.TimeoutExpired:
            return jsonify({'error': 'yt-dlp check timed out'}), 500
        
        # Create and start background download task
        task_data = {
            'video_url': video_url,
            'start_time': start_time,
            'output_filename': output_filename,
            'system_name': system_name,
            'rom_file': data.get('rom_file'),  # Include the ROM file path
            'auto_crop': auto_crop  # Include auto crop setting
        }
        
        # Create and start the task directly (flat data, not nested) so frontend can read system_name
        task = create_task('youtube_download', task_data)
        current_task_id = task.id
        task.start()
        
        # Start YouTube download in background thread
        thread = threading.Thread(target=run_youtube_download_task, args=(task.id, task_data))
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True,
            'message': 'Video download started',
            'task_id': task.id,
            'status': 'running'
        })
        
    except Exception as e:
        print(f"YouTube download error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/rom-system/<system_name>/download-images', methods=['POST'])
@login_required
def download_images_endpoint(system_name):
    """Download LaunchBox images for a specific game or all games in a system"""
    import time
    import threading
    
    global current_task_id
    
    # Check if another task is already running
    can_start, message = can_start_task('image_download')
    if not can_start:
        # Queue the task if it can't start immediately
        queued, queue_message = queue_task('image_download', {
            'system_name': system_name,
            'data': request.get_json()
        })
        return jsonify({
            'error': message,
            'queued': queued,
            'queue_message': queue_message
        }), 409  # Conflict status
    
    try:
        # Create and start new task
        task = create_task('image_download', {
            'system_name': system_name,
            'data': request.get_json()
        })
        current_task_id = task.id
        task.start()
        
        # Start task in background thread and return immediately
        thread = threading.Thread(target=run_image_download_task, args=(system_name, request.get_json()))
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True,
            'message': f'Image download task started for {system_name}',
            'task_id': current_task_id
        })
        
    except Exception as e:
        # Update task state with error
        if current_task_id and current_task_id in tasks:
            tasks[current_task_id].complete(False, str(e))
        
        return jsonify({'error': f'Image download failed: {str(e)}'}), 500

@app.route('/api/rom-system/<system_name>/scan-roms', methods=['POST'])
@login_required
def scan_rom_endpoint(system_name):
    """Start ROM scan for a specific system"""
    global current_task_id
    
    # Check if another task is already running
    can_start, message = can_start_task('rom_scan')
    if not can_start:
        # Queue the task if it can't start immediately
        queued, queue_message = queue_task('rom_scan', {
            'system_name': system_name
        })
        return jsonify({
            'error': message,
            'queued': queued,
            'queue_message': queue_message
        }), 409  # Conflict status
    
    try:
        # Create and start new task
        task = create_task('rom_scan', {
            'system_name': system_name
        })
        current_task_id = task.id
        task.start()
        
        # Start task in background thread
        thread = threading.Thread(target=run_rom_scan_task, args=(system_name,))
        thread.daemon = True
        thread.start()
        
        return jsonify({'success': True, 'message': 'ROM scan started'})
    except Exception as e:
        return jsonify({'error': f'ROM scan failed: {str(e)}'}), 500

def run_rom_scan_task(system_name):
    """Run ROM scan task in background thread"""
    global current_task_id
    
    try:
        if not current_task_id or current_task_id not in tasks:
            print("Error: No active task found for ROM scan")
            return
        
        task = tasks[current_task_id]
        
        # Initialize task state
        task.update_progress("Starting ROM scan")
        
        # Load media config to get ROM extensions
        media_config = load_media_config()
        if not media_config:
            task.update_progress("Failed to load media configuration")
            return
        
        system_path = os.path.join(ROMS_FOLDER, system_name)
        task.update_progress(f"System path: {system_path}")
        if not os.path.exists(system_path):
            task.update_progress(f"System path does not exist: {system_path}")
            return
        
        # Ensure gamelist exists in var/gamelists, copying from roms/ if needed (only during scan)
        gamelist_path = ensure_gamelist_exists_for_scan(system_name)
        task.update_progress(f"Gamelist path: {gamelist_path}")
        
        # Get supported ROM extensions for this system
        system_config = config.get('systems', {}).get(system_name, {})
        rom_extensions = system_config.get('extensions', [])
        if not rom_extensions:
            # Default extensions if system not found in config
            rom_extensions = ['.zip', '.ZIP', '.7z', '.7Z', '.nes', '.NES', '.sfc', '.smc', '.SFC', '.SMC', '.gba', '.GBA']
        
        task.update_progress(f"Supported ROM extensions: {', '.join(rom_extensions)}")
        
        # Scan for ROM files
        rom_files = []
        for filename in os.listdir(system_path):
            if any(filename.lower().endswith(ext.lower()) for ext in rom_extensions):
                rom_files.append(filename)
        
        task.update_progress(f"Found {len(rom_files)} ROM files in system directory")
        
        # Load existing gamelist if it exists
        existing_games = []
        if os.path.exists(gamelist_path):
            existing_games = parse_gamelist_xml(gamelist_path)
            task.update_progress(f"Loaded {len(existing_games)} existing games from gamelist.xml")
        
        # Create a set of existing ROM filenames for quick lookup
        existing_roms = set()
        for game in existing_games:
            rom_path = game.get('path', '')
            if rom_path:
                rom_filename = os.path.basename(rom_path)
                existing_roms.add(rom_filename)
        
        # Find new ROMs to add
        new_roms = []
        for rom_file in rom_files:
            if rom_file not in existing_roms:
                new_roms.append(rom_file)
        
        # Find games with missing ROM files
        missing_roms = []
        for game in existing_games:
            rom_path = game.get('path', '')
            if rom_path:
                rom_filename = os.path.basename(rom_path)
                rom_file_path = os.path.join(system_path, rom_filename)
                if not os.path.exists(rom_file_path):
                    missing_roms.append(game)
        
        task.update_progress(f"Found {len(new_roms)} new ROMs to add")
        task.update_progress(f"Found {len(missing_roms)} games with missing ROM files")
        
        # If no missing ROMs, proceed with adding new ones
        if not missing_roms:
            # Add new ROMs to gamelist
            next_id = max([game.get('id', 0) for game in existing_games] + [0]) + 1
            for rom_file in new_roms:
                new_game = {
                    'id': next_id,
                    'path': f'./{rom_file}',
                    'name': os.path.splitext(rom_file)[0],  # Use filename without extension as name
                    'desc': '',
                    'genre': '',
                    'developer': '',
                    'publisher': '',
                    'rating': '',
                    'players': ''
                }
                existing_games.append(new_game)
                next_id += 1
                task.update_progress(f"Added new game: {rom_file}")
            
            # Save updated gamelist
            if new_roms:
                write_gamelist_xml(existing_games, gamelist_path)
                task.update_progress(f"Added {len(new_roms)} new games to gamelist.xml")
                
                # Notify all connected clients about the gamelist update
                notify_gamelist_updated(system_name, len(existing_games))
            
            # Automatically trigger media scan to verify media files exist
            task.update_progress("Starting automatic media scan to verify media files...")
            try:
                media_scan_result = scan_media_files(system_name)
                if media_scan_result.get('success'):
                    task.update_progress(f"Media scan completed: {media_scan_result.get('message', '')}")
                else:
                    task.update_progress(f"Media scan warning: {media_scan_result.get('error', 'Unknown error')}")
            except Exception as e:
                task.update_progress(f"Media scan error: {str(e)}")
            
            task.update_progress(f"ROM scan completed successfully! Added {len(new_roms)} new games and verified media files.")
            task.complete()
        else:
            # Store scan results for confirmation
            task.scan_results = {
                'new_roms': new_roms,
                'missing_roms': missing_roms,
                'total_existing': len(existing_games),
                'total_rom_files': len(rom_files)
            }
            task.update_progress(f"ROM scan completed. Found {len(new_roms)} new ROMs and {len(missing_roms)} missing ROMs. Awaiting confirmation.")
            task.complete()
        
    except Exception as e:
        print(f"Error in ROM scan task: {e}")
        import traceback
        traceback.print_exc()
        if current_task_id and current_task_id in tasks:
            tasks[current_task_id].error(str(e))
        return

@app.route('/api/rom-system/<system_name>/scan-roms', methods=['GET'])
@login_required
def get_rom_scan_results(system_name):
    """Get ROM scan results for confirmation"""
    global current_task_id
    
    try:
        if not current_task_id or current_task_id not in tasks:
            return jsonify({'error': 'No active task found'})
        
        task = tasks[current_task_id]
        if task.type != 'rom_scan':
            return jsonify({'error': 'Current task is not a ROM scan'})
        
        if not hasattr(task, 'scan_results'):
            return jsonify({'error': 'No scan results available'})
        
        scan_summary = {
            'new_roms': task.scan_results['new_roms'],
            'missing_roms': [{'id': game.get('id'), 'name': game.get('name'), 'path': game.get('path')} for game in task.scan_results['missing_roms']],
            'total_existing': task.scan_results['total_existing'],
            'total_rom_files': task.scan_results['total_rom_files'],
            'requires_confirmation': len(task.scan_results['missing_roms']) > 0
        }
        
        return jsonify({
            'success': True,
            'message': f'ROM scan completed. Found {len(scan_summary["new_roms"])} new ROMs and {len(scan_summary["missing_roms"])} missing ROMs.',
            'scan_summary': scan_summary,
            'action_taken': 'requires_confirmation'
        })
        
    except Exception as e:
        print(f"Error getting ROM scan results: {e}")
        return jsonify({'error': f'Failed to get scan results: {str(e)}'}), 500

@app.route('/api/rom-system/<system_name>/scan-roms-confirm', methods=['POST'])
@login_required
def scan_rom_files_confirm(system_name):
    """Confirm ROM scan and apply changes (add new ROMs, remove games with missing ROMs)"""
    global current_task_id
    
    try:
        if not current_task_id or current_task_id not in tasks:
            print("Error: No active task found for ROM scan confirmation")
            return jsonify({'error': 'No active task found'})
        
        task = tasks[current_task_id]
        
        data = request.get_json()
        if not data or 'action' not in data:
            return jsonify({'error': 'Invalid request data'})
        
        action = data['action']
        if action not in ['proceed', 'cancel']:
            return jsonify({'error': 'Invalid action'})
        
        if action == 'cancel':
            task.update_progress("ROM scan cancelled by user")
            return jsonify({
                'success': True,
                'message': 'ROM scan cancelled',
                'action_taken': 'cancelled'
            })
        
        # Proceed with the scan
        task.update_progress("Proceeding with ROM scan changes...")
        
        # Load media config
        media_config = load_media_config()
        if not media_config:
            task.update_progress("Failed to load media configuration")
            return jsonify({'error': 'Failed to load media configuration'})
        
        system_path = os.path.join(ROMS_FOLDER, system_name)
        gamelist_path = os.path.join(system_path, 'gamelist.xml')
        
        # Get supported ROM extensions
        system_config = config.get('systems', {}).get(system_name, {})
        rom_extensions = system_config.get('extensions', [])
        if not rom_extensions:
            rom_extensions = ['.zip', '.ZIP', '.7z', '.7Z', '.nes', '.NES', '.sfc', '.smc', '.SFC', '.SMC', '.gba', '.GBA']
        
        # Scan for ROM files
        rom_files = []
        for filename in os.listdir(system_path):
            if any(filename.lower().endswith(ext.lower()) for ext in rom_extensions):
                rom_files.append(filename)
        
        # Load existing gamelist
        existing_games = []
        if os.path.exists(gamelist_path):
            existing_games = parse_gamelist_xml(gamelist_path)
        
        # Create a set of existing ROM filenames
        existing_roms = set()
        for game in existing_games:
            rom_path = game.get('path', '')
            if rom_path:
                rom_filename = os.path.basename(rom_path)
                existing_roms.add(rom_filename)
        
        # Find new ROMs to add
        new_roms = []
        for rom_file in rom_files:
            if rom_file not in existing_roms:
                new_roms.append(rom_file)
        
        # Find games with missing ROM files
        missing_roms = []
        valid_games = []
        for game in existing_games:
            rom_path = game.get('path', '')
            if rom_path:
                rom_filename = os.path.basename(rom_path)
                rom_file_path = os.path.join(system_path, rom_filename)
                if not os.path.exists(rom_file_path):
                    missing_roms.append(game)
                    task.update_progress(f"Removing game with missing ROM: {game.get('name', 'Unknown')} ({rom_filename})")
                else:
                    valid_games.append(game)
            else:
                # Keep games without path (they might be manually added)
                valid_games.append(game)
        
        # Add new ROMs
        next_id = max([game.get('id', 0) for game in valid_games] + [0]) + 1
        for rom_file in new_roms:
            new_game = {
                'id': next_id,
                'path': f'./{rom_file}',
                'name': os.path.splitext(rom_file)[0],
                'desc': '',
                'genre': '',
                'developer': '',
                'publisher': '',
                'rating': '',
                'players': ''
            }
            valid_games.append(new_game)
            next_id += 1
            task.update_progress(f"Added new game: {rom_file}")
        
        # Save updated gamelist
        write_gamelist_xml(valid_games, gamelist_path)
        
        # Notify all connected clients about the gamelist update
        notify_gamelist_updated(system_name, len(valid_games))
        
        # Automatically trigger media scan to verify media files exist
        task.update_progress("Starting automatic media scan to verify media files...")
        try:
            media_scan_result = scan_media_files(system_name)
            if media_scan_result.get('success'):
                task.update_progress(f"Media scan completed: {media_scan_result.get('message', '')}")
            else:
                task.update_progress(f"Media scan warning: {media_scan_result.get('error', 'Unknown error')}")
        except Exception as e:
            task.update_progress(f"Media scan error: {str(e)}")
        
        task.update_progress(f"ROM scan completed successfully!")
        task.update_progress(f"Added {len(new_roms)} new games")
        task.update_progress(f"Removed {len(missing_roms)} games with missing ROMs")
        task.update_progress(f"Total games in system: {len(valid_games)}")
        task.update_progress("Media files have been verified and updated")
        
        return jsonify({
            'success': True,
            'message': f'ROM scan completed. Added {len(new_roms)} new games, removed {len(missing_roms)} games with missing ROMs.',
            'action_taken': 'completed',
            'new_games_added': len(new_roms),
            'games_removed': len(missing_roms),
            'total_games': len(valid_games)
        })
        
    except Exception as e:
        print(f"Error confirming ROM scan: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'ROM scan confirmation failed: {str(e)}'}), 500

def update_gamelist_and_complete(task, system_path, output_filename, output_path, file_size, start_time, end_time, rom_file):
    """Helper function to update gamelist.xml and complete the task"""
    try:
        # Update gamelist.xml to include the new video
        gamelist_path = os.path.join(system_path, 'gamelist.xml')
        if os.path.exists(gamelist_path):
            try:
                # Parse existing gamelist
                games = parse_gamelist_xml(gamelist_path)
                
                # Find the game by ROM file path (exact match)
                game_updated = False
                
                task.update_progress(f"Looking for game with ROM file: '{rom_file}'")
                task.update_progress(f"Total games in gamelist: {len(games)}")
                
                for i, game in enumerate(games):
                    game_path = game.get('path', '')
                    if game_path:
                        task.update_progress(f"Game {i+1}: path='{game_path}'")
                        
                        # Check if the game path exactly matches the ROM file
                        if game_path == rom_file:
                            # Update or add video field
                            game['video'] = f'./media/videos/{output_filename}'
                            game_updated = True
                            task.update_progress(f"✅ MATCH FOUND! Updated gamelist for game: {game.get('name', 'Unknown')}")
                            break
                
                if game_updated:
                    # Write updated gamelist back
                    task.update_progress(f"Writing updated gamelist to: {gamelist_path}")
                    write_gamelist_xml(games, gamelist_path)
                    task.update_progress("✅ Gamelist.xml updated successfully")
                    
                    # Notify all connected clients about the gamelist update
                    system_name = os.path.basename(system_path)
                    notify_gamelist_updated(system_name, len(games))
                    notify_game_updated(system_name, rom_file, ['video'])
                    
                    # Verify the file was written
                    if os.path.exists(gamelist_path):
                        file_size = os.path.getsize(gamelist_path)
                        task.update_progress(f"✅ Gamelist file verified: {file_size} bytes")
                    else:
                        task.update_progress(f"❌ ERROR: Gamelist file not found after writing!")
                else:
                    task.update_progress(f"❌ WARNING: Game not found in gamelist for ROM file: {rom_file}")
                    task.update_progress(f"Available games in gamelist:")
                    for i, game in enumerate(games):
                        game_path = game.get('path', '')
                        if game_path:
                            task.update_progress(f"  {i+1}. '{game_path}'")
                    
            except Exception as e:
                task.update_progress(f"Warning: Failed to update gamelist: {e}")
        
        task.update_progress(f"YouTube download completed successfully!")
        task.update_progress(f"Video saved to: {output_path}")
        task.update_progress(f"File size: {file_size} bytes")
        task.update_progress(f"Duration: 30 seconds from {start_time}s to {end_time}s")
        
        # Mark task as completed
        task.complete(True)
        
        # Send a signal to refresh the grid (this will be handled by the frontend)
        task.update_progress("Grid refresh signal sent")
        
        # Process next task in queue if any
        process_next_queued_task()
        
    except Exception as e:
        task.complete(False, f'Error in update_gamelist_and_complete: {e}')


def run_youtube_download_task(task_id, data):
    """Run YouTube download task in background thread"""
    global current_task_id
    
    try:
        if not task_id or task_id not in tasks:
            print(f"Error: Task {task_id} not found for YouTube download")
            return
        
        task = tasks[task_id]
        
        # Extract parameters
        video_url = data.get('video_url')
        start_time = data.get('start_time', 0)
        output_filename = data.get('output_filename')
        system_name = data.get('system_name')
        rom_file = data.get('rom_file')  # ROM file path (e.g., "./Pac-Man (USA).nes")
        auto_crop = data.get('auto_crop', False)
        
        # Log the received parameters
        task.update_progress(f"Received parameters:")
        task.update_progress(f"  Video URL: {video_url}")
        task.update_progress(f"  Start time: {start_time} seconds")
        task.update_progress(f"  Output filename: {output_filename}")
        task.update_progress(f"  System: {system_name}")
        task.update_progress(f"  ROM file: {rom_file}")
        task.update_progress(f"  Auto crop: {auto_crop}")
        
        if not all([video_url, output_filename, system_name, rom_file]):
            missing_params = []
            if not video_url: missing_params.append('video_url')
            if not output_filename: missing_params.append('output_filename')
            if not system_name: missing_params.append('system_name')
            if not rom_file: missing_params.append('rom_file')
            task.update_progress(f"ERROR: Missing required parameters: {missing_params}")
            task.complete(False, f'Missing required parameters: {missing_params}')
            return
        
        task.update_progress(f"Starting YouTube download for: {output_filename}")
        task.update_progress(f"Video URL: {video_url}")
        task.update_progress(f"Start time: {start_time} seconds")
        task.update_progress(f"System: {system_name}")
        task.update_progress(f"ROM file: {rom_file}")
        
        # Validate system exists
        system_path = os.path.join(ROMS_FOLDER, system_name)
        if not os.path.exists(system_path):
            task.complete(False, f'System not found: {system_path}')
            return
        
        # Create media/videos directory if it doesn't exist
        videos_dir = os.path.join(system_path, 'media', 'videos')
        os.makedirs(videos_dir, exist_ok=True)
        task.update_progress(f"Created videos directory: {videos_dir}")
        
        # Full output path
        output_path = os.path.join(videos_dir, output_filename)
        task.update_progress(f"Output path: {output_path}")
        
        # Clean up any existing temporary files from previous failed downloads
        try:
            for file in os.listdir(videos_dir):
                if file.startswith('temp_') and (file.endswith('.mp4') or file.endswith('.webm') or file.endswith('.mkv')):
                    temp_file_path = os.path.join(videos_dir, file)
                    os.remove(temp_file_path)
                    task.update_progress(f"Cleaned up old temporary file: {file}")
        except Exception as e:
            task.update_progress(f"Warning: Could not clean up old temporary files: {e}")
        
        # Check if yt-dlp is available
        try:
            import subprocess
            yt_dlp_path = get_yt_dlp_path()
            result = subprocess.run([yt_dlp_path, '--version'], capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                task.complete(False, 'yt-dlp is not installed or not available')
                return
            task.update_progress(f"yt-dlp version: {result.stdout.strip()}")
        except FileNotFoundError:
            task.complete(False, 'yt-dlp is not installed')
            return
        except subprocess.TimeoutExpired:
            task.complete(False, 'yt-dlp check timed out')
            return
        
        # Download video with yt-dlp using optimized section download with fallback
        task.update_progress(f"Attempting optimized section download from {start_time}s to {start_time + 30}s...")
        
        # Use just the filename for output to avoid path issues
        output_filename_only = os.path.basename(output_path)
        # Create temporary filename for download
        temp_filename = f"temp_{output_filename_only}"
        output_template = temp_filename.replace('.mp4', '.%(ext)s')
        
        # Calculate end time for the 30-second section
        end_time = start_time + 30
        
        # First attempt: Optimized section download
        yt_dlp_path = get_yt_dlp_path()
        download_cmd = [
            yt_dlp_path,
            '-f', 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',  # Optimized format selection
            '-o', output_template,  # Output template (just filename)
            '--download-sections', f'*{start_time}-{end_time}',  # Download only the specific section
            '--force-keyframes-at-cuts',  # Ensure clean cuts at keyframes
            '--progress',  # Show progress
            '--newline',   # Progress on new lines
            video_url
        ]
        
        task.update_progress(f"Primary download command: {' '.join(download_cmd)}")
        
        # Run primary download with real-time output capture
        process = subprocess.Popen(
            download_cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.STDOUT, 
            text=True, 
            cwd=videos_dir,
            bufsize=1,
            universal_newlines=True
        )
        
        # Monitor download progress
        section_download_success = False
        for line in iter(process.stdout.readline, ''):
            if line:
                line = line.strip()
                if line:
                    task.update_progress(f"yt-dlp: {line}")
                    # Check for download completion indicators
                    if '[download] 100%' in line or 'has already been downloaded' in line:
                        task.update_progress("Section download completed!")
                        section_download_success = True
                        break
        
        # Wait for download to complete
        process.wait()
        
        if process.returncode == 0 and section_download_success:
            # Section download succeeded - process the file
            task.update_progress("Section download successful! Processing file...")
            
            # Find the actual downloaded temporary file
            downloaded_file = None
            for file in os.listdir(videos_dir):
                if file.startswith(temp_filename.replace('.mp4', '')):
                    downloaded_file = os.path.join(videos_dir, file)
                    break
            
            if downloaded_file and os.path.exists(downloaded_file):
                # Rename temporary file to final output filename
                try:
                    os.rename(downloaded_file, output_path)
                    task.update_progress(f"Renamed temporary file to final filename: {output_path}")
                except Exception as e:
                    task.update_progress(f"Warning: Could not rename temporary file: {e}")
                    # If rename fails, copy the file
                    import shutil
                    shutil.copy2(downloaded_file, output_path)
                    os.remove(downloaded_file)
                    task.update_progress(f"Copied temporary file to final filename: {output_path}")
                
                # Verify the final file exists
                if os.path.exists(output_path):
                    file_size = os.path.getsize(output_path)
                    task.update_progress(f"Final video size: {file_size} bytes")
                    
                    # Apply auto cropping if enabled (BEFORE early return)
                    if auto_crop:
                        try:
                            task.update_progress("Auto cropping enabled - detecting and removing black borders...")
                            task.update_progress(f"Input video path: {output_path}")
                            task.update_progress(f"Video exists: {os.path.exists(output_path)}")
                            
                            # Check if ffmpeg is available
                            try:
                                ffmpeg_result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True, timeout=10)
                                if ffmpeg_result.returncode != 0:
                                    raise Exception("FFmpeg is not available")
                                task.update_progress("FFmpeg is available for cropping")
                            except FileNotFoundError:
                                raise Exception("FFmpeg is not installed")
                            except subprocess.TimeoutExpired:
                                raise Exception("FFmpeg check timed out")
                            
                            # Create temporary file for cropped video
                            cropped_filename = output_filename.replace('.mp4', '_cropped.mp4')
                            cropped_path = os.path.join(videos_dir, cropped_filename)
                            task.update_progress(f"Output cropped path: {cropped_path}")
                            
                            # Apply cropping
                            task.update_progress("Starting crop detection...")
                            crop_result = crop_video(output_path, cropped_path, 0, 30)  # Crop the entire 30-second clip
                            if crop_result:
                                task.update_progress("Crop detection and application completed successfully")
                            else:
                                task.update_progress("Crop process completed but returned False")
                            
                            # Verify cropped file exists
                            if os.path.exists(cropped_path):
                                task.update_progress("Cropped file created successfully")
                                # Replace original with cropped version
                                os.replace(cropped_path, output_path)
                                task.update_progress("Original file replaced with cropped version")
                            else:
                                task.update_progress("Warning: Cropped file was not created")
                            
                            # Update file size
                            file_size = os.path.getsize(output_path)
                            task.update_progress(f"Auto cropping completed! New file size: {file_size} bytes")
                            
                        except Exception as e:
                            task.update_progress(f"Warning: Auto cropping failed: {e}")
                            import traceback
                            task.update_progress(f"Error details: {traceback.format_exc()}")
                            task.update_progress("Continuing with original video...")
                    
                    # Update gamelist.xml and complete task
                    update_gamelist_and_complete(task, system_path, output_filename, output_path, file_size, start_time, end_time, rom_file)
                    return
                else:
                    task.update_progress("Warning: Section download file not found, falling back to full download...")
            else:
                task.update_progress("Warning: Section download file not found, falling back to full download...")
        else:
            task.update_progress(f"Section download failed (return code: {process.returncode}), falling back to full download...")
        
        # Fallback: Download full video and extract clip with FFmpeg
        task.update_progress("Starting fallback: downloading full video and extracting clip...")
        
        # Clean up any partial files from failed section download
        for file in os.listdir(videos_dir):
            if file.startswith(output_filename.replace('.mp4', '')):
                try:
                    os.remove(os.path.join(videos_dir, file))
                    task.update_progress(f"Cleaned up partial file: {file}")
                except Exception as e:
                    task.update_progress(f"Warning: Could not clean up partial file {file}: {e}")
        
        # Download full video to temporary file
        full_download_cmd = [
            yt_dlp_path,
            '-f', 'best[height<=720]',  # Best quality up to 720p for full download
            '-o', output_template,  # Output template (temporary filename)
            '--progress',  # Show progress
            '--newline',   # Progress on new lines
            video_url
        ]
        
        task.update_progress(f"Fallback download command: {' '.join(full_download_cmd)}")
        
        # Run full download
        full_process = subprocess.Popen(
            full_download_cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.STDOUT, 
            text=True, 
            cwd=videos_dir,
            bufsize=1,
            universal_newlines=True
        )
        
        # Monitor full download progress
        for line in iter(full_process.stdout.readline, ''):
            if line:
                line = line.strip()
                if line:
                    task.update_progress(f"yt-dlp (full): {line}")
                    # Check for download completion indicators
                    if '[download] 100%' in line or 'has already been downloaded' in line:
                        task.update_progress("Full video download completed!")
                        break
        
        # Wait for full download to complete
        full_process.wait()
        
        if full_process.returncode != 0:
            task.complete(False, f'Full video download failed with return code: {full_process.returncode}')
            return
        
        # Find the full downloaded temporary file
        full_downloaded_file = None
        for file in os.listdir(videos_dir):
            if file.startswith(temp_filename.replace('.mp4', '')):
                full_downloaded_file = os.path.join(videos_dir, file)
                break
        
        if not full_downloaded_file:
            task.complete(False, 'Full downloaded temporary file not found')
            return
        
        task.update_progress(f"Full video downloaded to temporary file: {full_downloaded_file}")
        
        # Extract 30-second clip using ffmpeg to temporary output file
        task.update_progress(f"Extracting 30-second clip from {start_time}s using FFmpeg...")
        
        # Use relative paths for FFmpeg since it's running from the videos directory
        downloaded_filename = os.path.basename(full_downloaded_file)
        temp_output_filename = f"temp_clip_{output_filename_only}"
        
        clip_cmd = [
            'ffmpeg',
            '-i', downloaded_filename,  # Just the filename
            '-ss', str(start_time),
            '-t', '30',
            '-c', 'copy',  # Copy without re-encoding for speed
            '-avoid_negative_ts', 'make_zero',
            temp_output_filename  # Temporary output filename
        ]
        
        task.update_progress(f"FFmpeg command: {' '.join(clip_cmd)} (running from {videos_dir})")
        
        # Run ffmpeg
        ffmpeg_result = subprocess.run(clip_cmd, capture_output=True, text=True, cwd=videos_dir)
        
        if ffmpeg_result.returncode != 0:
            task.update_progress(f"FFmpeg error: {ffmpeg_result.stderr}")
            task.complete(False, f'Failed to extract clip: {ffmpeg_result.stderr}')
            return
        
        # Clean up the full downloaded video file
        try:
            os.remove(full_downloaded_file)
            task.update_progress("Cleaned up full downloaded video file")
        except Exception as e:
            task.update_progress(f"Warning: Could not clean up full video file: {e}")
        
        # Move temporary clip to final location
        temp_clip_path = os.path.join(videos_dir, temp_output_filename)
        if not os.path.exists(temp_clip_path):
            task.complete(False, 'Temporary clip file not found after FFmpeg extraction')
            return
        
        try:
            os.rename(temp_clip_path, output_path)
            task.update_progress(f"Moved temporary clip to final location: {output_path}")
        except Exception as e:
            task.update_progress(f"Warning: Could not move temporary clip: {e}")
            # If rename fails, copy the file
            import shutil
            shutil.copy2(temp_clip_path, output_path)
            os.remove(temp_clip_path)
            task.update_progress(f"Copied temporary clip to final location: {output_path}")
        
        # Verify the final clip exists
        if not os.path.exists(output_path):
            task.complete(False, 'Final clip file not found after moving from temporary location')
            return
        
        file_size = os.path.getsize(output_path)
        task.update_progress(f"Final clip size: {file_size} bytes")
        
        # Update gamelist.xml and complete task
        update_gamelist_and_complete(task, system_path, output_filename, output_path, file_size, start_time, end_time, rom_file)
        
    except Exception as e:
        print(f"Error in YouTube download task: {e}")
        import traceback
        traceback.print_exc()
        if task_id and task_id in tasks:
            tasks[task_id].complete(False, str(e))

def run_manual_crop_task(task_id, data):
    """Run manual crop task in background thread"""
    global current_task_id
    
    try:
        if not task_id or task_id not in tasks:
            print(f"Error: Task {task_id} not found for manual crop")
            return
        
        task = tasks[task_id]
        
        # Extract parameters
        video_path = data.get('video_path')
        crop_dimensions = data.get('crop_dimensions')
        game_id = data.get('game_id')
        system_name = data.get('system_name')
        rom_file = data.get('rom_file')
        
        # Log the received parameters
        task.update_progress(f"Received parameters:")
        task.update_progress(f"Video path: {video_path}")
        task.update_progress(f"Crop dimensions: {crop_dimensions}")
        task.update_progress(f"Game ID: {game_id}")
        task.update_progress(f"System: {system_name}")
        task.update_progress(f"ROM file: {rom_file}")
        
        # Validate system exists
        system_path = os.path.join(ROMS_FOLDER, system_name)
        if not os.path.exists(system_path):
            task.complete(False, f'System {system_name} not found')
            return
        
        # Check if video file exists
        if not os.path.exists(video_path):
            task.complete(False, f'Video file not found: {video_path}')
            return
        
        # Create videos directory if it doesn't exist
        videos_dir = os.path.join(system_path, 'media', 'videos')
        os.makedirs(videos_dir, exist_ok=True)
        
        # Use original filename (replace the original video)
        original_filename = os.path.basename(video_path)
        output_path = os.path.join(videos_dir, original_filename)
        
        # Create temporary filename for crop
        temp_filename = f"temp_crop_{original_filename}"
        temp_path = os.path.join(videos_dir, temp_filename)
        
        task.update_progress(f"Output path: {output_path}")
        task.update_progress(f"Temporary path: {temp_path}")
        
        # Check if ffmpeg is available
        try:
            result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                task.complete(False, 'ffmpeg is not installed or not available')
                return
            task.update_progress(f"ffmpeg version: {result.stdout.split('ffmpeg version')[1].split()[0]}")
        except FileNotFoundError:
            task.complete(False, 'ffmpeg is not installed')
            return
        except subprocess.TimeoutExpired:
            task.complete(False, 'ffmpeg check timed out')
            return
        
        # Apply crop using ffmpeg
        task.update_progress(f"Applying manual crop with dimensions: {crop_dimensions}")
        
        crop_cmd = [
            'ffmpeg',
            '-i', video_path,
            '-filter:v', f'crop={crop_dimensions}',
            '-c:a', 'copy',  # Copy audio without re-encoding
            '-y',  # Overwrite output file
            temp_path
        ]
        
        task.update_progress(f"FFmpeg command: {' '.join(crop_cmd)}")
        
        # Run ffmpeg
        result = subprocess.run(crop_cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode != 0:
            task.update_progress(f"FFmpeg error: {result.stderr}")
            task.complete(False, f'Failed to apply crop: {result.stderr}')
            return
        
        task.update_progress("Crop applied successfully!")
        
        # Move temporary file to final location
        try:
            os.rename(temp_path, output_path)
            task.update_progress(f"Moved cropped video to final location: {output_path}")
        except Exception as e:
            task.update_progress(f"Warning: Could not move temporary file: {e}")
            # If rename fails, copy the file
            import shutil
            shutil.copy2(temp_path, output_path)
            os.remove(temp_path)
            task.update_progress(f"Copied cropped video to final location: {output_path}")
        
        # Verify the final file exists
        if not os.path.exists(output_path):
            task.complete(False, 'Cropped video file not found after processing')
            return
        
        file_size = os.path.getsize(output_path)
        task.update_progress(f"Final cropped video size: {file_size} bytes")
        
        # Update gamelist.xml with the new cropped video
        try:
            # Find the game in gamelist.xml
            gamelist_path = os.path.join(system_path, 'gamelist.xml')
            if os.path.exists(gamelist_path):
                tree = ET.parse(gamelist_path)
                root = tree.getroot()
                
                # Find the game element by ROM file path
                game_element = None
                for game in root.findall('game'):
                    if game.find('path') is not None:
                        game_path = game.find('path').text
                        if game_path and rom_file and rom_file in game_path:
                            game_element = game
                            task.update_progress(f"Found game element with ROM file: {rom_file}")
                            break
                
                if game_element is None:
                    task.update_progress(f"Could not find game with ROM file: {rom_file}")
                
                if game_element is not None:
                    # Update or add video field
                    video_element = game_element.find('video')
                    if video_element is not None:
                        video_element.text = f"./media/videos/{original_filename}"
                    else:
                        video_element = ET.SubElement(game_element, 'video')
                        video_element.text = f"./media/videos/{original_filename}"
                    
                    # Save the updated gamelist.xml
                    tree.write(gamelist_path, encoding='utf-8', xml_declaration=True)
                    task.update_progress("Updated gamelist.xml with cropped video")
                else:
                    task.update_progress("Warning: Could not find game in gamelist.xml to update")
            
            # Notify clients about the update
            socketio.emit('game_updated', {
                'system': system_name,
                'game_id': game_id,
                'message': 'Video cropped successfully'
            })
            
        except Exception as e:
            task.update_progress(f"Warning: Could not update gamelist.xml: {e}")
        
        # Complete the task
        task.complete(True, f'Manual crop completed successfully. Output: {original_filename}')
        
        # Emit task completion event
        socketio.emit('task_completed', {
            'task_type': 'manual_crop',
            'success': True,
            'message': 'Manual crop completed successfully',
            'game_id': game_id,
            'system_name': system_name
        })
        
    except Exception as e:
        print(f"Error in manual crop task: {e}")
        import traceback
        traceback.print_exc()
        if task_id and task_id in tasks:
            tasks[task_id].complete(False, str(e))
            
            # Emit task failure event
            socketio.emit('task_completed', {
                'task_type': 'manual_crop',
                'success': False,
                'message': str(e),
                'game_id': data.get('game_id'),
                'system_name': data.get('system_name')
            })

def run_2d_box_generation_task(system_name, selected_games):
    """Run 2D box generation task in background thread"""
    global current_task_id
    
    try:
        if not current_task_id or current_task_id not in tasks:
            print(f"Error: No active task found for 2D box generation")
            return
        
        task = tasks[current_task_id]
        
        # Import the box generator
        from box_generator import BoxGenerator
        
        task.update_progress(f"Starting 2D box generation for {len(selected_games)} games")
        task.update_progress(f"System: {system_name}")
        
        # Validate system exists
        system_path = os.path.join(ROMS_FOLDER, system_name)
        if not os.path.exists(system_path):
            task.complete(False, f'System not found: {system_path}')
            return
        
        # Load gamelist to get game data
        gamelist_path = os.path.join(system_path, 'gamelist.xml')
        if not os.path.exists(gamelist_path):
            task.complete(False, f'Gamelist not found: {gamelist_path}')
            return
        
        games = parse_gamelist_xml(gamelist_path)
        if not games:
            task.complete(False, 'No games found in gamelist')
            return
        
        # Create box generator
        generator = BoxGenerator()
        
        # Validate ImageMagick is available
        if not generator.validate_dependencies():
            task.complete(False, 'ImageMagick not available. Please install ImageMagick and Wand library.')
            return
        
        # Load media config to get media mappings
        media_config = load_media_config()
        media_mappings = media_config.get('mappings', {})
        
        # Debug logging
        task.update_progress(f"DEBUG: media_config = {media_config}")
        task.update_progress(f"DEBUG: media_mappings = {media_mappings}")
        
        # Find the media directory for extra1 field
        extra1_directory = None
        for directory, field in media_mappings.items():
            if field == 'extra1':
                extra1_directory = directory
                break
        
        task.update_progress(f"DEBUG: extra1_directory = {extra1_directory}")
        
        if not extra1_directory:
            task.complete(False, f'No media mapping found for extra1 field. Available mappings: {media_mappings}')
            return
        
        # Create media directories
        media_dir = os.path.join(system_path, 'media')
        extra1_dir = os.path.join(media_dir, extra1_directory)
        os.makedirs(extra1_dir, exist_ok=True)
        
        # Process each selected game
        processed = 0
        failed = 0
        
        for i, game_path in enumerate(selected_games):
            if is_task_stopped():
                task.update_progress("🛑 Task stopped by user")
                break
            
            # Find game in gamelist
            game_data = None
            for game in games:
                if game.get('path') == game_path:
                    game_data = game
                    break
            
            if not game_data:
                task.update_progress(f"⚠️  Game not found in gamelist: {game_path}")
                failed += 1
                continue
            
            game_name = game_data.get('name', 'Unknown')
            rom_filename = os.path.splitext(os.path.basename(game_path))[0]
            
            task.update_progress(f"Processing {i+1}/{len(selected_games)}: {game_name}")
            
            # Get required media files
            titlescreen_path = None
            gameplay_path = None
            logo_path = None
            
            # Look for titlescreen (screenshot)
            screenshot = game_data.get('screenshot')
            if screenshot and screenshot.startswith('./'):
                titlescreen_path = os.path.join(system_path, screenshot[2:])
            
            # Look for gameplay (fanart or screenshot as fallback)
            fanart = game_data.get('fanart')
            if fanart and fanart.startswith('./'):
                gameplay_path = os.path.join(system_path, fanart[2:])
            elif screenshot and screenshot.startswith('./'):
                gameplay_path = os.path.join(system_path, screenshot[2:])
            
            # Look for logo (marquee)
            marquee = game_data.get('marquee')
            if marquee and marquee.startswith('./'):
                logo_path = os.path.join(system_path, marquee[2:])
            
            # Check if all required files exist
            missing_files = []
            if not titlescreen_path or not os.path.exists(titlescreen_path):
                missing_files.append('titlescreen (screenshot)')
            if not gameplay_path or not os.path.exists(gameplay_path):
                missing_files.append('gameplay (fanart/screenshot)')
            if not logo_path or not os.path.exists(logo_path):
                missing_files.append('logo (marquee)')
            
            if missing_files:
                task.update_progress(f"⚠️  Missing required media for {game_name}: {', '.join(missing_files)}")
                failed += 1
                continue
            
            # Generate 2D box
            output_filename = f"{rom_filename}.jpg"
            output_path = os.path.join(extra1_dir, output_filename)
            
            try:
                generator.generate_2d_box(
                    titlescreen_path=titlescreen_path,
                    gameplay_path=gameplay_path,
                    logo_path=logo_path,
                    output_path=output_path
                )
                
                # Update gamelist.xml with new boxart
                game_element = None
                tree = ET.parse(gamelist_path)
                root = tree.getroot()
                
                # Find the game element by path (same way as other functions)
                for game in root.findall('game'):
                    if game.find('path') is not None:
                        xml_game_path = game.find('path').text
                        if xml_game_path and xml_game_path == game_path:
                            game_element = game
                            break
                
                if game_element is not None:
                    # Update or add extra1 field
                    extra1_element = game_element.find('extra1')
                    if extra1_element is not None:
                        extra1_element.text = f"./media/{extra1_directory}/{output_filename}"
                    else:
                        extra1_element = ET.SubElement(game_element, 'extra1')
                        extra1_element.text = f"./media/{extra1_directory}/{output_filename}"
                    
                    # Save the updated gamelist.xml
                    tree.write(gamelist_path, encoding='utf-8', xml_declaration=True)
                
                task.update_progress(f"✅ Generated 2D box for {game_name}")
                processed += 1
                
            except Exception as e:
                task.update_progress(f"❌ Failed to generate 2D box for {game_name}: {e}")
                failed += 1
                continue
            
            # Update progress
            progress = int((i + 1) / len(selected_games) * 100)
            task.update_progress(f"Progress: {progress}% ({i+1}/{len(selected_games)})", 
                               progress_percentage=progress, current_step=i+1, total_steps=len(selected_games))
        
        # Complete the task
        if processed > 0:
            task.complete(True, f'2D box generation completed. Generated: {processed}, Failed: {failed}')
        else:
            task.complete(False, f'No 2D boxes were generated. Failed: {failed}')
        
        # Emit task completion event
        socketio.emit('task_completed', {
            'task_type': '2d_box_generation',
            'success': processed > 0,
            'message': f'Generated {processed} 2D boxes, {failed} failed',
            'system_name': system_name
        })
        
    except Exception as e:
        print(f"Error in 2D box generation task: {e}")
        import traceback
        traceback.print_exc()
        if current_task_id and current_task_id in tasks:
            tasks[current_task_id].complete(False, str(e))
        
        # Emit task failure event
        socketio.emit('task_completed', {
            'task_type': '2d_box_generation',
            'success': False,
            'message': str(e),
            'system_name': system_name
        })
    finally:
        # Process next queued task
        process_next_queued_task()

# WebSocket event handlers for real-time updates
@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    print(f"Client connected: {request.sid}")
    emit('connected', {'message': 'Connected to server'})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    client_sid = request.sid
    print(f"Client disconnected: {client_sid}")
    
    # Clean up tracking with thread safety
    if client_sid in client_systems:
        system_name = client_systems[client_sid]
        with system_clients_lock:
            if system_name in system_clients:
                system_clients[system_name].discard(client_sid)
                if not system_clients[system_name]:
                    del system_clients[system_name]
        del client_systems[client_sid]
        print(f"Cleaned up tracking for disconnected client {client_sid} from system {system_name}")

@socketio.on('join_system')
def handle_join_system(data):
    """Handle client joining a system room for real-time updates"""
    system_name = data.get('system')
    if system_name:
        client_sid = request.sid
        
        # Clean up previous system tracking with thread safety
        if client_sid in client_systems:
            old_system = client_systems[client_sid]
            with system_clients_lock:
                if old_system in system_clients:
                    system_clients[old_system].discard(client_sid)
                    if not system_clients[old_system]:
                        del system_clients[old_system]
            print(f"Client {client_sid} removed from system {old_system}")
            # Leave the old system room
            leave_room(f'system_{old_system}')
        
        # Join the new system room
        join_room(f'system_{system_name}')
        
        # Update tracking with thread safety
        client_systems[client_sid] = system_name
        with system_clients_lock:
            if system_name not in system_clients:
                system_clients[system_name] = set()
            system_clients[system_name].add(client_sid)
            client_count = len(system_clients[system_name])
        
        print(f"Client {client_sid} joined system room: {system_name}")
        print(f"System {system_name} now has {client_count} clients")
        
        emit('joined_system', {'system': system_name, 'message': f'Joined {system_name} room'})

@socketio.on('leave_system')
def handle_leave_system(data):
    """Handle client leaving a system room"""
    try:
        system_name = data.get('system')
        if system_name:
            client_sid = request.sid
            room_name = f'system_{system_name}'
            
            leave_room(room_name)
            
            # Clean up tracking with thread safety
            if client_sid in client_systems:
                del client_systems[client_sid]
            with system_clients_lock:
                if system_name in system_clients:
                    system_clients[system_name].discard(client_sid)
                    if not system_clients[system_name]:
                        del system_clients[system_name]
                        client_count = 0
                    else:
                        client_count = len(system_clients[system_name])
                else:
                    client_count = 0
            
            print(f"Client {client_sid} left system room: {system_name}")
            if client_count > 0:
                print(f"System {system_name} now has {client_count} clients")
            else:
                print(f"System {system_name} has no more clients")
            
            emit('left_system', {'system': system_name, 'message': f'Left {system_name} room'})
    except Exception as e:
        print(f"Error in handle_leave_system: {e}")
        import traceback
        traceback.print_exc()

def notify_system_update(system_name, action, data=None):
    """Notify all clients in a system room about updates"""
    if system_name:
        room = f'system_{system_name}'
        
        # Use our tracking system to get accurate client count with thread safety
        with system_clients_lock:
            client_count = len(system_clients.get(system_name, set()))
        print(f"🔔 Notifying room {room} about {action} - {client_count} clients tracked in system {system_name}")
        
        if client_count > 0:
            # Send to the specific room (Flask-SocketIO will handle the routing)
            socketio.emit('system_updated', {
                'system': system_name,
                'action': action,
                'data': data,
                'timestamp': datetime.now().isoformat()
            }, room=room)
            print(f"✅ Notification sent to room {room} for {action} ({client_count} clients)")
        else:
            print(f"⚠️  System {system_name} has no clients to notify")

def notify_gamelist_updated(system_name, games_count, deleted_count=0, updated_count=0):
    """Notify all clients when gamelist.xml is updated"""
    print(f"🔔 About to notify gamelist update for system: {system_name}")
    debug_client_tracking()
    notify_system_update(system_name, 'gamelist_updated', {
        'games_count': games_count,
        'deleted_count': deleted_count,
        'updated_count': updated_count,
        'message': f'Gamelist updated: {games_count} total games, {updated_count} games updated, {deleted_count} deleted'
    })

def notify_game_deleted(system_name, deleted_files):
    """Notify all clients when games are deleted"""
    notify_system_update(system_name, 'games_deleted', {
        'deleted_files': deleted_files,
        'message': f'Deleted {len(deleted_files)} files'
    })

def notify_game_updated(system_name, game_name, changes):
    """Notify all clients when a game is updated"""
    print(f"🔔 About to notify game update for system: {system_name}, game: {game_name}")
    debug_client_tracking()
    notify_system_update(system_name, 'game_updated', {
        'game_name': game_name,
        'changes': changes,
        'message': f'Game updated: {game_name}'
    })

def debug_client_tracking():
    """Debug function to show current client tracking state"""
    print("🔍 Current client tracking state:")
    print(f"  Total clients: {len(client_systems)}")
    with system_clients_lock:
        print(f"  Systems with clients: {list(system_clients.keys())}")
        for system, clients in system_clients.items():
            print(f"  System {system}: {len(clients)} clients")
            for client_sid in clients:
                print(f"    - Client {client_sid[:8]}...")

@app.route('/api/debug/clients')
@login_required
def debug_clients_endpoint():
    """Debug endpoint to check current client tracking state"""
    with system_clients_lock:
        return jsonify({
            'client_systems': {k: v for k, v in client_systems.items()},
            'system_clients': {k: list(v) for k, v in system_clients.items()},
            'total_clients': len(client_systems),
            'systems_with_clients': list(system_clients.keys())
        })

@app.route('/api/media-mappings')
def get_media_mappings():
    """Get media mappings from config.json for dynamic UI generation"""
    try:
        media_mappings = config.get('media', {}).get('mappings', {})
        return jsonify({
            'success': True,
            'mappings': media_mappings
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Authentication Routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember_me = request.form.get('remember_me')
        
        if not username or not password:
            flash('Please fill in all fields', 'error')
            return render_template('login.html')
        
        # Check if user exists and password is correct
        users = load_users()
        user = None
        for user_id, user_data in users.items():
            if user_data['username'] == username:
                if verify_password(password, user_data['password_hash']):
                    user = User(
                        user_id=user_id,
                        username=user_data['username'],
                        email=user_data.get('email'),
                        discord_id=user_data.get('discord_id'),
                        is_active=user_data.get('is_active', True),
                        is_validated=user_data.get('is_validated', False),
                        created_at=user_data.get('created_at'),
                        last_login=user_data.get('last_login')
                    )
                    break
        
        if user and user.is_active:
            if user.is_validated:
                print(f"Logging in user: {user.username}")
                print(f"Session before login: {dict(session)}")
                login_user(user, remember=remember_me)
                print(f"Session after login: {dict(session)}")
                update_user_last_login(user.id)
                flash(f'Welcome back, {user.username}!', 'success')
                next_page = request.args.get('next')
                return redirect(next_page) if next_page else redirect(url_for('index'))
            else:
                flash('Your account is pending validation. Please contact an administrator.', 'warning')
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        terms = request.form.get('terms')
        
        # Validation
        if not username or not password or not confirm_password:
            flash('Please fill in all required fields', 'error')
            return render_template('register.html')
        
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('register.html')
        
        if len(username) < 3 or len(username) > 20:
            flash('Username must be between 3 and 20 characters', 'error')
            return render_template('register.html')
        
        if len(password) < 6:
            flash('Password must be at least 6 characters long', 'error')
            return render_template('register.html')
        
        if not terms:
            flash('You must accept the Terms of Service', 'error')
            return render_template('register.html')
        
        # Create user
        user, error = create_user(username, password, email)
        if user:
            flash('Account created successfully! Your account is pending validation by an administrator.', 'success')
            return redirect(url_for('login'))
        else:
            flash(error or 'Failed to create account', 'error')
    
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out successfully', 'info')
    return redirect(url_for('login'))

@app.route('/discord/login')
def discord_login():
    # Discord OAuth2 URL
    discord_config = config.get('discord', {})
    discord_client_id = discord_config.get('client_id', 'your_discord_client_id')
    discord_redirect_uri = discord_config.get('redirect_uri', url_for('discord_callback', _external=True))
    discord_scope = discord_config.get('scope', 'identify email')
    
    discord_url = f"https://discord.com/api/oauth2/authorize?client_id={discord_client_id}&redirect_uri={discord_redirect_uri}&response_type=code&scope={discord_scope}"
    return redirect(discord_url)

@app.route('/discord/register')
def discord_register():
    # Same as login but we'll handle registration in the callback
    return redirect(url_for('discord_login'))

@app.route('/discord/callback')
def discord_callback():
    code = request.args.get('code')
    if not code:
        flash('Discord authentication failed', 'error')
        return redirect(url_for('login'))
    
    # Exchange code for access token
    discord_config = config.get('discord', {})
    discord_client_id = discord_config.get('client_id', 'your_discord_client_id')
    discord_client_secret = discord_config.get('client_secret', 'your_discord_client_secret')
    discord_redirect_uri = discord_config.get('redirect_uri', url_for('discord_callback', _external=True))
    
    token_data = {
        'client_id': discord_client_id,
        'client_secret': discord_client_secret,
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': discord_redirect_uri
    }
    
    try:
        response = requests.post('https://discord.com/api/oauth2/token', data=token_data)
        if response.status_code == 200:
            token_info = response.json()
            access_token = token_info['access_token']
            
            # Get user info from Discord
            headers = {'Authorization': f'Bearer {access_token}'}
            user_response = requests.get('https://discord.com/api/users/@me', headers=headers)
            
            if user_response.status_code == 200:
                discord_user = user_response.json()
                discord_id = discord_user['id']
                username = discord_user['username']
                email = discord_user.get('email')
                
                # Check if user already exists
                user = get_user_by_discord_id(discord_id)
                if user:
                    if user.is_active and user.is_validated:
                        login_user(user)
                        update_user_last_login(user.id)
                        flash(f'Welcome back, {user.username}!', 'success')
                        return redirect(url_for('index'))
                    else:
                        flash('Your account is pending validation. Please contact an administrator.', 'warning')
                        return redirect(url_for('login'))
                else:
                    # Create new user with Discord info
                    user, error = create_user(username, secrets.token_hex(16), email, discord_id)
                    if user:
                        flash('Account created successfully! Your account is pending validation by an administrator.', 'success')
                        return redirect(url_for('login'))
                    else:
                        flash(error or 'Failed to create account', 'error')
            else:
                flash('Failed to get Discord user information', 'error')
        else:
            flash('Discord authentication failed', 'error')
    except Exception as e:
        print(f"Discord authentication error: {e}")
        flash('Discord authentication failed', 'error')
    
    return redirect(url_for('login'))

# User Management Routes (for admins)
@app.route('/admin/users')
@login_required
def admin_users():
    # Check if user is validated (basic admin check)
    if not current_user.is_validated:
        flash('Access denied. You need to be validated to access this page.', 'error')
        return redirect(url_for('index'))
    
    users = load_users()
    user_list = []
    for user_id, user_data in users.items():
        user_list.append({
            'id': user_id,
            'username': user_data['username'],
            'email': user_data.get('email'),
            'discord_id': user_data.get('discord_id'),
            'is_active': user_data.get('is_active', True),
            'is_validated': user_data.get('is_validated', False),
            'created_at': user_data.get('created_at'),
            'last_login': user_data.get('last_login')
        })
    
    return render_template('admin_users.html', users=user_list)

@app.route('/admin/users/<user_id>/validate', methods=['POST'])
@login_required
def validate_user(user_id):
    if not current_user.is_validated:
        return jsonify({'error': 'Access denied'}), 403
    
    users = load_users()
    if user_id in users:
        users[user_id]['is_validated'] = True
        save_users(users)
        return jsonify({'success': True, 'message': 'User validated successfully'})
    
    return jsonify({'error': 'User not found'}), 404

@app.route('/admin/users/<user_id>/deactivate', methods=['POST'])
@login_required
def deactivate_user(user_id):
    if not current_user.is_validated:
        return jsonify({'error': 'Access denied'}), 403
    
    users = load_users()
    if user_id in users:
        users[user_id]['is_active'] = False
        save_users(users)
        return jsonify({'success': True, 'message': 'User deactivated successfully'})
    
    return jsonify({'error': 'User not found'}), 404

@app.route('/admin/users/<user_id>/activate', methods=['POST'])
@login_required
def activate_user(user_id):
    if not current_user.is_validated:
        return jsonify({'error': 'Access denied'}), 403
    
    users = load_users()
    if user_id in users:
        users[user_id]['is_active'] = True
        save_users(users)
        return jsonify({'success': True, 'message': 'User activated successfully'})
    
    return jsonify({'error': 'User not found'}), 404

def _matches_media_type(image_type, requested_media_type, media_directory):
    """Check if an image type matches the requested media type using config mappings"""
    # Load the LaunchBox configuration from config
    launchbox_config = config.get('launchbox', {})
    image_type_mappings = launchbox_config.get('image_type_mappings', {})
    
    # Check if this image type maps to the requested media type
    mapped_media_type = image_type_mappings.get(image_type)
    
    # Return True if the image type maps to the requested media type
    return mapped_media_type == requested_media_type

@app.route('/api/launchbox-media/<launchbox_id>/<media_type>', methods=['GET'])
@login_required
def get_launchbox_media(launchbox_id, media_type):
    """Get available media from LaunchBox database for a specific game and media type"""
    try:
        if not launchbox_id or launchbox_id == 'None':
            return jsonify({'error': 'LaunchBox ID is required'}), 400
        
        # Load media config to get media mappings
        media_config = load_media_config()
        media_mappings = media_config.get('mappings', {})
        
        # Debug logging
        print(f"DEBUG: media_type = {media_type}")
        print(f"DEBUG: media_mappings = {media_mappings}")
        
        # Load image config for base URL
        image_config = load_image_mappings()
        
        # Find the media type mapping
        media_directory = None
        for key, value in media_mappings.items():
            if value == media_type:
                media_directory = key
                break
        
        if not media_directory:
            return jsonify({'error': f'Unknown media type: {media_type}. Available mappings: {media_mappings}'}), 400
        
        # Use the global global_metadata_cache (should already be loaded at startup)
        if not global_metadata_cache:
            # Fallback: load cache if not already loaded
            load_metadata_cache()
        
        # Get game metadata from global global_metadata_cache
        game_metadata = global_metadata_cache.get(launchbox_id)
        if not game_metadata:
            return jsonify({'error': 'Game not found in LaunchBox database'}), 404
        
        # Get available media for this type
        available_media = []
        
        
        # The metadata structure has 'images' array containing XML elements
        if game_metadata and 'images' in game_metadata:
            for image_element in game_metadata['images']:
                # Parse the XML element to get image details
                type_elem = image_element.find('Type')
                if type_elem is not None and type_elem.text:
                    image_type = type_elem.text.strip()
                    
                    # Check if this image type matches what we're looking for
                    if _matches_media_type(image_type, media_type, media_directory):
                        filename_elem = image_element.find('FileName')
                        region_elem = image_element.find('Region')
                        
                        if filename_elem is not None and filename_elem.text:
                            base_url = image_config.get('launchbox_image_base_url', 'https://images.launchbox-app.com/')
                            media_url = base_url + filename_elem.text
                            
                            available_media.append({
                                'url': media_url,
                                'filename': filename_elem.text,
                                'region': region_elem.text if region_elem is not None and region_elem.text else 'Unknown',
                                'primary': False,  # We don't have primary info in this structure
                                'type': image_type
                            })
        
        # Sort by primary first, then by region
        available_media.sort(key=lambda x: (not x.get('primary', False), x.get('region', '')))
        
        return jsonify({
            'success': True,
            'media': available_media,
            'count': len(available_media)
        })
        
    except Exception as e:
        print(f"Error fetching LaunchBox media: {e}")
        return jsonify({'error': f'Failed to fetch media: {str(e)}'}), 500

@app.route('/api/generate-2d-box', methods=['POST'])
@login_required
def generate_2d_box():
    """Start 2D box generation task for selected games"""
    try:
        data = request.get_json()
        system_name = data.get('system_name')
        selected_games = data.get('selected_games', [])
        
        if not system_name or not selected_games:
            return jsonify({'error': 'Missing required parameters'}), 400
        
        # Add task to queue
        task = add_task_to_queue('2d_box_generation', {
            'system_name': system_name,
            'selected_games': selected_games
        })
        
        return jsonify({
            'success': True,
            'task_id': task.id,
            'games_count': len(selected_games)
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to start 2D box generation: {str(e)}'}), 500

@app.route('/api/download-launchbox-media', methods=['POST'])
@login_required
def download_launchbox_media():
    """Download and replace a specific media file from LaunchBox"""
    print(f"DEBUG: download_launchbox_media called with data: {request.get_json()}")
    try:
        data = request.get_json()
        game_id = data.get('game_id')
        media_type = data.get('media_type')
        media_url = data.get('media_url')
        region = data.get('region', 'Unknown')
        system_name = data.get('system_name')
        
        if not all([game_id, media_type, media_url, system_name]):
            return jsonify({'error': 'Missing required parameters'}), 400
        
        # Load media config to get media mappings
        media_config = load_media_config()
        media_mappings = media_config.get('mappings', {})
        
        # Load image config for base URL
        image_config = load_image_mappings()
        
        # Find the media directory
        media_directory = None
        for key, value in media_mappings.items():
            if value == media_type:
                media_directory = key
                break
        
        if not media_directory:
            return jsonify({'error': f'Unknown media type: {media_type}'}), 400
        
        # Get the game from the current system
        system_path = os.path.join(ROMS_FOLDER, system_name)
        gamelist_path = os.path.join(system_path, 'gamelist.xml')
        
        if not os.path.exists(gamelist_path):
            return jsonify({'error': 'Gamelist not found'}), 404
        
        # Parse gamelist to find the game
        tree = ET.parse(gamelist_path)
        root = tree.getroot()
        
        game_element = None
        # Find by launchboxid
        for game in root.findall('game'):
            launchboxid_elem = game.find('launchboxid')
            if launchboxid_elem is not None and launchboxid_elem.text == game_id:
                game_element = game
                break
        
        if not game_element:
            return jsonify({'error': 'Game not found in gamelist'}), 404
        
        # Get ROM filename for naming the media file
        rom_path = game_element.find('path')
        if rom_path is None or rom_path.text is None:
            return jsonify({'error': 'Game path not found'}), 400
        
        rom_filename = os.path.splitext(os.path.basename(rom_path.text))[0]
        
        # Create media directory if it doesn't exist
        media_dir = os.path.join(system_path, 'media', media_directory)
        os.makedirs(media_dir, exist_ok=True)
        
        # Determine file extension from URL
        file_extension = os.path.splitext(media_url.split('/')[-1])[1]
        if not file_extension:
            file_extension = '.jpg'  # Default to jpg
        
        # Create local filename
        local_filename = f"{rom_filename}{file_extension}"
        local_path = os.path.join(media_dir, local_filename)
        
        # Download the media file
        import requests
        response = requests.get(media_url, timeout=30)
        response.raise_for_status()
        
        # Save the file
        with open(local_path, 'wb') as f:
            f.write(response.content)
        
        # Update gamelist.xml
        media_field = game_element.find(media_type)
        if media_field is not None:
            media_field.text = f"./media/{media_directory}/{local_filename}"
        else:
            # Create new media field
            new_media_field = ET.SubElement(game_element, media_type)
            new_media_field.text = f"./media/{media_directory}/{local_filename}"
        
        # Save the updated gamelist
        tree.write(gamelist_path, encoding='utf-8', xml_declaration=True)
        
        return jsonify({
            'success': True,
            'message': f'Media downloaded and replaced successfully',
            'local_path': local_path,
            'gamelist_field': media_type
        })
        
    except Exception as e:
        print(f"Error downloading LaunchBox media: {e}")
        return jsonify({'error': f'Failed to download media: {str(e)}'}), 500

# =============================================================================
# IGDB Integration Functions
# =============================================================================

def get_igdb_config():
    """Get IGDB configuration from config.json"""
    try:
        config = load_config()
        return config.get('igdb', {})
    except Exception as e:
        print(f"Error loading IGDB config: {e}")
        return {}

def ensure_igdb_directory():
    """Ensure IGDB database directory exists"""
    try:
        igdb_config = get_igdb_config()
        igdb_dir = igdb_config.get('database_directory', 'var/db/igdb')
        os.makedirs(igdb_dir, exist_ok=True)
        return igdb_dir
    except Exception as e:
        print(f"Error creating IGDB directory: {e}")
        return None

def get_igdb_access_token():
    """Get IGDB access token"""
    try:
        igdb_config = get_igdb_config()
        if not igdb_config.get('enabled', False):
            return None
            
        client_id = igdb_config.get('client_id')
        client_secret = igdb_config.get('client_secret')
        
        if not client_id or not client_secret:
            print("IGDB credentials not configured")
            return None
        
        # Get access token from IGDB
        import httpx
        
        token_url = "https://id.twitch.tv/oauth2/token"
        token_data = {
            'client_id': client_id,
            'client_secret': client_secret,
            'grant_type': 'client_credentials'
        }
        
        with httpx.Client(http2=True) as client:
            response = client.post(token_url, data=token_data)
            
            if response.status_code == 200:
                token_info = response.json()
                return token_info.get('access_token')
            else:
                print(f"Failed to get IGDB access token: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"Error getting IGDB access token: {e}")
        return None

async def make_igdb_request_with_retry(async_client, url, headers, data, max_retries=3):
    """Make an IGDB API request with retry logic for rate limiting"""
    import asyncio
    
    for attempt in range(max_retries):
        try:
            response = await async_client.post(url, headers=headers, content=data)
            
            if response.status_code == 200:
                return response
            elif response.status_code == 429:
                # Rate limited - wait and retry
                wait_time = (2 ** attempt) + 1  # Exponential backoff: 2, 5, 9 seconds
                print(f"IGDB API rate limited (429), waiting {wait_time}s before retry {attempt + 1}/{max_retries}")
                await asyncio.sleep(wait_time)
                continue
            else:
                print(f"IGDB API error: {response.status_code} - {response.text}")
                return response
                
        except Exception as e:
            print(f"IGDB API request error (attempt {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                wait_time = (2 ** attempt) + 1
                await asyncio.sleep(wait_time)
                continue
            else:
                raise e
    
    return None

async def search_igdb_game_by_name_async(game_name, platform_id, access_token, client_id, async_client):
    """Search for a game in IGDB by name and platform (async)"""
    try:
        import re
        
        # Clean game name - remove parentheses and extra text
        clean_name = re.sub(r'\s*\([^)]*\)', '', game_name).strip()
        clean_name = re.sub(r'\s*\[[^\]]*\]', '', clean_name).strip()
        
        # Search for games with more detailed fields
        search_url = "https://api.igdb.com/v4/games"
        search_data = f'fields id,name,summary,first_release_date,platforms,genres,total_rating,rating_count,player_perspectives,game_modes,cover,screenshots,artworks; search "{clean_name}"; where platforms = ({platform_id}); limit 10;'
        
        headers = {
            'Client-ID': client_id,
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'text/plain'
        }
        
        # Make the request with retry logic
        response = await make_igdb_request_with_retry(async_client, search_url, headers, search_data)
        
        if response and response.status_code == 200:
            games = response.json()
            if games:
                # Return the first match (best match)
                return games[0]
            else:
                # No games found for this platform
                return None
        else:
            if response:
                print(f"IGDB API error: {response.status_code} - {response.text}")
        
        return None
        
    except Exception as e:
        print(f"Error searching IGDB for game '{game_name}': {e}")
        return None

async def fetch_igdb_game_by_id_async(game_id, access_token, client_id, async_client):
    """Fetch a specific game from IGDB by ID"""
    try:
        search_url = "https://api.igdb.com/v4/games"
        search_data = f'fields id,name,summary,first_release_date,platforms,genres,total_rating,rating_count,player_perspectives,game_modes,cover,screenshots,artworks; where id = {game_id};'
        
        headers = {
            'Client-ID': client_id,
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'text/plain'
        }
        
        # Make the request with retry logic
        response = await make_igdb_request_with_retry(async_client, search_url, headers, search_data)
        
        if response and response.status_code == 200:
            games = response.json()
            if games:
                return games[0]  # Return the first (and only) game
            else:
                print(f"No game found with ID {game_id}")
                return None
        else:
            if response:
                print(f"IGDB API error: {response.status_code} - {response.text}")
            return None
        
    except Exception as e:
        print(f"Error fetching IGDB game by ID {game_id}: {e}")
        return None

async def fetch_igdb_involved_companies(async_client, access_token, client_id, game_id):
    """Fetch involved companies for a specific game"""
    try:
        search_url = "https://api.igdb.com/v4/involved_companies"
        search_data = f'fields company,developer,publisher; where game = {game_id};'
        
        headers = {
            'Client-ID': client_id,
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'text/plain'
        }
        
        # Make the request with retry logic
        response = await make_igdb_request_with_retry(async_client, search_url, headers, search_data)
        
        if response and response.status_code == 200:
            return response.json()
        else:
            if response:
                print(f"IGDB involved companies API error: {response.status_code} - {response.text}")
            return []
    except Exception as e:
        print(f"Error fetching IGDB involved companies: {e}")
        return []

async def fetch_igdb_artworks(async_client, access_token, client_id, game_id):
    """Fetch artworks for a specific game and return the first landscape image"""
    try:
        print(f"🎨 DEBUG: fetch_igdb_artworks called for game_id: {game_id}")
        search_url = "https://api.igdb.com/v4/artworks"
        search_data = f'fields id,image_id,width,height,url; where game = {game_id};'
        
        print(f"🎨 DEBUG: Artworks API request - URL: {search_url}")
        print(f"🎨 DEBUG: Artworks API request - Data: {search_data}")
        
        headers = {
            'Client-ID': client_id,
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'text/plain'
        }
        
        # Make the request with retry logic
        response = await make_igdb_request_with_retry(async_client, search_url, headers, search_data)
        
        if response and response.status_code == 200:
            artworks = response.json()
            print(f"🎨 DEBUG: Received {len(artworks)} artworks from API")
            
            # Debug: Print all artworks
            for i, artwork in enumerate(artworks):
                width = artwork.get('width', 0)
                height = artwork.get('height', 0)
                image_id = artwork.get('image_id', 'N/A')
                url = artwork.get('url', 'N/A')
                print(f"🎨 DEBUG: Artwork {i+1}: id={artwork.get('id')}, image_id={image_id}, width={width}, height={height}, url={url}")
            
            # Filter for landscape images (width >= 1.5 * height)
            landscape_artworks = []
            for artwork in artworks:
                width = artwork.get('width', 0)
                height = artwork.get('height', 0)
                if width > 0 and height > 0 and width >= (1.5 * height):
                    landscape_artworks.append(artwork)
                    print(f"🎨 DEBUG: Found landscape artwork: {artwork.get('id')} ({width}x{height})")
            
            print(f"🎨 DEBUG: Found {len(landscape_artworks)} landscape artworks")
            
            # Return the first landscape artwork
            if landscape_artworks:
                selected = landscape_artworks[0]
                print(f"🎨 DEBUG: Selected artwork: {selected.get('id')} with image_id: {selected.get('image_id')} and url: {selected.get('url')}")
                return selected
            else:
                print(f"🎨 DEBUG: No landscape artworks found for game {game_id}")
                return None
        else:
            if response:
                print(f"🎨 DEBUG: IGDB artworks API error: {response.status_code} - {response.text}")
            else:
                print(f"🎨 DEBUG: No response received from artworks API")
            return None
    except Exception as e:
        print(f"🎨 DEBUG: Error fetching IGDB artworks: {e}")
        import traceback
        traceback.print_exc()
        return None

async def fetch_igdb_logos(async_client, access_token, client_id, game_id):
    """Fetch logos for a specific game and return the first one"""
    try:
        print(f"🏷️ DEBUG: fetch_igdb_logos called for game_id: {game_id}")
        search_url = "https://api.igdb.com/v4/artworks"
        search_data = f'fields id,image_id,width,height,url,artwork_type; where game = {game_id} & artwork_type = 7;'
        
        print(f"🏷️ DEBUG: Logos API request - URL: {search_url}")
        print(f"🏷️ DEBUG: Logos API request - Data: {search_data}")
        
        headers = {
            'Client-ID': client_id,
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'text/plain'
        }
        
        # Make the request with retry logic
        response = await make_igdb_request_with_retry(async_client, search_url, headers, search_data)
        
        if response and response.status_code == 200:
            logos = response.json()
            print(f"🏷️ DEBUG: Received {len(logos)} logos from API")
            
            # Debug: Print all logos
            for i, logo in enumerate(logos):
                width = logo.get('width', 0)
                height = logo.get('height', 0)
                image_id = logo.get('image_id', 'N/A')
                url = logo.get('url', 'N/A')
                artwork_type = logo.get('artwork_type', 'N/A')
                print(f"🏷️ DEBUG: Logo {i+1}: id={logo.get('id')}, image_id={image_id}, width={width}, height={height}, url={url}, artwork_type={artwork_type}")
            
            # Return the first logo if any exist (use original format)
            if logos:
                selected = logos[0]
                print(f"🏷️ DEBUG: Selected logo: {selected.get('id')} with image_id: {selected.get('image_id')} and url: {selected.get('url')}")
                return selected
            else:
                print(f"🏷️ DEBUG: No logos found for game {game_id}")
                return None
        else:
            if response:
                print(f"🏷️ DEBUG: IGDB logos API error: {response.status_code} - {response.text}")
            else:
                print(f"🏷️ DEBUG: No response received from logos API")
            return None
    except Exception as e:
        print(f"🏷️ DEBUG: Error fetching IGDB logos: {e}")
        import traceback
        traceback.print_exc()
        return None

async def fetch_igdb_screenshots(async_client, access_token, client_id, game_id):
    """Fetch screenshots for a specific game and return the first one"""
    try:
        print(f"📸 DEBUG: fetch_igdb_screenshots called for game_id: {game_id}")
        search_url = "https://api.igdb.com/v4/screenshots"
        search_data = f'fields id,image_id,width,height,url; where game = {game_id};'
        
        print(f"📸 DEBUG: Screenshots API request - URL: {search_url}")
        print(f"📸 DEBUG: Screenshots API request - Data: {search_data}")
        
        headers = {
            'Client-ID': client_id,
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'text/plain'
        }
        
        # Make the request with retry logic
        response = await make_igdb_request_with_retry(async_client, search_url, headers, search_data)
        
        if response and response.status_code == 200:
            screenshots = response.json()
            print(f"📸 DEBUG: Received {len(screenshots)} screenshots from API")
            
            # Debug: Print all screenshots
            for i, screenshot in enumerate(screenshots):
                width = screenshot.get('width', 0)
                height = screenshot.get('height', 0)
                image_id = screenshot.get('image_id', 'N/A')
                url = screenshot.get('url', 'N/A')
                print(f"📸 DEBUG: Screenshot {i+1}: id={screenshot.get('id')}, image_id={image_id}, width={width}, height={height}, url={url}")
            
            # Return the first screenshot
            if screenshots:
                selected = screenshots[0]
                print(f"📸 DEBUG: Selected screenshot: {selected.get('id')} with image_id: {selected.get('image_id')} and url: {selected.get('url')}")
                return selected
            else:
                print(f"📸 DEBUG: No screenshots found for game {game_id}")
                return None
        else:
            if response:
                print(f"📸 DEBUG: IGDB screenshots API error: {response.status_code} - {response.text}")
            else:
                print(f"📸 DEBUG: No response received from screenshots API")
            return None
    except Exception as e:
        print(f"📸 DEBUG: Error fetching IGDB screenshots: {e}")
        import traceback
        traceback.print_exc()
        return None

# =============================================================================
# IGDB Regions Cache
# =============================================================================

def get_igdb_regions_cache_path():
    """Get the path to the IGDB regions cache file"""
    cache_dir = ensure_igdb_directory()
    if cache_dir:
        return os.path.join(cache_dir, 'regions_cache.json')
    return None

def load_igdb_regions_cache():
    """Load IGDB regions cache from file"""
    cache_path = get_igdb_regions_cache_path()
    if cache_path and os.path.exists(cache_path):
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading IGDB regions cache: {e}")
    return {}

def save_igdb_regions_cache(cache):
    """Save IGDB regions cache to file"""
    cache_path = get_igdb_regions_cache_path()
    if cache_path:
        try:
            os.makedirs(os.path.dirname(cache_path), exist_ok=True)
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(cache, f, indent=2, ensure_ascii=False)
            print(f"✅ Saved IGDB regions cache with {len(cache)} entries")
        except Exception as e:
            print(f"Error saving IGDB regions cache: {e}")

def get_igdb_region_name(region_id, regions_cache):
    """Get region name from region ID"""
    if region_id in regions_cache:
        return regions_cache[region_id].get('name', 'Unknown')
    return 'Unknown'

async def ensure_igdb_regions_cache(async_client, access_token, client_id):
    """Ensure IGDB regions cache is populated"""
    cache = load_igdb_regions_cache()
    
    if not cache:
        print("🔄 IGDB regions cache is empty, fetching from API...")
        try:
            search_url = "https://api.igdb.com/v4/regions"
            search_data = 'fields id,name; limit 50;'
            
            headers = {
                'Client-ID': client_id,
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'text/plain'
            }
            
            response = await make_igdb_request_with_retry(async_client, search_url, headers, search_data)
            
            if response and response.status_code == 200:
                regions = response.json()
                print(f"🌍 Found {len(regions)} regions")
                
                for region in regions:
                    cache[region['id']] = {
                        'name': region.get('name', '')
                    }
                
                save_igdb_regions_cache(cache)
            else:
                print(f"❌ Failed to fetch IGDB regions: {response.status_code if response else 'No response'}")
        except Exception as e:
            print(f"❌ Error fetching IGDB regions: {e}")
    
    return cache

def get_igdb_region_priority():
    """Get IGDB region priority from config"""
    try:
        config = load_config()
        igdb_config = config.get('igdb', {})
        return igdb_config.get('region_priority', [
            "World",
            "North America", 
            "Europe",
            "Japan"
        ])
    except Exception as e:
        print(f"Error loading IGDB region priority: {e}")
        return ["World", "North America", "Europe", "Japan"]

def extract_region_from_game_name(game_name):
    """Extract region from game name if it's in parentheses"""
    import re
    # Look for region in parentheses at the end
    match = re.search(r'\(([^)]+)\)$', game_name)
    if match:
        region = match.group(1).strip()
        print(f"🌍 DEBUG: Extracted region from game name: '{region}'")
        return region
    return None

def find_matching_cover(covers, target_region, regions_cache, game_localizations):
    """Find cover that matches the target region or uses region priority"""
    if not covers:
        return None
    
    # If we have a target region from game name, try to match it
    if target_region:
        print(f"🌍 DEBUG: Looking for cover matching region: '{target_region}'")
        
        # First, try exact match
        for cover in covers:
            if cover.get('game_localization'):
                # Get the region ID from game_localization
                localization = game_localizations.get(cover['game_localization'])
                if localization and localization.get('region'):
                    region_name = get_igdb_region_name(localization['region'], regions_cache)
                    print(f"🌍 DEBUG: Cover {cover.get('id')} has region: '{region_name}'")
                    
                    # Normalize both regions for comparison
                    target_normalized = target_region.lower().strip()
                    region_normalized = region_name.lower().strip()
                    
                    if region_normalized == target_normalized:
                        print(f"🌍 DEBUG: Found exact region match!")
                        return cover
                    
                    # Special case mappings for common regions
                    region_mappings = {
                        'japan': ['japan', 'jp'],
                        'usa': ['usa', 'united states', 'north america', 'us'],
                        'europe': ['europe', 'eu', 'european'],
                        'world': ['world', 'global', 'international']
                    }
                    
                    for key, values in region_mappings.items():
                        if target_normalized in values and region_normalized in values:
                            print(f"🌍 DEBUG: Found mapped region match: '{region_name}' matches '{target_region}' via mapping")
                            return cover
        
        # If no exact match, try partial match
        for cover in covers:
            if cover.get('game_localization'):
                localization = game_localizations.get(cover['game_localization'])
                if localization and localization.get('region'):
                    region_name = get_igdb_region_name(localization['region'], regions_cache)
                    target_normalized = target_region.lower().strip()
                    region_normalized = region_name.lower().strip()
                    
                    if target_normalized in region_normalized or region_normalized in target_normalized:
                        print(f"🌍 DEBUG: Found partial region match: '{region_name}'")
                        return cover
    
    # If no target region or no match found, use region priority
    print(f"🌍 DEBUG: Using region priority to select cover")
    region_priority = get_igdb_region_priority()
    print(f"🌍 DEBUG: Region priority: {region_priority}")
    
    # Try to find cover matching region priority order
    for priority_region in region_priority:
        for cover in covers:
            if cover.get('game_localization'):
                localization = game_localizations.get(cover['game_localization'])
                if localization and localization.get('region'):
                    region_name = get_igdb_region_name(localization['region'], regions_cache)
                    priority_normalized = priority_region.lower().strip()
                    region_normalized = region_name.lower().strip()
                    
                    if region_normalized == priority_normalized:
                        print(f"🌍 DEBUG: Found cover matching priority region: '{region_name}'")
                        return cover
                    
                    # Also try partial matching for priority regions
                    if priority_normalized in region_normalized or region_normalized in priority_normalized:
                        print(f"🌍 DEBUG: Found cover matching priority region (partial): '{region_name}' matches '{priority_region}'")
                        return cover
    
    # If no priority match, use first cover
    print(f"🌍 DEBUG: No priority region match found, using first cover")
    return covers[0]

async def fetch_igdb_covers(async_client, access_token, client_id, game_id, game_name):
    """Fetch covers for a specific game and return the best match based on region"""
    try:
        print(f"🖼️ DEBUG: fetch_igdb_covers called for game_id: {game_id}, game_name: {game_name}")
        
        # Ensure regions cache is populated
        regions_cache = await ensure_igdb_regions_cache(async_client, access_token, client_id)
        
        # Fetch covers
        search_url = "https://api.igdb.com/v4/covers"
        search_data = f'fields id,image_id,width,height,url,game_localization; where game = {game_id};'
        
        print(f"🖼️ DEBUG: Covers API request - URL: {search_url}")
        print(f"🖼️ DEBUG: Covers API request - Data: {search_data}")
        
        headers = {
            'Client-ID': client_id,
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'text/plain'
        }
        
        # Make the request with retry logic
        response = await make_igdb_request_with_retry(async_client, search_url, headers, search_data)
        
        if response and response.status_code == 200:
            covers = response.json()
            print(f"🖼️ DEBUG: Received {len(covers)} covers from API")
            
            if not covers:
                print(f"🖼️ DEBUG: No covers found for game {game_id}")
                return None
            
            # Get unique localization IDs from covers
            localization_ids = list(set([cover.get('game_localization') for cover in covers if cover.get('game_localization')]))
            
            # Fetch game localizations for this specific game
            game_localizations = {}
            if localization_ids:
                print(f"🖼️ DEBUG: Fetching {len(localization_ids)} game localizations...")
                localization_url = "https://api.igdb.com/v4/game_localizations"
                localization_data = f'fields id,name,region; where id = ({",".join(map(str, localization_ids))});'
                
                localization_response = await make_igdb_request_with_retry(async_client, localization_url, headers, localization_data)
                
                if localization_response and localization_response.status_code == 200:
                    localizations = localization_response.json()
                    for loc in localizations:
                        game_localizations[loc['id']] = {
                            'name': loc.get('name', ''),
                            'region': loc.get('region', 0)
                        }
                    print(f"🖼️ DEBUG: Loaded {len(game_localizations)} game localizations")
            
            # Debug: Print all covers with region info
            for i, cover in enumerate(covers):
                width = cover.get('width', 0)
                height = cover.get('height', 0)
                image_id = cover.get('image_id', 'N/A')
                url = cover.get('url', 'N/A')
                localization_id = cover.get('game_localization', 'N/A')
                
                region_name = 'N/A'
                if localization_id != 'N/A' and localization_id in game_localizations:
                    region_id = game_localizations[localization_id].get('region')
                    if region_id:
                        region_name = get_igdb_region_name(region_id, regions_cache)
                
                print(f"🖼️ DEBUG: Cover {i+1}: id={cover.get('id')}, image_id={image_id}, width={width}, height={height}, url={url}, region='{region_name}'")
            
            # Extract region from game name
            target_region = extract_region_from_game_name(game_name)
            
            # Find best matching cover
            selected_cover = find_matching_cover(covers, target_region, regions_cache, game_localizations)
            
            if selected_cover:
                region_name = 'Default'
                if selected_cover.get('game_localization') and selected_cover.get('game_localization') in game_localizations:
                    region_id = game_localizations[selected_cover.get('game_localization')].get('region')
                    if region_id:
                        region_name = get_igdb_region_name(region_id, regions_cache)
                
                print(f"🖼️ DEBUG: Selected cover: {selected_cover.get('id')} with image_id: {selected_cover.get('image_id')}, url: {selected_cover.get('url')}, region: '{region_name}'")
                return selected_cover
            else:
                print(f"🖼️ DEBUG: No suitable cover found for game {game_id}")
                return None
        else:
            if response:
                print(f"🖼️ DEBUG: IGDB covers API error: {response.status_code} - {response.text}")
            else:
                print(f"🖼️ DEBUG: No response received from covers API")
            return None
    except Exception as e:
        print(f"🖼️ DEBUG: Error fetching IGDB covers: {e}")
        import traceback
        traceback.print_exc()
        return None

async def download_igdb_image(image_data, system_name, rom_filename, image_type="fanart"):
    """Download image from IGDB and save it to the appropriate directory"""
    try:
        image_id = image_data.get('image_id')
        image_url = image_data.get('url')
        if image_type == "fanart":
            emoji = "🎨"
        elif image_type == "screenshot":
            emoji = "📸"
        elif image_type == "cover":
            emoji = "🖼️"
        elif image_type == "logo":
            emoji = "🏷️"
        else:
            emoji = "🖼️"
        print(f"{emoji} DEBUG: download_igdb_image called - type: {image_type}, image_id: {image_id}, system: {system_name}, rom: {rom_filename}")
        print(f"{emoji} DEBUG: Raw URL from API: {image_url}")
        
        if not image_url:
            print(f"{emoji} DEBUG: ERROR - No URL found in image data!")
            return None
        
        # IGDB returns relative URLs, need to prefix with base URL
        if image_url.startswith('//'):
            image_url = f"https:{image_url}"
        elif not image_url.startswith('http'):
            image_url = f"https://images.igdb.com{image_url}"
        
        # Replace thumb size with 720p for better quality
        if '/t_thumb/' in image_url:
            image_url = image_url.replace('/t_thumb/', '/t_720p/')
            print(f"{emoji} DEBUG: Replaced /t_thumb/ with /t_720p/ for better quality")
        
        print(f"{emoji} DEBUG: Final image URL: {image_url}")
        
        # Create appropriate directory for the system
        if image_type == "fanart":
            media_dir = os.path.join(ROMS_FOLDER, system_name, 'media', 'fanarts')
        elif image_type == "screenshot":
            media_dir = os.path.join(ROMS_FOLDER, system_name, 'media', 'screenshots')
        elif image_type == "cover":
            # Cover maps to extra1 field, which uses box2d directory
            media_dir = os.path.join(ROMS_FOLDER, system_name, 'media', 'box2d')
        elif image_type == "logo":
            # Logo maps to marquee field
            media_dir = os.path.join(ROMS_FOLDER, system_name, 'media', 'marquee')
        else:
            media_dir = os.path.join(ROMS_FOLDER, system_name, 'media', 'images')
        
        print(f"{emoji} DEBUG: Media directory: {media_dir}")
        os.makedirs(media_dir, exist_ok=True)
        
        # Create filename from ROM filename (without extension) + .png extension
        rom_name_without_ext = os.path.splitext(os.path.basename(rom_filename))[0]
        filename = f"{rom_name_without_ext}.png"  # Always save as PNG
        file_path = os.path.join(media_dir, filename)
        print(f"{emoji} DEBUG: Safe filename: {filename}")
        print(f"{emoji} DEBUG: Full file path: {file_path}")
        
        # Download the image using httpx with separate connection pool
        print(f"{emoji} DEBUG: Starting image download with httpx...")
        try:
            import httpx
            # Use a separate connection pool for image downloads to avoid interference with IGDB API calls
            limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)
            async with httpx.AsyncClient(
                timeout=20.0,
                limits=limits,
                http2=True,  # Enable HTTP/2 for better performance
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            ) as image_client:
                response = await image_client.get(image_url)
                print(f"{emoji} DEBUG: Download response status: {response.status_code}")
        except Exception as e:
            print(f"{emoji} DEBUG: Error downloading image: {e}")
            return None
        
        if response.status_code == 200:
            print(f"{emoji} DEBUG: Writing image to file...")
            
            # Get the content type to determine if we need to convert
            content_type = response.headers.get('content-type', '').lower()
            print(f"{emoji} DEBUG: Content type: {content_type}")
            
            # Write the raw image data to a temporary file first
            temp_file_path = file_path + '.temp'
            with open(temp_file_path, 'wb') as f:
                f.write(response.content)
            
            # Use original format without conversion
            print(f"{emoji} DEBUG: Using original format, no conversion needed...")
            # Just rename the temp file to the final file
            os.rename(temp_file_path, file_path)
            
            # Check if file was written successfully
            if os.path.exists(file_path):
                file_size = os.path.getsize(file_path)
                print(f"{emoji} DEBUG: File written successfully, size: {file_size} bytes")
            else:
                print(f"{emoji} DEBUG: ERROR - File was not created!")
                return None
            
            # Return relative path for gamelist
            if image_type == "fanart":
                relative_path = f"./media/fanarts/{filename}"
            elif image_type == "screenshot":
                relative_path = f"./media/screenshots/{filename}"
            elif image_type == "cover":
                # Cover maps to extra1 field, which uses box2d directory
                relative_path = f"./media/box2d/{filename}"
            elif image_type == "logo":
                # Logo maps to marquee field
                relative_path = f"./media/marquee/{filename}"
            else:
                relative_path = f"./media/images/{filename}"
            
            print(f"{emoji} DEBUG: Returning relative path: {relative_path}")
            return relative_path
        else:
            print(f"{emoji} DEBUG: Failed to download image: {response.status_code}")
            print(f"{emoji} DEBUG: Response text: {response.text}")
            return None
            
    except Exception as e:
        print(f"{emoji} DEBUG: Error downloading image: {e}")
        import traceback
        traceback.print_exc()
        return None

# =============================================================================
# IGDB HTTP Client and Rate Limiter
# =============================================================================

# Global httpx async client and rate limiter for IGDB API
_igdb_async_client = None

async def get_igdb_async_client():
    """Get or create global httpx async client for IGDB API"""
    global _igdb_async_client
    if _igdb_async_client is None:
        import httpx
        
        # Create async client with connection pooling
        _igdb_async_client = httpx.AsyncClient(
            http2=True,
            limits=httpx.Limits(
                max_connections=8,
                max_keepalive_connections=8,
                keepalive_expiry=30.0
            ),
            timeout=httpx.Timeout(30.0, connect=10.0)
        )
    
    return _igdb_async_client

async def close_igdb_async_client():
    """Close the global httpx async client"""
    global _igdb_async_client
    if _igdb_async_client is not None:
        await _igdb_async_client.aclose()
        _igdb_async_client = None

# =============================================================================
# IGDB Platform Cache Functions
# =============================================================================

def get_igdb_platform_cache_path():
    """Get the path to the IGDB platform cache file"""
    cache_dir = os.path.join(os.getcwd(), 'var', 'db', 'igdb')
    os.makedirs(cache_dir, exist_ok=True)
    return os.path.join(cache_dir, 'platforms.json')

def load_igdb_platform_cache():
    """Load IGDB platform cache from file"""
    cache_path = get_igdb_platform_cache_path()
    try:
        if os.path.exists(cache_path):
            with open(cache_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Check if cache is still valid (less than 7 days old)
                if 'timestamp' in data and 'platforms' in data:
                    cache_age = time.time() - data['timestamp']
                    if cache_age < 7 * 24 * 3600:  # 7 days
                        return data['platforms']
        return {}
    except Exception as e:
        print(f"Error loading IGDB platform cache: {e}")
        return {}

def save_igdb_platform_cache(platforms):
    """Save IGDB platform cache to file"""
    cache_path = get_igdb_platform_cache_path()
    try:
        data = {
            'timestamp': time.time(),
            'platforms': platforms
        }
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"IGDB platform cache saved to {cache_path}")
    except Exception as e:
        print(f"Error saving IGDB platform cache: {e}")

async def fetch_igdb_platforms(async_client, access_token, client_id):
    """Fetch all IGDB platforms and return as ID->name mapping"""
    try:
        search_url = "https://api.igdb.com/v4/platforms"
        search_data = 'fields id,name; limit 500;'
        
        headers = {
            'Client-ID': client_id,
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'text/plain'
        }
        
        response = await async_client.post(search_url, headers=headers, content=search_data)
        
        if response.status_code == 200:
            platforms = response.json()
            # Convert to ID->name mapping
            platform_map = {str(platform['id']): platform['name'] for platform in platforms}
            return platform_map
        else:
            print(f"IGDB platforms API error: {response.status_code} - {response.text}")
            return {}
    except Exception as e:
        print(f"Error fetching IGDB platforms: {e}")
        return {}

def get_igdb_platform_name(platform_id, platform_cache=None):
    """Get platform name from cache or return platform_id if not found"""
    if platform_cache is None:
        platform_cache = load_igdb_platform_cache()
    
    platform_id_str = str(platform_id)
    return platform_cache.get(platform_id_str, f"Platform {platform_id}")

async def ensure_igdb_platform_cache():
    """Ensure IGDB platform cache is up to date"""
    cache = load_igdb_platform_cache()
    
    # If cache is empty or very old, refresh it
    if not cache:
        print("IGDB platform cache is empty, fetching from API...")
        
        # Get IGDB configuration
        igdb_config = get_igdb_config()
        if not igdb_config.get('enabled', False):
            print("IGDB integration is disabled")
            return cache
        
        # Get access token
        access_token = get_igdb_access_token()
        if not access_token:
            print("Failed to get IGDB access token")
            return cache
        
        # Fetch platforms
        async_client = await get_igdb_async_client()
        try:
            platforms = await fetch_igdb_platforms(
                async_client, 
                access_token, 
                igdb_config['client_id']
            )
            if platforms:
                save_igdb_platform_cache(platforms)
                return platforms
        except Exception as e:
            print(f"Error refreshing IGDB platform cache: {e}")
    
    return cache

# =============================================================================
# IGDB Company Cache Functions
# =============================================================================

def get_igdb_company_cache_path():
    """Get the path to the IGDB company cache file"""
    cache_dir = os.path.join(os.getcwd(), 'var', 'db', 'igdb')
    os.makedirs(cache_dir, exist_ok=True)
    return os.path.join(cache_dir, 'companies.json')

def load_igdb_company_cache():
    """Load IGDB company cache from file"""
    cache_path = get_igdb_company_cache_path()
    try:
        if os.path.exists(cache_path):
            with open(cache_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Check if cache is still valid (less than 7 days old)
                if 'timestamp' in data and 'companies' in data:
                    cache_age = time.time() - data['timestamp']
                    if cache_age < 7 * 24 * 3600:  # 7 days
                        return data['companies']
        return {}
    except Exception as e:
        print(f"Error loading IGDB company cache: {e}")
        return {}

def save_igdb_company_cache(companies):
    """Save IGDB company cache to file"""
    cache_path = get_igdb_company_cache_path()
    try:
        data = {
            'timestamp': time.time(),
            'companies': companies
        }
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"IGDB company cache saved to {cache_path}")
    except Exception as e:
        print(f"Error saving IGDB company cache: {e}")

async def fetch_igdb_companies(async_client, access_token, client_id, company_ids):
    """Fetch specific IGDB companies and return as ID->name mapping"""
    try:
        if not company_ids:
            return {}
            
        # Convert to comma-separated string
        ids_str = ','.join(map(str, company_ids))
        
        search_url = "https://api.igdb.com/v4/companies"
        search_data = f'fields id,name; where id = ({ids_str}); limit 500;'
        
        headers = {
            'Client-ID': client_id,
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'text/plain'
        }
        
        response = await async_client.post(search_url, headers=headers, content=search_data)
        
        if response.status_code == 200:
            companies = response.json()
            # Convert to ID->name mapping
            company_map = {str(company['id']): company['name'] for company in companies}
            return company_map
        else:
            print(f"IGDB companies API error: {response.status_code} - {response.text}")
            return {}
    except Exception as e:
        print(f"Error fetching IGDB companies: {e}")
        return {}

def get_igdb_company_name(company_id, company_cache=None):
    """Get company name from cache or return company_id if not found"""
    if company_cache is None:
        company_cache = load_igdb_company_cache()
    
    company_id_str = str(company_id)
    return company_cache.get(company_id_str, f"Company {company_id}")

async def ensure_igdb_company_cache(company_ids):
    """Ensure IGDB company cache contains the required companies"""
    cache = load_igdb_company_cache()
    
    # Check which companies are missing from cache
    missing_ids = []
    for company_id in company_ids:
        if str(company_id) not in cache:
            missing_ids.append(company_id)
    
    # If we have missing companies, fetch them
    if missing_ids:
        print(f"IGDB company cache missing {len(missing_ids)} companies, fetching from API...")
        
        # Get IGDB configuration
        igdb_config = get_igdb_config()
        if not igdb_config.get('enabled', False):
            print("IGDB integration is disabled")
            return cache
        
        # Get access token
        access_token = get_igdb_access_token()
        if not access_token:
            print("Failed to get IGDB access token")
            return cache
        
        # Fetch missing companies
        async_client = await get_igdb_async_client()
        try:
            new_companies = await fetch_igdb_companies(
                async_client, 
                access_token, 
                igdb_config['client_id'],
                missing_ids
            )
            if new_companies:
                # Merge with existing cache
                cache.update(new_companies)
                save_igdb_company_cache(cache)
                print(f"Added {len(new_companies)} companies to cache")
        except Exception as e:
            print(f"Error refreshing IGDB company cache: {e}")
    
    return cache

# =============================================================================
# IGDB Scraper Task
# =============================================================================

def populate_gamelist_with_igdb_data(game, igdb_game, igdb_config, company_cache=None):
    """Populate gamelist fields with IGDB data if fields are empty"""
    try:
        
        mapping = igdb_config.get('mapping', {})
        updated = False
        
        # Helper function to get or create element
        def get_or_create_element(tag_name):
            elem = game.find(tag_name)
            if elem is None:
                elem = ET.SubElement(game, tag_name)
            return elem
        
        # Helper function to safely get text from element
        def get_element_text(tag_name):
            elem = game.find(tag_name)
            return elem.text.strip() if elem is not None and elem.text else ""
        
        # Resolve company IDs to names from involved_companies
        developer_names = []
        publisher_names = []
        
        if igdb_game.get('involved_companies'):
            for involvement in igdb_game['involved_companies']:
                company_id = involvement.get('company')
                is_developer = involvement.get('developer', False)
                is_publisher = involvement.get('publisher', False)
                
                if company_id:
                    company_name = get_igdb_company_name(company_id, company_cache)
                    if company_name and not company_name.startswith('Company '):
                        if is_developer:
                            developer_names.append(company_name)
                        if is_publisher:
                            publisher_names.append(company_name)
        
        # Map IGDB fields to gamelist fields
        field_mappings = {
            'name': igdb_game.get('name', ''),
            'summary': igdb_game.get('summary', ''),
            'developer': ', '.join(developer_names) if developer_names else '',
            'publisher': ', '.join(publisher_names) if publisher_names else '',
            'genre': ', '.join([str(g) for g in igdb_game.get('genres', [])]) if igdb_game.get('genres') else '',
            'rating': str(int(igdb_game.get('total_rating', 0))) if igdb_game.get('total_rating') else '',
            'players': str(igdb_game.get('player_perspectives', [0])[0]) if igdb_game.get('player_perspectives') else '',
            'release_date': str(igdb_game.get('first_release_date', '')) if igdb_game.get('first_release_date') else ''
        }
        
        # Clean up empty values
        for key, value in field_mappings.items():
            if not value or value == '0' or value == '':
                field_mappings[key] = ''
        
        # Get overwrite settings from cookies (passed from frontend)
        overwrite_text_fields = igdb_config.get('overwrite_text_fields', False)
        overwrite_media_fields = igdb_config.get('overwrite_media_fields', False)
        
        print(f"🔧 DEBUG: populate_gamelist_with_igdb_data - overwrite_text_fields: {overwrite_text_fields}, overwrite_media_fields: {overwrite_media_fields}")
        
        # Get selected fields from config
        selected_fields = igdb_config.get('selected_fields', [])
        
        # Update fields based on overwrite settings
        for igdb_field, gamelist_field in mapping.items():
            # Skip field if not in selected fields (except igdbid which is always processed)
            if selected_fields and igdb_field not in selected_fields and igdb_field != 'igdbid':
                continue
                
            if igdb_field in field_mappings:
                igdb_value = field_mappings[igdb_field]
                current_value = get_element_text(gamelist_field)
                
                # Determine if this is a text field or media field
                is_text_field = igdb_field in ['name', 'summary', 'developer', 'publisher', 'genre', 'rating', 'players', 'release_date']
                is_media_field = igdb_field in ['cover', 'screenshots', 'artworks']
                
                # Check if we should update this field
                should_update = False
                if is_text_field and overwrite_text_fields:
                    # Always overwrite text fields if setting is enabled
                    should_update = bool(igdb_value)
                elif is_media_field and overwrite_media_fields:
                    # Always overwrite media fields if setting is enabled
                    should_update = bool(igdb_value)
                else:
                    # Only update if current field is empty and IGDB has data
                    should_update = not current_value and bool(igdb_value)
                
                if should_update:
                    elem = get_or_create_element(gamelist_field)
                    elem.text = igdb_value
                    updated = True
                    overwrite_indicator = " (overwritten)" if current_value else ""
                    print(f"  📝 Updated {gamelist_field}: {igdb_value}{overwrite_indicator}")
        
        return updated
        
    except Exception as e:
        print(f"Error populating gamelist with IGDB data: {e}")
        return False

async def process_game_async(game, igdb_platform_id, access_token, client_id, async_client, igdb_config, company_cache=None):
    """Process a single game asynchronously"""
    try:
        # Get game name
        name_elem = game.find('name')
        if name_elem is None or not name_elem.text:
            return None, False, False  # game, found, error
        
        game_name = name_elem.text.strip()
        
        # Get ROM filename for media downloads
        path_elem = game.find('path')
        rom_filename = path_elem.text if path_elem is not None and path_elem.text else game_name
        
        # Check if already has IGDB ID
        igdbid_elem = game.find('igdbid')
        existing_igdb_id = None
        if igdbid_elem is not None and igdbid_elem.text:
            existing_igdb_id = igdbid_elem.text
            print(f"🔄 Game '{game_name}' already has IGDB ID: {existing_igdb_id} - will still process for field updates")
        
        # Get IGDB game data
        if existing_igdb_id:
            # Use existing IGDB ID to fetch game data
            print(f"🔍 Fetching IGDB data for existing ID: {existing_igdb_id}")
            igdb_game = await fetch_igdb_game_by_id_async(
                existing_igdb_id,
                access_token,
                client_id,
                async_client
            )
        else:
            # Search for game in IGDB by name
            print(f"🔍 Searching IGDB for game: {game_name}")
            igdb_game = await search_igdb_game_by_name_async(
                game_name, 
                igdb_platform_id, 
                access_token, 
                client_id,
                async_client
            )
        
        if igdb_game:
            # Add IGDB ID to gamelist (only if it doesn't already exist)
            if not existing_igdb_id:
                if igdbid_elem is None:
                    igdbid_elem = ET.SubElement(game, 'igdbid')
                igdbid_elem.text = str(igdb_game['id'])
                print(f"✅ Added IGDB ID for '{game_name}': {igdb_game['id']}")
            else:
                print(f"✅ Using existing IGDB ID for '{game_name}': {existing_igdb_id}")
            
            # Fetch involved companies data
            involved_companies = await fetch_igdb_involved_companies(
                async_client, 
                access_token, 
                client_id, 
                igdb_game['id']
            )
            igdb_game['involved_companies'] = involved_companies
            
            # Fetch and download fanart if selected fields include fanart
            selected_fields = igdb_config.get('selected_fields', [])
            print(f"🎨 DEBUG: Selected fields: {selected_fields}")
            print(f"🎨 DEBUG: Checking if fanart should be processed...")
            
            if not selected_fields or 'artworks' in selected_fields:
                print(f"🎨 DEBUG: Fanart field is selected or no field selection (all fields)")
                # Check if fanart field is selected or if no field selection (all fields)
                fanart_elem = game.find('fanart')
                overwrite_media_fields = igdb_config.get('overwrite_media_fields', False)
                
                print(f"🎨 DEBUG: Existing fanart element: {fanart_elem is not None}")
                if fanart_elem is not None:
                    print(f"🎨 DEBUG: Existing fanart text: '{fanart_elem.text}'")
                print(f"🎨 DEBUG: Overwrite media fields: {overwrite_media_fields}")
                
                # Only download fanart if it doesn't exist or if overwrite is enabled
                if fanart_elem is None or not fanart_elem.text or overwrite_media_fields:
                    print(f"🎨 DEBUG: Proceeding with fanart download for '{game_name}'...")
                    print(f"🎨 Fetching fanart for '{game_name}'...")
                    try:
                        # Add timeout to artwork fetching as well
                        import asyncio
                        artwork = await asyncio.wait_for(
                            fetch_igdb_artworks(async_client, access_token, client_id, igdb_game['id']),
                            timeout=15.0  # 15 second timeout for API call
                        )
                    except asyncio.TimeoutError:
                        print(f"⏰ Timeout fetching artworks for '{game_name}' (15s limit)")
                        artwork = None
                    except Exception as e:
                        print(f"❌ Error fetching artworks for '{game_name}': {e}")
                        artwork = None
                    if artwork and artwork.get('image_id'):
                        print(f"🎨 DEBUG: Artwork found, proceeding with download...")
                        # Get system name from the current system being processed
                        # We need to pass this from the calling function
                        system_name = igdb_config.get('system_name', 'unknown')
                        print(f"🎨 DEBUG: System name from config: {system_name}")
                        
                        try:
                            # Add timeout to prevent hanging
                            import asyncio
                            fanart_path = await asyncio.wait_for(
                                download_igdb_image(
                                    artwork, 
                                    system_name, 
                                    rom_filename,
                                    "fanart"
                                ),
                                timeout=30.0  # 30 second timeout
                            )
                            if fanart_path:
                                if fanart_elem is None:
                                    fanart_elem = ET.SubElement(game, 'fanart')
                                fanart_elem.text = fanart_path
                                print(f"✅ Downloaded fanart for '{game_name}': {fanart_path}")
                            else:
                                print(f"❌ Failed to download fanart for '{game_name}'")
                        except asyncio.TimeoutError:
                            print(f"⏰ Timeout downloading fanart for '{game_name}' (30s limit)")
                        except Exception as e:
                            print(f"❌ Error downloading fanart for '{game_name}': {e}")
                    else:
                        print(f"❌ No suitable fanart found for '{game_name}'")
                else:
                    print(f"🎨 DEBUG: Skipping fanart download - already exists and overwrite disabled")
            else:
                print(f"🎨 DEBUG: Fanart field not selected, skipping fanart processing")
            
            # Fetch and download screenshot if selected fields include screenshots
            if not selected_fields or 'screenshots' in selected_fields:
                print(f"📸 DEBUG: Screenshot field is selected or no field selection (all fields)")
                # Check if screenshot field is selected or if no field selection (all fields)
                screenshot_elem = game.find('screenshot')
                overwrite_media_fields = igdb_config.get('overwrite_media_fields', False)
                
                print(f"📸 DEBUG: Existing screenshot element: {screenshot_elem is not None}")
                if screenshot_elem is not None:
                    print(f"📸 DEBUG: Existing screenshot text: '{screenshot_elem.text}'")
                print(f"📸 DEBUG: Overwrite media fields: {overwrite_media_fields}")
                
                # Only download screenshot if it doesn't exist or if overwrite is enabled
                if screenshot_elem is None or not screenshot_elem.text or overwrite_media_fields:
                    print(f"📸 DEBUG: Proceeding with screenshot download for '{game_name}'...")
                    print(f"📸 Fetching screenshot for '{game_name}'...")
                    try:
                        # Add timeout to screenshot fetching as well
                        import asyncio
                        screenshot = await asyncio.wait_for(
                            fetch_igdb_screenshots(async_client, access_token, client_id, igdb_game['id']),
                            timeout=15.0  # 15 second timeout for API call
                        )
                    except asyncio.TimeoutError:
                        print(f"⏰ Timeout fetching screenshots for '{game_name}' (15s limit)")
                        screenshot = None
                    except Exception as e:
                        print(f"❌ Error fetching screenshots for '{game_name}': {e}")
                        screenshot = None
                    if screenshot and screenshot.get('image_id'):
                        print(f"📸 DEBUG: Screenshot found, proceeding with download...")
                        # Get system name from the current system being processed
                        system_name = igdb_config.get('system_name', 'unknown')
                        print(f"📸 DEBUG: System name from config: {system_name}")
                        
                        try:
                            # Add timeout to prevent hanging
                            import asyncio
                            screenshot_path = await asyncio.wait_for(
                                download_igdb_image(
                                    screenshot, 
                                    system_name, 
                                    rom_filename,
                                    "screenshot"
                                ),
                                timeout=30.0  # 30 second timeout
                            )
                            if screenshot_path:
                                if screenshot_elem is None:
                                    screenshot_elem = ET.SubElement(game, 'screenshot')
                                screenshot_elem.text = screenshot_path
                                print(f"✅ Downloaded screenshot for '{game_name}': {screenshot_path}")
                            else:
                                print(f"❌ Failed to download screenshot for '{game_name}'")
                        except asyncio.TimeoutError:
                            print(f"⏰ Timeout downloading screenshot for '{game_name}' (30s limit)")
                        except Exception as e:
                            print(f"❌ Error downloading screenshot for '{game_name}': {e}")
                    else:
                        print(f"❌ No suitable screenshot found for '{game_name}'")
                else:
                    print(f"📸 DEBUG: Skipping screenshot download - already exists and overwrite disabled")
            else:
                print(f"📸 DEBUG: Screenshot field not selected, skipping screenshot processing")
            
            # Fetch and download cover if selected fields include covers
            if not selected_fields or 'cover' in selected_fields:
                print(f"🖼️ DEBUG: Cover field is selected or no field selection (all fields)")
                # Check if cover field is selected or if no field selection (all fields)
                extra1_elem = game.find('extra1')  # Cover is stored in extra1 field
                overwrite_media_fields = igdb_config.get('overwrite_media_fields', False)
                
                print(f"🖼️ DEBUG: Existing extra1 element: {extra1_elem is not None}")
                if extra1_elem is not None:
                    print(f"🖼️ DEBUG: Existing extra1 text: '{extra1_elem.text}'")
                print(f"🖼️ DEBUG: Overwrite media fields: {overwrite_media_fields}")
                
                # Only download cover if it doesn't exist or if overwrite is enabled
                if extra1_elem is None or not extra1_elem.text or overwrite_media_fields:
                    print(f"🖼️ DEBUG: Proceeding with cover download for '{game_name}'...")
                    print(f"🖼️ Fetching cover for '{game_name}'...")
                    try:
                        # Add timeout to cover fetching as well
                        import asyncio
                        cover = await asyncio.wait_for(
                            fetch_igdb_covers(async_client, access_token, client_id, igdb_game['id'], game_name),
                            timeout=15.0  # 15 second timeout for API call
                        )
                    except asyncio.TimeoutError:
                        print(f"⏰ Timeout fetching covers for '{game_name}' (15s limit)")
                        cover = None
                    except Exception as e:
                        print(f"❌ Error fetching covers for '{game_name}': {e}")
                        cover = None
                    if cover and cover.get('image_id'):
                        print(f"🖼️ DEBUG: Cover found, proceeding with download...")
                        # Get system name from the current system being processed
                        system_name = igdb_config.get('system_name', 'unknown')
                        print(f"🖼️ DEBUG: System name from config: {system_name}")
                        
                        try:
                            # Add timeout to prevent hanging
                            import asyncio
                            cover_path = await asyncio.wait_for(
                                download_igdb_image(
                                    cover, 
                                    system_name, 
                                    rom_filename,
                                    "cover"
                                ),
                                timeout=30.0  # 30 second timeout
                            )
                            if cover_path:
                                if extra1_elem is None:
                                    extra1_elem = ET.SubElement(game, 'extra1')
                                extra1_elem.text = cover_path
                                print(f"✅ Downloaded cover for '{game_name}': {cover_path}")
                            else:
                                print(f"❌ Failed to download cover for '{game_name}'")
                        except asyncio.TimeoutError:
                            print(f"⏰ Timeout downloading cover for '{game_name}' (30s limit)")
                        except Exception as e:
                            print(f"❌ Error downloading cover for '{game_name}': {e}")
                    else:
                        print(f"❌ No suitable cover found for '{game_name}'")
                else:
                    print(f"🖼️ DEBUG: Skipping cover download - already exists and overwrite disabled")
            else:
                print(f"🖼️ DEBUG: Cover field not selected, skipping cover processing")
            
            # Fetch and download logo if selected fields include logos
            if not selected_fields or 'logos' in selected_fields:
                print(f"🏷️ DEBUG: Logo field is selected or no field selection (all fields)")
                # Check if logo field is selected or if no field selection (all fields)
                marquee_elem = game.find('marquee')
                overwrite_media_fields = igdb_config.get('overwrite_media_fields', False)
                
                print(f"🏷️ DEBUG: Existing marquee element: {marquee_elem is not None}")
                if marquee_elem is not None:
                    print(f"🏷️ DEBUG: Existing marquee text: '{marquee_elem.text}'")
                print(f"🏷️ DEBUG: Overwrite media fields: {overwrite_media_fields}")
                
                # Only download logo if it doesn't exist or if overwrite is enabled
                if marquee_elem is None or not marquee_elem.text or overwrite_media_fields:
                    print(f"🏷️ DEBUG: Proceeding with logo download for '{game_name}'...")
                    print(f"🏷️ Fetching logo for '{game_name}'...")
                    try:
                        # Add timeout to logo fetching as well
                        import asyncio
                        logo = await asyncio.wait_for(
                            fetch_igdb_logos(async_client, access_token, client_id, igdb_game['id']),
                            timeout=15.0  # 15 second timeout for API call
                        )
                    except asyncio.TimeoutError:
                        print(f"⏰ Timeout fetching logos for '{game_name}' (15s limit)")
                        logo = None
                    except Exception as e:
                        print(f"❌ Error fetching logos for '{game_name}': {e}")
                        logo = None
                    if logo and logo.get('image_id'):
                        print(f"🏷️ DEBUG: Logo found, proceeding with download...")
                        # Get system name from the current system being processed
                        system_name = igdb_config.get('system_name', 'unknown')
                        print(f"🏷️ DEBUG: System name from config: {system_name}")
                        
                        try:
                            # Add timeout to prevent hanging
                            import asyncio
                            logo_path = await asyncio.wait_for(
                                download_igdb_image(
                                    logo, 
                                    system_name, 
                                    rom_filename,
                                    "logo"
                                ),
                                timeout=30.0  # 30 second timeout
                            )
                            if logo_path:
                                if marquee_elem is None:
                                    marquee_elem = ET.SubElement(game, 'marquee')
                                marquee_elem.text = logo_path
                                print(f"✅ Downloaded logo for '{game_name}': {logo_path}")
                            else:
                                print(f"❌ Failed to download logo for '{game_name}'")
                        except asyncio.TimeoutError:
                            print(f"⏰ Timeout downloading logo for '{game_name}' (30s limit)")
                        except Exception as e:
                            print(f"❌ Error downloading logo for '{game_name}': {e}")
                    else:
                        print(f"❌ No suitable logo found for '{game_name}'")
                else:
                    print(f"🏷️ DEBUG: Skipping logo download - already exists and overwrite disabled")
            else:
                print(f"🏷️ DEBUG: Logo field not selected, skipping logo processing")
            
            # Populate other fields with IGDB data
            fields_updated = populate_gamelist_with_igdb_data(game, igdb_game, igdb_config, company_cache)
            
            print(f"✅ Found IGDB ID for '{game_name}': {igdb_game['id']}" + (" (fields updated)" if fields_updated else ""))
            return game, True, False  # game, found, error
        else:
            print(f"❌ No IGDB match for '{game_name}'")
            return game, False, True  # game, found, error
            
    except Exception as e:
        print(f"Error processing game: {e}")
        return game, False, True  # game, found, error

def run_igdb_scraper_task(system_name, task_id, selected_games=None, overwrite_text_fields=False, overwrite_media_fields=False, selected_fields=None):
    """Run IGDB scraper task for a specific system"""
    import asyncio
    import multiprocessing
    import queue
    
    # Create result queue for progress updates
    result_q = multiprocessing.Queue()
    
    # Create cancel map for task cancellation
    cancel_map = multiprocessing.Manager().dict()
    
    # Store the cancel map globally so it can be accessed for cancellation
    global _igdb_cancel_maps
    _igdb_cancel_maps[task_id] = cancel_map
    
    # Start the async scraper in a subprocess with result queue
    process = multiprocessing.Process(
        target=_run_igdb_scraper_worker,
        args=(system_name, task_id, selected_games, result_q, cancel_map, overwrite_text_fields, overwrite_media_fields, selected_fields)
    )
    process.start()
    
    # Start result listener to handle progress updates (runs in main process)
    listener_thread = threading.Thread(
        target=_igdb_scraping_result_listener,
        args=(result_q, process, system_name),
        daemon=True
    )
    listener_thread.start()

def _run_igdb_scraper_worker(system_name, task_id, selected_games, result_q, cancel_map, overwrite_text_fields=False, overwrite_media_fields=False, selected_fields=None):
    """IGDB scraper worker process"""
    import asyncio
    
    async def async_scraper():
        try:
            print(f"Starting IGDB scraper task for system: {system_name}")
            
            # Get IGDB configuration
            igdb_config = get_igdb_config()
            if not igdb_config.get('enabled', False):
                result_q.put({
                    'type': 'progress',
                    'task_id': task_id,
                    'message': "IGDB integration is disabled",
                    'progress_percentage': 100
                })
                return
            
            # Add overwrite settings to IGDB config
            igdb_config['overwrite_text_fields'] = overwrite_text_fields
            igdb_config['overwrite_media_fields'] = overwrite_media_fields
            igdb_config['selected_fields'] = selected_fields or []
            igdb_config['system_name'] = system_name
            
            print(f"🔧 DEBUG: Worker received overwrite settings - text: {overwrite_text_fields}, media: {overwrite_media_fields}")
            print(f"🔧 DEBUG: Worker received selected fields: {selected_fields}")
            
            # Get system configuration
            config = load_config()
            systems_config = config.get('systems', {})
            system_config = systems_config.get(system_name, {})
            
            if not system_config:
                result_q.put({
                    'type': 'progress',
                    'task_id': task_id,
                    'message': f"System '{system_name}' not configured",
                    'progress_percentage': 100
                })
                return
            
            # Get IGDB platform ID
            igdb_platform_id = system_config.get('igdb')
            if not igdb_platform_id:
                result_q.put({
                    'type': 'progress',
                    'task_id': task_id,
                    'message': f"No IGDB platform ID configured for system '{system_name}'",
                    'progress_percentage': 100
                })
                return
            
            # Get access token
            access_token = get_igdb_access_token()
            if not access_token:
                result_q.put({
                    'type': 'progress',
                    'task_id': task_id,
                    'message': "Failed to get IGDB access token",
                    'progress_percentage': 100
                })
                return
            
            # Get gamelist path
            gamelist_path = get_gamelist_path(system_name)
            if not os.path.exists(gamelist_path):
                result_q.put({
                    'type': 'progress',
                    'task_id': task_id,
                    'message': f"Gamelist not found: {gamelist_path}",
                    'progress_percentage': 100
                })
                return
            
            # Parse gamelist
            tree = ET.parse(gamelist_path)
            root = tree.getroot()
            
            all_games = root.findall('game')
            total_games = len(all_games)
            
            if total_games == 0:
                result_q.put({
                    'type': 'progress',
                    'task_id': task_id,
                    'message': "No games found in gamelist",
                    'progress_percentage': 100
                })
                return
            
            # Filter games based on selection
            games = all_games
            if selected_games and len(selected_games) > 0:
                # Filter to only selected games by ROM file path
                games = [g for g in all_games if g.find('path').text in selected_games]
                if not games:
                    result_q.put({
                        'type': 'progress',
                        'task_id': task_id,
                        'message': f"None of the selected ROM files found in gamelist",
                        'progress_percentage': 100
                    })
                    return
                result_q.put({
                    'type': 'progress',
                    'task_id': task_id,
                    'message': f"Processing {len(games)} selected games out of {total_games} total games",
                    'current_step': 0,
                    'total_steps': len(games),
                    'progress_percentage': 0
                })
            else:
                result_q.put({
                    'type': 'progress',
                    'task_id': task_id,
                    'message': f"Processing all {total_games} games",
                    'current_step': 0,
                    'total_steps': total_games,
                    'progress_percentage': 0
                })
            
            print(f"Found {len(games)} games to process")
            
            # Get async client
            async_client = await get_igdb_async_client()
            
            # Collect all company IDs from games to cache them
            all_company_ids = set()
            for game in games:
                # We'll collect company IDs after we get the IGDB data
                pass
            
            # Ensure company cache is available (we'll populate it as we go)
            company_cache = load_igdb_company_cache()
            
            processed_count = 0
            found_count = 0
            error_count = 0
            
            # Process games in batches of 8 (max concurrent requests)
            batch_size = 8
            
            for i in range(0, len(games), batch_size):
                # Check for cancellation before processing each batch
                if cancel_map and cancel_map.get(task_id):
                    result_q.put({
                        'type': 'progress',
                        'task_id': task_id,
                        'message': '🛑 Task stopped by user - saving gamelist...',
                        'progress_percentage': int((processed_count / len(games)) * 100)
                    })
                    # Save the gamelist before exiting with explicit flushing
                    print(f"DEBUG: Saving gamelist to {gamelist_path} before task stop...")
                    tree.write(gamelist_path, encoding='utf-8', xml_declaration=True)
                    print(f"DEBUG: Gamelist write completed")
                    # Force flush to ensure file is written to disk
                    try:
                        with open(gamelist_path, 'r+b') as f:
                            f.flush()
                            os.fsync(f.fileno())
                        print(f"DEBUG: Gamelist file flushed to disk")
                    except Exception as e:
                        print(f"Warning: Could not flush gamelist file: {e}")
                    result_q.put({
                        'type': 'result',
                        'task_id': task_id,
                        'success': False,
                        'error': 'Task stopped by user',
                        'stopped': True
                    })
                    return
                
                batch = games[i:i + batch_size]
                
                # Create tasks for concurrent processing using functools.partial
                import functools
                import aiometer
                
                tasks = []
                for game in batch:
                    # Use functools.partial to create callable functions
                    task_func = functools.partial(
                        process_game_async,
                        game, 
                        igdb_platform_id, 
                        access_token, 
                        igdb_config['client_id'],
                        async_client,
                        igdb_config,
                        company_cache
                    )
                    tasks.append(task_func)
                
                # Process batch with rate limiting using aiometer
                results = await aiometer.run_all(tasks, max_at_once=8, max_per_second=4)
                
                # Process results and collect company IDs for caching
                batch_company_ids = set()
                for result in results:
                    if isinstance(result, Exception):
                        error_count += 1
                        print(f"Exception in batch processing: {result}")
                        processed_count += 1
                    else:
                        game, found, error = result
                        if found and game is not None:
                            # Get IGDB data to collect company IDs
                            igdbid_elem = game.find('igdbid')
                            if igdbid_elem and igdbid_elem.text:
                                # We need to get the full game data to extract company IDs
                                # For now, we'll handle this in the next iteration
                                pass
                        if found:
                            found_count += 1
                        if error:
                            error_count += 1
                        processed_count += 1
                        
                        # Get game name for progress message
                        game_name = "Unknown"
                        if game is not None:
                            name_elem = game.find('name')
                            if name_elem is not None and name_elem.text:
                                game_name = name_elem.text.strip()
                        
                        # Send individual game progress update
                        progress_percent = int((processed_count / len(games)) * 100)
                        status_icon = "✅" if found else "❌" if error else "⏭️"
                        progress_update = {
                            'type': 'progress',
                            'task_id': task_id,
                            'message': f"{status_icon} {game_name}",
                            'current_step': processed_count,
                            'total_steps': len(games),
                            'progress_percentage': progress_percent
                        }
                        print(f"DEBUG: Sending progress update: {progress_update}")
                        result_q.put(progress_update)
                
                # Update company cache if we found new company IDs
                if batch_company_ids:
                    company_cache = await ensure_igdb_company_cache(list(batch_company_ids))
            
            # Save updated gamelist
            tree.write(gamelist_path, encoding='utf-8', xml_declaration=True)
            
            # Complete task
            result_q.put({
                'type': 'result',
                'task_id': task_id,
                'success': True,
                'message': f"✅ IGDB scraping completed! Found {found_count} games, {error_count} errors"
            })
            print(f"IGDB scraper completed for {system_name}: {found_count} games found, {error_count} errors")
            
        except Exception as e:
            print(f"Error in IGDB scraper task: {e}")
            result_q.put({
                'type': 'result',
                'task_id': task_id,
                'success': False,
                'error': str(e)
            })
        finally:
            # Close async client
            await close_igdb_async_client()
    
    # Run the async scraper
    asyncio.run(async_scraper())

def _igdb_scraping_result_listener(result_q, process, system_name):
    """Listen for results from IGDB scraper worker and update task progress"""
    import queue
    
    print(f"DEBUG: IGDB result listener started for process {process.pid}")
    
    while process.is_alive():
        try:
            res = result_q.get(timeout=1)
            if res is None:
                break
                
            print(f"DEBUG: IGDB result listener received: {res}")
                
            # Handle progress updates
            if isinstance(res, dict) and res.get('type') == 'progress':
                msg_task_id = res.get('task_id')
                message = res.get('message', '')
                curr = res.get('current_step')
                total = res.get('total_steps')
                pct = res.get('progress_percentage')
                
                print(f"DEBUG: Processing progress update for task {msg_task_id}: {message}")
                
                if msg_task_id and msg_task_id in tasks:
                    try:
                        t = tasks[msg_task_id]
                        if t.status == TASK_STATUS_RUNNING:
                            t.update_progress(message, progress_percentage=pct, current_step=curr, total_steps=total)
                            print(f"DEBUG: Updated task {msg_task_id} progress: {message}")
                        else:
                            print(f"DEBUG: Task {msg_task_id} status is {t.status}, not running")
                    except Exception as e:
                        print(f"DEBUG: Error updating task {msg_task_id}: {e}")
                else:
                    print(f"DEBUG: Task {msg_task_id} not found in tasks dictionary")
                continue
            
            # Handle final result
            task_id = res.get('task_id')
            if task_id and task_id in tasks:
                try:
                    t = tasks[task_id]
                    if res.get('success'):
                        t.complete(True, res.get('message', 'IGDB scraping completed successfully'))
                        
                        # Emit task completion event to refresh task grid
                        socketio.emit('task_completed', {
                            'task_type': 'igdb_scraping',
                            'success': True,
                            'message': res.get('message', 'IGDB scraping completed successfully'),
                            'system_name': system_name
                        })
                    elif res.get('stopped'):
                        # Task was stopped by user - treat as completed since gamelist was saved
                        t.complete(True, res.get('error', 'Task stopped by user'))
                        
                        # Emit task completion event to refresh task grid (same as successful completion)
                        socketio.emit('task_completed', {
                            'task_type': 'igdb_scraping',
                            'success': True,
                            'stopped': True,
                            'message': res.get('error', 'Task stopped by user'),
                            'system_name': system_name
                        })
                    else:
                        t.complete(False, res.get('error', 'IGDB scraping failed'))
                        
                        # Emit task failure event
                        socketio.emit('task_completed', {
                            'task_type': 'igdb_scraping',
                            'success': False,
                            'message': res.get('error', 'IGDB scraping failed'),
                            'system_name': system_name
                        })
                except Exception as e:
                    print(f"DEBUG: Error completing task {task_id}: {e}")
                
                # Clean up the IGDB cancel map when task completes
                try:
                    global _igdb_cancel_maps
                    if task_id in _igdb_cancel_maps:
                        del _igdb_cancel_maps[task_id]
                        print(f"DEBUG: Cleaned up IGDB cancel map for task {task_id}")
                except Exception as e:
                    print(f"DEBUG: Error cleaning up IGDB cancel map: {e}")
                
                break
                
        except queue.Empty:
            continue
        except Exception as e:
            print(f"Error in IGDB result listener: {e}")
            break
    
    print(f"DEBUG: IGDB result listener ended for process {process.pid}")

# =============================================================================
# IGDB Scraper API Routes
# =============================================================================

@app.route('/api/scrap-igdb/<system_name>', methods=['POST'])
@login_required
def scrap_igdb_system(system_name):
    """Start IGDB scraping process for a specific system"""
    global current_task_id
    
    try:
        if not system_name:
            return jsonify({'error': 'System name is required'}), 400
        
        # Check if IGDB is enabled
        igdb_config = get_igdb_config()
        if not igdb_config.get('enabled', False):
            return jsonify({'error': 'IGDB integration is disabled'}), 400
        
        # Check if system has IGDB platform ID configured
        config = load_config()
        systems_config = config.get('systems', {})
        system_config = systems_config.get(system_name, {})
        
        if not system_config.get('igdb'):
            return jsonify({'error': f'No IGDB platform ID configured for system "{system_name}"'}), 400
        
        # Get request data
        data = request.get_json() or {}
        selected_games = data.get('selected_games', [])
        selected_fields = data.get('selected_fields', [])
        
        # Get overwrite settings from cookies
        overwrite_text_fields = request.cookies.get('overwriteTextFields', 'false').lower() == 'true'
        overwrite_media_fields = request.cookies.get('overwriteMediaFields', 'false').lower() == 'true'
        
        print(f"🍪 DEBUG: Cookie values - overwriteTextFields: '{request.cookies.get('overwriteTextFields', 'NOT_SET')}', overwriteMediaFields: '{request.cookies.get('overwriteMediaFields', 'NOT_SET')}'")
        print(f"🍪 DEBUG: Parsed values - overwrite_text_fields: {overwrite_text_fields}, overwrite_media_fields: {overwrite_media_fields}")
        print(f"🍪 DEBUG: Selected fields: {selected_fields}")
        
        # Create task object
        task_data = {
            'system_name': system_name, 
            'selected_games': selected_games,
            'selected_fields': selected_fields,
            'overwrite_text_fields': overwrite_text_fields,
            'overwrite_media_fields': overwrite_media_fields
        }
        username = current_user.username if current_user and current_user.is_authenticated else 'Unknown'
        
        task = Task('igdb_scraping', task_data, username)
        
        # Set global current task ID for progress updates
        global current_task_id
        current_task_id = task.id
        
        # Add to tasks list
        tasks[task.id] = task
        
        # Start the task
        task.start()
        
        # Start the scraper task in a separate thread
        import threading
        scraper_thread = threading.Thread(
            target=run_igdb_scraper_task,
            args=(system_name, task.id, selected_games, overwrite_text_fields, overwrite_media_fields, selected_fields),
            daemon=True
        )
        scraper_thread.start()
        
        return jsonify({
            'success': True,
            'task_id': task.id,
            'message': f'IGDB scraping started for {system_name}'
        })
        
    except Exception as e:
        print(f"Error starting IGDB scraper: {e}")
        return jsonify({'error': f'Failed to start IGDB scraper: {str(e)}'}), 500

@app.route('/api/igdb/search', methods=['POST'])
@login_required
def search_igdb_games_api():
    """Search for games in IGDB database"""
    try:
        data = request.get_json()
        game_name = data.get('game_name', '').strip()
        platform_id = data.get('platform_id')
        limit = data.get('limit', 10)
        
        if not game_name:
            return jsonify({'error': 'Game name is required'}), 400
        
        if not platform_id:
            return jsonify({'error': 'Platform ID is required'}), 400
        
        # Get IGDB configuration
        igdb_config = get_igdb_config()
        if not igdb_config.get('enabled', False):
            return jsonify({'error': 'IGDB integration is disabled'}), 400
        
        # Get access token
        access_token = get_igdb_access_token()
        if not access_token:
            return jsonify({'error': 'Failed to get IGDB access token'}), 500
        
        # Search for games
        import asyncio
        
        async def search_games():
            async_client = await get_igdb_async_client()
            try:
                # Ensure platform cache is available
                platform_cache = await ensure_igdb_platform_cache()
                
                # Clean game name - remove parentheses and extra text
                import re
                clean_name = re.sub(r'\s*\([^)]*\)', '', game_name).strip()
                clean_name = re.sub(r'\s*\[[^\]]*\]', '', clean_name).strip()
                
                # Search for games with platform filter
                search_url = "https://api.igdb.com/v4/games"
                search_data = f'fields id,name,summary,first_release_date,platforms,genres,total_rating,rating_count,player_perspectives,game_modes,cover,screenshots,artworks; search "{clean_name}"; where platforms = ({platform_id}); limit {limit};'
                
                headers = {
                    'Client-ID': igdb_config['client_id'],
                    'Authorization': f'Bearer {access_token}',
                    'Content-Type': 'text/plain'
                }
                
                response = await make_igdb_request_with_retry(async_client, search_url, headers, search_data)
                
                if response.status_code == 200:
                    games = response.json()
                    if games:
                        # Fetch involved companies for each game
                        for game in games:
                            involved_companies = await fetch_igdb_involved_companies(
                                async_client, 
                                access_token, 
                                igdb_config['client_id'], 
                                game['id']
                            )
                            game['involved_companies'] = involved_companies
                        
                        # Collect company IDs for caching
                        company_ids = set()
                        for game in games:
                            if game.get('involved_companies'):
                                for involvement in game['involved_companies']:
                                    company_id = involvement.get('company')
                                    if company_id:
                                        company_ids.add(company_id)
                        
                        # Ensure company cache is available
                        company_cache = await ensure_igdb_company_cache(list(company_ids))
                        
                        # Enhance games with cached platform and company names
                        for game in games:
                            if 'platforms' in game and game['platforms']:
                                game['platforms'] = [
                                    {'id': platform_id, 'name': get_igdb_platform_name(platform_id, platform_cache)}
                                    for platform_id in game['platforms']
                                ]
                            
                            # Add company names from involved_companies
                            developer_names = []
                            publisher_names = []
                            
                            if game.get('involved_companies'):
                                for involvement in game['involved_companies']:
                                    company_id = involvement.get('company')
                                    is_developer = involvement.get('developer', False)
                                    is_publisher = involvement.get('publisher', False)
                                    
                                    if company_id:
                                        company_name = get_igdb_company_name(company_id, company_cache)
                                        if company_name and not company_name.startswith('Company '):
                                            if is_developer:
                                                developer_names.append(company_name)
                                            if is_publisher:
                                                publisher_names.append(company_name)
                            
                            if developer_names:
                                game['developer_names'] = developer_names
                            if publisher_names:
                                game['publisher_names'] = publisher_names
                        
                        return games
                    else:
                        # No games found for this platform
                        return []
                else:
                    print(f"IGDB API error: {response.status_code} - {response.text}")
                    return []
                    
            finally:
                await close_igdb_async_client()
        
        # Run the async search
        games = asyncio.run(search_games())
        
        return jsonify({
            'success': True,
            'games': games,
            'count': len(games)
        })
        
    except Exception as e:
        print(f"Error searching IGDB games: {e}")
        return jsonify({'error': f'Failed to search IGDB games: {str(e)}'}), 500

if __name__ == '__main__':
    # Initialize default admin user
    initialize_default_admin()
    
    # Ensure yt-dlp binary is available
    yt_dlp_path = ensure_yt_dlp_binary()
    if yt_dlp_path:
        print(f"✅ yt-dlp binary ready: {yt_dlp_path}")
    else:
        print("⚠️  yt-dlp binary not available, YouTube downloads may fail")
    
    # Start server immediately, then load cache in background
    print("Starting server...")
    try:
        import os as _os
        print(f"Main server PID: {_os.getpid()}")
    except Exception:
        pass
    print("Cache will load in background - server is ready to accept requests")
    print(f'📁 ROMs directory: {ROMS_FOLDER}')
    
    # Load existing tasks from log files
    load_existing_tasks_from_logs()
    
    # Ensure worker started for producer-consumer model
    try:
        _ensure_worker_started()
    except Exception as e:
        print(f"Failed to start scraping worker: {e}")
    
    # Start cache loading in a separate thread
    import threading
    def load_cache_background():
        print("🔄 Loading comprehensive metadata cache in background...")
        try:
            load_metadata_cache()
            print("✅ Cache loading completed successfully!")
        except Exception as e:
            print(f"❌ Cache loading failed: {e}")
    
    cache_thread = threading.Thread(target=load_cache_background, daemon=True)
    cache_thread.start()
    
    # Start the server using SocketIO
    # In production, use Flask development server
    if config['server']['debug']:
        # Development mode - use Werkzeug with allow_unsafe_werkzeug
        socketio.run(
            app,
            debug=True,
            host=config['server']['host'],
            port=config['server']['port'],
            allow_unsafe_werkzeug=True
        )
    else:
        # Production mode - use Flask development server
        print("Starting production server...")
        print("To run manually: python3 app.py")
        socketio.run(
            app,
            debug=False,
            host=config['server']['host'],
            port=config['server']['port'],
            allow_unsafe_werkzeug=True
        )
