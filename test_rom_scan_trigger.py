#!/usr/bin/env python3
"""
Script to trigger ROM scan and check results
"""
import requests
import time
import json
import os

def trigger_rom_scan():
    """Trigger ROM scan via API and check results"""
    
    print("🚀 Triggering ROM scan for windows system")
    
    # Wait for app to be ready
    print("⏳ Waiting for app to be ready...")
    time.sleep(3)
    
    # Trigger ROM scan
    try:
        response = requests.post(
            "http://localhost:5000/api/rom-system/windows/scan-roms",
            json={},
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ ROM scan triggered successfully")
            print(f"📊 Response: {json.dumps(result, indent=2)}")
            
            # Wait for scan to complete
            print("⏳ Waiting for scan to complete...")
            time.sleep(10)
            
            # Check if gamelist was created
            gamelist_path = "var/gamelists/windows/gamelist.xml"
            if os.path.exists(gamelist_path):
                print(f"✅ Gamelist created: {gamelist_path}")
                
                # Read and analyze gamelist
                with open(gamelist_path, 'r') as f:
                    content = f.read()
                
                # Count games
                game_count = content.count('<game>')
                print(f"📊 Games in gamelist: {game_count}")
                
                # Check if gameX.wsquashfs is in the gamelist
                if 'gameX.wsquashfs' in content:
                    print("✅ gameX.wsquashfs found in gamelist!")
                else:
                    print("❌ gameX.wsquashfs NOT found in gamelist")
                
                # Show first few games
                print(f"\n📋 First 5 games in gamelist:")
                lines = content.split('\n')
                game_lines = [line for line in lines if '<path>' in line]
                for i, line in enumerate(game_lines[:5]):
                    print(f"  {i+1}. {line.strip()}")
                
            else:
                print(f"❌ Gamelist not created: {gamelist_path}")
                
        else:
            print(f"❌ ROM scan failed: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Error triggering ROM scan: {e}")

if __name__ == "__main__":
    trigger_rom_scan()
