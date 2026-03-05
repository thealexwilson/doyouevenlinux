# api/update_protondb_cache/main.py
import os
import asyncio
from fastapi import FastAPI, HTTPException, Request

from vapor.cache_handler import Cache
from vapor.api_interface import refresh_protondb_cache

app = FastAPI(title="Update ProtonDB Cache")

CRON_SECRET = os.environ.get("CRON_SECRET", "")


@app.get("/api/update_protondb_cache")
async def update_protondb_cache(request: Request):
    """
    Update cached ProtonDB ratings for games missing in the cache.
    Designed to be triggered by Vercel Cron Jobs.
    """
    # Authorization check for Vercel Cron
    auth = request.headers.get("Authorization")
    if auth != f"Bearer {CRON_SECRET}":
        raise HTTPException(status_code=401, detail="Unauthorized")

    cache = Cache().load_cache()
    # refresh_protondb_cache now handles only missing/unknown ratings in parallel
    await refresh_protondb_cache(cache)

    return {"status": "completed"}