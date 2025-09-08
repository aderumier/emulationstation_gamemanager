# IGDB API Setup Guide

This guide will walk you through setting up IGDB (Internet Game Database) API access for GameManager.

## What is IGDB?

IGDB is a comprehensive video game database that provides detailed information about games, including:
- Game metadata (titles, descriptions, release dates)
- Screenshots and artwork
- Videos and trailers
- Developer and publisher information
- Genres and categories
- User ratings and reviews

## Prerequisites

- A Twitch account (IGDB is owned by Twitch)
- Access to the Twitch Developer Console

## Step 1: Create a Twitch Account

If you don't already have a Twitch account:

1. Go to [twitch.tv](https://www.twitch.tv)
2. Click "Sign Up" in the top-right corner
3. Follow the registration process
4. Verify your email address

## Step 2: Access Twitch Developer Console

1. Go to [Twitch Developer Console](https://dev.twitch.tv/console/apps)
2. Log in with your Twitch account
3. You'll see the "Applications" dashboard

## Step 3: Create a New Application

1. Click the **"Create"** button or **"Register Your Application"**
2. Fill out the application form:

### Application Details

**Name**: `GameManager` (or any name you prefer)
- This is the display name for your application

**OAuth Redirect URLs**: 
- For local development: `http://localhost:5000`
- For production: `https://yourdomain.com`
- You can add multiple URLs if needed

**Category**: Select **"Application Integration"**
- This category is appropriate for tools like GameManager

**Description**: 
```
Game collection management system that uses IGDB API to fetch game metadata, artwork, and videos for organizing ROM collections.
```

## Step 4: Get Your Credentials

After creating the application, you'll be taken to the application details page:

1. **Client ID**: This is your `IGDB_CLIENT_ID`
   - Copy this value - you'll need it for GameManager
   - It's visible on the main application page

2. **Client Secret**: This is your `IGDB_CLIENT_SECRET`
   - Click **"New Secret"** to generate a client secret
   - **Important**: Copy this immediately - you won't be able to see it again
   - If you lose it, you'll need to generate a new one

## Step 5: Configure GameManager

You have several options to configure your IGDB credentials in GameManager:

### Option 1: Environment Variables (Recommended for Docker)

#### Docker Run Command
```bash
docker run -d \
  --name gamemanager \
  -p 5000:5000 \
  -v $(pwd)/roms:/opt/gamemanager/roms \
  -v $(pwd)/var:/opt/gamemanager/var \
  -e IGDB_CLIENT_ID=your_client_id_here \
  -e IGDB_CLIENT_SECRET=your_client_secret_here \
  aderumier/cursorscraper:latest
```

#### Docker Compose
```yaml
version: '3.8'
services:
  gamemanager:
    image: aderumier/cursorscraper:latest
    ports:
      - "5000:5000"
    volumes:
      - ./roms:/opt/gamemanager/roms
      - ./var:/opt/gamemanager/var
    environment:
      - IGDB_CLIENT_ID=your_client_id_here
      - IGDB_CLIENT_SECRET=your_client_secret_here
```

#### .env File
Create a `.env` file in your project directory:
```bash
# IGDB API Credentials
IGDB_CLIENT_ID=your_client_id_here
IGDB_CLIENT_SECRET=your_client_secret_here
```

### Option 2: Web Interface Configuration

1. Start GameManager without IGDB credentials
2. Go to **Settings** → **IGDB Configuration**
3. Enter your Client ID and Client Secret
4. Click **"Save Credentials"**
5. The credentials will be stored in `var/config/credentials.json`

### Option 3: Manual Configuration File

Create or edit `var/config/credentials.json`:
```json
{
  "igdb": {
    "client_id": "your_client_id_here",
    "client_secret": "your_client_secret_here"
  }
}
```

## Step 6: Test Your Configuration

1. Start GameManager with your IGDB credentials configured
2. Go to any system with games
3. Try the **"IGDB Scrape"** feature
4. If configured correctly, you should see games being scraped with metadata

## Troubleshooting

### Common Issues

#### "IGDB integration is disabled"
- **Cause**: IGDB credentials not configured
- **Solution**: Set up your Client ID and Client Secret using one of the methods above

#### "Failed to get IGDB access token"
- **Cause**: Invalid credentials or network issues
- **Solution**: 
  - Verify your Client ID and Client Secret are correct
  - Check your internet connection
  - Ensure your Twitch application is active

#### "Rate limited" errors
- **Cause**: Too many API requests
- **Solution**: GameManager automatically handles rate limiting with exponential backoff

#### "No games found" during scraping
- **Cause**: Game names don't match IGDB database
- **Solution**: 
  - Try different game name variations
  - Check if the game exists in IGDB database
  - Use manual IGDB search to verify game availability

### API Limits

IGDB API has the following limits:
- **Rate Limit**: 4 requests per second
- **Concurrent Requests**: 8 simultaneous requests
- **Daily Limit**: Varies based on your Twitch application tier

GameManager automatically handles these limits with:
- Request throttling
- Exponential backoff on rate limits
- Concurrent request management

## Security Best Practices

### Protect Your Credentials

1. **Never commit credentials to version control**
   - Use `.env` files (excluded from git)
   - Use environment variables in production
   - Use the web interface for local development

2. **Use environment variables in production**
   - Docker: Use `-e` flags or environment files
   - Systemd: Use environment files
   - Cloud platforms: Use their secret management

3. **Rotate credentials regularly**
   - Generate new Client Secrets periodically
   - Update GameManager configuration when rotating

### File Permissions

Ensure proper file permissions for credential files:
```bash
# For credentials.json
chmod 600 var/config/credentials.json

# For .env files
chmod 600 .env
```

## Advanced Configuration

### Custom IGDB Settings

You can customize IGDB behavior in `var/config/config.json`:

```json
{
  "igdb": {
    "enabled": true,
    "rate_limit": {
      "requests_per_second": 4,
      "max_concurrent": 8
    },
    "retry": {
      "max_retries": 3,
      "backoff_factor": 2
    },
    "timeout": {
      "connect": 10,
      "read": 30
    }
  }
}
```

### Multiple Applications

If you need higher rate limits:
1. Create multiple Twitch applications
2. Configure GameManager to use different credentials for different operations
3. Implement load balancing across applications

## Support

### Getting Help

- **IGDB API Documentation**: [api-docs.igdb.com](https://api-docs.igdb.com/)
- **Twitch Developer Console**: [dev.twitch.tv/console](https://dev.twitch.tv/console/apps)
- **GameManager Issues**: [GitHub Issues](https://github.com/aderumier/emulationstation_gamemanager/issues)

### Common Questions

**Q: Do I need to pay for IGDB API access?**
A: No, IGDB API is free for personal and commercial use within the rate limits.

**Q: Can I use IGDB for commercial projects?**
A: Yes, but check the [IGDB Terms of Service](https://www.igdb.com/terms) for specific requirements.

**Q: What if I exceed the rate limits?**
A: GameManager automatically handles rate limiting. If you consistently hit limits, consider creating multiple Twitch applications.

**Q: Can I cache IGDB data locally?**
A: Yes, GameManager caches metadata locally to reduce API calls and improve performance.

---

**Need more help?** Check the main [README.md](README.md) or open an issue on GitHub.
