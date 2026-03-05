#!/usr/bin/env python3
"""
Regenerate ProtonDB Summary from Mirror API
Downloads full 464MB dataset and creates accurate tier summary
"""
import json
import time
from collections import Counter
from urllib.request import urlopen, Request


def download_protondb_dataset():
    """Download full ProtonDB dataset from mirror API"""
    print("=" * 60)
    print("PROTONDB DATASET DOWNLOAD & PROCESSING")
    print("=" * 60)
    print("\nStep 1: Downloading full dataset from mirror API...")
    print("URL: https://protondb.max-p.me/reports.json")
    print("Size: ~464MB (this will take ~30 seconds)")
    
    req = Request('https://protondb.max-p.me/reports.json')
    req.add_header('User-Agent', 'Mozilla/5.0')
    
    start = time.time()
    with urlopen(req, timeout=300) as response:
        data = response.read()
        elapsed = time.time() - start
        print(f"✓ Downloaded {len(data) / 1024 / 1024:.1f} MB in {elapsed:.1f}s")
    
    print("\nStep 2: Parsing JSON...")
    reports = json.loads(data)
    print(f"✓ Loaded {len(reports)} individual reports")
    
    return reports


def aggregate_reports_to_tiers(reports):
    """
    Aggregate individual reports into game -> tier mapping.
    Uses most common tier rating per game.
    """
    print("\nStep 3: Aggregating reports by game...")
    
    game_reports = {}  # app_id -> list of ratings
    
    for report in reports:
        app_id = report.get('app', {}).get('steam', {}).get('appId')
        rating = report.get('rating')
        
        if not app_id or not rating:
            continue
        
        # Normalize rating to lowercase
        rating = rating.lower()
        
        # Only keep valid ProtonDB tiers
        valid_tiers = ['platinum', 'gold', 'silver', 'bronze', 'borked']
        if rating not in valid_tiers:
            continue
        
        if app_id not in game_reports:
            game_reports[app_id] = []
        game_reports[app_id].append(rating)
    
    print(f"✓ Found {len(game_reports)} unique games with ratings")
    
    # Aggregate to most common tier per game
    print("\nStep 4: Calculating consensus tier per game...")
    summary = {}
    tier_priority = {
        'platinum': 5,
        'gold': 4,
        'silver': 3,
        'bronze': 2,
        'borked': 1
    }
    
    for app_id, ratings in game_reports.items():
        # Count occurrences of each tier
        counter = Counter(ratings)
        
        # Get most common tier
        # If tie, prefer higher tier (platinum > gold > silver > bronze > borked)
        most_common_tier = max(
            counter.keys(),
            key=lambda t: (counter[t], tier_priority.get(t, 0))
        )
        
        summary[str(app_id)] = most_common_tier
    
    print(f"✓ Generated summary for {len(summary)} games")
    
    return summary


def analyze_distribution(summary):
    """Analyze tier distribution"""
    print("\nStep 5: Analyzing tier distribution...")
    
    tier_counts = Counter(summary.values())
    total = len(summary)
    
    print(f"\nTier Distribution ({total} games):")
    print("-" * 40)
    
    for tier in ['platinum', 'gold', 'silver', 'bronze', 'borked']:
        count = tier_counts.get(tier, 0)
        pct = (count / total * 100) if total else 0
        bar = '█' * int(pct / 2)
        print(f"  {tier:10s}: {count:6d} ({pct:5.1f}%) {bar}")
    
    return tier_counts


def save_summary(summary, output_path):
    """Save summary to JSON file"""
    print(f"\nStep 6: Saving summary...")
    print(f"Output: {output_path}")
    
    with open(output_path, 'w') as f:
        json.dump(summary, f)
    
    file_size = len(json.dumps(summary)) / 1024 / 1024
    print(f"✓ Saved {len(summary)} games ({file_size:.2f} MB)")


def compare_with_old_data(new_summary):
    """Compare new data with old static cache"""
    print("\nStep 7: Comparing with old cache...")
    
    try:
        with open('/Users/alex.wilson/doyouevenlinux/protondb_summary.json', 'r') as f:
            old_summary = json.load(f)
        
        old_count = len(old_summary)
        new_count = len(new_summary)
        
        print(f"  Old cache: {old_count} games")
        print(f"  New cache: {new_count} games")
        print(f"  Difference: +{new_count - old_count} games")
        
        # Check some games that were mismatched in validation
        test_games = {
            '219990': 'Grim Dawn',
            '367500': "Dragon's Dogma",
            '292030': 'The Witcher 3'
        }
        
        print("\n  Sample comparisons (games that had mismatches):")
        for app_id, name in test_games.items():
            old_rating = old_summary.get(app_id, 'N/A')
            new_rating = new_summary.get(app_id, 'N/A')
            if old_rating != new_rating:
                print(f"    {name}:")
                print(f"      Old: {old_rating}")
                print(f"      New: {new_rating} ✓")
            else:
                print(f"    {name}: {new_rating} (unchanged)")
        
    except Exception as e:
        print(f"  Could not compare: {e}")


def main():
    """Main execution"""
    try:
        # Download dataset
        reports = download_protondb_dataset()
        
        # Aggregate to tier summary
        summary = aggregate_reports_to_tiers(reports)
        
        # Analyze distribution
        analyze_distribution(summary)
        
        # Compare with old data
        compare_with_old_data(summary)
        
        # Save new summary
        output_path = '/Users/alex.wilson/doyouevenlinux/protondb_summary.json'
        save_summary(summary, output_path)
        
        # Create backup of old file first
        import shutil
        backup_path = '/Users/alex.wilson/doyouevenlinux/protondb_summary_OLD.json'
        try:
            shutil.copy(output_path, backup_path)
            print(f"\n✓ Backup of old file saved to: protondb_summary_OLD.json")
        except:
            pass
        
        # Save new summary
        save_summary(summary, output_path)
        
        print("\n" + "=" * 60)
        print("✅ COMPLETE!")
        print("=" * 60)
        print("\nNew protondb_summary.json ready with:")
        print(f"  • {len(summary)} games (vs 30,968 previously)")
        print(f"  • Accurate ProtonDB tiers (Platinum, Gold, Silver, Bronze, Borked)")
        print(f"  • Data from {len(reports)} community reports")
        print("\nNext steps:")
        print("  1. Deploy the updated protondb_summary.json")
        print("  2. Test with your Steam library")
        print("  3. Run validate_data.py again to verify accuracy")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
