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

import pandas as pd
from backend.database import get_raw_data


from datetime import datetime
import pandas as pd


from datetime import datetime
import pandas as pd

def load_and_clean_data():
    
    df, _ = get_raw_data()

    if df is None or df.empty:
        return pd.DataFrame()

    # Chuẩn hóa tên cột
    df.columns = df.columns.str.strip()
    df.columns = df.columns.str.replace(".", "", regex=False)
    df.columns = df.columns.str.replace(",", "", regex=False)
    df.columns = df.columns.str.replace(" ", "", regex=False)

    # Convert date
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")

        # Lọc tới hôm nay
        today = pd.Timestamp.today().normalize()
        df = df[df["date"] <= today]

    # Convert numeric
    exclude_cols = ["station_slug", "station_name", "latitude", "longitude", "year", "date"]

    for col in df.columns:
        if col not in exclude_cols:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Sort
    if "station_name" in df.columns and "date" in df.columns:
        df = df.sort_values(["station_name", "date"])

    print("Max date after filter:", df["date"].max())
    print("Columns in dataframe:", df.columns.tolist())

    return df
    
