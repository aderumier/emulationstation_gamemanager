# Discord OAuth2 Setup Example

## Step-by-Step Discord OAuth2 Configuration

### 1. Create Discord Application

1. Go to https://discord.com/developers/applications
2. Click "New Application"
3. Enter a name (e.g., "CursorScraper")
4. Click "Create"

### 2. Get OAuth2 Credentials

1. In your Discord application, go to "OAuth2" → "General"
2. Copy the "Client ID" and "Client Secret"
3. Go to "OAuth2" → "URL Generator"
4. Select scopes: `identify` and `email`
5. Add redirect URI: `http://localhost:5000/discord/callback` (for development)

### 3. Update var/config/config.json

Replace the placeholder values in your `var/config/config.json`:

```json
{
    "discord": {
        "client_id": "1234567890123456789",
        "client_secret": "abcdefghijklmnopqrstuvwxyz123456",
        "redirect_uri": "http://localhost:5000/discord/callback",
        "scope": "identify email"
    }
}
```

### 4. Production Configuration

For production, update the redirect URI:

```json
{
    "discord": {
        "client_id": "1234567890123456789",
        "client_secret": "abcdefghijklmnopqrstuvwxyz123456",
        "redirect_uri": "https://yourdomain.com/discord/callback",
        "scope": "identify email"
    }
}
```

### 5. Test Discord Login

1. Start the application: `python3 app.py`
2. Go to `http://localhost:5000/login`
3. Click "Login with Discord"
4. You should be redirected to Discord for authorization
5. After authorization, you'll be redirected back to the application

### 6. Troubleshooting

**Common Issues:**

- **"Invalid redirect URI"**: Make sure the redirect URI in Discord Developer Portal exactly matches the one in var/config/config.json
- **"Invalid client"**: Check that the client_id and client_secret are correct
- **"Access denied"**: Ensure the Discord application is not in development mode (if required)

**Development vs Production:**

- **Development**: Use `http://localhost:5000/discord/callback`
- **Production**: Use `https://yourdomain.com/discord/callback`
- Make sure to update both Discord Developer Portal and var/config/config.json

### 7. Security Notes

- Keep your client_secret secure and never commit it to version control
- Use environment variables or secure configuration management in production
- Consider using different Discord applications for development and production
