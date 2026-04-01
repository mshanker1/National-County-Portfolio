"""
LocalCSVRadarChartDataProvider
==============================
A drop-in replacement for BigQueryRadarChartDataProvider that reads directly
from the local CSV files.  No Google Cloud credentials or network access required.

Public API is identical to BigQueryRadarChartDataProvider so that the Dash
dashboard and all chart-rendering code require no changes — only the provider
instantiation block in county_secure_dashboard.py switches on DATA_SOURCE=local.

Startup sequence (runs once, ~2-4 seconds for 3,100 counties):
  1. Read National_County_Dashboard.csv (3-row multi-level header)
  2. Clean and coerce all metric columns to float
  3. Compute national percentile ranks for every county × metric
  4. Aggregate per-metric ranks to per-sub-measure scores
  5. Cache everything in memory; state comparisons are computed on first use

How to run:
  DATA_SOURCE=local python county_secure_dashboard.py
  # then open: http://localhost:8050/?county=01001&key=autauga2024
"""

import os
import re
import time

import numpy as np
import pandas as pd


class LocalCSVRadarChartDataProvider:
    """
    In-memory, CSV-backed data provider with the same public interface as
    BigQueryRadarChartDataProvider.

    Attributes (same names as BigQuery version, intentionally):
        stage            int  – 3 (national + state comparisons available)
        comparison_mode  str  – 'national' | 'state'
        current_state    str  – state name when in state mode, else None
        display_names_map dict – db_name -> human-readable label
        reverse_metrics  set  – metric names where lower value = better
    """

    # ── Reverse-metric set ────────────────────────────────────────────────────
    # Kept in sync with enhanced_radar_v2_with_fast_state.py.
    # These are the *exact* column names that appear in National_County_Dashboard.csv.
    _REVERSE_METRICS = {
        # People – Community
        'People_Community_LongCommuteAndDrivesAlone',
        'People_Community_ViolentCrimeRate',
        # People – Health behaviours
        'People_Health_HealthBehaviours_AdultsSmoking',
        'People_Health_HealthBehaviours_AdultsWithObesity',
        'People_Health_HealthBehaviours_ExcessiveDrinking',
        'People_Health_HealthBehaviours_InsufficientSleep',
        'People_Health_HealthBehaviours_PhysicallyInactive',
        # People – Health resources
        'People_Health_HealthResources_AccessToCare_Uninsured',
        'People_Health_HealthResources_QualityOfCare_PreventableHospitalizationRate',
        # People – Health outcomes
        'People_Health_LengthOfLife_Premature Death',   # note the space
        'People_Health_QualityOfLife_AdultWithDiabetes',
        'People_Health_QualityOfLife_FreqMenDistress',
        'People_Health_QualityOfLife_FreqPhyDistress',
        'People_Health_QualityOfLife_HIVPrevRate',
        # People – Wealth
        'People_Wealth_ChildPoverty',
        'People_Wealth_IncomeRatio80by20',
        # Place – Climate
        'Place_ClimateAndResilience_CO2OrCapita',
        # Place – Air quality
        'Place_LandAirWater_AirQualityIndexPerPm2.5',
        # Prosperity – Business
        'Prosperity_Business_RatioOfEstablishmentBirthsPerDeaths2020',
        # Prosperity – Employment
        'Prosperity_Employment_UnemploymentRate',
        # Prosperity – Government
        'Prosperity_Government_DependencyRatio',
        'Prosperity_Government_ViolentCrimeRate',
        # Prosperity – Nonprofit
        'Prosperity_Nonprofit_WageRatio',
    }

    # Sub-measures to exclude from the radar chart (population is metadata, not scored)
    _EXCLUDE_SUB_MEASURES = {'People_Population'}

    def __init__(
        self,
        csv_file='National_County_Dashboard.csv',
        county_key_file='County-Key.csv',
        display_names_file='display_names.csv',
    ):
        self.csv_file = csv_file
        self.county_key_file = county_key_file
        self.display_names_file = display_names_file

        # ── Public attributes (matching BigQueryRadarChartDataProvider) ────────
        self.comparison_mode = 'national'
        self.current_state = None
        self.stage = 2               # upgraded to 3 after successful load
        self.display_names_map = {}
        self.reverse_metrics = self._REVERSE_METRICS

        # ── Internal caches ────────────────────────────────────────────────────
        self._raw = None          # DataFrame: county × metric  (raw float values)
        self._pct = None          # DataFrame: county × metric  (national pct ranks 0-100)
        self._sub = None          # DataFrame: county × sub_measure (national agg scores)
        self._county_info = None  # DataFrame indexed by FIPS: state, county columns
        self._units = {}          # metric_col -> unit string
        self._years = {}          # metric_col -> year string
        self._metric_cols = []    # ordered list of metric column names
        self._sub_map = {}        # sub_measure_key -> [metric_col, ...]
        self._sub_cols = []       # ordered list of sub-measure keys
        self._state_cache = {}    # state_name -> (state_pct_df, state_sub_df)

        self._load_display_names()
        self._load_and_preprocess()

    # ──────────────────────────────────────────────────────────────────────────
    # Internal helpers
    # ──────────────────────────────────────────────────────────────────────────

    def _load_display_names(self):
        """Load db_name → display_name mappings from display_names.csv."""
        if not os.path.exists(self.display_names_file):
            print(f"⚠️  [Local] Display names file not found: {self.display_names_file}")
            return
        try:
            df = pd.read_csv(self.display_names_file, comment='#')
            for _, row in df.iterrows():
                db  = row.get('database_name')
                disp = row.get('display_name')
                if pd.notna(db) and pd.notna(disp) and str(db).strip():
                    self.display_names_map[str(db).strip()] = str(disp).strip()
            print(f"✅ [Local] Loaded {len(self.display_names_map)} display name mappings")
        except Exception as exc:
            print(f"⚠️  [Local] Could not load display names: {exc}")

    @staticmethod
    def _clean_numeric(series):
        """
        Coerce a string Series to float.
        Handles: $1,234.5  |  (negative)  |  90%  |  whitespace  |  blank → NaN
        """
        def _parse(v):
            if pd.isna(v):
                return np.nan
            s = str(v).strip()
            if s == '':
                return np.nan
            # Parenthetical negatives: (123) → -123
            if s.startswith('(') and s.endswith(')'):
                s = '-' + s[1:-1]
            # Strip formatting characters
            s = re.sub(r'[$,\s%]', '', s)
            try:
                return float(s)
            except (ValueError, TypeError):
                return np.nan

        return series.apply(_parse)

    def _percentile_ranks(self, df):
        """
        Compute percentile rank 0-100 for every column, across rows.
        NaN values are preserved as NaN (excluded from ranking).
        Uses pandas rank with pct=True so ties are averaged.

        IMPORTANT: Applies reversal for reverse metrics (where lower is better).
        For reverse metrics, percentile = 100 - raw_percentile.
        """
        # Compute raw percentiles for all columns
        pct_df = df.rank(axis=0, pct=True, na_option='keep') * 100

        # Apply reversal for reverse metrics
        for col in df.columns:
            if col in self._REVERSE_METRICS:
                pct_df[col] = 100 - pct_df[col]

        return pct_df

    @staticmethod
    def _sub_measure_key(col_name):
        """
        Parse a metric column name into its sub-measure key.
        'People_Health_LengthOfLife_LifeExpectancy' → 'People_Health'
        'Prosperity_Employment_UnemploymentRate'   → 'Prosperity_Employment'
        Returns None if col_name is not a recognised metric.

        NOTE: By the time this is called, 'Productivity_*' columns have already
        been renamed to 'Prosperity_*', so only 'Prosperity' needs to be listed.
        """
        parts = col_name.split('_')
        if len(parts) < 2:
            return None
        if parts[0] not in ('People', 'Prosperity', 'Place'):
            return None
        return f"{parts[0]}_{parts[1]}"

    def _load_and_preprocess(self):
        """
        Load the CSV, compute percentile rankings, cache everything.
        Called once at startup.
        """
        t0 = time.time()
        print("⏳ [Local] Loading and preprocessing CSV data …")

        # ── 1. Read CSV without parsing headers ───────────────────────────────
        raw_df = pd.read_csv(
            self.csv_file, header=None, dtype=str, low_memory=False
        )

        col_names  = raw_df.iloc[0].tolist()   # row 0 → column names
        units_row  = raw_df.iloc[1].tolist()   # row 1 → units
        years_row  = raw_df.iloc[2].tolist()   # row 2 → years

        data = raw_df.iloc[3:].copy()
        data.columns = col_names
        data = data.reset_index(drop=True)

        # ── 2. Normalise identifier columns ───────────────────────────────────
        # First three columns are: Fips, State, County
        fips_col   = col_names[0]   # 'Fips'
        state_col  = col_names[1]   # 'State'
        county_col = col_names[2]   # 'County'

        # Zero-pad FIPS to 5 digits (CSV already has '01001' but be safe)
        data[fips_col] = data[fips_col].apply(
            lambda v: str(v).strip().zfill(5) if pd.notna(v) and str(v).strip() else v
        )

        # ── 3. Identify metric columns ─────────────────────────────────────────
        # Everything after the three identifier columns that has a valid name
        metric_cols = [
            c for c in col_names[3:]
            if isinstance(c, str) and c.strip()
        ]

        # Store unit / year metadata per metric
        col_index = {c: i for i, c in enumerate(col_names)}
        for col in metric_cols:
            idx = col_index.get(col)
            if idx is not None:
                u = units_row[idx]
                y = years_row[idx]
                self._units[col] = str(u).strip() if pd.notna(u) else ''
                self._years[col] = str(y).strip() if pd.notna(y) else ''

        # ── 4. Convert metrics to numeric ─────────────────────────────────────
        metrics_df = data[metric_cols].copy()
        for col in metric_cols:
            metrics_df[col] = self._clean_numeric(metrics_df[col])

        # ── 4b. Rename Productivity_* → Prosperity_* ──────────────────────────
        # The CSV uses "Productivity" as the top-level prefix, but the dashboard,
        # display_names.csv, and enhanced_radar_v2_with_fast_state.py all expect
        # "Prosperity".  Renaming here keeps everything downstream consistent.
        rename_map = {}
        for col in list(metrics_df.columns):
            if col.startswith('Productivity_'):
                new_col = 'Prosperity_' + col[len('Productivity_'):]
                rename_map[col] = new_col
        if rename_map:
            metrics_df = metrics_df.rename(columns=rename_map)
            # Update units/years dicts to use the new names
            for old_col, new_col in rename_map.items():
                if old_col in self._units:
                    self._units[new_col] = self._units.pop(old_col)
                if old_col in self._years:
                    self._years[new_col] = self._years.pop(old_col)
            # Update metric_cols list
            metric_cols = [rename_map.get(c, c) for c in metric_cols]
            print(f"✅ [Local] Renamed {len(rename_map)} Productivity_* columns → Prosperity_*")

        # Index by FIPS for O(1) row access
        metrics_df.index = data[fips_col].values

        # ── 5. Store county identity ──────────────────────────────────────────
        county_info = data[[fips_col, state_col, county_col]].copy()
        county_info.columns = ['fips', 'state', 'county']
        self._county_info = county_info.set_index('fips')

        # ── 6. National percentile ranks ──────────────────────────────────────
        print("📊 [Local] Computing national percentile ranks …")
        pct_df = self._percentile_ranks(metrics_df)

        # ── 7. Group metrics into sub-measures ────────────────────────────────
        sub_map = {}
        for col in metric_cols:
            sub_key = self._sub_measure_key(col)
            if sub_key and sub_key not in self._EXCLUDE_SUB_MEASURES:
                sub_map.setdefault(sub_key, []).append(col)

        # ── 8. Aggregate to sub-measure level (mean of metric percentiles) ─────
        sub_scores = {}
        for sub_key, cols in sub_map.items():
            sub_scores[sub_key] = pct_df[cols].mean(axis=1, skipna=True)

        sub_df = pd.DataFrame(sub_scores)
        sub_df.index = metrics_df.index

        # ── 9. Persist everything ─────────────────────────────────────────────
        self._raw        = metrics_df
        self._pct        = pct_df
        self._sub        = sub_df
        self._metric_cols = metric_cols
        self._sub_map    = sub_map
        self._sub_cols   = list(sub_map.keys())

        # State comparison is computable on demand → report Stage 3
        self.stage = 3

        elapsed = time.time() - t0
        print(
            f"✅ [Local] Ready — {len(metrics_df)} counties, "
            f"{len(metric_cols)} metrics, "
            f"{len(self._sub_cols)} sub-measures  "
            f"({elapsed:.1f}s)"
        )
        print("✅ [Local] Stage 3 available (state comparisons computed on demand)")

    def _get_state_data(self, state_code):
        """
        Return (state_pct_df, state_sub_df) for the given state name.
        Results are cached after first computation.
        Falls back to national data if the state is not found.
        """
        if state_code in self._state_cache:
            return self._state_cache[state_code]

        # Match state name (case-insensitive fallback)
        mask = self._county_info['state'] == state_code
        if not mask.any():
            mask = self._county_info['state'].str.lower() == state_code.lower()

        state_fips = self._county_info[mask].index
        if len(state_fips) == 0:
            print(f"⚠️  [Local] State '{state_code}' not found — using national")
            return self._pct, self._sub

        state_raw = self._raw.loc[self._raw.index.isin(state_fips)]
        state_pct = self._percentile_ranks(state_raw)

        sub_scores = {}
        for sub_key, cols in self._sub_map.items():
            valid = [c for c in cols if c in state_pct.columns]
            if valid:
                sub_scores[sub_key] = state_pct[valid].mean(axis=1, skipna=True)

        state_sub = pd.DataFrame(sub_scores)
        state_sub.index = state_raw.index

        self._state_cache[state_code] = (state_pct, state_sub)
        print(
            f"✅ [Local] Cached state percentiles for {state_code} "
            f"({len(state_fips)} counties)"
        )
        return state_pct, state_sub

    # ──────────────────────────────────────────────────────────────────────────
    # Public API  (identical signatures to BigQueryRadarChartDataProvider)
    # ──────────────────────────────────────────────────────────────────────────

    def set_comparison_mode(self, mode='national', state_code=None):
        """Switch between national and state-level percentile comparisons."""
        if mode == 'state' and state_code:
            self.comparison_mode = 'state'
            self.current_state   = state_code
            self._get_state_data(state_code)   # pre-warm cache
            print(f"✅ [Local] Switched to state comparison: {state_code}")
        else:
            self.comparison_mode = 'national'
            self.current_state   = None
            print("✅ [Local] Switched to national comparison")

    def get_display_name(self, database_name):
        """Return the human-readable label for a database field name."""
        return self.display_names_map.get(database_name, database_name)

    def is_reverse_metric(self, metric_name):
        """Return True if a lower raw value means better performance."""
        return metric_name in self.reverse_metrics

    def get_county_population(self, county_fips):
        """Return the total population for a county as int, or None."""
        pop_col = 'People_Population_Population'
        if pop_col not in self._raw.columns:
            return None
        try:
            val = self._raw.loc[county_fips, pop_col]
            return None if pd.isna(val) else int(val)
        except (KeyError, ValueError):
            return None

    def get_all_counties(self):
        """
        Return a DataFrame of counties that have sufficient data.
        Columns: fips_code, county_name, state_code, state_name, data_completeness
        Mirrors the BigQuery version (requires >= 8 non-null sub-measures).
        """
        completeness = self._sub.notna().sum(axis=1)
        sufficient_fips = completeness[completeness >= 8].index

        info = self._county_info.loc[
            self._county_info.index.isin(sufficient_fips)
        ].copy().reset_index()

        info.columns = ['fips_code', 'state_code', 'county_name']
        info['state_name']        = info['state_code']
        info['data_completeness'] = (
            completeness.reindex(info['fips_code']).values
        )
        return info.sort_values(['state_code', 'county_name']).reset_index(drop=True)

    def get_county_metrics(self, county_fips):
        """
        Return (county_info_df, structured_data) for one county.

        county_info_df  – single-row DataFrame with columns:
                          county_name, state_code, state_name
        structured_data – nested dict:
                          {'People': {'Health': pct, ...},
                           'Prosperity': {...},
                           'Place': {...}}
        """
        if county_fips not in self._county_info.index:
            return pd.DataFrame(), {}

        row = self._county_info.loc[county_fips]
        county_info_df = pd.DataFrame([{
            'county_name': row['county'],
            'state_code':  row['state'],
            'state_name':  row['state'],
        }])

        # Choose comparison basis
        if self.comparison_mode == 'state' and self.current_state:
            _, sub_df = self._get_state_data(self.current_state)
        else:
            sub_df = self._sub

        if county_fips not in sub_df.index:
            return county_info_df, {}

        county_row = sub_df.loc[county_fips]

        structured_data = {'People': {}, 'Prosperity': {}, 'Place': {}}

        for sub_key in self._sub_cols:
            parts = sub_key.split('_', 1)   # ['People', 'Health']
            if len(parts) < 2:
                continue
            top_level = parts[0]
            if top_level not in structured_data:
                continue

            score = county_row.get(sub_key, np.nan)
            if pd.isna(score):
                continue

            # Map to display name  (e.g. 'People_Health' → 'Health')
            display_key = self.get_display_name(sub_key)
            if display_key == sub_key:
                # No mapping found — use the raw sub part
                display_key = parts[1]

            structured_data[top_level][display_key] = float(score)

        return county_info_df, structured_data

    def get_submetric_details(self, county_fips, top_level, sub_category):
        """
        Return a DataFrame of individual metric details for one sub-category.

        Mirrors the BigQuery version's output columns:
          metric_name, sub_metric_name, metric_value, percentile_rank,
          unit, year, is_reverse_metric, display_name

        Parameters
        ----------
        county_fips  : str  e.g. '01001'
        top_level    : str  e.g. 'People'
        sub_category : str  display name e.g. 'Health'
        """
        # ── Resolve display name back to sub-measure DB key ───────────────────
        # Try display_names_map: find the entry whose display_name == sub_category
        # AND whose db_name contains top_level.
        db_sub_key = None
        for db_name, disp_name in self.display_names_map.items():
            if disp_name == sub_category and top_level in db_name:
                db_sub_key = db_name
                break

        if db_sub_key is None:
            # Fallback: construct 'People_Health' style key directly
            db_sub_key = f"{top_level}_{sub_category.replace(' ', '').replace(',', '')}"

        # Get the metric columns for this sub-measure
        cols = self._sub_map.get(db_sub_key)
        if not cols:
            # Case-insensitive search
            for key, key_cols in self._sub_map.items():
                if key.lower() == db_sub_key.lower():
                    cols = key_cols
                    break

        if not cols or county_fips not in self._raw.index:
            return pd.DataFrame()

        # Choose comparison percentile source
        if self.comparison_mode == 'state' and self.current_state:
            pct_df, _ = self._get_state_data(self.current_state)
        else:
            pct_df = self._pct

        # ── Build per-metric result rows ──────────────────────────────────────
        records = []
        for col in cols:
            if col not in self._raw.columns:
                continue

            raw_val = self._raw.loc[county_fips, col]

            if county_fips in pct_df.index and col in pct_df.columns:
                pct_val = pct_df.loc[county_fips, col]
            else:
                pct_val = np.nan

            if pd.isna(pct_val):
                continue   # skip missing metrics (matches BigQuery IS NOT NULL filter)

            # Parse sub_metric_name from column: parts after top_sub
            parts = col.split('_')
            sub_metric = '_'.join(parts[2:]) if len(parts) > 2 else col

            # Display name
            display_name = self.get_display_name(col)
            if display_name == col and sub_metric:
                display_name = sub_metric.replace('_', ' ').title()

            records.append({
                'metric_name':       col,
                'sub_metric_name':   sub_metric,
                'metric_value':      raw_val,
                'percentile_rank':   pct_val,
                'unit':              self._units.get(col, ''),
                'year':              self._years.get(col, ''),
                'is_reverse_metric': self.is_reverse_metric(col),
                'display_name':      display_name,
            })

        if not records:
            return pd.DataFrame()

        result = pd.DataFrame(records)
        result = result.sort_values(
            'percentile_rank', ascending=False
        ).reset_index(drop=True)
        return result
