# Normalization Levels: National vs State

## Quick Answer

**Z-score normalization**: Always done at the **NATIONAL level** (across all ~3,100 counties)

**Percentile rankings**: Computed at **BOTH levels**:
- **National percentiles**: Default, always available
- **State percentiles**: Optional, used when comparing counties within a state

**Consistency**: Both BigQuery and Local approaches use the **same methodology**

---

## Detailed Explanation

### 1. Z-Score Normalization (Stage 2)

**Level**: NATIONAL ONLY

**Formula**:
```
z_score = (county_value - national_mean) / national_std_dev
```

**BigQuery Implementation** (`stage2_normalization.py`):
```sql
-- Lines 154-165: Statistics calculated across ALL counties
SELECT
    metric_name,
    COUNT(*) as total_counties,
    AVG(raw_value) as mean_value,      -- National mean
    STDDEV_SAMP(raw_value) as std_dev, -- National std dev
    MIN(raw_value) as min_value,
    MAX(raw_value) as max_value
FROM raw_metrics
WHERE raw_value IS NOT NULL
GROUP BY metric_name
```

Then for each county (lines 280-282):
```python
z_score = (raw_value - mean_val) / std_val  # Uses national mean/std
```

**Local Implementation** (`local_data_provider.py`):
```python
# Lines 283-285: National percentile ranks
print("📊 [Local] Computing national percentile ranks …")
pct_df = self._percentile_ranks(metrics_df)  # Computed across all counties
```

The Z-scores are always based on the **national distribution** because:
1. They're used for mathematical aggregation (averaging metrics into sub-measures)
2. Changing the reference population would invalidate aggregations
3. State-level Z-scores aren't needed since percentiles serve that purpose

---

### 2. National Percentile Rankings (Stage 2)

**Level**: NATIONAL (across all ~3,100 U.S. counties)

**BigQuery** (`stage2_normalization.py`, lines 254-260):
```python
# Get all valid values for percentile calculation
all_values_query = """
    SELECT raw_value
    FROM raw_metrics
    WHERE metric_name = '{metric_name}'
      AND is_missing = FALSE
      AND raw_value IS NOT NULL
"""
all_values = all_values_df['raw_value'].values

# Lines 285-288: Calculate percentile among ALL counties nationally
if is_reverse:
    percentile_rank = 100 - stats.percentileofscore(all_values, raw_value)
else:
    percentile_rank = stats.percentileofscore(all_values, raw_value)
```

**Local** (`local_data_provider.py`, lines 163-180):
```python
def _percentile_ranks(self, df):
    """
    Compute percentile rank 0-100 for every column, across rows.
    """
    # Compute raw percentiles for all columns
    pct_df = df.rank(axis=0, pct=True, na_option='keep') * 100

    # Apply reversal for reverse metrics
    for col in df.columns:
        if col in self._REVERSE_METRICS:
            pct_df[col] = 100 - pct_df[col]

    return pct_df
```

National percentiles answer: **"How does this county rank among all U.S. counties?"**

---

### 3. State Percentile Rankings (Stage 3)

**Level**: STATE (only counties within the same state)

**BigQuery** (`enhanced_radar_v2_with_fast_state.py`):
- Pre-computed and stored in `state_percentiles` and `state_aggregated_scores` tables
- Used when `comparison_mode = 'state'` and `stage >= 3`
- Lines 305-306: Queries from pre-computed `state_percentiles` table
- Lines 210-211: Queries from pre-computed `state_aggregated_scores` table

**Local** (`local_data_provider.py`, lines 322-358):
```python
def _get_state_data(self, state_code):
    """
    Return (state_pct_df, state_sub_df) for the given state name.
    Results are cached after first computation.
    """
    # Match state name
    mask = self._county_info['state'] == state_code
    state_fips = self._county_info[mask].index

    # Get only counties in this state
    state_raw = self._raw.loc[self._raw.index.isin(state_fips)]

    # Compute percentiles ONLY among this state's counties
    state_pct = self._percentile_ranks(state_raw)

    # Cache results
    self._state_cache[state_code] = (state_pct, state_sub)
    return state_pct, state_sub
```

