# Display Name Fix - "Premature Death" Label

## Issue

The dashboard was showing **"lengthoflife Premature Death"** instead of **"Premature Death"** for the Premature Death metric.

## Root Cause

**Mismatch between column name and display_names.csv mapping:**

### Actual Column Name (in CSV)
```
"People_Health_LengthOfLife_Premature Death"  ← Has a SPACE
```

### Display Names Entry (before fix)
```
People_Health_LengthOfLife_PrematureDeath,Premature Death,metric_group  ← No space
```

Since the lookup failed, the code fell back to auto-generating the display name from the column parts.

## Why "lengthoflife" Appeared

The fallback logic in `local_data_provider.py` (lines 537-539):

```python
display_name = self.get_display_name(col)  # Returns col if not found
if display_name == col and sub_metric:
    display_name = sub_metric.replace('_', ' ').title()
```

For `"People_Health_LengthOfLife_Premature Death"`:
1. `sub_metric = 'LengthOfLife_Premature Death'` (parts after People_Health)
2. `.replace('_', ' ')` → `'LengthOfLife Premature Death'`
3. `.title()` → `'Lengthoflife Premature Death'`

The `.title()` method lowercases everything except the first letter of each word, turning "LengthOfLife" into "Lengthoflife".

## The Fix

**File**: `display_names.csv` (line 48)

**Before** (incorrect):
```csv
People_Health_LengthOfLife_PrematureDeath,Premature Death,metric_group
```

**After** (correct):
```csv
People_Health_LengthOfLife_Premature Death,Premature Death,metric_group
```

Added the space in "Premature Death" to match the actual column name.

## Verification

```python
from local_data_provider import LocalCSVRadarChartDataProvider
provider = LocalCSVRadarChartDataProvider()

metric_col = 'People_Health_LengthOfLife_Premature Death'
display_name = provider.get_display_name(metric_col)

print(display_name)  # "Premature Death" ✓
```

## Note About the Space in Column Name

This is a **known quirk** mentioned in `CLAUDE.md`:

> **"Premature Death" has a space**: The metric `People_Health_LengthOfLife_Premature Death` contains a literal space (not underscore). This must be preserved in all reverse metric sets.

The space must be maintained in:
1. ✅ `display_names.csv` mappings
2. ✅ Reverse metrics sets (Local and BigQuery)
3. ✅ Any code that references this metric

## Impact

- **Before**: Dashboard showed "lengthoflife Premature Death"
- **After**: Dashboard shows "Premature Death"
- **Applies to**: Both Local CSV and BigQuery modes

## Related Files

- **Fixed**: `display_names.csv` (line 48)
- **Fallback logic**: `local_data_provider.py` (lines 537-539)
- **Documentation**: `CLAUDE.md` (mentions the space issue)

## Status

✅ Fixed and verified
✅ Dashboard restarted with correction
✅ Display name now shows correctly as "Premature Death"
