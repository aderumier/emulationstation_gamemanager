# Selenium Docker Setup for Google Images Scraping

This document explains how to set up and use Selenium with Docker for Google Images scraping in GameManager.

## Overview

Google Images uses JavaScript protections that require a real browser to bypass. Using Selenium with Docker provides:
- ✅ **No local Chrome/ChromeDriver installation required**
- ✅ **Consistent environment across different systems**
- ✅ **Easy deployment and scaling**
- ✅ **Isolation from host system**

## Quick Start

### 1. Start Selenium Container

```bash
# Start Selenium with the provided script
./start_selenium.sh
```

This will:
- Pull the latest Selenium standalone Chrome image
- Start a container with proper configuration
- Wait for Selenium to be ready
- Display connection information

### 2. Set Environment Variables

```bash
# Set environment variables for GameManager
export SELENIUM_HOST=localhost
export SELENIUM_PORT=4444
```

### 3. Start GameManager

```bash
# Start your GameManager application
python3 app.py
```

The Google Images search will now use the Selenium Docker container.

## Manual Docker Commands

### Start Selenium Container

```bash
docker run -d \
    --name gamemanager-selenium \
    --restart unless-stopped \
    -p 4444:4444 \
    -p 7900:7900 \
    -e SE_NODE_MAX_SESSIONS=2 \
    -e SE_NODE_SESSION_TIMEOUT=300 \
    --shm-size=2g \
    selenium/standalone-chrome:latest
```

### Stop Selenium Container

```bash
# Stop the container
./stop_selenium.sh

# Or manually:
docker stop gamemanager-selenium
docker rm gamemanager-selenium
```

## Docker Compose Setup

For more complex setups, use the provided Docker Compose file:

```bash
# Start with Docker Compose
docker-compose -f docker-compose.selenium.yml up -d

# Stop with Docker Compose
docker-compose -f docker-compose.selenium.yml down
```

## Configuration Options

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SELENIUM_HOST` | `localhost` | Selenium container host |
| `SELENIUM_PORT` | `4444` | Selenium container port |

### Selenium Container Options

| Option | Value | Description |
|--------|-------|-------------|
| `SE_NODE_MAX_SESSIONS` | `2` | Maximum concurrent sessions |
| `SE_NODE_SESSION_TIMEOUT` | `300` | Session timeout in seconds |
| `--shm-size` | `2g` | Shared memory size for Chrome |

## Troubleshooting

### Check Selenium Status

```bash
# Check if Selenium is running
curl http://localhost:4444/wd/hub/status

# Check container logs
docker logs gamemanager-selenium
```

### Common Issues

1. **Connection Refused**
   - Ensure Selenium container is running: `docker ps`
   - Check if port 4444 is available: `netstat -tlnp | grep 4444`

2. **Out of Memory**
   - Increase shared memory: `--shm-size=4g`
   - Reduce max sessions: `SE_NODE_MAX_SESSIONS=1`

3. **Chrome Crashes**
   - Check container logs: `docker logs gamemanager-selenium`
   - Try restarting the container: `docker restart gamemanager-selenium`

### VNC Access (Debugging)

If you need to see what Chrome is doing:

1. Open VNC viewer: `http://localhost:7900`
2. Password: `secret`
3. You'll see the Chrome browser in action

## Production Deployment

### Docker Compose with GameManager

```yaml
version: '3.8'
services:
  gamemanager:
    build: .
    ports:
      - "5000:5000"
    environment:
      - SELENIUM_HOST=selenium
      - SELENIUM_PORT=4444
    depends_on:
      - selenium

  selenium:
    image: selenium/standalone-chrome:latest
    ports:
      - "4444:4444"
    environment:
      - SE_NODE_MAX_SESSIONS=2
      - SE_NODE_SESSION_TIMEOUT=300
    shm_size: 2gb
```

### Scaling with Selenium Grid

For high-traffic scenarios, use Selenium Grid:

```bash
# Start Grid Hub
docker run -d -p 4442:4442 --name selenium-hub selenium/hub:latest

# Start Chrome nodes
docker run -d --name selenium-chrome --link selenium-hub:hub selenium/node-chrome:latest
```

## Security Considerations

- Selenium container runs with elevated privileges
- Only expose necessary ports (4444, 7900)
- Use Docker networks for isolation
- Consider using Selenium Grid for production

## Performance Tips

- Use `--shm-size=2g` or higher for better performance
- Limit `SE_NODE_MAX_SESSIONS` based on your server capacity
- Monitor memory usage: `docker stats gamemanager-selenium`
- Consider using `selenium/node-chrome` for better resource management

## Fallback Behavior

If the Selenium Docker container is not available, the application will:
1. Try to connect to the remote Selenium container
2. Fall back to local Chrome driver (if available)
3. Return an error if neither is available

This ensures the application continues to work even without Docker.

