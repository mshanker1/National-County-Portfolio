# Double Reversal Bug Fix - March 12, 2026

## Issue Discovered

The dashboard was displaying **incorrect percentiles** for reverse metrics in the detail drill-down charts.

### Example: Delaware County, Indiana - Premature Death
- **Raw value**: 10,902 (high = bad performance)
- **Expected percentile**: 21.29% (correctly shows poor performance)
- **Dashboard was showing**: 78.71% (incorrectly shows good performance)
- **Error**: 78.71% - 21.29% = 57.42 percentage point error!

## Root Cause

**Double reversal** of percentiles in the `create_detail_chart` function.

### How Percentile Reversal Works

Both data providers (Local CSV and BigQuery) apply reversal at the **data layer**:

#### Local CSV Provider (`local_data_provider.py`, lines 163-180)
```python
def _percentile_ranks(self, df):
    """Compute percentile rank 0-100 for every column, across rows."""
    # Compute raw percentiles for all columns
    pct_df = df.rank(axis=0, pct=True, na_option='keep') * 100

    # Apply reversal for reverse metrics
    for col in df.columns:
        if col in self._REVERSE_METRICS:
            pct_df[col] = 100 - pct_df[col]  # ← ALREADY REVERSED

    return pct_df
```

#### BigQuery Provider (`stage2_normalization.py`, lines 284-288)
```python
# Calculate percentile rank using scipy
if is_reverse:
    percentile_rank = 100 - stats.percentileofscore(all_values, raw_value)  # ← ALREADY REVERSED
else:
    percentile_rank = stats.percentileofscore(all_values, raw_value)
```

### What Was Wrong

The `create_detail_chart` function in `enhanced_radar_v2_with_fast_state.py` was **reversing again**:

```python
# Lines 652-656 (BEFORE FIX - INCORRECT)
if is_reverse:
    # REVERSE IT! Lower percentile = Better performance
    display_percentile = 100 - percentile  # ❌ DOUBLE REVERSAL!
else:
    display_percentile = percentile
```

### The Double Reversal Problem

**For Delaware County - Premature Death:**

1. **Raw value**: 10,902
2. **Raw percentile** (higher value = higher rank): 78.71%
3. **Data provider reverses** (because lower death = better): `100 - 78.71 = 21.29%` ✓
4. **Detail chart reverses AGAIN**: `100 - 21.29 = 78.71%` ❌
5. **Result**: Back to wrong value!

This made it appear that Delaware County had **good** performance (78.71%) when it actually has **poor** performance (21.29%).

## The Fix

**File**: `enhanced_radar_v2_with_fast_state.py`

**Lines 639-650** (AFTER FIX - CORRECT):
```python
def create_detail_chart(details_df, title, comparison_mode='national'):
    """Create enhanced detail chart - percentiles already reversed by data provider"""
    import plotly.graph_objects as go

    if details_df.empty:
        return go.Figure()

    # NOTE: The data provider (both BigQuery and Local) already applies
    # the reversal logic (100 - percentile) for reverse metrics.
    # DO NOT reverse again here or it will double-reverse!
    # Just use the percentile_rank as-is.
    details_df['display_percentile'] = details_df['percentile_rank']  # ✓ CORRECT
```

## Why This Fix Works for Both Providers

Both data providers handle reversal identically:

| Provider | Where Reversal Happens | When | Formula |
|----------|----------------------|------|---------|
| **Local CSV** | `_percentile_ranks()` | During data load | `100 - percentile` |
| **BigQuery** | `normalize_metrics()` | Stage 2 processing | `100 - stats.percentileofscore()` |

By removing the reversal logic from `create_detail_chart`, we ensure:
1. ✓ Data providers apply reversal once (correct)
2. ✓ Chart displays the already-reversed percentile (correct)
3. ✗ No double-reversal (fixed)

## Verification

### Test with Delaware County, Indiana (FIPS: 18035)

**Access URL**:
```
http://localhost:8050/?county=18035&key=county_dashboard_2024
```

**Click on "Health" sub-measure** to see detail chart.

**Expected Results**:
- Premature Death should show: **21.29%** (not 78.71%)
- Lower percentile correctly indicates higher premature death (worse performance)

### Programmatic Verification

