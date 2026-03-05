from fastapi import APIRouter, Request, HTTPException
from vapor.cache_handler import Cache
from vapor.api_interface import prefill_protondb_cache  # the job function we wrote

router = APIRouter()

CRON_SECRET = "your_secret_here"

@router.get("/")
async def update_cache(request: Request):
    # check secret
    auth = request.headers.get("Authorization")
    if auth != f"Bearer {CRON_SECRET}":
        raise HTTPException(status_code=401, detail="Unauthorized")

    cache = Cache().load_cache()
    await prefill_protondb_cache(cache)
    return {"ok": True, "message": "ProtonDB cache updated"}