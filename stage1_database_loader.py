import pandas as pd
from google.cloud import bigquery
import numpy as np
import re
import os

class BigQueryDataLoader:
    """
    Stage 1: Load CSV data directly into BigQuery with proper hierarchical structure
    This replaces the Snowflake version and loads data directly to BigQuery
    """
    
    def __init__(self, csv_file_path, project_id, dataset_id):
        self.csv_file_path = csv_file_path
        self.project_id = project_id
        self.dataset_id = dataset_id
        self.client = None
        
    def connect(self):
        """Establish connection to BigQuery"""
        try:
            self.client = bigquery.Client(project=self.project_id)
            print(f"✅ Connected to BigQuery: {self.project_id}.{self.dataset_id}")
            return True
        except Exception as e:
            print(f"❌ Failed to connect to BigQuery: {str(e)}")
            return False
    
    def create_database_schema(self):
        """Create the dataset and tables in BigQuery"""
        print("📋 Creating database schema in BigQuery...")
        
        # Create dataset if it doesn't exist
        dataset_id = f"{self.project_id}.{self.dataset_id}"
        dataset = bigquery.Dataset(dataset_id)
        dataset.location = "US"  # Choose your location
        
        try:
            self.client.create_dataset(dataset, exists_ok=True)
            print(f"   ✅ Dataset {self.dataset_id} created/verified")
        except Exception as e:
            print(f"   ℹ️  Dataset already exists or error: {e}")
        
        # Drop existing tables if they exist (for fresh start)
        tables_to_drop = ['raw_metrics', 'counties', 'raw_metrics_wide']
        for table_name in tables_to_drop:
            table_id = f"{self.project_id}.{self.dataset_id}.{table_name}"
            try:
                self.client.delete_table(table_id, not_found_ok=True)
                print(f"   🗑️  Dropped existing table: {table_name}")
            except:
                pass
        
        # Create counties table
        counties_schema = [
            bigquery.SchemaField("fips", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("state", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("county", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("state_code", "STRING"),
        ]
        
        counties_table_id = f"{self.project_id}.{self.dataset_id}.counties"
        counties_table = bigquery.Table(counties_table_id, schema=counties_schema)
        self.client.create_table(counties_table)
        print("   ✅ Created counties table")
        
        # Create raw_metrics table
        metrics_schema = [
            bigquery.SchemaField("fips", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("metric_name", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("raw_value", "FLOAT"),
            bigquery.SchemaField("raw_value_text", "STRING"),
            bigquery.SchemaField("unit", "STRING"),
            bigquery.SchemaField("year", "STRING"),
            bigquery.SchemaField("top_level", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("sub_measure", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("metric_group", "STRING"),
            bigquery.SchemaField("sub_metric_name", "STRING"),
            bigquery.SchemaField("is_missing", "BOOLEAN"),
            bigquery.SchemaField("column_index", "INTEGER"),
        ]
        
        metrics_table_id = f"{self.project_id}.{self.dataset_id}.raw_metrics"
        metrics_table = bigquery.Table(metrics_table_id, schema=metrics_schema)
        self.client.create_table(metrics_table)
        print("   ✅ Created raw_metrics table")
        
        print("✅ Database schema created successfully in BigQuery")
        
    def load_csv_data(self):
        """Load and parse the CSV file with multi-row headers"""
        print("📊 Loading CSV data from local file...")
        
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
        Handles: PEOPLE_HEALTH_LENGTHOFLIFE_LIFEEXPECTANCY
        Returns: dict with hierarchy information
        """
        parts = column_name.split('_')
        
        if len(parts) < 2:
            return None
            
        hierarchy = {
            'original_name': column_name,
            'top_level': parts[0].capitalize(),  # PEOPLE -> People
            'sub_measure': parts[1].capitalize(),  # HEALTH -> Health
            'metric_group': None,
            'sub_metric_name': None,
            'full_metric_path': column_name
        }
        
        if len(parts) == 2:
            # Direct sub-measure metric: People_Health
            hierarchy['metric_group'] = parts[1].capitalize()
            hierarchy['sub_metric_name'] = parts[1].capitalize()
        elif len(parts) >= 3:
            # Nested metric: People_Health_LengthOfLife_LifeExpectancy
            hierarchy['metric_group'] = parts[2]  # LengthOfLife
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
        clean_str = str(value_str).strip().upper()
        
        if clean_str == '' or clean_str in ['NA', 'NULL', 'NAN', 'N/A', 'NONE']:
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
        """Load county information into BigQuery counties table"""
        print("🏛️  Loading counties data into BigQuery...")
        
        counties_data = []
        
        for idx, row in data_rows.iterrows():
            fips_raw = str(row.iloc[0]).strip()
            state = str(row.iloc[1]).strip()
            county = str(row.iloc[2]).strip()
            
            # Skip rows with missing essential data
            if fips_raw and fips_raw.upper() not in ['NAN', 'NULL', '']:
                # Pad FIPS to 5 digits
                fips = fips_raw.zfill(5)
                state_code = fips[:2]
                counties_data.append({
                    'fips': fips,
                    'state': state,
                    'county': county,
                    'state_code': state_code
                })
        
        # Load to BigQuery
        if counties_data:
            counties_df = pd.DataFrame(counties_data)
            table_id = f"{self.project_id}.{self.dataset_id}.counties"
            
            job_config = bigquery.LoadJobConfig(
                write_disposition="WRITE_APPEND",
            )
            
            job = self.client.load_table_from_dataframe(
                counties_df, table_id, job_config=job_config
            )
            job.result()  # Wait for the job to complete
            
            print(f"   ✅ Loaded {len(counties_data)} counties into BigQuery")
        
        return len(counties_data)
    
    def load_metrics_data(self, column_names, units, years, data_rows):
        """Load all metrics data with hierarchical parsing INTO BigQuery"""
        print("📈 Loading metrics data into BigQuery...")
        
        # Skip the first 3 columns (FIPS, State, County)
        metric_columns = column_names[3:]
        metric_units = units[3:]
        metric_years = years[3:]
        
        metrics_data = []
        skipped_columns = 0
        total_values = 0
        missing_values = 0
        
        print("   Processing metrics...")
        
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
                fips_raw = str(row.iloc[0]).strip()
                
                # Skip rows with invalid FIPS
                if not fips_raw or fips_raw.upper() in ['NAN', 'NULL', '']:
                    continue
                
                # Pad FIPS to 5 digits
                fips = fips_raw.zfill(5)
                    
                # Get raw value
                raw_value_text = str(row.iloc[col_idx + 3]) if col_idx + 3 < len(row) else ''
                numeric_value, is_missing = self.clean_numeric_value(raw_value_text)
                
                total_values += 1
                if is_missing:
                    missing_values += 1
                
                metrics_data.append({
                    'fips': fips,
                    'metric_name': hierarchy['original_name'],
                    'raw_value': numeric_value,
                    'raw_value_text': raw_value_text[:100] if raw_value_text else None,
                    'unit': unit[:50] if unit else None,
                    'year': year[:20] if year else None,
                    'top_level': hierarchy['top_level'],
                    'sub_measure': hierarchy['sub_measure'],
                    'metric_group': hierarchy['metric_group'],
                    'sub_metric_name': hierarchy['sub_metric_name'],
                    'is_missing': is_missing,
                    'column_index': col_idx + 3
                })
            
            # Print progress every 10 columns
            if (col_idx + 1) % 10 == 0:
                print(f"      Processed {col_idx + 1}/{len(metric_columns)} metrics...")
        
        print(f"   Loading {len(metrics_data):,} rows into BigQuery...")
        
        # Convert to DataFrame and load to BigQuery in batches
        metrics_df = pd.DataFrame(metrics_data)
        table_id = f"{self.project_id}.{self.dataset_id}.raw_metrics"
        
        job_config = bigquery.LoadJobConfig(
            write_disposition="WRITE_APPEND",
        )
        
        # Load in chunks for better performance
        chunk_size = 10000
        total_loaded = 0
        
        for i in range(0, len(metrics_df), chunk_size):
            chunk = metrics_df.iloc[i:i + chunk_size]
            job = self.client.load_table_from_dataframe(
                chunk, table_id, job_config=job_config
            )
            job.result()  # Wait for completion
            total_loaded += len(chunk)
            print(f"      Loaded {total_loaded:,} / {len(metrics_df):,} rows...")
        
        print(f"   ✅ Loaded {len(metrics_data):,} metric values into BigQuery")
        print(f"   ⚠️  Skipped {skipped_columns} invalid columns")
        print(f"   📊 Data quality: {missing_values}/{total_values} missing ({missing_values/total_values*100:.1f}%)")
        
        return len(metrics_data)
    
    def generate_data_summary(self):
        """Generate summary statistics about the loaded data FROM BigQuery"""
        print("\n📋 DATA SUMMARY:")
        print("=" * 50)
        
        # County count
        query = f"""
            SELECT COUNT(*) as count 
            FROM `{self.project_id}.{self.dataset_id}.counties`
        """
        county_count = self.client.query(query).to_dataframe().iloc[0]['count']
        print(f"Counties: {county_count}")
        
        # Top-level measures
        query = f"""
            SELECT 
                top_level, 
                COUNT(DISTINCT sub_measure) as sub_measures,
                COUNT(DISTINCT metric_name) as metrics
            FROM `{self.project_id}.{self.dataset_id}.raw_metrics`
            GROUP BY top_level 
            ORDER BY top_level
        """
        
        print("\nHierarchical Structure:")
        results = self.client.query(query).to_dataframe()
        for _, row in results.iterrows():
            print(f"  {row['top_level']}: {row['sub_measures']} sub-measures, {row['metrics']} metrics")
        
        # Sub-measure breakdown
        query = f"""
            SELECT 
                top_level, 
                sub_measure, 
                COUNT(DISTINCT metric_name) as metrics
            FROM `{self.project_id}.{self.dataset_id}.raw_metrics`
            GROUP BY top_level, sub_measure 
            ORDER BY top_level, sub_measure
        """
        
        print("\nDetailed Sub-measures:")
        results = self.client.query(query).to_dataframe()
        current_top = None
        for _, row in results.iterrows():
            if current_top != row['top_level']:
                print(f"\n  {row['top_level']}:")
                current_top = row['top_level']
            print(f"    {row['sub_measure']}: {row['metrics']} metrics")
        
        # Data quality
        query = f"""
            SELECT 
                COUNT(*) as total_values,
                COUNTIF(is_missing = TRUE) as missing_values,
                COUNT(DISTINCT fips) as counties_with_data
            FROM `{self.project_id}.{self.dataset_id}.raw_metrics`
        """
        
        result = self.client.query(query).to_dataframe().iloc[0]
        total = result['total_values']
        missing = result['missing_values']
        counties_with_data = result['counties_with_data']
        
        print(f"\nData Quality:")
        print(f"  Total values: {total:,}")
        print(f"  Missing values: {missing:,} ({missing/total*100:.1f}%)")
        print(f"  Counties with data: {counties_with_data}")
        
        # Sample data
        query = f"""
            SELECT c.state, c.county, rm.metric_name, rm.raw_value, rm.unit
            FROM `{self.project_id}.{self.dataset_id}.raw_metrics` rm
            JOIN `{self.project_id}.{self.dataset_id}.counties` c 
            ON rm.fips = c.fips
            WHERE rm.raw_value IS NOT NULL
            LIMIT 5
        """
        
        print(f"\nSample Data:")
        results = self.client.query(query).to_dataframe()
        for _, row in results.iterrows():
            print(f"  {row['county']}, {row['state']}: {row['metric_name']} = {row['raw_value']} {row['unit']}")
    
    def run_stage1(self):
        """Execute complete Stage 1 pipeline - Load CSV to BigQuery"""
        print("🚀 STARTING STAGE 1: Data Loading to BigQuery")
        print("=" * 70)
        
        try:
            # Step 1: Connect to BigQuery
            if not self.connect():
                raise Exception("Failed to connect to BigQuery")
            
            # Step 2: Create database schema
            self.create_database_schema()
            
            # Step 3: Load and parse CSV from local file
            column_names, units, years, data_rows = self.load_csv_data()
            
            # Step 4: Load counties into BigQuery
            counties_loaded = self.load_counties_data(data_rows)
            
            # Step 5: Load metrics with hierarchy into BigQuery
            metrics_loaded = self.load_metrics_data(column_names, units, years, data_rows)
            
            # Step 6: Generate summary from BigQuery data
            self.generate_data_summary()
            
            print(f"\n✅ STAGE 1 COMPLETED SUCCESSFULLY!")
            print(f"   All data stored in BigQuery")
            print(f"   Project: {self.project_id}")
            print(f"   Dataset: {self.dataset_id}")
            print(f"   Counties: {counties_loaded}")
            print(f"   Metric values: {metrics_loaded:,}")
            
        except Exception as e:
            print(f"❌ ERROR in Stage 1: {str(e)}")
            import traceback
            traceback.print_exc()
            raise

# Usage example
if __name__ == "__main__":
    # BigQuery configuration
    project_id = 'county-dashboard'  # UPDATE THIS with your Google Cloud project ID
    dataset_id = 'sustainability_data'  # Name for your dataset in BigQuery
    
    # Path to your local CSV file
    csv_file_path = './National_County_Dashboard.csv'  # Update this path
    
    # Initialize the loader
    loader = BigQueryDataLoader(
        csv_file_path=csv_file_path,
        project_id=project_id,
        dataset_id=dataset_id
    )
    
    # Run Stage 1 - This will load CSV directly to BigQuery
    loader.run_stage1()
    
    print("\n🎯 Next Steps:")
    print(f"   - View data in BigQuery Console: https://console.cloud.google.com/bigquery")
    print(f"   - Query: SELECT * FROM `{project_id}.{dataset_id}.raw_metrics` LIMIT 10")
    print(f"   - Query: SELECT * FROM `{project_id}.{dataset_id}.counties` LIMIT 10")
    print("   - Run Stage 2: python stage2_normalization.py")