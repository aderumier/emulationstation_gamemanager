# GameManager - Dockerfile for Debian 13
FROM debian:13-slim

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV FLASK_APP=app.py
ENV FLASK_ENV=production

# Accept image version as build argument
ARG IMAGE_VERSION="2.9.1-1"
ENV IMAGE_VERSION=${IMAGE_VERSION}

# Set working directory
WORKDIR /opt/gamemanager

# Install system dependencies and .deb package dependencies
# Optimized: removed development tools and unnecessary utilities
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Python runtime (removed dev tools: python3-pip, python3-venv, python3-dev, python3-setuptools)
    python3 \
    # .deb package dependencies
    python3-flask \
    python3-flask-login \
    python3-flask-socketio \
    python3-flask-cors \
    python3-flask-compress \
    python3-requests \
    python3-httpx \
    python3-h2 \
    python3-aiofiles \
    python3-bs4 \
    python3-pil \
    python3-lxml \
    python3-bcrypt \
    python3-dotenv \
    python3-wand \
    python3-jellyfish \
    python3-pymupdf \
    python3-websocket \
    # Application dependencies
    imagemagick \
    ffmpeg \
    yt-dlp \
    curl \
    wget \
    # dpkg-deb needed for .deb extraction
    dpkg \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Install Google Chrome
