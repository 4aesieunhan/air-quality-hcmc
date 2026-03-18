# MONGO_URI = "mongodb+srv://dinhkntruong_db_user:1@airqualitystatistics.gxetykt.mongodb.net/?appName=AirQualityStatistics"

import pandas as pd
import numpy as np
from pymongo import MongoClient
import certifi  # Thêm thư viện này để tránh lỗi SSL khi kết nối MongoDB Atlas
import xgboost as xgb
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from datetime import datetime, timedelta
import warnings

warnings.filterwarnings('ignore')

# ==========================================
# 1. CẤU HÌNH MONGODB
# ==========================================
# Thay bằng chuỗi kết nối MongoDB Atlas thực tế của nhóm
MONGO_URI = "mongodb+srv://dinhkntruong_db_user:1@airqualitystatistics.gxetykt.mongodb.net/?appName=AirQualityStatistics"
DB_NAME = "air_quality_hcm_full_7stations"
COLLECTION_INPUT = "aqi_daily_t"
COLLECTION_OUTPUT = "aqi_predictions_t"


def get_mongo_connection():
    # Sử dụng certifi để cung cấp chứng chỉ SSL/TLS bảo mật cho kết nối Atlas
    client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
    db = client[DB_NAME]
    return db


# ==========================================
# 2. LẤY & TIỀN XỬ LÝ DỮ LIỆU TỪ MONGODB
# ==========================================
def fetch_and_preprocess_data(db):
    print("Đang tải dữ liệu từ MongoDB Atlas...")
    cursor = db[COLLECTION_INPUT].find({}, {"_id": 0})
    raw_data = list(cursor)

    if not raw_data:
        raise ValueError("Không có dữ liệu trong Database!")

    df = pd.DataFrame(raw_data)

    if isinstance(df['date'].iloc[0], dict):
        df['date'] = df['date'].apply(lambda x: pd.to_datetime(x['$date']))
    else:
        df['date'] = pd.to_datetime(df['date'])

    df['date'] = df['date'].dt.tz_localize(None)

    df['PM25'] = df['pollutants'].apply(lambda x: x.get('PM25') if isinstance(x, dict) else np.nan)
    df['PM10'] = df['pollutants'].apply(lambda x: x.get('PM10') if isinstance(x, dict) else np.nan)

    df = df[['date', 'station_slug', 'station_name', 'aqi', 'PM25', 'PM10']]
    df = df.sort_values(by=['station_slug', 'date']).reset_index(drop=True)

    return df


# ==========================================
# 3. FEATURE ENGINEERING & IMPUTATION
# ==========================================
def process_station_data(station_df, lags=7):
    """
    Xử lý dữ liệu cho TỪNG TRẠM cụ thể.
    Điền khuyết và tạo Lag features cho cả AQI, PM2.5 và PM10.
    """
    df = station_df.copy()

    # Imputation theo chuẩn Pandas 3.0+
    df['aqi'] = df['aqi'].ffill().bfill()
    df['PM25'] = df['PM25'].ffill().bfill()
    df['PM10'] = df['PM10'].ffill().bfill()

    # Tạo Lag features (dùng quá khứ đoán tương lai)
    # Ta phải lag cả PM25 và PM10 vì trong tương lai ta không có sẵn 2 chỉ số này
    for lag in range(1, lags + 1):
        df[f'aqi_lag_{lag}'] = df['aqi'].shift(lag)
        df[f'PM25_lag_{lag}'] = df['PM25'].shift(lag)
        df[f'PM10_lag_{lag}'] = df['PM10'].shift(lag)

    df = df.dropna().reset_index(drop=True)
    return df


# ==========================================
# 4. TRAINING & EVALUATION (CẮT DYNAMIC THEO 14 NGÀY)
# ==========================================
def train_and_evaluate(df, test_days=14):
    """
    Tự động lấy `test_days` ngày cuối cùng của trạm làm Ground Truth.
    """
    max_date = df['date'].max()
    split_date = max_date - timedelta(days=test_days)

    train_df = df[df['date'] <= split_date]
    test_df = df[df['date'] > split_date]

    if len(train_df) < 30:
        print(f"  -> Cảnh báo: Dữ liệu Train quá ít ({len(train_df)} dòng). Kết quả có thể không chính xác!")
        if len(train_df) == 0:
            return None, None

    if test_df.empty:
        print("  -> Lỗi: Không có dữ liệu để Test!")
        return None, None

    # Chỉ dùng các cột lag làm Feature (đúng bản chất dự báo)
    feature_cols = [col for col in df.columns if 'lag' in col]

    X_train, y_train = train_df[feature_cols], train_df['aqi']
    X_test, y_test = test_df[feature_cols], test_df['aqi']

    model = xgb.XGBRegressor(objective='reg:squarederror', n_estimators=100, learning_rate=0.1, random_state=42)
    model.fit(X_train, y_train)

    preds = model.predict(X_test)

    print(
        f"MAE: {mean_absolute_error(y_test, preds):.2f} | RMSE: {np.sqrt(mean_squared_error(y_test, preds)):.2f} | R2: {r2_score(y_test, preds):.2f}")

    test_results = test_df[['date', 'station_slug', 'station_name', 'aqi']].copy()
    test_results = test_results.rename(columns={'aqi': 'ground_truth_aqi'})
    test_results['predicted_aqi'] = np.round(preds, 2)
    test_results['horizon'] = 'historical_test'

    return model, test_results


# ==========================================
# 5. LƯU VÀO MONGODB
# ==========================================
def save_predictions_to_mongo(db, results_df):
    if results_df is None or results_df.empty:
        return

    collection = db[COLLECTION_OUTPUT]
    records = results_df.to_dict('records')

    for rec in records:
        rec['created_at'] = datetime.now()

    # Xóa dữ liệu cũ đi để ghi đè (tránh bị lặp lại khi chạy nhiều lần)
    collection.delete_many({})

    collection.insert_many(records)
    print(f"Đã lưu {len(records)} bản ghi dự đoán vào collection '{COLLECTION_OUTPUT}'")


# ==========================================
# CHẠY LUỒNG CHÍNH
# ==========================================
if __name__ == "__main__":
    db = get_mongo_connection()

    try:
        df_all = fetch_and_preprocess_data(db)
        stations = df_all['station_slug'].unique()
        print(f"Tìm thấy dữ liệu của {len(stations)} trạm.")

        all_predictions = []

        for station in stations:
            print(f"\n--- Đang xử lý trạm: {station} ---")
            station_df = df_all[df_all['station_slug'] == station]

            # Xử lý missing và Lag
            processed_df = process_station_data(station_df, lags=7)

            # Cắt 14 ngày cuối để test, tự động điều chỉnh cho mọi trạm
            model, test_results = train_and_evaluate(processed_df, test_days=14)

            if test_results is not None:
                all_predictions.append(test_results)

        if all_predictions:
            final_results_df = pd.concat(all_predictions, ignore_index=True)
            save_predictions_to_mongo(db, final_results_df)
            print("\nPipeline đã chạy xong thành công!")

    except Exception as e:
        print(f"Lỗi xảy ra: {e}")