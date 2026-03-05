"""
ProtonDB Cache Miss Logging

Tracks which games are frequently not in our 30k static cache.
This helps identify which games should be added to improve coverage.
"""
import json
from datetime import datetime
from pathlib import Path

CACHE_MISS_LOG_PATH = Path(__file__).resolve().parent.parent / "cache_miss_log.json"


def log_cache_misses(missing_games: list[str], user_steam_id: str) -> None:
    """
    Log games that were not found in static cache.
    
    Format: {
        "app_id": {
            "count": 5,
            "first_seen": "2026-03-05T10:30:00",
            "last_seen": "2026-03-05T15:45:00",
            "users": ["76561197960287930", ...]
        }
    }
    """
    if not missing_games:
        return
    
    try:
        if CACHE_MISS_LOG_PATH.exists():
            with open(CACHE_MISS_LOG_PATH, 'r') as f:
                log_data = json.load(f)
        else:
            log_data = {}
        
        timestamp = datetime.utcnow().isoformat()
        
        for app_id in missing_games:
            if app_id not in log_data:
                log_data[app_id] = {
                    "count": 0,
                    "first_seen": timestamp,
                    "last_seen": timestamp,
                    "users": []
                }
            
            log_data[app_id]["count"] += 1
            log_data[app_id]["last_seen"] = timestamp
            
            if user_steam_id not in log_data[app_id]["users"]:
                log_data[app_id]["users"].append(user_steam_id)
        
        with open(CACHE_MISS_LOG_PATH, 'w') as f:
            json.dump(log_data, f, indent=2)
        
        print(f"Logged {len(missing_games)} cache misses for user {user_steam_id}")
    except Exception as e:
        print(f"Failed to log cache misses: {e}")


def get_top_missing_games(limit: int = 20) -> list[tuple[str, int]]:
    """
    Get the most frequently missed games.
    Returns list of (app_id, count) tuples.
    """
    try:
        if not CACHE_MISS_LOG_PATH.exists():
            return []
        
        with open(CACHE_MISS_LOG_PATH, 'r') as f:
            log_data = json.load(f)
        
        sorted_games = sorted(
            log_data.items(),
            key=lambda x: x[1]["count"],
            reverse=True
        )
        
        return [(app_id, data["count"]) for app_id, data in sorted_games[:limit]]
    except Exception as e:
        print(f"Failed to get top missing games: {e}")
        return []
