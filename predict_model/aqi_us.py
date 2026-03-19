def calc_sub_index(C, breakpoints):
    for Clow, Chigh, Ilow, Ihigh in breakpoints:
        if Clow <= C <= Chigh:
            return ((Ihigh - Ilow) / (Chigh - Clow)) * (C - Clow) + Ilow
    return 0

def convert_co_to_ppm(co_ugm3):
    return (co_ugm3 * 24.45) / (28.01 * 1000)

def calculate_aqi(pm25, pm10, co, no2, so2, o3):

    co = convert_co_to_ppm(co)
    co = max(0, min(co, 50))

    pm25_bp = [(0.0, 12.0, 0, 50), (12.1, 35.4, 51, 100), (35.5, 55.4, 101, 150), (55.5, 150.4, 151, 200), (150.5, 250.4, 201, 300), (250.5, 500.4, 301, 500)]
    pm10_bp = [(0, 54, 0, 50), (55, 154, 51, 100), (155, 254, 101, 150), (255, 354, 151, 200), (355, 424, 201, 300), (425, 604, 301, 500)]
    co_bp   = [(0.0, 4.4, 0, 50), (4.5, 9.4, 51, 100), (9.5, 12.4, 101, 150), (12.5, 15.4, 151, 200), (15.5, 30.4, 201, 300), (30.5, 50.4, 301, 500)]
    no2_bp  = [(0, 53, 0, 50), (54, 100, 51, 100), (101, 360, 101, 150), (361, 649, 151, 200), (650, 1249, 201, 300), (1250, 2049, 301, 500)]
    so2_bp  = [(0, 35, 0, 50), (36, 75, 51, 100), (76, 185, 101, 150), (186, 304, 151, 200), (305, 604, 201, 300), (605, 1004, 301, 500)]
    o3_bp   = [(0, 54, 0, 50), (55, 70, 51, 100), (71, 85, 101, 150), (86, 105, 151, 200), (106, 200, 201, 300), (201, 400, 301, 500)]

    sub_indices = {
        "PM2.5": calc_sub_index(pm25, pm25_bp),
        "PM10": calc_sub_index(pm10, pm10_bp),
        "CO": calc_sub_index(co, co_bp),
        "NO2": calc_sub_index(no2, no2_bp),
        "SO2": calc_sub_index(so2, so2_bp),
        "O3": calc_sub_index(o3, o3_bp)
    }

    main = max(sub_indices, key=sub_indices.get)
    aqi = int(sub_indices[main])

    if aqi <= 50:
        cat = "Good"
    elif aqi <= 100:
        cat = "Moderate"
    elif aqi <= 150:
        cat = "Unhealthy for Sensitive Groups"
    elif aqi <= 200:
        cat = "Unhealthy"
    elif aqi <= 300:
        cat = "Very Unhealthy"
    else:
        cat = "Hazardous"

    return aqi, cat, main