import pandas as pd
import snowflake.connector
import numpy as np
from scipy import stats
import os
import time
import warnings
warnings.filterwarnings('ignore', category=UserWarning, message='pandas only supports SQLAlchemy')

class SnowflakeRadarChartDataProvider:
    """
    Enhanced data provider for Snowflake with human-readable names and state-level comparison support
    """
    
    def __init__(self, connection_params, display_names_file='display_names.csv'):
        """
        Initialize with Snowflake connection parameters
        
        connection_params example:
        {
            'user': 'mabel10',
            'password': 'Abvin!123456789',
            'account': 'wthggzd-ah61676',
            'warehouse': 'COMPUTE_WH',
            'database': 'SUSTAINABILITY_DB',
            'schema': 'PUBLIC'
        }
        """
        self.connection_params = connection_params
        self.display_names_file = display_names_file
        self.display_names_map = {}
        self.comparison_mode = 'national'  # 'national' or 'state'
        self.current_state = None
        self.conn = None
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
        """Get Snowflake connection"""
        if self.conn is None or self.conn.is_closed():
            self.conn = snowflake.connector.connect(**self.connection_params)
        return self.conn
    
    def _check_database_status(self):
        """Check what stage the database is in"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Get all tables
            cursor.execute("""
                SELECT TABLE_NAME 
                FROM INFORMATION_SCHEMA.TABLES 
                WHERE TABLE_SCHEMA = %s
            """, [self.connection_params['schema']])
            
            tables = [row[0] for row in cursor.fetchall()]
            
            # Check for state comparison tables
            has_state_tables = 'STATE_PERCENTILES' in tables and 'STATE_AGGREGATED_SCORES' in tables
            
            if 'AGGREGATED_SCORES' in tables and 'NORMALIZED_METRICS' in tables:
                if has_state_tables:
                    self.stage = 3  # Fast state comparisons available
                    print("✅ Database Status: Stage 3 Complete (Fast state comparisons available)")
                else:
                    self.stage = 2
                    print("✅ Database Status: Stage 2 Complete (Normalized data available)")
                    print("💡 Run create_state_percentiles_table() for instant state comparisons")
            elif 'RAW_METRICS' in tables and 'COUNTIES' in tables:
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
        conn = self.get_connection()
        
        counties_df = pd.read_sql("""
            SELECT 
                c.FIPS as FIPS_CODE,
                c.COUNTY as COUNTY_NAME,
                c.STATE as STATE_CODE,
                c.STATE as STATE_NAME,
                COUNT(a.MEASURE_NAME) as DATA_COMPLETENESS
            FROM COUNTIES c
            LEFT JOIN aggregated_scores a ON c.FIPS = a.FIPS 
                AND a.MEASURE_LEVEL = 'sub_measure' 
                AND a.NORMALIZED_SCORE IS NOT NULL
            GROUP BY c.FIPS, c.COUNTY, c.STATE
            HAVING DATA_COMPLETENESS >= 8
            ORDER BY c.STATE, c.COUNTY
        """, conn)
        
        return counties_df
    
    def get_county_metrics(self, county_fips):
        """Get structured metrics for a county"""
        conn = self.get_connection()
        
        # Get county information
        county_info = pd.read_sql("""
            SELECT 
                COUNTY as COUNTY_NAME,
                STATE as STATE_CODE,
                STATE as STATE_NAME
            FROM COUNTIES 
            WHERE FIPS = %s
        """, conn, params=[county_fips])
        
        if county_info.empty:
            return pd.DataFrame(), {}
        
        # Use national percentiles (state comparison would require Stage 3)
        submeasures_query = """
            SELECT 
                PARENT_MEASURE as TOP_LEVEL,
                MEASURE_NAME,
                CASE 
                    WHEN PARENT_MEASURE = 'People' THEN REPLACE(MEASURE_NAME, 'People_', '')
                    WHEN PARENT_MEASURE = 'Productivity' THEN REPLACE(MEASURE_NAME, 'Productivity_', '')
                    WHEN PARENT_MEASURE = 'Place' THEN REPLACE(MEASURE_NAME, 'Place_', '')
                END as SUB_MEASURE,
                PERCENTILE_RANK,
                NORMALIZED_SCORE,
                COMPONENT_COUNT,
                COMPLETENESS_RATIO
            FROM aggregated_scores
            WHERE FIPS = %s 
            AND MEASURE_LEVEL = 'sub_measure'
            AND NORMALIZED_SCORE IS NOT NULL
            AND MEASURE_NAME NOT LIKE '%%Population%%'
            ORDER BY PARENT_MEASURE, MEASURE_NAME
        """
        
        submeasures_df = pd.read_sql(submeasures_query, conn, params=[county_fips])
        
        # Structure data in the format expected by radar chart
        structured_data = {
            'People': {},
            'Productivity': {},
            'Place': {}
        }
        
        # Map the data to the expected structure
        top_level_mapping = {
            'People': 'People',
            'Productivity': 'Productivity',
            'Place': 'Place'
        }
        
        for _, row in submeasures_df.iterrows():
            top_level_key = top_level_mapping.get(row['TOP_LEVEL'])
            if top_level_key:
                # Use human-readable name if available
                sub_measure_key = row['SUB_MEASURE']
                display_key = self.get_display_name(row['MEASURE_NAME'])
                
                # Extract just the sub-measure part from display name
                if display_key != row['MEASURE_NAME']:
                    structured_data[top_level_key][display_key] = row['PERCENTILE_RANK']
                else:
                    structured_data[top_level_key][sub_measure_key] = row['PERCENTILE_RANK']
        
        return county_info, structured_data
    
    def get_submetric_details(self, county_fips, top_level, sub_category):
        """Get detailed metrics for drill-down"""
        conn = self.get_connection()
        
        # Convert display names back to database names
        top_level_mapping = {
            'people': 'People',
            'productivity': 'Productivity',
            'place': 'Place'
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
        details_query = """
            SELECT 
                rm.METRIC_NAME,
                nm.RAW_VALUE as METRIC_VALUE,
                nm.PERCENTILE_RANK,
                ms.IS_REVERSE_METRIC
            FROM normalized_metrics nm
            JOIN RAW_METRICS rm ON nm.FIPS = rm.FIPS AND nm.METRIC_NAME = rm.METRIC_NAME
            LEFT JOIN metric_statistics ms ON nm.METRIC_NAME = ms.METRIC_NAME
            WHERE nm.FIPS = %s 
            AND UPPER(rm.TOP_LEVEL) = UPPER(%s)
            AND UPPER(rm.SUB_MEASURE) = UPPER(%s)
            AND nm.IS_MISSING = FALSE
            ORDER BY nm.PERCENTILE_RANK DESC
        """
        
        details_df = pd.read_sql(details_query, conn, 
                               params=[county_fips, db_top_level, db_sub_category])
        
        # Add human-readable display names
        if not details_df.empty:
            display_names = []
            for _, row in details_df.iterrows():
                display_name = self.get_display_name(row['METRIC_NAME'])
                if display_name == row['METRIC_NAME']:
                    # Use metric name formatted nicely
                    display_name = row['METRIC_NAME'].replace('_', ' ').title()
                display_names.append(display_name)
            
            details_df['DISPLAY_NAME'] = display_names
        
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
    """Create enhanced radar chart for Snowflake data with SVG background"""
    import plotly.graph_objects as go
    import base64
    
    if not county_data:
        return go.Figure()
    
    # Define categories
    categories_config = {
        'People': {'color': '#5760a6', 'label': 'People', 'start_angle': 150, 'end_angle': 270},
        'Productivity': {'color': '#c0b265', 'label': 'Productivity', 'start_angle': 270, 'end_angle': 390},
        'Place': {'color': "#588f57", 'label': 'Place', 'start_angle': 30, 'end_angle': 150}
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
    
    for category in ['People', 'Productivity', 'Place']:
        if category in county_data and county_data[category]:
            config = categories_config[category]
            
            sub_categories = list(county_data[category].keys())
            values = list(county_data[category].values())
            
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
                
                # Add to overall data
                for i, (sub_cat, value, angle) in enumerate(zip(sub_categories, values, angles)):
                    hover_detail = ""
                    try:
                        sample_details = data_provider.get_submetric_details(county_fips, category, sub_cat)
                        if not sample_details.empty:
                            top_metrics = sample_details.head(2)
                            metrics_list = []
                            for _, row in top_metrics.iterrows():
                                display_name = row.get('DISPLAY_NAME', row['METRIC_NAME'])
                                metric_text = f"• {display_name}: {row['METRIC_VALUE']:.1f} ({row['PERCENTILE_RANK']:.0f}%)"
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
    
    # Update layout
    comparison_context = "All US Counties" if data_provider.comparison_mode == 'national' else f"{data_provider.current_state} Counties"
    svg_indicator = " 🎨" if svg_loaded else ""
    main_title = f"<b>{county_name} Sustainability Dashboard</b><br><sub>Percentile Rankings vs. {comparison_context}{svg_indicator} • Click sub-measures for details</sub>"
    
    fig.update_layout(
        polar=dict(
            bgcolor='rgba(255,255,255,0)' if svg_loaded else 'white',
            radialaxis=dict(
                visible=True,
                range=[0, 100],
                tickfont=dict(size=12, color='#374151'),
                gridcolor='rgba(200,200,200,0.3)'
            ),
            angularaxis=dict(
                tickmode='array',
                tickvals=[0, 30, 60, 90, 120, 150, 180, 210, 240, 270, 300, 330],
                ticktext=[''] * 12,
                gridcolor='rgba(200,200,200,0.3)',
                showticklabels=False
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
    """Create enhanced detail chart"""
    import plotly.graph_objects as go
    
    if details_df.empty:
        return go.Figure()
    
    # Add comparison context to title
    comparison_label = "National" if comparison_mode == 'national' else "State"
    title_with_context = f"{title} ({comparison_label} Comparison)"
    
    # Sort by percentile rank
    details_df = details_df.sort_values('PERCENTILE_RANK', ascending=True)
    
    fig = go.Figure()
    
    # Create bars with color coding
    fig.add_trace(go.Bar(
        y=details_df.get('DISPLAY_NAME', details_df['METRIC_NAME']),
        x=details_df['PERCENTILE_RANK'],
        orientation='h',
        marker=dict(
            color=details_df['PERCENTILE_RANK'],
            colorscale='RdYlGn',
            colorbar=dict(title="Percentile"),
            cmin=0,
            cmax=100
        ),
        text=[f"{val:.1f}" for val in details_df['PERCENTILE_RANK']],
        textposition='auto',
        hovertemplate='<b>%{y}</b><br>' +
                      'Value: %{customdata[0]:.1f}<br>' +
                      'Percentile: %{x:.0f}%<br>' +
                      '<extra></extra>',
        customdata=list(zip(details_df['METRIC_VALUE']))
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
    print("🚀 ENHANCED RADAR CHART INTEGRATION - SNOWFLAKE VERSION")
    print("=" * 70)
    
    # Configure Snowflake connection
    connection_params = {
        'user': 'mabel10',
        'password': 'Abvin!123456789',
        'account': 'wthggzd-ah61676',
        'warehouse': 'COMPUTE_WH',
        'database': 'SUSTAINABILITY_DB',
        'schema': 'PUBLIC'
    }
    
    # Test the enhanced integration
    provider = SnowflakeRadarChartDataProvider(connection_params)
    
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
        sample_fips = counties.iloc[0]['FIPS_CODE']
        sample_state = counties.iloc[0]['STATE_CODE']
        county_info, structured_data = provider.get_county_metrics(sample_fips)
        
        if not county_info.empty:
            county_name = f"{county_info.iloc[0]['COUNTY_NAME']}, {county_info.iloc[0]['STATE_CODE']}"
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
            if structured_data.get('People'):
                first_submeasure = list(structured_data['People'].keys())[0]
                print(f"\n🔍 Testing drill-down for '{first_submeasure}':")
                
                details = provider.get_submetric_details(sample_fips, 'People', first_submeasure)
                if not details.empty:
                    print(f"   Found {len(details)} metrics")
                    for _, row in details.head(3).iterrows():
                        display_name = row.get('DISPLAY_NAME', row['METRIC_NAME'])
                        print(f"   • {display_name}: {row['METRIC_VALUE']:.1f} ({row['PERCENTILE_RANK']:.0f}%)")
    
    print(f"\n✨ Key Features:")
    print(f"   • Connected to Snowflake database")
    print(f"   • Human-readable display names from CSV")
    print(f"   • National comparisons ready")
    print(f"   • Enhanced hover text with context")
    print(f"   • SVG background support")
    
    print(f"\n🎯 Ready for integration!")
    print("=" * 70)
