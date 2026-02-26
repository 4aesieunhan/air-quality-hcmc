import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

# Import backend functions
from backend.etl import load_and_clean_data
from backend.tab1_overview import (
    get_city_overview_metrics,
    get_latest_spatial_data,
    get_top_polluted_stations
)
from backend.tab2_details import (
    get_station_current_metrics,
    get_station_time_series,
    get_calendar_heatmap_data
)
from backend.tab3_eda import (
    get_correlation_matrix,
    get_distribution_data
)


# PAGE CONFIG

st.set_page_config(
    page_title="HCMC Air Quality Dashboard",
    layout="wide"
)

st.title("Air Quality Monitoring Dashboard - HCMC")


# LOAD DATA FROM MONGODB

@st.cache_data
def load_data():
    return load_and_clean_data()

df = load_data()

# Stop app if no data
if df.empty:
    st.error("Failed to load data from MongoDB.")
    st.stop()


# CREATE TABS
tab1, tab2, tab3 = st.tabs(["Overview", "Station Details", "EDA"])



# TAB 1 - OVERVIEW
with tab1:

    st.header("City Overview")

    # Get city metrics
    metrics = get_city_overview_metrics(df)

    col1, col2 = st.columns(2)

    col1.metric("City Average AQI", metrics["current_aqi"])
    col2.metric("Status", metrics["status"])

    st.divider()

    # Top polluted stations
    st.subheader("Top Polluted Stations")

    top_stations = get_top_polluted_stations(df)
    st.dataframe(top_stations, use_container_width=True)


# TAB 2 - STATION DETAILS
with tab2:

    st.header("Station Deep Dive")

    # Dropdown for selecting station
    station_list = sorted(df["station_name"].unique())
    selected_station = st.selectbox(
        "Select Station",
        station_list
    )

    # Get station info
    station_info = df[df["station_name"] == selected_station].iloc[0]

    col_left, col_right = st.columns([2, 1])

    # Display station basic info
    with col_left:
        st.subheader(selected_station)
        st.write("Latitude:", station_info["latitude"])
        st.write("Longitude:", station_info["longitude"])
        st.write("Latest Date:", df["date"].max().date())


    # AQI GAUGE

    metrics = get_station_current_metrics(df, selected_station)
    aqi_value = metrics.get("AQI", 0)

    with col_right:

        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number",
            value=aqi_value,
            title={'text': "AQI"},
            gauge={
                'axis': {'range': [0, 300]},
                'steps': [
                    {'range': [0, 50], 'color': "#00e400"},
                    {'range': [50, 100], 'color': "#ffff00"},
                    {'range': [100, 150], 'color': "#ff7e00"},
                    {'range': [150, 200], 'color': "#ff0000"},
                ],
            }
        ))

        st.plotly_chart(fig_gauge, use_container_width=True)

    st.divider()

    # POLLUTANT METRICS + SPARKLINES

    st.subheader("Current Pollutants")

    time_series = get_station_time_series(df, selected_station)

    cols = st.columns(4)
    pollutants = ["PM25", "PM10", "CO", "NO2"]

    for i, pol in enumerate(pollutants):

        current_value = metrics.get(pol, None)

        with cols[i]:
            st.metric(pol, current_value)

            if not time_series.empty:
                st.line_chart(
                    time_series.set_index("date")[pol],
                    height=80
                )

    st.divider()

    # LINE CHART - LAST 30 DAYS

    st.subheader("AQI Trend - Last 30 Days")

    if not time_series.empty:

        fig_line = px.line(
            time_series,
            x="date",
            y="AQI",
            title="AQI Trend"
        )

        st.plotly_chart(fig_line, use_container_width=True)

    st.divider()


    # CALENDAR HEATMAP (BASIC TABLE VERSION)

    st.subheader("Calendar Heatmap")

    heatmap_data = get_calendar_heatmap_data(df, selected_station)

    if not heatmap_data.empty:

        heatmap_data["week"] = heatmap_data["date"].dt.isocalendar().week
        heatmap_data["day"] = heatmap_data["date"].dt.weekday

        pivot = heatmap_data.pivot_table(
            index="week",
            columns="day",
            values="value",
            aggfunc="mean"
        )

        st.dataframe(pivot, use_container_width=True)


# TAB 3 - EDA
with tab3:

    st.header("Exploratory Data Analysis")

    # Correlation Matrix
    st.subheader("Correlation Matrix")

    corr = get_correlation_matrix(
        df,
        ["PM25", "PM10", "CO", "NO2", "SO2", "O3", "AQI"]
    )

    st.dataframe(corr, use_container_width=True)

    st.divider()

    # Distribution of AQI
    st.subheader("AQI Distribution")

    dist_data = get_distribution_data(df, "AQI")

    if not dist_data.empty:
        st.bar_chart(dist_data)