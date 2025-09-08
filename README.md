# GameManager - Game Collection Management System

A Flask-based web application for managing ROM collections, scanning media files, and scraping metadata from Launchbox.

## License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.

Copyright (C) 2024 Alexandre Derumier <aderumier@gmail.com>

## Features

- **ROM Management**: Scan and organize ROM files by system
- **Media Scanning**: Automatically detect and link media files (screenshots, box art, etc.)
- **Launchbox Integration**: Scrape metadata from Launchbox XML files
- **IGDB Integration**: Fetch game metadata, artwork, and videos from IGDB database
- **Multi-platform Support**: Works with various ROM systems (MAME, NES, GBA, etc.)
- **Real-time Progress**: Live progress updates during scraping operations
- **Real-time Multi-user Support**: WebSocket-based real-time updates for collaborative editing
- **Responsive UI**: Modern web interface with AG Grid for data management

## Real-time Multi-user Support

The application now supports real-time collaboration through WebSocket technology. When multiple users are connected:

- **Automatic Updates**: Game grid automatically refreshes when any user saves changes
- **Real-time Notifications**: Toast messages inform users of updates happening in real-time
- **System Rooms**: Users join system-specific rooms to receive targeted updates
- **Data Consistency**: All connected users see the same data simultaneously
- **Collaborative Editing**: Multiple users can edit the same system without conflicts

### WebSocket Events

- `gamelist_updated`: Fired when gamelist.xml is saved
- `games_deleted`: Fired when games are removed
- `game_updated`: Fired when individual games are modified
- `system_updated`: General system update notifications

### Testing WebSocket Functionality

Use the included `test_websocket.html` file to test real-time updates:

1. Open the test file in multiple browser tabs
2. Join different system rooms
3. Make changes in the main application
4. Watch real-time updates across all connected clients

## Git Version Control Setup

This project now uses Git for version control. Here's how to work with it:

### Initial Setup (Already Done)
```bash
git init                    # Initialize Git repository
git add .                   # Add all files (excluding .gitignore items)
git commit -m "Initial commit"  # Make first commit
git checkout -b development # Create and switch to development branch
```

### Daily Workflow

#### 1. Starting Work
```bash
git status                  # Check current status
git checkout development    # Switch to development branch
git pull origin development # Pull latest changes (if working with others)
```

#### 2. Making Changes
```bash
# Edit your files...
git add <filename>          # Stage specific files
git add .                   # Stage all changes
git status                  # Review what's staged
git commit -m "Description of changes"
```

#### 3. Before Pushing
```bash
git log --oneline          # Review recent commits
git diff HEAD~1            # See changes in last commit
git push origin development # Push to remote (if configured)
```

### Branch Strategy

- **`master`**: Stable, working code
- **`development`**: Active development work
- **Feature branches**: Create for specific features: `git checkout -b feature/new-feature`

### Useful Git Commands

```bash
# View history
git log --oneline          # Compact commit history
git log --graph --oneline  # Visual branch history

# Undo changes
git checkout -- <file>     # Discard file changes
git reset HEAD~1           # Undo last commit (keep changes)
git revert HEAD            # Create new commit that undoes last commit

# Stash work in progress
git stash                  # Save current work
git stash pop              # Restore stashed work

# View differences
git diff                   # See unstaged changes
git diff --staged          # See staged changes
git diff HEAD~1            # See changes in last commit
```

### File Management

#### Tracked Files (in Git)
- Source code (`app.py`, `static/`, `templates/`)
- Configuration files (`*.json`)
- Documentation (`README.md`)
- Dependencies (`requirements.txt`)

#### Ignored Files (not in Git)
- Python cache (`__pycache__/`)
- Large data files (`var/db/launchbox/Metadata.xml`, `roms/`)
- Environment files (`.env`)
- IDE files (`.vscode/`, `.idea/`)
- Temporary files (`*.bak`, `*.tmp`)

### Adding Large Files (Optional)

If you want to track large files like `var/db/launchbox/Metadata.xml`:

