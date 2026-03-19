from pymongo import MongoClient
import pandas as pd
import numpy as np
from xgboost import XGBRegressor
import joblib
import os
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

MONGO_URI = "mongodb+srv://anhthuongle1109_db_user:1@airqualitystatistics.gxetykt.mongodb.net/?appName=AirQualityStatisticsI"
DB = "air_quality_hcmc"
COLLECTION = "aqi_daily_imputed_v2"
POLLUTANTS = ["PM2.5", "PM10", "NO2", "SO2", "O3", "CO"]

os.makedirs("models", exist_ok=True)

client = MongoClient(MONGO_URI)
print("Downloading data from MongoDB...")
df = pd.DataFrame(list(client[DB][COLLECTION].find()))

df.columns = [c.strip() for c in df.columns]

def extract_nested_dict(val):
    if isinstance(val, dict):
        return list(val.values())[0] if val else np.nan
    return val

cols_to_unpack = ['PM2', 'imputed_PM2', 'gap_length_PM2', 'is_spike_PM2', 'gap_type_PM2']
for col in cols_to_unpack:
    if col in df.columns:
        df[col] = df[col].apply(extract_nested_dict)

df.rename(columns={
    "PM25": "PM2.5", "pm25": "PM2.5", "PM2_5": "PM2.5", "PM2": "PM2.5",
    "pm10": "PM10", "co": "CO", "no2": "NO2", "so2": "SO2", "o3": "O3",
    "imputed_PM2": "imputed_PM2.5",
    "gap_length_PM2": "gap_length_PM2.5",
    "gap_type_PM2": "gap_type_PM2.5",
    "is_spike_PM2": "is_spike_PM2.5"
}, inplace=True)

for p in POLLUTANTS:
    if p in df.columns:
        df[p] = pd.to_numeric(df[p], errors='coerce')
    if f"gap_length_{p}" in df.columns:
        df[f"gap_length_{p}"] = pd.to_numeric(df[f"gap_length_{p}"], errors='coerce')

df["date"] = pd.to_datetime(df["date"])
df = df.sort_values(["station_name", "date"]).reset_index(drop=True)

eval_results = []

for station in df["station_name"].unique():
    df_s = df[df["station_name"] == station].copy()

    if len(df_s) < 200:
        continue

    df_s["month"] = df_s["date"].dt.month
    df_s["dow"] = df_s["date"].dt.dayofweek
    df_s["dayofyear"] = df_s["date"].dt.dayofyear
    df_s["month_sin"] = np.sin(2*np.pi*df_s["month"]/12)
    df_s["month_cos"] = np.cos(2*np.pi*df_s["month"]/12)
    df_s["dow_sin"] = np.sin(2*np.pi*df_s["dow"]/7)
    df_s["dow_cos"] = np.cos(2*np.pi*df_s["dow"]/7)

    df_s["station_tier_encoded"] = df_s["station_tier"].map({"A": 0, "B": 1, "C": 2})

    for col in POLLUTANTS:
        if col in df_s.columns:
            df_s[f"{col}_lag1"] = df_s[col].shift(1)
            df_s[f"{col}_lag2"] = df_s[col].shift(2)
            df_s[f"{col}_lag3"] = df_s[col].shift(3)

    for target in POLLUTANTS:
        features = [
            "month_sin", "month_cos", "dow_sin", "dow_cos", "dayofyear",
            f"{target}_lag1", f"{target}_lag2", f"{target}_lag3",
            f"gap_length_{target}", "station_tier_encoded"
        ]

        columns_to_use = features + [target]
        if not all(c in df_s.columns for c in columns_to_use):
            continue
            
        model_data = df_s[columns_to_use].dropna()

        if len(model_data) < 100:
             continue

        X = model_data[features].copy()
        y = model_data[target].copy()

        if target == "CO":
            y = np.log1p(y)

        X = X.astype(np.float32)
        y = y.astype(np.float32)

        split = int(len(X) * 0.8)
        X_train, X_test = X[:split], X[split:]
        y_train, y_test = y[:split], y[split:]

        model = XGBRegressor(n_estimators=400, max_depth=5, learning_rate=0.05, subsample=0.8, colsample_bytree=0.8)
        model.fit(X_train, y_train)

        y_pred = model.predict(X_test)
        
        if target == "CO":
            y_test_eval = np.expm1(y_test)
            y_pred_eval = np.expm1(y_pred)
        else:
            y_test_eval = y_test
            y_pred_eval = y_pred

        mae = mean_absolute_error(y_test_eval, y_pred_eval)
        rmse = np.sqrt(mean_squared_error(y_test_eval, y_pred_eval))
        r2 = r2_score(y_test_eval, y_pred_eval)

        print(f"Trained: {station} - {target} | MAE: {mae:.2f} | R2: {r2:.2f}")

        eval_results.append({
            "station": station, "pollutant": target,
            "mae": mae, "rmse": rmse, "r2": r2
        })

        joblib.dump(model, f"models/{station}__{target}.pkl")

pd.DataFrame(eval_results).to_csv("model_evaluation.csv", index=False)
print("Training process completed.")