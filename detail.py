import requests
import json

# --- CẤU HÌNH ---
# Dùng lại đúng cấu hình bạn đang chạy ổn
url = 'https://airquality.aqi.in/api/v1/getAllStationsMapLocation'
headers = {
    'accept': '*/*',
    'accept-language': 'en-US,en;q=0.9',
    # CHÚ Ý: Copy lại cái Token dài ngoằng của bạn dán vào đây nhé (Token cũ hết hạn thì lấy cái mới)
    'authorization': 'Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJodHRwOi8vYWlycXVhbGl0eS5hcWkuaW4vYXBpL3YxL2xvZ2luIiwiaWF0IjoxNzY4Mzg2MDcwLCJleHAiOjE3NzA4MDUyNzAsIm5iZiI6MTc2ODM4NjA3MCwianRpIjoiOE5rTjRkdFVqZ0FQblhibiIsInN1YiI6IjI5MTY4IiwicHJ2IjoiMjNiZDVjODk0OWY2MDBhZGIzOWU3MDFjNDAwODcyZGI3YTU5NzZmNyJ9.BUahc1My7HF1u8HFTZDlgmgfL4HVz1wP0LdCm21oGps',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
}

print("Đang tải dữ liệu thô để kiểm tra...")
try:
    response = requests.get(url, headers=headers)
    data = response.json()
    
    stations = data.get('Locations', data.get('data', []))
    
    if len(stations) > 0:
        print("\n--- ĐÂY LÀ DỮ LIỆU GỐC CỦA 1 TRẠM (Copy cái này gửi mình) ---")
        # In ra trạm đầu tiên tìm thấy
        first_station = stations[0]
        print(json.dumps(first_station, indent=4)) 
        
        print("\n-------------------------------------------------------------")
        print(f"Tổng số trạm lấy được: {len(stations)}")
    else:
        print("Không tìm thấy trạm nào. (Có thể Token bị lỗi/hết hạn)")

except Exception as e:
    print(f"Lỗi: {e}")