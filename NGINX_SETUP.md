# Nginx Setup for GameManager

This guide explains how to configure nginx as a reverse proxy for the GameManager application.

## Features

- ✅ **HTTP and HTTPS support**
- ✅ **WebSocket support** (for real-time task updates)
- ✅ **Large file uploads** (up to 500MB for ROMs and media)
- ✅ **Extended timeouts** for long-running operations
- ✅ **Direct media access** (bypasses Flask for faster performance)
- ✅ **Security headers**

### Direct Media Access

The nginx configuration includes direct access to ROM media files, which means:

- **Faster loading**: Media files (images, videos) are served directly by nginx
- **Reduced load**: Less work for the Python application
- **Smart caching**: Media files are cached with ETag validation (no forced expiration)
- **Scalability**: Nginx handles static content more efficiently

Direct access applies to:
- `/roms/` - All ROM media files (boxart, screenshots, videos, etc.)
  - Uses `Cache-Control: public, must-revalidate` - allows client-side caching
  - Uses ETag for cache validation - files are revalidated on server changes
  - **No forced expiration** - files cached until server changes detected
  
- `/static/` - Application static files (CSS, JS, images)
  - Uses long-term caching (30 days) - files rarely change
  - Uses `Cache-Control: public, immutable` - assumes files never change

All other requests (API calls, WebSocket) go through the Flask application.

#### Caching Strategy

The configuration uses different caching strategies for different content types:

1. **ROM Media** (`/roms/`): 
   - Cached by browsers but always validated before use
   - ETag allows quick revalidation without re-downloading
   - If file unchanged, browser uses cache
   - If file changed, browser downloads new version
   - No forced expiration date

2. **Static Files** (`/static/`):
   - Long-term caching (30 days)
   - Assumes files rarely change
   - Perfect for CSS, JS, and UI assets

## Installation Steps

### 1. Install Nginx

```bash
sudo apt update
sudo apt install nginx
```

### 2. Copy Configuration

```bash
# Copy the configuration file
sudo cp nginx-gamemanager.conf /etc/nginx/sites-available/gamemanager

# Create a symbolic link to enable the site
sudo ln -s /etc/nginx/sites-available/gamemanager /etc/nginx/sites-enabled/

# Remove default site (optional)
sudo rm /etc/nginx/sites-enabled/default
```

### 3. Edit Configuration

Edit the configuration file to match your setup:

```bash
sudo nano /etc/nginx/sites-available/gamemanager
```

**Key settings to modify:**

- **`server_name`**: Change `gamemanager.local` to your domain or IP address
- **`proxy_pass`**: Default is `http://127.0.0.1:5000` - confirm this matches your GameManager port

### 4. Test and Reload Nginx

```bash
# Test the configuration
sudo nginx -t

# If successful, reload nginx
sudo systemctl reload nginx
```

### 5. Configure GameManager

Make sure GameManager is configured to listen on `127.0.0.1` (localhost only) in production mode:

Check your GameManager configuration or environment variables.

## HTTPS Setup (Optional but Recommended)

### Using Let's Encrypt (Free SSL)

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Get SSL certificate
sudo certbot --nginx -d your-domain.com

# Certbot will automatically configure nginx with HTTPS
```

### Manual SSL Configuration

1. Uncomment the HTTPS server block in the nginx configuration
2. Update SSL certificate paths:
   ```nginx
   ssl_certificate /path/to/your/certificate.crt;
   ssl_certificate_key /path/to/your/private.key;
   ```
3. Reload nginx: `sudo systemctl reload nginx`

## Firewall Configuration

If you have a firewall, allow HTTP and HTTPS:

```bash
sudo ufw allow 'Nginx Full'
# Or separately:
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
```

## WebSocket Support

The configuration includes full WebSocket support for real-time features:

- ✅ Task progress updates
- ✅ Live log streaming
- ✅ Real-time status changes

Key WebSocket settings:
```nginx
proxy_http_version 1.1;
proxy_set_header Upgrade $http_upgrade;
proxy_set_header Connection "upgrade";
```

## Testing

1. **Test HTTP:**
   ```bash
   curl http://localhost/
   ```

2. **Test from browser:**
   - Open `http://your-server-ip/` in your browser
   - You should see the GameManager interface

3. **Check WebSocket:**
   - Open browser developer tools
   - Look for WebSocket connections in Network tab
   - Task updates should work in real-time

## Troubleshooting

### GameManager not accessible

- Check if GameManager is running: `sudo systemctl status gamemanager`
- Check if it's listening on the correct port: `sudo netstat -tlnp | grep 5000`
- Check nginx logs: `sudo tail -f /var/log/nginx/gamemanager_error.log`

### WebSocket not working

- Verify headers are set correctly
- Check browser console for WebSocket errors
- Test direct connection to GameManager port (bypassing nginx)

### Large file uploads failing

- Increase `client_max_body_size` if needed
- Check application logs for timeout issues
- Verify sufficient disk space

### 502 Bad Gateway

- GameManager application is not running
- Check GameManager logs: `sudo journalctl -u gamemanager -f`

## File Locations

- **Configuration**: `/etc/nginx/sites-available/gamemanager`
- **Access logs**: `/var/log/nginx/gamemanager_access.log`
- **Error logs**: `/var/log/nginx/gamemanager_error.log`

## Performance Tips

1. **Enable static file caching** (if applicable):
   Uncomment the static files location block in the configuration

2. **Adjust timeouts** if you're processing very large files:
   Increase `proxy_read_timeout` and `proxy_send_timeout`

3. **Monitor connection limits**:
   Adjust `worker_connections` in `/etc/nginx/nginx.conf` if needed

## Security Notes

- The configuration includes basic security headers
- For production, consider:
  - Enabling HTTPS only (redirect HTTP to HTTPS)
  - Adding rate limiting
  - Implementing IP whitelisting for admin access
  - Setting up fail2ban for brute force protection

