import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium

# 1. Cấu hình trang cơ bản
st.set_page_config(page_title="HCMC Air Quality", layout="wide")
st.title("🌍 Dashboard Chất Lượng Không Khí TP.HCM")
st.markdown("Hiển thị dữ liệu trực tiếp từ 7 trạm đo quan trắc.")

# 2. Tạo dữ liệu giả lập cho 7 trạm tại TP.HCM (Tọa độ thực tế)
# Trong thực tế, bạn sẽ dùng pd.read_csv() để load file data của nhóm
data = {
    'Tên Trạm': ['Trạm Q1', 'Trạm Thủ Đức', 'Trạm Tân Bình', 'Trạm Q7', 'Trạm Bình Thạnh', 'Trạm Gò Vấp', 'Trạm Bình Chánh'],
    'Lat': [10.7769, 10.8500, 10.8015, 10.7336, 10.8106, 10.8275, 10.6859],
    'Lon': [106.7009, 106.7500, 106.6526, 106.7220, 106.7006, 106.6744, 106.5655],
    'AQI': [45, 120, 85, 55, 155, 90, 40] # Chỉ số giả lập
}
df = pd.DataFrame(data)

# Hàm định dạng màu chuẩn theo mức độ ô nhiễm AQI
def get_color(aqi):
    if aqi <= 50: return '#00E400'     # Tốt (Xanh lá)
    elif aqi <= 100: return '#FFFF00'  # Trung bình (Vàng)
    elif aqi <= 150: return '#FF7E00'  # Kém (Cam)
    else: return '#FF0000'             # Xấu (Đỏ)

# 3. Khu vực 1: Thẻ thông số (Metric Cards)
st.subheader("📊 Trạng thái hiện tại")
cols = st.columns(len(df)) # Tạo 7 cột nhỏ nằm ngang
for i, row in df.iterrows():
    # Hiển thị thông số từng trạm
    cols[i].metric(label=row['Tên Trạm'], value=f"{row['AQI']} AQI")

st.divider() # Đường kẻ ngang phân cách

# 4. Khu vực 2: Bản đồ không gian
st.subheader("🗺️ Bản đồ phân bổ không gian")
# Khởi tạo bản đồ lấy trung tâm là TP.HCM
m = folium.Map(location=[10.7769, 106.7009], zoom_start=11, tiles="CartoDB positron")

# Chấm 7 điểm lên bản đồ
for i, row in df.iterrows():
    folium.CircleMarker(
        location=[row['Lat'], row['Lon']],
        radius=12,
        color=get_color(row['AQI']),
        fill=True,
        fill_color=get_color(row['AQI']),
        fill_opacity=0.8,
        tooltip=f"<b>{row['Tên Trạm']}</b><br>AQI: {row['AQI']}" # Pop-up khi hover chuột
    ).add_to(m)

# Render bản đồ ra giao diện Streamlit
st_folium(m, width=1200, height=500)