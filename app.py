import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, date 
from entsoe import EntsoePandasClient
import plotly.graph_objects as go
import plotly.express as px
import base64

# --- Streamlit Page Configuration ---
st.set_page_config(
    page_title="Day-Ahead Electricity Price Heatmap",
    layout="wide", # Expands the graph to full width
    initial_sidebar_state="expanded" # Expands the sidebar automatically
)

# Function to load and encode a local image
@st.cache_data
def get_img_as_base64(file):
    with open(file, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode()

# Handle case where logo file might not exist
img = None
try:
    img = get_img_as_base64("assets/logo.svg")
except FileNotFoundError:
    st.warning("Logo file 'assets/logo.svg' not found. Logo will not be displayed.")

# Create columns for the header
col1, col2, col3 = st.columns([5, 1, 1])

with col1:
    st.title("Day-Ahead Electricity Price Heatmap")
    st.markdown("Visualization of day-ahead electricity prices across European countries.")

# Second column: Empty space
with col2:
    st.write("")

# Third column: Clickable logo
with col3:
    if img: # Display logo only if successfully loaded
        st.markdown(
            f'<a href="https://www.egubrno.cz/" target="_blank"><img src="data:image/svg+xml;base64,{img}" width="150"></a>',
            unsafe_allow_html=True
        )

# --- API Token (from Streamlit secrets) ---
# Ensure you have a .streamlit/secrets.toml file
# with content: entsoe_token = "YOUR_TOKEN"
try:
    token = st.secrets["entsoe_token"]
except KeyError:
    st.error("ENTSPE API token not found in `.streamlit/secrets.toml`. Please create the file and add the 'entsoe_token' key.")
    st.stop() # Stop app execution if token is not available

client = EntsoePandasClient(api_key=token)

if 'cache_buster' not in st.session_state:
    st.session_state.cache_buster = 0

# --- Data Fetching Function (with caching) ---
@st.cache_data(ttl=3600)
def get_entsoe_data(selected_day_dt, selected_countries, api_token, resolution_code_entsoe, cache_buster):
    """
    Fetches day-ahead electricity price data from ENTSOE for a selected day with a given resolution.
    Returns a DataFrame, a list of countries for which data could not be fetched, and a list of status messages.
    """
    client_local = EntsoePandasClient(api_key=api_token)
    final_df_cached = pd.DataFrame()
    failed_countries_list = []
    status_messages = [] # List for status messages

    start_ts = pd.Timestamp(selected_day_dt, tz='Europe/Brussels')
    end_ts = pd.Timestamp(selected_day_dt + timedelta(days=1), tz='Europe/Brussels')

    translated_resolution_for_api = resolution_code_entsoe
    if resolution_code_entsoe == "PT60M":
        translated_resolution_for_api = "60min"
    elif resolution_code_entsoe == "PT15M":
        translated_resolution_for_api = "15min"
    
    for country in selected_countries:
        status_messages.append(f"Fetching data for **{country}** ({translated_resolution_for_api})...")
        try:
            price_series = client_local.query_day_ahead_prices(
                country_code=country,
                start=start_ts,
                end=end_ts,
                resolution=translated_resolution_for_api
            )

            if price_series is None or price_series.empty:
                status_messages.append(f"⚠️ Data for **{country}** not available for {selected_day_dt.strftime('%Y-%m-%d')} with {translated_resolution_for_api} resolution.")
                failed_countries_list.append(country)
            else:
                final_df_cached[country] = price_series
                status_messages.append(f"✅ Data for **{country}** fetched successfully.")

        except Exception as e:
            status_messages.append(f"❌ Error fetching data for **{country}** with {translated_resolution_for_api} resolution – {e}")
            failed_countries_list.append(country)
            
    if not final_df_cached.empty:
        expected_freq = 'h' if resolution_code_entsoe == 'PT60M' else '15min'
        expected_index = pd.date_range(start=start_ts, end=end_ts, freq=expected_freq, inclusive='left', tz='Europe/Brussels')
        
        final_df_cached.index = final_df_cached.index.tz_convert('Europe/Brussels')
        final_df_cached = final_df_cached.reindex(expected_index)


    return final_df_cached, failed_countries_list, status_messages

# --- Sidebar Parameters ---
with st.sidebar:
    st.header("Query Parameters")

    today = datetime.now().date()
    default_selected_day = today 

    selected_day_input = st.date_input(
        "Select Date", 
        default_selected_day,
        max_value=today + timedelta(days=1) # Allows selecting today and tomorrow
    )
    
    RESOLUTION_CHANGE_DATE = date(2025, 10, 1)

    selected_resolution_entsoe_code = "PT60M" # Default resolution to hourly

    if selected_day_input >= RESOLUTION_CHANGE_DATE:
        st.subheader("Data Resolution")
        resolution_display_options = {
            "Hourly": "PT60M",
            "15 minutes": "PT15M"
        }
        selected_resolution_display_name = st.radio(
            "Choose time resolution for data:",
            options=list(resolution_display_options.keys()),
            index=0, # Default to "Hourly"
            key="resolution_selector"
        )
        selected_resolution_entsoe_code = resolution_display_options[selected_resolution_display_name]
    else:
        st.info(f"For data before {RESOLUTION_CHANGE_DATE.strftime('%d.%m.%Y')}, only hourly resolution is available.")
        # selected_resolution_entsoe_code is already "PT60M" from default setting, no change needed

    all_countries = ["CZ", "PL", "DE_LU", "FR", "SK", "DK_1", "SE_4", "ES", "AT", "IT_NORD", "NO_3", "HU", "HR", "SI", "BE", "NL", "PT", "IE_SEM", "LT", "LV", "EE", "GR", "FI", "BG", "RO", "CH", "LU"]

    selected_countries = st.multiselect(
        "Select Countries",
        options=all_countries,
        default=["CZ", "DE_LU", "SK", "PL", "AT", "FR",]
    )

    if not selected_countries:
        st.info("Please select at least one country to display data.")
        st.stop()

st.sidebar.markdown("---") 
st.sidebar.markdown(
    f'<span style="color: rgb(255, 153, 0);">by <b><a href="https://www.linkedin.com/in/patrikpetovsky/" target="_blank" style="color: rgb(255, 153, 0); text-decoration: none;">Patrik Petovsky</a></b> <img src="https://upload.wikimedia.org/wikipedia/commons/c/ca/LinkedIn_logo_initials.png" width="20" height="20" style="vertical-align: middle;"></span>', 
    unsafe_allow_html=True
)

# --- Data Fetching and Display ---
# Define global font and size
GLOBAL_FONT_FAMILY = "Arial"
GLOBAL_FONT_SIZE = 18
GLOBAL_FONT_COLOR = "black"

resolution_text = "15-minute" if selected_resolution_entsoe_code == "PT15M" else "hourly"

final_df = pd.DataFrame() # Initialize an empty DataFrame
failed_countries = []
messages_from_fetch = []

# Single status box for all data loading
with st.status(f"Loading {resolution_text} day-ahead prices for {selected_day_input.strftime('%Y-%m-%d')}...", expanded=False) as status:
    # Call the cached function
    final_df, failed_countries, messages_from_fetch = get_entsoe_data(
        selected_day_input, 
        selected_countries, 
        token, 
        selected_resolution_entsoe_code, 
        st.session_state.cache_buster
    )

    # Display individual messages from the fetching process
    for msg in messages_from_fetch:
        status.write(msg)
    
    # Update the final state of the status box
    if failed_countries:
        status.update(label=f"Data loading completed with issues for {len(failed_countries)} countries. ⚠️", state="error", expanded=True)
    else:
        status.update(label=f"Data loading completed for all selected countries. ✅", state="complete", expanded=False)

# After data loading is complete (or errors displayed via status box), proceed with visualization
if not final_df.empty:
    # --- LINE CHART SECTION (DEFAULT ON, NO CHECKBOX) ---
    st.markdown("---") 
    st.subheader(f"Day-Ahead Price Line Chart ({resolution_text} resolution)")

    df_line = final_df.copy()
    df_line.index.name = "Time" 
    df_line_melted = df_line.reset_index().melt(id_vars="Time", var_name="Country", value_name="Price [€/MWh]")

    fig_line = px.line(
        df_line_melted,
        x="Time",
        y="Price [€/MWh]",
        color="Country",
        line_shape="hv", 
        title=f"Day-Ahead Electricity Price Curves for {selected_day_input.strftime('%Y-%m-%d')} ({'15 min' if selected_resolution_entsoe_code == 'PT15M' else 'hourly'})",
        labels={"Time": "Time", "Price [€/MWh]": "Price [€/MWh]", "Country": "Countries"},
        height=600
    )

    fig_line.update_traces(line=dict(width=2.2)) 

    # Apply custom hovertemplate to each trace
    for trace in fig_line.data:
        trace.hovertemplate = '<b>Country: %{fullData.name}</b><br>Time: %{x|%H:%M}<br>Price: %{y:.2f} €/MWh<extra></extra>'


    fig_line.update_layout(
        hovermode='x unified', # Setting for "table of all values"
        font=dict(family=GLOBAL_FONT_FAMILY, size=GLOBAL_FONT_SIZE * 0.9, color=GLOBAL_FONT_COLOR),
        plot_bgcolor='white',
        paper_bgcolor='white',
        xaxis=dict(
            title_font=dict(color=GLOBAL_FONT_COLOR, size=GLOBAL_FONT_SIZE * 1.05, family=GLOBAL_FONT_FAMILY),
            tickfont=dict(color=GLOBAL_FONT_COLOR, size=GLOBAL_FONT_SIZE * 0.9, family=GLOBAL_FONT_FAMILY),
            linecolor=GLOBAL_FONT_COLOR,
            gridcolor="lightgray",
            title = None, # Remove X-axis title "Time", it's clear enough
            
        ),
        yaxis=dict(
            title_font=dict(color=GLOBAL_FONT_COLOR, size=GLOBAL_FONT_SIZE * 1.05, family=GLOBAL_FONT_FAMILY),
            tickfont=dict(color=GLOBAL_FONT_COLOR, size=GLOBAL_FONT_SIZE * 0.9, family=GLOBAL_FONT_FAMILY),
            linecolor=GLOBAL_FONT_COLOR,
            gridcolor="lightgray",
            zerolinecolor = "black"
            
        ),
        title_font=dict(size=GLOBAL_FONT_SIZE * 1.1, color=GLOBAL_FONT_COLOR, family=GLOBAL_FONT_FAMILY),
        legend_title_text=None,
        legend_font=dict(size=GLOBAL_FONT_SIZE * 0.9, color=GLOBAL_FONT_COLOR, family=GLOBAL_FONT_FAMILY),
        annotations=[dict(
            x=1,
            y=1.05,
            xref="paper",
            yref="paper",
            text="PattPet",
            showarrow=False,
            font=dict(size=GLOBAL_FONT_SIZE * 0.7, color="grey", family=GLOBAL_FONT_FAMILY),
            align="right",
            borderpad=4
            )
        ],
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.2,
            xanchor="center",
            x=0.5
        )
    )

    st.plotly_chart(fig_line, use_container_width=True)

    # --- HEATMAP SECTION (now second, with checkbox to show) ---
    st.markdown("---") 
    show_heatmap = st.checkbox("Show Heatmap", value=False, key="heatmap_checkbox")

    if show_heatmap:
        st.subheader(f"Day-Ahead Electricity Prices for {selected_day_input.strftime('%Y-%m-%d')} ({resolution_text} resolution)")

        # --- Colorscale Selection and Reverse button ---
        colorscale_options = ["Default", "Picnic", "balance", "Temps", "Fall", "Tropic", "Portland", "Earth", "PRGn", "RdBu", "Viridis"]
        
        col_cs, col_rev = st.columns([2, 1])
        with col_cs:
            selected_colorscale_name = st.selectbox(
                "Select heatmap colorscale:",
                options=colorscale_options,
                index=0, # Default to "Default"
                key="colorscale_selector"
            )
        with col_rev:
            st.write("") # Space for alignment
            reverse_colorscale = st.checkbox("Reverse Colors", key="reverse_colorscale_checkbox")

        # Prepare the final colorscale to be used
        actual_colorscale_for_plotly = ""
        
        # Define the custom colors for the "Default" scale
        GREEN = '#6AA84F'
        NEUTRAL = '#E1EDDB'
        RED = '#CC0000'

        if selected_colorscale_name == "Default":
            if reverse_colorscale:
                 # Reversed Default: Red for low, Neutral for 0, Green for high
                 actual_colorscale_for_plotly = [
                    [0.0, RED],    
                    [0.5, NEUTRAL], 
                    [1.0, GREEN]   
                ]
            else:
                 # Original Default: Green for low, Neutral for 0, Red for high
                 actual_colorscale_for_plotly = [
                    [0.0, GREEN],  
                    [0.5, NEUTRAL], 
                    [1.0, RED]     
                ]
        else:
            actual_colorscale_for_plotly = selected_colorscale_name
            if reverse_colorscale:
                actual_colorscale_for_plotly += "_r" # Add "_r" for reversed Plotly built-in colorscales
        # --- End Colorscale Selection ---


        # Prepare data for heatmap
        spreads = (final_df.max() - final_df.min()).round(1)
        new_labels = [f"{country}<br>{spread}" for country, spread in zip(final_df.columns, spreads)]
        text_labels = final_df.round(1).astype(str).values
        
        # Y-axis labels for heatmap (for hover and all points)
        heatmap_y_labels = final_df.index.strftime('%H:%M').tolist()
        
        # Tick values and ticktext for Y-axis (dynamically by resolution)
        if selected_resolution_entsoe_code == "PT15M":
            y_axis_tick_vals_display = [h for i, h in enumerate(heatmap_y_labels) if i % 4 == 0]
            # For 15-minute resolution, text in cells will not be displayed
            heatmap_show_text = False
            heatmap_text_font_size = None # Not relevant when text is not displayed
        else:
            y_axis_tick_vals_display = [f"{h:02d}:00" for h in range(24)]
            heatmap_show_text = True
            heatmap_text_font_size = GLOBAL_FONT_SIZE * 0.9 # Standard font size for hourly resolution

        # --- Logic for dynamic zmin, zmax, zmid for the chosen colorscale ---
        data_zmin = final_df.values.min()
        data_zmax = final_df.values.max()

        plot_zmin = data_zmin
        plot_zmax = data_zmax
        plot_zmid = None

        # Determine if the colorscale is diverging for appropriate zmid setting
        # We need to consider the base name of the colorscale, ignoring "_r"
        base_colorscale_name = selected_colorscale_name.replace("_r", "")
        diverging_scales_list = ["Default", "Picnic", "PRGn", "RdBu", "balance", "Temps"] 
        is_diverging_scale = base_colorscale_name in diverging_scales_list
        
        if is_diverging_scale: 
            if data_zmin < 0 and data_zmax > 0:
                max_abs_val = max(abs(data_zmin), abs(data_zmax))
                plot_zmin = -max_abs_val
                plot_zmax = max_abs_val
                plot_zmid = 0
            elif data_zmin >= 0: # All positive, start from 0, zmid not strictly for centering
                plot_zmin = 0
                plot_zmax = data_zmax
                plot_zmid = None 
            elif data_zmax <= 0: # All negative, end at 0, zmid not strictly for centering
                plot_zmin = data_zmin
                plot_zmax = 0
                plot_zmid = None
        else: # For sequential colorscales (Fall, Tropic, Portland, Earth, Viridis)
            if data_zmin >= 0: # All positive
                plot_zmin = 0 # Start from 0 for better visualization
                plot_zmax = data_zmax
            elif data_zmax <= 0: # All negative
                plot_zmin = data_zmin
                plot_zmax = 0 # End at 0
            else: # Mixed, even though a sequential scale is not ideal for mixed data, retain range
                plot_zmin = data_zmin
                plot_zmax = data_zmax
            plot_zmid = None


        fig = go.Figure(
            data=go.Heatmap(
                z=final_df.values,
                x=final_df.columns,
                y=heatmap_y_labels, # All time points for detailed hover
                colorscale=actual_colorscale_for_plotly, # Use the user-selected colorscale (or custom default)
                zmin=plot_zmin, # Dynamically set zmin for color mapping
                zmax=plot_zmax, # Dynamically set zmax for color mapping
                zmid=plot_zmid, # Dynamically set zmid for color mapping
                colorbar_title="price <br>[€/MWh]",
                colorbar=dict(
                    title_font=dict(color=GLOBAL_FONT_COLOR, size=GLOBAL_FONT_SIZE, family=GLOBAL_FONT_FAMILY),
                    tickfont=dict(color=GLOBAL_FONT_COLOR, size=GLOBAL_FONT_SIZE * 0.9, family=GLOBAL_FONT_FAMILY)
                ),
                # Conditional display of text in the heatmap
                text=text_labels if heatmap_show_text else None,
                texttemplate="%{text}" if heatmap_show_text else None,
                textfont=dict(size=heatmap_text_font_size, family=GLOBAL_FONT_FAMILY) if heatmap_show_text else None,
                hoverinfo="z+x+y"
            )
        )

        fig.update_layout(
            title={
                'text': f"Day-Ahead Electricity Prices for {selected_day_input.strftime('%Y-%m-%d')} ({'15 min' if selected_resolution_entsoe_code == 'PT15M' else 'hourly'})",
                'y':0.95,
                'x':0.5,
                'xanchor': 'center',
                'yanchor': 'top',
                'font': dict(size=GLOBAL_FONT_SIZE * 1.3, family=GLOBAL_FONT_FAMILY, color=GLOBAL_FONT_COLOR)
            },
            plot_bgcolor='white',
            paper_bgcolor='white',
            height=800,
            xaxis=dict(
                tickmode='array',
                tickvals=final_df.columns,
                ticktext=new_labels,
                title="Country (bidding zone) / Spread [€/MWh]",
                title_font=dict(color=GLOBAL_FONT_COLOR, size=GLOBAL_FONT_SIZE * 1.1, family=GLOBAL_FONT_FAMILY),
                tickfont=dict(color=GLOBAL_FONT_COLOR, size=GLOBAL_FONT_SIZE, family=GLOBAL_FONT_FAMILY),
                linecolor=GLOBAL_FONT_COLOR,
                gridcolor="lightgray"
            ),
            yaxis=dict(
                autorange="reversed",
                tickmode='array',
                tickvals=y_axis_tick_vals_display, # Use dynamic tick marks
                ticktext=y_axis_tick_vals_display,
                ticklabelposition="outside right",
                tickfont=dict(color=GLOBAL_FONT_COLOR, size=GLOBAL_FONT_SIZE, family=GLOBAL_FONT_FAMILY),
                linecolor=GLOBAL_FONT_COLOR,
                gridcolor="lightgray"
            ),
            font=dict(family=GLOBAL_FONT_FAMILY, size=GLOBAL_FONT_SIZE, color=GLOBAL_FONT_COLOR),
            annotations=[dict(
                x=1,
                y=1.05,
                xref="paper",
                yref="paper",
                text="PattPet",
                showarrow=False,
                font=dict(size=GLOBAL_FONT_SIZE * 0.7, color="grey", family=GLOBAL_FONT_FAMILY),
                align="right",
                borderpad=4
                )
            ]
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    # --- DATA TABLE SECTION ---
    st.markdown("---") # Another visual separator
    show_data_table = st.checkbox("Show Data Table", key="data_table_checkbox")

    if show_data_table:
        st.subheader(f"Data Table ({resolution_text} resolution)")
        st.dataframe(final_df.round(2))

else:
    # This message is displayed only if no data was fetched for ANY selected country
    # and the status box has already displayed error details.
    if not failed_countries and len(selected_countries) > 0: 
         st.warning("No data found for the selected criteria. Try a different date range or other countries.")