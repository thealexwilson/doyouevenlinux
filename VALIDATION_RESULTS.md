# ProtonDB Rating Validation Results

## Summary
Our current `protondb_summary.json` ratings are **INACCURATE** compared to actual ProtonDB data.

## Data Source Comparison

### Our Data (games_list.json)
- Format: Simple "yes/no" verdicts
- Sample size: 348,683 reports for 30,968 games
- Mapping used: yes → gold, no → borked

### Mirror API (protondb.max-p.me)
- Format: Proper ProtonDB tiers (Platinum, Gold, Silver, Bronze, Borked)
- More accurate reflection of actual ProtonDB ratings

## Test Results

| Game ID | Our Rating | Mirror API (Most Common) | Actual Distribution |
|---------|------------|--------------------------|---------------------|
| 352620  | borked     | **Platinum** (75%)       | 3 Platinum, 1 Borked |
| 219990  | gold       | **Platinum** (55%)       | 128 Platinum, others |
| 367500  | gold       | **Platinum** (34%)       | 17 Platinum, others |
| 251570  | gold       | **Platinum** (78%)       | 7 Platinum, others |
| 292030  | gold       | **Platinum** (73%)       | 340 Platinum, others |

## Root Cause

Our `games_list.json` contains **older report format** with simple yes/no verdicts:
- Game 352620: 2 "no" + 1 "yes" → We marked "borked"
- Game 219990: 302 "yes" + 33 "no" → We marked "gold"

But the **mirror API has newer, proper tier ratings** that are more accurate.

## Conclusion

✅ **Mirror API data is higher quality and more accurate**
✅ **We should use mirror API as fallback for missing games**
✅ **Consider regenerating our static cache from mirror API data**

## Recommendation

1. **Immediate:** Implement fallback to mirror API for games not in our 30k cache
2. **Next:** Download full 464MB mirror API dataset and regenerate protondb_summary.json with proper tiers
3. **Future:** This will give us accurate Platinum/Gold/Silver/Bronze/Borked ratings instead of simplified gold/borked
