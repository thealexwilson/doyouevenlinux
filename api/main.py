import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from vapor.api_interface import get_steam_user_data
from vapor.exceptions import InvalidIDError, PrivateAccountError, UnauthorizedError
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="doyouevenlinux")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

STEAM_API_KEY = os.environ.get("STEAM_API_KEY", "")


@app.get("/")
async def root():
    return {"status": "doyouevenlinux is live"}


@app.get("/api/check/{steam_id}")
async def check_library(steam_id: str):
    if not STEAM_API_KEY:
        raise HTTPException(status_code=500, detail="Steam API key not configured")

    try:
        user_data = await get_steam_user_data(STEAM_API_KEY, steam_id)
    except InvalidIDError:
        raise HTTPException(status_code=400, detail="Invalid Steam ID")
    except UnauthorizedError:
        raise HTTPException(status_code=401, detail="Invalid Steam API key")
    except PrivateAccountError:
        raise HTTPException(status_code=403, detail="Steam profile is private")

    games = [
        {
            "appid": game.app_id,
            "name": game.name,
            "rating": game.rating,
            "playtime_minutes": game.playtime,
        }
        for game in user_data.game_ratings
    ]

    return {
        "games": games,
        "user_average": user_data.user_average,
        "total_games": len(games),
    }