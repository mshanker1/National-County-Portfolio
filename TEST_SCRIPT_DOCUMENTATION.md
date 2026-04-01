# Test Script Documentation

## Overview

The `test_percentile_logic.py` script has been enhanced to export comprehensive metric data for all counties in the National County Dashboard.

## What Was Changed

### Original Script
The original script only:
- Tested percentile calculations for specific counties
- Verified reverse metric logic
- Displayed results to console

### Enhanced Script
The enhanced script now:
1. **Exports all metric data to CSV** with the following columns:
   - `FIPS`: County FIPS code
   - `County`: County name
   - `State`: State name
   - `Category`: Top-level category (People, Prosperity, Place)
   - `Sub_Measure`: Sub-measure category
   - `Metric_Database_Name`: Database column name for the metric
   - `Metric_Display_Name`: Human-readable metric name
   - `Raw_Value`: Original raw data value
   - `Z_Score_Normalized`: Z-score normalized value (standardized)
   - `National_Percentile`: Percentile rank compared to all ~3,100 U.S. counties
   - `State_Percentile`: Percentile rank compared to counties within the same state
   - `Is_Reverse_Metric`: Boolean indicating if lower raw values = better performance
   - `Unit`: Unit of measurement
   - `Year`: Year(s) of data collection

2. **Maintains all original testing functionality**
   - Tests specific county metrics
   - Verifies reverse metric logic
   - Validates normal metric logic

## How to Run

```bash
# Set environment to use local CSV data (no cloud dependencies)
DATA_SOURCE=local python3 test_percentile_logic.py
```

## Output

### Console Output
The script prints:
- Progress indicators during data processing
- Summary statistics about the export
- Test results for specific counties
- Validation of percentile calculation logic

### CSV File
Creates a timestamped CSV file: `county_metrics_detailed_YYYYMMDD_HHMMSS.csv`

**Example filename**: `county_metrics_detailed_20260311_180754.csv`

**File Statistics** (for full dataset):
- **Size**: ~41 MB
- **Total records**: 236,785 metric records
- **Counties**: 3,142
- **Unique metrics**: 79
- **Reverse metrics**: 67,288 records (where lower = better)

## Normalization Methods Used

The dashboard uses **two complementary normalization approaches**:

### 1. Z-Score Normalization (Standardization)
```
z_score = (raw_value - mean) / standard_deviation
```
- Transforms data to have mean = 0, std dev = 1
- Typical range: -3 to +3
- Stored in `Z_Score_Normalized` column

### 2. Percentile Ranking
```
percentile = rank of value among all values (0-100 scale)
```
- For normal metrics: higher raw value → higher percentile
- For reverse metrics: lower raw value → higher percentile (inverted using `100 - percentile`)
- Stored in `National_Percentile` and `State_Percentile` columns

### Reverse Metrics
The following metrics are "reverse" where **lower raw values = better performance**:

**People - Health** (13 metrics):
- Premature Death, Adult with Diabetes, HIV Prevalence, etc.
- Obesity, Smoking, Excessive Drinking, Insufficient Sleep
- Uninsured, Preventable Hospitalization Rate

**People - Community** (2 metrics):
- Long Commute and Drives Alone
- Violent Crime Rate

**People - Wealth** (2 metrics):
- Income Ratio 80by20
- Child Poverty

**Prosperity** (4 metrics):
- Unemployment Rate
- Violent Crime Rate (Government)
- Dependency Ratio
- Wage Ratio (Nonprofit)

**Place** (2 metrics):
- CO2 per Capita
- Air Quality Index per PM2.5

## Data Verification

The script includes built-in verification that:
1. ✅ Reverse metrics are correctly inverted (lower unemployment → higher percentile)
2. ✅ Normal metrics work correctly (higher life expectancy → higher percentile)
3. ✅ State percentiles are computed correctly for all 51 states (50 states + DC)
4. ✅ All percentile calculations match expected behavior

## Example Use Cases

### 1. Compare a specific county's performance nationally vs. within state
```python
import pandas as pd
df = pd.read_csv('county_metrics_detailed_20260311_180754.csv')

# Get Autauga County, Alabama metrics
autauga = df[df['FIPS'] == '01001']

# Compare national vs state percentiles
print(autauga[['Metric_Display_Name', 'National_Percentile', 'State_Percentile']])
```

### 2. Analyze reverse metrics across all counties
```python
# Get all reverse metrics
reverse = df[df['Is_Reverse_Metric'] == True]

# Verify lower raw values have higher percentiles
correlation = reverse.groupby('Metric_Database_Name').apply(
    lambda x: x['Raw_Value'].corr(x['National_Percentile'])
)
print(correlation)  # Should be negative for reverse metrics
```

### 3. Find counties with highest percentiles for specific metric
```python
# Get unemployment data
unemployment = df[df['Metric_Database_Name'] == 'Prosperity_Employment_UnemploymentRate']

# Sort by national percentile (descending = best performance)
best_employment = unemployment.nlargest(10, 'National_Percentile')
print(best_employment[['County', 'State', 'Raw_Value', 'National_Percentile']])
```

## Technical Notes

### Performance Optimizations
1. **Pre-computation of Z-scores**: All Z-scores calculated once upfront
2. **State percentile caching**: State percentiles computed once per state and cached
3. **Batch processing**: Processes all counties and metrics in a single pass

### Data Quality
- Skips metrics with NaN (missing) raw values
- Maintains data integrity from source CSV
- Preserves all metadata (units, years)

## Files Modified

1. **`test_percentile_logic.py`**: Enhanced with `export_all_metrics_to_csv()` function
2. **`TEST_SCRIPT_DOCUMENTATION.md`**: This documentation file

## Dependencies

- `pandas`: Data manipulation
- `numpy`: Numerical operations
- `local_data_provider.py`: Local CSV data provider
- `National_County_Dashboard.csv`: Source data file
- `display_names.csv`: Display name mappings

## Next Steps

After running the script, you can:
1. Import the CSV into Excel, Tableau, or other analytics tools
2. Perform statistical analysis on normalization approaches
3. Compare national vs. state percentile distributions
4. Validate reverse metric handling
5. Generate visualizations and reports
