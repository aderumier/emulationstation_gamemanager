import json
import urllib.request
import os

VPSDB_URL = "https://virtualpinballspreadsheet.github.io/vps-db/db/vpsdb.json"
VPINMDB_URL = "https://raw.githubusercontent.com/superhac/vpinmediadb/main/vpinmdb.json"
# Try to resolve relative to running script to ensure the path is correct
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUTPUT_FILE = os.path.join(BASE_DIR, "var", "db", "custom", "vpinball.json")

def fetch_json(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as response:
        return json.loads(response.read().decode())

def main():
    print("Fetching vpsdb.json...")
    vpsdb = fetch_json(VPSDB_URL)
    print("Fetching vpinmdb.json...")
    vpinmdb = fetch_json(VPINMDB_URL)
    
    print("Processing data...")
    custom_db = {}
    
    for game in vpsdb:
        game_id = game.get("id")
        if not game_id:
            continue
            
        media = vpinmdb.get(game_id)
        
        recent_table = None
        max_updated = -1
        for table in game.get("tableFiles", []):
            updated_at = table.get("updatedAt", 0)
            if updated_at > max_updated:
                max_updated = updated_at
                recent_table = table
                
        custom_game = {
            "id": game_id,
        }
        
        # name -> name
        if "name" in game:
            custom_game["name"] = game["name"]
            
        # manufacturer -> publisher
        if "manufacturer" in game:
            custom_game["publisher"] = game["manufacturer"]
            
        # year --> release_date: convert to 01/01/<year>
        if "year" in game:
            custom_game["release_date"] = f"01/01/{game['year']}"
            
        # players -> nbplayers
        if "players" in game:
            custom_game["nbplayers"] = str(game["players"])
            
        # authors -> developer
        if recent_table:
            authors = recent_table.get("authors", [])
            if authors:
                custom_game["developer"] = ",".join(authors)
                
        # Check media fields from vpinmdb.json
        if media:
            # table_video (in 1k format) -> video
            if "1k" in media and "table_video" in media["1k"]:
                custom_game["video"] = media["1k"]["table_video"]
                
            # flyer -> boxfront
            if "flyer" in media:
                custom_game["boxfront"] = media["flyer"]
                
            # cab -> cartridge
            if "cab" in media:
                custom_game["cartridge"] = media["cab"]
                
            # wheel -> marquee
            if "wheel" in media:
                custom_game["marquee"] = media["wheel"]
                
            # table -> screenshot
            if "1k" in media and "table" in media["1k"]:
                custom_game["screenshot"] = media["1k"]["table"]
                
        custom_db[game_id] = custom_game
        
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(custom_db, f, indent=2, ensure_ascii=False)
        
    print(f"Successfully generated {OUTPUT_FILE} with {len(custom_db)} games.")

if __name__ == "__main__":
    main()
