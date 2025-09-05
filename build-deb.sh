#!/bin/bash
set -e

# Build script for GameManager .deb package

echo "Building GameManager .deb package..."

# Clean previous builds
echo "Cleaning previous builds..."
rm -rf debian/opt
rm -rf debian/usr
rm -rf debian/etc
rm -f *.deb

# Create package structure
echo "Creating package structure..."
mkdir -p debian/opt/gamemanager
mkdir -p debian/usr/share/doc/gamemanager
mkdir -p debian/usr/share/applications

# Copy application files
echo "Copying application files..."
cp -r app.py download_manager.py box_generator.py static templates requirements.txt README.md AUTHENTICATION_SETUP.md DISCORD_SETUP_EXAMPLE.md Dockerfile docker-compose.yml .dockerignore debian/opt/gamemanager/

# Copy configuration files
echo "Copying configuration files..."
mkdir -p debian/opt/gamemanager/var/config
cp var/config/config.json debian/opt/gamemanager/var/config/
cp var/config/user.cfg debian/opt/gamemanager/var/config/ 2>/dev/null || true

# Update config.json for system installation
echo "Updating configuration for system installation..."
sed -i 's|"roms_root_directory": "[^"]*"|"roms_root_directory": "/opt/gamemanager/roms"|g' debian/opt/gamemanager/var/config/config.json

# Create desktop entry
echo "Creating desktop entry..."
cat > debian/usr/share/applications/gamemanager.desktop << 'EOF'
[Desktop Entry]
Name=GameManager
Comment=Game Collection Management System
Exec=python3 /opt/gamemanager/app.py
Icon=applications-games
Terminal=true
Type=Application
Categories=Game;Utility;
EOF

# Copy documentation
echo "Copying documentation..."
cp README.md debian/usr/share/doc/gamemanager/
cp AUTHENTICATION_SETUP.md debian/usr/share/doc/gamemanager/
cp DISCORD_SETUP_EXAMPLE.md debian/usr/share/doc/gamemanager/

# Create changelog
echo "Creating changelog..."
cat > debian/usr/share/doc/gamemanager/changelog << 'EOF'
gamemanager (1.0-1) unstable; urgency=medium

  * Initial release of GameManager v1.0
  * Complete game collection management system
  * LaunchBox integration for metadata and media
  * 2D box art generation with ImageMagick
  * Video processing and YouTube integration
  * Docker support and production deployment
  * Systemd service integration
  * Comprehensive documentation

 -- GameManager Team <admin@gamemanager.local>  $(date -R)
EOF

# Compress changelog
gzip -9 debian/usr/share/doc/gamemanager/changelog

# Set permissions
echo "Setting permissions..."
chmod 755 debian/opt/gamemanager/app.py
find debian/opt/gamemanager -name "*.py" -exec chmod 644 {} \; 2>/dev/null || true
find debian/opt/gamemanager -name "*.md" -exec chmod 644 {} \; 2>/dev/null || true
find debian/opt/gamemanager -name "*.yml" -exec chmod 644 {} \; 2>/dev/null || true
find debian/opt/gamemanager -name "*.json" -exec chmod 644 {} \; 2>/dev/null || true
find debian/opt/gamemanager/var/config -type f -exec chmod 644 {} \; 2>/dev/null || true
chmod 644 debian/usr/share/applications/gamemanager.desktop
find debian/usr/share/doc/gamemanager -type f -exec chmod 644 {} \; 2>/dev/null || true

# Build the .deb package
echo "Building .deb package..."
dpkg-deb --build debian gamemanager_1.4-1_all.deb

# Verify the package
echo "Verifying package..."
dpkg-deb --info gamemanager_1.4-1_all.deb
echo ""
echo "Package contents:"
dpkg-deb --contents gamemanager_1.4-1_all.deb

echo ""
echo "✅ GameManager .deb package built successfully!"
echo "Package: gamemanager_1.4-1_all.deb"
echo ""
echo "To install:"
echo "  sudo dpkg -i gamemanager_1.4-1_all.deb"
echo ""
echo "To fix dependencies:"
echo "  sudo apt-get install -f"
echo ""
echo "To remove:"
echo "  sudo dpkg -r gamemanager"
