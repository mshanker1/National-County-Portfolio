# Percentile Normalization and Reverse Metrics - Technical Documentation

## Overview

The National County Dashboard normalizes sustainability metrics into percentile ranks (0-100) to enable fair comparison across counties. This document explains the normalization process, the reverse metric issue, and how to fix it.

## Normalization Process

### Step 1: Raw Data Collection
- Source: `National_County_Dashboard.csv`
- 3,144 counties across all US states
- 82 individual metrics organized into 15 sub-measures
- 3 top-level categories: People, Prosperity, Place

### Step 2: Percentile Ranking

For each metric, we calculate where each county stands relative to all other counties:

```python
# Standard percentile calculation
df.rank(axis=0, pct=True, na_option='keep') * 100
```

**How it works:**
- Sorts all county values for a metric from lowest to highest
- Assigns ranks: 1st, 2nd, 3rd, ... nth
- Converts to percentage: (rank / total_counties) × 100
- Result: 0-100 scale where 100 = highest raw value

### Step 3: Aggregation to Sub-Measures

Sub-measure scores = mean of constituent metric percentiles

Example: **People_Health** score = average of:
- Life Expectancy percentile
- Physical Distress percentile
- Mental Distress percentile
- HIV Prevalence percentile
- Diabetes prevalence percentile
- etc.

## The Reverse Metric Problem

### Definition

**Reverse metrics** are those where a LOWER raw value indicates BETTER performance.

Examples:
- **Unemployment Rate**: 2% is better than 20%
- **Violent Crime Rate**: Lower is better
- **Air Pollution (PM2.5)**: Lower is better
- **CO2 Emissions**: Lower is better

### The Issue

Standard percentile ranking gives:
```
Raw Value    Standard Percentile
---------    -------------------
2% (BEST)    →  5th percentile  ❌ WRONG!
10% (MED)    → 50th percentile
20% (WORST)  → 95th percentile  ❌ WRONG!
```

This is backwards! Counties with low unemployment appear to be poor performers.

### The Solution

Apply an inversion transformation for reverse metrics:

```python
if metric in reverse_metrics:
    display_percentile = 100 - raw_percentile
else:
    display_percentile = raw_percentile
```

After correction:
```
Raw Value    Raw Percentile    Display Percentile (Corrected)
---------    --------------    ------------------------------
2% (BEST)    →   5th          →  95th  ✓ CORRECT!
10% (MED)    →  50th          →  50th  ✓
20% (WORST)  →  95th          →   5th  ✓ CORRECT!
```

## Implementation Details

### Current State

**BigQuery Implementation** (`stage2_normalization.py`):
```python
# Line 285-288
if is_reverse:
    percentile_rank = 100 - stats.percentileofscore(all_values, raw_value)
else:
    percentile_rank = stats.percentileofscore(all_values, raw_value)
```
✅ **Correctly reverses percentiles**

**Local CSV Implementation** (`local_data_provider.py`):
```python
# Line 170
def _percentile_ranks(df):
    return df.rank(axis=0, pct=True, na_option='keep') * 100
```
❌ **Does NOT reverse percentiles** - needs fixing!

**Visualization Layer** (`enhanced_radar_v2_with_fast_state.py`):
```python
# Lines 650-658
if is_reverse:
    display_percentile = 100 - percentile
else:
    display_percentile = percentile
```
✅ **Applies reversal before displaying** - but only in charts!

### Where Should Reversal Happen?

**Option 1: In Data Provider** (RECOMMENDED)
- Pro: All consumers get correct data
- Pro: Consistent with BigQuery implementation
- Pro: Simplifies downstream code
- Con: Requires modification to local_data_provider.py

**Option 2: Only in Visualization** (CURRENT PARTIAL APPROACH)
- Pro: No data layer changes needed
- Con: API consumers get wrong percentiles
- Con: Aggregation happens on wrong percentiles
- Con: Inconsistent with BigQuery

**Recommendation:** Fix in the data provider (Option 1)

## List of Reverse Metrics

These 23 metrics must have percentiles reversed:

