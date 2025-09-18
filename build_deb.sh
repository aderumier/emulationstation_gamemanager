#!/bin/bash

# GameManager Debian Package Builder
# This script ensures the Debian package always contains the latest source files

set -e  # Exit on any error

echo "🔨 Building GameManager Debian Package..."

# Get version from git tag
if git describe --tags --exact-match HEAD >/dev/null 2>&1; then
    # We're on a tag, use it as version
    GIT_TAG=$(git describe --tags --exact-match HEAD)
    # Remove 'v' prefix if present for Debian package version
    VERSION_NUMBER=${GIT_TAG#v}
    VERSION="${VERSION_NUMBER}-1"
    echo "🏷️  Using git tag: $GIT_TAG -> version: $VERSION"
else
    # Not on a tag, use control file version
    VERSION=$(grep "^Version:" debian/DEBIAN/control | cut -d' ' -f2)
    echo "⚠️  Not on a git tag, using control file version: $VERSION"
fi

PACKAGE_NAME="gamemanager_${VERSION}_all.deb"

echo "📦 Package: $PACKAGE_NAME"

# Clean previous build
echo "🧹 Cleaning previous build..."
rm -f "$PACKAGE_NAME"

# Sync latest source files to Debian package directory
echo "📋 Syncing latest source files..."

# Core application files
cp app.py debian/opt/gamemanager/app.py
cp box_generator.py debian/opt/gamemanager/box_generator.py
cp download_manager.py debian/opt/gamemanager/download_manager.py
cp credential_manager.py debian/opt/gamemanager/credential_manager.py
cp screenscraper_service.py debian/opt/gamemanager/screenscraper_service.py
cp game_utils.py debian/opt/gamemanager/game_utils.py
cp steam_service.py debian/opt/gamemanager/steam_service.py
cp steamgrid_service.py debian/opt/gamemanager/steamgrid_service.py
cp requirements.txt debian/opt/gamemanager/requirements.txt

# Static files
cp -r static/* debian/opt/gamemanager/static/
cp -r templates/* debian/opt/gamemanager/templates/

# Configuration files
cp var/config/config.json debian/opt/gamemanager/var/config/config.json

# Credentials and embedded modules
cp var/config/credentials.enc debian/opt/gamemanager/var/config/credentials.enc
cp -r pyrate_limiter debian/opt/gamemanager/pyrate_limiter

# Fix paths in config.json for production environment
echo "🔧 Updating paths for production environment..."
sed -i 's|"roms_root_directory": "/home/aderumier/cursorscraper/roms"|"roms_root_directory": "/opt/gamemanager/roms"|g' debian/opt/gamemanager/var/config/config.json

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

if [ ! -f "debian/opt/gamemanager/var/config/credentials.enc" ]; then
    echo "❌ ERROR: credentials.enc not found in package!"
    exit 1
fi

if [ ! -d "debian/opt/gamemanager/pyrate_limiter" ]; then
    echo "❌ ERROR: pyrate_limiter directory not found in package!"
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
