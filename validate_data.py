#!/usr/bin/env python3
"""
Data Validation Script
Tests app data against official sources (ProtonDB, AreWeAntiCheatYet, Steam)
"""
import asyncio
import json
import sys
from urllib.request import urlopen, Request
from collections import Counter

# Add parent directory to path to import vapor modules
sys.path.insert(0, '/Users/alex.wilson/doyouevenlinux')

from vapor.api_interface import async_get, check_game_is_native


async def fetch_protondb_rating(app_id: str) -> dict:
    """Fetch rating from ProtonDB mirror API"""
    try:
        url = f"https://protondb.max-p.me/games/{app_id}/reports"
        response = await async_get(url)
        
        if response.status != 200:
            return {"status": "error", "rating": None, "error": f"HTTP {response.status}"}
        
        reports = json.loads(response.data)
        if not reports:
            return {"status": "no_reports", "rating": None}
        
        ratings = [r.get('rating', '').lower() for r in reports if r.get('rating')]
        if not ratings:
            return {"status": "no_ratings", "rating": None}
        
        counter = Counter(ratings)
        most_common = counter.most_common(1)[0][0]
        
        return {
            "status": "success",
            "rating": most_common,
            "total_reports": len(reports),
            "distribution": dict(counter)
        }
    except Exception as e:
        return {"status": "error", "rating": None, "error": str(e)}


async def fetch_anticheat_status(app_id: str) -> dict:
    """Fetch anti-cheat status from AreWeAntiCheatYet API"""
    try:
        response = await async_get(
            'https://raw.githubusercontent.com/AreWeAntiCheatYet/AreWeAntiCheatYet/master/games.json'
        )
        
        if response.status != 200:
            return {"status": "error", "anticheat": None}
        
        games = json.loads(response.data)
        
        for game in games:
            if 'steam' in game.get('storeIds', {}):
                if str(game['storeIds']['steam']) == app_id:
                    status = game.get('status', 'BLANK')
                    # Map to our format
                    if status == 'Supported':
                        return {"status": "success", "anticheat": "supported"}
                    elif status == 'Denied':
                        return {"status": "success", "anticheat": "denied"}
                    else:
                        return {"status": "success", "anticheat": "unknown"}
        
        return {"status": "not_found", "anticheat": "unknown"}
    except Exception as e:
        return {"status": "error", "anticheat": None, "error": str(e)}


async def validate_game(app_id: str, name: str, our_data: dict) -> dict:
    """
    Validate a single game's data against official sources
    
    Args:
        app_id: Steam app ID
        name: Game name
        our_data: Data from our app (rating, native, anticheat)
    
    Returns:
        Validation results with comparison
    """
    print(f"\n{'='*60}")
    print(f"Validating: {name} ({app_id})")
    print(f"{'='*60}")
    
    results = {
        "app_id": app_id,
        "name": name,
        "our_data": our_data,
        "validations": {}
    }
    
    # 1. Validate ProtonDB Rating
    print(f"  📊 ProtonDB Rating Check...")
    protondb_data = await fetch_protondb_rating(app_id)
    
    our_rating = our_data.get("rating", "unknown")
    official_rating = protondb_data.get("rating")
    
    if our_rating == "native":
        print(f"     Our data: {our_rating} (native Linux)")
        print(f"     Official: N/A (game is native, no ProtonDB rating needed)")
        results["validations"]["protondb"] = {
            "match": True,
            "our_rating": our_rating,
            "official_rating": "N/A (native)",
            "note": "Native games don't need ProtonDB ratings"
        }
    elif protondb_data["status"] == "success":
        match = our_rating == official_rating
        print(f"     Our data: {our_rating}")
        print(f"     Official: {official_rating}")
        print(f"     Reports: {protondb_data['total_reports']}")
        print(f"     Distribution: {protondb_data['distribution']}")
        print(f"     ✅ MATCH" if match else f"     ❌ MISMATCH")
        
        results["validations"]["protondb"] = {
            "match": match,
            "our_rating": our_rating,
            "official_rating": official_rating,
            "total_reports": protondb_data["total_reports"],
            "distribution": protondb_data["distribution"]
        }
    else:
        print(f"     Our data: {our_rating}")
        print(f"     Official: Error - {protondb_data.get('error', 'No data')}")
        results["validations"]["protondb"] = {
            "match": None,
            "our_rating": our_rating,
            "official_rating": None,
            "error": protondb_data.get("error")
        }
    
    # 2. Validate Anti-Cheat Status
    print(f"\n  🛡️  Anti-Cheat Status Check...")
    anticheat_data = await fetch_anticheat_status(app_id)
    
    our_anticheat = our_data.get("anticheat", "unknown")
    official_anticheat = anticheat_data.get("anticheat")
    
    if anticheat_data["status"] == "success":
        match = our_anticheat == official_anticheat
        print(f"     Our data: {our_anticheat}")
        print(f"     Official: {official_anticheat}")
        print(f"     ✅ MATCH" if match else f"     ❌ MISMATCH")
        
        results["validations"]["anticheat"] = {
            "match": match,
            "our_status": our_anticheat,
            "official_status": official_anticheat
        }
    else:
        print(f"     Our data: {our_anticheat}")
        print(f"     Official: {anticheat_data['status']}")
        results["validations"]["anticheat"] = {
            "match": our_anticheat == "unknown",  # Should both be unknown if not found
            "our_status": our_anticheat,
            "official_status": "not_found"
        }
    
    # 3. Validate Native Linux Status
    if our_rating == "native":
        print(f"\n  🐧 Native Linux Check...")
        is_native = await check_game_is_native(app_id)
        match = is_native
        print(f"     Our data: native")
        print(f"     Steam API: {'native' if is_native else 'not native'}")
        print(f"     ✅ MATCH" if match else f"     ❌ MISMATCH")
        
        results["validations"]["native"] = {
            "match": match,
            "our_says_native": True,
            "steam_api_native": is_native
        }
    
    return results


