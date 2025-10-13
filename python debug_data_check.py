"""
Debug script to check Stage 2 data availability
"""
import sqlite3
import pandas as pd

def check_stage2_data(county_fips='39133'):
    """Check what data exists for a specific county"""
    
    conn = sqlite3.connect('sustainability_data.db')
    
    print("=" * 70)
    print(f"DEBUGGING DATA FOR COUNTY: {county_fips}")
    print("=" * 70)
    
    # Check county info
    print("\n1. COUNTY INFO:")
    county_info = pd.read_sql("""
        SELECT fips, county, state
        FROM counties
        WHERE fips = ?
    """, conn, params=[county_fips])
    print(county_info)
    
    # Check if raw_metrics exists for this county
    print("\n2. RAW METRICS (Top-level summary):")
    raw_summary = pd.read_sql("""
        SELECT 
            top_level,
            COUNT(DISTINCT sub_measure) as sub_measure_count,
            COUNT(DISTINCT metric_name) as metric_count,
            COUNT(*) as total_records
        FROM raw_metrics
        WHERE fips = ?
        GROUP BY top_level
    """, conn, params=[county_fips])
    print(raw_summary)
    
    # Check sub-measures in raw_metrics
    print("\n3. RAW METRICS (Sub-measures detail):")
    raw_detail = pd.read_sql("""
        SELECT 
            top_level,
            sub_measure,
            COUNT(DISTINCT metric_name) as metric_count
        FROM raw_metrics
        WHERE fips = ?
        GROUP BY top_level, sub_measure
        ORDER BY top_level, sub_measure
    """, conn, params=[county_fips])
    print(raw_detail)
    
    # Check normalized_metrics
    print("\n4. NORMALIZED METRICS:")
    norm_check = pd.read_sql("""
        SELECT COUNT(*) as count
        FROM normalized_metrics
        WHERE fips = ?
    """, conn, params=[county_fips])
    print(f"Total normalized metrics: {norm_check.iloc[0]['count']}")
    
    # Check aggregated_scores
    print("\n5. AGGREGATED SCORES (by measure_level):")
    agg_summary = pd.read_sql("""
        SELECT 
            measure_level,
            COUNT(*) as count,
            COUNT(CASE WHEN percentile_rank IS NOT NULL THEN 1 END) as with_percentile
        FROM aggregated_scores
        WHERE fips = ?
        GROUP BY measure_level
    """, conn, params=[county_fips])
    print(agg_summary)
    
    # Check specific sub-measures in aggregated_scores
    print("\n6. SUB-MEASURES IN AGGREGATED_SCORES:")
    submeasures = pd.read_sql("""
        SELECT 
            measure_name,
            parent_measure,
            raw_score,
            percentile_rank,
            component_count,
            completeness_ratio
        FROM aggregated_scores
        WHERE fips = ?
        AND measure_level = 'sub_measure'
        ORDER BY parent_measure, measure_name
    """, conn, params=[county_fips])
    
    if submeasures.empty:
        print("❌ NO SUB-MEASURES FOUND! This is the problem.")
        
        # Check if we have top-level measures instead
        print("\n7. TOP-LEVEL MEASURES (checking if these exist instead):")
        top_level = pd.read_sql("""
            SELECT 
                measure_name,
                measure_level,
                percentile_rank
            FROM aggregated_scores
            WHERE fips = ?
            AND measure_level = 'top_level'
        """, conn, params=[county_fips])
        print(top_level)
        
        # Check raw structure to see what we have
        print("\n8. CHECKING RAW METRICS STRUCTURE:")
        structure_check = pd.read_sql("""
            SELECT DISTINCT
                top_level,
                sub_measure
            FROM raw_metrics
            WHERE fips = ?
            ORDER BY top_level, sub_measure
        """, conn, params=[county_fips])
        print(structure_check)
        
    else:
        print(submeasures)
        
        # Group by parent measure
        print("\n7. SUB-MEASURES GROUPED BY PARENT:")
        for parent in submeasures['parent_measure'].unique():
            parent_data = submeasures[submeasures['parent_measure'] == parent]
            print(f"\n{parent}:")
            for _, row in parent_data.iterrows():
                print(f"  • {row['measure_name']}: {row['percentile_rank']:.1f}%")
    
    # Check if Stage 2 was actually run
    print("\n9. CHECKING IF STAGE 2 COMPLETED:")
    
    # Check metric_statistics table
    stats_check = pd.read_sql("""
        SELECT COUNT(*) as count
        FROM metric_statistics
    """, conn)
    print(f"Metric statistics records: {stats_check.iloc[0]['count']}")
    
    # Check if aggregation was successful
    agg_total = pd.read_sql("""
        SELECT COUNT(*) as total
        FROM aggregated_scores
    """, conn)
    print(f"Total aggregated scores: {agg_total.iloc[0]['total']}")
    
    # Sample some data
    print("\n10. SAMPLE AGGREGATED DATA:")
    sample = pd.read_sql("""
        SELECT 
            c.county,
            c.state,
            a.measure_name,
            a.measure_level,
            a.percentile_rank
        FROM aggregated_scores a
        JOIN counties c ON a.fips = c.fips
        WHERE a.measure_level = 'sub_measure'
        AND a.percentile_rank IS NOT NULL
        LIMIT 10
    """, conn)
    
    if sample.empty:
        print("❌ NO SUB-MEASURE DATA EXISTS IN DATABASE")
        print("\n⚠️  DIAGNOSIS: Stage 2 normalization may not have completed successfully")
        print("   or the aggregation step failed.")
        print("\n💡 SOLUTION: Re-run stage2_normalization.py")
    else:
        print(sample)
    
    conn.close()
    
    print("\n" + "=" * 70)
    print("DIAGNOSIS COMPLETE")
    print("=" * 70)

if __name__ == "__main__":
    # Check the default county
    check_stage2_data('39133')  # Portage County, OH
    
    # Optionally check another county
    # check_stage2_data('06037')  # Los Angeles County, CA