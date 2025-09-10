"""
Secure credential management for ScreenScraper API credentials.
Uses base64 encoding with a simple obfuscation method.
"""

import base64
import json
import os
from typing import Dict, Optional

class CredentialManager:
    def __init__(self):
        self.credentials_file = 'var/config/credentials.json'
        self.encoded_credentials_file = 'var/config/credentials.enc'
        
    def _encode_credentials(self, credentials: Dict) -> str:
        """Encode credentials using base64 with simple obfuscation"""
        # Convert to JSON string
        json_str = json.dumps(credentials, indent=2)
        
        # Add some obfuscation by reversing and adding a simple key
        obfuscated = json_str[::-1]  # Reverse the string
        obfuscated = base64.b64encode(obfuscated.encode()).decode()
        
        return obfuscated
    
    def _decode_credentials(self, encoded_str: str) -> Dict:
        """Decode credentials from base64 with deobfuscation"""
        try:
            # Decode from base64
            decoded = base64.b64decode(encoded_str.encode()).decode()
            
            # Reverse the obfuscation
            deobfuscated = decoded[::-1]
            
            # Parse JSON
            return json.loads(deobfuscated)
        except Exception as e:
            print(f"Error decoding credentials: {e}")
            return {}
    
    def get_screenscraper_credentials(self) -> Dict[str, str]:
        """Get ScreenScraper credentials - dev credentials from encoded file, user credentials from regular file"""
        # Get developer credentials from encoded file
        dev_creds = self._get_developer_credentials()
        
        # Get user credentials from regular credentials file
        user_creds = self._get_user_credentials()
        
        # Combine both
        return {
            'devid': dev_creds.get('devid', ''),
            'devpassword': dev_creds.get('devpassword', ''),
            'ssid': user_creds.get('ssid', ''),
            'sspassword': user_creds.get('sspassword', '')
        }
    
    def get_igdb_credentials(self) -> Dict[str, str]:
        """Get IGDB credentials from regular credentials file"""
        if os.path.exists(self.credentials_file):
            try:
                with open(self.credentials_file, 'r') as f:
                    credentials = json.load(f)
                    if 'igdb' in credentials:
                        return credentials['igdb']
            except Exception as e:
                print(f"Error loading IGDB credentials: {e}")
        
        # Return empty IGDB credentials
        return {
            'client_id': '',
            'client_secret': ''
        }
    
    def _get_developer_credentials(self) -> Dict[str, str]:
        """Get developer credentials from encoded file"""
        if os.path.exists(self.encoded_credentials_file):
            try:
                with open(self.encoded_credentials_file, 'r') as f:
                    encoded_data = f.read().strip()
                    credentials = self._decode_credentials(encoded_data)
                    if credentials and 'screenscraper' in credentials:
                        return credentials['screenscraper']
            except Exception as e:
                print(f"Error loading encoded credentials: {e}")
        
        # Return default developer credentials
        return {
            'devid': 'djspirit',
            'devpassword': 'cUIYyyJaImL'
        }
    
    def _get_user_credentials(self) -> Dict[str, str]:
        """Get user credentials from regular credentials file"""
        if os.path.exists(self.credentials_file):
            try:
                with open(self.credentials_file, 'r') as f:
                    credentials = json.load(f)
                    if 'screenscraper' in credentials:
                        return credentials['screenscraper']
            except Exception as e:
                print(f"Error loading regular credentials: {e}")
        
        # Return empty user credentials
        return {
            'ssid': '',
            'sspassword': ''
        }
    
    def save_developer_credentials(self, devid: str, devpassword: str):
        """Save only developer credentials in encoded format"""
        credentials = {
            'screenscraper': {
                'devid': devid,
                'devpassword': devpassword
            }
        }
        
        # Encode and save
        encoded_data = self._encode_credentials(credentials)
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.encoded_credentials_file), exist_ok=True)
        
        with open(self.encoded_credentials_file, 'w') as f:
            f.write(encoded_data)
        
        print("ScreenScraper developer credentials saved securely")
    
    def update_screenscraper_user_credentials(self, ssid: str, sspassword: str):
        """Update only the user credentials (ssid/sspassword) in regular credentials file"""
        # Load existing credentials
        credentials = {}
        if os.path.exists(self.credentials_file):
            try:
                with open(self.credentials_file, 'r') as f:
                    credentials = json.load(f)
            except Exception as e:
                print(f"Error loading existing credentials: {e}")
        
        # Update only the user credentials
        if 'screenscraper' not in credentials:
            credentials['screenscraper'] = {}
        
        credentials['screenscraper']['ssid'] = ssid
        credentials['screenscraper']['sspassword'] = sspassword
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.credentials_file), exist_ok=True)
        
        # Save to regular credentials file
        with open(self.credentials_file, 'w') as f:
            json.dump(credentials, f, indent=2)
        
        print("ScreenScraper user credentials updated in regular file")
    
    def create_encoded_credentials_file(self):
        """Create the encoded credentials file with only developer credentials"""
        credentials = {
            'screenscraper': {
                'devid': 'djspirit',
                'devpassword': 'cUIYyyJaImL'
            }
        }
        
        # Encode and save
        encoded_data = self._encode_credentials(credentials)
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.encoded_credentials_file), exist_ok=True)
        
        with open(self.encoded_credentials_file, 'w') as f:
            f.write(encoded_data)
        
        print("Encoded developer credentials file created successfully")
        print(f"File saved to: {self.encoded_credentials_file}")
        
        # Show the encoded content (for verification)
        print(f"Encoded content: {encoded_data[:50]}...")

# Global instance
credential_manager = CredentialManager()
