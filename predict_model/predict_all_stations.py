from pymongo import MongoClient
import pandas as pd
import numpy as np
import joblib
from datetime import datetime
import os
from aqi_us import calculate_aqi

MONGO_URI = "mongodb+srv://anhthuongle1109_db_user:1@airqualitystatistics.gxetykt.mongodb.net/?appName=AirQualityStatisticsI"
DB_NAME = "air_quality_hcmc"
COLLECTION_NAME = "aqi_daily_imputed_v2"
POLLUTANTS = ["PM2.5", "PM10", "NO2", "SO2", "O3", "CO"]

client = MongoClient(MONGO_URI)
db = client[DB_NAME]

print("Downloading data from MongoDB...")
df = pd.DataFrame(list(db[COLLECTION_NAME].find()))
df.columns = [c.strip() for c in df.columns]

# --- Giải nén và chuẩn hóa tên cột (như các bước trước) ---
def extract_nested_dict(val):
    if isinstance(val, dict): return list(val.values())[0] if val else np.nan
    return val

cols_to_unpack = ['PM2', 'imputed_PM2', 'gap_length_PM2', 'is_spike_PM2', 'gap_type_PM2']
for col in cols_to_unpack:
    if col in df.columns: df[col] = df[col].apply(extract_nested_dict)

df.rename(columns={
    "PM25": "PM2.5", "pm25": "PM2.5", "PM2_5": "PM2.5", "PM2": "PM2.5",
    "pm10": "PM10", "co": "CO", "no2": "NO2", "so2": "SO2", "o3": "O3"
}, inplace=True)

for p in POLLUTANTS:
    if p in df.columns: df[p] = pd.to_numeric(df[p], errors='coerce')
    if f"gap_length_{p}" in df.columns: df[f"gap_length_{p}"] = pd.to_numeric(df[f"gap_length_{p}"], errors='coerce')

df["date"] = pd.to_datetime(df["date"])
df = df.sort_values(["station_name", "date"]).reset_index(drop=True)

results = []

# --- CẤU HÌNH BACKTEST ---
# Chúng ta sẽ dự đoán lại 30 ngày cuối cùng của dữ liệu để so sánh Ground Truth
BACKTEST_DAYS = 30 

for station in df["station_name"].unique():
    df_s = df[df["station_name"] == station].copy()
    if len(df_s) < 100: continue
    
    df_s["station_tier_encoded"] = df_s["station_tier"].map({"A": 0, "B": 1, "C": 2})
    
    # Load models cho trạm
    models = {}
    for p in POLLUTANTS:
        path = f"models/{station}__{p}.pkl"
        if os.path.exists(path): models[p] = joblib.load(path)
    
    if not models: continue

    # 1. DỰ ĐOÁN QUÁ KHỨ (Để vẽ biểu đồ so sánh Ground Truth)
    # Lấy 30 ngày cuối của trạm này
    test_period = df_s.tail(BACKTEST_DAYS)
    
    for i, row in test_period.iterrows():
        preds_historical = {}
        ground_truth = {}
        
        # Lấy lag từ dataframe gốc (vì đây là quá khứ, ta có lag xịn)
        idx = df_s.index.get_loc(i)
        
        for p in POLLUTANTS:
            if p not in models: continue
            
            # Chuẩn bị feature (lag lấy từ các dòng trước dòng i)
            try:
                l1 = df_s.iloc[idx-1][p]
                l2 = df_s.iloc[idx-2][p]
                l3 = df_s.iloc[idx-3][p]
                gap = row[f"gap_length_{p}"]
                tier = row["station_tier_encoded"]
                
                # Tính sin/cos thời gian cho ngày i
                d = row["date"]
                feat = np.array([
                    np.sin(2*np.pi*d.month/12), np.cos(2*np.pi*d.month/12),
                    np.sin(2*np.pi*d.dayofweek/7), np.cos(2*np.pi*d.dayofweek/7),
                    d.dayofyear, l1, l2, l3, gap, tier
                ], dtype=np.float32)
                
                p_val = models[p].predict([feat])[0]
                if p == "CO": p_val = np.expm1(p_val)
                preds_historical[p] = max(0, float(p_val))
                ground_truth[p] = float(row[p])
            except: continue

        if preds_historical:
            # Tính AQI dự đoán
            aqi_p, cat_p, _ = calculate_aqi(**{p.lower().replace(".",""): preds_historical.get(p,0) for p in POLLUTANTS})
            # Tính AQI thực tế
            aqi_g, cat_g, _ = calculate_aqi(**{p.lower().replace(".",""): ground_truth.get(p,0) for p in POLLUTANTS})
            
            results.append({
                "station": station,
                "date": str(row["date"].date()),
                "type": "historical_test",
                "predicted_aqi": aqi_p,
                "ground_truth_aqi": aqi_g,
                "predicted_pollutants": preds_historical,
                "actual_pollutants": ground_truth
            })

    # 2. DỰ ĐOÁN 14 NGÀY TƯƠNG LAI (Dự báo cuốn chiếu)
    latest = df_s.iloc[-1]
    current_date = latest["date"]
    lag_history = {p: [df_s.iloc[-3][p], df_s.iloc[-2][p], df_s.iloc[-1][p]] for p in POLLUTANTS if p in df_s.columns}

    for day_ahead in range(1, 15):
        future_date = current_date + pd.Timedelta(days=day_ahead)
        preds_future = {}
        
        for p in POLLUTANTS:
            if p not in models or lag_history.get(p) is None: continue
            l3, l2, l1 = lag_history[p]
            feat = np.array([
                np.sin(2*np.pi*future_date.month/12), np.cos(2*np.pi*future_date.month/12),
                np.sin(2*np.pi*future_date.dayofweek/7), np.cos(2*np.pi*future_date.dayofweek/7),
                future_date.dayofyear, l1, l2, l3, 0, latest["station_tier_encoded"]
            ], dtype=np.float32)
            
            p_val = models[p].predict([feat])[0]
            if p == "CO": p_val = np.expm1(p_val)
            preds_future[p] = max(0, float(p_val))

        aqi_f, cat_f, _ = calculate_aqi(**{p.lower().replace(".",""): preds_future.get(p,0) for p in POLLUTANTS})
        
        results.append({
            "station": station,
            "date": str(future_date.date()),
            "type": "future_forecast",
            "predicted_aqi": aqi_f,
            "ground_truth_aqi": None, # Tương lai chưa có thực tế
            "predicted_pollutants": preds_future
        })
        
        # Update lag cuốn chiếu
        for p in preds_future:
            lag_history[p].pop(0); lag_history[p].append(preds_future[p])

    print(f"Completed Station: {station}")

# Lưu vào Collection mới để vẽ chart
if results:
    db["aqi_predictions_with_tl"].insert_many(results)
    print("Inserted to MongoDB: aqi_predictions_with_tl")