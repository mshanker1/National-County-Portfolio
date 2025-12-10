import pandas as pd
from google.cloud import bigquery
import numpy as np
from scipy import stats
import os
import time
import warnings
warnings.filterwarnings('ignore', category=UserWarning, message='pandas only supports SQLAlchemy')

class BigQueryRadarChartDataProvider:
    """
    Enhanced data provider for BigQuery with human-readable names and state-level comparison support
    """
    
    def __init__(self, project_id, dataset_id, display_names_file='display_names.csv'):
        """
        Initialize with BigQuery connection parameters
        
        Example:
        project_id = 'county-dashboard'
        dataset_id = 'sustainability_data'
        """
        self.project_id = project_id
        self.dataset_id = dataset_id
        self.display_names_file = display_names_file
        self.display_names_map = {}
        self.comparison_mode = 'national'  # 'national' or 'state'
        self.current_state = None
        self.client = None
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
    
    def get_connection(self):
        """Get BigQuery connection"""
        if self.client is None:
            self.client = bigquery.Client(project=self.project_id)
        return self.client
    
    def _check_database_status(self):
        """Check what stage the database is in"""
        try:
            client = self.get_connection()
            
            # Get all tables
            tables_query = f"""
                SELECT table_name 
                FROM `{self.project_id}.{self.dataset_id}.INFORMATION_SCHEMA.TABLES`
            """
            tables_df = client.query(tables_query).to_dataframe()
            tables = tables_df['table_name'].tolist()
            
            # Check for state comparison tables
            has_state_tables = 'state_percentiles' in tables and 'state_aggregated_scores' in tables
            
            if 'aggregated_scores' in tables and 'normalized_metrics' in tables:
                if has_state_tables:
                    self.stage = 3  # Fast state comparisons available
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
        client = self.get_connection()
        
        counties_query = f"""
            SELECT 
                c.fips as fips_code,
                c.county as county_name,
                c.state as state_code,
                c.state as state_name,
                COUNT(a.measure_name) as data_completeness
            FROM `{self.project_id}.{self.dataset_id}.counties` c
            LEFT JOIN `{self.project_id}.{self.dataset_id}.aggregated_scores` a 
                ON c.fips = a.fips 
                AND a.measure_level = 'sub_measure' 
                AND a.normalized_score IS NOT NULL
            GROUP BY c.fips, c.county, c.state
            HAVING data_completeness >= 8
            ORDER BY c.state, c.county
        """
        
        counties_df = client.query(counties_query).to_dataframe()
        
        return counties_df
    
    def get_county_metrics(self, county_fips):
        """Get structured metrics for a county"""
        client = self.get_connection()
        
        # Get county information
        county_info_query = f"""
            SELECT 
                county as county_name,
                state as state_code,
                state as state_name
            FROM `{self.project_id}.{self.dataset_id}.counties`
            WHERE fips = '{county_fips}'
        """
        
        county_info = client.query(county_info_query).to_dataframe()
        
        if county_info.empty:
            return pd.DataFrame(), {}
        
        # Use national percentiles (state comparison would require Stage 3)
        # NOTE: Database still uses old names (People/Productivity/Place)
        # We map them to new display names (Society/Economy/Environment)
        submeasures_query = f"""
            SELECT 
                parent_measure as top_level,
                measure_name,
                CASE 
                    WHEN parent_measure = 'People' THEN REPLACE(measure_name, 'People_', '')
                    WHEN parent_measure = 'Productivity' THEN REPLACE(measure_name, 'Productivity_', '')
                    WHEN parent_measure = 'Place' THEN REPLACE(measure_name, 'Place_', '')
                END as sub_measure,
                percentile_rank,
                normalized_score,
                component_count,
                completeness_ratio
            FROM `{self.project_id}.{self.dataset_id}.aggregated_scores`
            WHERE fips = '{county_fips}'
            AND measure_level = 'sub_measure'
            AND normalized_score IS NOT NULL
            AND measure_name NOT LIKE '%Population%'
            ORDER BY parent_measure, measure_name
        """
        
        submeasures_df = client.query(submeasures_query).to_dataframe()
        
        # Structure data in the format expected by radar chart
        # Using NEW names for the dashboard
        structured_data = {
            'Society': {},      # Maps from 'People'
            'Economy': {},      # Maps from 'Productivity'
            'Environment': {}   # Maps from 'Place'
        }
        
        # Map the OLD database names to NEW display names
        top_level_mapping = {
            'People': 'Society',
            'Productivity': 'Economy',
            'Place': 'Environment'
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
        
        return county_info, structured_data
    
    def get_submetric_details(self, county_fips, top_level, sub_category):
        """Get detailed metrics for drill-down"""
        client = self.get_connection()
        
        # Convert display names back to database names
        # NEW display names -> OLD database names
        top_level_mapping = {
            'society': 'People',
            'economy': 'Productivity',
            'environment': 'Place'
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
        
        # Get metrics with national percentiles
        details_query = f"""
            SELECT 
                rm.metric_name,
                nm.raw_value as metric_value,
                nm.percentile_rank,
                ms.is_reverse_metric
            FROM `{self.project_id}.{self.dataset_id}.normalized_metrics` nm
            JOIN `{self.project_id}.{self.dataset_id}.raw_metrics` rm 
                ON nm.fips = rm.fips AND nm.metric_name = rm.metric_name
            LEFT JOIN `{self.project_id}.{self.dataset_id}.metric_statistics` ms 
                ON nm.metric_name = ms.metric_name
            WHERE nm.fips = '{county_fips}' 
            AND UPPER(rm.top_level) = UPPER('{db_top_level}')
            AND UPPER(rm.sub_measure) = UPPER('{db_sub_category}')
            AND nm.is_missing = FALSE
            ORDER BY nm.percentile_rank DESC
        """
        
        details_df = client.query(details_query).to_dataframe()
        
        # Add human-readable display names
        if not details_df.empty:
            display_names = []
            for _, row in details_df.iterrows():
                display_name = self.get_display_name(row['metric_name'])
                if display_name == row['metric_name']:
                    # Use metric name formatted nicely
                    display_name = row['metric_name'].replace('_', ' ').title()
                display_names.append(display_name)
            
            details_df['display_name'] = display_names
        
        return details_df

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

def create_enhanced_radar_chart(county_data, county_name, data_provider, county_fips):
    """Enhanced radar chart aligned PERFECTLY with SVG - MATCHING SQLite V2 STYLING"""
    import plotly.graph_objects as go
    import base64
    
    if not county_data:
        return go.Figure()
    
    # Define categories with SQLite V2 colors
    categories_config = {
        'Society': {'color': '#6B7FD7', 'label': 'Society', 'start_angle': 150, 'end_angle': 270},  # Purple
        'Economy': {'color': '#D4AF37', 'label': 'Economy', 'start_angle': 270, 'end_angle': 390},  # Gold
        'Environment': {'color': '#4ECDC4', 'label': 'Environment', 'start_angle': 30, 'end_angle': 150}  # Teal
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
    
    # Process each category
    all_theta = []
    all_r = []
    all_colors = []
    all_hover = []
    all_customdata = []
    all_labels = []
    
    # Define EXACT order for each category (CLOCKWISE from start of sector)
    sector_orders = {
        'Society': ['Health', 'Arts and Culture', 'Community', 'Education', 'Wealth'],
        'Environment': ['Built Environment', 'Climate and Resilience', 'Land, Air, Water', 'Biodiversity', 'Food and Agriculture Systems'],
        'Economy': ['Employment', 'Nonprofit', 'Business', 'Government', 'Energy']
    }
    
    # Process in order: Society → Economy → Environment for smooth polygon flow
    for category in ['Society', 'Economy', 'Environment']:
        if category in county_data and county_data[category]:
            config = categories_config[category]
            
            # Get the correct order for this category
            correct_order = sector_orders.get(category, [])
            
            # Match data to correct order
            ordered_sub_categories = []
            ordered_values = []
            
            for correct_name in correct_order:
                # Try to find matching data
                found = False
                for sub_cat, value in county_data[category].items():
                    # Flexible matching (handles variations in naming)
                    sub_cat_clean = sub_cat.lower().replace(' ', '').replace(',', '').replace('&', 'and')
                    correct_name_clean = correct_name.lower().replace(' ', '').replace(',', '').replace('&', 'and')
                    
                    if (correct_name_clean in sub_cat_clean or 
                        sub_cat_clean in correct_name_clean or
                        correct_name_clean == sub_cat_clean):
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
                
                # Add to overall data with enhanced hover info
                for i, (sub_cat, value, angle) in enumerate(zip(sub_categories, values, angles)):
                    hover_detail = ""
                    try:
                        sample_details = data_provider.get_submetric_details(county_fips, category, sub_cat)
                        if not sample_details.empty:
                            top_metrics = sample_details.head(2)
                            metrics_list = []
                            for _, row in top_metrics.iterrows():
                                display_name = row.get('display_name', row['metric_name'])
                                metric_text = f"• {display_name}: {row['metric_value']:.1f} ({row['percentile_rank']:.0f}%)"
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
    
    # Debug: Print what we're plotting
    print(f"\n🔍 Plotting {len(all_r)} data points:")
    print(f"   R values (first 5): {all_r[:5]}")
    print(f"   Theta values (first 5): {all_theta[:5]}")
    print(f"   Labels (first 5): {all_labels[:5]}")
    
    # Create the main radar trace
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
        text=[f"{val:.0f}%" for val in all_r],
        textposition='top center',
        textfont=dict(
            size=8,
            color='#1F2937',
            family='Arial, sans-serif'
        ),
        mode='markers+lines+text',
        hovertext=all_hover,
        hovertemplate='%{hovertext}<extra></extra>',
        customdata=all_customdata
    ))
    
    # Update layout with SQLite V2 styling
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
        width=700,
        margin=dict(t=120, b=100, l=100, r=100),
        paper_bgcolor='rgba(255,255,255,0)' if svg_loaded else 'white',
        plot_bgcolor='rgba(255,255,255,0)' if svg_loaded else 'white'
    )
    
    return fig