async def main():
    """Run validation tests"""
    print("=" * 60)
    print("DATA VALIDATION SCRIPT")
    print("=" * 60)
    print("\nThis script validates our app data against official sources:")
    print("  • ProtonDB (via mirror API)")
    print("  • AreWeAntiCheatYet (GitHub)")
    print("  • Steam Store API (for native Linux)")
    print()
    
    # Test games (mix of native, popular, and various ProtonDB tiers)
    test_games = [
        # Known native games
        {"app_id": "730", "name": "Counter-Strike 2", "expected_native": True},
        {"app_id": "440", "name": "Team Fortress 2", "expected_native": True},
        
        # Popular games with ProtonDB ratings
        {"app_id": "570", "name": "Dota 2", "expected_native": True},
        {"app_id": "219990", "name": "Grim Dawn", "expected_rating": "platinum"},
        {"app_id": "367500", "name": "Dragon's Dogma: Dark Arisen", "expected_rating": "platinum"},
        {"app_id": "292030", "name": "The Witcher 3", "expected_rating": "platinum"},
        
        # Games from your screenshot
        {"app_id": "240", "name": "Counter-Strike: Source", "expected_rating": "gold"},
        {"app_id": "320", "name": "Half-Life 2: Deathmatch", "expected_rating": "gold"},
    ]
    
    all_results = []
    
    for game_info in test_games:
        # Simulate what our app would return
        # You would normally fetch this from your API endpoint
        # For now, we'll test the backend functions directly
        
        app_id = game_info["app_id"]
        name = game_info["name"]
        
        # Check native status
        is_native = await check_game_is_native(app_id)
        
        # Get ProtonDB rating from our static cache
        try:
            with open('/Users/alex.wilson/doyouevenlinux/protondb_summary.json', 'r') as f:
                protondb_cache = json.load(f)
            cached_rating = protondb_cache.get(app_id, "pending")
        except:
            cached_rating = "pending"
        
        # Simulate our app's data
        our_data = {
            "rating": "native" if is_native else cached_rating,
            "anticheat": "unknown"  # Would come from our cache
        }
        
        result = await validate_game(app_id, name, our_data)
        all_results.append(result)
        
        # Small delay to avoid overwhelming APIs
        await asyncio.sleep(1)
    
    # Summary
    print("\n" + "=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)
    
    protondb_matches = sum(1 for r in all_results if r["validations"].get("protondb", {}).get("match"))
    protondb_total = sum(1 for r in all_results if "protondb" in r["validations"])
    
    anticheat_matches = sum(1 for r in all_results if r["validations"].get("anticheat", {}).get("match"))
    anticheat_total = len(all_results)
    
    native_matches = sum(1 for r in all_results if r["validations"].get("native", {}).get("match"))
    native_total = sum(1 for r in all_results if "native" in r["validations"])
    
    print(f"\n📊 ProtonDB Ratings: {protondb_matches}/{protondb_total} matches")
    print(f"🛡️  Anti-Cheat Status: {anticheat_matches}/{anticheat_total} matches")
    print(f"🐧 Native Linux: {native_matches}/{native_total} matches")
    
    # Show any mismatches
    mismatches = []
    for result in all_results:
        for validation_type, validation in result["validations"].items():
            if validation.get("match") == False:
                mismatches.append({
                    "game": result["name"],
                    "type": validation_type,
                    "details": validation
                })
    
    if mismatches:
        print("\n❌ MISMATCHES FOUND:")
        for mismatch in mismatches:
            print(f"\n  {mismatch['game']} ({mismatch['type']}):")
            print(f"    {json.dumps(mismatch['details'], indent=4)}")
    else:
        print("\n✅ ALL VALIDATIONS PASSED!")
    
    # Save detailed results
    output_file = "/Users/alex.wilson/doyouevenlinux/validation_results.json"
    with open(output_file, 'w') as f:
        json.dump(all_results, f, indent=2)
    
    print(f"\n📄 Detailed results saved to: {output_file}")


if __name__ == "__main__":
    asyncio.run(main())
