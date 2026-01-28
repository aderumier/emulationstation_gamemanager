# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for GameManager Windows executable
"""

import sys
import os
from pathlib import Path

# Get the base directory
base_dir = Path(SPECPATH)

# Block cipher (set to None for no encryption)
block_cipher = None

# Collect all data files
datas = [
    # Templates
    ('templates', 'templates'),
    # Static files
    ('static', 'static'),
    # Local Python modules (already in path, but ensure they're included)
    ('selenium', 'selenium'),
    ('pixelmatch', 'pixelmatch'),
    ('pyrate_limiter', 'pyrate_limiter'),
    ('typing_extensions', 'typing_extensions'),
]

# Collect hidden imports (modules that PyInstaller might miss)
hiddenimports = [
    # Flask and extensions
    'flask',
    'flask_cors',
    'flask_socketio',
    'flask_login',
    'flask_compress',
    'werkzeug',
    'werkzeug.middleware.proxy_fix',
    # SocketIO dependencies
    'engineio',
    'socketio',
    # HTTP clients
    'requests',
    'httpx',
    'httpx._client',
    'httpx._transports',
    'h2',
    'hpack',
    'aiofiles',
    # HTML parsing
    'bs4',
    'lxml',
    'lxml.etree',
    'lxml._elementpath',
    # Image processing
    'PIL',
    'PIL.Image',
    'PIL.ImageTk',
    'Wand',
    # Authentication
    'bcrypt',
    # Environment
    'dotenv',
    # String matching
    'jellyfish',
    # PDF processing
    'fitz',  # PyMuPDF
    # Local modules
    'selenium',
    'selenium.webdriver',
    'selenium.webdriver.chrome',
    'selenium.webdriver.common',
    'selenium.webdriver.remote',
    'pixelmatch',
    'pyrate_limiter',
    # Services
    'steam_service',
    'screenscraper_service',
    'steamgrid_service',
    'mobygames_service',
    'igdb_service',
    'datscrapper_service',
    'emumovies_service',
    'custom_scraper_service',
    'launchbox_service',
    'game_utils',
    'credential_manager',
    'download_manager',
    # Standard library modules that might be missed
    'multiprocessing',
    'multiprocessing.pool',
    'concurrent.futures',
    'asyncio',
    'json',
    'xml.etree.ElementTree',
    'xml.etree.cElementTree',
    'encodings',
    'encodings.utf_8',
    'encodings.latin_1',
]

# Exclude unnecessary modules to reduce size
excludes = [
    'matplotlib',
    'numpy',
    'pandas',
    'scipy',
    'IPython',
    'jupyter',
    'notebook',
    'pytest',
    'setuptools',
    'distutils',
]

# Binary analysis
binaries = []

# Analysis
a = Analysis(
    ['app.py'],
    pathex=[str(base_dir)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Remove duplicate entries
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# Create executable
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='gamemanager',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,  # Use UPX compression if available
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Show console window (change to False for windowed app)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Add icon path here if you have one: 'icon.ico'
)
