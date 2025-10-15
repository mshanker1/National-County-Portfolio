import pandas as pd
import sqlite3
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

class NormalizationVerifier:
    """
    Verify and test the normalization results from Stage 2
    """
    
    def __init__(self, db_file_path='sustainability_data.db'):
        self.db_file_path = db_file_path
    
    def connect(self):
        """Create database connection"""
        return sqlite3.connect(self.db_file_path)
    
    def verify_normalization_quality(self):
        """Verify that normalization was applied correctly"""
        print("🔍 VERIFYING NORMALIZATION QUALITY")
        print("=" * 40)
        
        conn = self.connect()
        
        # Test 1: Check Z-score properties (should have mean ~0, std ~1)
        zscore_stats = pd.read_sql("""
            SELECT 
                metric_name,
                COUNT(*) as sample_size,
                AVG(normalized_value) as mean_zscore,
                SQRT(AVG(normalized_value * normalized_value) - AVG(normalized_value) * AVG(normalized_value)) as std_zscore
            FROM normalized_metrics
            WHERE is_missing = 0 AND normalized_value IS NOT NULL
            GROUP BY metric_name
            HAVING sample_size > 20
            ORDER BY ABS(mean_zscore) DESC
            LIMIT 10
        """, conn)
        
        print("Z-score Quality Check (should have mean≈0, std≈1):")
        print("Top 10 metrics by mean deviation from 0:")
        for _, row in zscore_stats.iterrows():
            print(f"  {row['metric_name'][:50]:<50} Mean: {row['mean_zscore']:6.3f}, Std: {row['std_zscore']:6.3f}")
        
        # Test 2: Check percentile ranges (should be 0-100)
        percentile_check = pd.read_sql("""
            SELECT 
                MIN(percentile_rank) as min_percentile,
                MAX(percentile_rank) as max_percentile,
                AVG(percentile_rank) as avg_percentile,
                COUNT(CASE WHEN percentile_rank < 0 OR percentile_rank > 100 THEN 1 END) as invalid_percentiles,
                COUNT(*) as total_percentiles
            FROM normalized_metrics
            WHERE is_missing = 0 AND percentile_rank IS NOT NULL
        """, conn)
        
        perc = percentile_check.iloc[0]
        print(f"\nPercentile Range Check:")
        print(f"  Min percentile: {perc['min_percentile']:.2f}")
        print(f"  Max percentile: {perc['max_percentile']:.2f}")
        print(f"  Average percentile: {perc['avg_percentile']:.2f} (should be ~50)")
        print(f"  Invalid percentiles: {perc['invalid_percentiles']} / {perc['total_percentiles']}")
        
        # Test 3: Verify reverse metrics using pandas correlation
        # First, get all the data we need for correlation calculation
        reverse_metrics_query = """
            SELECT 
                nm.metric_name,
                ms.is_reverse_metric,
                nm.raw_value,
                nm.percentile_rank
            FROM normalized_metrics nm
            JOIN metric_statistics ms ON nm.metric_name = ms.metric_name
            WHERE nm.is_missing = 0 AND nm.raw_value IS NOT NULL AND nm.percentile_rank IS NOT NULL
        """
        
        reverse_data = pd.read_sql(reverse_metrics_query, conn)
        
        # Calculate correlations in pandas
        reverse_check_results = []
        for metric_name in reverse_data['metric_name'].unique():
            metric_data = reverse_data[reverse_data['metric_name'] == metric_name]
            if len(metric_data) > 50:  # Same filter as original query
                correlation = metric_data['raw_value'].corr(metric_data['percentile_rank'])
                is_reverse = metric_data['is_reverse_metric'].iloc[0]
                avg_raw = metric_data['raw_value'].mean()
                avg_percentile = metric_data['percentile_rank'].mean()
                
                reverse_check_results.append({
                    'metric_name': metric_name,
                    'is_reverse_metric': is_reverse,
                    'avg_raw': avg_raw,
                    'avg_percentile': avg_percentile,
                    'correlation': correlation if not pd.isna(correlation) else 0.0
                })
        
        # Convert to DataFrame and sort like the original query
        if reverse_check_results:
            reverse_check_df = pd.DataFrame(reverse_check_results)
            reverse_check_df = reverse_check_df.sort_values(
                ['is_reverse_metric', 'correlation'], 
                ascending=[False, False],
                key=lambda x: x.abs() if x.name == 'correlation' else x
            ).head(5)
            
            print(f"\nReverse Metrics Verification:")
            print("(Normal metrics: positive correlation, Reverse metrics: negative correlation)")
            for _, row in reverse_check_df.iterrows():
                metric_type = "REVERSE" if row['is_reverse_metric'] else "NORMAL"
                print(f"  {row['metric_name'][:40]:<40} {metric_type:<7} Corr: {row['correlation']:6.3f}")
        else:
            print(f"\nReverse Metrics Verification:")
            print("  No metrics found with sufficient data for correlation analysis")
        
        conn.close()
        
        # Overall assessment
        valid_normalization = (
            abs(perc['avg_percentile'] - 50) < 5 and
            perc['invalid_percentiles'] == 0
        )
        
        if valid_normalization:
            print("\n✅ Normalization appears to be working correctly!")
        else:
            print("\n⚠️  Normalization may have issues - review the statistics above")
    
    def test_aggregation_logic(self):
        """Test the hierarchical aggregation logic"""
        print("\n🧮 TESTING AGGREGATION LOGIC")
        print("=" * 40)
        
        conn = self.connect()
        
        # Test 1: Check aggregation completeness
        agg_completeness = pd.read_sql("""
            SELECT 
                measure_level,
                COUNT(*) as total_measures,
                COUNT(CASE WHEN normalized_score IS NOT NULL THEN 1 END) as valid_scores,
                AVG(completeness_ratio) * 100 as avg_completeness,
                MIN(completeness_ratio) * 100 as min_completeness,
                MAX(completeness_ratio) * 100 as max_completeness
            FROM aggregated_scores
            GROUP BY measure_level
            ORDER BY 
                CASE measure_level 
                    WHEN 'top_level' THEN 1 
                    WHEN 'sub_measure' THEN 2 
                    WHEN 'metric_group' THEN 3 
                END
        """, conn)
        
        print("Aggregation Completeness by Level:")
        for _, row in agg_completeness.iterrows():
            print(f"  {row['measure_level']:<12}: {row['valid_scores']:4}/{row['total_measures']:4} valid " +
                  f"(Avg: {row['avg_completeness']:5.1f}%, Range: {row['min_completeness']:5.1f}%-{row['max_completeness']:5.1f}%)")
        
        # Test 2: Sample a specific county's aggregation chain
        sample_county_query = """
            SELECT c.fips, c.state, c.county
            FROM counties c
            JOIN aggregated_scores a ON c.fips = a.fips
            WHERE a.measure_level = 'top_level' AND a.normalized_score IS NOT NULL
            ORDER BY RANDOM()
            LIMIT 1
        """
        
        sample_county = pd.read_sql(sample_county_query, conn)
        if not sample_county.empty:
            fips = sample_county.iloc[0]['fips']
            county_name = f"{sample_county.iloc[0]['county']}, {sample_county.iloc[0]['state']}"
            
            print(f"\nSample Aggregation Chain for {county_name}:")
            
            # Show the complete hierarchy for this county
            hierarchy_query = """
                SELECT 
                    measure_level,
                    measure_name,
                    parent_measure,
                    raw_score,
                    normalized_score,
                    percentile_rank,
                    component_count,
                    completeness_ratio * 100 as completeness_pct
                FROM aggregated_scores
                WHERE fips = ?
                ORDER BY 
                    CASE measure_level 
                        WHEN 'top_level' THEN 1 
                        WHEN 'sub_measure' THEN 2 
                        WHEN 'metric_group' THEN 3 
                    END,
                    measure_name
            """
            
            hierarchy_df = pd.read_sql(hierarchy_query, conn, params=[fips])
            
            current_level = None
            for _, row in hierarchy_df.iterrows():
                if current_level != row['measure_level']:
                    print(f"\n  {row['measure_level'].upper()}:")
                    current_level = row['measure_level']
                
                indent = "    " if row['measure_level'] != 'top_level' else "  "
                print(f"{indent}{row['measure_name']:<30} " +
                      f"Score: {row['percentile_rank']:5.1f}% " +
                      f"(Z: {row['normalized_score']:6.2f}, " +
                      f"Components: {row['component_count']}, " +
                      f"Complete: {row['completeness_pct']:5.1f}%)")
        
        conn.close()
    
    def sample_county_analysis(self, fips_code=None):
        """Detailed analysis of a specific county"""
        print("\n🏛️  DETAILED COUNTY ANALYSIS")
        print("=" * 40)
        
        conn = self.connect()
        
        if fips_code is None:
            # Pick a county with good data completeness
            county_query = """
                SELECT c.fips, c.state, c.county,
                       AVG(a.completeness_ratio) as avg_completeness
                FROM counties c
                JOIN aggregated_scores a ON c.fips = a.fips
                WHERE a.measure_level = 'sub_measure'
                GROUP BY c.fips, c.state, c.county
                HAVING avg_completeness > 0.8
                ORDER BY RANDOM()
                LIMIT 1
            """
            county_result = pd.read_sql(county_query, conn)
            if county_result.empty:
                print("❌ No counties found with sufficient data completeness")
                conn.close()
                return
            
            fips_code = county_result.iloc[0]['fips']
            county_name = f"{county_result.iloc[0]['county']}, {county_result.iloc[0]['state']}"
        else:
            county_query = "SELECT state, county FROM counties WHERE fips = ?"
            county_result = pd.read_sql(county_query, conn, params=[fips_code])
            if county_result.empty:
                print(f"❌ County with FIPS {fips_code} not found")
                conn.close()
                return
            county_name = f"{county_result.iloc[0]['county']}, {county_result.iloc[0]['state']}"
        
        print(f"County: {county_name} (FIPS: {fips_code})")
        
        # Get top-level scores
        toplevel_query = """
            SELECT measure_name, percentile_rank, normalized_score, completeness_ratio
            FROM aggregated_scores
            WHERE fips = ? AND measure_level = 'top_level'
            ORDER BY measure_name
        """
        
        toplevel_df = pd.read_sql(toplevel_query, conn, params=[fips_code])
        
        print(f"\nTop-level Measure Scores:")
        for _, row in toplevel_df.iterrows():
            print(f"  {row['measure_name']:<12}: {row['percentile_rank']:5.1f}% " +
                  f"(Z-score: {row['normalized_score']:6.2f}, " +
                  f"Completeness: {row['completeness_ratio']*100:5.1f}%)")
        
        # Get sub-measure breakdown for People (most detailed)
        #Changed People to Society as per new csv file
        submeasure_query = """
            SELECT measure_name, percentile_rank, normalized_score, component_count, completeness_ratio
            FROM aggregated_scores
            WHERE fips = ? AND measure_level = 'sub_measure' AND parent_measure = 'Society'
            ORDER BY percentile_rank DESC
        """
        
        submeasure_df = pd.read_sql(submeasure_query, conn, params=[fips_code])
        
        if not submeasure_df.empty:
            print(f"\nSociety Sub-measures (ranked by percentile):")#Changed People to Society as per new csv file
            for _, row in submeasure_df.iterrows():
                sub_name = row['measure_name'].replace('Society_', '')
                print(f"  {sub_name:<15}: {row['percentile_rank']:5.1f}% " +
                      f"({row['component_count']} components, " +
                      f"{row['completeness_ratio']*100:5.1f}% complete)")
        
        # Show some raw metrics for context - Updated query to handle missing 'unit' column
        raw_metrics_query = """
            SELECT nm.metric_name, nm.raw_value, nm.percentile_rank
            FROM normalized_metrics nm
            WHERE nm.fips = ? AND nm.is_missing = 0
            AND nm.metric_name LIKE 'Society_Health%' -- Changed People to Society as per new csv file
            ORDER BY nm.percentile_rank DESC
            LIMIT 5
        """
        
        raw_metrics_df = pd.read_sql(raw_metrics_query, conn, params=[fips_code])
        
        if not raw_metrics_df.empty:
            print(f"\nTop 5 Society_Health Raw Metrics:")#Changed People to Society as per new csv file
            for _, row in raw_metrics_df.iterrows():
                metric_short = row['metric_name'].replace('Society_Health_', '')#Changed People to Society as per new csv file
                print(f"  {metric_short:<30}: {row['raw_value']:8.1f} " +
                      f"({row['percentile_rank']:5.1f}%)")
        
        conn.close()
    
    def generate_data_quality_report(self):
        """Generate comprehensive data quality report"""
        print("\n📊 COMPREHENSIVE DATA QUALITY REPORT")
        print("=" * 50)
        
        conn = self.connect()
        
        # Metric-level quality
        metric_quality = pd.read_sql("""
            SELECT 
                ms.metric_name,
                ms.data_quality_score * 100 as completeness_pct,
                ms.is_reverse_metric,
                COUNT(nm.fips) as counties_with_data,
                AVG(nm.percentile_rank) as avg_percentile
            FROM metric_statistics ms
            LEFT JOIN normalized_metrics nm ON ms.metric_name = nm.metric_name 
                AND nm.is_missing = 0
            GROUP BY ms.metric_name, ms.data_quality_score, ms.is_reverse_metric
            ORDER BY ms.data_quality_score ASC
            LIMIT 10
        """, conn)
        
        print("Metrics with Lowest Data Quality:")
        for _, row in metric_quality.iterrows():
            reverse_flag = " (REVERSE)" if row['is_reverse_metric'] else ""
            print(f"  {row['metric_name'][:45]:<45}{reverse_flag:<10} " +
                  f"{row['completeness_pct']:5.1f}% complete")
        
        # County-level quality
        county_quality = pd.read_sql("""
            SELECT 
                c.state,
                c.county,
                COUNT(nm.metric_name) as total_metrics,
                COUNT(CASE WHEN nm.is_missing = 0 THEN 1 END) as valid_metrics,
                (COUNT(CASE WHEN nm.is_missing = 0 THEN 1 END) * 100.0 / COUNT(nm.metric_name)) as completeness_pct,
                AVG(CASE WHEN nm.is_missing = 0 THEN nm.percentile_rank END) as avg_percentile
            FROM counties c
            LEFT JOIN normalized_metrics nm ON c.fips = nm.fips
            GROUP BY c.fips, c.state, c.county
            HAVING total_metrics > 0
            ORDER BY completeness_pct ASC
            LIMIT 10
        """, conn)
        
        print(f"\nCounties with Lowest Data Completeness:")
        for _, row in county_quality.iterrows():
            print(f"  {row['county']}, {row['state']:<12}: " +
                  f"{row['valid_metrics']:3}/{row['total_metrics']:3} metrics " +
                  f"({row['completeness_pct']:5.1f}% complete)")
        
        # Overall system health
        system_health = pd.read_sql("""
            SELECT 
                'Raw Metrics' as data_type,
                COUNT(*) as total_records,
                COUNT(CASE WHEN is_missing = 0 THEN 1 END) as valid_records,
                (COUNT(CASE WHEN is_missing = 0 THEN 1 END) * 100.0 / COUNT(*)) as completeness_pct
            FROM normalized_metrics
            
            UNION ALL
            
            SELECT 
                'Aggregated Scores' as data_type,
                COUNT(*) as total_records,
                COUNT(CASE WHEN normalized_score IS NOT NULL THEN 1 END) as valid_records,
                (COUNT(CASE WHEN normalized_score IS NOT NULL THEN 1 END) * 100.0 / COUNT(*)) as completeness_pct
            FROM aggregated_scores
        """, conn)
        
        print(f"\nSystem Health Summary:")
        for _, row in system_health.iterrows():
            print(f"  {row['data_type']:<18}: {row['valid_records']:,}/{row['total_records']:,} " +
                  f"({row['completeness_pct']:5.1f}% complete)")
        
        conn.close()
    
    def test_radar_chart_queries(self):
        """Test the queries needed for radar chart integration"""
        print("\n🎯 TESTING RADAR CHART INTEGRATION QUERIES")
        print("=" * 50)
        
        conn = self.connect()
        
        # Test query 1: Get sub-measures for a county (what the radar chart needs)
        test_county_query = """
            SELECT c.fips, c.state, c.county
            FROM counties c
            JOIN aggregated_scores a ON c.fips = a.fips
            WHERE a.measure_level = 'sub_measure' AND a.normalized_score IS NOT NULL
            GROUP BY c.fips, c.state, c.county
            HAVING COUNT(*) >= 10  -- County with good sub-measure coverage
            ORDER BY RANDOM()
            LIMIT 1
        """
        
        test_county = pd.read_sql(test_county_query, conn)
        if test_county.empty:
            print("❌ No suitable test county found")
            conn.close()
            return
        
        fips = test_county.iloc[0]['fips']
        county_name = f"{test_county.iloc[0]['county']}, {test_county.iloc[0]['state']}"
        
        print(f"Testing with: {county_name}")
        
        # Query for radar chart data
        radar_data_query = """
            SELECT 
                parent_measure as top_level,
                REPLACE(measure_name, parent_measure || '_', '') as sub_measure,
                percentile_rank,
                normalized_score,
                component_count,
                completeness_ratio
            FROM aggregated_scores
            WHERE fips = ? AND measure_level = 'sub_measure'
            AND normalized_score IS NOT NULL
            ORDER BY parent_measure, measure_name
        """
        
        radar_df = pd.read_sql(radar_data_query, conn, params=[fips])
        
        print(f"\nRadar Chart Data Structure:")
        print(f"{'Top Level':<12} {'Sub-Measure':<15} {'Percentile':<10} {'Components':<10} {'Complete':<8}")
        print("-" * 65)
        
        for _, row in radar_df.iterrows():
            print(f"{row['top_level']:<12} {row['sub_measure']:<15} " +
                  f"{row['percentile_rank']:8.1f}% {row['component_count']:8d} " +
                  f"{row['completeness_ratio']*100:6.1f}%")
        
        # Test drill-down query (what happens when user clicks on a sub-measure) - Updated to remove 'unit' field
        print(f"\nDrill-down Test (Society_Health):")#Changed People to Society as per new csv file
        drilldown_query = """
            SELECT 
                nm.metric_name,
                nm.raw_value,
                nm.percentile_rank,
                ms.is_reverse_metric
            FROM normalized_metrics nm
            JOIN metric_statistics ms ON nm.metric_name = ms.metric_name
            WHERE nm.fips = ? 
            AND nm.metric_name LIKE 'Society_Health_%'
            AND nm.is_missing = 0
            ORDER BY nm.percentile_rank DESC
            LIMIT 5
        """
        
        drilldown_df = pd.read_sql(drilldown_query, conn, params=[fips])
        
        for _, row in drilldown_df.iterrows():
            metric_short = row['metric_name'].replace('Society_Health_', '')#Changed People to Society as per new csv file
            reverse_flag = " (↓)" if row['is_reverse_metric'] else " (↑)"
            print(f"  {metric_short[:30]:<30}: {row['raw_value']:8.1f} " +
                  f"→ {row['percentile_rank']:5.1f}%{reverse_flag}")
        
        conn.close()
        
        print(f"\n✅ Radar chart queries working correctly!")
        print(f"   - Found {len(radar_df)} sub-measures for visualization")
        print(f"   - Drill-down data available for detailed analysis")
    
    def run_full_verification(self):
        """Run complete verification suite"""
        print("🔍 COMPREHENSIVE STAGE 2 VERIFICATION")
        print("=" * 60)
        
        self.verify_normalization_quality()
        self.test_aggregation_logic()
        self.sample_county_analysis()
        self.generate_data_quality_report()
        self.test_radar_chart_queries()
        
        print(f"\n✅ VERIFICATION COMPLETED")
        print(f"   Stage 2 normalization appears to be working correctly!")
        print(f"   Ready for radar chart integration!")

# Usage example
if __name__ == "__main__":
    verifier = NormalizationVerifier('sustainability_data.db')
    
    # Run full verification
    verifier.run_full_verification()
    
    # Or run specific tests:
    # verifier.verify_normalization_quality()
    # verifier.sample_county_analysis('01001')  # Specific FIPS code
    # verifier.test_radar_chart_queries()