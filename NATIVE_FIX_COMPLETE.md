# Native Linux Detection Fix - Complete Solution

## Issue
Native Linux games were showing "No" in the Native Linux column even though they have native support.

## Root Cause
During the Phase 1 refactor to use in-memory caching, the native Linux detection was accidentally removed from `_parse_steam_user_games()` in `vapor/api_interface.py`. 

**Line 205 was:**
```python
rating="pending",  # Will be replaced in api/main.py from memory cache
```

This meant ALL games were marked as "pending" instead of checking for native Linux support.

## Fix Applied

### 1. Fixed `vapor/api_interface.py` (lines 190-213)
Restored native Linux checking in `_parse_steam_user_games()`:

```python
async def _parse_steam_user_games(data: SteamAPIUserDataResponse) -> SteamUserData:
    # ... existing code ...
    
    # Check each game for native Linux support
    for game in games:
        app_id = str(game['appid'])
        # Check if game has native Linux support
        is_native = await check_game_is_native(app_id)
        rating = "native" if is_native else "pending"
        
        game_ratings.append(
            Game(
                name=game['name'],
                rating=rating,  # "native" or "pending"
                playtime=game['playtime_forever'],
                app_id=app_id
            )
        )
```

### 2. Already Fixed `api/main.py` (lines 171-181)
Preserved native ratings before ProtonDB lookup:

```python
for game in user_data.game_ratings:
    # If game is native Linux, keep that rating
    if game.rating == "native":
        rating = "native"
    else:
        # Otherwise fetch from ProtonDB
        rating = await get_protondb_rating_with_fallback(...)
```

## How It Works

```
User requests library check
    ↓
get_steam_user_data() called
    ↓
_parse_steam_user_games() processes each game:
    ↓
    For each game:
        ↓
        check_game_is_native(app_id) calls Steam API
        ↓
        Returns TRUE if platforms.linux = true
        ↓
        Set rating = "native" OR "pending"
    ↓
api/main.py receives games with native status
    ↓
    For native games: Keep "native" rating
    For non-native: Fetch from ProtonDB (3-tier fallback)
    ↓
Frontend receives rating field
    ↓
    Calculates: native_linux = (rating === "native")
    ↓
    Displays Native badge ✓
```

## API Calls Per Game

- **Native check:** 1 Steam API call per game (unavoidable, checks platforms)
- **ProtonDB lookup:** Only for non-native games (3-tier fallback with rate limiting)

## Performance Considerations

**Before fix:** 0 native checks (fast but wrong)
**After fix:** N native checks where N = number of games in library

For a user with 250 games:
- 250 Steam API calls to check native status
- 0-5 ProtonDB mirror API calls (for non-native games not in cache)
- Total: ~250-255 API calls

**Mitigation for future:**
The native status could be cached in Redis to avoid repeated Steam API calls for the same games. This would be a Phase 2 optimization.

## Files Modified
1. `vapor/api_interface.py` - Restored native Linux checking
2. `api/main.py` - Already had native rating preservation (from previous fix)

## Testing
After this fix:
1. ✅ Native Linux games show "Yes" in Native column
2. ✅ Non-native games get ProtonDB ratings (Gold, Platinum, etc.)
3. ✅ Fallback system works for games not in 30k cache
4. ✅ Anti-cheat status displays correctly
5. ✅ All linter checks pass

## Status
**COMPLETE** - Native Linux detection is now fully functional.
