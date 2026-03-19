import requests
import pandas as pd
import sys
import io
import time
import os
import json

# Fix lỗi hiển thị tiếng Việt
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# --- QUAN TRỌNG: DÁN TOKEN MỚI (F5 WEB ĐỂ LẤY) ---
TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJodHRwOi8vYWlycXVhbGl0eS5hcWkuaW4vYXBpL3YxL2xvZ2luIiwiaWF0IjoxNzY4NDQwOTI0LCJleHAiOjE3NzA4NjAxMjQsIm5iZiI6MTc2ODQ0MDkyNCwianRpIjoiVExERk9GR0xrQUd1NzBQayIsInN1YiI6IjI5MTY4IiwicHJ2IjoiMjNiZDVjODk0OWY2MDBhZGIzOWU3MDFjNDAwODcyZGI3YTU5NzZmNyJ9.6tFIe_qMlmcpGldbhzdVHdeb0jty8gLYiCB_bwzu_oQ" 

# Danh sách 11 trạm cố định
TARGET_STATIONS = [
    {"name": "US Consulate", "slug": "vietnam/ho-chi-minh/ho-chi-minh-city/ho-chi-minh-city-us-consulate"},
    {"name": "Long An - Duc Lap Ha", "slug": "vietnam/ho-chi-minh/ho-chi-minh-city/long-an-xa-duc-lap-ha"},
    {"name": "Nguyen Van Tao", "slug": "vietnam/ho-chi-minh/ho-chi-minh-city/tp-ho-chi-minh-duong-nguyen-van-tao"},
    {"name": "Tay Ninh - Trang Bang", "slug": "vietnam/binh-duong/thu-dau-mot/tay-ninh-thi-xa-trang-bang"},
    {"name": "Long An - Ben Luc", "slug": "vietnam/long-an/tan-an/long-an-tt-van-hoa-huyen-ben-luc"},
    {"name": "Long An - Can Giuoc", "slug": "vietnam/ho-chi-minh/ho-chi-minh-city/long-an-tt-van-hoa-huyen-can-giuoc"},
    {"name": "Hem 108 Tran Van Quang", "slug": "vietnam/ho-chi-minh/ho-chi-minh-city/hem-108-tran-van-quang"},
    {"name": "Duong Ngo Quang Tham", "slug": "vietnam/ho-chi-minh/ho-chi-minh-city/duong-ngo-quang-tham"},
    {"name": "Vung Tau - Phuong 7", "slug": "vietnam/ba-ria-vung-tau/vung-tau/phuong-7"},
    {"name": "Binh Duong - Hiep Thanh", "slug": "vietnam/binh-duong/thanh-pho-thu-dau-mot/hiep-thanh"},
    {"name": "Long An - Phuong 2", "slug": "vietnam/long-an/thanh-pho-tan-an/phuong-2"}
]

URL_DETAIL = "https://airquality.aqi.in/api/v1/getLocationDetailsBySlugNew"

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    'Authorization': f'Bearer {TOKEN}',
    'Accept': 'application/json'
}

def parse_airquality_list(aq_list):
    """
    Hàm đọc dữ liệu từ list 'airquality' (Dựa trên ảnh image_e5846b.jpg)
    """
    result = {}
    if not isinstance(aq_list, list): return result
    
    for item in aq_list:
        name = str(item.get('sensorName', '')).lower().strip()
        val = item.get('sensorData', 0)
        
        # Bắt các chỉ số quan trọng
        if name == 'aqi': result['AQI'] = val # QUAN TRỌNG: Bắt AQI ở đây
        elif name in ['pm25', 'pm2.5']: result['PM2.5'] = val
        elif name == 'pm10': result['PM10'] = val
        elif name == 'co': result['CO'] = val
        elif name == 'no2': result['NO2'] = val
        elif name == 'so2': result['SO2'] = val
        elif name in ['o3', 'ozone']: result['O3'] = val
        elif name in ['t', 'temp']: result['Temp'] = val
        
    return result

def get_realtime_metrics(slug):
    # Luôn thử type="location" trước
    params = {
        "slug": slug,
        "type": "location",
        "lang": "vn",
        "sendevid": "1"
    }
    h = headers.copy()
    h['Referer'] = f'https://www.aqi.in/dashboard/{slug}'

    try:
        res = requests.get(URL_DETAIL, headers=h, params=params, timeout=10)
        
        # Nếu lỗi 400 (sai type), thử lại với type="city"
        if res.status_code == 400:
            params['type'] = 'city'
            res = requests.get(URL_DETAIL, headers=h, params=params, timeout=10)

        if res.status_code == 200:
            data = res.json()
            root_d = data.get('data', {})
            if not root_d: return None

            # 1. Khởi tạo dict chứa dữ liệu
            metrics = {
                'AQI': 0, 'PM2.5': 0, 'PM10': 0, 'CO': 0, 'NO2': 0, 'SO2': 0, 'O3': 0, 'Temp': 0
            }

            # 2. Ưu tiên lấy từ list 'airquality' (Cấu trúc mới trong ảnh bạn gửi)
            if 'airquality' in root_d and isinstance(root_d['airquality'], list):
                # print(f"   (DEBUG: Tim thay list airquality voi {len(root_d['airquality'])} sensor)") 
                parsed = parse_airquality_list(root_d['airquality'])
                metrics.update(parsed)

            # 3. Nếu vẫn bằng 0 thì mới tìm ở ngoài (Fallback cho cấu trúc cũ)
            if metrics['AQI'] == 0: metrics['AQI'] = root_d.get('aqi', 0)
            if metrics['PM2.5'] == 0: metrics['PM2.5'] = root_d.get('pm25', 0)
            if metrics['PM10'] == 0: metrics['PM10'] = root_d.get('pm10', 0)
            if metrics['CO'] == 0: metrics['CO'] = root_d.get('co', 0)
            
            # Lấy thêm địa chỉ
            metrics['Address'] = root_d.get('location', '')
            
            return metrics
            
    except Exception as e:
        print(f"Loi: {e}")
        pass
    return None

# --- CHẠY CHƯƠNG TRÌNH ---
if "DÁN_TOKEN" in TOKEN:
    print("LOI: BAN CHUA DAN TOKEN MOI!")
    sys.exit()

print(f"=== BAT DAU LAY DU LIEU CHO {len(TARGET_STATIONS)} TRAM ===")
final_data = []

for i, item in enumerate(TARGET_STATIONS):
    print(f"[{i+1}/{len(TARGET_STATIONS)}] {item['name']}")
    
    metrics = get_realtime_metrics(item['slug'])
    
    row = {'Station Name': item['name']}
    
    if metrics:
        print(f"   -> OK! AQI: {metrics.get('AQI')} | PM2.5: {metrics.get('PM2.5')} | CO: {metrics.get('CO')}")
        row.update(metrics)
    else:
        print("   -> That bai (Token het han hoac loi mang).")
        row.update({'AQI': 0, 'PM2.5':0, 'PM10':0, 'CO':0})
        
    final_data.append(row)
    time.sleep(1)

if final_data:
    df = pd.DataFrame(final_data)
    cols = ['Station Name', 'AQI', 'PM2.5', 'PM10', 'CO', 'NO2', 'SO2', 'O3', 'Temp', 'Address']
    final_cols = [c for c in cols if c in df.columns]
    
    print("\n" + "="*80)
    print("KET QUA:")
    print(df[final_cols].to_string(index=False))
    
    fn = 'hcm_aqi_realtime_FIXED.csv'
    df.to_csv(fn, index=False, encoding='utf-8-sig')
    print(f"\n-> DA LUU FILE: {os.path.abspath(fn)}")

    