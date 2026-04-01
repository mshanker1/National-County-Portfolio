# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Dash-based web application for visualizing county-level sustainability metrics across the United States. The dashboard displays interactive radar charts showing performance across People, Prosperity, and Place dimensions with ~3,100 counties nationwide.

**Security Model**: Each county has a unique password (format: `countyname2024`), plus a master password (`county_dashboard_2024`) for all counties.

## Running the Application

### Local CSV Mode (No Cloud Dependencies)
```bash
DATA_SOURCE=local python county_secure_dashboard.py
# Dashboard runs at: http://localhost:8050/?county=01001&key=autauga2024
```

### BigQuery Mode (Cloud Backend)
```bash
# Requires Google Cloud authentication
python county_secure_dashboard.py
# OR explicitly: DATA_SOURCE=bigquery python county_secure_dashboard.py
```

### Deployment to Google App Engine
```bash
gcloud app deploy app.yaml
```

## Data Processing Pipeline

The codebase implements a **3-stage data pipeline**:

### Stage 1: Database Loading (`stage1_database_loader.py`)
- Loads `National_County_Dashboard.csv` (3-row header: column names, units, years)
- Parses hierarchical metric names (e.g., `People_Health_LengthOfLife_LifeExpectancy`)
- Creates BigQuery tables: `counties`, `raw_metrics`, `raw_metrics_wide`
- **Run via**: `python stage1_database_loader.py`

### Stage 2: Normalization (`stage2_normalization.py`)
- Computes percentile ranks (0-100) for all metrics nationally
- Handles reverse metrics (where lower raw values = better performance)
- Aggregates individual metrics into sub-measure scores
- Creates BigQuery tables: `metric_statistics`, `normalized_metrics`, `aggregated_scores`
- **Run via**: `python stage2_normalization.py`
- **Verification**: `python stage2_verification_updated.py`

### Stage 3: State Comparisons (`enhanced_radar_v2_with_fast_state.py`)
- Pre-computes state-level percentiles for fast switching between national/state views
- Creates BigQuery tables: `state_percentiles`, `state_aggregated_scores`
- **Run via**: Execute as main script (contains Stage 3 builder code)

## Architecture

### Dual Data Provider Pattern

The dashboard supports two interchangeable data providers with **identical APIs**:

1. **`BigQueryRadarChartDataProvider`** (in `enhanced_radar_v2_with_fast_state.py`)
   - Queries Google BigQuery for percentile data
   - Used in production deployment (Google App Engine)

2. **`LocalCSVRadarChartDataProvider`** (in `local_data_provider.py`)
   - Reads `National_County_Dashboard.csv` directly into memory
   - Computes percentiles on-the-fly (2-4 second startup)
   - Zero cloud dependencies for local development

**Selection Logic** (in `county_secure_dashboard.py`):
```python
DATA_SOURCE = os.environ.get('DATA_SOURCE', 'bigquery').lower()
if DATA_SOURCE == 'local':
    provider = LocalCSVRadarChartDataProvider(...)
else:
    provider = BigQueryRadarChartDataProvider(...)
```

### Key Files

- **`county_secure_dashboard.py`**: Main Dash application (~3,600 lines)
  - Password authentication for each county
  - Interactive radar charts with drill-down detail views
  - National vs. state comparison modes
  - Contains hardcoded `COUNTY_PASSWORDS` dict mapping all ~3,100 FIPS codes

- **`enhanced_radar_v2_with_fast_state.py`**: BigQuery data provider
  - `BigQueryRadarChartDataProvider` class
  - `create_enhanced_radar_chart()` - main radar visualization
  - `create_detail_chart()` - metric drill-down charts
  - Stage 3 precomputation logic for state percentiles

- **`local_data_provider.py`**: Local CSV data provider
  - Drop-in replacement for BigQuery provider
  - Implements: `get_county_metrics()`, `get_submetric_details()`, `get_all_counties()`, `set_comparison_mode()`

