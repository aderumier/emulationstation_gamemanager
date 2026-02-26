#!/usr/bin/env python3
import os
import sys
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)

# Add current directory to path
sys.path.append(os.getcwd())

try:
    from steam_service import SteamService
    print("✅ Successfully imported SteamService")
except Exception as e:
    print(f"❌ Failed to import SteamService: {e}")
    sys.exit(1)

try:
    print("🔧 Instantiating SteamService...")
    service = SteamService()
    print(f"✅ SteamService instantiated. base_dir={service.base_dir}")
    
    print("🔧 Calling save_api_key...")
    result = service.save_api_key("test_key_123")
    print(f"✅ save_api_key returned: {result}")
    
except Exception as e:
    print(f"❌ Error caught during execution: {e}")
    import traceback
    traceback.print_exc()
