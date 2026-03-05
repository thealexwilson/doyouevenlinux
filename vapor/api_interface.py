"""Steam and ProtonDB API helper functions."""

from __future__ import annotations

import json
from typing import cast

import aiohttp

from vapor.cache_handler import Cache
# PHASE 1: Redis functions commented out to avoid request limit
# from vapor.redis_cache import get_protondb_rating, set_cached_rating, redis_client
from vapor.data_structures import (
    HTTP_BAD_REQUEST,
    HTTP_FORBIDDEN,
    HTTP_SUCCESS,
    HTTP_UNAUTHORIZED,
    RATING_DICT,
    STEAM_USER_ID_LENGTH,
    AntiCheatAPIResponse,
    AntiCheatData,
    AntiCheatStatus,
    Game,
    Response,
    SteamAPINameResolutionResponse,
    SteamAPIPlatformsResponse,
    SteamAPIUserDataResponse,
    SteamUserData,
)
from vapor.exceptions import InvalidIDError, PrivateAccountError, UnauthorizedError


async def refresh_protondb_cache():
    """
    PHASE 1: Disabled - Not using Redis to avoid hitting request limit.
    PHASE 2: Will be re-enabled with optimized bulk update after Redis limit resets.
    
    Original function refreshed ProtonDB cache for all games missing a rating in Upstash Redis.
    """
    # PHASE 1: Completely disabled
    return
    
    # PHASE 2: Re-enable with optimized bulk refresh
    # from vapor.redis_cache import redis_client, set_cached_rating
    # 
    # keys = redis_client.keys("protondb:*")
    # cached_app_ids = {key.split(":")[1] for key in keys}
    # 
    # data = await async_get("https://www.protondb.com/api/v1/reports/summaries.json")
    # if data.status != HTTP_SUCCESS:
    #     return
    # 
    # try:
    #     protondb_data = json.loads(data.data)
    # except json.JSONDecodeError:
    #     return
    # 
    # # Use bulk data directly instead of individual API calls
    # for app_id, game_data in protondb_data.items():
    #     if app_id not in cached_app_ids:
    #         tier = game_data.get("tier", "pending")
    #         # Check if native (requires Steam API call)
    #         if await check_game_is_native(app_id):
    #             tier = "native"
    #         set_cached_rating(app_id, tier)
    #         print(f"Set rating for {app_id}: {tier}")


async def async_get(url: str) -> Response:
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.9',
    }
    async with aiohttp.ClientSession(headers=headers) as session, session.get(url) as response:
        return Response(data=await response.text(), status=response.status)


async def check_game_is_native(app_id: str) -> bool:
    data = await async_get(
        f'https://store.steampowered.com/api/appdetails?appids={app_id}&filters=platforms',
    )
    if data.status != HTTP_SUCCESS:
        return False

    json_data = cast(dict[str, SteamAPIPlatformsResponse], json.loads(data.data))

    if str(app_id) not in json_data:
        return False

    game_data = json_data[str(app_id)]
    return game_data.get('success', False) and game_data['data']['platforms'].get('linux', False)


async def get_anti_cheat_data() -> Cache | None:
    """Fetch anti-cheat data and store in local JSON cache."""
    cache = Cache()
    if cache.has_anticheat_cache:
        return cache

    data = await async_get(
        'https://raw.githubusercontent.com/AreWeAntiCheatYet/AreWeAntiCheatYet/master/games.json',
    )
    if data.status != HTTP_SUCCESS:
        return None

    try:
        anti_cheat_data = cast(list[AntiCheatAPIResponse], json.loads(data.data))
    except json.JSONDecodeError:
        return None

    deserialized_data = [
        AntiCheatData(app_id=game['storeIds']['steam'], status=AntiCheatStatus(game['status']))
        for game in anti_cheat_data
        if 'steam' in game['storeIds']
    ]

    cache.update_cache(anti_cheat_list=deserialized_data)
    return cache


async def get_game_average_rating(app_id: str) -> str:
    """
    PHASE 1: Skip Redis and ProtonDB API calls - ratings fetched in-memory in api/main.py
    This function returns 'pending' as placeholder. Actual rating lookup happens in API layer.
    """
    # PHASE 1: Bypass Redis to avoid hitting request limit
    # cached_rating = get_protondb_rating(app_id)
    # if cached_rating is not None:
    #     return cached_rating

    # Check if the game is native Linux (still needed for accurate ratings)
    if await check_game_is_native(app_id):
        return "native"
    
    # PHASE 1: Don't fetch from ProtonDB API - will be looked up from memory in api/main.py
    return "pending"
    
    # PHASE 2: Re-enable after populating Redis properly
    # rating = "pending"
    # data = await async_get(f'https://www.protondb.com/api/v1/reports/summaries/{app_id}.json')
    # if data.status == HTTP_SUCCESS:
    #     try:
    #         json_data = json.loads(data.data)
    #         rating = json_data.get("tier", "pending")
    #     except json.JSONDecodeError:
    #         rating = "pending"
    # set_cached_rating(app_id, rating)
    # return rating


async def resolve_vanity_name(api_key: str, name: str) -> str:
    data = await async_get(
        f'https://api.steampowered.com/ISteamUser/ResolveVanityURL/v0001/?key={api_key}&vanityurl={name}',
    )

    if data.status == HTTP_FORBIDDEN:
        raise UnauthorizedError

    user_data = cast(SteamAPINameResolutionResponse, json.loads(data.data))
    if 'response' not in user_data or user_data['response']['success'] != 1:
        raise InvalidIDError

    return user_data['response']['steamid']


async def get_steam_user_data(api_key: str, user_id: str) -> SteamUserData:
    """Fetch a Steam user's games and ProtonDB ratings."""
    if len(user_id) != STEAM_USER_ID_LENGTH or not user_id.startswith('76561198'):
        try:
            user_id = await resolve_vanity_name(api_key, user_id)
        except UnauthorizedError as e:
            raise UnauthorizedError from e
        except InvalidIDError:
            pass

    data = await async_get(
        f'http://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/?key={api_key}&steamid={user_id}&format=json&include_appinfo=1&include_played_free_games=1',
    )
    if data.status == HTTP_BAD_REQUEST:
        raise InvalidIDError
    if data.status == HTTP_UNAUTHORIZED:
        raise UnauthorizedError

    user_data = cast(SteamAPIUserDataResponse, json.loads(data.data))
    return await _parse_steam_user_games(user_data)


async def _parse_steam_user_games(data: SteamAPIUserDataResponse) -> SteamUserData:
    game_data = data['response']
    if 'games' not in game_data:
        raise PrivateAccountError

    games = game_data['games']
    game_ratings: list[Game] = []

    # Check each game for native Linux support
    for game in games:
        app_id = str(game['appid'])
        # Check if game has native Linux support
        is_native = await check_game_is_native(app_id)
        rating = "native" if is_native else "pending"
        
        game_ratings.append(
            Game(
                name=game['name'],
                rating=rating,  # "native" or "pending" (will be replaced with ProtonDB rating in api/main.py)
                playtime=game['playtime_forever'],
                app_id=app_id
            )
        )

    game_ratings.sort(key=lambda x: x.playtime, reverse=True)

    known_game_ratings = [RATING_DICT[g.rating][0] for g in game_ratings if g.rating in RATING_DICT]
    user_average = round(sum(known_game_ratings) / len(known_game_ratings)) if known_game_ratings else 0
    user_average_text = next((k for k, v in RATING_DICT.items() if v[0] == user_average), "Unknown")

    return SteamUserData(game_ratings=game_ratings, user_average=user_average_text)