- **`display_names.csv`**: Human-readable labels for database field names
  - Maps technical names (e.g., `People_Health`) to display names (e.g., "Health")

- **`National_County_Dashboard.csv`**: Master data file
  - Row 0: Column names (hierarchical: `Top_Sub_Group_Metric`)
  - Row 1: Units (e.g., "per 100,000", "%")
  - Row 2: Years (e.g., "2020", "2019-2021")
  - Row 3+: County data (FIPS, State, County, then metric values)

## Important Patterns

### Reverse Metrics

Certain metrics are "reverse" where **lower values = better performance** (e.g., `UnemploymentRate`, `CO2OrCapita`). These are defined in:
- `enhanced_radar_v2_with_fast_state.py`: `reverse_metrics` set (BigQuery version)
- `local_data_provider.py`: `_REVERSE_METRICS` set (local version)
- `stage2_normalization.py`: `reverse_metrics` set (data processing)

**Critical**: All three sets must stay synchronized. When adding/removing reverse metrics, update all three files.

### Productivity → Prosperity Renaming

The CSV file uses `Productivity_*` as a top-level prefix, but the dashboard expects `Prosperity_*`. The local provider automatically renames on load:
```python
# In local_data_provider.py _load_and_preprocess()
if col.startswith('Productivity_'):
    new_col = 'Prosperity_' + col[len('Productivity_'):]
```

### Display Name Resolution

Three-tier fallback for converting database names to display labels:
1. Check `display_names_map` (loaded from `display_names.csv`)
2. If not found, use raw sub-measure name (e.g., `People_Health` → "Health")
3. For metrics, split on underscores and title-case (e.g., `unemployment_rate` → "Unemployment Rate")

## Testing

### Stress Testing
```bash
python stress_test_3000_counties.py
```
- Tests concurrent access with 100+ simultaneous users
- Validates authentication across all counties
- Requires `County-Key.csv` with columns: `County`, `State`, `County Name`, `Key`

## Configuration Files

- **`requirements.txt`**: Python dependencies (Dash, Plotly, BigQuery client, etc.)
- **`app.yaml`**: Google App Engine deployment configuration
  - Runtime: Python 3.12
  - Instance class: F2
  - Contains Snowflake credentials (legacy, not currently used)
  - Auto-scaling: 0-10 instances based on CPU (65% target)

## Data Schema Notes

### Hierarchical Metric Naming
All metrics follow the pattern: `TopLevel_SubMeasure_[Group_]Metric`

Examples:
- `People_Health_LengthOfLife_LifeExpectancy` → Top: People, Sub: Health, Group: LengthOfLife, Metric: LifeExpectancy
- `Prosperity_Employment_UnemploymentRate` → Top: Prosperity, Sub: Employment, Metric: UnemploymentRate

### FIPS Codes
- 5-digit zero-padded strings (e.g., `"01001"` for Autauga County, AL)
- Used as primary key across all tables
- First 2 digits = state, last 3 digits = county

### Percentile Scoring
- All metrics normalized to 0-100 percentile ranks
- Sub-measures = mean of constituent metric percentiles
- Radar charts display sub-measure scores only (not individual metrics)
- Detail drill-downs show individual metric percentiles

## Known Issues & Gotchas

1. **"Premature Death" has a space**: The metric `People_Health_LengthOfLife_Premature Death` contains a literal space (not underscore). This must be preserved in all reverse metric sets.

2. **Population excluded from scoring**: `People_Population_Population` is a metadata field, not a scored sub-measure. It's explicitly excluded via `_EXCLUDE_SUB_MEASURES`.

3. **State comparison caching**: The local provider computes state percentiles on first use and caches results. Switching to a new state triggers a ~0.5s computation.

4. **Master password security**: The hardcoded master password `county_dashboard_2024` grants access to all counties. Do not expose in public repositories.
