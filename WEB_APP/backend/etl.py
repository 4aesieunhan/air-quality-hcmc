import pandas as pd
import numpy as np
from datetime import datetime
from backend.database import get_raw_data

# Placeholder coordinates dictionary. 
# KEY: station_slug (from database) -> VALUE: (latitude, longitude)
# TODO: Update these coordinates with accurate values for each station.
STATION_COORDS = {
    "hiep-thanh": (10.98, 106.67), # Approximate for Thu Dau Mot
    "hem-108-tran-van-quang": (10.79, 106.65), # Approximate for Tan Binh, HCMC
    "ho-chi-minh-city-us-consulate": (10.783, 106.700), # US Consulate, District 1
    # Add other stations as encountered in the data
}

def load_and_clean_data(file_path=None):
    """
    Loads raw data from database, cleans it, fills missing coordinates, 
    and prepares it for analysis.
    
    Args:
        file_path: Optional, for compatibility if loading from a file is needed later. 
                   Currently defaults to fetching from MongoDB.
    
    Returns:
        pd.DataFrame: Cleaned and merged dataset.
    """
    # 1. Load Data
    print("Loading data from database...")
    stations_df, aqi_df = get_raw_data()
    
    if stations_df is None or aqi_df is None:
        raise Exception("Failed to load data from database.")
    
    if stations_df.empty or aqi_df.empty:
        print("Warning: One of the datasets is empty.")
        return pd.DataFrame()

    # 2. Merge Data
    # Ensure station_slug is consistent (strip whitespace, lowercase)
    stations_df['station_slug'] = stations_df['station_slug'].str.strip()
    aqi_df['station_slug'] = aqi_df['station_slug'].str.strip()
    
    # Merge on station_slug
    # We use a left join on aqi_df to keep all daily records and attach station info
    merged_df = pd.merge(aqi_df, stations_df, on='station_slug', how='left')
    
    # 3. Data Cleaning & Transformation
    
    # Convert date column to datetime
    # Assuming 'date' format is YYYY-MM-DD
    merged_df['date'] = pd.to_datetime(merged_df['date'], errors='coerce')
    
    # Handle Missing Values (Interpolation for time series)
    # Sort by station and date to ensure correct interpolation
    merged_df.sort_values(by=['station_slug', 'date'], inplace=True)
    
    # Columns to interpolate
    pollutants = ['PM25', 'PM10', 'CO', 'SO2', 'O3', 'NO2', 'AQI']
    
    # Interpolate missing values linearly within each station group
    # Limit interpolation to small gaps (e.g., 2 days) to avoid fabricating data for long outages
    for col in pollutants:
        if col in merged_df.columns:
            # Check if column is numeric required for interpolation
             merged_df[col] = pd.to_numeric(merged_df[col], errors='coerce')
             merged_df[col] = merged_df.groupby('station_slug')[col].transform(
                lambda group: group.interpolate(method='linear', limit=2)
            )

    # 4. Fill Coordinates
    # Apply manual coordinates mapping
    def get_lat(slug):
        return STATION_COORDS.get(slug, (None, None))[0]
    
    def get_lon(slug):
        return STATION_COORDS.get(slug, (None, None))[1]

    # If latitude/longitude are missing in DB (which they are), fill them
    if 'latitude' not in merged_df.columns or merged_df['latitude'].isnull().all():
        merged_df['latitude'] = merged_df['station_slug'].apply(get_lat)
    
    if 'longitude' not in merged_df.columns or merged_df['longitude'].isnull().all():
        merged_df['longitude'] = merged_df['station_slug'].apply(get_lon)
        
    # Drop rows where critical info is still missing after all attempts?
    # For now, we keep them but they might be excluded in spatial analysis
    
    print("Data loading and cleaning complete.")
    return merged_df
