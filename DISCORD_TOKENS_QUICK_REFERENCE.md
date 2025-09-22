# Discord Tokens Quick Reference

## Token Types and Where to Find Them

### 1. OAuth2 Client Credentials

| Token | Where to Find | Purpose | Security |
|-------|---------------|---------|----------|
| **Client ID** | Discord Developer Portal → OAuth2 → General | Public app identifier | Can be public |
| **Client Secret** | Discord Developer Portal → OAuth2 → General → Reset Secret | Server-side authentication | Keep secret |

### 2. Bot Token

| Token | Where to Find | Purpose | Security |
|-------|---------------|---------|----------|
| **Bot Token** | Discord Developer Portal → Bot → Reset Token | Bot authentication & role verification | Keep secret |

### 3. Server Information

| Information | Where to Find | Purpose | Security |
|-------------|---------------|---------|----------|
| **Guild ID** | Right-click server → Copy Server ID (Developer Mode ON) | Server identification | Can be public |
| **Role Name** | Server Settings → Roles → Create/Select Role | Access control | Can be public |

## Quick Setup Checklist

### Discord Developer Portal Setup

- [ ] Create Discord Application
- [ ] Get Client ID from OAuth2 → General
- [ ] Generate Client Secret from OAuth2 → General
- [ ] Add Redirect URI: `http://localhost:5000/discord/callback`
- [ ] Create Bot User (Bot section)
- [ ] Generate Bot Token (Bot section)
- [ ] Enable "SERVER MEMBERS INTENT" (Bot section)

### Discord Server Setup

- [ ] Enable Developer Mode in Discord
- [ ] Get Guild ID (right-click server → Copy Server ID)
- [ ] Create role (e.g., "Creator")
- [ ] Add bot to server with OAuth2 URL Generator
- [ ] Give bot "View Server" permission

### GameManager Configuration

- [ ] Set Client ID in Discord Configuration
- [ ] Set Client Secret in Discord Configuration
- [ ] Set Redirect URI in Discord Configuration
- [ ] Set Bot Token in Discord Configuration
- [ ] Enable Auto-create users
- [ ] Set Guild ID in Discord Configuration
- [ ] Set Role Name in Discord Configuration

## Token Format Examples

### Client ID
```
1351823474087165984
```
- 17-18 digits
- Public identifier
- Safe to share

### Client Secret
```
zJnP5iT6197CKp0Ktw1kCZlvkFwLq7oQ
```
- 32 characters
- Secret key
- Keep private

### Bot Token
```
MTA0NjI3MjM3MTQ5MDM5NjE4MA.G9aIXX.xxx
```
- 59+ characters
- Starts with letters/numbers
- Keep secret

### Guild ID
```
1006854943157788722
```
- 17-18 digits
- Server identifier
- Safe to share

## Common Issues & Solutions

| Error | Cause | Solution |
|-------|-------|----------|
| `invalid_client` | Wrong Client ID/Secret | Check Discord Developer Portal |
| `redirect_uri_mismatch` | Wrong redirect URI | Update in Discord Developer Portal |
| `rate_limited` | Too many requests | Wait and retry |
| `role_verification_failed` | Bot can't check roles | Enable SERVER MEMBERS INTENT |
| `user_not_found` | User not in server | Check Guild ID and user membership |

## Security Reminders

- 🔒 **Never commit tokens to git**
- 🔒 **Use environment variables in production**
- 🔒 **Rotate tokens regularly**
- 🔒 **Limit bot permissions to minimum required**
- 🔒 **Use HTTPS in production**

## Testing Commands

### Test Bot Token
```bash
curl -H "Authorization: Bot YOUR_BOT_TOKEN" https://discord.com/api/guilds/YOUR_GUILD_ID
```

### Test OAuth2 Flow
1. Go to: `https://discord.com/api/oauth2/authorize?client_id=YOUR_CLIENT_ID&redirect_uri=YOUR_REDIRECT_URI&response_type=code&scope=identify%20email%20guilds%20guilds.members.read`
2. Complete authorization
3. Check callback URL for code parameter

## File Locations

### GameManager Configuration
- **Web Interface**: Application Configuration → Discord Configuration
- **File**: `var/config/credentials.json`
- **Example**: `var/config/credentials.json.example`

### Discord Developer Portal
- **URL**: https://discord.com/developers/applications
- **OAuth2 Settings**: Your App → OAuth2 → General
- **Bot Settings**: Your App → Bot
- **URL Generator**: Your App → OAuth2 → URL Generator
