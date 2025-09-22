# Discord Authentication Setup Guide

This guide explains how to set up Discord authentication for GameManager, including generating the required tokens and configuring the application.

## Overview

GameManager supports two types of Discord authentication:

1. **OAuth2 User Authentication** - For user login via Discord
2. **Bot Token Authentication** - For role verification and server management

## Prerequisites

- A Discord account
- Administrator access to a Discord server (for role verification)
- Basic understanding of Discord Developer Portal

## Step 1: Create a Discord Application

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click **"New Application"**
3. Enter a name for your application (e.g., "GameManager")
4. Click **"Create"**

## Step 2: Configure OAuth2 Settings

### 2.1 OAuth2 General Settings

1. In your application, go to **"OAuth2" → "General"**
2. Copy the **Client ID** - you'll need this later
3. Click **"Reset Secret"** to generate a **Client Secret** - copy this too
4. Add redirect URIs:
   - For development: `http://localhost:5000/discord/callback`
   - For production: `https://yourdomain.com/discord/callback`

### 2.2 OAuth2 Scopes

The following scopes are required for user authentication:

- `identify` - Get user's basic information
- `email` - Get user's email address
- `guilds` - Get user's guild (server) memberships
- `guilds.members.read` - Read user's guild members (for role verification)

## Step 3: Create and Configure Bot

### 3.1 Create Bot User

1. Go to **"Bot"** in your application settings
2. Click **"Add Bot"**
3. Click **"Yes, do it!"** to confirm

### 3.2 Generate Bot Token

1. In the **"Bot"** section, click **"Reset Token"**
2. Copy the **Bot Token** - this is sensitive, keep it secure!
3. The token looks like: `MTA0NjI3MjM3MTQ5MDM5NjE4MA.G9aIXX.xxx`

### 3.3 Configure Bot Permissions

1. In the **"Bot"** section, scroll down to **"Privileged Gateway Intents"**
2. Enable **"SERVER MEMBERS INTENT"** - Required for role verification
3. Optionally enable **"MESSAGE CONTENT INTENT"** if needed

### 3.4 Add Bot to Your Server

1. Go to **"OAuth2" → "URL Generator"**
2. Select scopes: **"bot"**
3. Select permissions:
   - **"Read Messages/View Channels"** (minimum)
   - **"Read Message History"** (optional)
   - **"View Server"** (for role verification)
4. Copy the generated URL and open it in your browser
5. Select your server and authorize the bot

## Step 4: Configure GameManager

### 4.1 Using Web Interface (Recommended)

1. Start GameManager and go to **Application Configuration**
2. Navigate to **"Discord Configuration"** section
3. Fill in the following fields:

```
Client ID: [Your Discord Client ID]
Client Secret: [Your Discord Client Secret]
Redirect URI: http://localhost:5000/discord/callback
Bot Token: [Your Discord Bot Token]
Auto-create users: ✓ (checked)
Guild ID: [Your Discord Server ID]
Role Name: Creator
```

### 4.2 Using credentials.json (Advanced)

Create or edit `var/config/credentials.json`:

```json
{
  "discord": {
    "client_id": "your_discord_client_id_here",
    "client_secret": "your_discord_client_secret_here",
    "redirect_uri": "http://localhost:5000/discord/callback",
    "scope": "identify email guilds guilds.members.read",
    "bot_token": "your_discord_bot_token_here",
    "auto_create": {
      "enabled": true,
      "guild_id": "your_discord_guild_id_here",
      "role_name": "Creator"
    }
  }
}
```

## Step 5: Get Discord Server ID

### Method 1: Using Discord Desktop App

1. Enable Developer Mode:
   - Go to **User Settings** → **Advanced** → **Developer Mode** (ON)
2. Right-click on your server name
3. Select **"Copy Server ID"**

### Method 2: Using Discord Web

1. Go to **User Settings** → **Advanced** → **Developer Mode** (ON)
2. Right-click on your server name in the server list
3. Select **"Copy Server ID"**

## Step 6: Create Required Role

1. In your Discord server, go to **Server Settings** → **Roles**
2. Create a new role (e.g., "Creator")
3. Set appropriate permissions for the role
4. Assign this role to users who should have access to GameManager

## Token Types Explained

### OAuth2 Client Credentials

- **Client ID**: Public identifier for your application
- **Client Secret**: Secret key for server-side authentication
- **Redirect URI**: Where Discord sends users after authentication

### Bot Token

- **Purpose**: Allows the application to act as a bot
- **Permissions**: Can read server members and roles
- **Security**: Keep this secret - it has full bot access

### User Access Token

- **Generated**: Automatically during OAuth2 flow
- **Purpose**: Access user's Discord information
- **Scope**: Limited to what user authorized

