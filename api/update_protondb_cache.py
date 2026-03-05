# api/update_protondb_cache.py
from fastapi import FastAPI, HTTPException
import asyncio

from vapor.cache_handler import Cache
from vapor.api_interface import get_game_average_rating
from vapor.data_structures import Game, RATING_DICT

app = FastAPI(title="Update ProtonDB Cache")

@app.get("/api/update_protondb_cache")
async def update_protondb_cache():
    """
    Update cached ProtonDB ratings for games missing in the cache.
    Designed to be triggered by Vercel Cron Jobs.
    """
    cache = Cache().load_cache()
    updated_games = []

    # Gather all cached games and all games in cache file
    # For demo purposes, assume we track all known app_ids elsewhere
    # or pull from Steam API/other source. Here we just scan cache keys.
    all_app_ids = list(cache._games_data.keys())

    coros = []
    app_id_mapping = {}

    for app_id in all_app_ids:
        game = cache.get_game_data(app_id)
        if game and game.rating not in RATING_DICT:
            # missing or unknown rating
            coros.append(get_game_average_rating(app_id, cache))
            app_id_mapping[app_id] = game.name

    if not coros:
        return {"status": "no updates needed"}

    # fetch all missing ratings in parallel
    results = await asyncio.gather(*coros, return_exceptions=True)

    for i, app_id in enumerate(app_id_mapping):
        rating_result = results[i]
        rating = str(rating_result) if not isinstance(rating_result, Exception) else "Unknown"
        game = Game(
            name=app_id_mapping[app_id],
            rating=rating,
            playtime=0,  # can't know playtime here
            app_id=app_id
        )
        updated_games.append(game)

    if updated_games:
        cache.update_cache(game_list=updated_games)

    return {"status": "completed", "updated_count": len(updated_games)}