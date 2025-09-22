# Discord Authentication Setup

> **📚 For comprehensive documentation, see [DISCORD_AUTHENTICATION_GUIDE.md](DISCORD_AUTHENTICATION_GUIDE.md)**

## Quick Setup Guide

### 1. Create Discord Application

1. Go to https://discord.com/developers/applications
2. Click "New Application"
3. Enter a name (e.g., "CursorScraper")
4. Click "Create"

### 2. Get OAuth2 Credentials

1. In your Discord application, go to "OAuth2" → "General"
2. Copy the "Client ID" and "Client Secret"
3. Add redirect URI: `http://localhost:5000/discord/callback` (for development)

### 3. Create Bot for Role Verification

1. Go to "Bot" section in your Discord application
2. Click "Add Bot" → "Yes, do it!"
3. Click "Reset Token" and copy the Bot Token
4. Enable "SERVER MEMBERS INTENT" in Privileged Gateway Intents
5. Use OAuth2 → URL Generator to add bot to your server

### 4. Configure GameManager

**Option A: Using Web Interface (Recommended)**
1. Start GameManager and go to Application Configuration
2. Navigate to Discord Configuration section
3. Fill in all Discord settings

**Option B: Using credentials.json**
Create `var/config/credentials.json`:

```json
{
    "discord": {
        "client_id": "1234567890123456789",
        "client_secret": "abcdefghijklmnopqrstuvwxyz123456",
        "redirect_uri": "http://localhost:5000/discord/callback",
        "scope": "identify email guilds guilds.members.read",
        "bot_token": "MTA0NjI3MjM3MTQ5MDM5NjE4MA.G9aIXX.xxx",
        "auto_create": {
            "enabled": true,
            "guild_id": "1006854943157788722",
            "role_name": "Creator"
        }
    }
}
```

### 5. Get Server Information

1. Enable Developer Mode in Discord (User Settings → Advanced → Developer Mode)
2. Right-click your server name → "Copy Server ID" (this is your Guild ID)
3. Create a role in your server (e.g., "Creator") for access control

### 6. Test Discord Authentication

1. Start GameManager: `python3 app.py`
2. Go to `http://localhost:5000/login`
3. Click "Login with Discord"
4. Complete Discord authorization
5. Verify you're logged in and user is created (if auto-create enabled)

### 7. Production Configuration

For production, update the redirect URI in both:
- Discord Developer Portal: `https://yourdomain.com/discord/callback`
- GameManager configuration: `https://yourdomain.com/discord/callback`

### 8. Troubleshooting

**Common Issues:**

- **"Invalid client"**: Check Client ID and Client Secret
- **"Redirect URI mismatch"**: Ensure redirect URI matches exactly
- **"Role verification failed"**: Enable SERVER MEMBERS INTENT and add bot to server
- **"Rate limited"**: Wait and retry, implement backoff

**For detailed troubleshooting, see [DISCORD_AUTHENTICATION_GUIDE.md](DISCORD_AUTHENTICATION_GUIDE.md)**

### 9. Security Notes

- 🔒 Keep Bot Token and Client Secret secure
- 🔒 Never commit credentials to version control
- 🔒 Use environment variables in production
- 🔒 Enable HTTPS in production
- 🔒 Limit bot permissions to minimum required

## Next Steps

- 📖 Read the [comprehensive guide](DISCORD_AUTHENTICATION_GUIDE.md) for detailed setup
- 🔧 Configure additional settings in GameManager web interface
