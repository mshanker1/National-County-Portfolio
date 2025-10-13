import pandas as pd
import sqlite3
import numpy as np
import re
from pathlib import Path

class SustainabilityDataLoader:
    """
    Stage 1: Load CSV data into SQLite database with proper hierarchical structure
    """
#Csv data loader and database creator- to change the csv file path to the new file path
    def __init__(self, csv_file_path, db_file_path='sustainability_data.db'):
        self.csv_file_path = csv_file_path
        self.db_file_path = db_file_path
        self.conn = None
        
    def create_database_schema(self):
        """Create the database schema with all required tables"""
        self.conn = sqlite3.connect(self.db_file_path)
        cursor = self.conn.cursor()
        
        # Drop existing tables if they exist (for fresh start)
        cursor.execute('DROP TABLE IF EXISTS raw_metrics')
        cursor.execute('DROP TABLE IF EXISTS counties')
        
        # Create counties table
        cursor.execute('''
            CREATE TABLE counties (
                fips TEXT PRIMARY KEY,
                state TEXT NOT NULL,
                county TEXT NOT NULL,
                UNIQUE(fips)
            )
        ''')
        
        # Create raw_metrics table to store all original data with metadata
        cursor.execute('''
            CREATE TABLE raw_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fips TEXT NOT NULL,
                metric_name TEXT NOT NULL,
                raw_value REAL,
                raw_value_text TEXT,  -- Store original text format
                unit TEXT,
                year TEXT,
                top_level TEXT NOT NULL,
                sub_measure TEXT NOT NULL,
                metric_group TEXT,
                sub_metric_name TEXT,
                is_missing INTEGER DEFAULT 0,
                column_index INTEGER,
                FOREIGN KEY (fips) REFERENCES counties(fips),
                UNIQUE(fips, metric_name)
            )
        ''')
        
        # Create indexes for better query performance
        cursor.execute('CREATE INDEX idx_raw_metrics_fips ON raw_metrics(fips)')
        cursor.execute('CREATE INDEX idx_raw_metrics_hierarchy ON raw_metrics(top_level, sub_measure)')
        cursor.execute('CREATE INDEX idx_raw_metrics_metric ON raw_metrics(metric_name)')
        
        self.conn.commit()
        print("✅ Database schema created successfully")
        
    def load_csv_data(self):
        """Load and parse the CSV file with multi-row headers"""
        print("📊 Loading CSV data...")
    # here again change the csv file path to the new file path
        # Read CSV without treating first row as header
        df = pd.read_csv(self.csv_file_path, header=None, dtype=str)
        
        print(f"   Raw data shape: {df.shape}")
        
        # Extract the three header rows
        column_names = df.iloc[0].values
        units = df.iloc[1].values
        years = df.iloc[2].values
        
        # Extract actual data (skip first 3 header rows)
        data_rows = df.iloc[3:].reset_index(drop=True)
        
        print(f"   Data rows: {len(data_rows)}")
        print(f"   Columns: {len(column_names)}")
        
        return column_names, units, years, data_rows
    
    def parse_metric_hierarchy(self, column_name):
        """
        Parse hierarchical column names into components
        Returns: dict with hierarchy information
        """
        parts = column_name.split('_')
        
        if len(parts) < 2:
            return None
            
        hierarchy = {
            'original_name': column_name,
            'top_level': parts[0],
            'sub_measure': parts[1],
            'metric_group': None,
            'sub_metric_name': None,
            'full_metric_path': column_name
        }
        
        if len(parts) == 2:
            # Direct sub-measure metric: People_Health
            hierarchy['metric_group'] = parts[1]
            hierarchy['sub_metric_name'] = parts[1]
        elif len(parts) >= 3:
            # Nested metric: People_Health_LengthOfLife_LifeExpectancy
            hierarchy['metric_group'] = parts[2]
            if len(parts) > 3:
                hierarchy['sub_metric_name'] = '_'.join(parts[3:])
            else:
                hierarchy['sub_metric_name'] = parts[2]
                
        return hierarchy
    
    def clean_numeric_value(self, value_str):
        """
        Clean numeric values by removing formatting characters
        Returns: (cleaned_numeric_value, is_missing_flag)
        """
        if pd.isna(value_str) or value_str == '' or value_str is None:
            return None, True
            
        # Convert to string and strip whitespace
        clean_str = str(value_str).strip()
        
        if clean_str == '' or clean_str.upper() in ['NA', 'NULL', 'NAN', 'N/A']:
            return None, True
            
        # Remove common formatting characters
        clean_str = re.sub(r'[$,\s%]', '', clean_str)
        
        # Handle parentheses (negative numbers)
        if clean_str.startswith('(') and clean_str.endswith(')'):
            clean_str = '-' + clean_str[1:-1]
            
        try:
            numeric_value = float(clean_str)
            return numeric_value, False
        except (ValueError, TypeError):
            # If can't convert to float, it's likely a text value or corrupted
            return None, True
    
    def load_counties_data(self, data_rows):
        """Load county information into counties table"""
        print("🏛️  Loading counties data...")
        
        counties_data = []
        for idx, row in data_rows.iterrows():
            fips = str(row.iloc[0]).strip()
            state = str(row.iloc[1]).strip()
            county = str(row.iloc[2]).strip()
            
            # Skip rows with missing essential data
            if fips and fips != 'nan' and state and state != 'nan':
                counties_data.append((fips, state, county))
        
        # Insert into database
        cursor = self.conn.cursor()
        cursor.executemany('''
            INSERT OR REPLACE INTO counties (fips, state, county) 
            VALUES (?, ?, ?)
        ''', counties_data)
        
        self.conn.commit()
        print(f"   ✅ Loaded {len(counties_data)} counties")
        
        return len(counties_data)
    
    def load_metrics_data(self, column_names, units, years, data_rows):
        """Load all metrics data with hierarchical parsing"""
        print("📈 Loading metrics data...")
        
        # Skip the first 3 columns (FIPS, State, County)
        metric_columns = column_names[3:]
        metric_units = units[3:]
        metric_years = years[3:]
        
        metrics_data = []
        skipped_columns = 0
        total_values = 0
        missing_values = 0
        
        for col_idx, column_name in enumerate(metric_columns):
            # Parse hierarchy
            hierarchy = self.parse_metric_hierarchy(column_name)
            
            if hierarchy is None:
                skipped_columns += 1
                continue
                
            # Get metadata
            unit = str(metric_units[col_idx]).strip() if col_idx < len(metric_units) else ''
            year = str(metric_years[col_idx]).strip() if col_idx < len(metric_years) else ''
            
            # Process each county's value for this metric
            for row_idx, row in data_rows.iterrows():
                fips = str(row.iloc[0]).strip()
                
                # Skip rows with invalid FIPS
                if not fips or fips == 'nan':
                    continue
                    
                # Get raw value
                raw_value_text = str(row.iloc[col_idx + 3]) if col_idx + 3 < len(row) else ''
                numeric_value, is_missing = self.clean_numeric_value(raw_value_text)
                
                total_values += 1
                if is_missing:
                    missing_values += 1
                
                metrics_data.append((
                    fips,
                    hierarchy['original_name'],
                    numeric_value,
                    raw_value_text,
                    unit,
                    year,
                    hierarchy['top_level'],
                    hierarchy['sub_measure'],
                    hierarchy['metric_group'],
                    hierarchy['sub_metric_name'],
                    1 if is_missing else 0,
                    col_idx + 3
                ))
        
        # Batch insert into database
        cursor = self.conn.cursor()
        cursor.executemany('''
            INSERT OR REPLACE INTO raw_metrics 
            (fips, metric_name, raw_value, raw_value_text, unit, year, 
             top_level, sub_measure, metric_group, sub_metric_name, 
             is_missing, column_index)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', metrics_data)
        
        self.conn.commit()
        
        print(f"   ✅ Loaded {len(metrics_data)} metric values")
        print(f"   ⚠️  Skipped {skipped_columns} invalid columns")
        print(f"   📊 Data quality: {missing_values}/{total_values} missing ({missing_values/total_values*100:.1f}%)")
        
        return len(metrics_data)
    
    def generate_data_summary(self):
        """Generate summary statistics about the loaded data"""
        print("\n📋 DATA SUMMARY:")
        print("=" * 50)
        
        cursor = self.conn.cursor()
        
        # County count
        cursor.execute("SELECT COUNT(*) FROM counties")
        county_count = cursor.fetchone()[0]
        print(f"Counties: {county_count}")
        
#here we need to check if the top level and sub level are correct
        # Top-level measures
        cursor.execute("""
            SELECT top_level, COUNT(DISTINCT sub_measure) as sub_measures,
                   COUNT(DISTINCT metric_name) as metrics
            FROM raw_metrics 
            GROUP BY top_level 
            ORDER BY top_level
        """)
        
        print("\nHierarchical Structure:")
        for top_level, sub_count, metric_count in cursor.fetchall():
            print(f"  {top_level}: {sub_count} sub-measures, {metric_count} metrics")
        
        # Sub-measure breakdown
        cursor.execute("""
            SELECT top_level, sub_measure, COUNT(DISTINCT metric_name) as metrics
            FROM raw_metrics 
            GROUP BY top_level, sub_measure 
            ORDER BY top_level, sub_measure
        """)
        
        print("\nDetailed Sub-measures:")
        current_top = None
        for top_level, sub_measure, metric_count in cursor.fetchall():
            if current_top != top_level:
                print(f"\n  {top_level}:")
                current_top = top_level
            print(f"    {sub_measure}: {metric_count} metrics")
        
        # Data quality
        cursor.execute("""
            SELECT 
                COUNT(*) as total_values,
                SUM(is_missing) as missing_values,
                COUNT(DISTINCT fips) as counties_with_data
            FROM raw_metrics
        """)
        
        total, missing, counties_with_data = cursor.fetchone()
        print(f"\nData Quality:")
        print(f"  Total values: {total:,}")
        print(f"  Missing values: {missing:,} ({missing/total*100:.1f}%)")
        print(f"  Counties with data: {counties_with_data}")
        
        # Sample data
        cursor.execute("""
            SELECT c.state, c.county, rm.metric_name, rm.raw_value, rm.unit
            FROM raw_metrics rm
            JOIN counties c ON rm.fips = c.fips
            WHERE rm.raw_value IS NOT NULL
            LIMIT 5
        """)
        
        print(f"\nSample Data:")
        for state, county, metric, value, unit in cursor.fetchall():
            print(f"  {county}, {state}: {metric} = {value} {unit}")
    
    def run_stage1(self):
        """Execute complete Stage 1 pipeline"""
        print("🚀 STARTING STAGE 1: Database Creation and Data Loading")
        print("=" * 60)
        
        try:
            # Step 1: Create database schema
            self.create_database_schema()
            
            # Step 2: Load and parse CSV
            column_names, units, years, data_rows = self.load_csv_data()
            
            # Step 3: Load counties
            counties_loaded = self.load_counties_data(data_rows)
            
            # Step 4: Load metrics with hierarchy
            metrics_loaded = self.load_metrics_data(column_names, units, years, data_rows)
            
            # Step 5: Generate summary
            self.generate_data_summary()
            
            print(f"\n✅ STAGE 1 COMPLETED SUCCESSFULLY!")
            print(f"   Database: {self.db_file_path}")
            print(f"   Counties: {counties_loaded}")
            print(f"   Metric values: {metrics_loaded}")
            
        except Exception as e:
            print(f"❌ ERROR in Stage 1: {str(e)}")
            raise
        finally:
            if self.conn:
                self.conn.close()

# Usage example
if __name__ == "__main__":
    # Initialize the loader
    loader = SustainabilityDataLoader(
        csv_file_path='./National_County_Dashboard.csv',
        db_file_path='sustainability_data.db'
    )
    
    # Run Stage 1
    loader.run_stage1()
    
    print("\n🎯 Next Steps:")
    print("   - Verify data quality in the database")
    print("   - Proceed to Stage 2: Normalization pipeline")
    print("   - Test queries for the radar chart integration")