```bash
# Add to .gitignore first, then force add
echo "!var/db/launchbox/Metadata.xml" >> .gitignore
git add -f var/db/launchbox/Metadata.xml
git commit -m "Add Metadata.xml for scraping"
```

**Note**: Large files can make the repository slow. Consider using Git LFS for files >100MB.

## Project Structure

```
cursorscraper/
├── app.py                      # Main Flask application
├── run.py                      # Application entry point
├── requirements.txt            # Python dependencies
├── static/                     # CSS, JavaScript, images
│   ├── css/style.css
│   └── js/app.js
├── templates/                  # HTML templates
│   └── index.html
├── roms/                       # ROM files (not in Git)
├── launchbox_mapping.json      # Field mapping configuration
├── media_config.json           # Media scanning configuration
├── system_platform_mapping.json # System-to-platform mapping
└── .gitignore                  # Git ignore rules
```

## Installation & Setup

### Docker Deployment (Recommended)

For easy deployment, use the pre-built Docker image:

```bash
# Pull the latest image
docker pull aderumier/emulationstation_gamemanager:latest

# Run the container with IGDB credentials
docker run -d \
  --name gamemanager \
  -p 5000:5000 \
  -v $(pwd)/roms:/opt/gamemanager/roms \
  -v $(pwd)/var:/opt/gamemanager/var \
  -e IGDB_CLIENT_ID=your_igdb_client_id \
  -e IGDB_CLIENT_SECRET=your_igdb_client_secret \
  aderumier/emulationstation_gamemanager:latest
```

#### IGDB Integration Setup

To enable IGDB scraping features, you need to provide your IGDB API credentials:

