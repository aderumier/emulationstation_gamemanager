# GameManager Docker Deployment Guide

This guide provides comprehensive instructions for deploying GameManager using Docker on both Linux and Windows systems.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Linux Deployment](#linux-deployment)
3. [Windows Deployment with Docker Desktop](#windows-deployment-with-docker-desktop)
4. [Configuration](#configuration)
5. [Data Persistence](#data-persistence)
6. [Troubleshooting](#troubleshooting)
7. [Advanced Configuration](#advanced-configuration)

## Prerequisites

### Linux
- Docker Engine 20.10+ or Docker Desktop for Linux
- Docker Compose 2.0+
- At least 2GB RAM and 10GB free disk space

### Windows
- Windows 10/11 with WSL2 enabled
- Docker Desktop for Windows 4.0+
- At least 4GB RAM and 15GB free disk space

## Linux Deployment

### Method 1: Using Docker Compose (Recommended)

1. **Clone or download the GameManager repository:**
   ```bash
   git clone <repository-url>
   cd cursorscraper
   ```

2. **Create necessary directories:**
   ```bash
   mkdir -p var/config var/db/launchbox var/sessions var/gamelists var/task_logs
   ```

3. **Copy configuration files:**
   ```bash
   cp var/config/config.json.example var/config/config.json
   # Edit config.json with your settings
   nano var/config/config.json
   ```

4. **Start the application:**
   ```bash
   docker-compose up -d
   ```

5. **Check the logs:**
   ```bash
   docker-compose logs -f gamemanager
   ```

6. **Access the application:**
   Open your browser and navigate to `http://localhost:5000`

### Method 2: Using Docker Run

1. **Pull the image:**
   ```bash
   docker pull yourusername/gamemanager:latest
   ```

2. **Create directories:**
   ```bash
   mkdir -p ~/gamemanager/{roms,media,cache,var/{config,db/launchbox,sessions,gamelists,task_logs}}
   ```

3. **Run the container:**
   ```bash
   docker run -d \
     --name gamemanager \
     -p 5000:5000 \
     -v ~/gamemanager/roms:/app/roms \
     -v ~/gamemanager/media:/app/media \
     -v ~/gamemanager/cache:/app/cache \
     -v ~/gamemanager/var/config:/app/var/config \
     -v ~/gamemanager/var/db:/app/var/db \
     -v ~/gamemanager/var/sessions:/app/var/sessions \
     -v ~/gamemanager/var/gamelists:/app/var/gamelists \
     -v ~/gamemanager/var/task_logs:/app/var/task_logs \
     --restart unless-stopped \
     yourusername/gamemanager:latest
   ```

### Method 3: Building from Source

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd cursorscraper
   ```

2. **Build the image:**
   ```bash
   docker build -t gamemanager:latest .
   ```

3. **Run using docker-compose:**
   ```bash
   docker-compose up -d
   ```

## Windows Deployment with Docker Desktop

### Prerequisites Setup

1. **Install Docker Desktop:**
   - Download from [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop/)
   - Enable WSL2 integration during installation
   - Start Docker Desktop

2. **Enable WSL2 (if not already enabled):**
   ```powershell
   # Run as Administrator
   dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
   dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart
   ```

### Method 1: Using Docker Desktop GUI

1. **Open Docker Desktop**

2. **Create a new project:**
   - Click "Create" or "New Project"
   - Choose "From Git Repository" or "From Local Directory"

3. **If using Git:**
   - Enter repository URL
   - Choose a local directory for the project

4. **If using local directory:**
   - Navigate to your GameManager folder
   - Select the folder containing `docker-compose.yml`

5. **Configure volumes:**
   - In the Docker Desktop interface, go to "Volumes"
   - Create the following volume mappings:
     ```
     ./roms -> /app/roms
     ./media -> /app/media
     ./cache -> /app/cache
     ./var/config -> /app/var/config
     ./var/db -> /app/var/db
     ./var/sessions -> /app/var/sessions
     ./var/gamelists -> /app/var/gamelists
     ./var/task_logs -> /app/var/task_logs
     ```

6. **Start the application:**
   - Click "Start" in Docker Desktop
   - Wait for the container to start

7. **Access the application:**
   - Open browser to `http://localhost:5000`

### Method 2: Using Command Line (WSL2 or PowerShell)

1. **Open WSL2 or PowerShell as Administrator**

2. **Navigate to your project directory:**
   ```bash
   cd /path/to/gamemanager
   ```

3. **Create necessary directories:**
   ```bash
   mkdir -p var/config var/db/launchbox var/sessions var/gamelists var/task_logs
   ```

4. **Start with Docker Compose:**
   ```bash
   docker-compose up -d
   ```

5. **Check status:**
   ```bash
   docker-compose ps
   docker-compose logs -f gamemanager
   ```

### Method 3: Using Docker Run (Windows)

1. **Open PowerShell as Administrator**

2. **Pull the image:**
   ```powershell
   docker pull yourusername/gamemanager:latest
   ```

3. **Create directories:**
   ```powershell
   New-Item -ItemType Directory -Path "C:\gamemanager\roms" -Force
   New-Item -ItemType Directory -Path "C:\gamemanager\media" -Force
   New-Item -ItemType Directory -Path "C:\gamemanager\cache" -Force
   New-Item -ItemType Directory -Path "C:\gamemanager\var\config" -Force
   New-Item -ItemType Directory -Path "C:\gamemanager\var\db\launchbox" -Force
   New-Item -ItemType Directory -Path "C:\gamemanager\var\sessions" -Force
   New-Item -ItemType Directory -Path "C:\gamemanager\var\gamelists" -Force
   New-Item -ItemType Directory -Path "C:\gamemanager\var\task_logs" -Force
   ```

4. **Run the container:**
   ```powershell
   docker run -d `
     --name gamemanager `
     -p 5000:5000 `
     -v C:\gamemanager\roms:/app/roms `
     -v C:\gamemanager\media:/app/media `
     -v C:\gamemanager\cache:/app/cache `
     -v C:\gamemanager\var\config:/app/var\config `
     -v C:\gamemanager\var\db:/app/var\db `
     -v C:\gamemanager\var\sessions:/app/var\sessions `
     -v C:\gamemanager\var\gamelists:/app/var\gamelists `
     -v C:\gamemanager\var\task_logs:/app/var\task_logs `
     --restart unless-stopped `
     yourusername/gamemanager:latest
   ```

## Configuration

### Environment Variables

You can customize the application using environment variables in your `docker-compose.yml`:

```yaml
environment:
  - FLASK_ENV=production
  - PYTHONUNBUFFERED=1
  - FLASK_APP=app.py
  # Add custom environment variables here
```

### Configuration File

The main configuration is in `var/config/config.json`. Key settings include:

```json
{
  "roms_root_directory": "/app/roms",
  "media_root_directory": "/app/media",
  "cache_directory": "/app/cache",
  "max_concurrent_tasks": 3,
  "task_timeout": 3600
}
```

## Data Persistence

### Important Directories

The following directories are mounted as volumes for data persistence:

- **`/app/roms`** - Your ROM files and gamelist.xml files
- **`/app/media`** - Downloaded media files (images, videos)
- **`/app/cache`** - Application cache
- **`/app/var/config`** - Configuration files
- **`/app/var/db`** - Database files (including LaunchBox metadata)
- **`/app/var/sessions`** - User session data
- **`/app/var/gamelists`** - Working gamelist files
- **`/app/var/task_logs`** - Task execution logs

### Backup Recommendations

1. **Regular backups:**
   ```bash
   # Linux
   tar -czf gamemanager-backup-$(date +%Y%m%d).tar.gz var/ roms/ media/
   
   # Windows (PowerShell)
   Compress-Archive -Path "var,roms,media" -DestinationPath "gamemanager-backup-$(Get-Date -Format 'yyyyMMdd').zip"
   ```

2. **Database backup:**
   ```bash
   cp var/db/launchbox/Metadata.xml var/db/launchbox/Metadata.xml.backup
   ```

## Troubleshooting

### Common Issues

1. **Container won't start:**
   ```bash
   docker-compose logs gamemanager
   ```

2. **Permission issues:**
   ```bash
   # Linux
   sudo chown -R 1000:1000 var/ roms/ media/ cache/
   
   # Windows - Run Docker Desktop as Administrator
   ```

3. **Port already in use:**
   ```bash
   # Change port in docker-compose.yml
   ports:
     - "5001:5000"  # Use port 5001 instead
   ```

4. **Out of disk space:**
   ```bash
   docker system prune -a  # Clean up unused images
   ```

### Health Checks

The container includes health checks. Monitor with:

```bash
docker-compose ps
docker inspect gamemanager_gamemanager_1 | grep -A 10 "Health"
```

### Logs

View application logs:

```bash
# All logs
docker-compose logs gamemanager

# Follow logs in real-time
docker-compose logs -f gamemanager

# Last 100 lines
docker-compose logs --tail=100 gamemanager
```

## Advanced Configuration

### Resource Limits

Adjust resource limits in `docker-compose.yml`:

```yaml
deploy:
  resources:
    limits:
      memory: 4G      # Increase for large collections
      cpus: '2.0'     # Increase for faster processing
    reservations:
      memory: 1G
      cpus: '1.0'
```

### Reverse Proxy with Nginx

For production deployments, add nginx service to `docker-compose.yml`:

```yaml
services:
  nginx:
    image: nginx:alpine
    container_name: gamemanager-nginx
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - gamemanager
    restart: unless-stopped
```

### SSL/HTTPS Setup

1. **Obtain SSL certificates** (Let's Encrypt recommended)
2. **Configure nginx** with SSL
3. **Update docker-compose.yml** to mount certificates

### Multi-Platform Support

The Docker image supports multiple architectures:

```bash
# Build for multiple platforms
docker buildx build --platform linux/amd64,linux/arm64 -t yourusername/gamemanager:latest .
```

## Security Considerations

1. **Run as non-root user** (already configured)
2. **Use secrets for sensitive data**
3. **Enable firewall rules**
4. **Regular security updates**
5. **Backup encryption**

## Support

For issues and support:

1. Check the logs first
2. Review this documentation
3. Check GitHub issues
4. Create a new issue with:
   - Docker version
   - Operating system
   - Error logs
   - Configuration details

---

**Note:** Replace `yourusername` with your actual DockerHub username when pulling/pushing images.
