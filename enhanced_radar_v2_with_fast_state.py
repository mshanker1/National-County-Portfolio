"""
Enhanced Radar Chart Data Provider for BigQuery
Supports national and state-level comparisons with fast state percentiles
FIXED: Drill-down detail charts now working correctly
"""
import pandas as pd
from google.cloud import bigquery
import numpy as np
from scipy import stats
import plotly.graph_objects as go
import os
import time

class BigQueryRadarChartDataProvider:
    """
    Enhanced data provider with human-readable names and state-level comparison support for BigQuery
    """
    
    def __init__(self, project_id, dataset_id, display_names_file='display_names.csv'):
        self.project_id = project_id
        self.dataset_id = dataset_id
        self.display_names_file = display_names_file
        self.display_names_map = {}
        self.comparison_mode = 'national'
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
        """Check what stage the BigQuery dataset is in"""
        try:
            client = bigquery.Client(project=self.project_id)
            
            # Get list of tables in dataset
            tables = list(client.list_tables(self.dataset_id))
            table_names = [table.table_id for table in tables]
            
            # Check for fast state comparison tables
            has_state_tables = 'state_percentiles' in table_names and 'state_aggregated_scores' in table_names
            
            if 'aggregated_scores' in table_names and 'normalized_metrics' in table_names:
                if has_state_tables:
                    self.stage = 3
                    print("✅ BigQuery Status: Stage 3 Complete (Fast state comparisons available)")
                else:
                    self.stage = 2
                    print("✅ BigQuery Status: Stage 2 Complete (Normalized data available)")
            elif 'raw_metrics' in table_names and 'counties' in table_names:
                self.stage = 1
                print("⚠️  BigQuery Status: Stage 1 Complete (Raw data only)")
            else:
                self.stage = 0
                print("❌ BigQuery Status: No data found")
                
        except Exception as e:
            self.stage = 0
            print(f"❌ BigQuery Error: {e}")
    
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
    
    def get_county_population(self, county_fips):
        """Get population for a county"""
        client = bigquery.Client(project=self.project_id)
        
        query = f"""
            SELECT raw_value as population
            FROM `{self.project_id}.{self.dataset_id}.raw_metrics`
            WHERE fips = '{county_fips}'
            AND metric_name = 'People_Population_Population'
            LIMIT 1
        """
        
        try:
            result = client.query(query).to_dataframe()
            if not result.empty:
                return int(result.iloc[0]['population'])
        except Exception as e:
            print(f"Error fetching population: {e}")
        
        return None
    
    def get_all_counties(self):
        """Get list of all counties for dropdown"""
        client = bigquery.Client(project=self.project_id)
        
        query = f"""
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
        
        counties_df = client.query(query).to_dataframe()
        return counties_df
    
    def get_county_metrics(self, county_fips):
        """Get structured metrics for a county with appropriate comparison"""
        client = bigquery.Client(project=self.project_id)
        
        # Get county information
        county_query = f"""
            SELECT 
                county as county_name,
                state as state_code,
                state as state_name
            FROM `{self.project_id}.{self.dataset_id}.counties`
            WHERE fips = '{county_fips}'
        """
        
        county_info = client.query(county_query).to_dataframe()
        
        if county_info.empty:
            return pd.DataFrame(), {}
        
        if self.comparison_mode == 'state' and self.stage >= 3:
            # Use pre-calculated state percentiles (FAST!)
            submeasures_query = f"""
                SELECT 
                    parent_measure as top_level,
                    measure_name,
                    CASE 
                        WHEN parent_measure = 'People' THEN REPLACE(measure_name, 'People_', '')
                        WHEN parent_measure = 'Prosperity' THEN REPLACE(measure_name, 'Prosperity_', '')
                        WHEN parent_measure = 'Place' THEN REPLACE(measure_name, 'Place_', '')
                    END as sub_measure,
                    state_percentile_rank as percentile_rank,
                    normalized_score,
                    component_count,
                    completeness_ratio
                FROM `{self.project_id}.{self.dataset_id}.state_aggregated_scores`
                WHERE fips = '{county_fips}'
                AND measure_level = 'sub_measure'
                AND state_percentile_rank IS NOT NULL
                AND measure_name NOT LIKE '%Population%'
                ORDER BY parent_measure, measure_name
            """
            
        else:
            # Use national percentiles
            submeasures_query = f"""
                SELECT 
                    parent_measure as top_level,
                    measure_name,
                    CASE 
                        WHEN parent_measure = 'People' THEN REPLACE(measure_name, 'People_', '')
                        WHEN parent_measure = 'Prosperity' THEN REPLACE(measure_name, 'Prosperity_', '')
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
        structured_data = {
            'People': {},
            'Prosperity': {},
            'Place': {}
        }
        
        # Map the data to the expected structure
        top_level_mapping = {
            'People': 'People',
            'Prosperity': 'Prosperity',
            'Place': 'Place'
        }
        
        for _, row in submeasures_df.iterrows():
            top_level_key = top_level_mapping.get(row['top_level'])
            if top_level_key:
                sub_measure_key = row['sub_measure']
                display_key = self.get_display_name(row['measure_name'])
                
                if display_key != row['measure_name']:
                    structured_data[top_level_key][display_key] = row['percentile_rank']
                else:
                    structured_data[top_level_key][sub_measure_key] = row['percentile_rank']
        
        return county_info, structured_data
    
    def get_submetric_details(self, county_fips, top_level, sub_category):
        """Get detailed metrics for drill-down with appropriate comparison"""
        client = bigquery.Client(project=self.project_id)
        
        # Convert display names back to database names
        top_level_mapping = {
            'people': 'People',
            'Prosperity': 'Prosperity',
            'place': 'Place'
        }
        
        db_top_level = top_level_mapping.get(top_level.lower(), top_level)
        
        # Find the database name for this sub-category
        db_sub_category = sub_category
        for db_name, display_name in self.display_names_map.items():
            if display_name == sub_category and db_top_level in db_name:
                parts = db_name.split('_')
                if len(parts) >= 2:
                    db_sub_category = parts[1]
                    break
        
        if self.comparison_mode == 'state' and self.stage >= 3:
            # Use pre-calculated state percentiles (FAST!)
            # FIXED: Start from raw_metrics to ensure we have all the metadata
            details_query = f"""
                SELECT 
                    rm.metric_name,
                    rm.sub_metric_name,
                    rm.raw_value as metric_value,
                    sp.state_percentile as percentile_rank,
                    rm.unit,
                    rm.year,
                    ms.is_reverse_metric
                FROM `{self.project_id}.{self.dataset_id}.raw_metrics` rm
                JOIN `{self.project_id}.{self.dataset_id}.state_percentiles` sp 
                    ON rm.fips = sp.fips AND rm.metric_name = sp.metric_name
                JOIN `{self.project_id}.{self.dataset_id}.normalized_metrics` nm
                    ON rm.fips = nm.fips AND rm.metric_name = nm.metric_name
                LEFT JOIN `{self.project_id}.{self.dataset_id}.metric_statistics` ms 
                    ON rm.metric_name = ms.metric_name
                WHERE rm.fips = '{county_fips}'
                AND LOWER(rm.top_level) = LOWER('{db_top_level}')
                AND LOWER(rm.sub_measure) = LOWER('{db_sub_category}')
                AND nm.is_missing = FALSE
                ORDER BY sp.state_percentile DESC
            """
        else:
            # Use national percentiles
            details_query = f"""
                SELECT 
                    rm.metric_name,
                    rm.sub_metric_name,
                    nm.raw_value as metric_value,
                    nm.percentile_rank,
                    rm.unit,
                    rm.year,
                    ms.is_reverse_metric
                FROM `{self.project_id}.{self.dataset_id}.normalized_metrics` nm
                JOIN `{self.project_id}.{self.dataset_id}.raw_metrics` rm 
                    ON nm.fips = rm.fips AND nm.metric_name = rm.metric_name
                LEFT JOIN `{self.project_id}.{self.dataset_id}.metric_statistics` ms 
                    ON nm.metric_name = ms.metric_name
                WHERE nm.fips = '{county_fips}'
                AND LOWER(rm.top_level) = LOWER('{db_top_level}')
                AND LOWER(rm.sub_measure) = LOWER('{db_sub_category}')
                AND nm.is_missing = FALSE
                ORDER BY nm.percentile_rank DESC
            """
        
        try:
            details_df = client.query(details_query).to_dataframe()
            
            # Add human-readable display names
            if not details_df.empty:
                display_names = []
                for _, row in details_df.iterrows():
                    display_name = self.get_display_name(row['metric_name'])
                    if display_name == row['metric_name'] and row.get('sub_metric_name'):
                        display_name = row['sub_metric_name'].replace('_', ' ').title()
                    display_names.append(display_name)
                
                details_df['display_name'] = display_names
            
            return details_df
            
        except Exception as e:
            print(f"❌ Error in get_submetric_details: {e}")
            print(f"   Query attempted for: {county_fips}, {db_top_level}, {db_sub_category}")
            return pd.DataFrame()


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
    """Enhanced radar chart with custom colors matching reference design"""
    import plotly.graph_objects as go
    import math
    import os
    
    if not county_data:
        return go.Figure()
    
    # Define categories matching original SVG colors
    # People (150-270°) → Prosperity (270-390°) → Place (30-150°)
    categories_config = {
        'People': {'color': '#5760a6', 'label': 'People', 'start_angle': 150, 'end_angle': 270},        # Purple (left side)
        'Prosperity': {'color': '#c0b265', 'label': 'Prosperity', 'start_angle': 270, 'end_angle': 390},  # Gold (bottom)
        'Place': {'color': '#588f57', 'label': 'Place', 'start_angle': 30, 'end_angle': 150}            # Green (top-right)
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
            
            fig.add_layout_image(
                dict(
                    source=svg_data_url,
                    xref="paper",
                    yref="paper",
                    x=0.5,
                    y=0.5,
                    sizex=1.3,
                    sizey=1.3,
                    xanchor="center",
                    yanchor="middle",
                    opacity=0.8,
                    layer="below",
                    sizing="contain"
                )
            )
            svg_loaded = True
            print(f"✅ SVG background loaded from: {svg_path_used}")
    except Exception as e:
        print(f"⚠️ Error loading SVG: {e}")
    
    # SVG background will show the reference circles
    # No need to add them programmatically
    
    # Sector orders
    sector_orders = {
        'People': [
            'Health', 
            'Arts and Culture', 
            'Community', 
            'Education', 
            'Wealth'
        ],
        'Place': [
            'Built Environment', 
            'Climate and Resilience', 
            'Land, Air, Water', 
            'Biodiversity', 
            'Food and Agriculture Systems'
        ],
        'Prosperity': [
            'Employment', 
            'Nonprofit', 
            'Business', 
            'Government', 
            'Energy'
        ]
    }
    
    all_theta = []
    all_r = []
    all_colors = []
    all_hover = []
    all_customdata = []
    all_labels = []
    
    # Process in order: People → Prosperity → Place
    for category in ['People', 'Prosperity', 'Place']:
        if category in county_data and county_data[category]:
            config = categories_config[category]
            correct_order = sector_orders[category]
            
            ordered_sub_categories = []
            ordered_values = []
            
            for correct_name in correct_order:
                found = False
                for sub_cat, value in county_data[category].items():
                    if (correct_name.lower() in sub_cat.lower() or 
                        sub_cat.lower() in correct_name.lower() or
                        correct_name.replace(',', '').replace(' ', '').lower() == sub_cat.replace(',', '').replace(' ', '').lower()):
                        ordered_sub_categories.append(sub_cat)
                        ordered_values.append(value)
                        found = True
                        break
                
                if not found:
                    ordered_sub_categories.append(None)
                    ordered_values.append(None)
            
            sub_categories = ordered_sub_categories
            values = ordered_values
            
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
                    if sub_cat is None or value is None:
                        continue
                    
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
                    except Exception as e:
                        print(f"⚠️ Could not load hover details for {sub_cat}: {e}")
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
    
    # Create the main radar trace matching reference styling
    fig.add_trace(go.Scatterpolar(
        r=all_r,
        theta=all_theta,
        fill='toself',
        fillcolor='rgba(150,150,150,0.15)',  # Light semi-transparent fill
        line=dict(color='rgba(80,80,80,0.8)', width=2),  # Subtle line
        marker=dict(
            size=12,  # Moderate marker size
            color=all_colors,
            line=dict(color='white', width=2)  # White outline
        ),
        name='County Metrics',
        text=[f"{val:.0f}%" for val in all_r],  # Show percentages
        textposition='top center',
        textfont=dict(
            size=8,
            color='#1F2937',
            family='Arial, sans-serif'
        ),
        mode='markers+lines+text',  # Include text labels
        hovertext=all_hover,
        hovertemplate='%{hovertext}<extra></extra>',
        customdata=all_customdata
    ))
    
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
                visible=False,  # Hide for clean look 
                range=[0, 150],  # Extended range to push points outward
                angle=90,
                tickfont=dict(size=12, color='#374151'),
                gridcolor='rgba(200,200,200,0.2)',
                tickmode='array',
                tickvals=[0, 10, 25, 50, 75, 100],
                ticktext=['0', '10', '25', '50', '75', '100']
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
        height=800,
        width=800,
        margin=dict(t=120, b=100, l=100, r=100),
        paper_bgcolor='rgba(255,255,255,0)' if svg_loaded else 'white',
        plot_bgcolor='rgba(255,255,255,0)' if svg_loaded else 'white',
        autosize=False
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


if __name__ == "__main__":
    print("🚀 ENHANCED BIGQUERY RADAR CHART PROVIDER V2.1 - FIXED")
    print("=" * 70)
    print("✅ Module loaded successfully")
    print("📊 Ready for dashboard integration")
    print("🎨 Updated colors: Purple, Orange/Gold, Green")
    print("✨ Population query method added")
    print("🔧 FIXED: Drill-down detail charts now working")
    print("=" * 70)