def create_detail_chart(details_df, title, comparison_mode='national'):
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
                      'Value: %{customdata[0]:.1f}<br>' +
                      'Percentile: %{x:.0f}%<br>' +
                      '<extra></extra>',
        customdata=list(zip(details_df['metric_value']))
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

if __name__ == "__main__":
    print("🚀 ENHANCED RADAR CHART INTEGRATION - BIGQUERY V2 STYLED")
    print("=" * 70)
    
    # Configure BigQuery connection
    project_id = 'county-dashboard'  # UPDATE THIS with your Google Cloud project ID
    dataset_id = 'sustainability_data'
    
    # Test the enhanced integration
    provider = BigQueryRadarChartDataProvider(project_id, dataset_id)
    
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
            
            # Test drill-down
            if structured_data.get('Society'):
                first_submeasure = list(structured_data['Society'].keys())[0]
                print(f"\n🔍 Testing drill-down for '{first_submeasure}':")
                
                details = provider.get_submetric_details(sample_fips, 'Society', first_submeasure)
                if not details.empty:
                    print(f"   Found {len(details)} metrics")
                    for _, row in details.head(3).iterrows():
                        display_name = row.get('display_name', row['metric_name'])
                        print(f"   • {display_name}: {row['metric_value']:.1f} ({row['percentile_rank']:.0f}%)")
    
    print(f"\n✨ Key Features:")
    print(f"   • Connected to BigQuery database")
    print(f"   • NEW LABELS: Society, Economy, Environment")
    print(f"   • SQLite V2 visual styling (colors, radial axis)")
    print(f"   • Human-readable display names from CSV")
    print(f"   • National comparisons ready")
    print(f"   • Enhanced hover text with context")
    print(f"   • SVG background support")
    
    print(f"\n🎯 Ready for integration!")
    print("=" * 70)
