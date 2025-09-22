#!/usr/bin/env python3
"""
Test Discord OAuth2 configuration
"""
import requests
import json

# Load configuration
with open('var/config/config.json', 'r') as f:
    config = json.load(f)

discord_config = config.get('discord', {})
client_id = discord_config.get('client_id')
client_secret = discord_config.get('client_secret')
redirect_uri = discord_config.get('redirect_uri')

print("=== Discord Configuration Test ===")
print(f"Client ID: {client_id}")
print(f"Client Secret: {'*' * len(client_secret) if client_secret else 'NOT SET'}")
print(f"Redirect URI: {redirect_uri}")

# Test Discord OAuth2 URL
discord_url = f"https://discord.com/api/oauth2/authorize?client_id={client_id}&redirect_uri={redirect_uri}&response_type=code&scope=identify email"
print(f"\nDiscord OAuth2 URL:")
print(discord_url)

# Test if we can reach Discord API
try:
    response = requests.get('https://discord.com/api/oauth2/token', timeout=5)
    print(f"\nDiscord API Status: {response.status_code}")
except Exception as e:
    print(f"\nDiscord API Error: {e}")

print("\n=== Next Steps ===")
print("1. Visit the Discord OAuth2 URL above in your browser")
print("2. Try to authorize the application")
print("3. Check if you get redirected back with a 'code' parameter")
print("4. If you get an error, check the Discord Developer Portal settings")
