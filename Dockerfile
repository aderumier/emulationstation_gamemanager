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
COPY gamemanager_1.6-1_all.deb .

# Extract the .deb package manually (skip postinst script for Docker)
RUN dpkg-deb -x gamemanager_1.6-1_all.deb / && \
    rm gamemanager_1.6-1_all.deb

# Create necessary directories with proper structure first
RUN mkdir -p \
    /opt/gamemanager/roms \
    /opt/gamemanager/media \
    /opt/gamemanager/cache \
    /opt/gamemanager/var/task_logs \
    /opt/gamemanager/var/db/launchbox \
    /opt/gamemanager/var/sessions \
    /opt/gamemanager/var/gamelists \
    /opt/gamemanager/var/config

# Application files are installed by the .deb package

# Set ownership
RUN chown -R appuser:appuser /opt/gamemanager

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/ || exit 1

# Set default command
CMD ["python3", "/opt/gamemanager/app.py"]

# Labels for metadata
LABEL maintainer="GameManager Team <admin@gamemanager.local>"
LABEL description="Game Collection Management System with LaunchBox integration"
LABEL version="1.6-1"
LABEL org.opencontainers.image.source="https://github.com/yourusername/gamemanager"
LABEL org.opencontainers.image.description="Flask-based web application for managing game collections with metadata and media from LaunchBox database"
