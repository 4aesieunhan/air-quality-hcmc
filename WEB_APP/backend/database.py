from pymongo import MongoClient
import pandas as pd
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# MongoDB Connection Details
MONGO_URI = "mongodb+srv://dangquangnhat1504_db_user:1@airqualitystatistics.gxetykt.mongodb.net/?appName=AirQualityStatistics"
DB_NAME = "air_quality_hcmc"

def get_mongo_client():
    """Establishes a connection to the MongoDB client."""
    try:
        client = MongoClient(MONGO_URI)
        # Send a ping to confirm a successful connection
        client.admin.command('ping')
        logging.info("Successfully connected to MongoDB.")
        return client
    except Exception as e:
        logging.error(f"Failed to connect to MongoDB: {e}")
        return None

def get_raw_data():
    """
    Fetches raw data from 'stations' and 'aqi_daily' collections.
    Returns two pandas DataFrames: stations_df, aqi_df or None, None on failure.
    """
    client = get_mongo_client()
    if not client:
        return None, None
    
    try:
        db = client[DB_NAME]
        
        # Fetch stations
        stations_collection = db['stations']
        stations_data = list(stations_collection.find())
        if stations_data:
            stations_df = pd.DataFrame(stations_data)
            # Remove MongoDB _id field if present
            if '_id' in stations_df.columns:
                stations_df.drop('_id', axis=1, inplace=True)
        else:
            logging.warning("No data found in 'stations' collection.")
            stations_df = pd.DataFrame()

        # Fetch daily AQI data
        aqi_collection = db['aqi_daily']
        aqi_data = list(aqi_collection.find())
        if aqi_data:
            aqi_df = pd.DataFrame(aqi_data)
            # Remove MongoDB _id field if present
            if '_id' in aqi_df.columns:
                aqi_df.drop('_id', axis=1, inplace=True)
            
            # Flatten pollutants dictionary if it exists as a column (it depends on how pandas reads the nested dict)
            # Assuming 'pollutants' is a dictionary column, we normalize it.
            if 'pollutants' in aqi_df.columns:
                pollutants_df = pd.json_normalize(aqi_df['pollutants'])
                aqi_df = pd.concat([aqi_df.drop('pollutants', axis=1), pollutants_df], axis=1)

        else:
            logging.warning("No data found in 'aqi_daily' collection.")
            aqi_df = pd.DataFrame()
            
        return stations_df, aqi_df
        
    except Exception as e:
        logging.error(f"Error fetching data from MongoDB: {e}")
        return None, None
    finally:
        client.close()
