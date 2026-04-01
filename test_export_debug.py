"""Quick debug script to test export function"""

import pandas as pd
from local_data_provider import LocalCSVRadarChartDataProvider

# Initialize provider
print("Loading provider...")
provider = LocalCSVRadarChartDataProvider()

# Check structure
print(f"\nProvider._raw shape: {provider._raw.shape}")
print(f"Provider._raw index type: {type(provider._raw.index)}")
print(f"Provider._raw index first 5: {provider._raw.index[:5].tolist()}")
print(f"\nProvider._pct shape: {provider._pct.shape}")
print(f"Provider._pct columns (first 10): {provider._pct.columns[:10].tolist()}")

print(f"\nProvider._metric_cols length: {len(provider._metric_cols)}")
print(f"Provider._metric_cols (first 10): {provider._metric_cols[:10]}")

# Get all counties
all_counties = provider.get_all_counties()
print(f"\nAll counties shape: {all_counties.shape}")
print(f"All counties index type: {type(all_counties.index)}")
print(f"All counties columns: {all_counties.columns.tolist()}")
print(f"All counties first row:")
print(all_counties.iloc[0])

# Test iteration
print(f"\nTesting iteration:")
for idx, (fips, row) in enumerate(all_counties.iterrows()):
    print(f"  Index {idx}: FIPS={fips}, County={row['county_name']}, State={row['state_name']}")
    if idx >= 2:
        break

# Test accessing raw data
fips_test = all_counties.index[0]
print(f"\nTesting raw data access for FIPS {fips_test}:")
print(f"  FIPS in provider._raw.index: {fips_test in provider._raw.index}")
if fips_test in provider._raw.index:
    metric_test = provider._metric_cols[0]
    print(f"  Test metric: {metric_test}")
    print(f"  Raw value: {provider._raw.loc[fips_test, metric_test]}")
    print(f"  Is NaN: {pd.isna(provider._raw.loc[fips_test, metric_test])}")

# Count non-NaN values
print(f"\nNon-NaN counts:")
for i, col in enumerate(provider._metric_cols[:5]):
    non_nan = provider._raw[col].notna().sum()
    print(f"  {col}: {non_nan} non-NaN values")
