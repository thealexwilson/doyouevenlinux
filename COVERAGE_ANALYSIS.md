# ProtonDB Coverage Analysis

## Dataset Comparison

### Mirror API (protondb.max-p.me)
- **Total reports:** 348,683
- **Unique games:** 37,223
- **Data quality:** Proper ProtonDB tiers (Platinum, Gold, Silver, Bronze, Borked)

### Our Cache (protondb_summary.json)
- **Unique games:** 30,968
- **Coverage:** 83.2% of mirror API games
- **Overlap:** 29,067 games match (93.9% of our cache is valid)
- **Data quality:** Simplified (mostly gold/borked from yes/no verdicts)

## Missing Games

**8,156 games** in mirror API are NOT in our cache
- These games will show "pending" for users
- Represents ~16.8% gap in coverage

## User Impact Estimation

Assuming typical Steam user has 50-500 games:
- **Popular games (top 10k):** ~100% covered
- **Moderately popular (10k-30k):** ~95% covered
- **Indie/niche (30k+):** ~0% covered (will show "pending")

**Estimated user impact:**
- Users with mainstream libraries: < 5% pending games
- Users with indie/niche libraries: 15-30% pending games

## Recommendation

✅ **Implement fallback API** for the 8,156 missing games
✅ **Rate limit to 5 API calls** per user request to prevent slowdown
✅ **Eventually regenerate cache** from full mirror API dataset for better quality + coverage
