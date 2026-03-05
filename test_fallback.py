#!/usr/bin/env python3
"""
Quick test script to verify ProtonDB fallback implementation.
Tests both static cache hits and fallback API fetching.
"""
import asyncio
import json
from api.main import (
    get_protondb_cache,
    fetch_protondb_rating_fallback,
    get_protondb_rating_with_fallback
)


async def test_implementation():
    print("=" * 60)
    print("ProtonDB Fallback Implementation Test")
    print("=" * 60)
    
    # Test 1: Load static cache
    print("\n1. Testing static cache loading...")
    cache = await get_protondb_cache()
    print(f"   ✓ Loaded {len(cache)} games from static cache")
    
    # Test 2: Static cache hit (game in our 30k dataset)
    print("\n2. Testing static cache hit...")
    test_game_in_cache = "219990"  # Grim Dawn
    if test_game_in_cache in cache:
        print(f"   ✓ Game {test_game_in_cache} found in cache: {cache[test_game_in_cache]}")
    else:
        print(f"   ✗ Game {test_game_in_cache} NOT in cache (unexpected)")
    
    # Test 3: Fallback API for missing game
    print("\n3. Testing fallback API fetch...")
    test_game_not_in_cache = "999999"  # Non-existent game
    rating = await fetch_protondb_rating_fallback(test_game_not_in_cache)
    print(f"   ✓ Fallback fetch for game {test_game_not_in_cache}: {rating}")
    
    # Test 4: Fallback API for known good game
    print("\n4. Testing fallback API with known game...")
    test_known_game = "352620"  # Porcunipine (should be Platinum)
    rating = await fetch_protondb_rating_fallback(test_known_game)
    print(f"   ✓ Fallback fetch for game {test_known_game}: {rating}")
    if rating == "platinum":
        print(f"   ✓ Rating matches expected (Platinum)")
    else:
        print(f"   ! Rating is {rating}, expected Platinum")
    
    # Test 5: Rate limiting
    print("\n5. Testing rate limiting...")
    fallback_count = {'count': 0}
    missing_games = []
    
    # Test with 6 games not in cache (should only fetch 5)
    fake_games = ["999990", "999991", "999992", "999993", "999994", "999995"]
    fetched = []
    for game_id in fake_games:
        rating = await get_protondb_rating_with_fallback(
            game_id,
            cache,
            fallback_count,
            missing_games
        )
        fetched.append(rating)
    
    print(f"   ✓ Fetched {fallback_count['count']} games (max 5)")
    print(f"   ✓ Games marked as missing: {len(missing_games)}")
    
    if fallback_count['count'] == 5 and len(missing_games) == 1:
        print(f"   ✓ Rate limiting working correctly!")
    else:
        print(f"   ✗ Rate limiting issue: fetched={fallback_count['count']}, missing={len(missing_games)}")
    
    # Test 6: Cache miss logger
    print("\n6. Testing cache miss logger...")
    from api.cache_miss_logger import log_cache_misses
    log_cache_misses(["999990", "999991"], "test_user_12345")
    print(f"   ✓ Logged cache misses (check cache_miss_log.json)")
    
    print("\n" + "=" * 60)
    print("All tests complete! ✓")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_implementation())
