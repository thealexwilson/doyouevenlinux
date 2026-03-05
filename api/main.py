import json
import os
from collections import Counter
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse

load_dotenv()

from vapor.api_interface import async_get, get_steam_user_data
from vapor.exceptions import InvalidIDError, PrivateAccountError, UnauthorizedError

from api.cache_miss_logger import log_cache_misses

app = FastAPI(title="doyouevenlinux")

STEAM_API_KEY = os.environ.get("STEAM_API_KEY", "")
TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
PROTONDB_SUMMARY_PATH = Path(__file__).resolve().parent.parent / "protondb_summary.json"

MAX_FALLBACK_FETCHES_PER_REQUEST = 5

# PHASE 1: In-memory caches (persist across requests in same function instance)
_protondb_cache: dict[str, str] | None = None
_anticheat_cache: dict[str, str] | None = None
_protondb_fallback_cache: dict[str, str] = {}


async def get_protondb_cache() -> dict[str, str]:
    """Load ProtonDB summary from local JSON file (generated from games_list.json)."""
    global _protondb_cache
    if _protondb_cache is not None:
        return _protondb_cache
    
    try:
        # Load from static file instead of API (API endpoint no longer exists)
        with open(PROTONDB_SUMMARY_PATH, 'r') as f:
            _protondb_cache = json.load(f)
        return _protondb_cache
    except Exception as e:
        print(f"Error loading ProtonDB summary: {e}")
        _protondb_cache = {}
        return {}


async def fetch_protondb_rating_fallback(app_id: str) -> str:
    """
    Fetch ProtonDB rating from mirror API for a single game.
    Aggregates multiple reports into most common tier rating.
    """
    try:
        url = f"https://protondb.max-p.me/games/{app_id}/reports"
        response = await async_get(url)
        
        if response.status != 200:
            return "pending"
        
        reports = json.loads(response.data)
        if not reports:
            return "pending"
        
        ratings = [r.get('rating', '').lower() for r in reports if r.get('rating')]
        if not ratings:
            return "pending"
        
        most_common = Counter(ratings).most_common(1)[0][0]
        valid_tiers = ['platinum', 'gold', 'silver', 'bronze', 'borked']
        return most_common if most_common in valid_tiers else "pending"
    except Exception as e:
        print(f"Fallback fetch failed for {app_id}: {e}")
        return "pending"


async def get_protondb_rating_with_fallback(
    app_id: str, 
    protondb_cache: dict[str, str],
    fallback_count: dict[str, int],
    missing_games: list[str]
) -> str:
    """
    Three-tier lookup for ProtonDB ratings with rate limiting.
    
    Tier 1: Static cache (30k games, instant)
    Tier 2: In-memory fallback cache (games fetched this session)
    Tier 3: Fetch from mirror API (rate limited to 5 per request)
    """
    global _protondb_fallback_cache
    
    if app_id in protondb_cache:
        return protondb_cache[app_id]
    
    if app_id in _protondb_fallback_cache:
        return _protondb_fallback_cache[app_id]
    
    if fallback_count['count'] < MAX_FALLBACK_FETCHES_PER_REQUEST:
        fallback_count['count'] += 1
        rating = await fetch_protondb_rating_fallback(app_id)
        _protondb_fallback_cache[app_id] = rating
        print(f"Fetched fallback rating for {app_id}: {rating}")
        return rating
    else:
        missing_games.append(app_id)
        return "pending"


async def get_anticheat_cache() -> dict[str, str]:
    """Fetch anti-cheat data and cache in memory for function instance lifetime."""
    global _anticheat_cache
    if _anticheat_cache is not None:
        return _anticheat_cache
    
    try:
        data = await async_get(
            'https://raw.githubusercontent.com/AreWeAntiCheatYet/AreWeAntiCheatYet/master/games.json'
        )
        if data.status != 200:
            _anticheat_cache = {}
            return {}
        
        games = json.loads(data.data)
        # Build app_id -> status mapping
        _anticheat_cache = {}
        for game in games:
            if 'steam' in game.get('storeIds', {}):
                app_id = str(game['storeIds']['steam'])
                status = game.get('status', 'BLANK')
                # Map to frontend format
                if status == 'Supported':
                    _anticheat_cache[app_id] = 'supported'
                elif status == 'Denied':
                    _anticheat_cache[app_id] = 'denied'
                else:
                    _anticheat_cache[app_id] = 'unknown'
        return _anticheat_cache
    except Exception as e:
        print(f"Error fetching anti-cheat cache: {e}")
        _anticheat_cache = {}
        return {}


@app.get("/", response_class=HTMLResponse)
async def index():
    html = (TEMPLATES_DIR / "index.html").read_text()
    return HTMLResponse(content=html)


@app.get("/api/check/{steam_id}")
async def check_library(steam_id: str):
    if not STEAM_API_KEY:
        raise HTTPException(status_code=500, detail="Steam API key not configured")

    protondb_data = await get_protondb_cache()
    anticheat_data = await get_anticheat_cache()

    try:
        user_data = await get_steam_user_data(STEAM_API_KEY, steam_id)
    except InvalidIDError:
        raise HTTPException(status_code=400, detail="Invalid Steam ID")
    except UnauthorizedError:
        raise HTTPException(status_code=401, detail="Invalid Steam API key")
    except PrivateAccountError:
        raise HTTPException(status_code=403, detail="Steam profile is private. Set your profile and game details to public.")

    fallback_count = {'count': 0}
    missing_games = []
    
    games = []
    for game in user_data.game_ratings:
        # If game is native Linux, keep that rating
        if game.rating == "native":
            rating = "native"
        else:
            # Otherwise fetch from ProtonDB
            rating = await get_protondb_rating_with_fallback(
                game.app_id, 
                protondb_data,
                fallback_count,
                missing_games
            )
        
        games.append({
            "appid": game.app_id,
            "name": game.name,
            "rating": rating,
            "playtime_minutes": game.playtime,
            "anticheat": anticheat_data.get(game.app_id, "unknown"),
        })
    
    if fallback_count['count'] > 0:
        print(f"Fetched {fallback_count['count']} ratings via fallback API")
    
    if missing_games:
        print(f"WARNING: {len(missing_games)} games not in cache, rate limit reached. Missing: {missing_games[:10]}")
        log_cache_misses(missing_games, steam_id)

    return {
        "games": games,
        "user_average": user_data.user_average,
        "total_games": len(games),
    }