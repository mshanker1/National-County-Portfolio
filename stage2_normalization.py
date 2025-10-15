import pandas as pd
import sqlite3
import numpy as np
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

class SustainabilityNormalizer:
    """
    Stage 2: Implement normalization and percentile calculations for sustainability metrics
    """
    
    def __init__(self, db_file_path='sustainability_data.db'):
        self.db_file_path = db_file_path
        self.conn = None
        
        # Define metrics where "lower is better" (these need reversed percentiles)
        #Need to change these metrics as per the new csv file
        self.reverse_metrics = {
            # Health metrics (lower is better)
            'Society_Health_LengthOfLife_Premature Death',
            'Society_Health_QualityOfLife_FreqPhyDistress', 
            'Society_Health_QualityOfLife_FreqMenDistress',
            'Society_Health_QualityOfLife_AdultWithDiabetes',
            'Society_Health_QualityOfLife_HIVPrevRate',
            'Society_Health_HealthBehaviours_AdultsWithObesity',
            'Society_Health_HealthBehaviours_AdultsSmoking',
            'Society_Health_HealthBehaviours_ExcessiveDrinking',
            'Society_Health_HealthBehaviours_PhysicallyInactive',
            'Society_Health_HealthBehaviours_InsufficientSleep',
            'Society_Health_HealthResources_AccessToCare_Uninsured',
            'Society_Health_HealthResources_QualityOfCare_PreventableHospitalizationRate',
            
            # Community metrics (lower is better)
            'Society_Community_SevereHousingProblems',
            'Society_Community_FoodInsecurity',
            'Society_Community_LongCommuteAndDrivesAlone',
            'Society_Community_ViolentCrimeRate',
            
            # Wealth metrics (lower is better)
            'Society_Wealth_IncomeRatio80by20',
            'Society_Wealth_ChildPoverty',
            
            # Business metrics (some lower is better)
            'Economy_Government_ViolentCrimeRate',
            'Economy_Government_SevereHousingProblems',
            'Economy_Government_DependencyRatio',
            
            # Employment metrics (lower is better)
            'Economy_Employment_UnemploymentRate',
            
            # Environmental metrics (lower is better)  
            'Environment_ClimateAndResilience',
            'Environment_LandAirWater_AirQualityIndexPerPm2.5',
            'Environment_LandAirWater_WaterConservationOrGallonsOrPersonOrDay'
        }
    
    def create_normalization_tables(self):
        """Create tables for normalized data and statistics"""
        self.conn = sqlite3.connect(self.db_file_path)
        cursor = self.conn.cursor()
        
        # Drop existing tables if they exist
        cursor.execute('DROP TABLE IF EXISTS metric_statistics')
        cursor.execute('DROP TABLE IF EXISTS normalized_metrics')
        cursor.execute('DROP TABLE IF EXISTS aggregated_scores')
        
        # Create metric statistics table
        cursor.execute('''
            CREATE TABLE metric_statistics (
                metric_name TEXT PRIMARY KEY,
                total_counties INTEGER,
                valid_counties INTEGER,
                missing_counties INTEGER,
                mean_value REAL,
                std_dev REAL,
                min_value REAL,
                max_value REAL,
                median_value REAL,
                is_reverse_metric INTEGER DEFAULT 0,
                data_quality_score REAL
            )
        ''')
        
        # Create normalized metrics table
        cursor.execute('''
            CREATE TABLE normalized_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fips TEXT NOT NULL,
                metric_name TEXT NOT NULL,
                raw_value REAL,
                normalized_value REAL,
                percentile_rank REAL,
                is_missing INTEGER DEFAULT 0,
                FOREIGN KEY (fips) REFERENCES counties(fips),
                UNIQUE(fips, metric_name)
            )
        ''')
        
        # Create aggregated scores table for sub-measures and top-level measures
        cursor.execute('''
            CREATE TABLE aggregated_scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fips TEXT NOT NULL,
                measure_name TEXT NOT NULL,
                measure_level TEXT NOT NULL, -- 'metric_group', 'sub_measure', 'top_level'
                parent_measure TEXT, -- For hierarchy tracking
                raw_score REAL,
                normalized_score REAL,
                percentile_rank REAL,
                component_count INTEGER,
                missing_components INTEGER,
                completeness_ratio REAL,
                FOREIGN KEY (fips) REFERENCES counties(fips),
                UNIQUE(fips, measure_name, measure_level)
            )
        ''')
        
        # Create indexes
        cursor.execute('CREATE INDEX idx_normalized_fips ON normalized_metrics(fips)')
        cursor.execute('CREATE INDEX idx_normalized_metric ON normalized_metrics(metric_name)')
        cursor.execute('CREATE INDEX idx_aggregated_fips ON aggregated_scores(fips)')
        cursor.execute('CREATE INDEX idx_aggregated_measure ON aggregated_scores(measure_name, measure_level)')
        
        self.conn.commit()
        print("✅ Normalization tables created successfully")
    
    def calculate_metric_statistics(self):
        """Calculate statistics for each metric across all counties"""
        print("📊 Calculating metric statistics...")
        
        cursor = self.conn.cursor()
        
        # Get all unique metrics with their data
        metrics_query = """
            SELECT 
                metric_name,
                COUNT(*) as total_counties,
                COUNT(CASE WHEN is_missing = 0 THEN 1 END) as valid_counties,
                COUNT(CASE WHEN is_missing = 1 THEN 1 END) as missing_counties
            FROM raw_metrics
            GROUP BY metric_name
        """
        
        metrics_df = pd.read_sql(metrics_query, self.conn)
        statistics_data = []
        
        for _, metric_row in metrics_df.iterrows():
            metric_name = metric_row['metric_name']
            
            # Get valid values for this metric
            values_query = """
                SELECT raw_value 
                FROM raw_metrics 
                WHERE metric_name = ? AND is_missing = 0 AND raw_value IS NOT NULL
            """
            
            values_df = pd.read_sql(values_query, self.conn, params=[metric_name])
            
            if len(values_df) < 10:  # Skip metrics with too little data
                continue
                
            values = values_df['raw_value'].values
            
            # Calculate statistics
            mean_val = np.mean(values)
            std_val = np.std(values, ddof=1)  # Sample standard deviation
            min_val = np.min(values)
            max_val = np.max(values)
            median_val = np.median(values)
            
            # Data quality score (percentage of non-missing data)
            quality_score = metric_row['valid_counties'] / metric_row['total_counties']
            
            # Check if this is a reverse metric
            is_reverse = 1 if metric_name in self.reverse_metrics else 0
            
            statistics_data.append((
                metric_name,
                metric_row['total_counties'],
                metric_row['valid_counties'], 
                metric_row['missing_counties'],
                mean_val,
                std_val,
                min_val,
                max_val,
                median_val,
                is_reverse,
                quality_score
            ))
        
        # Insert statistics into database
        cursor.executemany('''
            INSERT INTO metric_statistics 
            (metric_name, total_counties, valid_counties, missing_counties,
             mean_value, std_dev, min_value, max_value, median_value,
             is_reverse_metric, data_quality_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', statistics_data)
        
        self.conn.commit()
        print(f"   ✅ Calculated statistics for {len(statistics_data)} metrics")
        
        return len(statistics_data)
    
    def normalize_metrics(self):
        """Apply Z-score normalization to all metrics"""
        print("🔄 Normalizing metrics using Z-scores...")
        
        cursor = self.conn.cursor()
        
        # Get all metrics with their statistics
        stats_query = """
            SELECT metric_name, mean_value, std_dev, is_reverse_metric
            FROM metric_statistics
            WHERE std_dev > 0  -- Only normalize metrics with variation
        """
        
        stats_df = pd.read_sql(stats_query, self.conn)
        normalized_data = []
        
        for _, stat_row in stats_df.iterrows():
            metric_name = stat_row['metric_name']
            mean_val = stat_row['mean_value']
            std_val = stat_row['std_dev']
            is_reverse = stat_row['is_reverse_metric']
            
            # Get all raw values for this metric
            values_query = """
                SELECT fips, raw_value, is_missing
                FROM raw_metrics
                WHERE metric_name = ?
            """
            
            values_df = pd.read_sql(values_query, self.conn, params=[metric_name])
            
            for _, value_row in values_df.iterrows():
                fips = value_row['fips']
                raw_value = value_row['raw_value']
                is_missing = value_row['is_missing']
                
                if is_missing or raw_value is None:
                    # Keep missing values as None
                    normalized_value = None
                    percentile_rank = None
                else:
                    # Calculate Z-score
                    z_score = (raw_value - mean_val) / std_val
                    normalized_value = z_score
                    
                    # Calculate percentile rank
                    # Get all valid values for percentile calculation
                    all_values_query = """
                        SELECT raw_value 
                        FROM raw_metrics 
                        WHERE metric_name = ? AND is_missing = 0 AND raw_value IS NOT NULL
                    """
                    all_values_df = pd.read_sql(all_values_query, self.conn, params=[metric_name])
                    all_values = all_values_df['raw_value'].values
                    
                    if is_reverse:
                        # For "lower is better" metrics, reverse the percentile
                        # Lower raw values should get higher percentiles
                        percentile_rank = 100 - stats.percentileofscore(all_values, raw_value)
                    else:
                        # For "higher is better" metrics, normal percentile
                        percentile_rank = stats.percentileofscore(all_values, raw_value)
                
                normalized_data.append((
                    fips,
                    metric_name,
                    raw_value,
                    normalized_value,
                    percentile_rank,
                    is_missing
                ))
        
        # Batch insert normalized data
        cursor.executemany('''
            INSERT OR REPLACE INTO normalized_metrics
            (fips, metric_name, raw_value, normalized_value, percentile_rank, is_missing)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', normalized_data)
        
        self.conn.commit()
        print(f"   ✅ Normalized {len(normalized_data)} metric values")
        
        return len(normalized_data)
    
    def aggregate_metric_groups(self):
        """Aggregate sub-metrics into metric groups (e.g., LifeExpectancy + PrematureDeath -> LengthOfLife)"""
        print("📋 Aggregating sub-metrics into metric groups...")
        
        cursor = self.conn.cursor()
        
        # Get the hierarchical structure from raw_metrics
        hierarchy_query = """
            SELECT DISTINCT 
                top_level,
                sub_measure,
                metric_group,
                COUNT(DISTINCT metric_name) as sub_metric_count
            FROM raw_metrics
            WHERE metric_group IS NOT NULL
            GROUP BY top_level, sub_measure, metric_group
            HAVING sub_metric_count > 1  -- Only aggregate groups with multiple sub-metrics
        """
        
        hierarchy_df = pd.read_sql(hierarchy_query, self.conn)
        aggregated_data = []
        
        # Get all counties
        counties_query = "SELECT fips FROM counties"
        counties_df = pd.read_sql(counties_query, self.conn)
        
        for _, group_row in hierarchy_df.iterrows():
            top_level = group_row['top_level']
            sub_measure = group_row['sub_measure']
            metric_group = group_row['metric_group']
            
            # Create a composite name for this metric group
            group_name = f"{top_level}_{sub_measure}_{metric_group}"
            
            for _, county_row in counties_df.iterrows():
                fips = county_row['fips']
                
                # Get all sub-metrics in this group for this county
                submetrics_query = """
                    SELECT nm.normalized_value, nm.percentile_rank, nm.is_missing
                    FROM normalized_metrics nm
                    JOIN raw_metrics rm ON nm.fips = rm.fips AND nm.metric_name = rm.metric_name
                    WHERE nm.fips = ? 
                    AND rm.top_level = ? 
                    AND rm.sub_measure = ? 
                    AND rm.metric_group = ?
                """
                
                submetrics_df = pd.read_sql(submetrics_query, self.conn, 
                                          params=[fips, top_level, sub_measure, metric_group])
                
                if submetrics_df.empty:
                    continue
                
                # Calculate aggregated scores
                valid_metrics = submetrics_df[submetrics_df['is_missing'] == 0]
                total_components = len(submetrics_df)
                missing_components = len(submetrics_df[submetrics_df['is_missing'] == 1])
                
                if len(valid_metrics) > 0:
                    # Average the normalized values and percentiles
                    avg_normalized = valid_metrics['normalized_value'].mean()
                    avg_percentile = valid_metrics['percentile_rank'].mean()
                    completeness_ratio = len(valid_metrics) / total_components
                    
                    # For raw score, we'll use the average percentile as a proxy
                    raw_score = avg_percentile
                else:
                    avg_normalized = None
                    avg_percentile = None
                    raw_score = None
                    completeness_ratio = 0.0
                
                aggregated_data.append((
                    fips,
                    group_name,
                    'metric_group',
                    f"{top_level}_{sub_measure}",  # parent measure
                    raw_score,
                    avg_normalized,
                    avg_percentile,
                    total_components,
                    missing_components,
                    completeness_ratio
                ))
        
        # Insert aggregated metric groups
        if aggregated_data:
            cursor.executemany('''
                INSERT OR REPLACE INTO aggregated_scores
                (fips, measure_name, measure_level, parent_measure, raw_score,
                 normalized_score, percentile_rank, component_count, 
                 missing_components, completeness_ratio)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', aggregated_data)
            
            self.conn.commit()
            print(f"   ✅ Aggregated {len(aggregated_data)} metric group scores")
        
        return len(aggregated_data)
    
    def aggregate_sub_measures(self):
        """Aggregate metrics and metric groups into sub-measures"""
        print("📊 Aggregating metrics into sub-measures...")
        
        cursor = self.conn.cursor()
        
        # Get all sub-measures
        submeasures_query = """
            SELECT DISTINCT top_level, sub_measure
            FROM raw_metrics
        """
        
        submeasures_df = pd.read_sql(submeasures_query, self.conn)
        counties_df = pd.read_sql("SELECT fips FROM counties", self.conn)
        
        aggregated_data = []
        
        for _, submeasure_row in submeasures_df.iterrows():
            top_level = submeasure_row['top_level']
            sub_measure = submeasure_row['sub_measure']
            submeasure_name = f"{top_level}_{sub_measure}"
            
            for _, county_row in counties_df.iterrows():
                fips = county_row['fips']
                
                # Get all individual metrics for this sub-measure (excluding metric groups)
                individual_metrics_query = """
                    SELECT nm.normalized_value, nm.percentile_rank, nm.is_missing
                    FROM normalized_metrics nm
                    JOIN raw_metrics rm ON nm.fips = rm.fips AND nm.metric_name = rm.metric_name
                    WHERE nm.fips = ? 
                    AND rm.top_level = ? 
                    AND rm.sub_measure = ?
                """
                
                individual_df = pd.read_sql(individual_metrics_query, self.conn,
                                          params=[fips, top_level, sub_measure])
                
                # Get aggregated metric groups for this sub-measure
                groups_query = """
                    SELECT normalized_score, percentile_rank
                    FROM aggregated_scores
                    WHERE fips = ? 
                    AND parent_measure = ?
                    AND measure_level = 'metric_group'
                    AND normalized_score IS NOT NULL
                """
                
                groups_df = pd.read_sql(groups_query, self.conn,
                                      params=[fips, submeasure_name])
                
                # Combine individual metrics and groups
                all_scores = []
                all_percentiles = []
                
                # Add individual metrics
                valid_individuals = individual_df[individual_df['is_missing'] == 0]
                if not valid_individuals.empty:
                    all_scores.extend(valid_individuals['normalized_value'].tolist())
                    all_percentiles.extend(valid_individuals['percentile_rank'].tolist())
                
                # Add metric groups
                if not groups_df.empty:
                    all_scores.extend(groups_df['normalized_score'].tolist())
                    all_percentiles.extend(groups_df['percentile_rank'].tolist())
                
                # Calculate sub-measure aggregated score
                total_components = len(individual_df) + len(groups_df)
                valid_components = len(all_scores)
                missing_components = total_components - valid_components
                
                if valid_components > 0:
                    avg_normalized = np.mean(all_scores)
                    avg_percentile = np.mean(all_percentiles)
                    completeness_ratio = valid_components / total_components if total_components > 0 else 0
                    raw_score = avg_percentile
                else:
                    avg_normalized = None
                    avg_percentile = None
                    raw_score = None
                    completeness_ratio = 0.0
                
                aggregated_data.append((
                    fips,
                    submeasure_name,
                    'sub_measure',
                    top_level,  # parent measure
                    raw_score,
                    avg_normalized,
                    avg_percentile,
                    total_components,
                    missing_components,
                    completeness_ratio
                ))
        
        # Insert aggregated sub-measures
        cursor.executemany('''
            INSERT OR REPLACE INTO aggregated_scores
            (fips, measure_name, measure_level, parent_measure, raw_score,
             normalized_score, percentile_rank, component_count, 
             missing_components, completeness_ratio)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', aggregated_data)
        
        self.conn.commit()
        print(f"   ✅ Aggregated {len(aggregated_data)} sub-measure scores")
        
        return len(aggregated_data)
    #Need to change the top level measures as per the new csv file
    def aggregate_top_level_measures(self):
        """Aggregate sub-measures into top-level measures (People, Prosperity, Planet)"""
        print("🌍 Aggregating sub-measures into top-level measures...")
        
        cursor = self.conn.cursor()
        counties_df = pd.read_sql("SELECT fips FROM counties", self.conn)

        top_levels = ['Society', 'Economy', 'Environment']
        aggregated_data = []
        
        for top_level in top_levels:
            for _, county_row in counties_df.iterrows():
                fips = county_row['fips']
                
                # Get all sub-measures for this top-level measure
                submeasures_query = """
                    SELECT normalized_score, percentile_rank
                    FROM aggregated_scores
                    WHERE fips = ? 
                    AND parent_measure = ?
                    AND measure_level = 'sub_measure'
                    AND normalized_score IS NOT NULL
                """
                
                submeasures_df = pd.read_sql(submeasures_query, self.conn,
                                           params=[fips, top_level])
                
                total_components = len(submeasures_df)
                valid_components = len(submeasures_df[submeasures_df['normalized_score'].notna()])
                missing_components = total_components - valid_components
                
                if valid_components > 0:
                    avg_normalized = submeasures_df['normalized_score'].mean()
                    avg_percentile = submeasures_df['percentile_rank'].mean()
                    completeness_ratio = valid_components / total_components if total_components > 0 else 0
                    raw_score = avg_percentile
                else:
                    avg_normalized = None
                    avg_percentile = None
                    raw_score = None
                    completeness_ratio = 0.0
                
                aggregated_data.append((
                    fips,
                    top_level,
                    'top_level',
                    None,  # no parent measure
                    raw_score,
                    avg_normalized,
                    avg_percentile,
                    total_components,
                    missing_components,
                    completeness_ratio
                ))
        
        # Insert aggregated top-level measures
        cursor.executemany('''
            INSERT OR REPLACE INTO aggregated_scores
            (fips, measure_name, measure_level, parent_measure, raw_score,
             normalized_score, percentile_rank, component_count, 
             missing_components, completeness_ratio)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', aggregated_data)
        
        self.conn.commit()
        print(f"   ✅ Aggregated {len(aggregated_data)} top-level measure scores")
        
        return len(aggregated_data)
    
    def generate_normalization_summary(self):
        """Generate summary of normalization results"""
        print("\n📋 NORMALIZATION SUMMARY:")
        print("=" * 50)
        
        cursor = self.conn.cursor()
        
        # Metric statistics summary
        stats_summary = pd.read_sql("""
            SELECT 
                COUNT(*) as total_metrics,
                AVG(data_quality_score) * 100 as avg_data_quality,
                COUNT(CASE WHEN is_reverse_metric = 1 THEN 1 END) as reverse_metrics,
                COUNT(CASE WHEN data_quality_score > 0.8 THEN 1 END) as high_quality_metrics
            FROM metric_statistics
        """, self.conn)
        
        stats = stats_summary.iloc[0]
        print(f"Metrics processed: {stats['total_metrics']}")
        print(f"Average data quality: {stats['avg_data_quality']:.1f}%")
        print(f"Reverse metrics (lower is better): {stats['reverse_metrics']}")
        print(f"High quality metrics (>80% complete): {stats['high_quality_metrics']}")
        
        # Normalization results
        norm_summary = pd.read_sql("""
            SELECT 
                COUNT(*) as total_normalized,
                COUNT(CASE WHEN is_missing = 0 THEN 1 END) as valid_normalized,
                COUNT(CASE WHEN is_missing = 1 THEN 1 END) as missing_normalized
            FROM normalized_metrics
        """, self.conn)
        
        norm = norm_summary.iloc[0]
        print(f"\nNormalized values: {norm['total_normalized']:,}")
        print(f"Valid normalized: {norm['valid_normalized']:,} ({norm['valid_normalized']/norm['total_normalized']*100:.1f}%)")
        print(f"Missing values: {norm['missing_normalized']:,}")
        
        # Aggregation results
        agg_summary = pd.read_sql("""
            SELECT 
                measure_level,
                COUNT(*) as count,
                AVG(completeness_ratio) * 100 as avg_completeness
            FROM aggregated_scores
            GROUP BY measure_level
            ORDER BY 
                CASE measure_level 
                    WHEN 'top_level' THEN 1 
                    WHEN 'sub_measure' THEN 2 
                    WHEN 'metric_group' THEN 3 
                END
        """, self.conn)
        
        print(f"\nAggregation Results:")
        for _, row in agg_summary.iterrows():
            print(f"  {row['measure_level']}: {row['count']} measures ({row['avg_completeness']:.1f}% avg completeness)")
        
        # Sample normalized data
        sample_query = """
            SELECT 
                c.state, c.county, nm.metric_name, nm.raw_value, 
                nm.normalized_value, nm.percentile_rank
            FROM normalized_metrics nm
            JOIN counties c ON nm.fips = c.fips
            WHERE nm.is_missing = 0
            ORDER BY RANDOM()
            LIMIT 5
        """
        
        sample_df = pd.read_sql(sample_query, self.conn)
        print(f"\nSample Normalized Data:")
        for _, row in sample_df.iterrows():
            print(f"  {row['county']}, {row['state']}: {row['metric_name']}")
            print(f"    Raw: {row['raw_value']:.2f} → Z-score: {row['normalized_value']:.2f} → Percentile: {row['percentile_rank']:.1f}%")
    
    def run_stage2(self):
        """Execute complete Stage 2 pipeline"""
        print("🚀 STARTING STAGE 2: Normalization and Percentile Calculations")
        print("=" * 70)
        
        try:
            # Step 1: Create normalization tables
            self.create_normalization_tables()
            
            # Step 2: Calculate statistics for each metric
            metrics_processed = self.calculate_metric_statistics()
            
            # Step 3: Normalize all metrics using Z-scores
            values_normalized = self.normalize_metrics()
            
            # Step 4: Aggregate sub-metrics into metric groups
            groups_aggregated = self.aggregate_metric_groups()
            
            # Step 5: Aggregate metrics into sub-measures
            submeasures_aggregated = self.aggregate_sub_measures()
            
            # Step 6: Aggregate sub-measures into top-level measures
            toplevel_aggregated = self.aggregate_top_level_measures()
            
            # Step 7: Generate summary
            self.generate_normalization_summary()
            
            print(f"\n✅ STAGE 2 COMPLETED SUCCESSFULLY!")
            print(f"   Metrics processed: {metrics_processed}")
            print(f"   Values normalized: {values_normalized:,}")
            print(f"   Metric groups: {groups_aggregated}")
            print(f"   Sub-measures: {submeasures_aggregated}")
            print(f"   Top-level measures: {toplevel_aggregated}")
            
        except Exception as e:
            print(f"❌ ERROR in Stage 2: {str(e)}")
            raise
        finally:
            if self.conn:
                self.conn.close()

# Usage example
if __name__ == "__main__":
    # Initialize the normalizer
    normalizer = SustainabilityNormalizer('sustainability_data.db')
    
    # Run Stage 2
    normalizer.run_stage2()
    
    print("\n🎯 Next Steps:")
    print("   - Verify normalized data quality")
    print("   - Test aggregated scores")
    print("   - Integrate with radar chart visualization")
    print("   - Build query functions for the dashboard")