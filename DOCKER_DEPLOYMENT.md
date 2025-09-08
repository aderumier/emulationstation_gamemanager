# GameManager Docker Deployment Guide

This guide explains how to deploy GameManager using Docker from DockerHub on both Linux and Windows systems.

## Prerequisites

### Linux
- Docker Engine installed
- Docker Compose (optional, for easier management)

### Windows
- Docker Desktop installed and running
- WSL2 enabled (recommended for better performance)

## Quick Start

### Pull the Image
```bash
docker pull aderumier/cursorscraper:latest
```

### Run the Container
```bash
docker run -d \
  --name gamemanager \
  -p 5000:5000 \
  -v $(pwd)/roms:/opt/gamemanager/roms \
  -v $(pwd)/var:/opt/gamemanager/var \
  -e IGDB_CLIENT_ID=your_igdb_client_id \
  -e IGDB_CLIENT_SECRET=your_igdb_client_secret \
  aderumier/cursorscraper:latest
```

**Note**: Replace `your_igdb_client_id` and `your_igdb_client_secret` with your actual IGDB API credentials. See [IGDB_SETUP.md](IGDB_SETUP.md) for detailed setup instructions.

## Detailed Deployment Instructions

### Linux Deployment

#### 1. Install Docker (if not already installed)
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install docker.io docker-compose
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker $USER

# Log out and back in for group changes to take effect
```

#### 2. Create Directory Structure
```bash
mkdir -p gamemanager-data/{roms,var}
cd gamemanager-data
```

#### 3. Run with Docker Run
```bash
docker run -d \
  --name gamemanager \
  --restart unless-stopped \
  -p 5000:5000 \
  -v $(pwd)/roms:/opt/gamemanager/roms \
  -v $(pwd)/var:/opt/gamemanager/var \
  -e FLASK_ENV=production \
  -e IGDB_CLIENT_ID=your_igdb_client_id \
  -e IGDB_CLIENT_SECRET=your_igdb_client_secret \
  aderumier/cursorscraper:latest
```

#### 4. Run with Docker Compose (Recommended)
Create `docker-compose.yml`:
```yaml
version: '3.8'

services:
  gamemanager:
    image: aderumier/cursorscraper:latest
    container_name: gamemanager
    ports:
      - "5000:5000"
    volumes:
      # Mount application data directories
      - ./roms:/opt/gamemanager/roms
      - ./var:/opt/gamemanager/var
    environment:
      - FLASK_ENV=production
      - PYTHONUNBUFFERED=1
      - FLASK_APP=app.py
      - IGDB_CLIENT_ID=your_igdb_client_id
      - IGDB_CLIENT_SECRET=your_igdb_client_secret
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    # Resource limits (optional)
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '1.0'
        reservations:
          memory: 512M
          cpus: '0.5'
    # Security options
    security_opt:
      - no-new-privileges:true
    # User mapping (optional)
    user: "1000:1000"
```

Then run:
```bash
docker-compose up -d
```

### Windows Deployment

#### 1. Install Docker Desktop
1. Download Docker Desktop from [docker.com](https://www.docker.com/products/docker-desktop/)
2. Install and start Docker Desktop
3. Enable WSL2 integration (recommended)

#### 2. Using Command Prompt/PowerShell

Create directory structure:
```cmd
mkdir gamemanager-data
cd gamemanager-data
mkdir roms
mkdir var
```

Run the container:
```cmd
docker run -d ^
  --name gamemanager ^
  --restart unless-stopped ^
  -p 5000:5000 ^
  -v "%cd%\roms:/opt/gamemanager/roms" ^
  -v "%cd%\var:/opt/gamemanager/var" ^
  -e FLASK_ENV=production ^
  -e IGDB_CLIENT_ID=your_igdb_client_id ^
  -e IGDB_CLIENT_SECRET=your_igdb_client_secret ^
  aderumier/cursorscraper:latest
```

#### 3. Using PowerShell

```powershell
# Create directory structure
New-Item -ItemType Directory -Path "gamemanager-data" -Force
Set-Location "gamemanager-data"
New-Item -ItemType Directory -Path "roms", "var" -Force

# Run the container
docker run -d `
  --name gamemanager `
  --restart unless-stopped `
  -p 5000:5000 `
  -v "${PWD}\roms:/opt/gamemanager/roms" `
  -v "${PWD}\var:/opt/gamemanager/var" `
  -e FLASK_ENV=production `
  -e IGDB_CLIENT_ID=your_igdb_client_id `
  -e IGDB_CLIENT_SECRET=your_igdb_client_secret `
  aderumier/cursorscraper:latest
```

#### 4. Using Docker Compose on Windows