### People - Community (2 metrics)
```
People_Community_LongCommuteAndDrivesAlone
People_Community_ViolentCrimeRate
```

### People - Health Behaviors (5 metrics)
```
People_Health_HealthBehaviours_AdultsSmoking
People_Health_HealthBehaviours_AdultsWithObesity
People_Health_HealthBehaviours_ExcessiveDrinking
People_Health_HealthBehaviours_InsufficientSleep
People_Health_HealthBehaviours_PhysicallyInactive
```

### People - Health Resources (2 metrics)
```
People_Health_HealthResources_AccessToCare_Uninsured
People_Health_HealthResources_QualityOfCare_PreventableHospitalizationRate
```

### People - Health Outcomes (5 metrics)
```
People_Health_LengthOfLife_Premature Death    # Note: has a SPACE!
People_Health_QualityOfLife_AdultWithDiabetes
People_Health_QualityOfLife_FreqMenDistress
People_Health_QualityOfLife_FreqPhyDistress
People_Health_QualityOfLife_HIVPrevRate
```

### People - Wealth (2 metrics)
```
People_Wealth_ChildPoverty
People_Wealth_IncomeRatio80by20
```

### Place - Climate (1 metric)
```
Place_ClimateAndResilience_CO2OrCapita
```

### Place - Air Quality (1 metric)
```
Place_LandAirWater_AirQualityIndexPerPm2.5
```

### Prosperity - Business (1 metric)
```
Prosperity_Business_RatioOfEstablishmentBirthsPerDeaths2020
```

### Prosperity - Employment (1 metric)
```
Prosperity_Employment_UnemploymentRate
```

### Prosperity - Government (2 metrics)
```
Prosperity_Government_DependencyRatio
Prosperity_Government_ViolentCrimeRate
```

### Prosperity - Nonprofit (1 metric)
```
Prosperity_Nonprofit_WageRatio
```

**Total: 23 reverse metrics out of 82 total metrics**

## Impact on Aggregation

### Current Incorrect Flow
```
1. Raw values → 2. Percentiles (NOT reversed) → 3. Aggregate to sub-measures → 4. Display
```

**Problem:** Sub-measure aggregation uses wrong percentiles!

Example for People_Health:
- Life Expectancy: 80 years → 90th percentile ✓ (higher is better)
- Unemployment: 2% → 5th percentile ❌ (should be 95th!)
- **Average: (90 + 5) / 2 = 47.5 percentile** ❌ WRONG!

### Correct Flow
```
1. Raw values → 2. Percentiles → 3. Reverse if needed → 4. Aggregate → 5. Display
```

After fix:
- Life Expectancy: 80 years → 90th percentile ✓
- Unemployment: 2% → 95th percentile ✓ (after reversal)
- **Average: (90 + 95) / 2 = 92.5 percentile** ✓ CORRECT!

## Testing Methodology

Use `test_percentile_logic.py` to verify calculations:

```bash
python3 test_percentile_logic.py
```

The script will:
1. Load a specific county's data
2. Show raw values vs. percentiles for all metrics
3. Highlight reverse metrics
4. Compare current vs. corrected percentiles
5. Validate aggregation logic

### What to Check

For reverse metrics:
- ✅ Lowest raw value should have ~100th percentile
- ✅ Highest raw value should have ~0th percentile
- ✅ Sub-measure aggregates should use reversed values

For normal metrics:
- ✅ Highest raw value should have ~100th percentile
- ✅ Lowest raw value should have ~0th percentile

## How to Fix

See the separate fix in `local_data_provider.py`:

1. Modify `_percentile_ranks()` method to accept a list of reverse columns
2. Apply `100 - percentile` transformation for those columns
3. Ensure aggregation happens AFTER reversal
4. Test with `test_percentile_logic.py`

## References

- BigQuery implementation: `stage2_normalization.py` lines 285-288
- Visualization reversal: `enhanced_radar_v2_with_fast_state.py` lines 650-658
- Reverse metric definitions: `local_data_provider.py` lines 47-82
