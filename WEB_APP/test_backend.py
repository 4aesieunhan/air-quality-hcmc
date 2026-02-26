import sys
import os

# Ensure the backend module can be imported
sys.path.append(os.path.join(os.path.dirname(__file__)))

from backend.etl import load_and_clean_data
from backend.tab1_overview import get_city_overview_metrics, get_latest_spatial_data, calculate_idw_surface, get_top_polluted_stations
from backend.tab2_details import get_station_current_metrics, get_station_time_series
from backend.tab3_eda import get_correlation_matrix, get_distribution_data

def test_backend():
    print("="*50)
    print("TESTING BACKEND MODULES")
    print("="*50)
    
    # 1. Test ETL
    print("\n--- Testing ETL Module ---")
    try:
        df = load_and_clean_data()
        if df.empty:
            print("❌ ETL failed: Returned empty DataFrame.")
            return
        print(f"✅ Data loaded successfully. Shape: {df.shape}")
        print("Sample Data:")
        print(df.head())
        
        # Check coordinates presence
        if 'latitude' in df.columns and 'longitude' in df.columns:
            missing_coords = df[df[['latitude', 'longitude']].isnull().any(axis=1)]
            if not missing_coords.empty:
               print(f"⚠️ Warning: {len(missing_coords)} rows have missing coordinates.")
               print(missing_coords[['station_slug']].drop_duplicates())
            else:
               print("✅ All rows have coordinates.")
        else:
            print("❌ Latitude/Longitude columns missing.")

    except Exception as e:
        print(f"❌ ETL failed with error: {e}")
        return

    # 2. Test Tab 1: Overview
    print("\n--- Testing Tab 1: Overview ---")
    try:
        metrics = get_city_overview_metrics(df)
        print(f"City Metrics: {metrics}")
        
        spatial_data = get_latest_spatial_data(df)
        print(f"Spatial Data (Top 5):\n{spatial_data.head()}")
        
        grid_x, grid_y, grid_z = calculate_idw_surface(spatial_data)
        if grid_z is not None:
             print(f"✅ IDW Surface generated. Grid shape: {grid_z.shape}")
        else:
             print("⚠️ IDW Surface generation skipped (not enough data points probably).")
            
        top_stations = get_top_polluted_stations(df)
        print(f"Top Polluted Stations:\n{top_stations}")
        print("✅ Tab 1 functions executed.")
    except Exception as e:
        print(f"❌ Tab 1 failed: {e}")

    # 3. Test Tab 2: Details
    print("\n--- Testing Tab 2: Details ---")
    try:
        station_name = df['station_name'].iloc[0] if not df.empty else "Unknown"
        print(f"Testing for station: {station_name}")
        
        station_metrics = get_station_current_metrics(df, station_name)
        print(f"Current Metrics: {station_metrics}")
        
        time_series = get_station_time_series(df, station_name)
        print(f"Time Series (Last 5):\n{time_series.head()}")
        print("✅ Tab 2 functions executed.")
    except Exception as e:
         print(f"❌ Tab 2 failed: {e}")

    # 4. Test Tab 3: EDA
    print("\n--- Testing Tab 3: EDA ---")
    try:
        corr_matrix = get_correlation_matrix(df, ['PM25', 'PM10', 'AQI'])
        print(f"Correlation Matrix:\n{corr_matrix}")
        
        dist_data = get_distribution_data(df, 'AQI')
        print(f"Distribution Data Support Details: Count={len(dist_data)}, Min={dist_data.min()}, Max={dist_data.max()}")
        print("✅ Tab 3 functions executed.")
    except Exception as e:
        print(f"❌ Tab 3 failed: {e}")

    print("\n" + "="*50)
    print("BACKEND TEST COMPLETED")
    print("="*50)

if __name__ == "__main__":
    test_backend()
