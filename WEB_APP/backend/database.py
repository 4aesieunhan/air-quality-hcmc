from pymongo import MongoClient
import pandas as pd
import logging

from pymongo import MongoClient

uri = "mongodb+srv://anhthuongle1109_db_user:1@airqualitystatistics.gxetykt.mongodb.net/?appName=AirQualityStatistics"

client = MongoClient(uri)

print("Databases:")
print(client.list_database_names())

db = client["air_quality_daily_all_stations"]

print("Collections:")
print(db.list_collection_names())

collection = db["air_daily"]

print("Number of documents:")
print(collection.count_documents({}))


# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# MongoDB Connection Details
MONGO_URI = "mongodb+srv://anhthuongle1109_db_user:1@airqualitystatistics.gxetykt.mongodb.net/?appName=AirQualityStatistics"
DB_NAME = "air_quality_daily_all_stations"

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
    client = get_mongo_client()
    if not client:
        return None, None

    try:
        db = client[DB_NAME]

        collection = db["air_daily"]

        data = list(collection.find())

        if not data:
            logging.warning("No data found in 'air_daily' collection.")
            return pd.DataFrame(), pd.DataFrame()

        df = pd.DataFrame(data)

        if '_id' in df.columns:
            df.drop('_id', axis=1, inplace=True)

        return df, df

    except Exception as e:
        logging.error(f"Error fetching data: {e}")
        return None, None
    finally:
        client.close()
