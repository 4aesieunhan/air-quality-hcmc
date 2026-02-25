import pandas as pd
import numpy as np
from scipy.interpolate import griddata

def get_city_overview_metrics(df):
    """
    Calculates the average AQI across all stations for the latest available date.
    """
    if df.empty:
        return {'current_aqi': None, 'status': 'Unknown'}

    latest_date = df['date'].max()
    latest_df = df[df['date'] == latest_date]
    
    current_aqi = latest_df['AQI'].mean()
    
    # Simple AQI status classification
    if current_aqi <= 50:
        status = 'Good'
    elif current_aqi <= 100:
        status = 'Moderate'
    elif current_aqi <= 150:
        status = 'Unhealthy for Sensitive Groups'
    elif current_aqi <= 200:
        status = 'Unhealthy'
    elif current_aqi <= 300:
        status = 'Very Unhealthy'
    else:
        status = 'Hazardous'
        
    return {
        'current_aqi': round(current_aqi, 2),
        'status': status
    }

def get_latest_spatial_data(df):
    """
    Extracts the latest data (Latitude, Longitude, AQI) for mapping.
    """
    if df.empty:
        return pd.DataFrame()

    latest_date = df['date'].max()
    latest_df = df[df['date'] == latest_date][['station_slug', 'latitude', 'longitude', 'AQI']]
    
    # Filter out rows with missing coordinates
    latest_df.dropna(subset=['latitude', 'longitude', 'AQI'], inplace=True)
    
    return latest_df

def calculate_idw_surface(spatial_data, grid_resolution=100):
    """
    Interpolates AQI values over a grid using IDW (Inverse Distance Weighting) or similar method.
    Returns grid coordinates (X, Y) and interpolated values (Z).
    """
    if spatial_data.empty:
        return None, None, None

    points = spatial_data[['latitude', 'longitude']].values
    values = spatial_data['AQI'].values
    
    # Create grid
    min_lat, max_lat = points[:, 0].min(), points[:, 0].max()
    min_lon, max_lon = points[:, 1].min(), points[:, 1].max()
    
    grid_x, grid_y = np.mgrid[min_lat:max_lat:complex(0, grid_resolution), 
                              min_lon:max_lon:complex(0, grid_resolution)]
    
    # Perform interpolation (using 'linear' or 'cubic' for smooth surface, 'nearest' for Voronoi-like)
    # Using 'linear' as simple IDW substitute
    try:
        if len(points) < 4:
           # Fallback for very few points (less than required for triangulation)
             method = 'nearest' 
        else:
             method = 'linear'
             
        grid_z = griddata(points, values, (grid_x, grid_y), method=method)
        
        # Fill NaN values (outside convex hull) with nearest neighbor to extend coverage
        # grid_z = griddata(points, values, (grid_x, grid_y), method='nearest') # Override logic for now?
        # Let's check logic: linear leaves NaNs. Nearest doesn't.
        # We can fill NaNs in linear result with nearest if desired.
        
        if np.isnan(grid_z).any():
             # Fill remaining NaNs with nearest neighbor interpolation
             grid_z_nearest = griddata(points, values, (grid_x, grid_y), method='nearest')
             grid_z = np.where(np.isnan(grid_z), grid_z_nearest, grid_z)
             
        return grid_x, grid_y, grid_z
        
    except Exception as e:
        print(f"Interpolation error: {e}")
        return None, None, None

def get_top_polluted_stations(df, top_k=3):
    """
    Returns the top K stations with the highest AQI currently.
    """
    if df.empty:
        return pd.DataFrame()

    latest_date = df['date'].max()
    latest_df = df[df['date'] == latest_date][['station_name', 'AQI']]
    
    return latest_df.sort_values(by='AQI', ascending=False).head(top_k)
