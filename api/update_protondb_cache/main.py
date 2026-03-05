from dotenv import load_dotenv

load_dotenv()

import os

from fastapi import FastAPI, HTTPException, Request

# PHASE 1: Imports commented out - not using Redis or refresh function
# from vapor.redis_cache import get_protondb_rating, set_cached_rating, redis_client
# from vapor.api_interface import refresh_protondb_cache

app = FastAPI(title="Update ProtonDB Cache")
CRON_SECRET = os.environ.get("CRON_SECRET", "")


@app.get("/api/update_protondb_cache")
async def update_protondb_cache(request: Request):
    auth = request.headers.get("Authorization")
    if auth != f"Bearer {CRON_SECRET}":
        raise HTTPException(status_code=401, detail="Unauthorized")

    # PHASE 1: Cron job disabled - not using Redis to avoid request limit
    # await refresh_protondb_cache()
    
    # PHASE 2: Re-enable after Redis is properly populated
    return {"status": "disabled_phase1", "message": "Cron job disabled in Phase 1 - using in-memory caching"}