## Security Best Practices

### 1. Token Security

- **Never commit tokens to version control**
- **Use environment variables in production**
- **Rotate tokens regularly**
- **Limit bot permissions to minimum required**

### 2. Server Security

- **Use HTTPS in production**
- **Validate redirect URIs**
- **Implement rate limiting**
- **Monitor for suspicious activity**

### 3. Role Management

- **Use specific roles for access control**
- **Regularly audit role assignments**
- **Remove access for inactive users**

## Troubleshooting

### Common Issues

#### 1. "Invalid Client" Error

**Cause**: Incorrect Client ID or Client Secret
**Solution**: 
- Verify Client ID and Secret in Discord Developer Portal
- Ensure credentials are copied correctly (no extra spaces)

#### 2. "Redirect URI Mismatch" Error

**Cause**: Redirect URI doesn't match configured URI
**Solution**:
- Check redirect URI in Discord Developer Portal
- Ensure it matches exactly (including http/https)

#### 3. "Rate Limited" Error

**Cause**: Too many API requests
**Solution**:
- Wait for rate limit to reset
- Implement exponential backoff in your application

#### 4. "Role Verification Failed" Error

**Cause**: Bot can't verify user roles
**Solution**:
- Ensure bot has "Server Members Intent" enabled
- Verify bot is in the server
- Check bot has "View Server" permission
- Verify Guild ID is correct

#### 5. "User Not Found" Error

**Cause**: User not in configured Discord server
**Solution**:
- Verify user is member of the Discord server
- Check Guild ID configuration
- Ensure user has the required role

### Debug Steps

1. **Check Bot Permissions**:
   ```bash
   # Test bot token validity
   curl -H "Authorization: Bot YOUR_BOT_TOKEN" https://discord.com/api/guilds/YOUR_GUILD_ID
   ```

2. **Verify OAuth2 Configuration**:
   - Test redirect URI manually
   - Check scopes in Discord Developer Portal
   - Verify Client ID and Secret

3. **Check Server Configuration**:
   - Verify Guild ID is correct
   - Ensure role exists and is spelled correctly
   - Check bot is in the server

## Testing Authentication

### 1. Test OAuth2 Flow

1. Go to GameManager login page
2. Click "Login with Discord"
3. Complete Discord authorization
4. Verify you're logged in

### 2. Test Role Verification

1. Create a test user with the required role
2. Try logging in with Discord
3. Verify user is created automatically
4. Test with user without required role (should be denied)

### 3. Test Bot Functionality

1. Check GameManager logs for bot API calls
2. Verify role verification works
3. Test with different user roles

## Production Deployment

### Environment Variables

For production, consider using environment variables:

```bash
export DISCORD_CLIENT_ID="your_client_id"
export DISCORD_CLIENT_SECRET="your_client_secret"
export DISCORD_BOT_TOKEN="your_bot_token"
export DISCORD_GUILD_ID="your_guild_id"
export DISCORD_ROLE_NAME="Creator"
```

### Docker Configuration

```yaml
version: '3.8'
services:
  gamemanager:
    image: aderumier/emulationstation_gamemanager:latest
    environment:
      - DISCORD_CLIENT_ID=your_client_id
      - DISCORD_CLIENT_SECRET=your_client_secret
      - DISCORD_BOT_TOKEN=your_bot_token
      - DISCORD_GUILD_ID=your_guild_id
      - DISCORD_ROLE_NAME=Creator
    volumes:
      - ./var:/opt/gamemanager/var
    ports:
      - "5000:5000"
```

## API Reference

### Discord API Endpoints Used

- `GET /oauth2/authorize` - Start OAuth2 flow
- `POST /oauth2/token` - Exchange code for access token
- `GET /users/@me` - Get current user info
- `GET /users/@me/guilds` - Get user's guild memberships
- `GET /guilds/{guild_id}/members/{user_id}` - Get guild member info
- `GET /guilds/{guild_id}/roles` - Get guild roles

### Required Scopes

- `identify` - Basic user information
- `email` - User's email address
- `guilds` - User's guild memberships
- `guilds.members.read` - Read guild members (for role verification)

## Support

If you encounter issues:

1. Check this troubleshooting guide
2. Review Discord Developer Portal documentation
3. Check GameManager logs for error messages
4. Verify all tokens and IDs are correct

## Additional Resources

- [Discord Developer Portal](https://discord.com/developers/applications)
- [Discord API Documentation](https://discord.com/developers/docs)
- [OAuth2 Documentation](https://discord.com/developers/docs/topics/oauth2)
- [Bot Documentation](https://discord.com/developers/docs/intro#bots-and-apps)
