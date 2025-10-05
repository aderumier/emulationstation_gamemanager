# GameManager - Dockerfile for Debian 13
FROM debian:13-slim

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV FLASK_APP=app.py
ENV FLASK_ENV=production

# Set working directory
WORKDIR /opt/gamemanager

# Install system dependencies and .deb package dependencies
RUN apt-get update && apt-get install -y \
    # Python and development tools
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    python3-setuptools \
    # .deb package dependencies
    python3-flask \
    python3-flask-login \
    python3-flask-socketio \
    python3-flask-cors \
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
    # Application dependencies
    imagemagick \
    ffmpeg \
    yt-dlp \
    git \
    curl \
    wget \
    # Additional utilities
    procps \
    htop \
    nano \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash appuser && \
    usermod -aG sudo appuser

# Copy the .deb package
COPY gamemanager_2.4.1-1_all.deb .

# Extract the .deb package manually (skip postinst script for Docker)
RUN dpkg-deb -x gamemanager_2.4.1-1_all.deb / && \
    rm gamemanager_2.4.1-1_all.deb

# Install the package dependencies manually
# Note: python3-jellyfish installation may fail due to network issues
# The application will work without it, but some features may be limited
RUN apt-get update && \
    (apt-get install -y python3-jellyfish || echo "Warning: Failed to install python3-jellyfish, continuing without it") && \
    rm -rf /var/lib/apt/lists/*

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
    /opt/gamemanager/var/sessions \
    /opt/gamemanager/var/gamelists \
    /opt/gamemanager/var/config

# Copy config files to default location outside var (for volume mount scenarios)
RUN cp /opt/gamemanager/var/config/config.json /opt/gamemanager/config.json.default && \
    cp /opt/gamemanager/var/config/scrappers.json /opt/gamemanager/scrappers.json.default && \
    cp /opt/gamemanager/var/config/systems.json /opt/gamemanager/systems.json.default && \
    chmod 644 /opt/gamemanager/config.json.default /opt/gamemanager/scrappers.json.default /opt/gamemanager/systems.json.default && \
    chown appuser:appuser /opt/gamemanager/config.json.default /opt/gamemanager/scrappers.json.default /opt/gamemanager/systems.json.default

# Copy platform cache files to default location outside var (for volume mount scenarios)
RUN (cp /opt/gamemanager/var/db/screenscraper/platforms.json /opt/gamemanager/screenscraper_platforms.json.default 2>/dev/null || echo '{}' > /opt/gamemanager/screenscraper_platforms.json.default) && \
    (cp /opt/gamemanager/var/db/igdb/platforms.json /opt/gamemanager/igdb_platforms.json.default 2>/dev/null || echo '{}' > /opt/gamemanager/igdb_platforms.json.default) && \
    (cp /opt/gamemanager/var/config/credentials.enc /opt/gamemanager/credentials.enc.default 2>/dev/null || touch /opt/gamemanager/credentials.enc.default) && \
    chmod 644 /opt/gamemanager/screenscraper_platforms.json.default /opt/gamemanager/igdb_platforms.json.default /opt/gamemanager/credentials.enc.default && \
    chown appuser:appuser /opt/gamemanager/screenscraper_platforms.json.default /opt/gamemanager/igdb_platforms.json.default /opt/gamemanager/credentials.enc.default

# Copy MobyGames database files to default location outside var (for volume mount scenarios)
RUN mkdir -p /opt/gamemanager/mobygames_db.default && \
    (cp -r /opt/gamemanager/var/db/mobygames/* /opt/gamemanager/mobygames_db.default/ 2>/dev/null || echo "No MobyGames database files found") && \
    chmod -R 644 /opt/gamemanager/mobygames_db.default/ && \
    chown -R appuser:appuser /opt/gamemanager/mobygames_db.default/

# Copy mediatype files to default location outside var (for volume mount scenarios)
RUN (cp /opt/gamemanager/var/db/igdb/mediatype.txt /opt/gamemanager/igdb_mediatype.txt.default 2>/dev/null || echo 'cover\nscreenshots\nartworks\nlogos' > /opt/gamemanager/igdb_mediatype.txt.default) && \
    (cp /opt/gamemanager/var/db/launchbox/mediatype.json /opt/gamemanager/launchbox_mediatype.json.default 2>/dev/null || echo '{}' > /opt/gamemanager/launchbox_mediatype.json.default) && \
    (cp /opt/gamemanager/var/db/screenscraper/mediastype.txt /opt/gamemanager/screenscraper_mediastype.txt.default 2>/dev/null || echo 'wheel\nscreenmarquee\nbox-2d\nbox-3d\ncartridge\nflyer\nfanart\nscreenshot\ntitlescreen\nvideo' > /opt/gamemanager/screenscraper_mediastype.txt.default) && \
    (cp /opt/gamemanager/var/db/steam/mediastype.txt /opt/gamemanager/steam_mediastype.txt.default 2>/dev/null || echo 'capsule\nlogo\nhero\nscreenshot' > /opt/gamemanager/steam_mediastype.txt.default) && \
    (cp /opt/gamemanager/var/db/steamgrid/mediastype.txt /opt/gamemanager/steamgrid_mediastype.txt.default 2>/dev/null || echo 'grids\nlogos\nheroes' > /opt/gamemanager/steamgrid_mediastype.txt.default) && \
    chmod 644 /opt/gamemanager/igdb_mediatype.txt.default /opt/gamemanager/launchbox_mediatype.json.default /opt/gamemanager/screenscraper_mediastype.txt.default /opt/gamemanager/steam_mediastype.txt.default /opt/gamemanager/steamgrid_mediastype.txt.default && \
    chown appuser:appuser /opt/gamemanager/igdb_mediatype.txt.default /opt/gamemanager/launchbox_mediatype.json.default /opt/gamemanager/screenscraper_mediastype.txt.default /opt/gamemanager/steam_mediastype.txt.default /opt/gamemanager/steamgrid_mediastype.txt.default

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
mkdir -p /opt/gamemanager/var/db/steam
mkdir -p /opt/gamemanager/var/db/steamgrid
mkdir -p /opt/gamemanager/var/sessions
mkdir -p /opt/gamemanager/var/task_logs
mkdir -p /opt/gamemanager/var/gamelists
mkdir -p /opt/gamemanager/var/cache
mkdir -p /opt/gamemanager/var/temp
mkdir -p /opt/gamemanager/var/temp/medias
mkdir -p /opt/gamemanager/var/temp/videos

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


# Copy platform cache files to var/db (always copy to ensure they're in the volume)
echo "Copying platform cache files to var/db..."
cp /opt/gamemanager/screenscraper_platforms.json.default /opt/gamemanager/var/db/screenscraper/platforms.json
cp /opt/gamemanager/igdb_platforms.json.default /opt/gamemanager/var/db/igdb/platforms.json
cp /opt/gamemanager/credentials.enc.default /opt/gamemanager/var/config/credentials.enc

# Copy mediatype files to var/db (always copy to ensure they're in the volume)
echo "Copying mediatype files to var/db..."
cp /opt/gamemanager/igdb_mediatype.txt.default /opt/gamemanager/var/db/igdb/mediatype.txt
cp /opt/gamemanager/launchbox_mediatype.json.default /opt/gamemanager/var/db/launchbox/mediatype.json
cp /opt/gamemanager/screenscraper_mediastype.txt.default /opt/gamemanager/var/db/screenscraper/mediastype.txt
cp /opt/gamemanager/steam_mediastype.txt.default /opt/gamemanager/var/db/steam/mediastype.txt
cp /opt/gamemanager/steamgrid_mediastype.txt.default /opt/gamemanager/var/db/steamgrid/mediastype.txt

# Copy additional database files to var/db (always copy to ensure they're in the volume)
echo "Copying additional database files to var/db..."
# Create empty files for cache and data files that will be populated by the application (only if they don't exist)
[ ! -f /opt/gamemanager/var/db/igdb/companies.json ] && touch /opt/gamemanager/var/db/igdb/companies.json
[ ! -f /opt/gamemanager/var/db/igdb/genres.json ] && touch /opt/gamemanager/var/db/igdb/genres.json
[ ! -f /opt/gamemanager/var/db/igdb/regions_cache.json ] && touch /opt/gamemanager/var/db/igdb/regions_cache.json
[ ! -f /opt/gamemanager/var/db/igdb/sample_games.json ] && touch /opt/gamemanager/var/db/igdb/sample_games.json
[ ! -f /opt/gamemanager/var/db/screenscraper/user_info.json ] && touch /opt/gamemanager/var/db/screenscraper/user_info.json
[ ! -f /opt/gamemanager/var/db/launchbox/Metadata.xml ] && touch /opt/gamemanager/var/db/launchbox/Metadata.xml
[ ! -f /opt/gamemanager/var/db/steam/appindex.json ] && touch /opt/gamemanager/var/db/steam/appindex.json

# Copy MobyGames database files to var/db (always copy to ensure they're in the volume)
echo "Copying MobyGames database files to var/db/mobygames..."
if [ -d /opt/gamemanager/mobygames_db.default ] && [ "$(ls -A /opt/gamemanager/mobygames_db.default 2>/dev/null)" ]; then
    cp -r /opt/gamemanager/mobygames_db.default/* /opt/gamemanager/var/db/mobygames/
    echo "✅ MobyGames database files copied to volume"
else
    echo "⚠️  No MobyGames database files found in default location"
fi

# Ensure proper permissions
chmod 644 /opt/gamemanager/var/config/* 2>/dev/null || true
chmod 644 /opt/gamemanager/var/db/screenscraper/* 2>/dev/null || true
chmod 644 /opt/gamemanager/var/db/igdb/* 2>/dev/null || true
chmod 644 /opt/gamemanager/var/db/launchbox/* 2>/dev/null || true
chmod 644 /opt/gamemanager/var/db/mobygames/* 2>/dev/null || true
chmod 644 /opt/gamemanager/var/db/steam/* 2>/dev/null || true
chmod 644 /opt/gamemanager/var/db/steamgrid/* 2>/dev/null || true

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
LABEL version="2.0-1"
LABEL org.opencontainers.image.source="https://github.com/yourusername/gamemanager"
LABEL org.opencontainers.image.description="Flask-based web application for managing game collections with metadata and media from LaunchBox database"
