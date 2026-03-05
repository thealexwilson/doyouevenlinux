#!/usr/bin/env python3
"""
Convert games_list.json (individual reports with verdicts) 
into a ProtonDB-style summary (app_id -> tier rating).
"""

import json
from collections import Counter

# Mapping from verdict patterns to ProtonDB tiers
VERDICT_TO_TIER = {
    # Platinum - works perfectly
    'platinum': ['yes', 'perfect', 'works perfectly', 'flawless', 'runs perfectly'],
    # Gold - works great with minor issues
    'gold': ['works great', 'works fine', 'runs great', 'works out of the box'],
    # Silver - works but with some issues  
    'silver': ['works', 'playable', 'runs'],
    # Bronze - barely playable
    'bronze': ['barely', 'crashes', 'issues'],
    # Borked - doesn't work
    'borked': ['no', 'borked', 'broken', 'doesn\'t work', 'unplayable']
}

def classify_verdict(verdict: str) -> str:
    """Classify a verdict string into a ProtonDB tier."""
    if not verdict or verdict.strip() == '':
        return 'pending'
    
    verdict_lower = verdict.lower().strip()
    
    # Simple mapping: yes = works (gold), no = broken (borked)
    if verdict_lower == 'yes':
        return 'gold'  # Works well
    elif verdict_lower == 'no':
        return 'borked'  # Doesn't work
    else:
        # For descriptive verdicts, look for keywords
        if any(word in verdict_lower for word in ['perfect', 'flawless', 'platinum']):
            return 'platinum'
        elif any(word in verdict_lower for word in ['great', 'fine', 'well', 'ootb', 'just works']):
            return 'gold'
        elif any(word in verdict_lower for word in ['issues', 'crashes', 'bugs']):
            return 'silver'
        elif 'no' in verdict_lower or 'broken' in verdict_lower or 'borked' in verdict_lower:
            return 'borked'
        else:
            return 'gold'  # Default to gold for positive-sounding verdicts

def aggregate_game_ratings(games_list):
    """Aggregate individual reports into a consensus tier rating per game."""
    game_ratings = {}  # app_id -> list of tiers
    
    for report in games_list:
        app_id = report.get('app', {}).get('steam', {}).get('appId')
        verdict = report.get('responses', {}).get('verdict', '')
        
        if not app_id:
            continue
        
        tier = classify_verdict(verdict)
        
        if app_id not in game_ratings:
            game_ratings[app_id] = []
        game_ratings[app_id].append(tier)
    
    # Calculate consensus tier (most common, with tie-breaking)
    tier_priority = {'platinum': 5, 'gold': 4, 'silver': 3, 'bronze': 2, 'borked': 1, 'pending': 0}
    
    summary = {}
    for app_id, tiers in game_ratings.items():
        # Count occurrences
        counter = Counter(tiers)
        # Get most common, but prefer higher tiers in case of tie
        most_common_tier = max(counter.keys(), key=lambda t: (counter[t], tier_priority.get(t, 0)))
        summary[str(app_id)] = most_common_tier
    
    return summary

def main():
    print("Loading games_list.json...")
    with open('/Users/alex.wilson/Desktop/games_list.json', 'r') as f:
        games = json.load(f)
    
    print(f"Loaded {len(games)} game reports")
    
    print("Aggregating ratings...")
    summary = aggregate_game_ratings(games)
    
    print(f"Generated summary for {len(summary)} unique games")
    
    # Show distribution
    tier_counts = Counter(summary.values())
    print("\nTier distribution:")
    for tier in ['platinum', 'gold', 'silver', 'bronze', 'borked', 'pending']:
        count = tier_counts.get(tier, 0)
        pct = (count / len(summary) * 100) if summary else 0
        print(f"  {tier:10s}: {count:6d} ({pct:5.2f}%)")
    
    # Save to output file
    output_path = '/Users/alex.wilson/doyouevenlinux/protondb_summary.json'
    print(f"\nSaving to {output_path}...")
    with open(output_path, 'w') as f:
        json.dump(summary, f)
    
    print("✅ Done! File ready to deploy with your app")
    print(f"   Size: {len(json.dumps(summary)) / 1024 / 1024:.2f} MB")

if __name__ == '__main__':
    main()
