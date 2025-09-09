#!/bin/bash

# GameManager Debian Package Builder
# This script ensures the Debian package always contains the latest source files

set -e  # Exit on any error

echo "🔨 Building GameManager Debian Package..."

# Get version from control file
VERSION=$(grep "^Version:" debian/DEBIAN/control | cut -d' ' -f2)
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
cp requirements.txt debian/opt/gamemanager/requirements.txt

# Static files
cp -r static/* debian/opt/gamemanager/static/
cp -r templates/* debian/opt/gamemanager/templates/

# Configuration files
cp var/config/config.json debian/opt/gamemanager/var/config/config.json
cp var/config/user.cfg debian/opt/gamemanager/var/config/user.cfg

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
