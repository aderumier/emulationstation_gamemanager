import requests
import json

url = "http://localhost:5000/api/fanart-search/stream"
data = {
    "game_name": "mario",
    "system_name": "snes",
    "direct_match": False,
    "scraper": "all",
    "field_type": "fanart"
}

with requests.post(url, json=data, stream=True) as r:
    for line in r.iter_lines():
        if line:
            print(line.decode('utf-8'))