```python
from local_data_provider import LocalCSVRadarChartDataProvider

provider = LocalCSVRadarChartDataProvider()
fips = '18035'  # Delaware County, Indiana
metric = 'People_Health_LengthOfLife_Premature Death'

raw_value = provider._raw.loc[fips, metric]
percentile = provider._pct.loc[fips, metric]

print(f"Raw value: {raw_value}")        # 10902.0
print(f"Percentile: {percentile:.2f}%") # 21.29% ✓
print(f"Is reversed: {metric in provider._REVERSE_METRICS}")  # True
```

## Impact Analysis

### Affected Metrics (23 Reverse Metrics)

All of these were showing inverted percentiles in detail charts:

**People - Health (13 metrics)**:
- Premature Death ✓ Fixed
- Adult with Diabetes ✓ Fixed
- HIV Prevalence Rate ✓ Fixed
- Adults with Obesity ✓ Fixed
- Adults Smoking ✓ Fixed
- Excessive Drinking ✓ Fixed
- Physically Inactive ✓ Fixed
- Insufficient Sleep ✓ Fixed
- Frequent Physical Distress ✓ Fixed
- Frequent Mental Distress ✓ Fixed
- Uninsured ✓ Fixed
- Preventable Hospitalization Rate ✓ Fixed

**People - Community (2 metrics)**:
- Long Commute and Drives Alone ✓ Fixed
- Violent Crime Rate ✓ Fixed

**People - Wealth (2 metrics)**:
- Income Ratio 80by20 ✓ Fixed
- Child Poverty ✓ Fixed

**Prosperity (4 metrics)**:
- Unemployment Rate ✓ Fixed
- Violent Crime Rate (Government) ✓ Fixed
- Dependency Ratio ✓ Fixed
- Wage Ratio (Nonprofit) ✓ Fixed

**Place (2 metrics)**:
- CO2 per Capita ✓ Fixed
- Air Quality Index per PM2.5 ✓ Fixed

### What Was NOT Affected

1. **Radar chart percentiles**: These were always correct (no reversal logic in radar chart code)
2. **Sub-measure aggregations**: These use the data provider's already-reversed percentiles
3. **Normal metrics** (60 metrics where higher = better): These were always correct
4. **Exported CSV data**: The test script uses the data provider directly, so percentiles were correct

### Only Detail Charts Were Wrong

The bug **only affected the drill-down detail charts** accessed by clicking on sub-measures in the radar chart.

## Future Prevention

### Code Review Checklist

When working with percentiles:

1. ✓ Check if data provider already reverses percentiles
2. ✓ Never apply `100 - percentile` in visualization code
3. ✓ Trust the data provider's percentile values
4. ✓ Add comments explaining reversal is handled upstream

### Documentation

Added clear documentation in `create_detail_chart`:
```python
# NOTE: The data provider (both BigQuery and Local) already applies
# the reversal logic (100 - percentile) for reverse metrics.
# DO NOT reverse again here or it will double-reverse!
```

### Testing Recommendation

Always test with a known reverse metric like Unemployment Rate or Premature Death:
- Verify that counties with **high** raw values get **low** percentiles
- Verify that counties with **low** raw values get **high** percentiles

## Timeline

- **Issue Discovered**: March 12, 2026
- **Root Cause Identified**: Double reversal in `create_detail_chart`
- **Fix Applied**: March 12, 2026
- **Verification**: Tested with Delaware County, Indiana (FIPS 18035)
- **Deployment**: Dashboard restarted with fix

## Related Files

- **Fixed**: `enhanced_radar_v2_with_fast_state.py` (lines 639-650)
- **Data Provider (Local)**: `local_data_provider.py` (lines 163-180)
- **Data Provider (BigQuery)**: `stage2_normalization.py` (lines 284-288)
- **Documentation**: This file

## Conclusion

The fix ensures that reverse metrics are **reversed exactly once** at the data provider level, and visualization code **displays the values as-is** without additional manipulation.

This fix applies to **both Local CSV and BigQuery modes** since both providers handle reversal identically.

✅ **Status**: Fixed and verified
✅ **Applies to**: Both Local CSV and BigQuery modes
✅ **Dashboard**: Restarted with fix applied
