#!/bin/bash

# GameManager Debian Package Builder
# This script ensures the Debian package always contains the latest source files

set -e  # Exit on any error

echo "🔨 Building GameManager Debian Package..."

# Get version from latest git tag
if GIT_TAG=$(git describe --tags --abbrev=0 2>/dev/null); then
    # Remove 'v' prefix if present for Debian package version
    VERSION_NUMBER=${GIT_TAG#v}
    VERSION="${VERSION_NUMBER}-1"
    echo "🏷️  Using latest git tag: $GIT_TAG -> version: $VERSION"
else
    # No tags found, use control file version
    VERSION=$(grep "^Version:" debian/DEBIAN/control | cut -d' ' -f2)
    # Extract version number (remove -1 suffix for HTML display)
    VERSION_NUMBER=${VERSION%-1}
    echo "⚠️  No git tags found, using control file version: $VERSION"
fi

PACKAGE_NAME="gamemanager_${VERSION}_all.deb"

echo "📦 Package: $PACKAGE_NAME"

# Clean previous build
echo "🧹 Cleaning previous build..."
rm -f "$PACKAGE_NAME"

# Clean previous build artifacts
echo "🧹 Cleaning previous build directory..."
rm -rf debian/opt/gamemanager/*

# Sync latest source files to Debian package directory
echo "📋 Syncing latest source files..."

# Ensure directories exist
mkdir -p debian/opt/gamemanager
mkdir -p debian/opt/gamemanager/static
mkdir -p debian/opt/gamemanager/templates
mkdir -p debian/opt/gamemanager/var/config

# Core application files
cp app.py debian/opt/gamemanager/app.py
cp box_generator.py debian/opt/gamemanager/box_generator.py
cp download_manager.py debian/opt/gamemanager/download_manager.py
cp credential_manager.py debian/opt/gamemanager/credential_manager.py
cp screenscraper_service.py debian/opt/gamemanager/screenscraper_service.py
cp game_utils.py debian/opt/gamemanager/game_utils.py
cp steam_service.py debian/opt/gamemanager/steam_service.py
cp steamgrid_service.py debian/opt/gamemanager/steamgrid_service.py
cp mobygames_service.py debian/opt/gamemanager/mobygames_service.py
cp igdb_service.py debian/opt/gamemanager/igdb_service.py
cp emumovies_service.py debian/opt/gamemanager/emumovies_service.py
cp custom_scraper_service.py debian/opt/gamemanager/custom_scraper_service.py
cp datscrapper_service.py debian/opt/gamemanager/datscrapper_service.py
cp launchbox_service.py debian/opt/gamemanager/launchbox_service.py
cp scan_launchbox_media_types.py debian/opt/gamemanager/scan_launchbox_media_types.py
cp requirements.txt debian/opt/gamemanager/requirements.txt

# Static files
cp -r static/* debian/opt/gamemanager/static/
cp -r templates/* debian/opt/gamemanager/templates/

# Configuration files
cp var/config/config.json debian/opt/gamemanager/var/config/config.json
cp var/config/scrappers.json debian/opt/gamemanager/var/config/scrappers.json
cp var/config/systems.json debian/opt/gamemanager/var/config/systems.json
cp var/config/scrapper_genre_mapping.json debian/opt/gamemanager/var/config/scrapper_genre_mapping.json
cp var/config/genres.json debian/opt/gamemanager/var/config/genres.json

# MobyGames databases
echo "📦 Copying MobyGames databases..."
mkdir -p debian/opt/gamemanager/var/db/mobygames
cp var/db/mobygames/*.json debian/opt/gamemanager/var/db/mobygames/

# IGDB databases and pickle files
echo "📦 Copying IGDB databases and pickle files..."
mkdir -p debian/opt/gamemanager/var/db/igdb
# Decompress igdb_db.pkl.gz if present (committed compressed to stay under GitHub 100MB limit)
if [ -f "var/db/igdb/igdb_db.pkl.gz" ] && [ ! -f "var/db/igdb/igdb_db.pkl" ]; then
  echo "  Decompressing igdb_db.pkl.gz..."
  gunzip -k -f var/db/igdb/igdb_db.pkl.gz 2>/dev/null || gzip -d -k -f var/db/igdb/igdb_db.pkl.gz 2>/dev/null || true
fi
cp var/db/igdb/*.pkl debian/opt/gamemanager/var/db/igdb/ 2>/dev/null || echo "⚠️  No IGDB pickle files found, skipping..."
cp var/db/igdb/mediatype.txt debian/opt/gamemanager/var/db/igdb/ 2>/dev/null || echo "⚠️  No IGDB mediatype.txt found, skipping..."
cp var/db/igdb/*.json debian/opt/gamemanager/var/db/igdb/ 2>/dev/null || echo "⚠️  No IGDB JSON files found, skipping..."

# EmuMovies databases
echo "📦 Copying EmuMovies databases..."
mkdir -p debian/opt/gamemanager/var/db/emumovies
cp var/db/emumovies/emumovies.json debian/opt/gamemanager/var/db/emumovies/ 2>/dev/null || echo "⚠️  No EmuMovies JSON database found, skipping..."
cp var/db/emumovies/emumovies_index.pkl debian/opt/gamemanager/var/db/emumovies/ 2>/dev/null || echo "⚠️  No EmuMovies index pickle file found, skipping..."

# Custom databases
echo "📦 Copying Custom databases..."
mkdir -p debian/opt/gamemanager/var/db/custom
cp var/db/custom/*.json debian/opt/gamemanager/var/db/custom/ 2>/dev/null || echo "⚠️  No Custom JSON databases found, skipping..."

# Steam cache (partitioned index)
echo "📦 Copying var/cache (Steam partitioned index)..."
mkdir -p debian/opt/gamemanager/var/cache
cp var/cache/steam_partitioned_index.pkl debian/opt/gamemanager/var/cache/ 2>/dev/null || echo "⚠️  No steam_partitioned_index.pkl found, skipping..."

# Fonts
echo "📦 Copying fonts..."
mkdir -p debian/opt/gamemanager/var/fonts
cp var/fonts/* debian/opt/gamemanager/var/fonts/ 2>/dev/null || echo "⚠️  No font files found, skipping..."

# 2D Box Templates (only if directory is empty)
echo "📦 Copying 2D box templates..."
mkdir -p debian/opt/gamemanager/var/2dbox/templates
if [ -z "$(ls -A debian/opt/gamemanager/var/2dbox/templates 2>/dev/null)" ]; then
    cp var/2dbox/templates/* debian/opt/gamemanager/var/2dbox/templates/ 2>/dev/null || echo "⚠️  No 2D box templates found, skipping..."
    echo "✅ 2D box templates copied (directory was empty)"
else
    echo "⚠️  2D box templates directory not empty, skipping copy"
fi

# 3D Box Templates (always include in package, deployment handled in postinst)
echo "📦 Copying 3D box templates..."
mkdir -p debian/opt/gamemanager/var/3dbox/templates
if [ -d "var/3dbox/templates" ] && [ -n "$(ls -A var/3dbox/templates 2>/dev/null)" ]; then
    cp var/3dbox/templates/* debian/opt/gamemanager/var/3dbox/templates/ 2>/dev/null || echo "⚠️  No 3D box templates found, skipping..."
    echo "✅ 3D box templates included in package"
else
    echo "⚠️  No 3D box templates found in source, skipping..."
fi

# Credentials and embedded modules
cp var/config/credentials.enc debian/opt/gamemanager/var/config/credentials.enc

# Remove user-specific config file (should not be in package)
rm -f debian/opt/gamemanager/var/config/user.cfg

# Copy pyrate_limiter correctly (avoid double nesting)
echo "📦 Copying pyrate_limiter..."
rm -rf debian/opt/gamemanager/pyrate_limiter
cp -r pyrate_limiter debian/opt/gamemanager/

# Copy pixelmatch module
echo "📦 Copying pixelmatch..."
rm -rf debian/opt/gamemanager/pixelmatch
cp -r pixelmatch debian/opt/gamemanager/

# Copy selenium module
echo "📦 Copying selenium..."
rm -rf debian/opt/gamemanager/selenium
cp -r selenium debian/opt/gamemanager/

# Copy typing_extensions module
echo "📦 Copying typing_extensions..."
rm -rf debian/opt/gamemanager/typing_extensions
cp -r typing_extensions debian/opt/gamemanager/

# Tools and plugins
mkdir -p debian/opt/gamemanager/tools
cp tools/yt-dlp debian/opt/gamemanager/tools/yt-dlp
if [ -f "tools/youtubedl" ]; then
    cp tools/youtubedl debian/opt/gamemanager/tools/youtubedl
    chmod +x debian/opt/gamemanager/tools/youtubedl
fi
if [ -f "tools/deno" ]; then
    cp tools/deno debian/opt/gamemanager/tools/deno
    chmod +x debian/opt/gamemanager/tools/deno
fi
rm -rf debian/opt/gamemanager/tools/yt-dlp-plugins
cp -r tools/yt-dlp-plugins debian/opt/gamemanager/tools/yt-dlp-plugins

# Fix paths in config.json for production environment
echo "🔧 Updating paths for production environment..."
sed -i 's|"roms_root_directory": "/home/aderumier/cursorscraper/roms2"|"roms_root_directory": "/opt/gamemanager/roms"|g' debian/opt/gamemanager/var/config/config.json

# Force disable_local_auth to false for fresh installs
echo "🔧 Forcing disable_local_auth to false for fresh installs..."
sed -i 's|"disable_local_auth": true|"disable_local_auth": false|g' debian/opt/gamemanager/var/config/config.json

# Documentation files
cp README.md debian/opt/gamemanager/README.md
cp AUTHENTICATION_SETUP.md debian/opt/gamemanager/AUTHENTICATION_SETUP.md
cp DISCORD_SETUP_EXAMPLE.md debian/opt/gamemanager/DISCORD_SETUP_EXAMPLE.md
cp docker-compose.yml debian/opt/gamemanager/docker-compose.yml
cp Dockerfile debian/opt/gamemanager/Dockerfile

echo "✅ Source files synced successfully"

# Update control file with correct version
echo "🔧 Updating control file with version: $VERSION"
sed -i "s/^Version: .*/Version: $VERSION/" debian/DEBIAN/control

# Update version in HTML template
echo "🔧 Updating version in HTML template: $VERSION_NUMBER"
if [ -f "debian/opt/gamemanager/templates/index.html" ]; then
    sed -i "s/<version>/$VERSION_NUMBER/g" debian/opt/gamemanager/templates/index.html
fi

# Verify critical files are updated
echo "🔍 Verifying critical files..."
if ! grep -q "get_launchbox_metadata_path" debian/opt/gamemanager/app.py; then
    echo "❌ ERROR: app.py doesn't contain updated metadata path function!"
    exit 1
fi

if ! grep -q "os.makedirs.*metadata_path" debian/opt/gamemanager/app.py; then
    echo "❌ ERROR: app.py doesn't contain directory creation logic!"
    exit 1
fi

# Verify new files are included
if [ ! -f "debian/opt/gamemanager/credential_manager.py" ]; then
    echo "❌ ERROR: credential_manager.py not found in package!"
    exit 1
fi

if [ ! -f "debian/opt/gamemanager/screenscraper_service.py" ]; then
    echo "❌ ERROR: screenscraper_service.py not found in package!"
    exit 1
fi

if [ ! -f "debian/opt/gamemanager/game_utils.py" ]; then
    echo "❌ ERROR: game_utils.py not found in package!"
    exit 1
fi

if [ ! -f "debian/opt/gamemanager/steam_service.py" ]; then
    echo "❌ ERROR: steam_service.py not found in package!"
    exit 1
fi

if [ ! -f "debian/opt/gamemanager/steamgrid_service.py" ]; then
    echo "❌ ERROR: steamgrid_service.py not found in package!"
    exit 1
fi

if [ ! -f "debian/opt/gamemanager/mobygames_service.py" ]; then
    echo "❌ ERROR: mobygames_service.py not found in package!"
    exit 1
fi

if [ ! -f "debian/opt/gamemanager/igdb_service.py" ]; then
    echo "❌ ERROR: igdb_service.py not found in package!"
    exit 1
fi

if [ ! -f "debian/opt/gamemanager/emumovies_service.py" ]; then
    echo "❌ ERROR: emumovies_service.py not found in package!"
    exit 1
fi

if [ ! -f "debian/opt/gamemanager/custom_scraper_service.py" ]; then
    echo "❌ ERROR: custom_scraper_service.py not found in package!"
    exit 1
fi

if [ ! -f "debian/opt/gamemanager/datscrapper_service.py" ]; then
    echo "❌ ERROR: datscrapper_service.py not found in package!"
    exit 1
fi

if [ ! -f "debian/opt/gamemanager/launchbox_service.py" ]; then
    echo "❌ ERROR: launchbox_service.py not found in package!"
    exit 1
fi

if [ ! -f "debian/opt/gamemanager/scan_launchbox_media_types.py" ]; then
    echo "❌ ERROR: scan_launchbox_media_types.py not found in package!"
    exit 1
fi


if [ ! -f "debian/opt/gamemanager/var/config/credentials.enc" ]; then
    echo "❌ ERROR: credentials.enc not found in package!"
    exit 1
fi

if [ ! -f "debian/opt/gamemanager/var/config/scrappers.json" ]; then
    echo "❌ ERROR: scrappers.json not found in package!"
    exit 1
fi

if [ ! -f "debian/opt/gamemanager/var/config/systems.json" ]; then
    echo "❌ ERROR: systems.json not found in package!"
    exit 1
fi

if [ ! -d "debian/opt/gamemanager/var/db/mobygames" ]; then
    echo "❌ ERROR: MobyGames databases directory not found in package!"
    exit 1
fi

if [ ! -f "debian/opt/gamemanager/var/db/mobygames/Windows.json" ]; then
    echo "❌ ERROR: Windows.json MobyGames database not found in package!"
    exit 1
fi

# Verify IGDB pickle files are included (if they exist)
if [ -f "var/db/igdb/igdb_db.pkl" ] && [ ! -f "debian/opt/gamemanager/var/db/igdb/igdb_db.pkl" ]; then
    echo "❌ ERROR: igdb_db.pkl not found in package!"
    exit 1
fi

if [ -f "var/db/igdb/igdb_platform_partition_index.pkl" ] && [ ! -f "debian/opt/gamemanager/var/db/igdb/igdb_platform_partition_index.pkl" ]; then
    echo "❌ ERROR: igdb_platform_partition_index.pkl not found in package!"
    exit 1
fi

if [ -f "var/db/igdb/igdb_companies.pkl" ] && [ ! -f "debian/opt/gamemanager/var/db/igdb/igdb_companies.pkl" ]; then
    echo "❌ ERROR: igdb_companies.pkl not found in package!"
    exit 1
fi

if [ -f "var/db/igdb/igdb_genres.pkl" ] && [ ! -f "debian/opt/gamemanager/var/db/igdb/igdb_genres.pkl" ]; then
    echo "❌ ERROR: igdb_genres.pkl not found in package!"
    exit 1
fi

# Verify EmuMovies database files are included (if they exist)
if [ -f "var/db/emumovies/emumovies.json" ] && [ ! -f "debian/opt/gamemanager/var/db/emumovies/emumovies.json" ]; then
    echo "❌ ERROR: emumovies.json not found in package!"
    exit 1
fi

if [ -f "var/db/emumovies/emumovies_index.pkl" ] && [ ! -f "debian/opt/gamemanager/var/db/emumovies/emumovies_index.pkl" ]; then
    echo "❌ ERROR: emumovies_index.pkl not found in package!"
    exit 1
fi

if [ ! -d "debian/opt/gamemanager/pyrate_limiter" ]; then
    echo "❌ ERROR: pyrate_limiter directory not found in package!"
    exit 1
fi

# Verify pyrate_limiter structure is correct (not double-nested)
if [ -d "debian/opt/gamemanager/pyrate_limiter/pyrate_limiter" ]; then
    echo "❌ ERROR: pyrate_limiter has double-nested structure!"
    echo "   Found: debian/opt/gamemanager/pyrate_limiter/pyrate_limiter/"
    echo "   Expected: debian/opt/gamemanager/pyrate_limiter/"
    exit 1
fi

if [ ! -f "debian/opt/gamemanager/pyrate_limiter/__init__.py" ]; then
    echo "❌ ERROR: pyrate_limiter/__init__.py not found!"
    exit 1
fi

# Verify pixelmatch is included
if [ ! -d "debian/opt/gamemanager/pixelmatch" ]; then
    echo "❌ ERROR: pixelmatch directory not found in package!"
    exit 1
fi

if [ ! -f "debian/opt/gamemanager/pixelmatch/__init__.py" ]; then
    echo "❌ ERROR: pixelmatch/__init__.py not found!"
    exit 1
fi

if [ ! -f "debian/opt/gamemanager/pixelmatch/contrib/PIL.py" ]; then
    echo "❌ ERROR: pixelmatch/contrib/PIL.py not found!"
    exit 1
fi

# Verify selenium is included
if [ ! -d "debian/opt/gamemanager/selenium" ]; then
    echo "❌ ERROR: selenium directory not found in package!"
    exit 1
fi

if [ ! -f "debian/opt/gamemanager/selenium/__init__.py" ]; then
    echo "❌ ERROR: selenium/__init__.py not found!"
    exit 1
fi

if [ ! -f "debian/opt/gamemanager/selenium/webdriver/common/linux/selenium-manager" ]; then
    echo "❌ ERROR: selenium-manager binary not found!"
    exit 1
fi

# Verify typing_extensions is included
if [ ! -d "debian/opt/gamemanager/typing_extensions" ]; then
    echo "❌ ERROR: typing_extensions directory not found in package!"
    exit 1
fi

if [ ! -f "debian/opt/gamemanager/typing_extensions/__init__.py" ]; then
    echo "❌ ERROR: typing_extensions/__init__.py not found!"
    exit 1
fi

# Verify tools are included
if [ -f "tools/youtubedl" ] && [ ! -f "debian/opt/gamemanager/tools/youtubedl" ]; then
    echo "❌ ERROR: youtubedl not found in package!"
    exit 1
fi

echo "✅ Critical files verified"

# Build the Debian package
echo "🏗️  Building Debian package..."
dpkg-deb --build debian "$PACKAGE_NAME"

if [ $? -eq 0 ]; then
    echo "✅ Package built successfully: $PACKAGE_NAME"
    
    # Show package info
    echo "📊 Package information:"
    dpkg-deb --info "$PACKAGE_NAME" | head -10
    
    # Show package contents (first 20 files)
    echo "📁 Package contents (first 20 files):"
    dpkg-deb --contents "$PACKAGE_NAME" | head -20
    
    echo ""
    echo "🎉 Build completed successfully!"
    echo "📦 Package: $PACKAGE_NAME"
    echo "💡 To install: sudo dpkg -i $PACKAGE_NAME"
else
    echo "❌ Package build failed!"
    exit 1
fi
