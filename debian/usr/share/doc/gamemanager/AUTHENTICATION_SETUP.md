# Authentication Setup Guide

## Overview

CursorScraper now includes a comprehensive authentication system with:
- Local user management with hashed passwords
- Discord OAuth2 SSO integration
- User registration with manual validation
- Admin user management panel

## Default Admin Account

On first startup, a default admin account is created:
- **Username**: `admin`
- **Password**: `admin123`
- **Status**: Validated and active

⚠️ **IMPORTANT**: Change the default password after first login!

## Discord OAuth2 Setup

To enable Discord SSO, you need to:

1. **Create a Discord Application**:
   - Go to https://discord.com/developers/applications
   - Click "New Application"
   - Give it a name (e.g., "CursorScraper")

2. **Get OAuth2 Credentials**:
   - Go to the "OAuth2" section
   - Copy the "Client ID" and "Client Secret"

3. **Configure in var/config/config.json**:
   - Edit `var/config/config.json` and update the `discord` section:
   ```json
   "discord": {
       "client_id": "your_discord_client_id_here",
       "client_secret": "your_discord_client_secret_here",
       "redirect_uri": "http://localhost:5000/discord/callback",
       "scope": "identify email"
   }
   ```

4. **Configure Redirect URI**:
   - In Discord Developer Portal, add redirect URI:
   - `http://localhost:5000/discord/callback` (for development)
   - `https://yourdomain.com/discord/callback` (for production)
   - Update the `redirect_uri` in var/config/config.json to match your domain

## User Management

### User Registration
- New users can register via the registration page
- All new accounts require manual validation by existing users
- Users can register with username/password or Discord SSO

### Admin Functions
- Access user management via Configuration → User Management
- Validate pending users
- Activate/deactivate user accounts
- View user activity and registration details

### User States
- **Pending**: New user, needs validation
- **Validated**: User can access all features
- **Inactive**: User account is disabled

## Security Features

- **Password Hashing**: SHA-256 with salt
- **Session Management**: Flask-Login with secure sessions
- **Route Protection**: All API endpoints require authentication
- **User Validation**: Manual approval process for new users

## File Structure

- `var/config/user.cfg`: Local user database (JSON format)
- `templates/login.html`: Login page
- `templates/register.html`: Registration page
- `templates/admin_users.html`: User management panel

## API Endpoints

### Authentication
- `GET /login` - Login page
- `POST /login` - Process login
- `GET /register` - Registration page
- `POST /register` - Process registration
- `GET /logout` - Logout user
- `GET /discord/login` - Discord OAuth login
- `GET /discord/callback` - Discord OAuth callback

### User Management (Admin only)
- `GET /admin/users` - User management panel
- `POST /admin/users/<user_id>/validate` - Validate user
- `POST /admin/users/<user_id>/activate` - Activate user
- `POST /admin/users/<user_id>/deactivate` - Deactivate user

## Troubleshooting

### Common Issues

1. **Discord OAuth not working**:
   - Check Discord configuration in var/config/config.json
   - Verify redirect URI in Discord Developer Portal matches var/config/config.json
   - Ensure Discord application is not in development mode (if needed)
   - Make sure client_id and client_secret are correctly set

2. **Users can't access application**:
   - Check if user is validated in User Management
   - Verify user account is active
   - Check browser console for authentication errors

3. **Default admin password**:
   - Default credentials: admin/admin123
   - Change immediately after first login
   - Use User Management to reset if needed

### Logs
- Check server console for authentication errors
- User login attempts are logged
- Failed authentication attempts are tracked
