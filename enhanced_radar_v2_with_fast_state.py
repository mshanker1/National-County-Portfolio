import pandas as pd
import sqlite3
import numpy as np
from scipy import stats
import os
import time

class RadarChartDataProviderV2:
    """
    Enhanced data provider with human-readable names and state-level comparison support
    """
    
    def __init__(self, db_file_path='sustainability_data.db', display_names_file='display_names.csv'):#Need to change display_names.csv to new csv file name 
        self.db_file_path = db_file_path
        self.display_names_file = display_names_file
        self.display_names_map = {}
        self.comparison_mode = 'national'  # 'national' or 'state'
        self.current_state = None
        self._load_display_names()
        self._check_database_status()
    
    def _load_display_names(self):
        """Load human-readable display names from CSV"""
        if os.path.exists(self.display_names_file):
            try:
                df = pd.read_csv(self.display_names_file, comment='#')
                for _, row in df.iterrows():
                    self.display_names_map[row['database_name']] = row['display_name']
                print(f"✅ Loaded {len(self.display_names_map)} display name mappings")
            except Exception as e:
                print(f"⚠️  Could not load display names: {e}")
        else:
            print(f"⚠️  Display names file not found: {self.display_names_file}")
    
    def get_display_name(self, database_name):
        """Get human-readable name for a database field"""
        return self.display_names_map.get(database_name, database_name)
    
    def _check_database_status(self):
        """Check what stage the database is in"""
        try:
            conn = self.get_database_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            conn.close()
            
            # Check for fast state comparison tables
            has_state_tables = 'state_percentiles' in tables and 'state_aggregated_scores' in tables
            
            if 'aggregated_scores' in tables and 'normalized_metrics' in tables:
                if has_state_tables:
                    self.stage = 3  # New stage for fast state comparisons
                    print("✅ Database Status: Stage 3 Complete (Fast state comparisons available)")
                else:
                    self.stage = 2
                    print("✅ Database Status: Stage 2 Complete (Normalized data available)")
                    print("💡 Run create_state_percentiles_table() for instant state comparisons")
            elif 'raw_metrics' in tables and 'counties' in tables:
                self.stage = 1
                print("⚠️  Database Status: Stage 1 Complete (Raw data only - run Stage 2 for normalization)")
            else:
                self.stage = 0
                print("❌ Database Status: No data found - run Stage 1 first")
                
        except Exception as e:
            self.stage = 0
            print(f"❌ Database Error: {e}")
    
    def get_database_connection(self):
        """Get connection to sustainability database"""
        return sqlite3.connect(self.db_file_path)
    
    def set_comparison_mode(self, mode='national', state_code=None):
        """Set comparison mode to national or state level"""
        if mode == 'state' and state_code:
            self.comparison_mode = 'state'
            self.current_state = state_code
            print(f"✅ Switched to state-level comparison for {state_code}")
        else:
            self.comparison_mode = 'national'
            self.current_state = None
            print("✅ Switched to national-level comparison")
    
    def get_all_counties(self):
        """Get list of all counties for dropdown"""
        conn = self.get_database_connection()
        
        counties_df = pd.read_sql("""
            SELECT 
                c.fips as fips_code,
                c.county as county_name,
                c.state as state_code,
                c.state as state_name,
                COUNT(a.measure_name) as data_completeness
            FROM counties c
            LEFT JOIN aggregated_scores a ON c.fips = a.fips 
                AND a.measure_level = 'sub_measure' 
                AND a.normalized_score IS NOT NULL
            GROUP BY c.fips, c.county, c.state
            HAVING data_completeness >= 8  -- Only counties with good data coverage
            ORDER BY c.state, c.county
        """, conn)
        
        conn.close()
        return counties_df
    
    def create_state_percentiles_table(self):
        """Create state-level percentile rankings for all metrics - Stage 2.5 -> Stage 3"""
        if self.stage < 2:
            print("❌ Please run Stage 1 and Stage 2 first")
            return False
        
        conn = self.get_database_connection()
        
        print("🏛️ Creating state-level percentile rankings...")
        start_time = time.time()
        
        # Create state percentiles table
        conn.execute("DROP TABLE IF EXISTS state_percentiles")
        conn.execute("""
            CREATE TABLE state_percentiles (
                fips TEXT,
                state_code TEXT,
                metric_name TEXT,
                raw_value REAL,
                state_percentile REAL,
                is_missing INTEGER,
                PRIMARY KEY (fips, metric_name)
            )
        """)
        
        # Get all states
        states_query = """
            SELECT DISTINCT state FROM counties 
            ORDER BY state
        """
        states_df = pd.read_sql(states_query, conn)
        
        total_states = len(states_df)
        print(f"📊 Processing {total_states} states...")
        
        for idx, state_row in states_df.iterrows():
            state_code = state_row['state']
            print(f"   Processing {state_code} ({idx+1}/{total_states})...")
            
            # Get all metrics for counties in this state
            state_metrics_query = """
                SELECT 
                    nm.fips,
                    nm.metric_name,
                    nm.raw_value,
                    nm.is_missing,
                    ms.is_reverse_metric,
                    c.state
                FROM normalized_metrics nm
                JOIN counties c ON nm.fips = c.fips
                JOIN metric_statistics ms ON nm.metric_name = ms.metric_name
                WHERE c.state = ?
                AND nm.is_missing = 0
                AND nm.raw_value IS NOT NULL
            """
            
            state_metrics_df = pd.read_sql(state_metrics_query, conn, params=[state_code])
            
            if state_metrics_df.empty:
                continue
                
            # Calculate state percentiles for each metric
            state_percentile_data = []
            
            for metric_name in state_metrics_df['metric_name'].unique():
                metric_data = state_metrics_df[state_metrics_df['metric_name'] == metric_name]
                
                if len(metric_data) < 2:  # Need at least 2 data points for percentiles
                    continue
                    
                is_reverse = metric_data['is_reverse_metric'].iloc[0]
                values = metric_data['raw_value'].values
                
                for _, row in metric_data.iterrows():
                    county_value = row['raw_value']
                    
                    if is_reverse:
                        # For "lower is better" metrics, reverse the percentile
                        percentile = 100 - stats.percentileofscore(values, county_value, kind='rank')
                    else:
                        # For "higher is better" metrics, normal percentile
                        percentile = stats.percentileofscore(values, county_value, kind='rank')
                    
                    state_percentile_data.append({
                        'fips': row['fips'],
                        'state_code': state_code,
                        'metric_name': metric_name,
                        'raw_value': county_value,
                        'state_percentile': percentile,
                        'is_missing': 0
                    })
            
            # Insert state percentiles for this state
            if state_percentile_data:
                state_percentiles_df = pd.DataFrame(state_percentile_data)
                state_percentiles_df.to_sql('state_percentiles', conn, if_exists='append', index=False)
        
        # Create state-level aggregated scores
        print("🏛️ Creating state-level aggregated scores...")
        
        conn.execute("DROP TABLE IF EXISTS state_aggregated_scores")
        conn.execute("""
            CREATE TABLE state_aggregated_scores (
                fips TEXT,
                state_code TEXT,
                measure_name TEXT,
                measure_level TEXT,
                parent_measure TEXT,
                state_percentile_rank REAL,
                normalized_score REAL,
                component_count INTEGER,
                completeness_ratio REAL,
                PRIMARY KEY (fips, measure_name, measure_level)
            )
        """)
        
        # Calculate state aggregated scores similar to national ones
        for idx, state_row in states_df.iterrows():
            state_code = state_row['state']
            print(f"   Creating aggregated scores for {state_code} ({idx+1}/{total_states})...")
            
            # Get all counties in this state
            state_counties_query = """
                SELECT fips FROM counties WHERE state = ?
            """
            state_counties = pd.read_sql(state_counties_query, conn, params=[state_code])
            
            for _, county_row in state_counties.iterrows():
                county_fips = county_row['fips']
                
                # Calculate state-level sub-measure scores
                for top_level in ['Society', 'Economy', 'Environment']: #Changed People to Society as per new csv file
                    submeasures_query = """
                        SELECT DISTINCT 
                            CASE 
                                WHEN rm.top_level = 'Society' THEN 'Society_' || rm.sub_measure
                                WHEN rm.top_level = 'Economy' THEN 'Economy_' || rm.sub_measure  
                                WHEN rm.top_level = 'Environment' THEN 'Environment_' || rm.sub_measure
                            END as measure_name,
                            rm.sub_measure
                        FROM raw_metrics rm
                        WHERE rm.top_level = ? AND rm.fips = ?
                    """
                    
                    submeasures = pd.read_sql(submeasures_query, conn, params=[top_level, county_fips])
                    
                    for _, submeasure_row in submeasures.iterrows():
                        measure_name = submeasure_row['measure_name']
                        sub_measure = submeasure_row['sub_measure']
                        
                        # Get state percentiles for this sub-measure
                        submeasure_percentiles_query = """
                            SELECT AVG(sp.state_percentile) as avg_state_percentile,
                                   COUNT(*) as component_count
                            FROM state_percentiles sp
                            JOIN raw_metrics rm ON sp.fips = rm.fips AND sp.metric_name = rm.metric_name
                            WHERE sp.fips = ? 
                            AND rm.top_level = ?
                            AND rm.sub_measure = ?
                            AND sp.state_percentile IS NOT NULL
                        """
                        
                        result = pd.read_sql(submeasure_percentiles_query, conn, 
                                           params=[county_fips, top_level, sub_measure])
                        
                        if not result.empty and result.iloc[0]['avg_state_percentile'] is not None:
                            avg_percentile = result.iloc[0]['avg_state_percentile']
                            component_count = result.iloc[0]['component_count']
                            
                            # Insert state aggregated score
                            conn.execute("""
                                INSERT OR REPLACE INTO state_aggregated_scores 
                                (fips, state_code, measure_name, measure_level, parent_measure, 
                                 state_percentile_rank, normalized_score, component_count, completeness_ratio)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, (county_fips, state_code, measure_name, 'sub_measure', top_level,
                                  avg_percentile, avg_percentile/100, component_count, 1.0))
        
        # Create indexes for performance
        print("🚀 Creating database indexes for fast queries...")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_state_percentiles_fips ON state_percentiles(fips)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_state_percentiles_state ON state_percentiles(state_code)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_state_agg_fips ON state_aggregated_scores(fips)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_state_agg_state ON state_aggregated_scores(state_code)")
        
        conn.commit()
        conn.close()
        
        total_time = time.time() - start_time
        print(f"✅ State percentile calculations complete in {total_time:.1f} seconds!")
        print("⚡ State comparisons will now be as fast as national comparisons")
        
        # Update stage
        self.stage = 3
        return True
    
    def get_county_metrics_fast_state(self, county_fips):
        """Get county metrics using pre-calculated state percentiles for speed"""
        conn = self.get_database_connection()
        
        # Check if state percentiles table exists
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='state_percentiles'")
        has_state_table = cursor.fetchone() is not None
        
        if not has_state_table:
            print("⚠️ State percentiles not pre-calculated. Using slower method.")
            conn.close()
            return self.get_county_metrics(county_fips)  # Fallback to original method
        
        # Get county information
        county_info = pd.read_sql("""
            SELECT 
                county as county_name,
                state as state_code,
                state as state_name
            FROM counties 
            WHERE fips = ?
        """, conn, params=[county_fips])
        
        if county_info.empty:
            conn.close()
            return pd.DataFrame(), {}
        
        if self.comparison_mode == 'state':
            # Use pre-calculated state percentiles (FAST!)
            submeasures_query = """
                SELECT 
                    parent_measure as top_level,
                    measure_name,
                    CASE 
                        WHEN parent_measure = 'Society' THEN REPLACE(measure_name, 'Society_', '') -- Changed Society to Society as per new csv file
                        WHEN parent_measure = 'Economy' THEN REPLACE(measure_name, 'Economy_', '')
                        WHEN parent_measure = 'Environment' THEN REPLACE(measure_name, 'Environment_', '')
                    END as sub_measure,
                    state_percentile_rank as percentile_rank,
                    normalized_score,
                    component_count,
                    completeness_ratio
                FROM state_aggregated_scores
                WHERE fips = ? 
                AND measure_level = 'sub_measure'
                AND state_percentile_rank IS NOT NULL
                AND measure_name NOT LIKE '%Population%'
                ORDER BY parent_measure, measure_name
            """
            
            submeasures_df = pd.read_sql(submeasures_query, conn, params=[county_fips])
            
        else:
            # Use national percentiles (original method)
            submeasures_query = """
                SELECT 
                    parent_measure as top_level,
                    measure_name,
                    CASE 
                        WHEN parent_measure = 'Society' THEN REPLACE(measure_name, 'Society_', '') -- Changed Society to Society as per new csv file
                        WHEN parent_measure = 'Economy' THEN REPLACE(measure_name, 'Economy_', '')
                        WHEN parent_measure = 'Environment' THEN REPLACE(measure_name, 'Environment_', '')
                    END as sub_measure,
                    percentile_rank,
                    normalized_score,
                    component_count,
                    completeness_ratio
                FROM aggregated_scores
                WHERE fips = ? 
                AND measure_level = 'sub_measure'
                AND normalized_score IS NOT NULL
                AND measure_name NOT LIKE '%Population%'
                ORDER BY parent_measure, measure_name
            """
            
            submeasures_df = pd.read_sql(submeasures_query, conn, params=[county_fips])
        
        # Structure data in the format expected by radar chart
        structured_data = {
            'Society': {},    #Changed Society to Society as per new csv file
            'Economy': {},   
            'Environment': {}     
        }
        
        # Map the data to the expected structure
        top_level_mapping = {
            'Society': 'Society',#Changed Society to Society as per new csv file
            'Economy': 'Economy', 
            'Environment': 'Environment'
        }
        
        for _, row in submeasures_df.iterrows():
            top_level_key = top_level_mapping.get(row['top_level'])
            if top_level_key:
                # Use human-readable name if available
                sub_measure_key = row['sub_measure']
                display_key = self.get_display_name(row['measure_name'])
                
                # Extract just the sub-measure part from display name
                if display_key != row['measure_name']:
                    structured_data[top_level_key][display_key] = row['percentile_rank']
                else:
                    structured_data[top_level_key][sub_measure_key] = row['percentile_rank']
        
        conn.close()
        return county_info, structured_data
    
    def get_submetric_details_fast_state(self, county_fips, top_level, sub_category):
        """Get detailed metrics for drill-down with fast state comparison support"""
        conn = self.get_database_connection()
        
        # Check if state percentiles table exists
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='state_percentiles'")
        has_state_table = cursor.fetchone() is not None
        
        if not has_state_table:
            conn.close()
            return self.get_submetric_details(county_fips, top_level, sub_category)  # Fallback
        
        # Convert display names back to database names
        top_level_mapping = {
            'Society': 'Society', #Changed Society to Society as per new csv file
            'Economy': 'Economy',
            'Environment': 'Environment'
        }
        
        db_top_level = top_level_mapping.get(top_level.lower(), top_level)
        
        # Find the database name for this sub-category
        db_sub_category = sub_category
        for db_name, display_name in self.display_names_map.items():
            if display_name == sub_category and db_top_level in db_name:
                # Extract the sub-measure part
                parts = db_name.split('_')
                if len(parts) >= 2:
                    db_sub_category = parts[1]
                    break
        
        if self.comparison_mode == 'state':
            # Use pre-calculated state percentiles (FAST!)
            details_query = """
                SELECT 
                    rm.metric_name,
                    rm.sub_metric_name,
                    nm.raw_value as metric_value,
                    sp.state_percentile as percentile_rank,
                    rm.unit,
                    rm.year,
                    ms.is_reverse_metric
                FROM normalized_metrics nm
                JOIN raw_metrics rm ON nm.fips = rm.fips AND nm.metric_name = rm.metric_name
                JOIN state_percentiles sp ON nm.fips = sp.fips AND nm.metric_name = sp.metric_name
                LEFT JOIN metric_statistics ms ON nm.metric_name = ms.metric_name
                WHERE nm.fips = ? 
                AND LOWER(rm.top_level) = LOWER(?)
                AND LOWER(rm.sub_measure) = LOWER(?)
                AND nm.is_missing = 0
                ORDER BY sp.state_percentile DESC
            """
            
            details_df = pd.read_sql(details_query, conn, 
                                   params=[county_fips, db_top_level, db_sub_category])
        else:
            # Use national percentiles (original method)
            details_query = """
                SELECT 
                    rm.metric_name,
                    rm.sub_metric_name,
                    nm.raw_value as metric_value,
                    nm.percentile_rank,
                    rm.unit,
                    rm.year,
                    ms.is_reverse_metric
                FROM normalized_metrics nm
                JOIN raw_metrics rm ON nm.fips = rm.fips AND nm.metric_name = rm.metric_name
                LEFT JOIN metric_statistics ms ON nm.metric_name = ms.metric_name
                WHERE nm.fips = ? 
                AND LOWER(rm.top_level) = LOWER(?)
                AND LOWER(rm.sub_measure) = LOWER(?)
                AND nm.is_missing = 0
                ORDER BY nm.percentile_rank DESC
            """
            
            details_df = pd.read_sql(details_query, conn, 
                                   params=[county_fips, db_top_level, db_sub_category])
        
        # Add human-readable display names
        if not details_df.empty:
            display_names = []
            for _, row in details_df.iterrows():
                display_name = self.get_display_name(row['metric_name'])
                if display_name == row['metric_name'] and row.get('sub_metric_name'):
                    # Use sub_metric_name if no display name found
                    display_name = row['sub_metric_name'].replace('_', ' ').title()
                display_names.append(display_name)
            
            details_df['display_name'] = display_names
        
        conn.close()
        return details_df
    
    def calculate_state_percentiles(self, county_fips):
        """Calculate percentile rankings within a state (SLOW - use for fallback only)"""
        conn = self.get_database_connection()
        
        # Get the state for this county
        state_query = """
            SELECT state FROM counties WHERE fips = ?
        """
        state_result = pd.read_sql(state_query, conn, params=[county_fips])
        if state_result.empty:
            conn.close()
            return {}
        
        state_code = state_result.iloc[0]['state']
        
        # Get all metrics for counties in this state
        state_metrics_query = """
            SELECT 
                nm.fips,
                nm.metric_name,
                nm.raw_value,
                ms.is_reverse_metric
            FROM normalized_metrics nm
            JOIN counties c ON nm.fips = c.fips
            JOIN metric_statistics ms ON nm.metric_name = ms.metric_name
            WHERE c.state = ?
            AND nm.is_missing = 0
            AND nm.raw_value IS NOT NULL
        """
        
        state_metrics_df = pd.read_sql(state_metrics_query, conn, params=[state_code])
        
        # Calculate state-level percentiles
        state_percentiles = {}
        
        for metric_name in state_metrics_df['metric_name'].unique():
            metric_data = state_metrics_df[state_metrics_df['metric_name'] == metric_name]
            county_value = metric_data[metric_data['fips'] == county_fips]['raw_value'].values
            
            if len(county_value) > 0:
                county_value = county_value[0]
                all_values = metric_data['raw_value'].values
                is_reverse = metric_data['is_reverse_metric'].iloc[0]
                
                if is_reverse:
                    # For "lower is better" metrics, reverse the percentile
                    percentile = 100 - stats.percentileofscore(all_values, county_value)
                else:
                    # For "higher is better" metrics, normal percentile
                    percentile = stats.percentileofscore(all_values, county_value)
                
                state_percentiles[metric_name] = percentile
        
        # Also calculate aggregated scores at state level
        agg_query = """
            SELECT 
                a.measure_name,
                a.measure_level,
                AVG(CASE WHEN a2.fips = ? THEN a2.percentile_rank END) as county_percentile,
                GROUP_CONCAT(a2.percentile_rank) as all_percentiles
            FROM aggregated_scores a
            JOIN counties c ON a.fips = c.fips
            JOIN aggregated_scores a2 ON a.measure_name = a2.measure_name 
                AND a.measure_level = a2.measure_level
            JOIN counties c2 ON a2.fips = c2.fips
            WHERE c.state = ? AND c2.state = ?
            AND a.measure_level IN ('sub_measure', 'top_level')
            GROUP BY a.measure_name, a.measure_level
        """
        
        agg_df = pd.read_sql(agg_query, conn, params=[county_fips, state_code, state_code])
        
        state_agg_percentiles = {}
        for _, row in agg_df.iterrows():
            if pd.notna(row['county_percentile']):
                # Recalculate percentile within state
                all_vals = [float(x) for x in row['all_percentiles'].split(',') if x]
                county_val = row['county_percentile']
                state_percentile = stats.percentileofscore(all_vals, county_val)
                state_agg_percentiles[row['measure_name']] = state_percentile
        
        conn.close()
        return state_percentiles, state_agg_percentiles
    
    def get_county_metrics(self, county_fips):
        """Get structured metrics for a county with appropriate comparison"""
        # Check if we have fast state comparison tables
        conn = self.get_database_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='state_percentiles'")
        has_fast_state = cursor.fetchone() is not None
        conn.close()
        
        # Use fast method if available
        if has_fast_state and self.stage >= 3:
            return self.get_county_metrics_fast_state(county_fips)
        
        # Fallback to original (slower) method
        conn = self.get_database_connection()
        
        # Get county information
        county_info = pd.read_sql("""
            SELECT 
                county as county_name,
                state as state_code,
                state as state_name
            FROM counties 
            WHERE fips = ?
        """, conn, params=[county_fips])
        
        if county_info.empty:
            conn.close()
            return pd.DataFrame(), {}
        
        # Get the data based on comparison mode
        if self.comparison_mode == 'state' and self.stage >= 2:
            # Calculate state-level percentiles (SLOW)
            state_percentiles, state_agg_percentiles = self.calculate_state_percentiles(county_fips)
            
            # Get sub-measures with state percentiles
            submeasures_query = """
                SELECT 
                    parent_measure as top_level,
                    measure_name,
                    CASE 
                        WHEN parent_measure = 'Society' THEN REPLACE(measure_name, 'Society_', '') -- Changed Society to Society as per new csv file
                        WHEN parent_measure = 'Economy' THEN REPLACE(measure_name, 'Economy_', '')
                        WHEN parent_measure = 'Environment' THEN REPLACE(measure_name, 'Environment_', '')
                    END as sub_measure,
                    percentile_rank as national_percentile,
                    normalized_score,
                    component_count,
                    completeness_ratio
                FROM aggregated_scores
                WHERE fips = ? 
                AND measure_level = 'sub_measure'
                AND normalized_score IS NOT NULL
                ORDER BY parent_measure, measure_name
                
            """
            
            submeasures_df = pd.read_sql(submeasures_query, conn, params=[county_fips])
            
            # Replace with state percentiles
            for idx, row in submeasures_df.iterrows():
                measure_name = row['measure_name']
                if measure_name in state_agg_percentiles:
                    submeasures_df.at[idx, 'percentile_rank'] = state_agg_percentiles[measure_name]
                else:
                    submeasures_df.at[idx, 'percentile_rank'] = row['national_percentile']
            
        else:
            # Use national percentiles (default)
            submeasures_query = """
                SELECT 
                    parent_measure as top_level,
                    measure_name,
                    CASE 
                        WHEN parent_measure = 'Society' THEN REPLACE(measure_name, 'Society_', '')-- Changed Society to Society as per new csv file
                        WHEN parent_measure = 'Economy' THEN REPLACE(measure_name, 'Economy_', '')
                        WHEN parent_measure = 'Environment' THEN REPLACE(measure_name, 'Environment_', '')
                    END as sub_measure,
                    percentile_rank,
                    normalized_score,
                    component_count,
                    completeness_ratio
                FROM aggregated_scores
                WHERE fips = ? 
                AND measure_level = 'sub_measure'
                AND normalized_score IS NOT NULL
                ORDER BY parent_measure, measure_name
            """
            
            submeasures_df = pd.read_sql(submeasures_query, conn, params=[county_fips])
        
        # Structure data in the format expected by radar chart
        structured_data = {
            'Society': {},    #Changed Society to Society as per new csv file
            'Economy': {},   
            'Environment': {}     
        }
        
        # Map the data to the expected structure
        top_level_mapping = {
            'Society': 'Society', #Changed Society to Society as per new csv file
            'Economy': 'Economy', 
            'Environment': 'Environment'
        }
        
        for _, row in submeasures_df.iterrows():
            top_level_key = top_level_mapping.get(row['top_level'])
            if top_level_key:
                # Use human-readable name if available
                sub_measure_key = row['sub_measure']
                display_key = self.get_display_name(row['measure_name'])
                
                # Extract just the sub-measure part from display name
                if display_key != row['measure_name']:
                    structured_data[top_level_key][display_key] = row['percentile_rank']
                else:
                    structured_data[top_level_key][sub_measure_key] = row['percentile_rank']
        
        conn.close()
        return county_info, structured_data
    
    def get_submetric_details(self, county_fips, top_level, sub_category):
        """Get detailed metrics for drill-down with appropriate comparison"""
        # Check if we have fast state comparison tables
        conn = self.get_database_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='state_percentiles'")
        has_fast_state = cursor.fetchone() is not None
        conn.close()
        
        # Use fast method if available
        if has_fast_state and self.stage >= 3:
            return self.get_submetric_details_fast_state(county_fips, top_level, sub_category)
        
        # Fallback to original (slower) method
        conn = self.get_database_connection()
        
        # Convert display names back to database names
        top_level_mapping = {
            'Society': 'Society', #Changed Society to Society as per new csv file
            'Economy': 'Economy',
            'Environment': 'Environment'
        }
        
        db_top_level = top_level_mapping.get(top_level.lower(), top_level)
        
        # Find the database name for this sub-category
        db_sub_category = sub_category
        for db_name, display_name in self.display_names_map.items():
            if display_name == sub_category and db_top_level in db_name:
                # Extract the sub-measure part
                parts = db_name.split('_')
                if len(parts) >= 2:
                    db_sub_category = parts[1]
                    break
        
        if self.comparison_mode == 'state' and self.stage >= 2:
            # Get state percentiles (SLOW)
            state_percentiles, _ = self.calculate_state_percentiles(county_fips)
            
            # Get metrics with state comparison
            details_query = """
                SELECT 
                    rm.metric_name,
                    rm.sub_metric_name,
                    nm.raw_value as metric_value,
                    nm.percentile_rank as national_percentile,
                    rm.unit,
                    rm.year,
                    ms.is_reverse_metric
                FROM normalized_metrics nm
                JOIN raw_metrics rm ON nm.fips = rm.fips AND nm.metric_name = rm.metric_name
                LEFT JOIN metric_statistics ms ON nm.metric_name = ms.metric_name
                WHERE nm.fips = ? 
                AND LOWER(rm.top_level) = LOWER(?)
                AND LOWER(rm.sub_measure) = LOWER(?)
                AND nm.is_missing = 0
                ORDER BY nm.percentile_rank DESC
            """
            
            details_df = pd.read_sql(details_query, conn, 
                                   params=[county_fips, db_top_level, db_sub_category])
            
            # Replace with state percentiles
            for idx, row in details_df.iterrows():
                metric_name = row['metric_name']
                if metric_name in state_percentiles:
                    details_df.at[idx, 'percentile_rank'] = state_percentiles[metric_name]
                else:
                    details_df.at[idx, 'percentile_rank'] = row['national_percentile']
            
        else:
            # Use national percentiles (default)
            details_query = """
                SELECT 
                    rm.metric_name,
                    rm.sub_metric_name,
                    nm.raw_value as metric_value,
                    nm.percentile_rank,
                    rm.unit,
                    rm.year,
                    ms.is_reverse_metric
                FROM normalized_metrics nm
                JOIN raw_metrics rm ON nm.fips = rm.fips AND nm.metric_name = rm.metric_name
                LEFT JOIN metric_statistics ms ON nm.metric_name = ms.metric_name
                WHERE nm.fips = ? 
                AND LOWER(rm.top_level) = LOWER(?)
                AND LOWER(rm.sub_measure) = LOWER(?)
                AND nm.is_missing = 0
                ORDER BY nm.percentile_rank DESC
            """
            
            details_df = pd.read_sql(details_query, conn, 
                                   params=[county_fips, db_top_level, db_sub_category])
        
        # Add human-readable display names
        if not details_df.empty:
            display_names = []
            for _, row in details_df.iterrows():
                display_name = self.get_display_name(row['metric_name'])
                if display_name == row['metric_name'] and row.get('sub_metric_name'):
                    # Use sub_metric_name if no display name found
                    display_name = row['sub_metric_name'].replace('_', ' ').title()
                display_names.append(display_name)
            
            details_df['display_name'] = display_names
        
        conn.close()
        return details_df

# Enhanced helper functions
def get_performance_label(percentile, comparison_mode='national'):
    """Get performance label based on percentile with comparison context"""
    context = "nationally" if comparison_mode == 'national' else "in state"
    
    if percentile >= 90:
        return f"Excellent (Top 10% {context})"
    elif percentile >= 75:
        return f"Good (Top 25% {context})"
    elif percentile >= 50:
        return f"Above Average {context}"
    elif percentile >= 25:
        return f"Below Average {context}"
    else:
        return f"Needs Improvement (Bottom 25% {context})"

def create_enhanced_radar_chart_with_units_v2(county_data, county_name, data_provider, county_fips):
    """Enhanced radar chart aligned PERFECTLY with SVG - NO REFERENCE CIRCLES"""
    import plotly.graph_objects as go
    import math
    import os
    
    if not county_data:
        return go.Figure()
    
    # Define categories - SMOOTH FLOW: Society → Economy → Environment (clockwise, no jumps)
    # Society (150-270°) → Economy (270-390°) → Environment (30-150°)
    categories_config = {
        'Society': {'color': '#6B7FD7', 'label': 'Society', 'start_angle': 150, 'end_angle': 270},  # Left side (purple)
        'Economy': {'color': '#D4AF37', 'label': 'Economy', 'start_angle': 270, 'end_angle': 390},  # Bottom, wraps (gold)
        'Environment': {'color': '#4ECDC4', 'label': 'Environment', 'start_angle': 30, 'end_angle': 150}  # Top-right (teal)
    }
    
    fig = go.Figure()
    
    # Try to load SVG as background
    svg_loaded = False
    try:
        possible_paths = [
            'assets/custom_visual.svg',
            'custom_visual.svg',
            '../assets/custom_visual.svg',
        ]
        
        svg_content = None
        svg_path_used = None
        
        for svg_path in possible_paths:
            if os.path.exists(svg_path):
                with open(svg_path, 'r', encoding='utf-8') as svg_file:
                    svg_content = svg_file.read()
                svg_path_used = svg_path
                break
        
        if svg_content:
            import base64
            svg_base64 = base64.b64encode(svg_content.encode('utf-8')).decode('utf-8')
            svg_data_url = f"data:image/svg+xml;base64,{svg_base64}"
            
            # Add SVG as background image
            fig.add_layout_image(
                dict(
                    source=svg_data_url,
                    xref="paper",
                    yref="paper",
                    x=0.5,
                    y=0.5,
                    sizex=1.0,
                    sizey=1.0,
                    xanchor="center",
                    yanchor="middle",
                    opacity=0.8,
                    layer="below",
                    sizing="contain"
                )
            )
            svg_loaded = True
            print(f"✅ SVG background loaded from: {svg_path_used}")
        else:
            print(f"⚠️ SVG file not found in any location")
    except Exception as e:
        print(f"⚠️ Error loading SVG: {e}")
    
    if not svg_loaded:
        print("💡 Continuing without SVG background...")
    
    # Process each category separately - REORDERED for smooth polygon flow
    all_theta = []
    all_r = []
    all_colors = []
    all_hover = []
    all_customdata = []
    all_labels = []
    
    # Define EXACT order as shown in SVG (CLOCKWISE from start of each sector)
    sector_orders = {
        'Society': ['Health', 'Arts and Culture', 'Community', 'Education', 'Wealth'],
        'Environment': ['Built Environment', 'Climate and Resilience', 'Land, Air, Water', 'Biodiversity', 'Food and Agriculture Systems'],
        'Economy': ['Employment', 'Nonprofit', 'Business', 'Government', 'Energy']
    }
    
    # NEW: Process in YOUR specified order for polygon connections
    # Order: Society (150-270°) → Economy (30-150°) → Environment (270-390°)
    for category in ['Society', 'Economy', 'Environment']:
        if category in county_data and county_data[category]:
            config = categories_config[category]
            
            # Get the correct order for this category
            correct_order = sector_orders[category]
            
            # Match data to correct order
            ordered_sub_categories = []
            ordered_values = []
            
            for correct_name in correct_order:
                # Try to find matching data
                found = False
                for sub_cat, value in county_data[category].items():
                    # Flexible matching
                    if (correct_name.lower() in sub_cat.lower() or 
                        sub_cat.lower() in correct_name.lower() or
                        correct_name.replace(',', '').replace(' ', '').lower() == sub_cat.replace(',', '').replace(' ', '').lower()):
                        ordered_sub_categories.append(sub_cat)
                        ordered_values.append(value)
                        found = True
                        break
                
                # If not found but expected, skip this position
                if not found:
                    continue
            
            sub_categories = ordered_sub_categories
            values = ordered_values
            
            # Calculate angles for this sector
            n_metrics = len(sub_categories)
            if n_metrics > 0:
                sector_span = config['end_angle'] - config['start_angle']
                padding = 5
                effective_span = sector_span - 2 * padding
                
                if n_metrics == 1:
                    angles = [(config['start_angle'] + sector_span / 2) % 360]
                else:
                    step = effective_span / (n_metrics - 1)
                    angles = [(config['start_angle'] + padding + i * step) % 360 for i in range(n_metrics)]
                
                # CUSTOM ADJUSTMENT: Move Climate and Resilience to 45°
                if category == 'Environment':
                    for idx, sub_cat in enumerate(sub_categories):
                        if 'Climate' in sub_cat and 'Resilience' in sub_cat:
                            angles[idx] = 45  # Force to 45°
                            print(f"✓ Adjusted {sub_cat} to 45°")
                
                # Add to overall data with enhanced hover info
                for i, (sub_cat, value, angle) in enumerate(zip(sub_categories, values, angles)):
                    hover_detail = ""
                    try:
                        sample_details = data_provider.get_submetric_details(county_fips, category, sub_cat)
                        if not sample_details.empty:
                            top_metrics = sample_details.head(2)
                            metrics_list = []
                            for _, row in top_metrics.iterrows():
                                unit_text = f" {row['unit']}" if row.get('unit') and row['unit'] != '' else ""
                                display_name = row.get('display_name', row['metric_name'])
                                metric_text = f"• {display_name}: {row['metric_value']:.1f}{unit_text} ({row['percentile_rank']:.0f}%)"
                                metrics_list.append(metric_text)
                            
                            metrics_text = "<br>".join(metrics_list)
                            hover_detail = f"<br><br>Top Metrics:<br>{metrics_text}"
                            if len(sample_details) > 2:
                                hover_detail += f"<br>... and {len(sample_details)-2} more"
                    except:
                        hover_detail = ""
                    
                    performance_label = get_performance_label(value, data_provider.comparison_mode)
                    
                    hover_detail_text = (
                        f"<b>{config['label']}</b><br>" +
                        f"{sub_cat}: {value:.1f}%<br>" +
                        f"Performance: {performance_label}" +
                        hover_detail
                    )
                    
                    all_theta.append(angle)
                    all_r.append(value)
                    all_colors.append(config['color'])
                    all_hover.append(hover_detail_text)
                    all_customdata.append([category, sub_cat])
                    all_labels.append(sub_cat)
    
    # Create the main radar trace with semi-transparent fill
    fig.add_trace(go.Scatterpolar(
        r=all_r,
        theta=all_theta,
        fill='toself',
        fillcolor='rgba(150,150,150,0.15)',
        line=dict(color='rgba(80,80,80,0.8)', width=2),
        marker=dict(
            size=12,
            color=all_colors,
            line=dict(color='white', width=2)
        ),
        name='County Metrics',
        text=all_hover,
        hovertemplate='%{text}<extra></extra>',
        customdata=all_customdata,
        mode='markers+lines'
    ))
    
    # REMOVED: Label traces - no text labels around the chart
    # The SVG background already has the indicator names
    
    # Update layout
    comparison_context = "All US Counties" if data_provider.comparison_mode == 'national' else f"{data_provider.current_state} Counties"
    speed_indicator = ""
    if data_provider.comparison_mode == 'state':
        speed_indicator = " ⚡" if data_provider.stage >= 3 else " ⏳"
    
    svg_indicator = " 🎨" if svg_loaded else ""
    main_title = f"<b>{county_name} Sustainability Dashboard</b><br><sub>Percentile Rankings vs. {comparison_context}{speed_indicator}{svg_indicator} • Click sub-measures for details</sub>"
    
    fig.update_layout(
        polar=dict(
            bgcolor='rgba(255,255,255,0)' if svg_loaded else 'white',
            radialaxis=dict(
                visible=True, 
                range=[0, 120],
                angle=90,
                tickfont=dict(size=12, color='#374151'),
                gridcolor='rgba(200,200,200,0.2)',
                tickmode='linear', 
                tick0=0, 
                dtick=20,
                tickvals=[0, 20, 40, 60, 80, 100],
                ticktext=['0th', '20th', '40th', '60th', '80th', '100th']
            ),
            angularaxis=dict(
                tickmode='array',
                tickvals=[0, 30, 60, 90, 120, 150, 180, 210, 240, 270, 300, 330],
                ticktext=[''] * 12,
                gridcolor='rgba(200,200,200,0.2)',
                showticklabels=False,
                rotation=0,
                direction='clockwise'
            )
        ),
        showlegend=False,
        title=dict(
            text=main_title,
            x=0.5, 
            font=dict(size=18, color='#1F2937')
        ),
        height=700,
        margin=dict(t=120, b=100, l=100, r=100),
        paper_bgcolor='rgba(255,255,255,0)' if svg_loaded else 'white',
        plot_bgcolor='rgba(255,255,255,0)' if svg_loaded else 'white'
    )
    
    return fig

def create_detail_chart_with_units_v2(details_df, title, comparison_mode='national'):
    """Create enhanced detail chart with units and comparison context"""
    import plotly.graph_objects as go
    
    if details_df.empty:
        return go.Figure()
    
    # Add comparison context to title
    comparison_label = "National" if comparison_mode == 'national' else "State"
    title_with_context = f"{title} ({comparison_label} Comparison)"
    
    # Sort by percentile rank
    details_df = details_df.sort_values('percentile_rank', ascending=True)
    
    fig = go.Figure()
    
    # Create bars with color coding
    fig.add_trace(go.Bar(
        y=details_df.get('display_name', details_df['metric_name']),
        x=details_df['percentile_rank'],
        orientation='h',
        marker=dict(
            color=details_df['percentile_rank'],
            colorscale='RdYlGn',
            colorbar=dict(title="Percentile"),
            cmin=0,
            cmax=100
        ),
        text=[f"{val:.1f}" for val in details_df['percentile_rank']],
        textposition='auto',
        hovertemplate='<b>%{y}</b><br>' +
                      'Value: %{customdata[0]:.1f} %{customdata[1]}<br>' +
                      'Percentile: %{x:.0f}%<br>' +
                      '<extra></extra>',
        customdata=list(zip(
            details_df['metric_value'],
            details_df.get('unit', [''] * len(details_df))
        ))
    ))
    
    # Add reference line at 50th percentile
    fig.add_vline(
        x=50, 
        line_dash="dash", 
        line_color="gray",
        annotation_text=f"50th Percentile ({comparison_label} Avg)",
        annotation_position="top"
    )
    
    fig.update_layout(
        title=dict(text=title_with_context, font=dict(size=16)),
        xaxis_title=f"Percentile Rank (vs {comparison_label} Average)",
        yaxis_title="Metrics",
        xaxis=dict(range=[0, 105]),
        height=max(400, len(details_df) * 50),
        margin=dict(l=250, r=50, t=80, b=50),
        showlegend=False
    )
    
    return fig

def get_performance_label(percentile, comparison_mode='national'):
    """Get performance label based on percentile with comparison context"""
    context = "nationally" if comparison_mode == 'national' else "in state"
    
    if percentile >= 90:
        return f"Excellent (Top 10% {context})"
    elif percentile >= 75:
        return f"Good (Top 25% {context})"
    elif percentile >= 50:
        return f"Above Average {context}"
    elif percentile >= 25:
        return f"Below Average {context}"
    else:
        return f"Needs Improvement (Bottom 25% {context})"

# Setup function for fast state comparisons
def setup_fast_state_comparisons(db_file_path='sustainability_data.db'):
    """One-time setup to enable fast state comparisons"""
    print("🚀 SETTING UP FAST STATE COMPARISONS")
    print("=" * 60)
    
    provider = RadarChartDataProviderV2(db_file_path)
    
    if provider.stage < 2:
        print("❌ Please run Stage 1 and Stage 2 first")
        return False
    
    print(f"📊 Current stage: {provider.stage}")
    success = provider.create_state_percentiles_table()
    
    if success:
        print("\n✅ Setup complete!")
        print("⚡ State comparisons will now be instant")
        print("🎯 Your dashboard can now use fast state comparisons")
    else:
        print("\n❌ Setup failed")
        
    return success

if __name__ == "__main__":
    print("🚀 ENHANCED RADAR CHART INTEGRATION V2 - WITH FAST STATE COMPARISONS")
    print("=" * 70)
    
    # Test the enhanced integration
    provider = RadarChartDataProviderV2()
    
    # Show status
    print(f"\n📊 Database Status: Stage {provider.stage}/3")
    print(f"📝 Display Names: {len(provider.display_names_map)} mappings loaded")
    print(f"🔄 Comparison Mode: {provider.comparison_mode}")
    
    if provider.stage == 0:
        print(f"\n❌ No data found. Please run Stage 1 first.")
        exit(1)
    elif provider.stage == 1:
        print(f"\n⚠️  Only raw data available. Run Stage 2 for full functionality.")
        exit(1)
    elif provider.stage == 2:
        print(f"\n💡 Stage 2 complete. Run setup_fast_state_comparisons() for instant state comparisons.")
        
        # Ask if user wants to set up fast state comparisons
        response = input("\nWould you like to set up fast state comparisons now? (y/n): ")
        if response.lower() in ['y', 'yes']:
            setup_fast_state_comparisons()
            provider._check_database_status()  # Refresh status
    
    # Test getting counties
    counties = provider.get_all_counties()
    print(f"\n✅ Found {len(counties)} counties with good data coverage")
    
    if not counties.empty:
        # Test with a sample county
        sample_fips = counties.iloc[0]['fips_code']
        sample_state = counties.iloc[0]['state_code']
        county_info, structured_data = provider.get_county_metrics(sample_fips)
        
        if not county_info.empty:
            county_name = f"{county_info.iloc[0]['county_name']}, {county_info.iloc[0]['state_code']}"
            print(f"\n✅ Testing with {county_name}")
            
            # Test national comparison
            print(f"\n🌎 National Comparison:")
            start_time = time.time()
            provider.set_comparison_mode('national')
            _, structured_data_national = provider.get_county_metrics(sample_fips)
            national_time = time.time() - start_time
            
            for category, sub_measures in structured_data_national.items():
                if sub_measures:
                    print(f"   {category}: {len(sub_measures)} sub-measures")
                    for sub_name, value in list(sub_measures.items())[:2]:
                        print(f"     • {sub_name}: {value:.1f}%")
            print(f"   ⏱️  Time: {national_time:.3f} seconds")
            
            # Test state comparison
            print(f"\n🏛️  State Comparison for {sample_state}:")
            start_time = time.time()
            provider.set_comparison_mode('state', sample_state)
            _, structured_data_state = provider.get_county_metrics(sample_fips)
            state_time = time.time() - start_time
            
            for category, sub_measures in structured_data_state.items():
                if sub_measures:
                    for sub_name, value in list(sub_measures.items())[:2]:
                        print(f"     • {sub_name}: {value:.1f}% (state ranking)")
            
            speed_status = "⚡ FAST" if provider.stage >= 3 else "⏳ SLOW"
            print(f"   ⏱️  Time: {state_time:.3f} seconds ({speed_status})")
            
            # Performance comparison
            if state_time > national_time * 2:
                print(f"\n💡 State comparisons are {state_time/national_time:.1f}x slower than national")
                print(f"   Run setup_fast_state_comparisons() to make them equally fast!")
            else:
                print(f"\n✅ State comparisons are optimized!")
            
            # Test drill-down with display names
            if structured_data.get('Society'):
                first_submeasure = list(structured_data['Society'].keys())[0]
                print(f"\n🔍 Testing drill-down for '{first_submeasure}':")
                
                details = provider.get_submetric_details(sample_fips, 'Society', first_submeasure)
                if not details.empty:
                    print(f"   Found {len(details)} metrics")
                    for _, row in details.head(3).iterrows():
                        display_name = row.get('display_name', row['metric_name'])
                        unit = row.get('unit', '')
                        print(f"   • {display_name}: {row['metric_value']:.1f} {unit} ({row['percentile_rank']:.0f}%)")
    
    print(f"\n✨ Key Features:")
    print(f"   • Human-readable display names from CSV")
    print(f"   • Toggle between National and State comparisons")
    print(f"   • ⚡ Fast state comparisons (Stage 3)")
    print(f"   • Percentile rankings adjust based on comparison mode")
    print(f"   • Enhanced hover text with context")
    print(f"   • Bar charts show appropriate reference lines")
    
    print(f"\n📋 Integration Steps:")
    print(f"   1. Create display_names.csv with your preferred names")
    print(f"   2. Import enhanced_radar_integration_v2 in your dashboard")
    print(f"   3. Add comparison mode toggle buttons")
    print(f"   4. Update callbacks to use the new provider")
    print(f"   5. Run setup_fast_state_comparisons() for instant state switching")
    
    print(f"\n🎯 Ready for integration!")
    print("=" * 70)