Create `docker-compose.yml` (same as Linux version):
```yaml
version: '3.8'

services:
  gamemanager:
    image: aderumier/cursorscraper:latest
    container_name: gamemanager
    ports:
      - "5000:5000"
    volumes:
      - ./roms:/opt/gamemanager/roms
      - ./var:/opt/gamemanager/var
    environment:
      - FLASK_ENV=production
      - PYTHONUNBUFFERED=1
      - FLASK_APP=app.py
      - IGDB_CLIENT_ID=your_igdb_client_id
      - IGDB_CLIENT_SECRET=your_igdb_client_secret
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

Then run:
```cmd
docker-compose up -d
```

## Configuration

### Initial Setup
1. Access the web interface at `http://localhost:5000`
2. Default login credentials:
   - Username: `admin`
   - Password: `admin123`
3. Change the default password immediately after first login

### Directory Structure
```
gamemanager-data/
├── roms/                    # Game ROMs organized by system
│   ├── nes/
│   ├── snes/
│   ├── gba/
│   └── ...
└── var/                     # Application data (persistent volume)
    ├── config/              # Configuration files
    │   ├── config.json
    │   └── user.cfg
    ├── db/                  # Database files
    │   ├── launchbox/
    │   │   └── Metadata.xml
    │   └── igdb/            # IGDB cache
    ├── sessions/            # User sessions
    ├── gamelists/           # Game list files
    └── task_logs/           # Task execution logs
```

## Management Commands

### View Logs
```bash
# Linux
docker logs gamemanager

# Windows
docker logs gamemanager
```

### Stop the Container
```bash
# Linux
docker stop gamemanager

# Windows
docker stop gamemanager
```

### Start the Container
```bash
# Linux
docker start gamemanager

# Windows
docker start gamemanager
```

### Remove the Container
```bash
# Linux
docker stop gamemanager
docker rm gamemanager

# Windows
docker stop gamemanager
docker rm gamemanager
```

### Update to Latest Version
```bash
# Pull latest image
docker pull aderumier/cursorscraper:latest

# Stop and remove old container
docker stop gamemanager
docker rm gamemanager

# Run new container (same command as initial setup)
docker run -d --name gamemanager --restart unless-stopped -p 5000:5000 -v $(pwd)/roms:/opt/gamemanager/roms -v $(pwd)/var:/opt/gamemanager/var -e FLASK_ENV=production -e IGDB_CLIENT_ID=your_igdb_client_id -e IGDB_CLIENT_SECRET=your_igdb_client_secret aderumier/cursorscraper:latest
```

## Troubleshooting

### Container Won't Start
1. Check if port 5000 is already in use:
   ```bash
   # Linux
   sudo netstat -tlnp | grep :5000
   
   # Windows
   netstat -an | findstr :5000
   ```

2. Use a different port:
   ```bash
   docker run -d --name gamemanager -p 5001:5000 aderumier/emulationstation_gamemanager:latest
   ```

### Permission Issues (Linux)
```bash
# Fix ownership of mounted directories
sudo chown -R 1000:1000 gamemanager-data/
```

### Windows WSL2 Issues
1. Ensure WSL2 is enabled in Docker Desktop settings
2. Update WSL2: `wsl --update`
3. Restart Docker Desktop

### Access Issues
1. Check if the container is running: `docker ps`
2. Check container logs: `docker logs gamemanager`
3. Verify firewall settings allow port 5000

## Security Considerations

1. **Change default credentials** immediately after first login
2. **Use HTTPS** in production (consider using a reverse proxy like nginx)
3. **Restrict network access** if running on a public server
4. **Regular updates** - pull the latest image periodically
5. **Backup data** - regularly backup your `var/` directory (contains all application data)

## Performance Optimization

### Resource Limits
Add resource limits to prevent the container from consuming too many resources:
```bash
docker run -d \
  --name gamemanager \
  --memory="2g" \
  --cpus="1.0" \
  -p 5000:5000 \
  aderumier/emulationstation_gamemanager:latest
```

### SSD Storage
For better performance, store the data directories on SSD storage.

## Support

For issues and support:
- Check the container logs: `docker logs gamemanager`
- Verify your directory structure matches the expected layout
- Ensure all required directories have proper permissions
- Check that Docker has sufficient resources allocated

## Version Information

- **Current Version**: 1.8-1
- **Docker Image**: `aderumier/cursorscraper:latest`
- **Base Image**: Debian 13-slim
- **Application**: GameManager Game Collection Management System

## IGDB Integration

To enable IGDB scraping features, you need to provide your IGDB API credentials. See [IGDB_SETUP.md](IGDB_SETUP.md) for detailed setup instructions.

**Required Environment Variables:**
- `IGDB_CLIENT_ID`: Your IGDB/Twitch Client ID
- `IGDB_CLIENT_SECRET`: Your IGDB/Twitch Client Secret

**Alternative Configuration:**
- Configure via web interface after container starts
- Use `.env` file for local development
- Use `var/config/credentials.json` for persistent storage