RUN apt-get update && \
    wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb -O /tmp/google-chrome.deb && \
    apt-get install -y /tmp/google-chrome.deb && \
    rm /tmp/google-chrome.deb && \
    rm -rf /var/lib/apt/lists/* && \
    apt-get clean

# Create non-root user for security (removed sudo group - not needed in container)
RUN useradd --create-home --shell /bin/bash appuser

# Copy the .deb package
ARG DEB_FILE=gamemanager_3.7.3-1_all.deb
COPY ${DEB_FILE} .

# Extract the .deb package manually (skip postinst script for Docker)
RUN dpkg-deb -x ${DEB_FILE} / && \
    rm ${DEB_FILE}

# Python packages are installed via system packages above

# Create necessary directories with proper structure first
RUN mkdir -p \
    /opt/gamemanager/roms \
    /opt/gamemanager/media \
    /opt/gamemanager/cache \
    /opt/gamemanager/var/task_logs \
    /opt/gamemanager/var/db \
    /opt/gamemanager/var/db/launchbox \
    /opt/gamemanager/var/db/igdb \
    /opt/gamemanager/var/db/screenscraper \
    /opt/gamemanager/var/db/mobygames \
    /opt/gamemanager/var/db/emumovies \
    /opt/gamemanager/var/sessions \
    /opt/gamemanager/var/gamelists \
    /opt/gamemanager/var/config

# Copy config files to default location outside var (for volume mount scenarios)
RUN cp /opt/gamemanager/var/config/config.json /opt/gamemanager/config.json.default && \
    cp /opt/gamemanager/var/config/scrappers.json /opt/gamemanager/scrappers.json.default && \
    cp /opt/gamemanager/var/config/systems.json /opt/gamemanager/systems.json.default && \
    cp /opt/gamemanager/var/config/genres.json /opt/gamemanager/genres.json.default && \
    cp /opt/gamemanager/var/config/scrapper_genre_mapping.json /opt/gamemanager/scrapper_genre_mapping.json.default && \
    chmod 644 /opt/gamemanager/config.json.default /opt/gamemanager/scrappers.json.default /opt/gamemanager/systems.json.default /opt/gamemanager/genres.json.default /opt/gamemanager/scrapper_genre_mapping.json.default && \
    chown appuser:appuser /opt/gamemanager/config.json.default /opt/gamemanager/scrappers.json.default /opt/gamemanager/systems.json.default /opt/gamemanager/genres.json.default /opt/gamemanager/scrapper_genre_mapping.json.default

# Copy platform cache files to default location outside var (for volume mount scenarios)
RUN (cp /opt/gamemanager/var/db/screenscraper/platforms.json /opt/gamemanager/screenscraper_platforms.json.default 2>/dev/null || echo '{}' > /opt/gamemanager/screenscraper_platforms.json.default) && \
    (cp /opt/gamemanager/var/db/igdb/platforms.json /opt/gamemanager/igdb_platforms.json.default 2>/dev/null || echo '{}' > /opt/gamemanager/igdb_platforms.json.default) && \
    (cp /opt/gamemanager/var/config/credentials.enc /opt/gamemanager/credentials.enc.default 2>/dev/null || touch /opt/gamemanager/credentials.enc.default) && \
    chmod 644 /opt/gamemanager/screenscraper_platforms.json.default /opt/gamemanager/igdb_platforms.json.default /opt/gamemanager/credentials.enc.default && \
    chown appuser:appuser /opt/gamemanager/screenscraper_platforms.json.default /opt/gamemanager/igdb_platforms.json.default /opt/gamemanager/credentials.enc.default

# Copy MobyGames database files to default location outside var (for volume mount scenarios)
RUN mkdir -p /opt/gamemanager/mobygames_db.default && \
    chmod -R 755 /opt/gamemanager/var/db/mobygames/ 2>/dev/null || true && \
    chmod -R 644 /opt/gamemanager/var/db/mobygames/*.json 2>/dev/null || true && \
    (cp -r /opt/gamemanager/var/db/mobygames/* /opt/gamemanager/mobygames_db.default/ 2>/dev/null || echo "No MobyGames database files found") && \
    chmod -R 755 /opt/gamemanager/mobygames_db.default/ && \
    chmod -R 644 /opt/gamemanager/mobygames_db.default/*.json 2>/dev/null || true && \
    chown -R appuser:appuser /opt/gamemanager/mobygames_db.default/

# Copy IGDB pickle files and JSON files to default location outside var (for volume mount scenarios)
RUN mkdir -p /opt/gamemanager/igdb_db.default && \
    chmod -R 755 /opt/gamemanager/var/db/igdb/ 2>/dev/null || true && \
    chmod -R 644 /opt/gamemanager/var/db/igdb/*.pkl 2>/dev/null || true && \
    chmod -R 644 /opt/gamemanager/var/db/igdb/*.json 2>/dev/null || true && \
    (cp /opt/gamemanager/var/db/igdb/*.pkl /opt/gamemanager/igdb_db.default/ 2>/dev/null || echo "No IGDB pickle files found") && \
    (cp /opt/gamemanager/var/db/igdb/*.json /opt/gamemanager/igdb_db.default/ 2>/dev/null || echo "No IGDB JSON files found") && \
    chmod -R 755 /opt/gamemanager/igdb_db.default/ && \
    chmod -R 644 /opt/gamemanager/igdb_db.default/*.pkl 2>/dev/null || true && \
    chmod -R 644 /opt/gamemanager/igdb_db.default/*.json 2>/dev/null || true && \
    chown -R appuser:appuser /opt/gamemanager/igdb_db.default/

# Copy EmuMovies database files to default location outside var (for volume mount scenarios)
RUN mkdir -p /opt/gamemanager/emumovies_db.default && \
    chmod -R 755 /opt/gamemanager/var/db/emumovies/ 2>/dev/null || true && \
    chmod -R 644 /opt/gamemanager/var/db/emumovies/*.json 2>/dev/null || true && \
    chmod -R 644 /opt/gamemanager/var/db/emumovies/*.pkl 2>/dev/null || true && \
    (cp /opt/gamemanager/var/db/emumovies/emumovies.json /opt/gamemanager/emumovies_db.default/ 2>/dev/null || echo "No EmuMovies JSON database found") && \
    (cp /opt/gamemanager/var/db/emumovies/emumovies_index.pkl /opt/gamemanager/emumovies_db.default/ 2>/dev/null || echo "No EmuMovies index pickle file found") && \
    chmod -R 755 /opt/gamemanager/emumovies_db.default/ && \
    chmod -R 644 /opt/gamemanager/emumovies_db.default/* 2>/dev/null || true && \
    chown -R appuser:appuser /opt/gamemanager/emumovies_db.default/

# Copy Custom database files to default location outside var (for volume mount scenarios)
RUN mkdir -p /opt/gamemanager/custom_db.default && \
    chmod -R 755 /opt/gamemanager/var/db/custom/ 2>/dev/null || true && \
    chmod -R 644 /opt/gamemanager/var/db/custom/*.json 2>/dev/null || true && \
    (cp /opt/gamemanager/var/db/custom/*.json /opt/gamemanager/custom_db.default/ 2>/dev/null || echo "No Custom JSON databases found") && \
    chmod -R 755 /opt/gamemanager/custom_db.default/ && \
    chmod -R 644 /opt/gamemanager/custom_db.default/*.json 2>/dev/null || true && \
    chown -R appuser:appuser /opt/gamemanager/custom_db.default/

# Copy font files to default location outside var (for volume mount scenarios)
RUN mkdir -p /opt/gamemanager/fonts.default && \
    chmod -R 755 /opt/gamemanager/var/fonts/ 2>/dev/null || true && \
    chmod -R 644 /opt/gamemanager/var/fonts/* 2>/dev/null || true && \
    (cp /opt/gamemanager/var/fonts/* /opt/gamemanager/fonts.default/ 2>/dev/null || echo "No font files found") && \
    chmod -R 755 /opt/gamemanager/fonts.default/ && \
    chmod -R 644 /opt/gamemanager/fonts.default/* 2>/dev/null || true && \
    chown -R appuser:appuser /opt/gamemanager/fonts.default/

# Copy 2D box template files to default location outside var (for volume mount scenarios)
RUN mkdir -p /opt/gamemanager/2dbox_templates.default && \
    chmod -R 755 /opt/gamemanager/var/2dbox/templates/ 2>/dev/null || true && \
    chmod -R 644 /opt/gamemanager/var/2dbox/templates/* 2>/dev/null || true && \
    (cp /opt/gamemanager/var/2dbox/templates/* /opt/gamemanager/2dbox_templates.default/ 2>/dev/null || echo "No 2D box templates found") && \
    chmod -R 755 /opt/gamemanager/2dbox_templates.default/ && \
    chmod -R 644 /opt/gamemanager/2dbox_templates.default/* 2>/dev/null || true && \
    chown -R appuser:appuser /opt/gamemanager/2dbox_templates.default/

# Copy 3D box template files to default location outside var (for volume mount scenarios)
RUN mkdir -p /opt/gamemanager/3dbox_templates.default && \
    chmod -R 755 /opt/gamemanager/var/3dbox/templates/ 2>/dev/null || true && \
    chmod -R 644 /opt/gamemanager/var/3dbox/templates/* 2>/dev/null || true && \
    (cp /opt/gamemanager/var/3dbox/templates/* /opt/gamemanager/3dbox_templates.default/ 2>/dev/null || echo "No 3D box templates found") && \
    chmod -R 755 /opt/gamemanager/3dbox_templates.default/ && \
    chmod -R 644 /opt/gamemanager/3dbox_templates.default/* 2>/dev/null || true && \
    chown -R appuser:appuser /opt/gamemanager/3dbox_templates.default/

# Copy mediatype files to default location outside var (for volume mount scenarios)
RUN (cp /opt/gamemanager/var/db/igdb/mediatype.txt /opt/gamemanager/igdb_mediatype.txt.default 2>/dev/null || echo 'cover\nscreenshots\nartworks\nlogos' > /opt/gamemanager/igdb_mediatype.txt.default) && \
    (cp /opt/gamemanager/var/db/launchbox/mediatype.json /opt/gamemanager/launchbox_mediatype.json.default 2>/dev/null || echo '{}' > /opt/gamemanager/launchbox_mediatype.json.default) && \
    (cp /opt/gamemanager/var/db/steam/mediastype.txt /opt/gamemanager/steam_mediastype.txt.default 2>/dev/null || echo 'capsule\nlogo\nhero\nscreenshot' > /opt/gamemanager/steam_mediastype.txt.default) && \
    (cp /opt/gamemanager/var/db/steamgrid/mediastype.txt /opt/gamemanager/steamgrid_mediastype.txt.default 2>/dev/null || echo 'grids\nlogos\nheroes' > /opt/gamemanager/steamgrid_mediastype.txt.default) && \
    chmod 644 /opt/gamemanager/igdb_mediatype.txt.default /opt/gamemanager/launchbox_mediatype.json.default /opt/gamemanager/steam_mediastype.txt.default /opt/gamemanager/steamgrid_mediastype.txt.default && \
    chown appuser:appuser /opt/gamemanager/igdb_mediatype.txt.default /opt/gamemanager/launchbox_mediatype.json.default /opt/gamemanager/steam_mediastype.txt.default /opt/gamemanager/steamgrid_mediastype.txt.default

# Ensure config files exist and are readable in var
RUN ls -la /opt/gamemanager/var/config/ && \
    chmod 644 /opt/gamemanager/var/config/* && \
    chown appuser:appuser /opt/gamemanager/var/config/*

# Application files are installed by the .deb package

# Create startup script to handle config files and directories for volume mounts
RUN cat > /opt/gamemanager/start.sh << 'EOF'
#!/bin/bash
set -e

# Create all necessary directories if they don't exist (for volume mount scenarios)
echo "Creating application directories..."
mkdir -p /opt/gamemanager/var/config
mkdir -p /opt/gamemanager/var/db
mkdir -p /opt/gamemanager/var/db/launchbox
mkdir -p /opt/gamemanager/var/db/igdb
mkdir -p /opt/gamemanager/var/db/screenscraper
mkdir -p /opt/gamemanager/var/db/mobygames
mkdir -p /opt/gamemanager/var/db/emumovies
mkdir -p /opt/gamemanager/var/db/custom
mkdir -p /opt/gamemanager/var/db/steam
mkdir -p /opt/gamemanager/var/db/steamgrid
mkdir -p /opt/gamemanager/var/db/dats
mkdir -p /opt/gamemanager/var/sessions
mkdir -p /opt/gamemanager/var/task_logs
mkdir -p /opt/gamemanager/var/gamelists
mkdir -p /opt/gamemanager/var/cache
mkdir -p /opt/gamemanager/var/temp

# Check for image upgrade and clear cache if version changed
VERSION_FILE="/opt/gamemanager/var/cache/.image_version"
IMAGE_VERSION="${IMAGE_VERSION:-unknown}"

if [ -f "$VERSION_FILE" ]; then
    STORED_VERSION=$(cat "$VERSION_FILE" 2>/dev/null || echo "")
    if [ "$STORED_VERSION" != "$IMAGE_VERSION" ]; then
        echo "🔄 Image version changed from '$STORED_VERSION' to '$IMAGE_VERSION'"
        echo "Clearing cache directory for clean upgrade..."
        rm -rf /opt/gamemanager/var/cache/*
        echo "✅ Cache directory cleared"
    else
        echo "✅ Image version unchanged ($IMAGE_VERSION), keeping cache"
    fi
else
    echo "First run detected (version: $IMAGE_VERSION), cache will be built on demand"
fi

# Store current image version
echo "$IMAGE_VERSION" > "$VERSION_FILE"

# Backup existing template files if they exist (before copying new ones)
TEMPLATE_BACKUP_DIR="/opt/gamemanager/var/cache/.template_backup"
mkdir -p "$TEMPLATE_BACKUP_DIR"

if [ -n "$(ls -A /opt/gamemanager/var/2dbox/templates 2>/dev/null)" ]; then
    echo "Backing up existing 2D box templates..."
    mkdir -p "$TEMPLATE_BACKUP_DIR/2dbox"
    cp -r /opt/gamemanager/var/2dbox/templates/* "$TEMPLATE_BACKUP_DIR/2dbox/" 2>/dev/null || true
    echo "✅ Backed up 2D box templates"
fi

if [ -n "$(ls -A /opt/gamemanager/var/3dbox/templates 2>/dev/null)" ]; then
    echo "Backing up existing 3D box templates..."
    mkdir -p "$TEMPLATE_BACKUP_DIR/3dbox"
    cp -r /opt/gamemanager/var/3dbox/templates/* "$TEMPLATE_BACKUP_DIR/3dbox/" 2>/dev/null || true
    echo "✅ Backed up 3D box templates"
fi

mkdir -p /opt/gamemanager/var/temp/medias
mkdir -p /opt/gamemanager/var/temp/videos
mkdir -p /opt/gamemanager/var/fonts
mkdir -p /opt/gamemanager/var/2dbox/templates
mkdir -p /opt/gamemanager/var/3dbox/templates

# Copy default config files if they don't exist in var/config
if [ ! -f /opt/gamemanager/var/config/config.json ]; then
    echo "Copying default config.json to var/config/"
    cp /opt/gamemanager/config.json.default /opt/gamemanager/var/config/config.json
fi

if [ ! -f /opt/gamemanager/var/config/scrappers.json ]; then
    echo "Copying default scrappers.json to var/config/"
    cp /opt/gamemanager/scrappers.json.default /opt/gamemanager/var/config/scrappers.json
fi

if [ ! -f /opt/gamemanager/var/config/systems.json ]; then
    echo "Copying default systems.json to var/config/"
    cp /opt/gamemanager/systems.json.default /opt/gamemanager/var/config/systems.json
fi

if [ ! -f /opt/gamemanager/var/config/genres.json ]; then
    echo "Copying default genres.json to var/config/"
    cp /opt/gamemanager/genres.json.default /opt/gamemanager/var/config/genres.json
fi

if [ ! -f /opt/gamemanager/var/config/scrapper_genre_mapping.json ]; then
    echo "Copying default scrapper_genre_mapping.json to var/config/"
    cp /opt/gamemanager/scrapper_genre_mapping.json.default /opt/gamemanager/var/config/scrapper_genre_mapping.json
fi


# Copy platform cache files to var/db (always copy to ensure they're in the volume)
echo "Copying platform cache files to var/db..."
cp /opt/gamemanager/screenscraper_platforms.json.default /opt/gamemanager/var/db/screenscraper/platforms.json
cp /opt/gamemanager/igdb_platforms.json.default /opt/gamemanager/var/db/igdb/platforms.json
cp /opt/gamemanager/credentials.enc.default /opt/gamemanager/var/config/credentials.enc

# Copy mediatype files to var/db (always copy to ensure they're in the volume)
echo "Copying mediatype files to var/db..."
cp /opt/gamemanager/igdb_mediatype.txt.default /opt/gamemanager/var/db/igdb/mediatype.txt
cp /opt/gamemanager/launchbox_mediatype.json.default /opt/gamemanager/var/db/launchbox/mediatype.json
cp /opt/gamemanager/steam_mediastype.txt.default /opt/gamemanager/var/db/steam/mediastype.txt
cp /opt/gamemanager/steamgrid_mediastype.txt.default /opt/gamemanager/var/db/steamgrid/mediastype.txt

# Copy IGDB pickle files and JSON files to var/db (always copy to ensure they're in the volume)
echo "Copying IGDB pickle files and JSON files to var/db/igdb..."
if [ -d /opt/gamemanager/igdb_db.default ] && [ "$(ls -A /opt/gamemanager/igdb_db.default 2>/dev/null)" ]; then
    cp /opt/gamemanager/igdb_db.default/*.pkl /opt/gamemanager/var/db/igdb/ 2>/dev/null || echo "⚠️  No IGDB pickle files found"
    cp /opt/gamemanager/igdb_db.default/*.json /opt/gamemanager/var/db/igdb/ 2>/dev/null || echo "⚠️  No IGDB JSON files found"
    echo "✅ IGDB database files copied to volume"
else
    echo "⚠️  No IGDB database files found in default location"
fi

# Copy MobyGames database files to var/db (always copy to ensure they're in the volume)
echo "Copying MobyGames database files to var/db/mobygames..."
if [ -d /opt/gamemanager/mobygames_db.default ] && [ "$(ls -A /opt/gamemanager/mobygames_db.default 2>/dev/null)" ]; then
    cp -r /opt/gamemanager/mobygames_db.default/* /opt/gamemanager/var/db/mobygames/
    echo "✅ MobyGames database files copied to volume"
else
    echo "⚠️  No MobyGames database files found in default location"
fi

# Copy additional database files to var/db (always copy to ensure they're in the volume)
echo "Copying additional database files to var/db..."
# Create empty files for cache and data files that will be populated by the application (only if they don't exist and weren't copied from default)
# Note: IGDB JSON files are now copied from igdb_db.default above, so we only create empty files if they're still missing
[ ! -f /opt/gamemanager/var/db/igdb/companies.json ] && touch /opt/gamemanager/var/db/igdb/companies.json
[ ! -f /opt/gamemanager/var/db/igdb/genres.json ] && touch /opt/gamemanager/var/db/igdb/genres.json
[ ! -f /opt/gamemanager/var/db/igdb/regions_cache.json ] && touch /opt/gamemanager/var/db/igdb/regions_cache.json
[ ! -f /opt/gamemanager/var/db/igdb/sample_games.json ] && touch /opt/gamemanager/var/db/igdb/sample_games.json
# Metadata.xml should only be created when downloading metadata, not as an empty file
[ ! -f /opt/gamemanager/var/db/steam/appindex.json ] && touch /opt/gamemanager/var/db/steam/appindex.json

# Copy EmuMovies database files to var/db (always copy to ensure they're in the volume)
echo "Copying EmuMovies database files to var/db/emumovies..."
if [ -d /opt/gamemanager/emumovies_db.default ] && [ "$(ls -A /opt/gamemanager/emumovies_db.default 2>/dev/null)" ]; then
    cp /opt/gamemanager/emumovies_db.default/* /opt/gamemanager/var/db/emumovies/
    echo "✅ EmuMovies database files copied to volume"
else
    echo "⚠️  No EmuMovies database files found in default location"
fi

# Copy Custom database files to var/db (always copy to ensure they're in the volume)
echo "Copying Custom database files to var/db/custom..."
if [ -d /opt/gamemanager/custom_db.default ] && [ "$(ls -A /opt/gamemanager/custom_db.default 2>/dev/null)" ]; then
    cp /opt/gamemanager/custom_db.default/*.json /opt/gamemanager/var/db/custom/
    echo "✅ Custom database files copied to volume"
else
    echo "⚠️  No Custom database files found in default location"
fi

# Copy font files to var/fonts (always copy to ensure they're in the volume)
echo "Copying font files to var/fonts..."
if [ -d /opt/gamemanager/fonts.default ] && [ "$(ls -A /opt/gamemanager/fonts.default 2>/dev/null)" ]; then
    cp /opt/gamemanager/fonts.default/* /opt/gamemanager/var/fonts/
    echo "✅ Font files copied to volume"
else
    echo "⚠️  No font files found in default location"
fi

# Copy 2D box template files to var/2dbox/templates (always copy from image, restore backups if they existed)
echo "Copying 2D box template files to var/2dbox/templates..."
if [ -d /opt/gamemanager/2dbox_templates.default ] && [ "$(ls -A /opt/gamemanager/2dbox_templates.default 2>/dev/null)" ]; then
    cp /opt/gamemanager/2dbox_templates.default/* /opt/gamemanager/var/2dbox/templates/ 2>/dev/null || true
    echo "✅ 2D box template files copied from image"
else
    echo "⚠️  No 2D box template files found in default location"
fi

# Restore backed up 2D box templates if they existed (overwrites image templates)
if [ -d "$TEMPLATE_BACKUP_DIR/2dbox" ] && [ -n "$(ls -A "$TEMPLATE_BACKUP_DIR/2dbox" 2>/dev/null)" ]; then
    echo "Restoring existing 2D box templates (directory was not empty before image update)..."
    cp -r "$TEMPLATE_BACKUP_DIR/2dbox"/* /opt/gamemanager/var/2dbox/templates/ 2>/dev/null || true
    echo "✅ Restored existing 2D box templates (overwrote image templates)"
fi

# Copy 3D box template files to var/3dbox/templates (always copy from image, restore backups if they existed)
echo "Copying 3D box template files to var/3dbox/templates..."
if [ -d /opt/gamemanager/3dbox_templates.default ] && [ "$(ls -A /opt/gamemanager/3dbox_templates.default 2>/dev/null)" ]; then
    cp /opt/gamemanager/3dbox_templates.default/* /opt/gamemanager/var/3dbox/templates/ 2>/dev/null || true
    echo "✅ 3D box template files copied from image"
else
    echo "⚠️  No 3D box template files found in default location"
fi

# Restore backed up 3D box templates if they existed (overwrites image templates)
if [ -d "$TEMPLATE_BACKUP_DIR/3dbox" ] && [ -n "$(ls -A "$TEMPLATE_BACKUP_DIR/3dbox" 2>/dev/null)" ]; then
    echo "Restoring existing 3D box templates (directory was not empty before image update)..."
    cp -r "$TEMPLATE_BACKUP_DIR/3dbox"/* /opt/gamemanager/var/3dbox/templates/ 2>/dev/null || true
    echo "✅ Restored existing 3D box templates (overwrote image templates)"
fi

# Clean up backup directory
rm -rf "$TEMPLATE_BACKUP_DIR" 2>/dev/null || true

# Ensure proper permissions
chmod 644 /opt/gamemanager/var/config/* 2>/dev/null || true
chmod 644 /opt/gamemanager/var/db/screenscraper/* 2>/dev/null || true
chmod 644 /opt/gamemanager/var/db/igdb/* 2>/dev/null || true
chmod 644 /opt/gamemanager/var/db/launchbox/* 2>/dev/null || true
chmod 644 /opt/gamemanager/var/db/mobygames/* 2>/dev/null || true
chmod 644 /opt/gamemanager/var/db/emumovies/* 2>/dev/null || true
chmod 644 /opt/gamemanager/var/db/custom/* 2>/dev/null || true
chmod 644 /opt/gamemanager/var/db/steam/* 2>/dev/null || true
chmod 644 /opt/gamemanager/var/db/steamgrid/* 2>/dev/null || true
chmod 755 /opt/gamemanager/var/2dbox/templates 2>/dev/null || true
chmod 644 /opt/gamemanager/var/2dbox/templates/* 2>/dev/null || true
chmod 755 /opt/gamemanager/var/3dbox/templates 2>/dev/null || true
chmod 644 /opt/gamemanager/var/3dbox/templates/* 2>/dev/null || true

echo "✅ All directories and configuration files ready"
echo "Starting GameManager..."

# Start the application
exec python3 /opt/gamemanager/app.py
EOF

RUN chmod +x /opt/gamemanager/start.sh && \
    chown appuser:appuser /opt/gamemanager/start.sh

# Set ownership
RUN chown -R appuser:appuser /opt/gamemanager

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/ || exit 1

# Set default command to use startup script
CMD ["/opt/gamemanager/start.sh"]

# Labels for metadata
LABEL maintainer="GameManager Team <admin@gamemanager.local>"
LABEL description="Game Collection Management System with LaunchBox integration"
LABEL version="${IMAGE_VERSION}"
LABEL org.opencontainers.image.source="https://github.com/aderumier/emulationstation_gamemanager"
LABEL org.opencontainers.image.description="Flask-based web application for managing game collections with metadata and media from LaunchBox database"
