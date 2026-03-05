from dotenv import load_dotenv
load_dotenv()

import os
from fastapi import FastAPI, HTTPException, Request

from vapor.redis_cache import get_protondb_rating, set_cached_rating, redis_client
from vapor.api_interface import refresh_protondb_cache

app = FastAPI(title="Update ProtonDB Cache")
CRON_SECRET = os.environ.get("CRON_SECRET", "")


@app.get("/api/update_protondb_cache")
async def update_protondb_cache(request: Request):
    auth = request.headers.get("Authorization")
    if auth != f"Bearer {CRON_SECRET}":
        raise HTTPException(status_code=401, detail="Unauthorized")

    # just pass redis_client to your function if needed
    await refresh_protondb_cache()

    return {"status": "completed"}