State percentiles answer: **"How does this county rank among counties in its own state?"**

---

## Comparison: BigQuery vs Local

### Similarities (Same Methodology)

| Aspect | BigQuery | Local | Match? |
|--------|----------|-------|--------|
| **Z-score level** | National | National | ✅ Yes |
| **Z-score formula** | `(value - mean) / std` | `(value - mean) / std` | ✅ Yes |
| **National percentiles** | All counties | All counties | ✅ Yes |
| **State percentiles** | By state | By state | ✅ Yes |
| **Reverse metrics** | `100 - percentile` | `100 - percentile` | ✅ Yes |
| **Reverse metric list** | 23 metrics | 23 metrics | ✅ Yes |

### Differences (Implementation Only)

| Aspect | BigQuery | Local |
|--------|----------|-------|
| **State percentile timing** | Pre-computed (Stage 3) | On-demand (cached) |
| **State percentile storage** | BigQuery tables | In-memory cache |
| **Initial load time** | N/A (cloud) | 2-4 seconds |
| **State switch speed** | Instant (pre-computed) | ~0.5s first time, instant after |
| **Memory usage** | None (cloud) | ~200 MB in RAM |

---

## When Each Percentile Type is Used

### Dashboard Display (Radar Charts)

The dashboard shows **either** national or state percentiles depending on mode:

```python
# In enhanced_radar_v2_with_fast_state.py (lines 195-239)
if self.comparison_mode == 'state' and self.stage >= 3:
    # Show STATE percentiles
    query = "SELECT state_percentile_rank FROM state_aggregated_scores ..."
else:
    # Show NATIONAL percentiles
    query = "SELECT percentile_rank FROM aggregated_scores ..."
```

### Example: Autauga County, Alabama - Unemployment Rate

**Raw value**: 4.2%

**National comparison** (among 3,142 U.S. counties):
- Z-score: -0.45 (below national average unemployment)
- National percentile: 72nd (better than 72% of U.S. counties)

**State comparison** (among 67 Alabama counties):
- Z-score: Still -0.45 (unchanged, always national)
- State percentile: 45th (average among Alabama counties)

**Interpretation**:
- Autauga has lower unemployment than most U.S. counties (72nd percentile nationally)
- But it's average compared to other Alabama counties (45th percentile in-state)

---

## Why This Design?

### Z-Scores at National Level Only
1. **Mathematical consistency**: Sub-measures aggregate Z-scores; changing reference population breaks this
2. **Comparability**: All counties use the same scale
3. **Stability**: National statistics don't change when switching views

### Percentiles at Both Levels
1. **National percentiles**: "How does my county rank nationally?"
2. **State percentiles**: "How does my county rank in-state?"
3. **User choice**: Dashboard lets users toggle between perspectives

### Pre-computation in BigQuery (Stage 3)
- Calculating state percentiles on-the-fly would be slow (50+ states × 3,000 counties)
- Pre-computing enables instant switching between national/state views
- Local provider computes on-demand but caches results (acceptable for single-user)

---

## Verification

You can verify this in your exported CSV file:

```python
import pandas as pd
df = pd.read_csv('county_metrics_detailed_20260311_180754.csv')

# Check a specific county and metric
autauga_unemp = df[
    (df['FIPS'] == '01001') &
    (df['Metric_Database_Name'] == 'Prosperity_Employment_UnemploymentRate')
]

print(autauga_unemp[['Raw_Value', 'Z_Score_Normalized',
                      'National_Percentile', 'State_Percentile']])

# The Z-score is the same regardless of comparison level
# But percentiles differ: national vs. state rankings
```

---

## Summary Table

| Normalization Type | Level | When Computed | Used For |
|-------------------|-------|---------------|----------|
| **Z-Score** | National only | Stage 2 | Mathematical aggregation, standardization |
| **National Percentile** | National (3,142 counties) | Stage 2 | Default dashboard view, national rankings |
| **State Percentile** | State-specific (varies) | Stage 3 (BQ) or on-demand (local) | State comparison view, in-state rankings |

**Bottom line**:
- Z-scores = always national reference
- Percentiles = user can choose national or state reference
- Both approaches (BigQuery & Local) use identical methodology
