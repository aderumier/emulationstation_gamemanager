import sys
import os
import json
import logging

# Add current directory to path
sys.path.append(os.getcwd())

from app import load_mobygames_platform_mapping, extract_mobygames_media_fields, load_mobygames_service, load_scrappers_config, download_mobygames_media_from_url
from app import load_config, ROMS_FOLDER

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_persistence():
    # Load service and config
    service = load_mobygames_service()
    platform_mapping = load_mobygames_platform_mapping()
    scrappers_config = load_scrappers_config()
    mobygames_config = scrappers_config.get('mobygames', {})
    
    # Simulate the task variables
    system_name = 'win98'
    game_name = 'The Scent of War I. - Damn Those Demons'
    mobygames_id = 48794
    selected_media_fields = ['boxart', 'boxback', 'cartridge', 'image', 'titleshot']
    overwrite_media_fields = True
    
    print(f"🔧 DEBUG: mobygames_config keys: {list(mobygames_config.keys())}")
    print(f"🔧 DEBUG: image_type_mappings keys: {list(mobygames_config.get('image_type_mappings', {}).keys())}")
    
    # Get game from service
    mobygames_game = service.find_game_by_id(system_name, mobygames_id)
    if not mobygames_game:
        # Try finding in 'Windows' directly
        mobygames_game = service.databases.get('Windows', {}).get(mobygames_id)
    
    if not mobygames_game:
        print("❌ Could not find game.")
        return

    # Add system info normally added in the loop
    mobygames_game['system'] = 'Windows'
    mobygames_game['system_name'] = system_name
    
    # Mock game object
    game = {'path': '/home/aderumier/roms/win98/scent.zip', 'name': game_name}
    
    # Processing logic
    print(f"🖼️  Processing media for '{game_name}' (ID: {mobygames_id})")
    
    image_type_mappings = mobygames_config.get('image_type_mappings', {})
    if selected_media_fields:
        image_type_mappings = {k: v for k, v in image_type_mappings.items() if k in selected_media_fields}
    
    # Ensure test directory exists
    system_path = os.path.join(ROMS_FOLDER, system_name)
    os.makedirs(system_path, exist_ok=True)
    
    fields_to_process = []
    for gamelist_field in selected_media_fields:
        current_media_value = game.get(gamelist_field, '')
        field_is_empty = not current_media_value
        
        if not field_is_empty and not overwrite_media_fields:
            continue
        
        fields_to_process.append(gamelist_field)
    
    print(f"🔧 DEBUG: fields_to_process: {fields_to_process}")
    
    if fields_to_process:
        media_fields = extract_mobygames_media_fields(mobygames_game, system_name, image_type_mappings, platform_mapping, service)
        print(f"🔧 DEBUG: extract_mobygames_media_fields result: {list(media_fields.keys()) if media_fields else 'None'}")
        
        if media_fields:
            for gamelist_field, media_options in media_fields.items():
                if gamelist_field not in fields_to_process:
                    continue
                
                print(f"Processing {gamelist_field}...")
                for media_option in media_options:
                    print(f"  Option: {media_option}")
                    # Try download
                    target_path = f"/tmp/test_download_{gamelist_field}.jpg"
                    try:
                        success = download_mobygames_media_from_url(
                            media_option.get('page_url', ''),
                            target_path
                        )
                        print(f"  Download success: {success}")
                        if success:
                            break
                    except Exception as e:
                        print(f"  Download error: {e}")

if __name__ == "__main__":
    test_persistence()
