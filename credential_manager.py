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
        """Get ScreenScraper credentials from encoded file or fallback to regular file"""
        # First try to load from encoded file
        if os.path.exists(self.encoded_credentials_file):
            try:
                with open(self.encoded_credentials_file, 'r') as f:
                    encoded_data = f.read().strip()
                    credentials = self._decode_credentials(encoded_data)
                    if credentials and 'screenscraper' in credentials:
                        return credentials['screenscraper']
            except Exception as e:
                print(f"Error loading encoded credentials: {e}")
        
        # Fallback to regular credentials file
        if os.path.exists(self.credentials_file):
            try:
                with open(self.credentials_file, 'r') as f:
                    credentials = json.load(f)
                    if 'screenscraper' in credentials:
                        return credentials['screenscraper']
            except Exception as e:
                print(f"Error loading regular credentials: {e}")
        
        # Return default/empty credentials
        return {
            'devid': '',
            'devpassword': '',
            'ssid': '',
            'sspassword': ''
        }
    
    def save_screenscraper_credentials(self, devid: str, devpassword: str, ssid: str, sspassword: str):
        """Save ScreenScraper credentials in encoded format"""
        credentials = {
            'screenscraper': {
                'devid': devid,
                'devpassword': devpassword,
                'ssid': ssid,
                'sspassword': sspassword
            }
        }
        
        # Encode and save
        encoded_data = self._encode_credentials(credentials)
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.encoded_credentials_file), exist_ok=True)
        
        with open(self.encoded_credentials_file, 'w') as f:
            f.write(encoded_data)
        
        print("ScreenScraper credentials saved securely")
    
    def create_encoded_credentials_file(self):
        """Create the encoded credentials file with the provided credentials"""
        credentials = {
            'screenscraper': {
                'devid': 'djspirit',
                'devpassword': 'cUIYyyJaImL',
                'ssid': '',  # Add your ssid if you have one
                'sspassword': ''  # Add your sspassword if you have one
            }
        }
        
        # Encode and save
        encoded_data = self._encode_credentials(credentials)
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.encoded_credentials_file), exist_ok=True)
        
        with open(self.encoded_credentials_file, 'w') as f:
            f.write(encoded_data)
        
        print("Encoded credentials file created successfully")
        print(f"File saved to: {self.encoded_credentials_file}")
        
        # Show the encoded content (for verification)
        print(f"Encoded content: {encoded_data[:50]}...")

# Global instance
credential_manager = CredentialManager()
