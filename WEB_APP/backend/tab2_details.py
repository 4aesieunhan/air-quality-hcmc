import pandas as pd
import datetime

def get_station_current_metrics(df, station_name):
    """
    Returns the latest available pollutant concentrations for a specific station.
    """
    if df.empty:
        return {}

    station_data = df[df['station_name'] == station_name]
    latest_date = station_data['date'].max()
    
    if pd.isna(latest_date):
        return {}
    
    current_data = station_data[station_data['date'] == latest_date].iloc[0]
    
    metrics = {
        'AQI': current_data.get('AQI', None),
        'PM2.5': current_data.get('PM25', None),
        'PM10': current_data.get('PM10', None),
        'CO': current_data.get('CO', None),
        'NO2': current_data.get('NO2', None),
        'SO2': current_data.get('SO2', None),
        'O3': current_data.get('O3', None),
        'Date': latest_date.strftime('%Y-%m-%d')
    }
    
    return metrics

def get_station_time_series(df, station_name, days=30):
    """
    Returns the historical data for the last N days (default 30) for a station.
    Useful for line charts and sparklines.
    """
    if df.empty:
        return pd.DataFrame()

    station_data = df[df['station_name'] == station_name].copy()
    station_data.sort_values(by='date', inplace=True)
    
    # Filter last N days
    latest_date = station_data['date'].max()
    if pd.isna(latest_date):
        return pd.DataFrame()

    start_date = latest_date - pd.Timedelta(days=days)
    filtered_data = station_data[station_data['date'] >= start_date]
    
    return filtered_data[['date', 'AQI', 'PM25', 'PM10']]

def get_calendar_heatmap_data(df, station_name, year=None):
    """
    Prepares data for a calendar heatmap (GitHub style).
    """
    if df.empty:
        return pd.DataFrame()

    station_data = df[df['station_name'] == station_name].copy()
    
    if year:
        station_data = station_data[station_data['date'].dt.year == year]
        
    # Ensure date is the index or formatted correctly for the heatmap library
    # Usually [date, value] is enough.
    heatmap_data = station_data[['date', 'AQI']].rename(columns={'date': 'date', 'AQI': 'value'})
    
    return heatmap_data
