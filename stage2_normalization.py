import pandas as pd
from google.cloud import bigquery
import numpy as np
from scipy import stats
import warnings
import uuid
import time
warnings.filterwarnings('ignore')

class BigQuerySustainabilityNormalizer:
    """
    Stage 2: Implement normalization and percentile calculations for sustainability metrics
    Using BigQuery for storage and processing
    """
    
    def __init__(self, project_id, dataset_id):
        """
        Initialize with BigQuery project and dataset
        
        Example:
        project_id = 'county-dashboard-uc-r'
        dataset_id = 'sustainability_data'
        """
        self.project_id = project_id
        self.dataset_id = dataset_id
        self.client = None
        
        # Define metrics where "lower is better" (these need reversed percentiles)
        self.reverse_metrics = {
            # Health metrics (lower is better)
            'PEOPLE_HEALTH_LENGTHOFLIFE_PREMATUREDEATH',
            'PEOPLE_HEALTH_QUALITYOFLIFE_FREQPHYDISTRESS', 
            'PEOPLE_HEALTH_QUALITYOFLIFE_FREQMENDISTRESS',
            'PEOPLE_HEALTH_QUALITYOFLIFE_ADULTWITHDIABETES',
            'PEOPLE_HEALTH_QUALITYOFLIFE_HIVPREVRATE',
            'PEOPLE_HEALTH_HEALTHBEHAVIOURS_ADULTSWITHOBESITY',
            'PEOPLE_HEALTH_HEALTHBEHAVIOURS_ADULTSSMOKING',
            'PEOPLE_HEALTH_HEALTHBEHAVIOURS_EXCESSIVEDRINKING',
            'PEOPLE_HEALTH_HEALTHBEHAVIOURS_PHYSICALLYINACTIVE',
            'PEOPLE_HEALTH_HEALTHBEHAVIOURS_INSUFFICIENTSLEEP',
            'PEOPLE_HEALTH_HEALTHRESOURCES_ACCESSTOCARE_UNINSURED',
            'PEOPLE_HEALTH_HEALTHRESOURCES_QUALITYOFCARE_PREVENTABLEHOSPITALIZATIONRATE',
            
            # Community metrics (lower is better)
            'PEOPLE_COMMUNITY_SEVEREHOUSINGPROBLEMS',
            'PEOPLE_COMMUNITY_FOODINSECURITY',
            'PEOPLE_COMMUNITY_LONGCOMMUTEANDDRIVESALONE',
            'PEOPLE_COMMUNITY_VIOLENTCRIMERATE',
            
            # Wealth metrics (lower is better)
            'PEOPLE_WEALTH_INCOMERATIO80BY20',
            'PEOPLE_WEALTH_CHILDPOVERTY',
            
            # Business/Government metrics (some lower is better)
            'PRODUCTIVITY_GOVERNMENT_VIOLENTCRIMERATE',
            'PRODUCTIVITY_GOVERNMENT_SEVEREHOUSINGPROBLEMS',
            'PRODUCTIVITY_GOVERNMENT_DEPENDENCYRATIO',
            
            # Employment metrics (lower is better)
            'PRODUCTIVITY_EMPLOYMENT_UNEMPLOYMENTRATE',
            
            # Environmental metrics (lower is better)  
            'PLACE_CLIMATEANDRESILIENCE_CO2ORCAPITA',
            'Place_LandAirWater_AirQualityIndexPerPm2.5',
            'PLACE_LANDAIRWATER_WATERCONSERVATIONORGALLONSORPERSONORDAY'
        }
    
    def connect(self):
        """Establish connection to BigQuery"""
        try:
            self.client = bigquery.Client(project=self.project_id)
            print(f"✅ Connected to BigQuery: {self.project_id}.{self.dataset_id}")
            return True
        except Exception as e:
            print(f"❌ Failed to connect to BigQuery: {str(e)}")
            return False
    
    def create_normalization_tables(self):
        """Create tables for normalized data and statistics IN BigQuery"""
        print("📋 Creating normalization tables in BigQuery...")
        
        # Drop existing tables if they exist
        tables_to_drop = ['metric_statistics', 'normalized_metrics', 'aggregated_scores']
        for table_name in tables_to_drop:
            table_id = f"{self.project_id}.{self.dataset_id}.{table_name}"
            self.client.delete_table(table_id, not_found_ok=True)
        
        # Create metric statistics table
        stats_schema = [
            bigquery.SchemaField("metric_name", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("total_counties", "INTEGER"),
            bigquery.SchemaField("valid_counties", "INTEGER"),
            bigquery.SchemaField("missing_counties", "INTEGER"),
            bigquery.SchemaField("mean_value", "FLOAT"),
            bigquery.SchemaField("std_dev", "FLOAT"),
            bigquery.SchemaField("min_value", "FLOAT"),
            bigquery.SchemaField("max_value", "FLOAT"),
            bigquery.SchemaField("median_value", "FLOAT"),
            bigquery.SchemaField("is_reverse_metric", "BOOLEAN"),
            bigquery.SchemaField("data_quality_score", "FLOAT"),
        ]
        
        stats_table_id = f"{self.project_id}.{self.dataset_id}.metric_statistics"
        stats_table = bigquery.Table(stats_table_id, schema=stats_schema)
        self.client.create_table(stats_table)
        print("   ✅ Created metric_statistics table")
        
        # Create normalized metrics table
        norm_schema = [
            bigquery.SchemaField("fips", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("metric_name", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("raw_value", "FLOAT"),
            bigquery.SchemaField("normalized_value", "FLOAT"),
            bigquery.SchemaField("percentile_rank", "FLOAT"),
            bigquery.SchemaField("is_missing", "BOOLEAN"),
        ]
        
        norm_table_id = f"{self.project_id}.{self.dataset_id}.normalized_metrics"
        norm_table = bigquery.Table(norm_table_id, schema=norm_schema)
        self.client.create_table(norm_table)
        print("   ✅ Created normalized_metrics table")
        
        # Create aggregated scores table
        agg_schema = [
            bigquery.SchemaField("fips", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("measure_name", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("measure_level", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("parent_measure", "STRING"),
            bigquery.SchemaField("raw_score", "FLOAT"),
            bigquery.SchemaField("normalized_score", "FLOAT"),
            bigquery.SchemaField("percentile_rank", "FLOAT"),
            bigquery.SchemaField("component_count", "INTEGER"),
            bigquery.SchemaField("missing_components", "INTEGER"),
            bigquery.SchemaField("completeness_ratio", "FLOAT"),
        ]
        
        agg_table_id = f"{self.project_id}.{self.dataset_id}.aggregated_scores"
        agg_table = bigquery.Table(agg_table_id, schema=agg_schema)
        self.client.create_table(agg_table)
        print("   ✅ Created aggregated_scores table")
        
        print("✅ Normalization tables created successfully in BigQuery")
    
    def calculate_metric_statistics(self):
        """Calculate statistics for each metric across all counties using BigQuery SQL"""
        print("📊 Calculating metric statistics in BigQuery...")
        
        # Calculate basic statistics using BigQuery's aggregate functions
        query = f"""
            INSERT INTO `{self.project_id}.{self.dataset_id}.metric_statistics`
            (metric_name, total_counties, valid_counties, missing_counties,
             mean_value, std_dev, min_value, max_value, median_value,
             is_reverse_metric, data_quality_score)
            SELECT 
                metric_name,
                COUNT(*) as total_counties,
                COUNTIF(is_missing = FALSE) as valid_counties,
                COUNTIF(is_missing = TRUE) as missing_counties,
                AVG(raw_value) as mean_value,
                STDDEV_SAMP(raw_value) as std_dev,
                MIN(raw_value) as min_value,
                MAX(raw_value) as max_value,
                APPROX_QUANTILES(raw_value, 2)[OFFSET(1)] as median_value,
                FALSE as is_reverse_metric,
                SAFE_DIVIDE(COUNTIF(is_missing = FALSE), COUNT(*)) as data_quality_score
            FROM `{self.project_id}.{self.dataset_id}.raw_metrics`
            WHERE raw_value IS NOT NULL
            GROUP BY metric_name
            HAVING COUNTIF(is_missing = FALSE) >= 10
        """
        
        job = self.client.query(query)
        job.result()  # Wait for completion
        
        # Update reverse metrics flag
        reverse_metrics_list = ', '.join([f"'{m}'" for m in self.reverse_metrics])
        update_query = f"""
            UPDATE `{self.project_id}.{self.dataset_id}.metric_statistics`
            SET is_reverse_metric = TRUE
            WHERE metric_name IN ({reverse_metrics_list})
        """
        
        job = self.client.query(update_query)
        job.result()
        
        # Get count of metrics processed
        count_query = f"""
            SELECT COUNT(*) as count 
            FROM `{self.project_id}.{self.dataset_id}.metric_statistics`
        """
        metrics_count = self.client.query(count_query).to_dataframe().iloc[0]['count']
        
        print(f"   ✅ Calculated statistics for {metrics_count} metrics")
        return metrics_count
    
    def normalize_metrics(self):
        """Apply Z-score normalization to all metrics using BigQuery SQL with Python for percentiles"""
        print("🔄 Normalizing metrics using Z-scores...")
        
        # Get all metrics with their statistics
        stats_query = f"""
            SELECT metric_name, mean_value, std_dev, is_reverse_metric
            FROM `{self.project_id}.{self.dataset_id}.metric_statistics`
            WHERE std_dev > 0
        """
        stats_df = self.client.query(stats_query).to_dataframe()
        
        # Check which metrics are already processed
        processed_query = f"""
            SELECT DISTINCT metric_name 
            FROM `{self.project_id}.{self.dataset_id}.normalized_metrics`
        """
        try:
            processed_df = self.client.query(processed_query).to_dataframe()
            processed_metrics = set(processed_df['metric_name'].tolist())
            print(f"   Found {len(processed_metrics)} already processed metrics")
        except:
            processed_metrics = set()
        
        total_normalized = 0
        total_metrics = len(stats_df)
        
        for idx, (_, stat_row) in enumerate(stats_df.iterrows(), 1):
            metric_name = stat_row['metric_name']
            
            # Skip if already processed
            if metric_name in processed_metrics:
                print(f"   Skipping metric {idx}/{total_metrics}: {metric_name[:60]} (already processed)")
                continue
            
            mean_val = stat_row['mean_value']
            std_val = stat_row['std_dev']
            is_reverse = stat_row['is_reverse_metric']
            
            # Show progress
            print(f"   Processing metric {idx}/{total_metrics}: {metric_name[:60]}...")
            
            # Retry logic for network errors
            max_retries = 3
            retry_count = 0
            success = False
            
            while retry_count < max_retries and not success:
                try:
                    # Get all raw values for this metric from BigQuery
                    values_query = f"""
                        SELECT fips, raw_value, is_missing
                        FROM `{self.project_id}.{self.dataset_id}.raw_metrics`
                        WHERE metric_name = '{metric_name}'
                    """
                    values_df = self.client.query(values_query).to_dataframe()
                    
                    # Get all valid values for percentile calculation
                    all_values_query = f"""
                        SELECT raw_value 
                        FROM `{self.project_id}.{self.dataset_id}.raw_metrics`
                        WHERE metric_name = '{metric_name}' AND is_missing = FALSE AND raw_value IS NOT NULL
                    """
                    all_values_df = self.client.query(all_values_query).to_dataframe()
                    all_values = all_values_df['raw_value'].values
                    
                    # Prepare batch data for insertion
                    normalized_data = []
                    
                    for _, value_row in values_df.iterrows():
                        fips = value_row['fips']
                        raw_value = value_row['raw_value']
                        is_missing = value_row['is_missing']
                        
                        # Convert pandas NaN to None for BigQuery
                        if pd.isna(raw_value):
                            raw_value = None
                        if pd.isna(is_missing):
                            is_missing = False
                        
                        if is_missing or raw_value is None:
                            normalized_value = None
                            percentile_rank = None
                        else:
                            # Calculate Z-score
                            z_score = (raw_value - mean_val) / std_val
                            normalized_value = float(z_score) if not np.isnan(z_score) else None
                            
                            # Calculate percentile rank using scipy
                            if is_reverse:
                                percentile_rank = 100 - stats.percentileofscore(all_values, raw_value)
                            else:
                                percentile_rank = stats.percentileofscore(all_values, raw_value)
                            
                            # Convert to float and handle NaN
                            percentile_rank = float(percentile_rank) if not np.isnan(percentile_rank) else None
                        
                        normalized_data.append({
                            'fips': fips,
                            'metric_name': metric_name,
                            'raw_value': raw_value,
                            'normalized_value': normalized_value,
                            'percentile_rank': percentile_rank,
                            'is_missing': is_missing
                        })
                    
                    # Batch insert into BigQuery with unique job ID
                    if normalized_data:
                        norm_df = pd.DataFrame(normalized_data)
                        table_id = f"{self.project_id}.{self.dataset_id}.normalized_metrics"
                        
                        # Generate unique job ID to avoid conflicts
                        job_id = f"load_normalized_{uuid.uuid4().hex}"
                        
                        job_config = bigquery.LoadJobConfig(write_disposition="WRITE_APPEND")
                        job = self.client.load_table_from_dataframe(
                            norm_df, 
                            table_id, 
                            job_config=job_config,
                            job_id=job_id
                        )
                        job.result()
                        
                        total_normalized += len(normalized_data)
                        success = True
                        print(f"      ✅ Successfully uploaded {len(normalized_data)} rows")
                    
                except Exception as e:
                    retry_count += 1
                    if retry_count < max_retries:
                        print(f"      ⚠️  Error occurred, retrying ({retry_count}/{max_retries})...")
                        time.sleep(5)  # Wait 5 seconds before retry
                    else:
                        print(f"      ❌ Failed after {max_retries} retries: {str(e)}")
                        print(f"      Continuing with next metric...")
                        break
        
        print(f"   ✅ Normalized {total_normalized:,} metric values in BigQuery")
        return total_normalized
    
    def aggregate_metric_groups(self):
        """Aggregate sub-metrics into metric groups using bulk SQL"""
        print("📋 Aggregating sub-metrics into metric groups...")
        
        # Use a single SQL query to calculate all metric group aggregations
        query = f"""
            INSERT INTO `{self.project_id}.{self.dataset_id}.aggregated_scores`
            (fips, measure_name, measure_level, parent_measure, raw_score,
             normalized_score, percentile_rank, component_count, 
             missing_components, completeness_ratio)
            SELECT 
                nm.fips,
                CONCAT(rm.top_level, '_', rm.sub_measure, '_', rm.metric_group) as measure_name,
                'metric_group' as measure_level,
                CONCAT(rm.top_level, '_', rm.sub_measure) as parent_measure,
                AVG(IF(nm.is_missing = FALSE, nm.percentile_rank, NULL)) as raw_score,
                AVG(IF(nm.is_missing = FALSE, nm.normalized_value, NULL)) as normalized_score,
                AVG(IF(nm.is_missing = FALSE, nm.percentile_rank, NULL)) as percentile_rank,
                COUNT(*) as component_count,
                COUNTIF(nm.is_missing = TRUE) as missing_components,
                SAFE_DIVIDE(COUNTIF(nm.is_missing = FALSE), COUNT(*)) as completeness_ratio
            FROM `{self.project_id}.{self.dataset_id}.normalized_metrics` nm
            JOIN `{self.project_id}.{self.dataset_id}.raw_metrics` rm 
                ON nm.fips = rm.fips AND nm.metric_name = rm.metric_name
            WHERE rm.metric_group IS NOT NULL
            GROUP BY nm.fips, rm.top_level, rm.sub_measure, rm.metric_group
            HAVING COUNT(DISTINCT rm.metric_name) > 1
        """
        
        job = self.client.query(query)
        job.result()
        
        # Get count of inserted rows
        count_query = f"""
            SELECT COUNT(*) as count 
            FROM `{self.project_id}.{self.dataset_id}.aggregated_scores` 
            WHERE measure_level = 'metric_group'
        """
        count = self.client.query(count_query).to_dataframe().iloc[0]['count']
        
        print(f"   ✅ Aggregated {count} metric group scores")
        return count
    
    def aggregate_sub_measures(self):
        """Aggregate metrics and metric groups into sub-measures using CTE (Common Table Expression)"""
        print("📊 Aggregating metrics into sub-measures...")
        
        # Use a single query with CTEs instead of temp tables
        query = f"""
            INSERT INTO `{self.project_id}.{self.dataset_id}.aggregated_scores`
            (fips, measure_name, measure_level, parent_measure, raw_score,
             normalized_score, percentile_rank, component_count, 
             missing_components, completeness_ratio)
            
            WITH temp_submeasure_metrics AS (
                SELECT 
                    nm.fips,
                    CONCAT(rm.top_level, '_', rm.sub_measure) as measure_name,
                    AVG(IF(nm.is_missing = FALSE, nm.normalized_value, NULL)) as avg_normalized,
                    AVG(IF(nm.is_missing = FALSE, nm.percentile_rank, NULL)) as avg_percentile,
                    COUNT(*) as component_count,
                    COUNTIF(nm.is_missing = TRUE) as missing_count
                FROM `{self.project_id}.{self.dataset_id}.normalized_metrics` nm
                JOIN `{self.project_id}.{self.dataset_id}.raw_metrics` rm 
                    ON nm.fips = rm.fips AND nm.metric_name = rm.metric_name
                GROUP BY nm.fips, rm.top_level, rm.sub_measure
            ),
            temp_submeasure_groups AS (
                SELECT 
                    fips,
                    parent_measure as measure_name,
                    AVG(normalized_score) as avg_normalized,
                    AVG(percentile_rank) as avg_percentile,
                    COUNT(*) as component_count,
                    SUM(missing_components) as missing_count
                FROM `{self.project_id}.{self.dataset_id}.aggregated_scores`
                WHERE measure_level = 'metric_group'
                GROUP BY fips, parent_measure
            )
            
            SELECT 
                COALESCE(m.fips, g.fips) as fips,
                COALESCE(m.measure_name, g.measure_name) as measure_name,
                'sub_measure' as measure_level,
                SPLIT(COALESCE(m.measure_name, g.measure_name), '_')[OFFSET(0)] as parent_measure,
                SAFE_DIVIDE(
                    COALESCE(m.avg_percentile, 0) * COALESCE(m.component_count, 0) + 
                    COALESCE(g.avg_percentile, 0) * COALESCE(g.component_count, 0),
                    COALESCE(m.component_count, 0) + COALESCE(g.component_count, 0)
                ) as raw_score,
                SAFE_DIVIDE(
                    COALESCE(m.avg_normalized, 0) * COALESCE(m.component_count, 0) + 
                    COALESCE(g.avg_normalized, 0) * COALESCE(g.component_count, 0),
                    COALESCE(m.component_count, 0) + COALESCE(g.component_count, 0)
                ) as normalized_score,
                SAFE_DIVIDE(
                    COALESCE(m.avg_percentile, 0) * COALESCE(m.component_count, 0) + 
                    COALESCE(g.avg_percentile, 0) * COALESCE(g.component_count, 0),
                    COALESCE(m.component_count, 0) + COALESCE(g.component_count, 0)
                ) as percentile_rank,
                COALESCE(m.component_count, 0) + COALESCE(g.component_count, 0) as component_count,
                COALESCE(m.missing_count, 0) + COALESCE(g.missing_count, 0) as missing_components,
                SAFE_DIVIDE(
                    COALESCE(m.component_count, 0) + COALESCE(g.component_count, 0) - 
                    COALESCE(m.missing_count, 0) - COALESCE(g.missing_count, 0),
                    COALESCE(m.component_count, 0) + COALESCE(g.component_count, 0)
                ) as completeness_ratio
            FROM temp_submeasure_metrics m
            FULL OUTER JOIN temp_submeasure_groups g 
                ON m.fips = g.fips AND m.measure_name = g.measure_name
        """
        
        job = self.client.query(query)
        job.result()  # Wait for completion
        
        # Get count
        count_query = f"""
            SELECT COUNT(*) as count 
            FROM `{self.project_id}.{self.dataset_id}.aggregated_scores` 
            WHERE measure_level = 'sub_measure'
        """
        count = self.client.query(count_query).to_dataframe().iloc[0]['count']
        
        print(f"   ✅ Aggregated {count} sub-measure scores")
        return count
    
    def aggregate_top_level_measures(self):
        """Aggregate sub-measures into top-level measures using bulk SQL"""
        print("🌍 Aggregating sub-measures into top-level measures...")
        
        # Use a single SQL query to calculate all top-level aggregations
        query = f"""
            INSERT INTO `{self.project_id}.{self.dataset_id}.aggregated_scores`
            (fips, measure_name, measure_level, parent_measure, raw_score,
            normalized_score, percentile_rank, component_count, 
            missing_components, completeness_ratio)
            SELECT 
                sub.fips,
                sub.parent_measure as measure_name,
                'top_level' as measure_level,
                CAST(NULL AS STRING) as parent_measure,
                AVG(IF(sub.normalized_score IS NOT NULL, sub.percentile_rank, NULL)) as raw_score,
                AVG(IF(sub.normalized_score IS NOT NULL, sub.normalized_score, NULL)) as normalized_score,
                AVG(IF(sub.normalized_score IS NOT NULL, sub.percentile_rank, NULL)) as percentile_rank,
                COUNT(*) as component_count,
                COUNTIF(sub.normalized_score IS NULL) as missing_components,
                SAFE_DIVIDE(COUNTIF(sub.normalized_score IS NOT NULL), COUNT(*)) as completeness_ratio
            FROM `{self.project_id}.{self.dataset_id}.aggregated_scores` sub
            WHERE sub.measure_level = 'sub_measure'
            AND sub.parent_measure IN ('People', 'Productivity', 'Place')
            GROUP BY sub.fips, sub.parent_measure
        """
        
        job = self.client.query(query)
        job.result()
        
        # Get count
        count_query = f"""
            SELECT COUNT(*) as count 
            FROM `{self.project_id}.{self.dataset_id}.aggregated_scores` 
            WHERE measure_level = 'top_level'
        """
        count = self.client.query(count_query).to_dataframe().iloc[0]['count']
        
        print(f"   ✅ Aggregated {count} top-level measure scores")
        return count
    def generate_normalization_summary(self):
        """Generate summary of normalization results from BigQuery"""
        print("\n📋 NORMALIZATION SUMMARY:")
        print("=" * 50)
        
        # Metric statistics summary
        stats_query = f"""
            SELECT 
                COUNT(*) as total_metrics,
                AVG(data_quality_score) * 100 as avg_data_quality,
                COUNTIF(is_reverse_metric = TRUE) as reverse_metrics,
                COUNTIF(data_quality_score > 0.8) as high_quality_metrics
            FROM `{self.project_id}.{self.dataset_id}.metric_statistics`
        """
        stats_summary = self.client.query(stats_query).to_dataframe()
        
        stats = stats_summary.iloc[0]
        print(f"Metrics processed: {int(stats['total_metrics'])}")
        print(f"Average data quality: {stats['avg_data_quality']:.1f}%")
        print(f"Reverse metrics (lower is better): {int(stats['reverse_metrics'])}")
        print(f"High quality metrics (>80% complete): {int(stats['high_quality_metrics'])}")
        
        # Normalization results
        norm_query = f"""
            SELECT 
                COUNT(*) as total_normalized,
                COUNTIF(is_missing = FALSE) as valid_normalized,
                COUNTIF(is_missing = TRUE) as missing_normalized
            FROM `{self.project_id}.{self.dataset_id}.normalized_metrics`
        """
        norm_summary = self.client.query(norm_query).to_dataframe()
        
        norm = norm_summary.iloc[0]
        print(f"\nNormalized values: {int(norm['total_normalized']):,}")
        print(f"Valid normalized: {int(norm['valid_normalized']):,} ({norm['valid_normalized']/norm['total_normalized']*100:.1f}%)")
        print(f"Missing values: {int(norm['missing_normalized']):,}")
        
        # Aggregation results
        agg_query = f"""
            SELECT 
                measure_level,
                COUNT(*) as count,
                AVG(completeness_ratio) * 100 as avg_completeness
            FROM `{self.project_id}.{self.dataset_id}.aggregated_scores`
            GROUP BY measure_level
            ORDER BY 
                CASE measure_level 
                    WHEN 'top_level' THEN 1 
                    WHEN 'sub_measure' THEN 2 
                    WHEN 'metric_group' THEN 3 
                END
        """
        agg_summary = self.client.query(agg_query).to_dataframe()
        
        print(f"\nAggregation Results:")
        for _, row in agg_summary.iterrows():
            print(f"  {row['measure_level']}: {int(row['count'])} measures ({row['avg_completeness']:.1f}% avg completeness)")
        
        # Sample normalized data
        sample_query = f"""
            SELECT 
                c.state, c.county, nm.metric_name, nm.raw_value, 
                nm.normalized_value, nm.percentile_rank
            FROM `{self.project_id}.{self.dataset_id}.normalized_metrics` nm
            JOIN `{self.project_id}.{self.dataset_id}.counties` c ON nm.fips = c.fips
            WHERE nm.is_missing = FALSE
            ORDER BY RAND()
            LIMIT 5
        """
        
        sample_df = self.client.query(sample_query).to_dataframe()
        print(f"\nSample Normalized Data:")
        for _, row in sample_df.iterrows():
            print(f"  {row['county']}, {row['state']}: {row['metric_name']}")
            print(f"    Raw: {row['raw_value']:.2f} → Z-score: {row['normalized_value']:.2f} → Percentile: {row['percentile_rank']:.1f}%")
    
    def run_stage2(self):
        """Execute complete Stage 2 pipeline"""
        print("🚀 STARTING STAGE 2: Normalization and Percentile Calculations")
        print("=" * 70)
        print("💾 All data will be stored in BIGQUERY")
        print("=" * 70)
        
        try:
            # Connect to BigQuery
            if not self.connect():
                raise Exception("Failed to connect to BigQuery")
            
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
            print(f"   All data stored in BigQuery")
            print(f"   Project: {self.project_id}")
            print(f"   Dataset: {self.dataset_id}")
            print(f"   Metrics processed: {metrics_processed}")
            print(f"   Values normalized: {values_normalized:,}")
            print(f"   Metric groups: {groups_aggregated}")
            print(f"   Sub-measures: {submeasures_aggregated}")
            print(f"   Top-level measures: {toplevel_aggregated}")
            
        except Exception as e:
            print(f"❌ ERROR in Stage 2: {str(e)}")
            import traceback
            traceback.print_exc()
            raise

# Usage example
if __name__ == "__main__":
    # BigQuery configuration
    project_id = 'county-dashboard'  # UPDATE THIS with your Google Cloud project ID
    dataset_id = 'sustainability_data'
    
    # Initialize the normalizer
    normalizer = BigQuerySustainabilityNormalizer(project_id, dataset_id)
    
    # Run Stage 2 (this will store everything in BigQuery)
    normalizer.run_stage2()
    
    print("\n🎯 Next Steps:")
    print(f"   - View data in BigQuery Console: https://console.cloud.google.com/bigquery")
    print(f"   - Query: SELECT * FROM `{project_id}.{dataset_id}.normalized_metrics` LIMIT 10")
    print(f"   - Test aggregated scores: SELECT * FROM `{project_id}.{dataset_id}.aggregated_scores` WHERE measure_level = 'top_level'")
    print("   - Integrate with your dashboard using BigQuery queries")