1. **Get IGDB Credentials**: Visit [Twitch Developer Console](https://dev.twitch.tv/console/apps) to create an app and get your Client ID and Client Secret
2. **Set Environment Variables**: Use the `-e` flags in your Docker run command
3. **Alternative**: Configure via web interface after container starts

**Environment Variables:**
- `IGDB_CLIENT_ID`: Your IGDB/Twitch Client ID
- `IGDB_CLIENT_SECRET`: Your IGDB/Twitch Client Secret

**📖 For detailed IGDB API setup instructions, see [IGDB_SETUP.md](IGDB_SETUP.md)**

**📖 For detailed Docker deployment instructions on Linux and Windows, see [DOCKER_DEPLOYMENT.md](DOCKER_DEPLOYMENT.md)**

### Debian/Ubuntu Installation

#### 1. System Requirements
- **Debian 11+** or **Ubuntu 20.04+**
- **Python 3.8+** (included in Debian 11+)
- **Git** (for version control)

#### 2. Install System Dependencies

```bash
# Update package lists
sudo apt update

# Install Python and development tools
sudo apt install -y python3 python3-pip python3-venv python3-dev

# Install system packages used by the application
sudo apt install -y \
    imagemagick \
    ffmpeg \
    yt-dlp \
    git \
    curl \
    wget

# Install Flask and related packages from Debian repositories
sudo apt install -y \
    python3-flask \
    python3-flask-cors \
    python3-flask-socketio \
    python3-flask-login \
    python3-flask-session \
    python3-requests \
    python3-httpx \
    python3-aiofiles \
    python3-lxml \
    python3-pil \
    python3-setuptools
```

#### 3. Clone and Setup Project

```bash
# Clone the repository
git clone <repository-url>
cd cursorscraper

# Create necessary directories
mkdir -p roms media cache var/task_logs var/db var/sessions var/config

# Copy configuration template (if needed)
# The application will create default config files on first run
```

**Note**: Since we're using Debian system packages, you don't need a virtual environment or pip installation. The system packages provide all required dependencies.

**Benefits of using Debian packages:**
- **System Integration**: Packages are managed by apt and integrate with system updates
- **Security**: Debian packages receive security updates through the system
- **Stability**: Tested versions that work well together
- **No Virtual Environment**: Simpler setup and management
- **System-wide Installation**: Available to all users on the system

#### 4. Verify Installation

```bash
# Check ImageMagick
convert -version

# Check FFmpeg
ffmpeg -version

# Check yt-dlp
yt-dlp --version

# Check Python packages
python3 -c "import flask, requests, httpx; print('All packages installed successfully')"
```

#### 5. Run the Application

```bash
# Run the application directly (no virtual environment needed)
python3 app.py
```

#### 6. Access the Web Interface
Open your browser to `http://localhost:5000`

### Manual Installation (Other Systems)

1. **Clone the repository** (if working with others):
   ```bash
   git clone <repository-url>
   cd cursorscraper
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Install required system software**:
   - **ImageMagick**: For 2D box generation
   - **FFmpeg**: For video processing and thumbnail extraction
   - **yt-dlp**: For video downloads

4. **Run the application**:
   ```bash
   python3 app.py
   ```

5. **Access the web interface**:
   Open your browser to `http://localhost:5000`

#### 6. Create Systemd Service (Production)

##### Create Service User
```bash
# Create a dedicated user for the application
sudo useradd --system --shell /bin/false --home-dir /opt/cursorscraper cursorscraper

# Create application directory
sudo mkdir -p /opt/cursorscraper
sudo chown cursorscraper:cursorscraper /opt/cursorscraper
```

##### Install Application
```bash
# Copy application to system directory
sudo cp -r /path/to/cursorscraper/* /opt/cursorscraper/

# Set ownership
sudo chown -R cursorscraper:cursorscraper /opt/cursorscraper

# Make app.py executable
sudo chmod +x /opt/cursorscraper/app.py
```

##### Create Systemd Service File
Create `/etc/systemd/system/cursorscraper.service`:
```ini
[Unit]
Description=Batocera Game Collection Manager
After=network.target
Wants=network.target

[Service]
Type=simple
User=cursorscraper
Group=cursorscraper
WorkingDirectory=/opt/cursorscraper
ExecStart=/usr/bin/python3 /opt/cursorscraper/app.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=cursorscraper

# Environment variables
Environment=PYTHONUNBUFFERED=1
Environment=FLASK_ENV=production

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/cursorscraper
ReadWritePaths=/home/cursorscraper

# Resource limits
LimitNOFILE=65536
MemoryMax=2G
CPUQuota=100%

[Install]
WantedBy=multi-user.target
```

##### Enable and Start Service
```bash
# Reload systemd configuration
sudo systemctl daemon-reload

# Enable service to start on boot
sudo systemctl enable cursorscraper

# Start the service
sudo systemctl start cursorscraper

# Check service status
sudo systemctl status cursorscraper

# View logs
sudo journalctl -u cursorscraper -f
```

##### Service Management Commands
```bash
# Start service
sudo systemctl start cursorscraper

# Stop service
sudo systemctl stop cursorscraper

# Restart service
sudo systemctl restart cursorscraper

# Check status
sudo systemctl status cursorscraper

# View logs
sudo journalctl -u cursorscraper

# View recent logs
sudo journalctl -u cursorscraper --since "1 hour ago"

# Follow logs in real-time
sudo journalctl -u cursorscraper -f
```

##### Update Application
```bash
# Stop service
sudo systemctl stop cursorscraper

# Update application files
sudo cp -r /path/to/updated/cursorscraper/* /opt/cursorscraper/
sudo chown -R cursorscraper:cursorscraper /opt/cursorscraper

# Start service
sudo systemctl start cursorscraper
```

##### Configure Firewall (Optional)
```bash
# Allow HTTP traffic
sudo ufw allow 5000/tcp

# Or if using reverse proxy
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
```

### Docker Installation (Recommended)

#### 1. Prerequisites
- **Docker** 20.10+ and **Docker Compose** 2.0+
- **Git** (for cloning the repository)

#### 2. Install Docker (Debian/Ubuntu)
```bash
# Update package lists
sudo apt update

# Install Docker
sudo apt install -y docker.io docker-compose-plugin

# Add user to docker group (logout/login required)
sudo usermod -aG docker $USER

# Verify installation
docker --version
docker compose version
```

#### 3. Clone and Run with Docker
```bash
# Clone the repository
git clone <repository-url>
cd cursorscraper

# Create necessary directories
mkdir -p roms media cache var/task_logs

# Build and run with Docker Compose
docker compose up -d

# Check container status
docker compose ps

# View logs
docker compose logs -f
```

#### 4. Access the Application
Open your browser to `http://localhost:5000`

#### 5. Docker Management Commands
```bash
# Stop the application
docker compose down

# Restart the application
docker compose restart

# Update the application
docker compose pull
docker compose up -d

# View container logs
docker compose logs -f cursorscraper

# Execute commands in container
docker compose exec cursorscraper bash

# Remove everything (including volumes)
docker compose down -v
```

#### 6. Docker Volume Mounts
The following directories are mounted as volumes for persistent data:
- `./roms` → `/app/roms` (ROM files)
- `./cache` → `/app/cache` (Application cache)
- `./var/task_logs` → `/app/var/task_logs` (Task logs)
- `./var/config/config.json` → `/app/var/config/config.json` (Configuration)

### Reverse Proxy Setup (Production)

#### Nginx Reverse Proxy

##### 1. Install Nginx
```bash
# Install Nginx
sudo apt update
sudo apt install -y nginx

# Start and enable Nginx
sudo systemctl start nginx
sudo systemctl enable nginx
```

##### 2. Configure Nginx
Create `/etc/nginx/sites-available/cursorscraper`:
```nginx
server {
    listen 80;
    server_name your-domain.com www.your-domain.com;
    
    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com www.your-domain.com;
    
    # SSL Configuration (replace with your certificates)
    ssl_certificate /etc/ssl/certs/your-domain.crt;
    ssl_certificate_key /etc/ssl/private/your-domain.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    
    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    
    # Client max body size for file uploads
    client_max_body_size 100M;
    
    # Proxy settings
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    # Static files caching
    location /static/ {
        proxy_pass http://127.0.0.1:5000;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    # Media files (ROMs, images, etc.)
    location /roms/ {
        proxy_pass http://127.0.0.1:5000;
        expires 1M;
        add_header Cache-Control "public";
    }
    
    location /media/ {
        proxy_pass http://127.0.0.1:5000;
        expires 1M;
        add_header Cache-Control "public";
    }
}
```

##### 3. Enable Site and Test
```bash
# Enable the site
sudo ln -s /etc/nginx/sites-available/cursorscraper /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Reload Nginx
sudo systemctl reload nginx
```

#### Apache Reverse Proxy

##### 1. Install Apache
```bash
# Install Apache and required modules
sudo apt update
sudo apt install -y apache2

# Enable required modules
sudo a2enmod proxy
sudo a2enmod proxy_http
sudo a2enmod proxy_wstunnel
sudo a2enmod rewrite
sudo a2enmod ssl
sudo a2enmod headers

# Start and enable Apache
sudo systemctl start apache2
sudo systemctl enable apache2
```

##### 2. Configure Apache
Create `/etc/apache2/sites-available/cursorscraper.conf`:
```apache
<VirtualHost *:80>
    ServerName your-domain.com
    ServerAlias www.your-domain.com
    
    # Redirect HTTP to HTTPS
    RewriteEngine On
    RewriteCond %{HTTPS} off
    RewriteRule ^(.*)$ https://%{HTTP_HOST}%{REQUEST_URI} [L,R=301]
</VirtualHost>

<VirtualHost *:443>
    ServerName your-domain.com
    ServerAlias www.your-domain.com
    
    # SSL Configuration
    SSLEngine on
    SSLCertificateFile /etc/ssl/certs/your-domain.crt
    SSLCertificateKeyFile /etc/ssl/private/your-domain.key
    SSLProtocol all -SSLv3 -TLSv1 -TLSv1.1
    SSLCipherSuite ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384
    
    # Security headers
    Header always set X-Frame-Options DENY
    Header always set X-Content-Type-Options nosniff
    Header always set X-XSS-Protection "1; mode=block"
    Header always set Strict-Transport-Security "max-age=31536000; includeSubDomains"
    
    # Client max body size
    LimitRequestBody 104857600  # 100MB
    
    # Proxy settings
    ProxyPreserveHost On
    ProxyRequests Off
    
    # Main application
    ProxyPass / http://127.0.0.1:5000/
    ProxyPassReverse / http://127.0.0.1:5000/
    
    # WebSocket support
    RewriteEngine On
    RewriteCond %{HTTP:Upgrade} websocket [NC]
    RewriteCond %{HTTP:Connection} upgrade [NC]
    RewriteRule ^/?(.*) "ws://127.0.0.1:5000/$1" [P,L]
    
    # Static files caching
    <LocationMatch "^/static/">
        ExpiresActive On
        ExpiresDefault "access plus 1 year"
        Header set Cache-Control "public, immutable"
    </LocationMatch>
    
    # Media files caching
    <LocationMatch "^/(roms|media)/">
        ExpiresActive On
        ExpiresDefault "access plus 1 month"
        Header set Cache-Control "public"
    </LocationMatch>
</VirtualHost>
```

##### 3. Enable Site and Test
```bash
# Enable the site
sudo a2ensite cursorscraper.conf

# Test configuration
sudo apache2ctl configtest

# Reload Apache
sudo systemctl reload apache2
```

#### SSL Certificate Setup (Let's Encrypt)

##### 1. Install Certbot
```bash
# Install Certbot
sudo apt install -y certbot python3-certbot-nginx  # For Nginx
# OR
sudo apt install -y certbot python3-certbot-apache  # For Apache
```

##### 2. Obtain SSL Certificate
```bash
# For Nginx
sudo certbot --nginx -d your-domain.com -d www.your-domain.com

# For Apache
sudo certbot --apache -d your-domain.com -d www.your-domain.com
```

##### 3. Auto-renewal
```bash
# Test auto-renewal
sudo certbot renew --dry-run

# Certbot automatically sets up cron job for renewal
```

#### Application Configuration for Reverse Proxy

##### 1. Update var/config/config.json
```json
{
    "server": {
        "host": "127.0.0.1",
        "port": 5000,
        "debug": false
    }
}
```

##### 2. Update Docker Compose (if using Docker)
```yaml
version: '3.8'
services:
  cursorscraper:
    image: aderumier/emulationstation_gamemanager:latest
    container_name: cursorscraper
    ports:
      - "127.0.0.1:5000:5000"  # Bind to localhost only
    volumes:
      - ./roms:/opt/gamemanager/roms
      - ./var:/opt/gamemanager/var
    environment:
      - FLASK_ENV=production
      - IGDB_CLIENT_ID=your_igdb_client_id
      - IGDB_CLIENT_SECRET=your_igdb_client_secret
    restart: unless-stopped
```

#### Firewall Configuration

##### 1. Configure UFW (Ubuntu Firewall)
```bash
# Enable UFW
sudo ufw enable

# Allow SSH
sudo ufw allow ssh

# Allow HTTP and HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Deny direct access to application port
sudo ufw deny 5000/tcp

# Check status
sudo ufw status
```

##### 2. Configure iptables (Alternative)
```bash
# Allow HTTP and HTTPS
sudo iptables -A INPUT -p tcp --dport 80 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 443 -j ACCEPT

# Block direct access to application
sudo iptables -A INPUT -p tcp --dport 5000 -j DROP

# Save rules
sudo iptables-save > /etc/iptables/rules.v4
```

## Configuration

- **`launchbox_mapping.json`**: Maps Launchbox XML fields to game fields
- **`media_config.json`**: Configures media file scanning
- **`system_platform_mapping.json`**: Maps system names to Launchbox platforms

## Development Workflow

1. **Make changes** in the `development` branch
2. **Test thoroughly** before committing
3. **Commit frequently** with descriptive messages
4. **Push to remote** when ready to share
5. **Merge to master** when features are stable

## Troubleshooting

### Docker Installation Issues

#### Docker Not Found
```bash
# Install Docker on Debian/Ubuntu
sudo apt update
sudo apt install -y docker.io docker-compose-plugin

# Start Docker service
sudo systemctl start docker
sudo systemctl enable docker

# Add user to docker group
sudo usermod -aG docker $USER
# Logout and login again, or run:
newgrp docker
```

#### Permission Denied
```bash
# Fix Docker permissions
sudo chmod 666 /var/run/docker.sock

# Or add user to docker group (recommended)
sudo usermod -aG docker $USER
newgrp docker
```

#### Container Won't Start
```bash
# Check container logs
docker compose logs cursorscraper

# Check if ports are available
sudo netstat -tulpn | grep :5000

# Rebuild container
docker compose down
docker compose build --no-cache
docker compose up -d
```

#### Volume Mount Issues
```bash
# Check volume mounts
docker compose exec cursorscraper ls -la /app/

# Fix permissions
sudo chown -R $USER:$USER ./roms ./media ./cache ./var/task_logs
```

#### ImageMagick/FFmpeg Issues in Container
```bash
# Test inside container
docker compose exec cursorscraper convert -version
docker compose exec cursorscraper ffmpeg -version

# If missing, rebuild with --no-cache
docker compose build --no-cache
```

### Reverse Proxy Issues

#### Nginx Issues
```bash
# Check Nginx status
sudo systemctl status nginx

# Test configuration
sudo nginx -t

# Check error logs
sudo tail -f /var/log/nginx/error.log

# Check access logs
sudo tail -f /var/log/nginx/access.log

# Common fixes
# 1. Restart Nginx
sudo systemctl restart nginx

# 2. Check if port 5000 is accessible
curl http://127.0.0.1:5000

# 3. Check WebSocket support
# Ensure proxy_http_version 1.1 and Upgrade headers are set
```

#### Apache Issues
```bash
# Check Apache status
sudo systemctl status apache2

# Test configuration
sudo apache2ctl configtest

# Check error logs
sudo tail -f /var/log/apache2/error.log

# Check access logs
sudo tail -f /var/log/apache2/access.log

# Enable required modules
sudo a2enmod proxy proxy_http proxy_wstunnel rewrite ssl headers

# Restart Apache
sudo systemctl restart apache2
```

#### SSL Certificate Issues
```bash
# Check certificate status
sudo certbot certificates

# Test certificate renewal
sudo certbot renew --dry-run

# Check certificate files
sudo ls -la /etc/letsencrypt/live/your-domain.com/

# Manual certificate renewal
sudo certbot renew

# Check certificate expiration
openssl x509 -in /etc/letsencrypt/live/your-domain.com/cert.pem -text -noout | grep "Not After"
```

#### WebSocket Issues
```bash
# Test WebSocket connection
wscat -c wss://your-domain.com/socket.io/

# Check if WebSocket headers are properly set
curl -H "Upgrade: websocket" -H "Connection: Upgrade" -H "Sec-WebSocket-Key: test" -H "Sec-WebSocket-Version: 13" http://your-domain.com/socket.io/

# For Nginx: Ensure proxy_http_version 1.1 and Upgrade headers
# For Apache: Ensure proxy_wstunnel module is enabled
```

#### Firewall Issues
```bash
# Check UFW status
sudo ufw status verbose

# Check iptables rules
sudo iptables -L -n

# Test port accessibility
telnet your-domain.com 80
telnet your-domain.com 443

# Check if application port is blocked
telnet your-domain.com 5000  # Should fail if properly configured
```

### Systemd Service Issues

#### Service Won't Start
```bash
# Check service status
sudo systemctl status cursorscraper

# Check detailed logs
sudo journalctl -u cursorscraper --no-pager

# Check if Python dependencies are installed
sudo -u cursorscraper python3 -c "import flask, requests, httpx"

# Check file permissions
sudo ls -la /opt/cursorscraper/
sudo ls -la /opt/cursorscraper/app.py
```

#### Permission Issues
```bash
# Fix ownership
sudo chown -R cursorscraper:cursorscraper /opt/cursorscraper

# Fix permissions
sudo chmod +x /opt/cursorscraper/app.py
sudo chmod 755 /opt/cursorscraper

# Check if user exists
id cursorscraper
```

#### Service Keeps Restarting
```bash
# Check for errors in logs
sudo journalctl -u cursorscraper --since "5 minutes ago"

# Check if port is already in use
sudo netstat -tulpn | grep :5000

# Test application manually
sudo -u cursorscraper /usr/bin/python3 /opt/cursorscraper/app.py
```

#### Memory/Resource Issues
```bash
# Check resource usage
sudo systemctl show cursorscraper --property=MemoryCurrent,CPUUsageNSec

# Adjust memory limits in service file
sudo nano /etc/systemd/system/cursorscraper.service
# Modify MemoryMax=2G to higher value

# Reload and restart
sudo systemctl daemon-reload
sudo systemctl restart cursorscraper
```

#### Log Issues
```bash
# Check if logging is working
sudo journalctl -u cursorscraper --since "1 hour ago" | tail -20

# Check systemd journal status
sudo systemctl status systemd-journald

# Clear old logs if needed
sudo journalctl --vacuum-time=7d
```

### Debian Installation Issues

#### ImageMagick Issues
```bash
# If ImageMagick commands fail, check installation
sudo apt install --reinstall imagemagick

# Test ImageMagick
convert -version
identify -version

# If policy issues occur (common on newer Debian/Ubuntu)
sudo nano /etc/ImageMagick-6/policy.xml
# Comment out or remove lines that restrict file types
```

#### FFmpeg Issues
```bash
# Install FFmpeg from official repository
sudo apt install ffmpeg

# If not available, add multimedia repository
sudo apt install software-properties-common
sudo add-apt-repository ppa:jonathonf/ffmpeg-4
sudo apt update && sudo apt install ffmpeg
```

#### yt-dlp Issues
```bash
# Install latest version
sudo pip3 install yt-dlp

# Or install from official repository
sudo apt install yt-dlp

# Update to latest version
sudo yt-dlp -U
```

#### Python Package Issues
```bash
# If system packages are missing or outdated
sudo apt update
sudo apt install --reinstall \
    python3-flask \
    python3-flask-cors \
    python3-flask-socketio \
    python3-flask-login \
    python3-flask-session \
    python3-requests \
    python3-httpx \
    python3-aiofiles

# Check package versions
python3 -c "import flask; print('Flask:', flask.__version__)"
python3 -c "import requests; print('Requests:', requests.__version__)"

# If you need newer versions, you can still use pip for specific packages
sudo pip3 install --upgrade flask flask-cors flask-socketio
```

#### Permission Issues
```bash
# If you get permission errors
sudo chown -R $USER:$USER /path/to/cursorscraper
chmod +x app.py
```

### Common Git Issues

- **File too large**: Check `.gitignore` and use `git add -f` if needed
- **Wrong branch**: Use `git checkout <branch-name>` to switch
- **Lost changes**: Use `git stash` to save work in progress
- **Undo commit**: Use `git reset HEAD~1` or `git revert HEAD`

### Application Issues

- **404 errors**: Check if Flask server is running
- **Import errors**: Verify all dependencies are installed
- **File corruption**: Use `git checkout -- <file>` to restore from Git
- **ImageMagick not found**: Ensure ImageMagick is installed and in PATH
- **FFmpeg not found**: Ensure FFmpeg is installed and in PATH
- **yt-dlp not found**: Ensure yt-dlp is installed and in PATH

## Contributing

1. Create a feature branch: `git checkout -b feature/your-feature`
2. Make your changes and commit them
3. Push to your branch: `git push origin feature/your-feature`
4. Create a pull request to merge into development

## License

This project is open source. Feel free to modify and distribute as needed.
