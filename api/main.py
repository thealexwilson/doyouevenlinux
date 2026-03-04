import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse

load_dotenv()

from vapor.api_interface import get_steam_user_data
from vapor.exceptions import InvalidIDError, PrivateAccountError, UnauthorizedError

app = FastAPI(title="doyouevenlinux")

STEAM_API_KEY = os.environ.get("STEAM_API_KEY", "")
TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"


@app.get("/", response_class=HTMLResponse)
async def index():
    html = (TEMPLATES_DIR / "index.html").read_text()
    return HTMLResponse(content=html)


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
        raise HTTPException(status_code=403, detail="Steam profile is private. Set your profile and game details to public.")

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