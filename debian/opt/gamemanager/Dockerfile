# Batocera Game Collection Manager - Dockerfile for Debian 13
FROM debian:13-slim

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    # Python and development tools
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    python3-requests \
    python3-lxml \
    python3-pil \
    python3-setuptools \
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

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip3 install --no-cache-dir --upgrade pip && \
    pip3 install --no-cache-dir -r requirements.txt

# Copy application files
COPY app.py .
COPY box_generator.py .
COPY download_manager.py .
COPY var/config/config.json ./var/config/
COPY static/ ./static/
COPY templates/ ./templates/

# Create necessary directories
RUN mkdir -p /app/roms /app/media /app/cache /app/var/task_logs /app/var/db /app/var/sessions /app/venv && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/ || exit 1

# Set default command
CMD ["python3", "app.py"]

# Labels for metadata
LABEL maintainer="Batocera Game Collection Manager"
LABEL description="Flask-based web application for managing ROM collections"
LABEL version="1.0.0"
