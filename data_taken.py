import requests
import json
import pandas as pd

# 1. URL bạn vừa tìm được trong tab Headers (Thay link thật của bạn vào đây)
url = "https://airquality.aqi.in/api/v1/getAllStationsMapLocation" # Ví dụ, bạn cần paste link đầy đủ bạn copy được

# 2. Giả lập trình duyệt (Copy User-Agent từ tab Headers của bạn nếu code này không chạy)
headers = {
    'User-Agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Mobile Safari/537.36 Edg/143.0.0.0',
    'Referer': 'https://www.aqi.in/'
}

try:
    # Gửi yêu cầu
    response = requests.get(url, headers=headers)
    
    # Kiểm tra thành công
    if response.status_code == 200:
        data = response.json()
        
        # In thử cấu trúc ra xem
        print("Đã lấy dữ liệu thành công!")
        # Tùy cấu trúc JSON thực tế mà ta truy xuất key khác nhau (thường là 'data' hoặc 'stations')
        # Ví dụ giả định:
        if 'data' in data:
            df = pd.DataFrame(data['data'])
            print(df[['stationName', 'lat', 'lon', 'aqi']].head()) # In thử vài cột quan trọng
        else:
            print(data.keys()) # Xem key chính là gì
            
    else:
        print(f"Lỗi: {response.status_code}")

except Exception as e:
    print(f"Có lỗi xảy ra: {e}")


    