# populate_upstash_from_json.py
import json

from dotenv import load_dotenv
from upstash_redis import Redis

load_dotenv()

redis_client = Redis.from_env()

# Load the JSON file
with open("default_games_list.json", "r", encoding="utf-8") as f:
    games = json.load(f)

print(f"Populating {len(games)} games into Upstash Redis...")

for game in games:
    app_id = game["app"]["steam"]["appId"]
    # pick a rating field; here we use verdict from the first response
    verdict = game.get("responses", {}).get("verdict", "pending")
    
    # Write to Upstash
    redis_client.set(f"protondb:{app_id}", verdict)
    print(f"Set protondb:{app_id} = {verdict}")

print("Done.")